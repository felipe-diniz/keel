"""clean-code-tools.py and the pins: no real tool, no network, no ~/.cache/keel.

Every test runs with KEEL_TOOLS_HOME in tmp_path (autouse); git runs only in throwaway repos under tmp_path.
"""
import hashlib
import os
import pathlib
import re
import subprocess
from types import SimpleNamespace

import pytest

from conftest import SCRIPTS, load_script

tools = load_script("clean-code-tools.py")


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    home = tmp_path / "keel-tools-home"
    monkeypatch.setenv("KEEL_TOOLS_HOME", str(home))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv("GIT_{}_NAME".format(who), "t")
        monkeypatch.setenv("GIT_{}_EMAIL".format(who), "t@example.com")
    return home


def touch(path, text="", mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if mode:
        path.chmod(mode)
    return path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_run(cwd, *args):
    subprocess.run(["git", "-C", str(cwd)] + list(args), check=True, capture_output=True)


def make_repo(path, files=None):
    path.mkdir(parents=True, exist_ok=True)
    git_run(path, "init", "-q")
    for name, text in (files or {}).items():
        touch(path / name, text)
    if files:
        git_run(path, "add", "-A")
        git_run(path, "commit", "-q", "-m", "init")
    return path



# ---------------------------------------------------------------- tools: platform

@pytest.mark.parametrize("system, machine, key", [
    ("Darwin", "arm64", "macos-arm64"),
    ("Darwin", "x86_64", "macos-x86_64"),
    ("Linux", "x86_64", "linux-x86_64"),
    ("Linux", "aarch64", "linux-aarch64"),
    ("Linux", "amd64", "linux-x86_64"),
    ("Linux", "arm64", "linux-aarch64"),
    ("Darwin", "AMD64", "macos-x86_64"),
    ("Windows", "AMD64", None),
])
def test_platform_key(monkeypatch, system, machine, key):
    monkeypatch.setattr(tools, "platform", SimpleNamespace(system=lambda: system, machine=lambda: machine))
    assert tools.platform_key() == key


def test_platform_pins_unknown_platform_raises(monkeypatch):
    monkeypatch.setattr(tools, "platform", SimpleNamespace(system=lambda: "Windows", machine=lambda: "AMD64"))
    with pytest.raises(tools.ToolError, match="no pinned grammars for this platform"):
        tools.platform_pins()


def test_platform_pins_platform_missing_from_the_pins_raises(monkeypatch):
    monkeypatch.setattr(tools, "platform", SimpleNamespace(system=lambda: "Linux", machine=lambda: "riscv64"))
    with pytest.raises(tools.ToolError, match="linux-riscv64"):
        tools.platform_pins()


def test_platform_pins_returns_the_entry_of_this_platform(monkeypatch):
    monkeypatch.setattr(tools, "platform", SimpleNamespace(system=lambda: "Linux", machine=lambda: "x86_64"))
    assert tools.platform_pins() == tools.pins()["parsers"]["platforms"]["linux-x86_64"]


# ---------------------------------------------------------------- tools: libs, parsers, checkout (fake pins)

LIBS = {"libone.so": b"one-bytes", "libtwo.so": b"two-bytes"}
BUNDLE = b"bundle-bytes"


def fake_data(sha_value="a" * 40):
    return {"python": "3.12",
            "tools": {"crapper": {"repo": "https://example.invalid/c.git", "sha": sha_value}},
            "parsers": {"version": "9.9.9", "languages": ["python"],
                        "platforms": {"linux-x86_64": {"bundle": sha(BUNDLE),
                                                       "libs": {name: sha(data) for name, data in LIBS.items()}}}}}


@pytest.fixture
def pinned(monkeypatch):
    data = fake_data()
    monkeypatch.setattr(tools, "pins", lambda: data)
    monkeypatch.setattr(tools, "platform_key", lambda: "linux-x86_64")
    return data


def write_libs(base, data, contents):
    directory = tools.libs_dir(base, data)
    os.makedirs(directory, exist_ok=True)
    for name, blob in contents.items():
        with open(os.path.join(directory, name), "wb") as handle:
            handle.write(blob)


def test_cache_root_is_the_env_override_not_the_home_cache(isolated_env):
    assert tools.cache_root() == str(isolated_env)
    assert ".cache/keel" not in tools.parsers_dir(fake_data())


def test_libs_problems_missing_lib(pinned):
    write_libs(tools.parsers_dir(pinned), pinned, {"libone.so": LIBS["libone.so"]})
    assert tools.libs_problems() == ["grammar libtwo.so is missing"]


def test_libs_problems_everything_missing_when_the_folder_does_not_exist(pinned):
    assert sorted(tools.libs_problems()) == ["grammar libone.so is missing", "grammar libtwo.so is missing"]


def test_libs_problems_wrong_content(pinned):
    write_libs(tools.parsers_dir(pinned), pinned, dict(LIBS, **{"libtwo.so": b"tampered"}))
    problems = tools.libs_problems()
    assert len(problems) == 1
    assert "libtwo.so" in problems[0] and "does not match its pinned sha256" in problems[0]


def test_libs_problems_correct_content(pinned):
    write_libs(tools.parsers_dir(pinned), pinned, LIBS)
    assert tools.libs_problems() == []


def test_libs_problems_unknown_platform_raises(pinned, monkeypatch):
    monkeypatch.setattr(tools, "platform_key", lambda: "linux-riscv64")
    with pytest.raises(tools.ToolError):
        tools.libs_problems()


def download_that_writes(monkeypatch, data, contents, bundle=None):
    """A run_step with the real call shape: the download lands in the staging dir given by the env."""
    calls = []

    def run_step(command, what, env=None):
        calls.append((command, what, env))
        staging = env["TREE_SITTER_LANGUAGE_PACK_CACHE_DIR"]
        write_libs(staging, data, contents)
        if bundle is not None:
            bundles = os.path.join(staging, "tree-sitter-language-pack", "v" + data["parsers"]["version"], "bundles")
            os.makedirs(bundles)
            with open(os.path.join(bundles, "bundle.tar.zst"), "wb") as handle:
                handle.write(bundle)

    monkeypatch.setattr(tools, "run_step", run_step)
    return calls


def test_install_parsers_wrong_lib_aborts_and_deletes_the_staging(pinned, monkeypatch):
    calls = download_that_writes(monkeypatch, pinned, dict(LIBS, **{"libone.so": b"evil"}))
    final = tools.parsers_dir(pinned)
    with pytest.raises(tools.ToolError, match="does not match its pinned sha256.*Nothing was installed"):
        tools.install_parsers(pinned)
    assert not os.path.exists(final + ".partial")
    assert not os.path.exists(final)
    assert len(calls) == 1


def test_install_parsers_missing_lib_after_download_aborts(pinned, monkeypatch):
    download_that_writes(monkeypatch, pinned, {"libone.so": LIBS["libone.so"]})
    final = tools.parsers_dir(pinned)
    with pytest.raises(tools.ToolError, match="libtwo.so is missing"):
        tools.install_parsers(pinned)
    assert not os.path.exists(final + ".partial")
    assert not os.path.exists(final)


def test_install_parsers_wrong_bundle_aborts_even_with_right_libs(pinned, monkeypatch):
    download_that_writes(monkeypatch, pinned, LIBS, bundle=b"other-bundle")
    final = tools.parsers_dir(pinned)
    with pytest.raises(tools.ToolError, match="grammar bundle does not match"):
        tools.install_parsers(pinned)
    assert not os.path.exists(final + ".partial")
    assert not os.path.exists(final)


def test_install_parsers_success_moves_staging_to_final(pinned, monkeypatch):
    calls = download_that_writes(monkeypatch, pinned, LIBS, bundle=BUNDLE)
    final = tools.parsers_dir(pinned)
    os.makedirs(final + ".partial")
    leftover = os.path.join(final + ".partial", "leftover")
    with open(leftover, "w") as handle:
        handle.write("from an earlier run")
    tools.install_parsers(pinned)
    assert os.path.isdir(final)
    assert not os.path.exists(final + ".partial")
    assert not os.path.exists(os.path.join(final, "leftover"))
    assert tools.libs_problems(final, pinned) == []
    command, what, env = calls[0]
    assert what == "download the grammars"
    assert command[1:3] == ["-I", "-c"] and command[-1:] == ["python"]
    assert env["TREE_SITTER_LANGUAGE_PACK_CACHE_DIR"] == final + ".partial"


def test_install_parsers_already_verified_does_not_download(pinned, monkeypatch):
    write_libs(tools.parsers_dir(pinned), pinned, LIBS)
    monkeypatch.setattr(tools, "run_step", lambda *args, **kwargs: pytest.fail("must not download"))
    tools.install_parsers(pinned)


def test_install_parsers_replaces_a_corrupted_final_when_the_new_download_is_right(pinned, monkeypatch):
    final = tools.parsers_dir(pinned)
    write_libs(final, pinned, dict(LIBS, **{"libone.so": b"corrupted"}))
    download_that_writes(monkeypatch, pinned, LIBS)
    tools.install_parsers(pinned)
    assert tools.libs_problems(final, pinned) == []


# ---------------------------------------------------------------- tools: checkout_problem

def test_checkout_problem_not_installed(pinned):
    assert tools.checkout_problem("crapper", pinned) == "crapper is not installed"


def test_checkout_problem_not_a_git_checkout(pinned):
    os.makedirs(tools.tool_dir("crapper", pinned))
    assert tools.checkout_problem("crapper", pinned) == "crapper checkout is not at the pinned SHA"


def checked_out_tool(pinned, monkeypatch):
    """A real local git repo standing in for the tool's checkout, at the SHA the pins name."""
    directory = tools.tool_dir("crapper", pinned)
    make_repo(pathlib.Path(directory), {"src/a.clj": "(ns a)\n"})
    head = subprocess.run(["git", "-C", directory, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    pinned["tools"]["crapper"]["sha"] = head
    new_dir = tools.tool_dir("crapper", pinned)
    os.rename(directory, new_dir)
    return new_dir


def test_checkout_problem_none_when_at_the_pinned_sha_and_clean(pinned, monkeypatch):
    checked_out_tool(pinned, monkeypatch)
    assert tools.checkout_problem("crapper", pinned) is None


def test_checkout_problem_local_change(pinned, monkeypatch):
    directory = checked_out_tool(pinned, monkeypatch)
    with open(os.path.join(directory, "src/a.clj"), "a") as handle:
        handle.write("(def x 1)\n")
    assert tools.checkout_problem("crapper", pinned) == "crapper checkout has local changes"


def test_checkout_problem_wrong_sha(pinned, monkeypatch):
    checked_out_tool(pinned, monkeypatch)
    directory = tools.tool_dir("crapper", pinned)
    pinned["tools"]["crapper"]["sha"] = "b" * 40
    os.rename(directory, tools.tool_dir("crapper", pinned))
    assert tools.checkout_problem("crapper", pinned) == "crapper checkout is not at the pinned SHA"


# ---------------------------------------------------------------- tools: sandbox_prefix / profile

def fake_machine(monkeypatch, system, binaries, probe_ok=None):
    monkeypatch.setattr(tools, "platform", SimpleNamespace(system=lambda: system, machine=lambda: "x86_64"))
    monkeypatch.setattr(tools, "shutil", SimpleNamespace(which=lambda name: "/usr/bin/" + name if name in binaries
                                                         else None))
    monkeypatch.setattr(tools, "probe", lambda command: command[0] in (binaries if probe_ok is None else probe_ok))


def test_sandbox_prefix_darwin_uses_sandbox_exec_with_the_profile(monkeypatch):
    fake_machine(monkeypatch, "Darwin", ["sandbox-exec"])
    assert tools.sandbox_prefix() == ["sandbox-exec", "-p", tools.DARWIN_PROFILE]


def test_sandbox_prefix_darwin_without_sandbox_exec_is_none(monkeypatch):
    fake_machine(monkeypatch, "Darwin", [])
    assert tools.sandbox_prefix() is None


def test_sandbox_prefix_linux_without_bwrap_or_unshare_is_none(monkeypatch):
    fake_machine(monkeypatch, "Linux", [])
    assert tools.sandbox_prefix() is None


def test_sandbox_prefix_linux_prefers_bwrap_with_unshare_net(monkeypatch):
    fake_machine(monkeypatch, "Linux", ["bwrap", "unshare"])
    prefix = tools.sandbox_prefix()
    assert prefix[0] == "bwrap" and "--unshare-net" in prefix and prefix[-1] == "--"


def test_sandbox_prefix_linux_falls_back_to_unshare_when_bwrap_does_not_work(monkeypatch):
    fake_machine(monkeypatch, "Linux", ["bwrap", "unshare"], probe_ok=["unshare"])
    prefix = tools.sandbox_prefix()
    assert prefix[0] == "unshare" and "--net" in prefix


def test_sandbox_prefix_linux_tools_present_but_none_works_is_none(monkeypatch):
    fake_machine(monkeypatch, "Linux", ["bwrap", "unshare"], probe_ok=[])
    assert tools.sandbox_prefix() is None


def test_sandbox_prefix_unsupported_system_is_none(monkeypatch):
    fake_machine(monkeypatch, "Windows", ["bwrap", "sandbox-exec"])
    assert tools.sandbox_prefix() is None


def test_darwin_profile_denies_outbound_and_has_no_measured_leak():
    # Measured on macOS: allowing `network*` to unix sockets let outbound traffic through.
    profile = tools.DARWIN_PROFILE
    assert "(deny network-outbound)" in profile
    assert "unix-socket" not in profile
    assert "network*" not in profile
    assert '(allow network-outbound (remote ip "localhost:*"))' in profile
    assert profile.index("(deny network-outbound)") < profile.index("(allow network-outbound")


# ---------------------------------------------------------------- tools: tool_command

def test_tool_command_refuses_when_problems_is_not_empty(monkeypatch):
    monkeypatch.setattr(tools, "problems", lambda: ["x"])
    with pytest.raises(tools.ToolError) as error:
        tools.tool_command("dryer", ["-"], [])
    assert "not ready (x)" in str(error.value)
    assert "clean-code-measure.py" in str(error.value) and "install" in str(error.value)


def test_tool_command_builds_the_isolated_command_and_env(monkeypatch, isolated_env):
    monkeypatch.setattr(tools, "problems", lambda: [])
    command, env = tools.tool_command("mutator", ["lcov", "--x"], ["sandbox-exec", "-p", "profile"])
    assert command[:3] == ["sandbox-exec", "-p", "profile"]
    assert command[3:] == [tools.venv_python(), "-I", tools.SHIM, "mutator", "lcov", "--x"]
    assert tools.venv_python().startswith(str(isolated_env))
    sources = env["KEEL_TOOL_SRC"].split(os.pathsep)
    assert sources == sorted([os.path.join(tools.tool_dir("crapper"), "src"),
                              os.path.join(tools.tool_dir("mutator"), "src")])
    assert env["TREE_SITTER_LANGUAGE_PACK_CACHE_DIR"] == tools.parsers_dir()
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"


def test_tool_command_unknown_tool_name_and_no_sandbox(monkeypatch):
    monkeypatch.setattr(tools, "problems", lambda: [])
    command, env = tools.tool_command("spans", ["-"], None)
    assert command[0] == tools.venv_python()
    assert command[-2:] == ["spans", "-"]
    assert env["KEEL_TOOL_SRC"] == os.path.join(tools.tool_dir("crapper"), "src")


def test_problems_on_an_empty_home_lists_every_tool_the_venv_and_the_grammars(isolated_env):
    found = tools.problems()
    assert [p for p in found if p.split(" ")[0] in ("crapper", "dryer", "mutator")] == [
        "crapper is not installed", "dryer is not installed", "mutator is not installed"]
    assert "the tools' Python environment is not installed" in found
    assert not isolated_env.exists()


# ---------------------------------------------------------------- pins: clean-code-tools.json / requirements

def test_pins_tools_are_pinned_to_a_full_sha():
    data = tools.pins()
    assert sorted(data["tools"]) == ["crapper", "dryer", "mutator"]
    for name, spec in data["tools"].items():
        assert re.fullmatch(r"[0-9a-f]{40}", spec["sha"]), name
        assert spec["repo"].startswith("https://") and spec["repo"].endswith(".git"), name


def test_pins_every_platform_has_a_bundle_and_four_lib_hashes():
    data = tools.pins()
    assert sorted(data["parsers"]["platforms"]) == ["linux-aarch64", "linux-x86_64", "macos-arm64", "macos-x86_64"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", data["parsers"]["version"])
    for key, platform_pin in data["parsers"]["platforms"].items():
        assert re.fullmatch(r"[0-9a-f]{64}", platform_pin["bundle"]), key
        assert len(platform_pin["libs"]) == 4, key
        for name, digest in platform_pin["libs"].items():
            assert re.fullmatch(r"[0-9a-f]{64}", digest), (key, name)
            assert name.endswith(".dylib" if key.startswith("macos") else ".so"), (key, name)


def requirement_blocks():
    """name==version line -> its --hash entries (hash and comment lines are indented continuations)."""
    blocks, current = {}, None
    with open(str(SCRIPTS / "clean-code-requirements.txt"), encoding="utf-8") as handle:
        for line in handle.read().splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            if line[0] in " \t":
                if current is not None and line.strip().startswith("--hash="):
                    blocks[current].append(line.strip().rstrip("\\").strip())
                continue
            current = line.rstrip("\\").strip()
            blocks[current] = []
    return blocks


def test_requirements_pin_exact_versions_with_hashes():
    blocks = requirement_blocks()
    assert len(blocks) >= 2
    for requirement, hashes in blocks.items():
        assert re.match(r"^[A-Za-z0-9._-]+(\[[A-Za-z0-9,._-]+\])?==[A-Za-z0-9.!+_-]+(\s*;.*)?$", requirement), requirement
        assert not re.search(r"[<>~*]|\s@\s|://|^-", requirement), requirement
        assert hashes, requirement
        for entry in hashes:
            assert re.fullmatch(r"--hash=sha256:[0-9a-f]{64}", entry), (requirement, entry)


def test_requirements_pin_the_grammar_package_at_the_version_of_the_lib_pins():
    pinned_versions = {name.split("==")[0]: name.split("==")[1].split()[0] for name in requirement_blocks()}
    assert pinned_versions["tree-sitter-language-pack"] == tools.pins()["parsers"]["version"]
