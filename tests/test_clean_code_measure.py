"""clean-code-runners.py and clean-code-measure.py (tools in test_clean_code_tools.py): no real tool, no network, no ~/.cache/keel.

Every test runs with KEEL_TOOLS_HOME in tmp_path (autouse); git runs only in throwaway repos under tmp_path.
"""
import hashlib
import json
import os
import shlex
import subprocess
from types import SimpleNamespace

import pytest

from conftest import load_script

runners = load_script("clean-code-runners.py")
measure = load_script("clean-code-measure.py")
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


# ---------------------------------------------------------------- runners: find_test

def test_find_test_ts_spec_beside_source(tmp_path):
    touch(tmp_path / "src/x.ts")
    spec = touch(tmp_path / "src/x.spec.ts")
    assert runners.find_test(str(tmp_path / "src/x.ts"), str(tmp_path)) == str(spec)


def test_find_test_tsx_test_beside_source(tmp_path):
    touch(tmp_path / "src/x.tsx")
    test = touch(tmp_path / "src/x.test.tsx")
    assert runners.find_test(str(tmp_path / "src/x.tsx"), str(tmp_path)) == str(test)


def test_find_test_dunder_tests_folder(tmp_path):
    touch(tmp_path / "src/x.ts")
    spec = touch(tmp_path / "src/__tests__/x.spec.ts")
    assert runners.find_test(str(tmp_path / "src/x.ts"), str(tmp_path)) == str(spec)


def test_find_test_spec_wins_over_test_and_beside_wins_over_dunder_tests(tmp_path):
    touch(tmp_path / "src/__tests__/x.spec.ts")
    touch(tmp_path / "src/x.test.ts")
    beside = touch(tmp_path / "src/x.spec.ts")
    assert runners.find_test(str(tmp_path / "src/x.ts"), str(tmp_path)) == str(beside)


def test_find_test_python_beside_prefix_then_suffix(tmp_path):
    touch(tmp_path / "pkg/x.py")
    suffix = touch(tmp_path / "pkg/x_test.py")
    assert runners.find_test(str(tmp_path / "pkg/x.py"), str(tmp_path)) == str(suffix)
    prefix = touch(tmp_path / "pkg/test_x.py")
    assert runners.find_test(str(tmp_path / "pkg/x.py"), str(tmp_path)) == str(prefix)


def test_find_test_python_tests_folder_found_walking_up_to_root(tmp_path):
    touch(tmp_path / "pkg/sub/x.py")
    found = touch(tmp_path / "tests/test_x.py")
    assert runners.find_test(str(tmp_path / "pkg/sub/x.py"), str(tmp_path)) == str(found)


def test_find_test_does_not_walk_above_root(tmp_path):
    touch(tmp_path / "tests/test_x.py")
    root = tmp_path / "proj"
    touch(root / "pkg/x.py")
    assert runners.find_test(str(root / "pkg/x.py"), str(root)) is None


def test_find_test_none_when_no_test_or_unknown_extension(tmp_path):
    touch(tmp_path / "src/x.ts")
    touch(tmp_path / "src/other.spec.ts")
    touch(tmp_path / "docs/readme.md")
    touch(tmp_path / "docs/readme.spec.ts")
    assert runners.find_test(str(tmp_path / "src/x.ts"), str(tmp_path)) is None
    assert runners.find_test(str(tmp_path / "docs/readme.md"), str(tmp_path)) is None


# ---------------------------------------------------------------- runners: jest

def jest_project(tmp_path, config="jest.config.cts"):
    """root/node_modules/.bin/jest, root/packages/a/<config>, root/packages/a/src/x.spec.ts."""
    touch(tmp_path / "node_modules/.bin/jest", "#!/bin/sh\n", 0o755)
    if config:
        touch(tmp_path / "packages/a" / config, "module.exports = {}\n")
    return touch(tmp_path / "packages/a/src/x.spec.ts")


