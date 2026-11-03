#!/usr/bin/env python3
"""Saves `high` as the effort of the session's model, so the main session doesn't start at a lower default.

Opus 5.5 and newer ignore a top-level `effortLevel` in the user's settings and start at their own default (`medium`
on the 5.5 family) until a level is saved for them under `modelSettings.<model id>`, which is what `/effort` writes. A
new model starts without an entry, so `/effort high` had to be run again on every release. At session start (`--hook`)
this reads the session's `model` from the hook input and, when nothing decides its effort yet, writes
`modelSettings.<id>.effortLevel = "high"` into the user's `settings.json`, with a backup in ~/.claude/backups/, and
prints one line. It applies from the next session on: the open one keeps the effort it started with.

The SessionStart input often has no `model` (measured on 2.1.317: absent at `startup`, in the CLI and in VS Code), and
`model` in settings is usually an alias (`opus[1m]`). Then the id comes from the newest session transcript under
`<home>/projects`: the model of its last main-thread assistant message, the id the alias resolved to. A new model is
picked up from its first session's transcript, so its second session on is at `high`.

It never writes over a decision: a saved level for that model (a `/effort low` included), `CLAUDE_CODE_EFFORT_LEVEL`,
and an `effortLevel` or an entry for that model in managed settings or in the project's settings all win. It only acts
on a Claude model id from 5.5 on (older ones honor the top-level `effortLevel`, and some default above `high`), and it
leaves a settings file that does not parse as JSON alone.

Usage:
  effort.py --hook       SessionStart: saves `high` for the session's model when nothing decides it
  effort.py status       shows what decides the effort of each model saved in the user's settings
  effort.py --self-test  runs the scenarios in a temporary home
"""
import datetime
import json
import os
import re
import shutil
import sys
import tempfile

LEVEL = "high"
MANAGED = (
    "/Library/Application Support/ClaudeCode/managed-settings.json",
    "/etc/claude-code/managed-settings.json",
    r"C:\Program Files\ClaudeCode\managed-settings.json",
)
PROJECT = (os.path.join(".claude", "settings.json"), os.path.join(".claude", "settings.local.json"))
MODEL_ID = re.compile(r"^claude-[a-z]+-(\d+)-(\d+)$")
FIRST_VERSION = (5, 5)


def home():
    return os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude")


def user_settings():
    return os.path.join(home(), "settings.json")


def canonical(model):
    """The `modelSettings` key of a model id: no `[1m]` suffix, no date suffix. None when it isn't a Claude id >= 5.5."""
    if not isinstance(model, str):
        return None
    key = re.sub(r"\[[^\]]*\]$", "", model.strip().lower())
    key = re.sub(r"-\d{8}$", "", key)
    match = MODEL_ID.match(key)
    if not match or (int(match.group(1)), int(match.group(2))) < FIRST_VERSION:
        return None
    return key


def transcript_model(skip=None, files=20, tail=1 << 20):
    """The canonical id of the last main-thread assistant message in the newest transcripts; None when none has one."""
    root = os.path.join(home(), "projects")
    try:
        paths = [os.path.join(root, folder, name) for folder in os.listdir(root)
                 if os.path.isdir(os.path.join(root, folder))
                 for name in os.listdir(os.path.join(root, folder)) if name.endswith(".jsonl")]
    except OSError:
        return None
    skip = os.path.abspath(skip) if skip else None
    paths = sorted((path for path in paths if os.path.abspath(path) != skip), key=mtime, reverse=True)
    for path in paths[:files]:
        try:
            with open(path, "rb") as handle:
                handle.seek(max(0, os.path.getsize(path) - tail))
                lines = handle.read().decode("utf-8", "replace").splitlines()
        except OSError:
            continue
        for line in reversed(lines):
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not isinstance(entry, dict) or entry.get("type") != "assistant" or entry.get("isSidechain"):
                continue
            key = canonical((entry.get("message") or {}).get("model"))
            if key:
                return key
    return None


def mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0


def load(path):
    """(text, data) of a settings file: (None, {}) when missing, (text, None) when it does not parse as an object."""
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return None, {}
    try:
        data = json.loads(text)
    except ValueError:
        return text, None
    return text, data if isinstance(data, dict) else None


def saved_level(data, key):
    """The level a settings object saves for that model, under any spelling of its id; None when it saves none."""
    entries = (data or {}).get("modelSettings")
    if not isinstance(entries, dict):
        return None
    for name, entry in entries.items():
        if canonical(name) == key and isinstance(entry, dict) and entry.get("effortLevel"):
            return entry["effortLevel"]
    return None


