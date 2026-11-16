"""size-budget.py (ratchet library + the script installed in projects) and clean-code-size.py (PostToolUse hook).

The hook runs as a subprocess with the stdin JSON Claude Code sends; $CLAUDE_CONFIG_DIR always points to a temp dir so
nothing touches ~/.claude.
"""
import json
import os
import re
import subprocess
import sys
import time

import pytest

from conftest import SCRIPTS, load_script

size_budget = load_script("size-budget.py")
HOOK = SCRIPTS / "clean-code-size.py"
DECLINED = ".keel-clean-code-declined"


# ---------------------------------------------------------------- helpers

def lines_file(path, count, ending=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join("x" for _ in range(count))
    path.write_text(body + ("\n" if ending and count else ""))
    return path


def git_init(path):
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def write_budget(root, files=None, **extra):
    root.mkdir(parents=True, exist_ok=True)
    data = {"keel": 1, "defaultMax": 1000, "files": files or {}}
    data.update(extra)
    (root / "size-budget.json").write_text(json.dumps(data))


def slug(path):
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


@pytest.fixture
def config_dir(tmp_path):
    d = tmp_path / "claude-config"
    d.mkdir()
    return d


def decline(config_dir, root):
    marker = config_dir / "projects" / slug(root) / DECLINED
    marker.parent.mkdir(parents=True)
    marker.write_text("2026-01-01\n")


def run_hook(config_dir, payload, cwd=None, raw=None):
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(config_dir))
    stdin = raw if raw is not None else json.dumps(payload)
    return subprocess.run([sys.executable, str(HOOK)], input=stdin, capture_output=True, text=True, env=env,
                          cwd=str(cwd) if cwd else None, timeout=30)