def test_jest_plan_coverage_command_and_mutant_command(tmp_path):
    test = jest_project(tmp_path)
    out = str(tmp_path / ".metrics/keel/coverage/abc")
    plan = runners.plan_for(str(test), str(tmp_path), out)
    assert plan.runner == "jest"
    assert plan.coverage_commands == [[
        "node_modules/.bin/jest", "-c", "packages/a/jest.config.cts", "packages/a/src/x.spec.ts",
        "--ci", "--silent", "--runInBand", "--coverage", "--coverageReporters=lcov", "--coverageDirectory=" + out]]
    assert isinstance(plan.mutant_command, str)
    mutant = shlex.split(plan.mutant_command)
    assert mutant == ["node_modules/.bin/jest", "-c", "packages/a/jest.config.cts", "packages/a/src/x.spec.ts",
                      "--ci", "--silent", "--runInBand"]
    assert not any("coverage" in part for part in mutant)


def test_jest_plan_mutant_command_survives_paths_with_spaces(tmp_path):
    touch(tmp_path / "node_modules/.bin/jest", "#!/bin/sh\n", 0o755)
    test = touch(tmp_path / "my pkg/src/x.spec.ts")
    plan = runners.plan_for(str(test), str(tmp_path), str(tmp_path / "out"))
    assert "'my pkg/src/x.spec.ts'" in plan.mutant_command
    assert "my pkg/src/x.spec.ts" in shlex.split(plan.mutant_command)


def test_jest_plan_without_config_has_no_dash_c(tmp_path):
    test = jest_project(tmp_path, config=None)
    command = runners.plan_for(str(test), str(tmp_path), "out").coverage_commands[0]
    assert "-c" not in command
    assert command[:2] == ["node_modules/.bin/jest", "packages/a/src/x.spec.ts"]


def test_jest_plan_without_binary_is_runner_error(tmp_path):
    touch(tmp_path / "packages/a/jest.config.cts")
    test = touch(tmp_path / "packages/a/src/x.spec.ts")
    with pytest.raises(runners.RunnerError, match="jest is not installed"):
        runners.plan_for(str(test), str(tmp_path), "out")


# ---------------------------------------------------------------- runners: vitest

def vitest_project(tmp_path, config="vitest.config.ts"):
    touch(tmp_path / "node_modules/.bin/vitest", "#!/bin/sh\n", 0o755)
    touch(tmp_path / "pkg" / config, "export default {}\n")
    return touch(tmp_path / "pkg/src/x.test.ts")


def test_vitest_without_coverage_provider_says_so_and_that_keel_never_installs(tmp_path):
    test = vitest_project(tmp_path)
    with pytest.raises(runners.RunnerError) as error:
        runners.plan_for(str(test), str(tmp_path), "out")
    message = str(error.value)
    assert "@vitest/coverage-v8" in message
    assert "keel never installs it" in message


@pytest.mark.parametrize("provider", ["@vitest/coverage-v8", "@vitest/coverage-istanbul"])
def test_vitest_with_provider_gives_lcov_plan(tmp_path, provider):
    test = vitest_project(tmp_path)
    (tmp_path / "node_modules" / provider).mkdir(parents=True)
    out = str(tmp_path / "out")
    plan = runners.plan_for(str(test), str(tmp_path), out)
    assert plan.runner == "vitest"
    assert plan.coverage_commands == [[
        "node_modules/.bin/vitest", "run", "--config", "pkg/vitest.config.ts", "pkg/src/x.test.ts",
        "--no-file-parallelism", "--coverage.enabled=true", "--coverage.reporter=lcov",
        "--coverage.reportsDirectory=" + out]]
    assert shlex.split(plan.mutant_command) == [
        "node_modules/.bin/vitest", "run", "--config", "pkg/vitest.config.ts", "pkg/src/x.test.ts",
        "--no-file-parallelism"]


