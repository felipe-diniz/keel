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
| its worktrees in the checkout, and their branch when merged | a worktree with uncommitted changes, an unmerged branch (reported) |
| the `window.md` lines that cite only it | shared `window.md` lines (reported, edit by hand) |
| in `queue.md`, its old `<name> …` line, replaced by one `<name> <sessionId> <shas> closed <date>` line | the other `queue.md` lines that cite it (reported) |

- It refuses a live session ("stop it first") and an unreadable agents list.
- **Owner files:** the front's report lists the prints and videos the owner should see. Send them with `SendUserFile`
  before the close, then rerun with `--sent`.
- **The project's cleanup** (test databases, Redis keys, servers or containers the front started) is the
  `## Cleanup at front close` list of the profile. The close prints it with the session name in place; the coordinator
  runs it, with the window when the resource is single.
- Then move the front's diary lines of `queue.md` to `queue-archive/YYYY-MM.md`.

## The sweep, at every session start

The plugin's sweep hook removes, in every project's `$D`, what the §3 table marks, counted from the entry's last
change: `logs/` after 3 days, `handoff/<session>.md` and `prompts/` after 14, `queue-archive/` after 90. What stays at
any age: what belongs to a session alive in `agents --json` (when the list can't be read, age alone decides), and what
`queue.md`, `window.md` or `handoff/coordinator.md` cite by path (`logs/<name>`, `prompts/<name>`, `handoff/<name>`).
So a tool, evidence or generator that an open item still needs is cited by that path in `queue.md`; once the item
closes and leaves it, the file expires. The hook also removes the safety refs older than 14 days (§6) and prunes the
worktrees whose directory has been gone for 14 days. Nobody deletes state by hand.