def outside_decision(key, cwd):
    """Where the effort of that model is decided outside the user's file: the env var, managed or project settings."""
    if os.environ.get("CLAUDE_CODE_EFFORT_LEVEL"):
        return "CLAUDE_CODE_EFFORT_LEVEL"
    paths = list(MANAGED) + [os.path.join(cwd, relative) for relative in PROJECT]
    for path in paths:
        data = load(path)[1]
        if data and (data.get("effortLevel") or saved_level(data, key)):
            return path
    return None


def write(key):
    """Saves LEVEL for that model in the user's settings; returns (ok, message)."""
    path = user_settings()
    text, data = load(path)
    if data is None:
        return False, "{} does not parse as JSON; left untouched.".format(path)
    entries = data.setdefault("modelSettings", {})
    if not isinstance(entries, dict):
        return False, "modelSettings in {} is not an object; left untouched.".format(path)
    entry = entries.get(key)
    if not isinstance(entry, dict):
        entry = entries[key] = {}
    entry["effortLevel"] = LEVEL
    backup = None
    if text is not None:
        backup = os.path.join(home(), "backups",
                              "keel-settings-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".json")
        os.makedirs(os.path.dirname(backup), exist_ok=True)
        shutil.copy2(path, backup)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    handle, fresh = tempfile.mkstemp(prefix=".settings-", suffix=".json", dir=os.path.dirname(path))
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    if load(path)[0] != text:
        os.unlink(fresh)
        return False, "{} changed while it was being written; try again.".format(path)
    if text is not None:
        shutil.copymode(path, fresh)
    os.replace(fresh, path)
    return True, "effort `{}` saved for {} in {}{}.".format(
        LEVEL, key, path, " (backup: {})".format(backup) if backup else "")


def hook(event):
    event = event or {}
    key = canonical(event.get("model")) or transcript_model(event.get("transcript_path"))
    if not key:
        return ""
    if outside_decision(key, event.get("cwd") or os.getcwd()):
        return ""
    data = load(user_settings())[1]
    if data is None or saved_level(data, key):
        return ""
    ok, message = write(key)
    if not ok:
        return ""
    return ("PLUGIN NOTICE: keel's effort hook set it: " + message + " Tell the user in one line: it applies from the "
            "next session on (this one keeps its effort), and `/effort <level>` saves another level for this model.\n")


def status(cwd):
    lines = []
    if os.environ.get("CLAUDE_CODE_EFFORT_LEVEL"):
        lines.append("CLAUDE_CODE_EFFORT_LEVEL={} decides every session (and overrides agent frontmatter).".format(
            os.environ["CLAUDE_CODE_EFFORT_LEVEL"]))
    for path in list(MANAGED) + [os.path.join(cwd, relative) for relative in PROJECT]:
        data = load(path)[1]
        if data and data.get("effortLevel"):
            lines.append("effortLevel `{}` in {} applies to every model.".format(data["effortLevel"], path))
    entries = (load(user_settings())[1] or {}).get("modelSettings")
    for name, entry in sorted(entries.items() if isinstance(entries, dict) else []):
        if isinstance(entry, dict) and entry.get("effortLevel"):
            lines.append("{}: `{}` (saved in {}).".format(name, entry["effortLevel"], user_settings()))
    return "\n".join(lines) or "No effort saved: each model starts at its own default until a session saves `high`."


def main():
    args = sys.argv[1:]
    if args == ["--self-test"]:
        sys.exit(self_test())
    if args == ["--hook"]:
        try:
            try:
                event = json.load(sys.stdin)
            except ValueError:
                event = {}
            sys.stdout.write(hook(event if isinstance(event, dict) else {}))
        except Exception:
            pass
        return
    print(status(os.getcwd()))


def self_test():
    failures = []

    def check(label, condition):
        if not condition:
            failures.append(label)

    sandbox = tempfile.mkdtemp(prefix="keel-effort-")
    saved = {key: os.environ.get(key) for key in ("CLAUDE_CONFIG_DIR", "CLAUDE_CODE_EFFORT_LEVEL")}
    os.environ.pop("CLAUDE_CODE_EFFORT_LEVEL", None)

    def put(path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)

    def fresh_home(label, settings=None):
        root = os.path.join(sandbox, label)
        os.environ["CLAUDE_CONFIG_DIR"] = root
        os.makedirs(root)
        if settings is not None:
            put(user_settings(), settings)
        project = os.path.join(root, "project")
        os.makedirs(project)
        return project

    def level(key):
        return saved_level(load(user_settings())[1], key)

    try:
        check("canonical: [1m] and date suffix dropped", canonical("claude-opus-5-6[1m]") == "claude-opus-5-6"
              and canonical("claude-sonnet-5-5-20261101") == "claude-sonnet-5-5")
        check("canonical: older, alias and provider ids skipped", canonical("claude-opus-4-7") is None
              and canonical("opus") is None and canonical("us.anthropic.claude-opus-5-5-v1:0") is None
              and canonical(None) is None)

        project = fresh_home("new-model", json.dumps({"theme": "dark", "effortLevel": "high", "modelSettings": {
            "claude-opus-5-5": {"effortLevel": "high"}}}, indent=2))
        notice = hook({"model": "claude-opus-5-6[1m]", "cwd": project})
        data = load(user_settings())[1]
        check("new model: saved high, the rest kept", notice.startswith("PLUGIN NOTICE")
              and level("claude-opus-5-6") == "high" and data["theme"] == "dark"
              and data["modelSettings"]["claude-opus-5-5"] == {"effortLevel": "high"})
        check("new model: backup kept", len(os.listdir(os.path.join(home(), "backups"))) == 1)
        check("second start: silent", hook({"model": "claude-opus-5-6", "cwd": project}) == "")

        project = fresh_home("chosen", json.dumps({"modelSettings": {"claude-opus-5-6[1m]": {"effortLevel": "low"}}}))
        check("a saved level under another spelling: respected",
              hook({"model": "claude-opus-5-6", "cwd": project}) == "" and level("claude-opus-5-6") == "low")

        project = fresh_home("other-keys", json.dumps({"modelSettings": {"claude-opus-5-6": {"other": 1}}}))
        hook({"model": "claude-opus-5-6", "cwd": project})
        check("entry without a level: level added, keys kept",
              load(user_settings())[1]["modelSettings"]["claude-opus-5-6"] == {"other": 1, "effortLevel": "high"})

        project = fresh_home("no-file")
        hook({"model": "claude-opus-5-5", "cwd": project})
        check("no settings file: created", level("claude-opus-5-5") == "high")

        project = fresh_home("no-model", json.dumps({}))
        check("no model in the input nor a transcript: nothing",
              hook({"cwd": project}) == "" and load(user_settings())[1] == {})

        project = fresh_home("from-transcript", json.dumps({}))
        lines = [{"type": "assistant", "message": {"model": "claude-opus-5-6"}},
                 {"type": "assistant", "isSidechain": True, "message": {"model": "claude-haiku-5-5"}},
                 {"type": "assistant", "message": {"model": "<synthetic>"}}, {"type": "user"}]
        put(os.path.join(home(), "projects", "-repo", "old.jsonl"),
            json.dumps({"type": "assistant", "message": {"model": "claude-opus-5-5"}}) + "\n")
        put(os.path.join(home(), "projects", "-repo", "new.jsonl"), "\n".join(json.dumps(x) for x in lines) + "\nnot json\n")
        os.utime(os.path.join(home(), "projects", "-repo", "old.jsonl"), (1, 1))
        current = os.path.join(home(), "projects", "-repo", "current.jsonl")
        put(current, json.dumps({"type": "assistant", "message": {"model": "claude-sonnet-5-5"}}) + "\n")
        hook({"cwd": project, "transcript_path": current})
        check("no model in the input: the newest transcript's main-thread model, the session's own skipped",
              level("claude-opus-5-6") == "high" and level("claude-sonnet-5-5") is None
              and level("claude-haiku-5-5") is None and level("claude-opus-5-5") is None)

        project = fresh_home("old-model", json.dumps({}))
        check("model before 5.5: nothing",
              hook({"model": "claude-opus-4-7", "cwd": project}) == "" and load(user_settings())[1] == {})

        project = fresh_home("broken", '{"theme": "dark",}')
        check("broken JSON: untouched", hook({"model": "claude-opus-5-6", "cwd": project}) == ""
              and write("claude-opus-5-6")[0] is False and load(user_settings())[0] == '{"theme": "dark",}')

        project = fresh_home("by-project", json.dumps({}))
        put(os.path.join(project, ".claude", "settings.json"), json.dumps({"effortLevel": "medium"}))
        check("project effortLevel decides: user file untouched",
              hook({"model": "claude-opus-5-6", "cwd": project}) == "" and load(user_settings())[1] == {})

        project = fresh_home("by-local", json.dumps({}))
        put(os.path.join(project, ".claude", "settings.local.json"),
            json.dumps({"modelSettings": {"claude-opus-5-6": {"effortLevel": "xhigh"}}}))
        check("local entry for the model decides: user file untouched",
              hook({"model": "claude-opus-5-6", "cwd": project}) == "" and load(user_settings())[1] == {})

        project = fresh_home("by-env", json.dumps({}))
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "medium"
        check("env var decides: user file untouched",
              hook({"model": "claude-opus-5-6", "cwd": project}) == "" and load(user_settings())[1] == {})
        os.environ.pop("CLAUDE_CODE_EFFORT_LEVEL", None)
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(sandbox, ignore_errors=True)

    print("{} failure(s){}".format(len(failures), ": " + "; ".join(failures) if failures else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    main()
