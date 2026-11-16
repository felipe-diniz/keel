#!/usr/bin/env python3
"""Pinned install, integrity check and network isolation of the clean-code tools (crapper, dryer, mutator).

Third-party code that runs inside the user's repository, so:
- each tool is a git checkout at the SHA in `clean-code-tools.json`, in the user's cache, never a branch or HEAD;
- its Python dependencies are installed from `clean-code-requirements.txt` with every hash required, wheels only;
- the tree-sitter grammars (native libraries the language pack downloads) are fetched ONLY by `install`, and their
  bundle and each library must match the sha256 recorded in keel, else the download is deleted and install aborts;
- every run re-checks the checkout (SHA, no local change) and the libraries' hashes, and runs inside a sandbox with
  no network (macOS `sandbox-exec`; Linux `bwrap`, else `unshare`); without one it refuses unless the caller passes
  an explicit flag.
Updating a tool is an edit of the pins, reviewed like any change; nothing updates on its own.

Usage (normally through clean-code-measure.py):
  clean-code-tools.py status    what is installed and what is missing
  clean-code-tools.py install   clone, create the environment, fetch and verify the grammars (uses the network)
"""
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PINS_FILE = os.path.join(HERE, "clean-code-tools.json")
REQUIREMENTS = os.path.join(HERE, "clean-code-requirements.txt")
SHIM = os.path.join(HERE, "clean-code-shim.py")
# Outbound traffic denied except to loopback: unit tests may bind localhost; DNS, HTTP and raw IPs are refused.
# Measured on macOS: a profile that also allows `network*` to unix sockets lets outbound traffic through.
DARWIN_PROFILE = ('(version 1)(allow default)(deny network-outbound)'
                  '(allow network-outbound (remote ip "localhost:*"))')


class ToolError(Exception):
    """Something the user has to do before measuring; the message says what."""


def pins():
    with open(PINS_FILE, encoding="utf-8") as handle:
        return json.load(handle)


def cache_root():
    return os.path.expanduser(os.environ.get("KEEL_TOOLS_HOME") or "~/.cache/keel/tools")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def tool_dir(name, data=None):
    data = data or pins()
    return os.path.join(cache_root(), "{}@{}".format(name, data["tools"][name]["sha"]))


def venv_dir():
    digest = sha256_file(REQUIREMENTS)[:12]
    return os.path.join(cache_root(), "venv@{}-py{}".format(digest, pins()["python"]))


def venv_python():
    return os.path.join(venv_dir(), "bin", "python")


def parsers_dir(data=None):
    data = data or pins()
    return os.path.join(cache_root(), "parsers@tslp-{}".format(data["parsers"]["version"]))


def platform_key():
    system = {"Darwin": "macos", "Linux": "linux"}.get(platform.system())
    machine = platform.machine().lower()
    if machine in ("amd64", "x86_64"):
        machine = "x86_64"
    elif machine in ("arm64", "aarch64"):
        machine = "arm64" if system == "macos" else "aarch64"
    return "{}-{}".format(system, machine) if system else None


def platform_pins(data=None):
    data = data or pins()
    key = platform_key()
    found = data["parsers"]["platforms"].get(key)
    if not found:
        raise ToolError("no pinned grammars for this platform ({}); the tools run on macOS and Linux "
                        "(x86_64, arm64)".format(key))
    return found


def libs_dir(base=None, data=None):
    data = data or pins()
    base = base or parsers_dir(data)
    return os.path.join(base, "tree-sitter-language-pack", "v" + data["parsers"]["version"], "libs")


