"""clean-code.py: the installer (plan / --apply / --decline) and the SessionStart `--hook`.

Every case runs the script as a subprocess from inside a temp project, with $CLAUDE_CONFIG_DIR on a temp dir so nothing
touches ~/.claude.
"""
import json
import os
import re
import subprocess
import sys
import time

import pytest

from conftest import SCRIPTS

INSTALLER = SCRIPTS / "clean-code.py"
TEMPLATE = SCRIPTS / "size-budget.py"
DECLINED = ".keel-clean-code-declined"
GITIGNORE = ["/.metrics/", "/target/mutation-workers/", "/target/mutator-backup/"]


# ---------------------------------------------------------------- helpers

def lines_file(path, count):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x\n" * count)
    return path


def git_init(path):
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def slug(path):
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


@pytest.fixture
def config_dir(tmp_path):
    d = tmp_path / "claude-config"
    d.mkdir()
    return d


@pytest.fixture
def js(tmp_path):
    """A new JS/TS project: flat eslint config, one 1200-line and one 900-line source file."""
    project = git_init(tmp_path / "proj")
    (project / "package.json").write_text(json.dumps({"name": "x", "devDependencies": {"eslint": "^9"}}))
    (project / "eslint.config.mjs").write_text("export default [];\n")
    lines_file(project / "src" / "big.ts", 1200)
    lines_file(project / "src" / "mid.ts", 900)
    return project


def env_for(config_dir):
    return dict(os.environ, CLAUDE_CONFIG_DIR=str(config_dir))


def cc(config_dir, project, *args):
    return subprocess.run([sys.executable, str(INSTALLER), *args], cwd=str(project), capture_output=True, text=True,
                          env=env_for(config_dir), timeout=60)


def hook(config_dir, cwd, source="startup", raw=None):
    stdin = raw if raw is not None else json.dumps({"cwd": str(cwd), "source": source})
    result = subprocess.run([sys.executable, str(INSTALLER), "--hook"], input=stdin, capture_output=True, text=True,
                            env=env_for(config_dir), timeout=30)
    assert result.returncode == 0 and result.stderr == ""
    return result.stdout


def budget_of(project):
    return json.loads((project / "size-budget.json").read_text())


def applied(config_dir, project):
    result = cc(config_dir, project, "--apply")
    assert result.returncode == 0, result.stderr
    return result.stdout


# ---------------------------------------------------------------- plan (nothing written)

def test_plan_lists_the_steps_and_writes_nothing(js, config_dir):
    before = sorted(p.relative_to(js).as_posix() for p in js.rglob("*") if ".git/" not in p.as_posix())
    result = cc(config_dir, js)
    assert result.returncode == 0
    out = result.stdout
    assert "create size-budget.json (defaultMax 1000, 1 own ceilings)" in out
    assert "create scripts/size-budget.py" in out
    assert "add to .gitignore: /.metrics/ /target/mutation-workers/ /target/mutator-backup/" in out
    assert "Nothing was written" in out
    assert "Stack: JS/TS" in out
    after = sorted(p.relative_to(js).as_posix() for p in js.rglob("*") if ".git/" not in p.as_posix())
    assert after == before
    assert not (js / "size-budget.json").exists()
    assert not (js / "scripts").exists()
    assert not (js / ".gitignore").exists()


def test_plan_outside_a_git_repository_refuses(tmp_path, config_dir):
    plain = tmp_path / "nogit"
    plain.mkdir()
    result = cc(config_dir, plain, "--apply")
    assert result.returncode == 1
    assert "Not inside a git repository" in result.stdout
    assert list(plain.iterdir()) == []


# ---------------------------------------------------------------- --apply

def test_apply_writes_budget_script_and_gitignore(js, config_dir):
    out = applied(config_dir, js)
    budget = budget_of(js)
    assert budget["keel"] == 1
    assert budget["defaultMax"] == 1000
    assert budget["files"] == {"src/big.ts": 1200}   # 900 lines: under the default, no own ceiling
    assert budget["script"] == "scripts/size-budget.py"
    assert ".ts" in budget["extensions"] and ".py" not in budget["extensions"]
    script = js / "scripts" / "size-budget.py"
    assert script.read_bytes() == TEMPLATE.read_bytes()
    assert os.access(script, os.X_OK)
    gitignore = (js / ".gitignore").read_text().splitlines()
    for line in GITIGNORE:
        assert gitignore.count(line) == 1
    assert "Done:" in out


