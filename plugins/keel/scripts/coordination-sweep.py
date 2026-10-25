#!/usr/bin/env python3
"""SessionStart: removes what the coordination of background sessions leaves behind, so nobody has to remember.

In every `~/.claude/coordination/<project>/`:
- `logs/<session>/` and `logs/<session>.prompt.md`: after 3 days without a change;
- `handoff/<session>.md` (not `coordinator.md`) and `prompts/<front>.md` (not the shared `_*.md`): after 14 days;
- `queue-archive/*.md`: after 90 days.
What stays at any age: whatever belongs to a session still alive (`claude agents --json`; when the list can't be read,
age alone decides), and whatever the open state cites by path (`logs/<name>`, `prompts/<name>`, `handoff/<name>` in
`queue.md`, `window.md` or `handoff/coordinator.md`). An open-state file that can't be read keeps the whole project.
`queue.md`, `window.md`, `handoff/coordinator.md` and `profile/` never go: they hold what is open and have a cap.

In the session's repo: the safety refs `refs/keel/backup/<YYYY-MM-DD>-<what>` older than 14 days, and
`git worktree prune --expire` for the worktrees whose directory has been gone for 14 days.

It prints one line only when it removed something. An internal failure stays quiet.

`--close <session> --state <D> [--checkout <repo>] [--sha <sha>...] [--worktree <path>...] [--force-worktree] [--sent]
[--dry-run]` is the coordinator's close of one front, at once and regardless of age: `logs/<session>/`, the assembled
prompt, `prompts/<session>.md` (and the front's `prompts/<front>.md` when it is not a phase), `handoff/<session>.md`,
the scratch of its job, its worktrees and branch in the checkout, and its lines in `window.md`; `queue.md` keeps one
`<session> <sessionId> <shas> closed` line. It refuses a live session or an unreadable agents list, and refuses when
the checkout's `git status` lists a file the `--sha` commits touched (the front wrote in the checkout). It keeps what
the open state or a live front cites, keeps the owner's media until `--sent`, forces out a worktree only when its HEAD
is on a remote branch and no tracked file changed (untracked leftovers need `--force-worktree`), fast-forwards the
checkout's branch to its upstream when no tracked file changed in it, and shows (never runs) the profile's cleanup
list.

Usage: no argument runs the sweep; `--self-test` runs the scenarios in a temporary home.
"""
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

DAY = 86400
LOGS_DAYS = 3
SESSION_DAYS = 14
ARCHIVE_DAYS = 90
BACKUP_REFS = "refs/keel/backup/"
BACKUP_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")
PROMPT_SUFFIX = ".prompt.md"
# The coordination skill writes to this literal path, whatever CLAUDE_CONFIG_DIR says.
STATE_ROOT = "~/.claude/coordination"
OPEN_STATE = ("queue.md", "window.md", os.path.join("handoff", "coordinator.md"),
              "fila.md", "janela.md", os.path.join("handoff", "coordenadora.md"))


def claude_binary():
    found = shutil.which("claude")
    if found:
        return found
    candidates = [os.path.expanduser("~/.local/bin/claude")]
    candidates += sorted(glob.glob(os.path.expanduser(
        "~/.vscode*/extensions/anthropic.claude-code-*/resources/native-binary/claude")))[-1:]
    return next((path for path in candidates if os.path.isfile(path)), None)


def live_names():
    """The names of the sessions alive on this machine, or None when the list can't be read."""
    binary = claude_binary()
    if not binary:
        return None
    try:
        result = subprocess.run([binary, "agents", "--json"], capture_output=True, text=True, timeout=8)
        sessions = json.loads(result.stdout) if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if not isinstance(sessions, list):
        return None
    return {item["name"] for item in sessions if isinstance(item, dict) and isinstance(item.get("name"), str)}


def newest_change(path):
    """The latest mtime of the entry and everything under it, without following links."""
    newest = os.lstat(path).st_mtime
    if os.path.isdir(path) and not os.path.islink(path):
        for base, dirs, files in os.walk(path):
            for name in dirs + files:
                try:
                    newest = max(newest, os.lstat(os.path.join(base, name)).st_mtime)
                except OSError:
                    pass
    return newest


