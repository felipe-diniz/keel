"""The session-start sweep says what it keeps that weighs: a worktree no live session uses, a heavy log kept only
because the open state cites it, and a `queue.md` grown past its cap."""
import os
import subprocess
import time

import pytest

from conftest import load_script

sweep = load_script("coordination-sweep.py")
DAY = 86400


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False)


def age(path, days):
    stamp = time.time() - days * DAY
    os.utime(path, (stamp, stamp))


@pytest.fixture
def repo(tmp_path):
    checkout = tmp_path / "proj"
    git(tmp_path, "init", "-q", "-b", "main", str(checkout))
    (checkout / "a.txt").write_text("a\n")
    git(checkout, "add", "a.txt")
    git(checkout, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "a")
    return checkout


def worktree(checkout, name, idle_days):
    path = checkout / ".claude" / "worktrees" / name
    git(checkout, "worktree", "add", "-q", "--detach", str(path), "HEAD")
    admin = git(path, "rev-parse", "--absolute-git-dir").stdout.strip()
    for base, dirs, files in os.walk(admin, topdown=False):
        for name in dirs + files:
            age(os.path.join(base, name), idle_days)
    age(admin, idle_days)
    return path


def test_an_idle_worktree_with_no_live_session_is_named(repo):
    worktree(repo, "pfx-done", 3)
    worktree(repo, "pfx-running", 3)
    worktree(repo, "pfx-new", 0)
    out = sweep.orphan_worktrees(str(repo), {"pfx-running"}, time.time())
    assert "pfx-done" in out and "--close" in out
    assert "pfx-running" not in out and "pfx-new" not in out


def test_no_warning_when_the_live_list_cannot_be_read(repo):
    worktree(repo, "pfx-done", 3)
    assert sweep.orphan_worktrees(str(repo), None, time.time()) == ""


def test_no_warning_outside_a_repo(tmp_path):
    assert sweep.orphan_worktrees(str(tmp_path), set(), time.time()) == ""


def state_with(tmp_path, queue_text):
    root = tmp_path / "coordination"
    state = root / "proj"
    (state / "logs" / "pfx-big").mkdir(parents=True)
    (state / "logs" / "pfx-big" / "film.bin").write_bytes(b"x" * (sweep.HELD_BYTES + 1))
    (state / "logs" / "pfx-small").mkdir()
    (state / "logs" / "pfx-small" / "a.log").write_text("x")
    for path in (state / "logs" / "pfx-big" / "film.bin", state / "logs" / "pfx-big", state / "logs" / "pfx-small" /
                 "a.log", state / "logs" / "pfx-small"):
        age(path, 10)
    (state / "queue.md").write_text(queue_text)
    return root, state


def test_a_heavy_log_kept_only_by_a_citation_is_reported(tmp_path):
    root, state = state_with(tmp_path, "- 31/10 frames in logs/pfx-big/ and logs/pfx-small/\n")
    held = []
    sweep.sweep_state(str(root), set(), time.time(), held)
    out = sweep.held_warning(held, str(root))
    assert (state / "logs" / "pfx-big").exists()
    assert "logs/pfx-big" in out and "queue.md" in out
    assert "pfx-small" not in out


def test_a_queue_past_its_cap_is_reported(tmp_path):
    root, _ = state_with(tmp_path, "- a line of the diary\n" * 1000)
    out = sweep.held_warning([], str(root))
    assert "queue.md" in out and "queue-archive" in out


def test_a_short_queue_and_nothing_held_is_quiet(tmp_path):
    root, _ = state_with(tmp_path, "- open: one item\n")
    assert sweep.held_warning([], str(root)) == ""