def test_apply_twice_does_not_duplicate_anything(js, config_dir):
    applied(config_dir, js)
    snapshot = {name: (js / name).read_bytes() for name in ("size-budget.json", ".gitignore", "scripts/size-budget.py")}
    out = applied(config_dir, js)
    assert "Nothing to write" in out and "Done:" not in out
    for name, content in snapshot.items():
        assert (js / name).read_bytes() == content
    assert (js / ".gitignore").read_text().count("/.metrics/") == 1


def test_installed_script_runs_clean_right_after_apply(js, config_dir):
    applied(config_dir, js)
    result = subprocess.run([sys.executable, "scripts/size-budget.py"], cwd=str(js), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "No file above its ceiling (1 with their own ceiling, default 1000)" in result.stdout


def test_gitignore_without_trailing_newline_and_with_existing_lines_is_preserved(js, config_dir):
    (js / ".gitignore").write_text("node_modules\n.metrics/")  # `.metrics/` counts as the `/.metrics/` line
    applied(config_dir, js)
    text = (js / ".gitignore").read_text()
    assert text.startswith("node_modules\n.metrics/\n")
    assert text.count(".metrics/") == 1
    assert text.count("/target/mutation-workers/") == 1 and text.count("/target/mutator-backup/") == 1


def test_apply_with_nothing_to_install_does_not_touch_the_files(js, config_dir):
    applied(config_dir, js)
    mtime = (js / "size-budget.json").stat().st_mtime_ns
    applied(config_dir, js)
    assert (js / "size-budget.json").stat().st_mtime_ns == mtime


def test_outdated_script_is_replaced_by_the_template(js, config_dir):
    applied(config_dir, js)
    (js / "scripts" / "size-budget.py").write_text("KEEL_PACKAGE = 1\n# stale\n")
    out = cc(config_dir, js).stdout
    assert "update scripts/size-budget.py" in out
    applied(config_dir, js)
    assert (js / "scripts" / "size-budget.py").read_bytes() == TEMPLATE.read_bytes()


# ---------------------------------------------------------------- rerun: the ratchet

def test_rerun_lowers_a_shrunk_ceiling_keeps_a_grown_one_and_never_adds(js, config_dir):
    applied(config_dir, js)
    big = js / "src" / "big.ts"

    lines_file(big, 1100)
    out = applied(config_dir, js)
    assert budget_of(js)["files"] == {"src/big.ts": 1100}
    assert "ceiling lowered: src/big.ts 1200 -> 1100" in out

    lines_file(big, 1300)
    out = applied(config_dir, js)
    assert budget_of(js)["files"] == {"src/big.ts": 1100}   # never raised
    assert "ABOVE its ceiling, kept at 1100: src/big.ts has 1300 lines" in out

    lines_file(js / "src" / "new.ts", 1500)
    out = applied(config_dir, js)
    assert budget_of(js)["files"] == {"src/big.ts": 1100}   # a new file is not baselined
    assert "ABOVE its ceiling, kept at 1000: src/new.ts has 1500 lines" in out


def test_rerun_drops_the_entry_when_the_file_fits_the_default_or_is_gone(js, config_dir):
    applied(config_dir, js)
    lines_file(js / "src" / "big.ts", 1000)
    out = applied(config_dir, js)
    assert budget_of(js)["files"] == {}
    assert "entry dropped (fits the default now): src/big.ts" in out

    lines_file(js / "src" / "big.ts", 1200)  # grew back after the entry was dropped: now a breach
    out = applied(config_dir, js)
    assert budget_of(js)["files"] == {}
    assert "ABOVE its ceiling" in out


def test_rerun_keeps_a_hand_raised_ceiling_the_user_wrote(js, config_dir):
    applied(config_dir, js)
    data = budget_of(js)
    data["files"]["src/big.ts"] = 1500   # raised by hand, in the diff, on purpose
    (js / "size-budget.json").write_text(json.dumps(data))
    lines_file(js / "src" / "big.ts", 1400)
    applied(config_dir, js)
    assert budget_of(js)["files"] == {"src/big.ts": 1400}


# ---------------------------------------------------------------- adoption of a budget without "keel"

def test_adopts_an_existing_budget_without_keel_and_baselines_what_it_left_out(js, config_dir):
    (js / "size-budget.json").write_text(json.dumps({"files": {"src/big.ts": 1300}}))
    lines_file(js / "src" / "other.ts", 1100)   # above 1000 and outside the old budget
    out = applied(config_dir, js)
    budget = budget_of(js)
    assert budget["keel"] == 1
    assert budget["files"] == {"src/big.ts": 1200, "src/other.ts": 1100}   # big lowered 1300 -> 1200, other adopted
    assert "adopted: src/other.ts (1100 lines)" in out
    assert "ceiling lowered: src/big.ts 1300 -> 1200" in out
    assert budget["defaultMax"] == 1000 and "ignore" in budget and budget["script"] == "scripts/size-budget.py"


def test_adoption_keeps_what_the_old_budget_declared(js, config_dir):
    (js / "size-budget.json").write_text(json.dumps(
        {"defaultMax": 1100, "extensions": [".ts"], "files": {"src/big.ts": 1300}}))
    lines_file(js / "src" / "legacy.js", 5000)   # .js is outside the old budget's extensions
    lines_file(js / "src" / "ok.ts", 1100)        # above 1000 but not above the declared 1100
    applied(config_dir, js)
    budget = budget_of(js)
    assert budget["defaultMax"] == 1100 and budget["extensions"] == [".ts"]
    assert budget["files"] == {"src/big.ts": 1200}


def test_after_adoption_a_new_big_file_is_a_breach_not_adopted(js, config_dir):
    (js / "size-budget.json").write_text(json.dumps({"files": {}}))
    applied(config_dir, js)
    lines_file(js / "src" / "later.ts", 1100)
    out = applied(config_dir, js)
    assert "later.ts" not in budget_of(js)["files"]
    assert "ABOVE its ceiling" in out and "adopted" not in out


# ---------------------------------------------------------------- Python project

def test_python_project_budget_and_output(tmp_path, config_dir):
    project = git_init(tmp_path / "py")
    (project / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    lines_file(project / "app" / "big.py", 1200)
    lines_file(project / "app" / "big.ts", 1500)   # not part of a Python-only budget
    out = applied(config_dir, project)
    budget = budget_of(project)
    assert budget["extensions"] == [".py"]
    assert budget["files"] == {"app/big.py": 1200}
    assert "Stack: Python" in out
    assert "Lint block" not in out
    ci = [line for line in out.splitlines() if line.startswith("CI and pre-commit")]
    assert ci and "scripts/size-budget.py" in ci[0]


def test_js_and_python_project_covers_both(tmp_path, config_dir):
    project = git_init(tmp_path / "mixed")
    (project / "package.json").write_text("{}")
    (project / "setup.py").write_text("")
    lines_file(project / "a.py", 1100)
    lines_file(project / "b.ts", 1100)
    applied(config_dir, project)
    budget = budget_of(project)
    assert ".py" in budget["extensions"] and ".ts" in budget["extensions"]
    assert budget["files"] == {"a.py": 1100, "b.ts": 1100}


def test_vue_and_svelte_add_their_extensions(js, config_dir):
    (js / "package.json").write_text(json.dumps({"dependencies": {"vue": "3", "svelte": "5"}}))
    applied(config_dir, js)
    exts = budget_of(js)["extensions"]
    assert ".vue" in exts and ".svelte" in exts


def test_no_stack_detected_falls_back_to_default_extensions(tmp_path, config_dir):
    project = git_init(tmp_path / "bare")
    out = applied(config_dir, project)
    assert "not detected (default extensions)" in out
    assert ".ts" in budget_of(project)["extensions"] and ".py" in budget_of(project)["extensions"]


# ---------------------------------------------------------------- lint proposal

def test_flat_config_with_sonarjs_installed_proposes_cognitive_complexity(js, config_dir):
    (js / "node_modules" / "eslint-plugin-sonarjs").mkdir(parents=True)
    out = cc(config_dir, js).stdout
    assert "Lint block for eslint.config.mjs (flat):" in out
    assert "'sonarjs/cognitive-complexity': ['warn', 15]" in out
    assert "import sonarjs from 'eslint-plugin-sonarjs';" in out
    assert "plugins: { sonarjs }" in out
    assert "is not installed" not in out
    assert "'max-lines': sizeRule(sizeBudget.defaultMax)" in out


def test_flat_config_without_sonarjs_leaves_it_out_and_says_so(js, config_dir):
    out = cc(config_dir, js).stdout
    assert "Lint block for eslint.config.mjs (flat):" in out
    assert "sonarjs/cognitive-complexity" not in out
    assert "import sonarjs" not in out
    assert "eslint-plugin-sonarjs is not installed" in out
    assert "'max-lines'" in out and "'max-lines-per-function'" in out


def test_flat_block_lists_the_budget_js_extensions_only(js, config_dir):
    out = cc(config_dir, js).stdout
    assert "files: ['**/*{.ts,.tsx,.mts,.cts,.js,.jsx,.mjs,.cjs}']" in out


def test_legacy_eslintrc_json_gets_the_legacy_block_with_overrides(js, config_dir):
    (js / "eslint.config.mjs").unlink()
    (js / ".eslintrc.json").write_text("{}")
    out = cc(config_dir, js).stdout
    assert "Lint block for .eslintrc.json (legacy):" in out
    assert "overrides: Object.entries(sizeBudget.files)" in out
    assert "module.exports" in out and "ignorePatterns: sizeBudget.ignore" in out
    assert "files: ['**/*{" not in out   # not the flat block


def test_legacy_block_with_sonarjs_indents_the_rule_inside_rules(js, config_dir):
    (js / "eslint.config.mjs").unlink()
    (js / ".eslintrc.json").write_text("{}")
    (js / "node_modules" / "eslint-plugin-sonarjs").mkdir(parents=True)
    out = cc(config_dir, js).stdout
    assert "  plugins: ['sonarjs']," in out
    assert "\n    'sonarjs/cognitive-complexity': ['warn', 15],\n  }," in out


def test_eslint_config_in_package_json_is_legacy(js, config_dir):
    (js / "eslint.config.mjs").unlink()
    (js / "package.json").write_text(json.dumps({"eslintConfig": {"root": True}}))
    assert "Lint block for package.json#eslintConfig (legacy):" in cc(config_dir, js).stdout


def test_no_eslint_means_no_lint_block(js, config_dir):
    (js / "eslint.config.mjs").unlink()
    assert "Lint block" not in cc(config_dir, js).stdout


def test_the_installer_never_edits_a_lint_config(js, config_dir):
    original = (js / "eslint.config.mjs").read_text()
    applied(config_dir, js)
    assert (js / "eslint.config.mjs").read_text() == original


def test_flat_block_with_a_single_extension_is_not_a_one_element_brace_set(js, config_dir):
    (js / "size-budget.json").write_text(json.dumps({"extensions": [".ts"], "files": {}}))
    out = cc(config_dir, js).stdout
    assert "**/*{.ts}" not in out
    assert "files: ['**/*.ts']" in out


# ---------------------------------------------------------------- --decline

def test_decline_writes_the_marker_outside_the_repo(js, config_dir):
    result = cc(config_dir, js, "--decline")
    assert result.returncode == 0
    marker = config_dir / "projects" / slug(js) / DECLINED
    assert marker.is_file()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}\n", marker.read_text())
    assert not (js / "size-budget.json").exists()
    assert not (js / DECLINED).exists()


def test_decline_silences_the_hook_for_that_project_only(js, tmp_path, config_dir):
    other = git_init(tmp_path / "other")
    (other / "package.json").write_text("{}")
    assert "/keel:clean-code" in hook(config_dir, js)
    cc(config_dir, js, "--decline")
    assert hook(config_dir, js) == ""
    assert "/keel:clean-code" in hook(config_dir, other)


def test_decline_from_a_subdirectory_targets_the_repo_root(js, config_dir):
    cc(config_dir, js / "src", "--decline")
    assert (config_dir / "projects" / slug(js) / DECLINED).is_file()


def test_decline_of_the_main_checkout_silences_its_worktree(tmp_path, config_dir):
    main = git_init(tmp_path / "main")
    (main / ".git" / "worktrees" / "w").mkdir(parents=True)
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text("gitdir: {}/.git/worktrees/w\n".format(main))
    (wt / "package.json").write_text("{}")
    assert "/keel:clean-code" in hook(config_dir, wt)
    cc(config_dir, main, "--decline")
    assert hook(config_dir, wt) == ""


# ---------------------------------------------------------------- --hook (SessionStart)

def test_hook_suggests_on_startup_for_a_code_project_without_budget(js, config_dir):
    out = hook(config_dir, js, "startup")
    assert out.startswith("PLUGIN NOTICE (clean-code):")
    assert "/keel:clean-code" in out and "no size budget" in out


def test_hook_suggests_on_clear_and_from_a_subdirectory(js, config_dir):
    assert "/keel:clean-code" in hook(config_dir, js, "clear")
    assert "/keel:clean-code" in hook(config_dir, js / "src", "startup")


@pytest.mark.parametrize("source", ["resume", "compact", "other"])
def test_hook_is_silent_for_resume_and_compact(js, config_dir, source):
    assert hook(config_dir, js, source) == ""


def test_hook_defaults_the_source_to_startup(js, config_dir):
    assert "/keel:clean-code" in hook(config_dir, js, raw=json.dumps({"cwd": str(js)}))


def test_hook_is_silent_for_a_repo_that_is_not_a_code_project(tmp_path, config_dir):
    docs = git_init(tmp_path / "docs")
    (docs / "README.md").write_text("hi\n")
    assert hook(config_dir, docs) == ""


def test_hook_suggests_for_a_python_project(tmp_path, config_dir):
    project = git_init(tmp_path / "py")
    (project / "requirements.txt").write_text("")
    assert "/keel:clean-code" in hook(config_dir, project)


def test_hook_is_silent_outside_a_git_repository(tmp_path, config_dir):
    plain = tmp_path / "nogit"
    plain.mkdir()
    (plain / "package.json").write_text("{}")
    assert hook(config_dir, plain) == ""


def test_hook_is_silent_when_the_package_is_current(js, config_dir):
    applied(config_dir, js)
    assert hook(config_dir, js) == ""


def test_hook_is_silent_for_a_current_package_whose_script_text_differs(js, config_dir):
    applied(config_dir, js)
    script = js / "scripts" / "size-budget.py"
    script.write_text(script.read_text() + "\n# local note\n")
    assert hook(config_dir, js) == ""


@pytest.mark.parametrize("how", ["keel 0", "no keel key", "script missing", "script KEEL_PACKAGE 0",
                                 "script without KEEL_PACKAGE"])
def test_hook_says_behind_when_budget_or_script_is_old(js, config_dir, how):
    applied(config_dir, js)
    script = js / "scripts" / "size-budget.py"
    data = budget_of(js)
    if how == "keel 0":
        data["keel"] = 0
        (js / "size-budget.json").write_text(json.dumps(data))
    elif how == "no keel key":
        del data["keel"]
        (js / "size-budget.json").write_text(json.dumps(data))
    elif how == "script missing":
        script.unlink()
    elif how == "script KEEL_PACKAGE 0":
        script.write_text(script.read_text().replace("KEEL_PACKAGE = 1", "KEEL_PACKAGE = 0", 1))
    else:
        script.write_text("print('old')\n")
    out = hook(config_dir, js)
    assert "behind the plugin's" in out and "/keel:clean-code" in out


def test_hook_behind_is_not_silenced_by_decline(js, config_dir):
    # decline only covers "no budget"; a project that has a budget but a stale one still hears about it
    applied(config_dir, js)
    data = budget_of(js)
    data["keel"] = 0
    (js / "size-budget.json").write_text(json.dumps(data))
    cc(config_dir, js, "--decline")
    assert "behind" in hook(config_dir, js)


def test_hook_honours_a_custom_script_path_from_the_budget(js, config_dir):
    applied(config_dir, js)
    data = budget_of(js)
    data["script"] = "tools/budget.py"
    (js / "size-budget.json").write_text(json.dumps(data))
    assert "behind" in hook(config_dir, js)   # nothing at tools/budget.py
    (js / "tools").mkdir()
    (js / "tools" / "budget.py").write_bytes(TEMPLATE.read_bytes())
    assert hook(config_dir, js) == ""


@pytest.mark.parametrize("raw", ["not json", "", "[]", "null", '{"cwd": 5}'])
def test_hook_swallows_garbage_stdin(config_dir, raw):
    result = subprocess.run([sys.executable, str(INSTALLER), "--hook"], input=raw, capture_output=True, text=True,
                            env=env_for(config_dir), timeout=30)
    assert result.returncode == 0 and result.stdout == "" and result.stderr == ""


def test_hook_is_fast(js, config_dir):
    times = []
    for _ in range(5):
        start = time.perf_counter()
        out = hook(config_dir, js)
        times.append(time.perf_counter() - start)
        assert "/keel:clean-code" in out
    print("clean-code.py --hook runs (s):", ["{:.3f}".format(t) for t in times])
    assert min(times) < 0.1, times


def test_lint_block_matches_budget_paths_literally_so_next_route_brackets_work(js, config_dir):
    out = cc(config_dir, js).stdout
    assert "const literalPath = (file) => file.replace(/[[\\]{}()*?!+@]/g, '\\\\$&');" in out
    assert "files: [literalPath(file)]" in out
    assert "files: [file]" not in out
