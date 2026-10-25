"""coordination-sweep.py --close: a temporary $D, a fake agents list, a temporary jobs root and a real temporary repo."""
import json
import os
import subprocess

import pytest

from conftest import load_script

sweep = load_script("coordination-sweep.py")

S = "pfx-front"
SID = "abcdef12-0000-0000-0000-000000000000"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False)


@pytest.fixture
def env(tmp_path):
    d = tmp_path / "coord"
    for sub in ("logs", "prompts", "handoff"):
        (d / sub).mkdir(parents=True)
    (d / "logs" / S).mkdir()
    (d / "logs" / S / "suite.log").write_text("x" * 100)
    (d / "logs" / f"{S}.prompt.md").write_text("prompt")
    (d / "prompts" / f"{S}.md").write_text("front")
    (d / "prompts" / "_shared.md").write_text("shared")
    (d / "prompts" / "pfx-other.md").write_text("other")
    (d / "handoff" / f"{S}.md").write_text("handoff")
    (d / "handoff" / "coordinator.md").write_text("checkpoint\n")
    (d / "handoff" / "pfx-other.md").write_text("other handoff\n")
    (d / "queue.md").write_text(f"# queue\nActive front: {S}, owner decision of 24/10 kept here.\n")
    (d / "window.md").write_text(
        "| resource | holder |\n|---|---|\n"
        f"| test db | {S} |\n"
        f"| bench | pfx-other, then {S} |\n"
        "| ports | pfx-other |\n")
    jobs = tmp_path / "jobs"
    (jobs / SID[:8] / "tmp").mkdir(parents=True)
    (jobs / SID[:8] / "tmp" / "scratch.txt").write_text("s")
    (jobs / SID[:8] / "keep.json").write_text("{}")
    agents_file = tmp_path / "agents.json"

    class Env:
        pass

    e = Env()
    e.d, e.jobs, e.tmp, e.agents_file = d, jobs, tmp_path, agents_file
    e.agents = [
        {"name": S, "sessionId": SID, "kind": "background", "state": "stopped", "startedAt": 1, "cwd": "/x"},
        {"name": "pfx-other", "sessionId": "ffff0000-1", "kind": "background", "state": "working", "pid": 1,
         "status": "busy", "startedAt": 2, "cwd": "/x"},
    ]

    def run(*extra, agents=None):
        data = e.agents if agents is None else agents
        agents_file.write_text(data if isinstance(data, str) else json.dumps(data))
        argv = ["--close", S, "--state", str(d), "--agents-file", str(agents_file), "--jobs-root", str(jobs),
                *extra]
        return sweep.close(argv)

    e.run = run
    return e


def test_close_removes_the_front_state_and_lists_it(env):
    out = env.run()
    d = env.d
    assert not (d / "logs" / S).exists() and not (d / "logs" / f"{S}.prompt.md").exists()
    assert not (d / "prompts" / f"{S}.md").exists() and not (d / "handoff" / f"{S}.md").exists()
    for rel in (f"logs/{S}", f"logs/{S}.prompt.md", f"prompts/{S}.md", f"handoff/{S}.md"):
        assert rel in out
    assert not (env.jobs / SID[:8] / "tmp" / "scratch.txt").exists()
    assert (env.jobs / SID[:8] / "keep.json").exists()


def test_close_keeps_shared_blocks_the_checkpoint_and_other_fronts(env):
    env.run()
    d = env.d
    assert (d / "prompts" / "_shared.md").exists() and (d / "prompts" / "pfx-other.md").exists()
    assert (d / "handoff" / "coordinator.md").exists() and (d / "handoff" / "pfx-other.md").exists()


def test_close_refuses_a_live_session(env):
    env.agents[0].update(state="working", pid=7, status="busy")
    out = env.run()
    assert "live" in out
    assert (env.d / "logs" / S).exists() and (env.d / "handoff" / f"{S}.md").exists()


def test_close_refuses_when_the_agents_list_is_unreadable(env):
    out = env.run(agents="not json")
    assert "unreadable" in out
    assert (env.d / "logs" / S).exists()


def test_a_path_cited_by_the_open_state_stays(env):
    (env.d / "queue.md").write_text(f"pending: owner checks logs/{S}/suite.log\n")
    out = env.run()
    assert (env.d / "logs" / S / "suite.log").exists()
    assert "kept" in out and f"logs/{S}" in out