def test_vitest_config_without_binary_is_runner_error(tmp_path):
    test = touch(tmp_path / "pkg/src/x.test.ts")
    touch(tmp_path / "pkg/vitest.config.ts")
    with pytest.raises(runners.RunnerError, match="vitest is not installed"):
        runners.plan_for(str(test), str(tmp_path), "out")


def test_jest_wins_when_both_configs_exist(tmp_path):
    touch(tmp_path / "node_modules/.bin/jest", "#!/bin/sh\n", 0o755)
    touch(tmp_path / "node_modules/.bin/vitest", "#!/bin/sh\n", 0o755)
    (tmp_path / "node_modules/@vitest/coverage-v8").mkdir(parents=True)
    touch(tmp_path / "pkg/vitest.config.ts")
    touch(tmp_path / "pkg/jest.config.ts")
    test = touch(tmp_path / "pkg/x.spec.ts")
    plan = runners.plan_for(str(test), str(tmp_path), "out")
    assert plan.runner == "jest"
    assert plan.coverage_commands[0][0] == "node_modules/.bin/jest"


# ---------------------------------------------------------------- runners: pytest

def fake_subprocess(monkeypatch, returncode):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=returncode)

    monkeypatch.setattr(runners, "subprocess", SimpleNamespace(run=run))
    return calls


def test_pytest_plan_without_coverage_or_pytest_is_runner_error(tmp_path, monkeypatch):
    calls = fake_subprocess(monkeypatch, 1)
    test = touch(tmp_path / "tests/test_x.py")
    with pytest.raises(runners.RunnerError, match="keel never installs them"):
        runners.plan_for(str(test), str(tmp_path), str(tmp_path / "out"))
    assert calls[0][0] == ["python3", "-c", "import coverage, pytest"]
    assert calls[0][1]["cwd"] == str(tmp_path)


def test_pytest_plan_with_returncode_zero_gives_run_and_lcov_commands(tmp_path, monkeypatch):
    fake_subprocess(monkeypatch, 0)
    test = touch(tmp_path / "tests/test_x.py")
    out = str(tmp_path / "out")
    plan = runners.plan_for(str(test), str(tmp_path), out)
    assert plan.runner == "pytest"
    assert plan.coverage_commands == [
        ["python3", "-m", "coverage", "run", "--data-file=" + out + "/.coverage", "-m", "pytest", "-q", "-x",
         "tests/test_x.py"],
        ["python3", "-m", "coverage", "lcov", "--data-file=" + out + "/.coverage", "-o", out + "/lcov.info"]]
    assert plan.mutant_command == "python3 -m pytest -q -x tests/test_x.py"
    assert "coverage" not in plan.mutant_command


def test_pytest_plan_uses_project_venv_python_relative_to_root(tmp_path, monkeypatch):
    calls = fake_subprocess(monkeypatch, 0)
    python = touch(tmp_path / ".venv/bin/python", "", 0o755)
    test = touch(tmp_path / "tests/test_x.py")
    plan = runners.plan_for(str(test), str(tmp_path), str(tmp_path / "out"))
    assert calls[0][0][0] == str(python)
    assert plan.coverage_commands[0][0] == ".venv/bin/python"
    assert plan.mutant_command.startswith(".venv/bin/python -m pytest")


# ---------------------------------------------------------------- measure: parse_mutants

MUTATOR_OUTPUT = (
    "SURVIVED  libs/a/x.service.ts:228 true -> false\n"
    "KILLED    libs/a/x.service.ts:242 0 -> 1\n"
    "SURVIVED  libs/a/x.service.ts:242 ?? -> ||\n"
    "Function  Namespace  Killed  Survived  Uncovered  Sites   Score\n"
    "---\n"
    "release   lib.x.X       2         5          0      7  28.6%\n"
    "---\n"
    "Total                                                                     2         5          0     43   28.6%\n")