def size_of(path):
    if os.path.islink(path) or not os.path.isdir(path):
        return os.lstat(path).st_size
    total = 0
    for base, _, files in os.walk(path):
        for name in files:
            try:
                total += os.lstat(os.path.join(base, name)).st_size
            except OSError:
                pass
    return total


def owner(path):
    name = os.path.basename(path)
    if name.endswith(PROMPT_SUFFIX):
        return name[: -len(PROMPT_SUFFIX)]
    if os.path.isdir(path) or name.startswith("."):
        return name
    return os.path.splitext(name)[0]


def is_live(key, live):
    """A session is `<prefix>-<front>[-phase<n>]`: a front's prompt belongs to the live session that carries its name."""
    if live is None:
        return False
    tail = re.compile(r"(^|-)" + re.escape(key) + r"(-phase\d+)?$")
    return any(tail.search(name) for name in live)


def open_state(state):
    """The text of the files that hold what is open, or None when one exists and can't be read."""
    texts = []
    for name in OPEN_STATE:
        path = os.path.join(state, name)
        if not os.path.lexists(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                texts.append(handle.read())
        except OSError:
            return None
    return "\n".join(texts)


def candidates(state):
    """(path, owner, retention in days) of what may go, per folder of the coordination state."""
    folders = (
        ("logs", LOGS_DAYS, lambda name: True),
        ("handoff", SESSION_DAYS, lambda name: name not in ("coordinator.md", "coordenadora.md")),
        ("prompts", SESSION_DAYS, lambda name: not name.startswith("_")),
        ("queue-archive", ARCHIVE_DAYS, lambda name: True),
    )
    for folder, days, allowed in folders:
        base = os.path.join(state, folder)
        if not os.path.isdir(base) or os.path.islink(base):
            continue
        for name in sorted(os.listdir(base)):
            if allowed(name):
                path = os.path.join(base, name)
                yield path, folder + "/" + name, owner(path), days


def sweep_state(root, live, now):
    """Removes what expired under `root`; returns [(path, bytes)] of what went."""
    removed = []
    if not os.path.isdir(root) or os.path.islink(root):
        return removed
    for project in sorted(os.listdir(root)):
        state = os.path.join(root, project)
        if not os.path.isdir(state) or os.path.islink(state):
            continue
        cited = open_state(state)
        if cited is None:
            continue
        for path, relative, key, days in candidates(state):
            try:
                if relative in cited or is_live(key, live) or now - newest_change(path) < days * DAY:
                    continue
                size = size_of(path)
                if os.path.isdir(path) and not os.path.islink(path):
                    shutil.rmtree(path)
                else:
                    os.unlink(path)
                removed.append((path, size))
            except OSError:
                pass
    return removed


def git(cwd, *args, timeout=8):
    return subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True, timeout=timeout)


def sweep_repo(cwd, today):
    """Removes the expired safety refs and prunes the gone worktrees; returns the refs that went."""
    removed = []
    try:
        if git(cwd, "rev-parse", "--git-dir").returncode != 0:
            return removed
        refs = git(cwd, "for-each-ref", "--format=%(refname)", BACKUP_REFS).stdout.split()
        for ref in refs:
            match = BACKUP_DATE.match(ref[len(BACKUP_REFS):])
            if not match:
                continue
            try:
                made = datetime.date.fromisoformat(match.group(1))
            except ValueError:
                continue
            if (today - made).days >= SESSION_DAYS and git(cwd, "update-ref", "-d", ref).returncode == 0:
                removed.append(ref)
        git(cwd, "worktree", "prune", "--expire", "{}.days.ago".format(SESSION_DAYS))
    except (OSError, subprocess.SubprocessError):
        pass
    return removed


def report(files, refs):
    if not files and not refs:
        return ""
    parts = []
    if files:
        megabytes = sum(size for _, size in files) / 1048576
        parts.append("{} expired item(s) from ~/.claude/coordination ({:.1f} MB)".format(len(files), megabytes))
    if refs:
        parts.append("{} expired safety ref(s) under {}".format(len(refs), BACKUP_REFS))
    return "keel sweep: removed " + " and ".join(parts) + ".\n"