def test_a_path_cited_by_a_live_front_stays(env):
    (env.d / "handoff" / "pfx-other.md").write_text(f"reuse the fixture in logs/{S}/suite.log\n")
    env.run()
    assert (env.d / "logs" / S / "suite.log").exists()


def test_media_for_the_owner_stays_until_sent(env):
    (env.d / "logs" / S / "screen.png").write_bytes(b"png")
    (env.d / "logs" / S / "walk.mp4").write_bytes(b"mp4")
    out = env.run()
    assert (env.d / "logs" / S / "screen.png").exists() and (env.d / "logs" / S / "walk.mp4").exists()
    assert not (env.d / "logs" / S / "suite.log").exists()
    assert "SendUserFile" in out and "screen.png" in out
    again = env.run("--sent")
    assert not (env.d / "logs" / S).exists()
    assert "SendUserFile" not in again


def test_window_lines_of_the_front_go_shared_lines_stay(env):
    out = env.run()
    window = (env.d / "window.md").read_text()
    assert "| test db |" not in window
    assert f"| bench | pfx-other, then {S} |" in window and "| ports | pfx-other |" in window
    assert "window.md" in out and "bench" in out


def test_queue_keeps_one_line_with_the_shas(env):
    (env.d / "queue.md").write_text(f"# queue\n{S} {SID} 1111111\nActive front: {S}, decision kept.\n")
    out = env.run("--sha", "1111111", "2222222")
    lines = (env.d / "queue.md").read_text().splitlines()
    front = [x for x in lines if x.startswith(S + " ")]
    assert len(front) == 1 and "1111111" in front[0] and "2222222" in front[0] and SID in front[0]
    assert "closed" in front[0]
    assert f"Active front: {S}, decision kept." in lines
    assert "queue.md" in out


def test_queue_line_is_appended_when_missing(env):
    env.run("--sha", "3333333")
    assert any(x.startswith(f"{S} {SID} 3333333") for x in (env.d / "queue.md").read_text().splitlines())


def test_dry_run_removes_nothing(env):
    out = env.run("--dry-run", "--sha", "1")
    assert "would remove" in out
    assert (env.d / "logs" / S).exists() and (env.d / "handoff" / f"{S}.md").exists()
    assert "| test db |" in (env.d / "window.md").read_text()
    assert (env.jobs / SID[:8] / "tmp" / "scratch.txt").exists()
    assert S + " " + SID not in (env.d / "queue.md").read_text()


def test_worktree_of_the_front_goes_dirty_one_stays(env, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "x")
    wt = repo / ".claude" / "worktrees" / S
    git(repo, "worktree", "add", "-q", "-b", f"worktree-{S}", str(wt))
    out = env.run("--checkout", str(repo))
    assert not wt.exists()
    assert "worktree" in out
    assert f"worktree-{S}" not in git(repo, "branch", "--list").stdout

    wt2 = repo / ".claude" / "worktrees" / S
    git(repo, "worktree", "add", "-q", "-b", f"worktree-{S}", str(wt2))
    (wt2 / "wip.txt").write_text("wip")
    (env.d / "logs" / S).mkdir()
    out = env.run("--checkout", str(repo))
    assert wt2.exists() and "left" in out


def test_profile_cleanup_list_is_shown_not_run(env, tmp_path):
    repo = tmp_path / "proj"
    (repo / ".claude" / "coordination").mkdir(parents=True)
    (repo / ".claude" / "coordination" / "profile.md").write_text(
        "# profile\n## Cleanup at front close\n"
        "- `dropdb test_<SESSION-NAME>`: the front's test database\n"
        "- `redis-cli -n 5 flushdb`\n"
        "## Production\n- `never this`\n")
    out = env.run("--checkout", str(repo))
    assert f"dropdb test_{S}" in out and "redis-cli -n 5 flushdb" in out and "never this" not in out


def test_cli_prints_the_report(env, capsys):
    env.agents_file.write_text(json.dumps(env.agents))
    rc = sweep.main(["--close", S, "--state", str(env.d), "--agents-file", str(env.agents_file),
                     "--jobs-root", str(env.jobs)])
    assert rc == 0
    assert f"keel close {S}" in capsys.readouterr().out