def warning(config_dir, file_path, cwd=None):
    """The additionalContext the hook printed, or None when it stayed silent (also asserts the contract)."""
    result = run_hook(config_dir, {"cwd": str(cwd or file_path.parent), "tool_input": {"file_path": str(file_path)}})
    assert result.returncode == 0
    assert result.stderr == ""
    if not result.stdout:
        return None
    out = json.loads(result.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PostToolUse"
    return out["additionalContext"]


# ---------------------------------------------------------------- size-budget.py

@pytest.mark.parametrize("content, expected", [(b"a\nb\n", 2), (b"a\nb", 2), (b"", 0), (b"\n", 1), (b"a\n\n", 2)])
def test_count_lines(tmp_path, content, expected):
    f = tmp_path / "f.txt"
    f.write_bytes(content)
    assert size_budget.count_lines(str(f)) == expected


@pytest.mark.parametrize("pattern, path, expected", [
    ("**/node_modules/**", "node_modules/x.js", True),
    ("**/node_modules/**", "a/node_modules/x.js", True),
    ("**/node_modules/**", "a/b/node_modules/c/d/x.js", True),
    ("**/node_modules/**", "a/mynode_modules/x.js", False),
    ("*.ts", "b.ts", True),
    ("*.ts", "a/b.ts", False),
    ("**/migrations/**/*.sql", "db/migrations/001/x.sql", True),
    ("**/migrations/**/*.sql", "migrations/x.sql", True),
    ("**/migrations/**/*.sql", "db/migrations/001/x.ts", False),
    ("**/*.spec.*", "src/a/x.spec.ts", True),
    ("**/*.spec.*", "x.spec.ts", True),
    ("a?c", "abc", True),
    ("a?c", "a/c", False),
    ("a.b", "axb", False),
])
def test_glob_regex(pattern, path, expected):
    assert bool(size_budget.glob_regex(pattern).match(path)) is expected


def test_ratchet_lowers_removes_and_never_raises():
    budget = {"defaultMax": 1000, "files": {
        "shrank.ts": 1500,    # 1200 now: lowered
        "same.ts": 1300,      # 1300 now: untouched
        "fits.ts": 1500,      # 900 now: dropped
        "atdefault.ts": 1500,  # 1000 now: dropped (fits the default)
        "gone.ts": 1500,      # deleted: dropped
        "grew.ts": 1200,      # 1300 now: breach, kept at 1200
    }}
    counts = {"shrank.ts": 1200, "same.ts": 1300, "fits.ts": 900, "atdefault.ts": 1000, "grew.ts": 1300,
              "newbig.ts": 1100, "small.ts": 10}
    files, breaches, lowered, removed = size_budget.ratchet(budget, counts)
    assert files == {"shrank.ts": 1200, "same.ts": 1300, "grew.ts": 1200}
    assert lowered == [("shrank.ts", 1500, 1200)]
    assert sorted(removed, key=lambda r: r[0]) == [
        ("atdefault.ts", 1500, 1000), ("fits.ts", 1500, 900), ("gone.ts", 1500, None)]
    assert sorted(breaches) == [("grew.ts", 1300, 1200), ("newbig.ts", 1100, 1000)]
    assert "newbig.ts" not in files  # a file above the default outside the budget is a breach, never a new entry


def test_ratchet_with_clean_tree_changes_nothing():
    budget = {"defaultMax": 1000, "files": {"a.ts": 1200}}
    files, breaches, lowered, removed = size_budget.ratchet(budget, {"a.ts": 1200, "b.ts": 5})
    assert (files, breaches, lowered, removed) == ({"a.ts": 1200}, [], [], [])


def test_rules_budget_with_only_default_and_files_gets_default_extensions_and_ignore():
    rules = size_budget.Rules({"defaultMax": 500, "files": {"a.ts": 700}})
    assert rules.covers("a.ts")
    assert rules.covers("src/deep/b.py")
    assert not rules.covers("a.spec.ts")
    assert not rules.covers("src/a.test.ts")
    assert not rules.covers("README.md")
    assert not rules.covers("node_modules/x/index.js")
    assert not rules.covers("src/generated/x.ts")
    assert rules.ceiling("a.ts") == 700
    assert rules.ceiling("b.ts") == 500


def test_rules_declared_extensions_and_ignore_win_over_defaults():
    rules = size_budget.Rules({"extensions": [".py"], "ignore": ["legacy/**"]})
    assert rules.covers("a.py")
    assert not rules.covers("a.ts")
    assert not rules.covers("legacy/a.py")
    assert rules.covers("src/a.spec.py") is True  # the declared ignore replaces the default list
    assert rules.default_max == 1000


def test_rules_empty_budget_is_all_defaults():
    rules = size_budget.Rules({})
    assert rules.default_max == 1000 and rules.files == {}
    assert rules.covers("a.ts") and not rules.covers("a.spec.ts")


def test_main_init_writes_baseline_only_for_files_above_default(tmp_path, monkeypatch, capsys):
    project = git_init(tmp_path / "p")
    lines_file(project / "src" / "big.ts", 1001)
    lines_file(project / "src" / "exact.ts", 1000)
    lines_file(project / "src" / "big.spec.ts", 3000)      # ignored: test
    lines_file(project / "src" / "doc.md", 3000)           # other extension
    lines_file(project / "node_modules" / "p" / "i.js", 3000)
    monkeypatch.chdir(project)
    assert size_budget.main(["--init"]) == 0
    data = json.loads((project / "size-budget.json").read_text())
    assert data["files"] == {"src/big.ts": 1001}
    assert data["keel"] == 1 and data["defaultMax"] == 1000
    assert "1 files above 1000" in capsys.readouterr().out


def test_main_init_skips_gitignored_files(tmp_path, monkeypatch):
    project = git_init(tmp_path / "p")
    (project / ".gitignore").write_text("secret/\n")
    lines_file(project / "secret" / "big.ts", 2000)
    lines_file(project / "src" / "big.ts", 1500)
    monkeypatch.chdir(project)
    assert size_budget.main(["--init"]) == 0
    assert json.loads((project / "size-budget.json").read_text())["files"] == {"src/big.ts": 1500}


def test_main_init_refuses_when_budget_exists(tmp_path, monkeypatch, capsys):
    project = git_init(tmp_path / "p")
    lines_file(project / "big.ts", 1500)
    original = json.dumps({"keel": 1, "files": {}})
    (project / "size-budget.json").write_text(original)
    monkeypatch.chdir(project)
    assert size_budget.main(["--init"]) == 1
    assert (project / "size-budget.json").read_text() == original
    assert "already exists" in capsys.readouterr().out


def test_main_without_budget_exits_1(tmp_path, monkeypatch, capsys):
    project = git_init(tmp_path / "p")
    monkeypatch.chdir(project)
    assert size_budget.main([]) == 1
    assert "--init" in capsys.readouterr().out


def test_report_exits_1_on_breach_and_0_when_clean(tmp_path, monkeypatch, capsys):
    project = git_init(tmp_path / "p")
    big = lines_file(project / "big.ts", 1200)
    monkeypatch.chdir(project)
    assert size_budget.main(["--init"]) == 0
    capsys.readouterr()
    assert size_budget.main([]) == 0
    assert "No file above its ceiling" in capsys.readouterr().out
    lines_file(big, 1201)
    assert size_budget.main([]) == 1
    assert "ABOVE their ceiling (1)" in capsys.readouterr().err
    lines_file(big, 1200)
    lines_file(project / "other.ts", 1001)  # above the default, outside the budget
    assert size_budget.main([]) == 1
    assert "other.ts  1001 -> 1000" in capsys.readouterr().err


def test_report_without_update_writes_nothing(tmp_path, monkeypatch):
    project = git_init(tmp_path / "p")
    big = lines_file(project / "big.ts", 1200)
    monkeypatch.chdir(project)
    size_budget.main(["--init"])
    before = (project / "size-budget.json").read_text()
    lines_file(big, 1100)
    assert size_budget.main([]) == 0
    assert (project / "size-budget.json").read_text() == before


def test_update_writes_lowered_ceilings_and_drops_obsolete(tmp_path, monkeypatch, capsys):
    project = git_init(tmp_path / "p")
    a = lines_file(project / "a.ts", 1200)
    b = lines_file(project / "b.ts", 1300)
    monkeypatch.chdir(project)
    size_budget.main(["--init"])
    capsys.readouterr()
    lines_file(a, 1100)
    lines_file(b, 900)
    assert size_budget.main(["--update"]) == 0
    assert json.loads((project / "size-budget.json").read_text())["files"] == {"a.ts": 1100}
    out = capsys.readouterr().out
    assert "Lowered (1)" in out and "Removed (1)" in out


def test_update_never_raises_a_ceiling_and_still_fails(tmp_path, monkeypatch):
    project = git_init(tmp_path / "p")
    a = lines_file(project / "a.ts", 1200)
    monkeypatch.chdir(project)
    size_budget.main(["--init"])
    lines_file(a, 1400)
    lines_file(project / "new.ts", 1100)
    assert size_budget.main(["--update"]) == 1
    assert json.loads((project / "size-budget.json").read_text())["files"] == {"a.ts": 1200}


def test_measure_without_git_walks_and_skips_dependency_dirs(tmp_path, monkeypatch):
    project = tmp_path / "plain"
    project.mkdir()
    write_budget(project)
    lines_file(project / "src" / "a.ts", 1200)
    lines_file(project / "node_modules" / "x" / "i.js", 5000)
    lines_file(project / ".git_not" / "b.ts", 1100)
    monkeypatch.chdir(project)
    counts = size_budget.measure(str(project), size_budget.Rules({}))
    assert counts == {"src/a.ts": 1200, ".git_not/b.ts": 1100}


# ---------------------------------------------------------------- clean-code-size.py

def test_own_ceiling_above_warns_naming_the_own_ceiling(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    write_budget(project, {"src/big.ts": 1200})
    text = warning(config_dir, lines_file(project / "src" / "big.ts", 1201))
    assert "own ceiling" in text and "src/big.ts" in text and "1201" in text and "1200" in text
    assert "close to" not in text


@pytest.mark.parametrize("count", [1200, 1100, 1])
def test_own_ceiling_at_or_below_is_silent(tmp_path, config_dir, count):
    project = git_init(tmp_path / "p")
    write_budget(project, {"src/big.ts": 1200})
    assert warning(config_dir, lines_file(project / "src" / "big.ts", count)) is None


def test_own_ceiling_does_not_borrow_the_default(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    write_budget(project, {"src/big.ts": 1200})
    other = warning(config_dir, lines_file(project / "src" / "other.ts", 1001))
    assert "the ceiling for a file" in other and "own ceiling" not in other


def test_default_ceiling_above_warns(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    write_budget(project)
    text = warning(config_dir, lines_file(project / "a.ts", 1001))
    assert "1001 lines" in text and "the ceiling for a file of 1000" in text
    assert "close to" not in text


@pytest.mark.parametrize("count", [900, 950, 1000])
def test_default_ceiling_near_warns_close_to(tmp_path, config_dir, count):
    project = git_init(tmp_path / "p")
    write_budget(project)
    text = warning(config_dir, lines_file(project / "a.ts", count))
    assert "close to its ceiling of 1000" in text and "{} lines".format(count) in text


@pytest.mark.parametrize("count", [899, 500, 1])
def test_default_ceiling_far_is_silent(tmp_path, config_dir, count):
    project = git_init(tmp_path / "p")
    write_budget(project)
    assert warning(config_dir, lines_file(project / "a.ts", count)) is None


def test_budget_default_max_is_read_from_the_budget(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    write_budget(project, defaultMax=200)
    assert "the ceiling for a file of 200" in warning(config_dir, lines_file(project / "a.ts", 201))


@pytest.mark.parametrize("relative", [
    "src/x.spec.ts", "src/x.test.tsx", "generated/x.ts", "src/generated/x.ts", "README.md",
    "migrations/001/x.sql", "db/migrations/001/x.sql", "node_modules/p/index.js", "dist/main.js",
    "tests/helpers.ts", "src/types.d.ts", "deps.lock.js",
])
def test_ignored_files_are_silent(tmp_path, config_dir, relative):
    project = git_init(tmp_path / "p")
    assert warning(config_dir, lines_file(project / relative, 3000)) is None


def test_ignored_files_are_silent_with_a_budget_too(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    write_budget(project)
    assert warning(config_dir, lines_file(project / "src" / "x.spec.ts", 3000)) is None


def test_budget_declared_extensions_and_ignore_apply_to_the_hook(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    write_budget(project, extensions=[".py"], ignore=["legacy/**"])
    assert warning(config_dir, lines_file(project / "a.ts", 3000)) is None
    assert warning(config_dir, lines_file(project / "legacy" / "a.py", 3000)) is None
    assert warning(config_dir, lines_file(project / "a.py", 3000)) is not None


def test_no_budget_with_git_dir_uses_the_1000_default(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    assert "the ceiling for a file of 1000" in warning(config_dir, lines_file(project / "a.ts", 1001))
    assert warning(config_dir, lines_file(project / "b.ts", 500)) is None


def test_no_budget_declined_is_silent(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    big = lines_file(project / "a.ts", 1500)
    assert warning(config_dir, big) is not None  # control: it warns until declined
    decline(config_dir, project)
    assert warning(config_dir, big) is None


def test_decline_of_another_project_does_not_silence(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    other = git_init(tmp_path / "q")
    decline(config_dir, other)
    assert warning(config_dir, lines_file(project / "a.ts", 1500)) is not None


def test_no_budget_and_no_git_is_silent(tmp_path, config_dir):
    plain = tmp_path / "nogit"
    assert warning(config_dir, lines_file(plain / "a.ts", 3000)) is None


def test_budget_without_git_still_applies(tmp_path, config_dir):
    plain = tmp_path / "nogit"
    plain.mkdir()
    write_budget(plain)
    assert warning(config_dir, lines_file(plain / "a.ts", 1500)) is not None


def test_budget_present_overrides_decline(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    decline(config_dir, project)
    big = lines_file(project / "a.ts", 1500)
    assert warning(config_dir, big) is None
    write_budget(project)
    assert warning(config_dir, big) is not None


def test_nearest_budget_wins_in_a_nested_package(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    write_budget(project, defaultMax=1000)
    write_budget(project / "pkg", defaultMax=100)
    assert "the ceiling for a file of 100" in warning(config_dir, lines_file(project / "pkg" / "a.ts", 101))
    assert warning(config_dir, lines_file(project / "other" / "a.ts", 101)) is None


def test_own_entries_are_relative_to_the_budget_root(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    write_budget(project, {"src/big.ts": 1200})
    assert warning(config_dir, lines_file(project / "src" / "deep" / "src" / "big.ts", 1100)) is not None  # not an entry


def make_worktree(tmp_path):
    main = git_init(tmp_path / "main")
    (main / ".git" / "worktrees" / "w").mkdir(parents=True)
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text("gitdir: {}/.git/worktrees/w\n".format(main))
    return main, wt


def test_worktree_inherits_the_decline_of_the_main_checkout(tmp_path, config_dir):
    main, wt = make_worktree(tmp_path)
    big = lines_file(wt / "a.ts", 1500)
    assert warning(config_dir, big) is not None  # control: nothing declined yet
    decline(config_dir, main)
    assert warning(config_dir, big) is None


def test_worktree_decline_keyed_by_its_own_path_does_not_count(tmp_path, config_dir):
    main, wt = make_worktree(tmp_path)
    decline(config_dir, wt)
    assert warning(config_dir, lines_file(wt / "a.ts", 1500)) is not None


def test_worktree_git_file_that_is_not_a_worktree_pointer_falls_back_to_itself(tmp_path, config_dir):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / ".git").write_text("gitdir: /somewhere/else/.git/modules/sub\n")  # a submodule, not a worktree
    big = lines_file(sub / "a.ts", 1500)
    decline(config_dir, sub)
    assert warning(config_dir, big) is None


def test_relative_file_path_resolves_against_the_payload_cwd(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    lines_file(project / "src" / "a.ts", 1500)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    result = run_hook(config_dir, {"cwd": str(project / "src"), "tool_input": {"file_path": "a.ts"}}, cwd=elsewhere)
    assert result.returncode == 0
    ctx = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "src/a.ts has 1500 lines" in ctx


@pytest.mark.parametrize("raw", ["not json", "", "[1, 2]", "null", '{"tool_input": null}', '{"tool_input": {}}'])
def test_garbage_stdin_is_silent_and_exit_0(tmp_path, config_dir, raw):
    result = run_hook(config_dir, None, raw=raw)
    assert result.returncode == 0 and result.stdout == "" and result.stderr == ""


def test_missing_file_is_silent(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    result = run_hook(config_dir, {"cwd": str(project), "tool_input": {"file_path": "gone.ts"}})
    assert result.returncode == 0 and result.stdout == ""


def test_corrupt_budget_json_is_silent_not_a_crash(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    (project / "size-budget.json").write_text("{ not json")
    big = lines_file(project / "a.ts", 1500)
    result = run_hook(config_dir, {"cwd": str(project), "tool_input": {"file_path": str(big)}})
    assert result.returncode == 0 and result.stderr == ""


def test_hook_is_fast_with_a_3000_line_file_and_no_budget(tmp_path, config_dir):
    project = git_init(tmp_path / "p")
    big = lines_file(project / "big.ts", 3000)
    payload = {"cwd": str(project), "tool_input": {"file_path": str(big)}}
    times = []
    for _ in range(5):
        start = time.perf_counter()
        result = run_hook(config_dir, payload)
        times.append(time.perf_counter() - start)
        assert "above" in json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    print("clean-code-size.py runs (s):", ["{:.3f}".format(t) for t in times])
    assert min(times) < 0.1, times