def test_parse_mutants_real_output():
    result = measure.parse_mutants(MUTATOR_OUTPUT)
    assert result["survived"] == [
        {"file": "libs/a/x.service.ts", "line": 228, "mutation": "true -> false"},
        {"file": "libs/a/x.service.ts", "line": 242, "mutation": "?? -> ||"}]
    assert result["killed"] == 2
    assert result["uncovered"] == 0
    assert result["sites"] == result["killed"] + len(result["survived"]) + result["uncovered"]
    assert result["sites"] != 43


def test_parse_mutants_without_total_line_is_all_zero():
    result = measure.parse_mutants("baseline failed\nsomething else\n")
    assert result == {"killed": 0, "survived": [], "uncovered": 0, "sites": 0}


def test_parse_mutants_ignores_killed_lines_and_counts_uncovered():
    output = "KILLED a.ts:1 x -> y\nTotal   1   0   3   9  25.0%\n"
    result = measure.parse_mutants(output)
    assert result["survived"] == []
    assert (result["killed"], result["uncovered"], result["sites"]) == (1, 3, 4)


# ---------------------------------------------------------------- measure: crap_entries

def test_crap_entries_parses_edn_with_nil(tmp_path):
    touch(tmp_path / ".metrics/crap.edn",
          '{:entries [\n'
          '  {:name "resolveContext", :namespace "lib.q.Q", :complexity 7, :coverage 87.5, :crap 7.1}\n'
          '  {:name "f", :namespace "m", :complexity 3, :coverage nil, :crap nil}\n'
          ']}\n')
    assert measure.crap_entries(str(tmp_path)) == [
        {"name": "resolveContext", "namespace": "lib.q.Q", "complexity": 7, "coverage": 87.5, "crap": 7.1},
        {"name": "f", "namespace": "m", "complexity": 3, "coverage": None, "crap": None}]


def test_crap_entries_name_with_escaped_quote(tmp_path):
    touch(tmp_path / ".metrics/crap.edn",
          '{:entries [\n  {:name "a\\"b", :namespace "n", :complexity 1, :coverage 100.0, :crap 1.0}\n]}\n')
    entries = measure.crap_entries(str(tmp_path))
    assert len(entries) == 1 and entries[0]["name"] == 'a\\"b'


# ---------------------------------------------------------------- measure: dry_pairs / injection_only

def dry_entry(left, right, score="1.0"):
    return (' {{:score {}\n  :language "typescript"\n  :left {{:file "{}", :start-line {}, :end-line {}}}\n'
            '  :right {{:file "{}", :start-line {}, :end-line {}}}\n  :left-nodes 20\n  :right-nodes 20}}'
            .format(score, left[0], left[1], left[2], right[0], right[1], right[2]))


def write_dry(root, *entries):
    touch(root / ".metrics/dry.edn", "{:candidates [\n" + "\n".join(entries) + "\n]}\n")


CTOR = "constructor(\n    private readonly db: Db,\n    private readonly x: X,\n  ) {}\n"
CTOR_WITH_BODY = "constructor(\n    private readonly db: Db,\n  ) {\n    this.db = db;\n  }\n"
FUNCTION_A = "function total(a) {\n  const b = a * 2;\n  return b + 1;\n}\n"
FUNCTION_B = "function sum(x) {\n  const y = x * 2;\n  return y + 1;\n}\n"


def test_dry_pairs_parses_the_real_format(tmp_path):
    write_dry(tmp_path, dry_entry(("a.ts", 1, 4), ("b.ts", 3, 9), "0.93"))
    assert measure.dry_pairs(str(tmp_path)) == [{
        "score": 0.93, "language": "typescript",
        "left": {"file": "a.ts", "start": 1, "end": 4}, "right": {"file": "b.ts", "start": 3, "end": 9}}]


