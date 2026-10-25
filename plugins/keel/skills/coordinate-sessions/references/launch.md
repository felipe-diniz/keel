# Launching and resuming a background session: the details

Read when opening or resuming a front, when a session is born wrong (effort, worktree, wrong checkout), or before
changing the launch command.

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
- **In the checkout, no worktree to work in** when the profile says so (`"worktree": {"bgIsolation": "none"}` in the
  repo's settings). A session that asks "Call EnterWorktree first": the key is gone; take it to the owner, do not accept
  the worktree.
- **`NX_WORKSPACE_ROOT_PATH` inherited:** the background session is born with that of the daemon that opened it, which
  may belong to another checkout. Every `nx` of the session and of the proof carries
  `NX_WORKSPACE_ROOT_PATH=<checkout or worktree> NX_DAEMON=false`.
- **Resuming** continues the same conversation; if it is still running, it opens a copy and warns. Before opening or
  resuming, check in `agents --json` that the owner has not already opened the same front.
- **Stopped by the usage limit:** the tick resumes it after the reset ([tick.md](tick.md)); by hand, the same
  `--resume` line with "the limit has reset; continue the interrupted step from your HANDOFF".
