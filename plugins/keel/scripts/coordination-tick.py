#!/usr/bin/env python3
"""keel: the coordinator's tick, as one cheap tool call.

The coordinator's cron runs this every 30 minutes. It reads `claude agents --json --all` and the tail of each front's
transcript, and prints one line:

- `stop`: no live front of this project and none waiting for a limit; the coordinator deletes the cron.
- `resumed <name>`: a background front stopped by the usage limit, whose reset has passed and that the open state
  still cites, was resumed here with `claude --bg --resume` and the lean profile.
- `wake <name>`: a live front is blocked by a limit that has already reset; the coordinator sends it a message.
- `waiting <name> until <time>`: a front cut by the limit, before its reset.
- `self`: the coordinator's own previous turn ended in a limit error; it resumes the interrupted step.

A front counts when its cwd is the checkout or when the open state (`queue.md`, `window.md`,
`handoff/coordinator.md`) cites its name. Interactive sessions and the coordinator itself are not fronts.

Usage: coordination-tick.py --self <coordinator name> --checkout <path> --state <D> [--dry-run]
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

DEAD = ("done", "stopped", "failed")
OPEN_STATE = ("queue.md", "window.md", "handoff/coordinator.md", "fila.md", "janela.md", "handoff/coordenadora.md")
RETRY_LIMIT = 30 * 60        # do not resume or wake the same front twice inside this window
RETRY_BILLING = 2 * 3600     # a billing error has no reset time: retry at this cadence
MAX_AGE = 8 * 86400          # a limit cut older than the longest limit window is not a stall anymore
TAIL_BYTES = 512 * 1024
STATE_FILE = "tick.json"
HERE = os.path.dirname(os.path.abspath(__file__))
LEAN = os.path.join(HERE, "..", "skills", "coordinate-sessions", "templates", "background-session.settings.json")


def claude_binary():
    found = shutil.which("claude")
    if found:
        return found
    local = os.path.expanduser("~/.local/bin/claude")
    if os.path.exists(local):
        return local
    hits = sorted(glob.glob(os.path.expanduser(
        "~/.vscode*/extensions/anthropic.claude-code-*/resources/native-binary/claude")))
    return hits[-1] if hits else "claude"


def read_agents(args):
    try:
        if args.agents_file:
            with open(args.agents_file) as f:
                data = json.load(f)
        else:
            out = subprocess.run([args.claude, "agents", "--json", "--all"], capture_output=True, text=True,
                                 timeout=30)
            data = json.loads(out.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if isinstance(data, dict):
        data = data.get("agents", [])
    return [e for e in data if isinstance(e, dict)] if isinstance(data, list) else None


def open_state(state):
    parts = []
    for rel in OPEN_STATE:
        try:
            with open(os.path.join(state, rel), errors="replace") as f:
                parts.append(f.read())
        except OSError:
            pass
    return "\n".join(parts)


def cited(name, text):
    return bool(name) and re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", text) is not None


def transcript_path(root, sid):
    hits = glob.glob(os.path.join(glob.escape(root), "*", glob.escape(sid) + ".jsonl"))
    return max(hits, key=os.path.getmtime) if hits else None


def tail_entries(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - TAIL_BYTES))
            raw = f.read().decode("utf-8", errors="replace")
    except (OSError, TypeError):
        return []
    entries = []
    for line in raw.splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if isinstance(e, dict) and not e.get("isSidechain"):
            entries.append(e)
    return entries


def cut(entry):
    """('limit', resetsAt) / ('billing', None) when the entry is a usage error, else None."""
    if entry.get("type") != "assistant" or not entry.get("isApiErrorMessage"):
        return None
    if entry.get("error") == "rate_limit" or entry.get("apiError") == "usage_limit_reached":
        info = (entry.get("apiErrorParams") or {}).get("rate_limit_info") or entry.get("quotaLimits") or {}
        resets = info.get("resetsAt")
        return ("limit", resets if isinstance(resets, (int, float)) else None)
    if entry.get("error") == "billing_error":
        return ("billing", None)
    return None


def last_turn(path):
    for e in reversed(tail_entries(path)):
        if e.get("type") == "assistant":
            return cut(e)
    return None


def is_prompt(e):
    if e.get("type") != "user" or e.get("isMeta"):
        return False
    content = (e.get("message") or {}).get("content")
    if isinstance(content, str):
        return True
    return isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "text" for b in content)


def previous_turn_cut(path):
    """The coordinator's turn before the current prompt ended in a usage error."""
    entries = tail_entries(path)
    prompts = [i for i, e in enumerate(entries) if is_prompt(e)]
    if not prompts:
        return False
    for e in reversed(entries[:prompts[-1]]):
        if e.get("type") == "assistant":
            return cut(e) is not None
    return False


def is_live(e):
    return e.get("state") not in DEAD and ("pid" in e or e.get("status") in ("busy", "idle"))


def hhmm(epoch):
    return time.strftime("%H:%M", time.localtime(epoch))