def test_injection_only_drops_di_constructors_and_keeps_real_functions(tmp_path):
    touch(tmp_path / "a.ts", CTOR)
    touch(tmp_path / "b.ts", CTOR)
    touch(tmp_path / "c.ts", FUNCTION_A)
    touch(tmp_path / "d.ts", FUNCTION_B)
    write_dry(tmp_path, dry_entry(("a.ts", 1, 4), ("b.ts", 1, 4)), dry_entry(("c.ts", 1, 4), ("d.ts", 1, 4)))
    ctor_pair, function_pair = measure.dry_pairs(str(tmp_path))
    assert measure.injection_only(str(tmp_path), ctor_pair) is True
    assert measure.injection_only(str(tmp_path), function_pair) is False


def test_injection_only_false_when_constructor_has_a_body_statement(tmp_path):
    touch(tmp_path / "a.ts", CTOR_WITH_BODY)
    touch(tmp_path / "b.ts", CTOR_WITH_BODY)
    write_dry(tmp_path, dry_entry(("a.ts", 1, 5), ("b.ts", 1, 5)))
    pair = measure.dry_pairs(str(tmp_path))[0]
    assert not measure.injection_only(str(tmp_path), pair)


def test_injection_only_false_when_only_one_side_is_a_constructor(tmp_path):
    touch(tmp_path / "a.ts", CTOR)
    touch(tmp_path / "d.ts", FUNCTION_B)
    write_dry(tmp_path, dry_entry(("a.ts", 1, 4), ("d.ts", 1, 4)))
    assert not measure.injection_only(str(tmp_path), measure.dry_pairs(str(tmp_path))[0])


def test_injection_only_accepts_parenthesised_defaults_and_empty_constructor(tmp_path):
    touch(tmp_path / "a.ts", "constructor(private readonly x = make(1)) {}\n")
    touch(tmp_path / "b.ts", "  constructor() {}\n")
    write_dry(tmp_path, dry_entry(("a.ts", 1, 1), ("b.ts", 1, 1)))
    assert measure.injection_only(str(tmp_path), measure.dry_pairs(str(tmp_path))[0])


def test_command_dry_filters_injection_only_pairs_and_counts_them(tmp_path, monkeypatch):
    touch(tmp_path / "a.ts", CTOR)
    touch(tmp_path / "b.ts", CTOR)
    touch(tmp_path / "c.ts", FUNCTION_A)
    touch(tmp_path / "d.ts", FUNCTION_B)
    write_dry(tmp_path, dry_entry(("a.ts", 1, 4), ("b.ts", 1, 4)), dry_entry(("c.ts", 1, 4), ("d.ts", 1, 4)))
    calls = []

    def run_tool(tool, lcov, args, root, prefix, timeout=None):
        calls.append((tool, lcov, args, root, prefix))
        return 0, "report\n"

    monkeypatch.setattr(measure, "run_tool", run_tool)
    paths = [str(tmp_path / "c.ts"), str(tmp_path / "d.ts")]
    result = measure.command_dry(measure.Options(["dry", "--min-lines", "6"] + paths), str(tmp_path), ["p"])
    assert calls == [("dryer", "-", ["--threshold", "0.8", "--min-lines", "6"] + paths, str(tmp_path), ["p"])]
    assert [pair["left"]["file"] for pair in result["pairs"]] == ["c.ts"]
    assert result["ignored_constructors"] == 1


def test_command_dry_stops_when_the_tool_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(measure, "run_tool", lambda *args, **kwargs: (1, "boom"))
    with pytest.raises(measure.Stop, match="dryer failed"):
        measure.command_dry(measure.Options(["dry", str(tmp_path / "a.ts")]), str(tmp_path), [])


def test_command_dry_without_paths_and_nothing_changed_runs_no_tool(tmp_path, monkeypatch):
    root = make_repo(tmp_path / "repo", {"a.ts": "x\n"})
    monkeypatch.setattr(measure, "run_tool", lambda *args, **kwargs: pytest.fail("tool must not run"))
    result = measure.command_dry(measure.Options(["dry"]), str(root), [])
    assert result["pairs"] == [] and result["ignored_constructors"] == 0


