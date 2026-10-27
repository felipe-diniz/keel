# Cleanup: the close of each front, and the sweep as the net

Read when a front closes (its commit checked, or the round's gate green), when the state directory grows, or when a
file the owner still needs could expire.

## The close, at once

```bash
python3 <SKILL_DIR>/../../scripts/coordination-sweep.py --close <name> --state "$D" --checkout "$CHECKOUT" --sha <shas> --dry-run
```

Then the same line without `--dry-run`. In a stacked round the close waits for the green gate
([integration-gate.md](integration-gate.md)), since a red gate resumes the culprit front from its HANDOFF.

| It removes | It keeps |
|---|---|
| `logs/<name>/` and `logs/<name>.prompt.md` | whatever `queue.md`, `window.md` or `handoff/coordinator.md` cites by path |
| `prompts/<name>.md`, and `prompts/<front>.md` when the session is not a phase | whatever a live front's HANDOFF or prompt cites by path |
| `handoff/<name>.md` | `_*.md` shared blocks and `handoff/coordinator.md` |
| the `tmp/` of its job (`~/.claude/jobs/<id>/tmp`) | prints, videos, PDFs and archives until `--sent` |
| its worktrees (named after it, or given by `--worktree`), and their branch when merged; forced out when every commit is on a remote branch, picked onto the upstream or given by `--sha`, and only ignored files are left | a worktree with changed tracked files or unintegrated commits, an unmerged branch (reported); untracked files not ignored until `--force-worktree` |
| the `window.md` lines that cite only it | shared `window.md` lines (reported, edit by hand) |
| in `queue.md`, its old `<name> …` line, replaced by one `<name> <sessionId> <shas> closed <date>` line | the other `queue.md` lines that cite it (reported) |

- It refuses a live session ("stop it first") and an unreadable agents list.
- **It refuses when the checkout holds the front's files**: a path the `--sha` commits touched that the checkout's
  `git status` lists, changed or untracked, means the front wrote in the checkout. Compare each with the commit,
  restore those that match (a backup first when in doubt) and rerun; nothing is removed until then.
- **It fast-forwards the checkout** to its upstream when the branch is behind and no tracked file changed in it
  (untracked files stay; one in the way stops the merge). A changed or diverged checkout is reported, never moved.
- **Owner files:** the front's report lists the prints and videos the owner should see. Send them with `SendUserFile`
  before the close, then rerun with `--sent`.
- **The project's cleanup** (test databases, Redis keys, servers or containers the front started) is the
  `## Cleanup at front close` list of the profile. The close prints it with the session name in place; the coordinator
  runs it, with the window when the resource is single.
- Then move the front's diary lines of `queue.md` to `queue-archive/YYYY-MM.md`.

## The sweep, at every session start

The plugin's sweep hook removes, in every project's `$D`, what the table in [state.md](state.md) marks, counted from the entry's last
change: `logs/` after 3 days, `handoff/<session>.md` and `prompts/` after 14, `queue-archive/` after 90. What stays at
any age: what belongs to a session alive in `agents --json` (when the list can't be read, age alone decides), and what
`queue.md`, `window.md` or `handoff/coordinator.md` cite by path (`logs/<name>`, `prompts/<name>`, `handoff/<name>`).
So a tool, evidence or generator that an open item still needs is cited by that path in `queue.md`; once the item
closes and leaves it, the file expires. The hook also removes the safety refs older than 14 days (SKILL §5) and prunes the
worktrees whose directory has been gone for 14 days. Nobody deletes state by hand.
