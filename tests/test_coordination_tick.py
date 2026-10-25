"""coordination-tick.py: fake `claude agents --json --all`, fake transcripts, a temporary $D and a fake launcher."""
import json
import os
import stat
import sys

import pytest

from conftest import load_script

tick = load_script("coordination-tick.py")

NOW = 1_800_000_000
CHECKOUT = "/work/repo"


def agent(name, sid, state, cwd=CHECKOUT, started=1, live=True, kind="background"):
    e = {"id": sid[:8], "cwd": cwd, "kind": kind, "startedAt": started, "sessionId": sid, "name": name, "state": state}
    if live:
        e["pid"] = 4242
        e["status"] = "busy" if state == "working" else "idle"
    return e


def limit_entry(resets, error="rate_limit"):
    e = {"type": "assistant", "isApiErrorMessage": True, "error": error,
         "message": {"model": "<synthetic>", "content": [{"type": "text", "text": "You've hit your limit"}]}}
    if error == "rate_limit":
        e["apiError"] = "usage_limit_reached"
        e["apiErrorStatus"] = 429
        e["apiErrorParams"] = {"rate_limit_info": {"status": "rejected", "resetsAt": resets}}
    else:
        e["apiErrorStatus"] = 400
    return e


def ok_entry(text="done"):
    return {"type": "assistant", "message": {"model": "m", "content": [{"type": "text", "text": text}]}}


def prompt_entry(text="keel keep-alive"):
    return {"type": "user", "message": {"role": "user", "content": text}}