# ---------------------------------------------------------------- measure: touched_lines

TWELVE = "".join("line{}\n".format(n) for n in range(1, 13))


def test_touched_lines_modified_line(tmp_path):
    root = make_repo(tmp_path / "repo", {"a.ts": TWELVE})
    touch(root / "a.ts", TWELVE.replace("line3\n", "changed\n"))
    assert measure.touched_lines(str(root), str(root / "a.ts"), "HEAD") == {3}


def test_touched_lines_added_range(tmp_path):
    root = make_repo(tmp_path / "repo", {"a.ts": "1\n2\n3\n4\n5\n"})
    touch(root / "a.ts", "1\n2\n3\n4\n5\n6\n7\n")
    assert measure.touched_lines(str(root), str(root / "a.ts"), "HEAD") == {6, 7}


def test_touched_lines_includes_staged_changes(tmp_path):
    root = make_repo(tmp_path / "repo", {"a.ts": TWELVE})
    touch(root / "a.ts", TWELVE.replace("line5\n", "changed\n"))
    git_run(root, "add", "a.ts")
    assert measure.touched_lines(str(root), str(root / "a.ts"), "HEAD") == {5}


def test_touched_lines_unchanged_tracked_file_is_empty_set(tmp_path):
    root = make_repo(tmp_path / "repo", {"a.ts": TWELVE})
    assert measure.touched_lines(str(root), str(root / "a.ts"), "HEAD") == set()


def test_touched_lines_untracked_file_is_none(tmp_path):
    root = make_repo(tmp_path / "repo", {"a.ts": TWELVE})
    touch(root / "new.ts", "x\n")
    assert measure.touched_lines(str(root), str(root / "new.ts"), "HEAD") is None


def test_touched_lines_against_an_older_base(tmp_path):
    root = make_repo(tmp_path / "repo", {"a.ts": TWELVE})
    touch(root / "a.ts", TWELVE.replace("line8\n", "changed\n"))
    git_run(root, "commit", "-q", "-am", "second")
    assert measure.touched_lines(str(root), str(root / "a.ts"), "HEAD") == set()
    assert measure.touched_lines(str(root), str(root / "a.ts"), "HEAD~1") == {8}


def test_touched_lines_unknown_base_stops_instead_of_reporting_nothing_touched(tmp_path):
    root = make_repo(tmp_path / "repo", {"a.ts": TWELVE})
    touch(root / "a.ts", TWELVE.replace("line3\n", "changed\n"))
    with pytest.raises(measure.Stop, match="no-such-ref"):
        measure.touched_lines(str(root), str(root / "a.ts"), "no-such-ref")


# ---------------------------------------------------------------- measure: touched_function_lines

SPANS = json.dumps([{"name": "a", "start": 1, "end": 5}, {"name": "b", "start": 7, "end": 12}])


def spans_repo(tmp_path, monkeypatch, changed_line, output=SPANS):
    root = make_repo(tmp_path / "repo", {"a.ts": TWELVE})
    touch(root / "a.ts", TWELVE.replace("line{}\n".format(changed_line), "changed\n"))
    calls = []

    def run_tool(tool, lcov, args, root_, prefix, timeout=None):
        calls.append((tool, lcov, args, root_, prefix))
        return 0, output

    monkeypatch.setattr(measure, "run_tool", run_tool)
    return root, calls


def test_touched_function_lines_selects_the_whole_function(tmp_path, monkeypatch):
    root, calls = spans_repo(tmp_path, monkeypatch, 9, "log noise\n" + SPANS + "\n")
    selected = measure.touched_function_lines(str(root), str(root / "a.ts"), "HEAD", ["p"])
    assert selected == set(range(7, 13))
    assert calls == [("spans", "-", [str(root / "a.ts")], str(root), ["p"])]