def plan(agents, args, text, memo, now):
    """The tick's decisions, without side effects."""
    live, waiting, wake, resume, self_cut = [], [], [], [], False
    groups = {}
    for e in agents:
        name = e.get("name")
        if e.get("kind") == "interactive" or not name:
            if name == args.self and e.get("sessionId"):
                path = transcript_path(args.projects_root, e["sessionId"])
                self_cut = self_cut or (path is not None and previous_turn_cut(path))
            continue
        if name == args.self:
            path = transcript_path(args.projects_root, e.get("sessionId", ""))
            self_cut = self_cut or (path is not None and is_live(e) and previous_turn_cut(path))
            continue
        cwd = (e.get("cwd") or "").rstrip("/")
        mine = cwd == args.checkout or cwd.startswith(args.checkout + "/")
        if mine or cited(name, text):
            groups.setdefault(name, []).append(e)
    for name, entries in sorted(groups.items()):
        entries.sort(key=lambda x: x.get("startedAt") or 0)
        newest = entries[-1]
        path = transcript_path(args.projects_root, newest.get("sessionId", ""))
        stop = last_turn(path) if path else None
        recent = args.now is not None or (path is not None and now - os.path.getmtime(path) < MAX_AGE)
        if is_live(newest):
            if newest.get("state") == "blocked" and stop:
                kind, resets = stop
                if kind == "limit" and resets and resets > now:
                    waiting.append((name, resets))
                    continue
                gap = RETRY_BILLING if kind == "billing" else RETRY_LIMIT
                if now - memo.get(name, 0) >= gap:
                    wake.append(name)
            live.append(name)
            continue
        if newest.get("state") not in ("stopped", "failed") or not stop or not cited(name, text) or not recent:
            continue
        kind, resets = stop
        if kind == "limit" and resets and resets > now:
            waiting.append((name, resets))
            continue
        gap = RETRY_BILLING if kind == "billing" else RETRY_LIMIT
        if now - memo.get(name, 0) >= gap:
            resume.append((name, newest))
        else:
            waiting.append((name, memo[name] + gap))
    return live, waiting, wake, resume, self_cut


def launch(args, name, entry):
    prompt = (f"keel tick: the usage limit that stopped this session has reset. Continue the interrupted step from "
              f"your HANDOFF ({os.path.join(args.state, 'handoff', name + '.md')}); the coordinator is {args.self}.")
    cmd = [args.claude, "--bg", "--resume", entry["sessionId"], "-n", name, "--settings", args.settings,
           "--add-dir", args.state, "--permission-mode", "auto", prompt]
    cwd = entry.get("cwd") if os.path.isdir(entry.get("cwd") or "") else None
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def load_memo(state):
    try:
        with open(os.path.join(state, STATE_FILE)) as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(v, (int, float))} if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_memo(state, memo):
    tmp = os.path.join(state, STATE_FILE + ".tmp")
    with open(tmp, "w") as f:
        json.dump(memo, f)
    os.replace(tmp, os.path.join(state, STATE_FILE))


def run(argv):
    p = argparse.ArgumentParser(prog="coordination-tick.py")
    p.add_argument("--self", required=True, help="the coordinator's session name")
    p.add_argument("--checkout", required=True)
    p.add_argument("--state", required=True, help="the coordination state directory ($D)")
    p.add_argument("--settings", default=os.path.normpath(LEAN))
    p.add_argument("--claude", default=None)
    p.add_argument("--dry-run", action="store_true", help="list only: no launch, no state written")
    p.add_argument("--agents-file", help=argparse.SUPPRESS)
    p.add_argument("--projects-root", default=os.path.expanduser("~/.claude/projects"), help=argparse.SUPPRESS)
    p.add_argument("--now", type=float, default=None, help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    args.checkout = os.path.abspath(os.path.expanduser(args.checkout)).rstrip("/")
    args.state = os.path.abspath(os.path.expanduser(args.state))
    args.claude = args.claude or claude_binary()
    now = args.now if args.now is not None else time.time()

    agents = read_agents(args)
    if agents is None:
        return "keel tick: agents list unreadable; keep the cron and check `claude agents --json`"
    memo = load_memo(args.state)
    live, waiting, wake, resume, self_cut = plan(agents, args, open_state(args.state), memo, now)

    parts, resumed = [], []
    if live:
        parts.append(f"{len(live)} live ({', '.join(live)})")
    for name, entry in resume:
        if args.dry_run:
            parts.append(f"would resume {name}")
            continue
        memo[name] = now
        ok = launch(args, name, entry)
        resumed.append(name)
        parts.append(f"resumed {name}" if ok else f"resume failed {name}")
    for name in wake:
        if not args.dry_run:
            memo[name] = now
        parts.append(f"wake {name}")
    for name, until in waiting:
        parts.append(f"waiting {name} until {hhmm(until)}")
    if self_cut:
        parts.append("self: your previous turn was cut by the usage limit; resume the interrupted step")
    if (resume or wake) and not args.dry_run:
        save_memo(args.state, memo)
    if not (live or waiting or resumed or wake or (args.dry_run and resume)):
        return "keel tick: stop, no live front; delete this cron" + ("; " + parts[-1] if self_cut else "")
    return "keel tick: " + "; ".join(parts)


def main(argv=None):
    print(run(sys.argv[1:] if argv is None else argv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