def git(directory, *args):
    try:
        result = subprocess.run(["git", "-C", directory] + list(args), capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def checkout_problem(name, data):
    directory = tool_dir(name, data)
    if not os.path.isdir(directory):
        return "{} is not installed".format(name)
    if git(directory, "rev-parse", "HEAD") != data["tools"][name]["sha"]:
        return "{} checkout is not at the pinned SHA".format(name)
    if git(directory, "status", "--porcelain", "--untracked-files=no") != "":
        return "{} checkout has local changes".format(name)
    return None


def libs_problems(base=None, data=None):
    data = data or pins()
    directory = libs_dir(base, data)
    problems = []
    for name, expected in sorted(platform_pins(data)["libs"].items()):
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            problems.append("grammar {} is missing".format(name))
        elif sha256_file(path) != expected:
            problems.append("grammar {} does not match its pinned sha256".format(name))
    return problems


def problems():
    """Everything that stops a run, empty when the tools are ready."""
    data = pins()
    found = [problem for problem in (checkout_problem(name, data) for name in sorted(data["tools"])) if problem]
    if not os.path.isfile(venv_python()):
        found.append("the tools' Python environment is not installed")
    try:
        found.extend(libs_problems(data=data))
    except ToolError as error:
        found.append(str(error))
    return found


def run_step(command, what, env=None):
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        tail = "\n".join((result.stderr or result.stdout).strip().splitlines()[-5:])
        raise ToolError("{} failed:\n{}".format(what, tail))


def install_checkout(name, data):
    directory = tool_dir(name, data)
    if checkout_problem(name, data) is None:
        return
    shutil.rmtree(directory, ignore_errors=True)
    staging = directory + ".partial"
    shutil.rmtree(staging, ignore_errors=True)
    spec = data["tools"][name]
    run_step(["git", "clone", "--quiet", "--no-checkout", spec["repo"], staging], "clone " + name)
    run_step(["git", "-C", staging, "checkout", "--quiet", "--detach", spec["sha"]], "checkout " + name)
    if git(staging, "rev-parse", "HEAD") != spec["sha"]:
        shutil.rmtree(staging, ignore_errors=True)
        raise ToolError("{} did not check out at the pinned SHA".format(name))
    os.rename(staging, directory)


def install_venv(data):
    if os.path.isfile(venv_python()):
        return
    uv = shutil.which("uv")
    if not uv:
        raise ToolError("uv is not installed: install it (https://docs.astral.sh/uv/) and run install again")
    run_step([uv, "venv", "--quiet", "--python", data["python"], venv_dir()], "create the environment")
    run_step([uv, "pip", "install", "--quiet", "--python", venv_python(), "--require-hashes", "--no-build",
              "-r", REQUIREMENTS], "install the pinned dependencies")


def bundle_problem(base, data):
    bundles = os.path.join(base, "tree-sitter-language-pack", "v" + data["parsers"]["version"], "bundles")
    expected = platform_pins(data)["bundle"]
    names = os.listdir(bundles) if os.path.isdir(bundles) else []
    if not names:
        return None
    if any(sha256_file(os.path.join(bundles, name)) != expected for name in names):
        return "the grammar bundle does not match its pinned sha256"
    return None


def install_parsers(data):
    final = parsers_dir(data)
    if os.path.isdir(final) and not libs_problems(final, data):
        return
    staging = final + ".partial"
    shutil.rmtree(staging, ignore_errors=True)
    env = dict(os.environ, TREE_SITTER_LANGUAGE_PACK_CACHE_DIR=staging)
    code = "import sys, tree_sitter_language_pack as t; t.download(sys.argv[1:])"
    run_step([venv_python(), "-I", "-c", code] + data["parsers"]["languages"], "download the grammars", env)
    problem = bundle_problem(staging, data) or next(iter(libs_problems(staging, data)), None)
    if problem:
        shutil.rmtree(staging, ignore_errors=True)
        raise ToolError(problem + "; the download was deleted. Nothing was installed.")
    shutil.rmtree(final, ignore_errors=True)
    os.rename(staging, final)


def install():
    data = pins()
    platform_pins(data)
    os.makedirs(cache_root(), exist_ok=True)
    for name in sorted(data["tools"]):
        install_checkout(name, data)
    install_venv(data)
    install_parsers(data)
    return problems()


def probe(command):
    try:
        return subprocess.run(command + ["true"], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def sandbox_prefix():
    """The command prefix that cuts the network, or None when this machine has none."""
    if platform.system() == "Darwin" and shutil.which("sandbox-exec"):
        return ["sandbox-exec", "-p", DARWIN_PROFILE]
    if platform.system() == "Linux":
        candidates = []
        if shutil.which("bwrap"):
            candidates.append(["bwrap", "--dev-bind", "/", "/", "--unshare-net", "--die-with-parent", "--"])
        if shutil.which("unshare"):
            candidates.append(["unshare", "--user", "--map-current-user", "--net", "--"])
        for prefix in candidates:
            if probe(prefix):
                return prefix
    return None


def tool_env(tool_src_dirs):
    env = dict(os.environ)
    env["TREE_SITTER_LANGUAGE_PACK_CACHE_DIR"] = parsers_dir()
    env["KEEL_TOOL_SRC"] = os.pathsep.join(tool_src_dirs)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def tool_command(tool, shim_args, sandbox):
    """Command and environment that run one tool through the shim, checked and isolated."""
    found = problems()
    if found:
        raise ToolError("the clean-code tools are not ready ({}). Run: python3 \"{}\" install".format(
            "; ".join(found), os.path.join(HERE, "clean-code-measure.py")))
    known = pins()["tools"]
    sources = [os.path.join(tool_dir(name), "src") for name in ("crapper", tool) if name in known]
    command = [venv_python(), "-I", SHIM, tool] + list(shim_args)
    return (sandbox or []) + command, tool_env(sorted(set(sources)))


def main(argv):
    try:
        if argv[:1] == ["install"]:
            found = install()
        else:
            found = problems()
    except ToolError as error:
        print("Stopped: {}".format(error))
        return 1
    if found:
        print("Not ready:\n" + "\n".join("- " + problem for problem in found))
        print("Install (uses the network, writes only in {}): python3 \"{}\" install".format(
            cache_root(), os.path.join(HERE, "clean-code-measure.py")))
        return 1
    sandbox = sandbox_prefix()
    print("Ready: crapper, dryer and mutator at their pinned SHAs in {}; grammars verified.".format(cache_root()))
    print("Network isolation: {}.".format(sandbox[0] if sandbox else "NONE on this machine (runs need an explicit "
                                                                     "--no-sandbox)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