def test_touched_function_lines_line_between_functions_selects_nothing(tmp_path, monkeypatch):
    root, _ = spans_repo(tmp_path, monkeypatch, 6)
    assert measure.touched_function_lines(str(root), str(root / "a.ts"), "HEAD", []) == set()


def test_touched_function_lines_untracked_file_is_none_without_calling_the_tool(tmp_path, monkeypatch):
    root, calls = spans_repo(tmp_path, monkeypatch, 9)
    touch(root / "new.ts", "x\n")
    assert measure.touched_function_lines(str(root), str(root / "new.ts"), "HEAD", []) is None
    assert calls == []


def test_touched_function_lines_stops_when_spans_tool_fails(tmp_path, monkeypatch):
    root, _ = spans_repo(tmp_path, monkeypatch, 9)
    monkeypatch.setattr(measure, "run_tool", lambda *args, **kwargs: (1, "traceback"))
    with pytest.raises(measure.Stop, match="could not read the functions"):
        measure.touched_function_lines(str(root), str(root / "a.ts"), "HEAD", [])


# ---------------------------------------------------------------- measure: check_outputs_ignored

def test_check_outputs_ignored_without_gitignore_stops(tmp_path):
    root = make_repo(tmp_path / "repo")
    with pytest.raises(measure.Stop, match="is not ignored by git"):
        measure.check_outputs_ignored(str(root))


def test_check_outputs_ignored_with_all_three_folders_passes(tmp_path):
    root = make_repo(tmp_path / "repo")
    touch(root / ".gitignore", "/.metrics/\n/target/mutation-workers/\n/target/mutator-backup/\n")
    assert measure.check_outputs_ignored(str(root)) is None


def test_check_outputs_ignored_stops_naming_the_folder_still_tracked_by_git(tmp_path):
    root = make_repo(tmp_path / "repo")
    touch(root / ".gitignore", "/.metrics/\n/target/mutator-backup/\n")
    with pytest.raises(measure.Stop, match="target/mutation-workers/"):
        measure.check_outputs_ignored(str(root))


# ---------------------------------------------------------------- measure: Options

def test_options_diff_with_base_and_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    options = measure.Options(["mutate", "--diff", "HEAD~1", "a.ts"])
    assert options.command == "mutate"
    assert options.diff == "HEAD~1"
    assert options.paths == [str(tmp_path / "a.ts")]


