"""coordination-sweep.py at SessionStart: a checkout file changed and not cited by the coordination's open state warns."""
import subprocess

import pytest

from conftest import load_script

sweep = load_script("coordination-sweep.py")


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True)


@pytest.fixture
def project(tmp_path):
    repo = tmp_path / "proj"
    (repo / "src").mkdir(parents=True)
    for name in ("a.ts", "b.ts", "c.ts"):
        (repo / "src" / name).write_text("x\n")
    git(repo, "init", "-q")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x")
    root = tmp_path / "coordination"
    (root / "proj").mkdir(parents=True)
    return repo, root


def test_uncited_change_warns_with_the_path(project):
    repo, root = project
    (root / "proj" / "queue.md").write_text("# Open\n- front-x: something else\n")
    (repo / "src" / "a.ts").write_text("changed\n")
    out = sweep.unregistered_changes(str(repo), str(root))
    assert "src/a.ts" in out
    assert "queue.md" in out


def test_change_cited_by_the_open_state_is_quiet(project):
    repo, root = project
    (root / "proj" / "queue.md").write_text("# Open\n- paused: src/a.ts (measure, then commit)\n")
    (repo / "src" / "a.ts").write_text("changed\n")
    assert sweep.unregistered_changes(str(repo), str(root)) == ""


def test_a_citation_in_the_coordinator_handoff_counts(project):
    repo, root = project
    (root / "proj" / "queue.md").write_text("# Open\n")
    (root / "proj" / "handoff").mkdir()
    (root / "proj" / "handoff" / "coordinator.md").write_text("owner's WIP: src/a.ts\n")
    (repo / "src" / "a.ts").write_text("changed\n")
    assert sweep.unregistered_changes(str(repo), str(root)) == ""


def test_only_the_uncited_paths_are_listed(project):
    repo, root = project
    (root / "proj" / "queue.md").write_text("paused: src/a.ts\n")
    for name in ("a.ts", "b.ts"):
        (repo / "src" / name).write_text("changed\n")
    out = sweep.unregistered_changes(str(repo), str(root))
    assert "src/b.ts" in out and "src/a.ts" not in out


def test_untracked_files_do_not_warn(project):
    repo, root = project
    (root / "proj" / "queue.md").write_text("# Open\n")
    (repo / "src" / "new.ts").write_text("new\n")
    assert sweep.unregistered_changes(str(repo), str(root)) == ""


def test_project_without_coordination_state_is_quiet(project, tmp_path):
    repo, _ = project
    (repo / "src" / "a.ts").write_text("changed\n")
    assert sweep.unregistered_changes(str(repo), str(tmp_path / "nothing")) == ""


def test_clean_checkout_is_quiet(project):
    repo, root = project
    (root / "proj" / "queue.md").write_text("# Open\n")
    assert sweep.unregistered_changes(str(repo), str(root)) == ""


def test_a_subdirectory_resolves_to_the_checkout(project):
    repo, root = project
    (root / "proj" / "queue.md").write_text("# Open\n")
    (repo / "src" / "a.ts").write_text("changed\n")
    assert "src/a.ts" in sweep.unregistered_changes(str(repo / "src"), str(root))


def test_long_lists_are_cut(project):
    repo, root = project
    (root / "proj" / "queue.md").write_text("# Open\n")
    for i in range(9):
        (repo / "src" / f"f{i}.ts").write_text("x\n")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "more")
    for i in range(9):
        (repo / "src" / f"f{i}.ts").write_text("changed\n")
    out = sweep.unregistered_changes(str(repo), str(root))
    assert "9 file(s)" in out and "+4 more" in out


def test_outside_a_repo_is_quiet(tmp_path):
    assert sweep.unregistered_changes(str(tmp_path), str(tmp_path)) == ""