# --- --close <session>: everything a closed front leaves, at once -----------------------------------------------------

OWNER_MEDIA = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".mp4", ".webm", ".mov", ".pdf", ".zip")
DEAD_STATES = ("done", "stopped", "failed")
PHASE = re.compile(r"-(phase|fase)\d+$")
CLEANUP_HEADINGS = ("## cleanup at front close", "## limpeza ao fechar a frente")


def cites(name, text):
    return re.search(r"(?<![\w.-])" + re.escape(name) + r"(?![\w-])", text) is not None


def read_agents(path):
    """The full agents list (live and dead), or None when it can't be read."""
    try:
        if path:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        else:
            binary = claude_binary()
            if not binary:
                return None
            result = subprocess.run([binary, "agents", "--json", "--all"], capture_output=True, text=True, timeout=30)
            data = json.loads(result.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else None


def agent_live(item):
    return item.get("state") not in DEAD_STATES and ("pid" in item or item.get("status") in ("busy", "idle"))


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def close_targets(state, session):
    """(relative path, absolute path) of the coordination state that belongs to the session."""
    names = [os.path.join("logs", session), os.path.join("logs", session + PROMPT_SUFFIX),
             os.path.join("prompts", session + ".md"), os.path.join("handoff", session + ".md")]
    if not PHASE.search(session):
        for name in sorted(os.listdir(os.path.join(state, "prompts"))) if os.path.isdir(
                os.path.join(state, "prompts")) else []:
            front = name[:-3] if name.endswith(".md") else None
            if front and not front.startswith("_") and front != session and session.endswith("-" + front):
                names.append(os.path.join("prompts", name))
    protected = ("handoff/coordinator.md", "handoff/coordenadora.md")
    return [(rel, os.path.join(state, rel)) for rel in names
            if rel.replace(os.sep, "/") not in protected and os.path.lexists(os.path.join(state, rel))]


def remove_entry(path, keep_media, dry_run):
    """Removes a file or a tree; with keep_media the owner's files stay. Returns (bytes, kept media paths)."""
    kept, size = [], 0
    if os.path.isdir(path) and not os.path.islink(path):
        for base, dirs, files in os.walk(path, topdown=False):
            for name in files:
                full = os.path.join(base, name)
                if keep_media and name.lower().endswith(OWNER_MEDIA):
                    kept.append(full)
                    continue
                size += os.lstat(full).st_size
                if not dry_run:
                    os.unlink(full)
            for name in dirs:
                full = os.path.join(base, name)
                if not dry_run and os.path.islink(full):
                    os.unlink(full)
                elif not dry_run and not os.listdir(full):
                    os.rmdir(full)
        if not dry_run and not kept:
            shutil.rmtree(path, ignore_errors=True)
        return size, kept
    if keep_media and path.lower().endswith(OWNER_MEDIA):
        return 0, [path]
    size = os.lstat(path).st_size
    if not dry_run:
        os.unlink(path)
    return size, kept


def edit_window(state, session, others, dry_run):
    """Drops the window lines that cite only this session; returns (dropped, left) lines."""
    path = os.path.join(state, "window.md")
    if not os.path.isfile(path):
        return [], []
    lines = read_text(path).splitlines(keepends=True)
    keep, dropped, left = [], [], []
    for line in lines:
        if cites(session, line):
            if any(cites(other, line) for other in others):
                left.append(line.strip())
                keep.append(line)
            else:
                dropped.append(line.strip())
            continue
        keep.append(line)
    if dropped and not dry_run:
        with open(path, "w", encoding="utf-8") as handle:
            handle.writelines(keep)
    return dropped, left


def edit_queue(state, session, session_id, shas, dry_run):
    """Leaves one `<session> <sessionId> <shas> closed <date>` line; returns it and the other lines that cite it."""
    path = os.path.join(state, "queue.md")
    lines = read_text(path).splitlines(keepends=True)
    others = [line.strip() for line in lines if cites(session, line) and not line.startswith(session + " ")]
    if not shas:
        return None, others
    entry = " ".join([session, session_id or "-"] + list(shas) + ["closed", datetime.date.today().isoformat()])
    body = [line for line in lines if not line.startswith(session + " ")]
    if body and not body[-1].endswith("\n"):
        body[-1] += "\n"
    if not dry_run:
        with open(path, "w", encoding="utf-8") as handle:
            handle.writelines(body + [entry + "\n"])
    return entry, others


def dirty_paths(repo, tracked_only=False):
    """The paths `git status` lists in the repo (both sides of a rename), or None when git fails."""
    args = ["status", "--porcelain", "-z"] + (["--untracked-files=no"] if tracked_only else [])
    result = git(repo, *args, timeout=60)
    if result.returncode != 0:
        return None
    paths, fields = [], result.stdout.split("\0")
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        paths.append(entry[3:])
        if entry[0] in "RC":
            paths.append(fields[i])
            i += 1
    return paths


def commit_paths(repo, shas):
    """The paths the commits touched, or None when one of them can't be read."""
    paths = set()
    for sha in shas:
        result = git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", "-z", sha)
        if result.returncode != 0:
            return None
        paths.update(p for p in result.stdout.split("\0") if p)
    return paths


def published(worktree, upstream=None, shas=()):
    """True when no commit of the worktree's HEAD would be lost: each is on a remote branch, has its patch on the
    upstream (`git cherry`, a cherry-pick onto a newer tip) or is one of the `--sha` the coordinator integrated."""
    pending = git(worktree, "rev-list", "HEAD", "--not", "--remotes")
    if pending.returncode != 0:
        return False
    left = set(pending.stdout.split())
    if left and upstream:
        cherry = git(worktree, "cherry", upstream, "HEAD")
        if cherry.returncode == 0:
            left -= {line[2:] for line in cherry.stdout.splitlines() if line.startswith("- ")}
    return not {sha for sha in left if not any(sha.startswith(given) for given in shas if len(given) >= 7)}


def remove_worktree(checkout, path, branch, force, upstream=None, shas=()):
    """Removes a front's worktree; returns None, or why it was left. A detached HEAD on no remote branch stays: removing
    it would leave its commits reachable only by the reflog."""
    if git(path, "rev-parse", "--git-dir").returncode != 0:
        return "unreadable"
    if not branch and not published(path, upstream, shas):
        return "its detached HEAD has commits on no remote branch and not given by --sha: integrate them first"
    if git(checkout, "worktree", "remove", path, timeout=300).returncode == 0:
        return None
    if not published(path, upstream, shas):
        return "its HEAD has commits on no remote branch and not given by --sha: integrate them first"
    tracked = dirty_paths(path, tracked_only=True)
    if tracked is None or tracked:
        return "uncommitted changes in {} tracked file(s)".format("?" if tracked is None else len(tracked))
    untracked = git(path, "ls-files", "--others", "--exclude-standard", "-z")
    loose = [p for p in untracked.stdout.split("\0") if p] if untracked.returncode == 0 else None
    if loose is None or (loose and not force):
        shown = "?" if loose is None else ", ".join(loose[:5]) + (" and {} more".format(len(loose) - 5)
                                                                    if len(loose) > 5 else "")
        return "untracked files not ignored ({}); rerun with --force-worktree once they are known to be leftovers" \
            .format(shown)
    if git(checkout, "worktree", "remove", "--force", path, timeout=300).returncode != 0:
        return "locked"
    return None


def fast_forward(checkout, dry_run):
    """Moves the checkout's branch to its upstream when it is clean and behind; returns the report line or None."""
    branch = git(checkout, "symbolic-ref", "--quiet", "--short", "HEAD")
    upstream = git(checkout, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if branch.returncode != 0 or upstream.returncode != 0:
        return None
    upstream = upstream.stdout.strip()
    behind = git(checkout, "rev-list", "--count", "HEAD.." + upstream)
    ahead = git(checkout, "rev-list", "--count", upstream + "..HEAD")
    if behind.returncode != 0 or ahead.returncode != 0 or behind.stdout.strip() == "0":
        return None
    count = behind.stdout.strip()
    if ahead.stdout.strip() != "0":
        return "checkout: {} is {} behind and {} ahead of {}; not moved (diverged)".format(
            branch.stdout.strip(), count, ahead.stdout.strip(), upstream)
    tracked = dirty_paths(checkout, tracked_only=True)
    if tracked is None or tracked:
        return "checkout: {} behind {}, not moved: {} tracked file(s) changed in it".format(
            count, upstream, "?" if tracked is None else len(tracked))
    if dry_run:
        return "checkout: would fast-forward {} by {} to {}".format(branch.stdout.strip(), count, upstream)
    if git(checkout, "merge", "--ff-only", "--quiet", upstream, timeout=300).returncode != 0:
        return "checkout: fast-forward to {} failed (an untracked file in the way?); not moved".format(upstream)
    return "checkout: fast-forwarded {} by {} to {}".format(branch.stdout.strip(), count, upstream)


def front_worktrees(checkout, session, job_dirs, named=()):
    """(path, branch) of the checkout's worktrees that belong to the session, or that `--worktree` named."""
    result = git(checkout, "worktree", "list", "--porcelain")
    if result.returncode != 0:
        return []
    found, path, branch = [], None, None
    for line in result.stdout.splitlines() + [""]:
        if line.startswith("worktree "):
            path, branch = line[len("worktree "):], None
        elif line.startswith("branch "):
            branch = line[len("branch refs/heads/"):]
        elif not line and path:
            mine = os.path.basename(path.rstrip("/")) == session or branch in (session, "worktree-" + session) \
                or any(path.startswith(job + os.sep) for job in job_dirs) \
                or os.path.realpath(path) in named
            if mine and os.path.realpath(path) != os.path.realpath(checkout):
                found.append((path, branch))
            path, branch = None, None
    return found


def profile_cleanup(checkout, session):
    """The commands of the profile's cleanup section, with the session name in place."""
    text = read_text(os.path.join(checkout, ".claude", "coordination", "profile.md"))
    commands, inside = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip().lower() in CLEANUP_HEADINGS
            continue
        if inside:
            commands += [c.replace("<SESSION-NAME>", session) for c in re.findall(r"`([^`]+)`", line)[:1]]
    return commands


def close(argv):
    import argparse
    parser = argparse.ArgumentParser(prog="coordination-sweep.py --close")
    parser.add_argument("--close", required=True, metavar="SESSION")
    parser.add_argument("--state", required=True, help="the coordination state directory ($D)")
    parser.add_argument("--checkout", help="the project checkout: its status, its worktrees, its fast-forward and the "
                        "profile's cleanup list")
    parser.add_argument("--worktree", nargs="+", default=[], help="the front's worktrees, when not named after it")
    parser.add_argument("--force-worktree", action="store_true",
                        help="discard the untracked files left in a published, committed worktree")
    parser.add_argument("--sha", nargs="+", default=[], help="the front's commits, kept as one line in queue.md")
    parser.add_argument("--sent", action="store_true", help="the owner's files were sent: remove them too")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--agents-file", help=argparse.SUPPRESS)
    parser.add_argument("--jobs-root", default=os.path.expanduser("~/.claude/jobs"), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    session, state, dry = args.close, os.path.abspath(os.path.expanduser(args.state)), args.dry_run
    head = "keel close {}{}:".format(session, " (dry run)" if dry else "")

    agents = read_agents(args.agents_file)
    if agents is None:
        return head + " agents list unreadable; nothing removed (a live front could lose its state)"
    mine = sorted((a for a in agents if a.get("name") == session), key=lambda a: a.get("startedAt") or 0)
    if any(agent_live(a) for a in mine):
        return head + " the session is still live; stop it first (`claude stop <id>`), nothing removed"
    others = {a["name"] for a in agents if agent_live(a) and isinstance(a.get("name"), str) and a["name"] != session}
    session_id = mine[-1].get("sessionId") if mine else None

    checkout = os.path.abspath(os.path.expanduser(args.checkout)) if args.checkout else None
    if checkout and git(checkout, "rev-parse", "--git-dir").returncode == 0:
        touched = commit_paths(checkout, args.sha) if args.sha else set()
        dirty = dirty_paths(checkout)
        if touched is None:
            return head + " a --sha is not in the checkout; fetch it first, nothing removed"
        if dirty is None:
            return head + " git status of the checkout failed; nothing removed"
        clash = sorted(set(dirty) & touched)
        if clash:
            shown = ", ".join(clash[:8]) + (" and {} more".format(len(clash) - 8) if len(clash) > 8 else "")
            return (head + " the checkout has {} file(s) the front committed, changed or untracked in it: {}. The front "
                    "wrote in the checkout; compare them with the commit, restore those that match and rerun. "
                    "Nothing removed").format(len(clash), shown)

    guard = open_state(state)
    if guard is None:
        return head + " open state unreadable; nothing removed"
    for other in sorted(others):
        guard += "\n" + read_text(os.path.join(state, "handoff", other + ".md"))
        guard += "\n" + read_text(os.path.join(state, "prompts", other + ".md"))

    verb = "would remove" if dry else "removed"
    removed, kept, media = [], [], []
    for rel, path in close_targets(state, session):
        if rel.replace(os.sep, "/") in guard:
            kept.append(rel + " (cited by the open state or a live front)")
            continue
        try:
            size, owner_files = remove_entry(path, not args.sent, dry)
        except OSError as error:
            kept.append("{} ({})".format(rel, error.strerror))
            continue
        removed.append("{} ({:.1f} KB{})".format(rel, size / 1024, ", owner files kept" if owner_files else ""))
        media += [os.path.relpath(f, state) for f in owner_files]

    job_dirs = [os.path.join(args.jobs_root, a["sessionId"][:8]) for a in mine if a.get("sessionId")]
    for job in job_dirs:
        scratch = os.path.join(job, "tmp")
        if os.path.isdir(scratch) and os.listdir(scratch):
            if not dry:
                for name in os.listdir(scratch):
                    target = os.path.join(scratch, name)
                    shutil.rmtree(target) if os.path.isdir(target) and not os.path.islink(target) else os.unlink(target)
            removed.append("scratch {}".format(scratch))

    lines = []
    if checkout:
        named = {os.path.realpath(os.path.expanduser(w)) for w in args.worktree}
        upstream = git(checkout, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        upstream = upstream.stdout.strip() if upstream.returncode == 0 else None
        for path, branch in front_worktrees(checkout, session, job_dirs, named):
            if dry:
                removed.append("worktree {}".format(path))
                continue
            why = remove_worktree(checkout, path, branch, args.force_worktree, upstream, args.sha)
            if why:
                lines.append("worktree left ({}): {}".format(why, path))
                continue
            removed.append("worktree {}".format(path))
            if branch and git(checkout, "branch", "-d", branch).returncode == 0:
                removed.append("branch {}".format(branch))
            elif branch:
                lines.append("branch {} left (not merged into HEAD)".format(branch))
        moved = fast_forward(checkout, dry)
        if moved:
            lines.append(moved)
        cleanup = profile_cleanup(checkout, session)
        if cleanup:
            lines.append("run (the profile's cleanup list): " + "; ".join(cleanup))

    dropped, left = edit_window(state, session, others, dry)
    if dropped:
        lines.append("window.md: {} {} line(s): {}".format(verb, len(dropped), " / ".join(dropped)))
    if left:
        lines.append("window.md: shared line(s) left, edit by hand: " + " / ".join(left))
    entry, cited_lines = edit_queue(state, session, session_id, args.sha, dry)
    if entry:
        lines.append("queue.md: " + entry)
    if cited_lines:
        lines.append("queue.md still cites it ({} line(s)): move what closed to queue-archive/".format(len(cited_lines)))
    if media:
        shown = ", ".join(media[:5]) + (" and {} more".format(len(media) - 5) if len(media) > 5 else "")
        lines.append("owner files kept ({}): {}; send what the owner needs with SendUserFile, then rerun with --sent"
                     .format(len(media), shown))
    out = [head + " " + ("{} {}".format(verb, ", ".join(removed)) if removed else "nothing to remove")]
    if kept:
        out.append("kept: " + ", ".join(kept))
    return "\n".join(out + lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--self-test"]:
        sys.exit(self_test())
    if "--close" in argv:
        print(close(argv))
        return 0
    try:
        try:
            cwd = json.load(sys.stdin).get("cwd") or os.getcwd()
        except (ValueError, AttributeError):
            cwd = os.getcwd()
        files = sweep_state(os.path.expanduser(STATE_ROOT), live_names(), time.time())
        refs = sweep_repo(cwd, datetime.date.today())
        sys.stdout.write(report(files, refs))
    except Exception:
        pass


def self_test():
    failures = []

    def check(name, condition):
        if not condition:
            failures.append(name)

    sandbox = tempfile.mkdtemp(prefix="keel-sweep-")
    now = time.time()

    def put(path, age_days, content="x"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        stamp = now - age_days * DAY
        os.utime(path, (stamp, stamp))

    def age_dir(path, age_days):
        stamp = now - age_days * DAY
        os.utime(path, (stamp, stamp))

    try:
        root = os.path.join(sandbox, "coordination")
        state = os.path.join(root, "proj")
        logs, handoff, prompts = (os.path.join(state, name) for name in ("logs", "handoff", "prompts"))

        put(os.path.join(logs, "proj-old", "main.js.orig"), 5, "x" * 2048)
        age_dir(os.path.join(logs, "proj-old"), 5)
        put(os.path.join(logs, "proj-old.prompt.md"), 5)
        put(os.path.join(logs, "proj-fresh", "suite.log"), 1)
        put(os.path.join(logs, "proj-live", "suite.log"), 30)
        put(os.path.join(logs, "proj-live.prompt.md"), 30)
        put(os.path.join(logs, "proj-touched", "old.log"), 10)
        put(os.path.join(logs, "proj-touched", "new.log"), 0)
        age_dir(os.path.join(logs, "proj-touched"), 10)
        outside = os.path.join(sandbox, "outside.txt")
        put(outside, 30)
        os.symlink(outside, os.path.join(logs, "link.log"))
        os.utime(os.path.join(logs, "link.log"), (now - 30 * DAY,) * 2, follow_symlinks=False)

        put(os.path.join(handoff, "coordinator.md"), 60)
        put(os.path.join(handoff, "proj-old.md"), 20)
        put(os.path.join(handoff, "proj-week.md"), 5)
        put(os.path.join(prompts, "_footer.md"), 60)
        put(os.path.join(prompts, "old-front.md"), 20)
        put(os.path.join(prompts, "live.md"), 20)
        put(os.path.join(state, "queue-archive", "2026-01.md"), 120)
        put(os.path.join(state, "queue-archive", "2026-09.md"), 30)
        put(os.path.join(state, "queue.md"), 400, "deploy pending: measure with logs/tool/measure.cjs; generator prompts/gen.py\n")
        put(os.path.join(logs, "tool", "measure.cjs"), 30)
        age_dir(os.path.join(logs, "tool"), 30)
        put(os.path.join(prompts, "gen.py"), 30)
        put(os.path.join(handoff, "coordenadora.md"), 60)
        put(os.path.join(prompts, "front.md"), 20)
        put(os.path.join(logs, "proj.v2", "a.log"), 30)
        age_dir(os.path.join(logs, "proj.v2"), 30)
        put(os.path.join(state, "window.md"), 400)
        put(os.path.join(state, "profile", "profile.md"), 400)

        swept = sweep_state(root, {"proj-live", "other", "proj-front-phase2", "proj.v2"}, now)
        removed = {os.path.relpath(path, state) for path, _ in swept}
        check("logs: old dead dir and its prompt go", {"logs/proj-old", "logs/proj-old.prompt.md"} <= removed)
        check("logs: fresh dir stays", os.path.isdir(os.path.join(logs, "proj-fresh")))
        check("logs: live session stays at any age", os.path.isdir(os.path.join(logs, "proj-live"))
              and os.path.isfile(os.path.join(logs, "proj-live.prompt.md")))
        check("logs: a fresh file inside keeps the dir", os.path.isdir(os.path.join(logs, "proj-touched")))
        check("logs: a link goes, its target stays", "logs/link.log" in removed and os.path.isfile(outside))
        check("handoff: coordinator stays, old goes, recent stays",
              os.path.isfile(os.path.join(handoff, "coordinator.md")) and "handoff/proj-old.md" in removed
              and os.path.isfile(os.path.join(handoff, "proj-week.md")))
        check("prompts: shared stays, old goes, live front stays",
              os.path.isfile(os.path.join(prompts, "_footer.md")) and "prompts/old-front.md" in removed
              and os.path.isfile(os.path.join(prompts, "live.md")))
        check("archive: only past 90 days", "queue-archive/2026-01.md" in removed
              and os.path.isfile(os.path.join(state, "queue-archive", "2026-09.md")))
        check("state files never go", all(os.path.isfile(os.path.join(state, name))
                                          for name in ("queue.md", "window.md", "profile/profile.md")))
        check("cited by the open state: stays at any age", os.path.isfile(os.path.join(logs, "tool", "measure.cjs"))
              and os.path.isfile(os.path.join(prompts, "gen.py")))
        check("legacy coordinator checkpoint stays", os.path.isfile(os.path.join(handoff, "coordenadora.md")))
        check("a phase session keeps its front's prompt", os.path.isfile(os.path.join(prompts, "front.md")))
        check("a live session with a dot keeps its logs", os.path.isdir(os.path.join(logs, "proj.v2")))
        check("the size is counted", dict(swept).get(os.path.join(logs, "proj-old")) == 2048)

        unknown = os.path.join(sandbox, "unknown")
        put(os.path.join(unknown, "proj", "logs", "proj-live", "a.log"), 5)
        age_dir(os.path.join(unknown, "proj", "logs", "proj-live"), 5)
        put(os.path.join(unknown, "proj", "logs", "proj-new", "a.log"), 1)
        age_dir(os.path.join(unknown, "proj", "logs", "proj-new"), 1)
        gone = {os.path.relpath(path, unknown) for path, _ in sweep_state(unknown, None, now)}
        check("live list unreadable: age alone decides", gone == {os.path.join("proj", "logs", "proj-live")})
        guarded = os.path.join(sandbox, "guarded")
        target = os.path.join(sandbox, "target")
        put(os.path.join(target, "logs", "old", "a.log"), 30)
        age_dir(os.path.join(target, "logs", "old"), 30)
        put(os.path.join(target, "elsewhere", "b.log"), 30)
        os.makedirs(os.path.join(guarded, "folder-link"))
        os.symlink(os.path.join(target, "elsewhere"), os.path.join(guarded, "folder-link", "logs"))
        os.symlink(target, os.path.join(guarded, "project-link"))
        os.makedirs(os.path.join(guarded, "locked", "queue.md"))
        put(os.path.join(guarded, "locked", "logs", "old", "a.log"), 30)
        age_dir(os.path.join(guarded, "locked", "logs", "old"), 30)
        check("a linked folder or project is not followed, an unreadable open state keeps the project",
              sweep_state(guarded, set(), now) == [] and os.path.isfile(os.path.join(target, "elsewhere", "b.log"))
              and os.path.isdir(os.path.join(target, "logs", "old"))
              and os.path.isdir(os.path.join(guarded, "locked", "logs", "old")))
        check("no coordination dir: nothing", sweep_state(os.path.join(sandbox, "missing"), set(), now) == [])

        repo = os.path.join(sandbox, "repo")
        os.makedirs(repo)
        for args in (["init", "-q"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty",
                                       "-m", "x"]):
            git(repo, *args)
        today = datetime.date(2026, 10, 22)
        for name in ("2026-10-01-rebase", "2026-10-20-rebase", "no-date"):
            git(repo, "update-ref", BACKUP_REFS + name, "HEAD")
        git(repo, "update-ref", "refs/heads/backup/mine", "HEAD")
        refs = sweep_repo(repo, today)
        left = git(repo, "for-each-ref", "--format=%(refname)").stdout.split()
        check("refs: only the expired backup goes", refs == [BACKUP_REFS + "2026-10-01-rebase"]
              and BACKUP_REFS + "2026-10-20-rebase" in left and BACKUP_REFS + "no-date" in left
              and "refs/heads/backup/mine" in left)
        check("refs: outside a repo, nothing", sweep_repo(sandbox, today) == [])
        check("report: silent when nothing went", report([], []) == "")
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

    print("{} failure(s){}".format(len(failures), ": " + "; ".join(failures) if failures else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    main()