def test_options_diff_followed_by_existing_file_means_head(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    touch(tmp_path / "a.ts")
    options = measure.Options(["mutate", "--diff", "a.ts"])
    assert options.diff == "HEAD"
    assert options.paths == [str(tmp_path / "a.ts")]


@pytest.mark.parametrize("argv", [["mutate", "--diff"], ["mutate", "--diff", "--json"]])
def test_options_diff_without_base_means_head(tmp_path, monkeypatch, argv):
    monkeypatch.chdir(tmp_path)
    assert measure.Options(argv).diff == "HEAD"


def test_options_defaults():
    options = measure.Options(["crap", "x.ts"])
    assert options.budget == 600.0
    assert options.min_lines == "4"
    assert (options.test, options.diff, options.json, options.no_sandbox) == (None, None, False, False)
    assert measure.Options([]).command == "status"


def test_options_flags_with_values(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    options = measure.Options(["mutate", "--test", "t.spec.ts", "--budget", "30", "--min-lines", "8", "--json",
                               "--no-sandbox", "a.ts"])
    assert options.test == "t.spec.ts"
    assert options.budget == 30.0
    assert options.min_lines == "8"
    assert options.json is True and options.no_sandbox is True
    assert options.paths == [str(tmp_path / "a.ts")]


# ---------------------------------------------------------------- measure: sandbox

def test_sandbox_without_prefix_and_without_flag_stops(monkeypatch):
    monkeypatch.setattr(measure.tools, "sandbox_prefix", lambda: None)
    with pytest.raises(measure.Stop, match="no network sandbox"):
        measure.sandbox(measure.Options(["crap", "a.ts"]))


def test_sandbox_no_sandbox_flag_returns_empty_prefix_and_warns(monkeypatch, capsys):
    monkeypatch.setattr(measure.tools, "sandbox_prefix", lambda: None)
    assert measure.sandbox(measure.Options(["crap", "a.ts", "--no-sandbox"])) == []
    captured = capsys.readouterr()
    assert "WARNING" in captured.err and "WITHOUT network isolation" in captured.err
    assert captured.out == ""


@pytest.mark.parametrize("argv", [["crap", "a.ts"], ["crap", "a.ts", "--no-sandbox"]])
def test_sandbox_with_prefix_returns_it_silently(monkeypatch, capsys, argv):
    monkeypatch.setattr(measure.tools, "sandbox_prefix", lambda: ["sandbox-exec", "-p", "profile"])
    assert measure.sandbox(measure.Options(argv)) == ["sandbox-exec", "-p", "profile"]
    assert capsys.readouterr().err == ""


# ---------------------------------------------------------------- measure: command_mutate deadline / clean_workers

class Clock:
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now


def test_command_mutate_budget_exhausted_skips_the_next_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    clock = Clock()
    monkeypatch.setattr(measure, "time", clock)
    workers = tmp_path / "target/mutation-workers"
    (workers / "run-old").mkdir(parents=True)
    calls = []

    def mutate_file(source, root, options, prefix, deadline):
        calls.append((source, deadline))
        (workers / "run-new").mkdir()
        clock.now += 20
        return {"file": "first", "status": "all killed", "survived": []}

    monkeypatch.setattr(measure, "mutate_file", mutate_file)
    options = measure.Options(["mutate", "a.ts", "b.ts", "--budget", "10"])
    result = measure.command_mutate(options, str(tmp_path), [])
    assert [item["status"] for item in result["files"]] == ["all killed", "not run (budget)"]
    assert result["files"][1]["file"] == "b.ts"
    assert result["budget_seconds"] == 10.0
    assert calls == [(str(tmp_path / "a.ts"), 1010.0)]
    assert not (workers / "run-new").exists()
    assert (workers / "run-old").is_dir()


def test_command_mutate_budget_zero_runs_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(measure, "mutate_file", lambda *args: pytest.fail("must not run"))
    result = measure.command_mutate(measure.Options(["mutate", "a.ts", "b.ts", "--budget", "0"]), str(tmp_path), [])
    assert [item["status"] for item in result["files"]] == ["not run (budget)"] * 2


def test_clean_workers_removes_only_run_dirs_created_after_the_start(tmp_path):
    base = tmp_path / "target/mutation-workers"
    for name in ("run-old", "other-old"):
        (base / name).mkdir(parents=True)
    before = set(os.listdir(base))
    for name in ("run-new", "run-2", "cache-new"):
        (base / name).mkdir()
    (base / "run-new/file").write_text("x")
    measure.clean_workers(str(tmp_path), before)
    assert sorted(os.listdir(base)) == ["cache-new", "other-old", "run-old"]


def test_clean_workers_without_the_folder_is_a_noop(tmp_path):
    measure.clean_workers(str(tmp_path), set())
    assert not (tmp_path / "target").exists()


def test_command_mutate_cleans_workers_even_when_a_file_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workers = tmp_path / "target/mutation-workers"
    workers.mkdir(parents=True)

    def mutate_file(*args):
        (workers / "run-new").mkdir()
        raise measure.Stop("boom")

    monkeypatch.setattr(measure, "mutate_file", mutate_file)
    with pytest.raises(measure.Stop):
        measure.command_mutate(measure.Options(["mutate", "a.ts"]), str(tmp_path), [])
    assert not (workers / "run-new").exists()
