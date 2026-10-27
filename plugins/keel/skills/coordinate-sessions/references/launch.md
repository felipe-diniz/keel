# Launching and resuming a background session: the details

Read when opening or resuming a front, when a session is born wrong (effort, worktree, wrong checkout) or stuck, or
before changing the launch command.

- **`--add-dir` is variadic:** always follow it with another option, or it swallows the prompt as a directory. It grants
  the session access to `$D` (HANDOFF and logs).
- **The lean profile goes on every launch, `--resume` included** (`--settings "$P"`): it removes from the background
  session what it never uses and would be reread on every call — Artifact, Workflow, ReportFindings, ScheduleWakeup,
  NotebookEdit, AskUserQuestion, the claude.ai connectors and the built-in skills in the listing. Measured: the baseline
  of each call dropped from 72k to 40k tokens ([context-baseline.md](context-baseline.md)). The project's skills stay.
  Decisions go to the coordinator by `SendMessage`.
- **Model and effort are inherited:** neither `--model` nor `--effort`, on any front, the critical-risk one included. The
  session is born at the effort its settings give its model: the level saved with `/effort` (per model, under
  `modelSettings`) or an `effortLevel` in the repo's settings; a top-level `effortLevel` in `~/.claude/settings.json`
  doesn't count for Opus 5.5 or newer, which then start at `medium`. `max` is only for the gate, through the frontmatter of
  `keel:critical-review`. Depth on a step is `ultrathink`. This rule holds by the file: an old copy of the skill in the
  context (or preserved by compaction) once ordered `--effort max` and opened four fronts at `max` (2026-10-16); before
  launching, check the command in the skill.
- **Each front works in its own worktree, never in the checkout.** A front writing in the checkout, with commits whose
  parent is the remote branch and a push by sha, leaves the checkout's branch behind and the front's files dirty in it:
  a coordinator found 339 such files after nine fronts (2026-10-25). So the coordinator, before the launch:
  ```bash
  git -C "$CHECKOUT" fetch <remote> <branch>
  git -C "$CHECKOUT" worktree add --detach "$CHECKOUT/.claude/worktrees/<name>" <remote>/<branch>
  ```
  then the steps the profile lists to prepare a worktree (install, generated files, caches it may copy), and launches
  from inside it (`cd` there, then `"$C" --bg …`), so the session's cwd, `CLAUDE.md` and project skills are the
  worktree's and `agents --cwd "$CHECKOUT"` still lists it. Named after the session, `--close` finds it; elsewhere,
  pass `--worktree <path>`. Keep `"worktree": {"bgIsolation": "none"}` in the settings: with it Claude Code does not
  make a second worktree of its own, on a new branch from the checkout's possibly stale HEAD. `.claude/worktrees/` goes
  in the project's `.gitignore`. A session that asks "Call EnterWorktree first": the key is gone; take it to the owner.
- **The checkout belongs to the owner and the coordinator.** No front writes there; the coordinator's own short fixes
  go by a worktree too when the checkout is not clean. After each push the clean checkout is fast-forwarded
  (`git merge --ff-only <remote>/<branch>`; `--close` does it), so it never drifts behind.
- **`NX_WORKSPACE_ROOT_PATH` inherited:** the background session is born with that of the daemon that opened it, which
  may belong to another checkout. Every `nx` of the session and of the proof carries
  `NX_WORKSPACE_ROOT_PATH=<checkout or worktree> NX_DAEMON=false`.
- **Resuming** continues the same conversation; if it is still running, it opens a copy and warns. Before opening or
  resuming, check in `agents --json` that the owner has not already opened the same front.
- **`--resume` takes the full sessionId**, never the short id from the listing: a short id opens the "Resume session"
  picker with "No sessions match", the session sits there with no model running, and every message to it is held and
  expires (2026-10-27). Right after a launch or resume, check `"$C" logs <id>` shows the turn running.
- **A gate that died midway:** the hook asks the owner to confirm the 2nd call to `keel:critical-review` in the
  session. If the 1st dropped with no report, the owner confirms through `attach`, or authorizes closing the session and
  opening another that continues from the HANDOFF and runs the gate once. Never work around it without the owner's
  word.
- **Stopped by the usage limit:** the tick resumes it after the reset ([tick.md](tick.md)); by hand, the same
  `--resume` line with "the limit has reset; continue the interrupted step from your HANDOFF".