@pytest.fixture
def env(tmp_path):
    d = tmp_path / "coord"
    (d / "handoff").mkdir(parents=True)
    (d / "queue.md").write_text("# queue\n")
    projects = tmp_path / "projects" / "-work-repo"
    projects.mkdir(parents=True)
    calls = tmp_path / "calls.jsonl"
    fake = tmp_path / "claude"
    fake.write_text(
        "#!/usr/bin/env python3\nimport json, os, sys\n"
        f"open({str(calls)!r}, 'a').write(json.dumps({{'argv': sys.argv[1:], 'cwd': os.getcwd()}}) + '\\n')\n"
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    agents_file = tmp_path / "agents.json"

    class Env:
        pass

    e = Env()
    e.d, e.projects, e.calls, e.fake, e.agents_file, e.tmp = d, projects, calls, fake, agents_file, tmp_path

    def transcript(sid, entries):
        (projects / f"{sid}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in entries))

    def run(agents, *extra, now=NOW):
        if agents is None:
            agents_file.write_text("not json")
        else:
            agents_file.write_text(json.dumps(agents))
        argv = ["--self", "coord", "--checkout", CHECKOUT, "--state", str(d), "--claude", str(fake),
                "--agents-file", str(agents_file), "--projects-root", str(tmp_path / "projects"),
                "--now", str(now), "--settings", "/lean.json", *extra]
        return tick.run(argv)

    def launches():
        if not calls.exists():
            return []
        return [json.loads(x) for x in calls.read_text().splitlines()]

    e.transcript, e.run, e.launches = transcript, run, launches
    return e


def test_no_front_prints_stop(env):
    out = env.run([agent("coord", "c-1", "working", kind="interactive")])
    assert out.startswith("keel tick: stop")
    assert "\n" not in out


def test_live_front_in_checkout_keeps_the_tick(env):
    env.transcript("f-1", [ok_entry()])
    out = env.run([agent("pfx-a", "f-1", "working")])
    assert "stop" not in out
    assert "1 live (pfx-a)" in out


def test_front_in_another_checkout_cited_in_open_state_counts(env):
    (env.d / "queue.md").write_text("active front: pfx-other, sha pending\n")
    env.transcript("f-2", [ok_entry()])
    out = env.run([agent("pfx-other", "f-2", "working", cwd="/elsewhere")])
    assert "1 live (pfx-other)" in out


def test_front_in_another_checkout_not_cited_is_ignored(env):
    out = env.run([agent("stranger", "f-3", "working", cwd="/elsewhere")])
    assert out.startswith("keel tick: stop")


def test_dead_front_cut_by_limit_after_reset_is_resumed(env):
    (env.d / "queue.md").write_text("active front: pfx-a\n")
    env.transcript("f-1", [prompt_entry("work"), limit_entry(NOW - 60)])
    out = env.run([agent("pfx-a", "f-1", "stopped", live=False)])
    assert "resumed pfx-a" in out
    [call] = env.launches()
    argv = call["argv"]
    assert argv[:4] == ["--bg", "--resume", "f-1", "-n"] and argv[4] == "pfx-a"
    assert argv[argv.index("--settings") + 1] == "/lean.json"
    assert argv[argv.index("--add-dir") + 1] == str(env.d)
    assert argv[argv.index("--permission-mode") + 1] == "auto"
    assert "handoff/pfx-a.md" in argv[-1]
    assert call["cwd"] == CHECKOUT or not os.path.isdir(CHECKOUT)
    assert "pfx-a" in json.loads((env.d / "tick.json").read_text())


def test_resume_is_throttled(env):
    (env.d / "queue.md").write_text("active front: pfx-a\n")
    env.transcript("f-1", [limit_entry(NOW - 60)])
    agents = [agent("pfx-a", "f-1", "stopped", live=False)]
    env.run(agents)
    out = env.run(agents, now=NOW + 300)
    assert len(env.launches()) == 1
    assert "stop" not in out


def test_dead_front_before_reset_waits(env):
    (env.d / "queue.md").write_text("active front: pfx-a\n")
    env.transcript("f-1", [limit_entry(NOW + 3600)])
    out = env.run([agent("pfx-a", "f-1", "failed", live=False)])
    assert env.launches() == []
    assert "waiting pfx-a" in out and "stop" not in out


def test_dead_front_cut_by_limit_but_not_open_is_left(env):
    env.transcript("f-1", [limit_entry(NOW - 60)])
    out = env.run([agent("pfx-a", "f-1", "stopped", live=False)])
    assert env.launches() == []
    assert out.startswith("keel tick: stop")


def test_closed_front_stopped_normally_is_left(env):
    (env.d / "queue.md").write_text("pfx-a f-1 abc1234 closed\n")
    env.transcript("f-1", [ok_entry("final report sent")])
    out = env.run([agent("pfx-a", "f-1", "stopped", live=False)])
    assert env.launches() == []
    assert out.startswith("keel tick: stop")


def test_newer_live_session_of_the_same_name_wins(env):
    (env.d / "queue.md").write_text("active front: pfx-a\n")
    env.transcript("f-old", [limit_entry(NOW - 60)])
    env.transcript("f-new", [ok_entry()])
    out = env.run([agent("pfx-a", "f-old", "stopped", started=1, live=False),
                   agent("pfx-a", "f-new", "working", started=2)])
    assert env.launches() == []
    assert "1 live (pfx-a)" in out


def test_live_front_blocked_by_limit_after_reset_is_woken_once(env):
    env.transcript("f-1", [limit_entry(NOW - 60)])
    agents = [agent("pfx-a", "f-1", "blocked")]
    out = env.run(agents)
    assert "wake pfx-a" in out
    again = env.run(agents, now=NOW + 300)
    assert "wake" not in again and "stop" not in again
    assert env.launches() == []


def test_live_front_blocked_for_permission_is_live(env):
    env.transcript("f-1", [ok_entry("asking")])
    out = env.run([agent("pfx-a", "f-1", "blocked")])
    assert "1 live (pfx-a)" in out and "wake" not in out


def test_billing_error_retries_every_two_hours(env):
    (env.d / "queue.md").write_text("active front: pfx-a\n")
    env.transcript("f-1", [limit_entry(None, error="billing_error")])
    agents = [agent("pfx-a", "f-1", "stopped", live=False)]
    env.run(agents)
    env.run(agents, now=NOW + 3600)
    env.run(agents, now=NOW + 2 * 3600 + 1)
    assert len(env.launches()) == 2


def test_self_cut_by_limit_is_reported(env):
    env.transcript("c-1", [prompt_entry("step"), limit_entry(NOW - 60), prompt_entry("keel keep-alive")])
    env.transcript("f-1", [ok_entry()])
    out = env.run([agent("coord", "c-1", "working", kind="interactive"), agent("pfx-a", "f-1", "working")])
    assert "self" in out


def test_self_not_cut_is_silent(env):
    env.transcript("c-1", [prompt_entry("step"), ok_entry(), prompt_entry("keel keep-alive")])
    env.transcript("f-1", [ok_entry()])
    out = env.run([agent("coord", "c-1", "working", kind="interactive"), agent("pfx-a", "f-1", "working")])
    assert "self" not in out


def test_dry_run_launches_nothing_and_writes_nothing(env):
    (env.d / "queue.md").write_text("active front: pfx-a\n")
    env.transcript("f-1", [limit_entry(NOW - 60)])
    out = env.run([agent("pfx-a", "f-1", "stopped", live=False)], "--dry-run")
    assert "would resume pfx-a" in out
    assert env.launches() == [] and not (env.d / "tick.json").exists()


def test_unreadable_agents_never_stops(env):
    out = env.run(None)
    assert "stop" not in out and "unreadable" in out


def test_cli_prints_one_line(env, capsys):
    env.agents_file.write_text("[]")
    rc = tick.main(["--self", "coord", "--checkout", CHECKOUT, "--state", str(env.d), "--claude", str(env.fake),
                    "--agents-file", str(env.agents_file), "--projects-root", str(env.tmp / "projects")])
    assert rc == 0
    assert capsys.readouterr().out.count("\n") == 1
