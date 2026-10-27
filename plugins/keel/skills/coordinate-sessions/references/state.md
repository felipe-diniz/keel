# The coordination state (`$D`)

Read when writing to `queue.md`, `window.md` or the checkpoint, when closing a delivery, or when the state grows.

| Path | What it is | Cap | Removed by the sweep |
|---|---|---|---|
| `queue.md` | **only what is open**: owner decisions and approvals still valid (literal, date, scope), active front, queue, owner pending items, the line of each committed front (`<session> <sessionId> <shas>`) and the last green integration gate | ~8 KB | never |
| `queue-archive/YYYY-MM.md` | the closed diary, moved out of `queue.md` when the delivery closes | never read whole; `grep` | after 90 days |
| `window.md` | **only the table** of who holds each resource that exists only once, and each one's queue | ~2 KB | never |
| `prompts/` | the front part of each session's prompt (SKILL §4); `_*.md` are shared blocks | | after 14 days; `_*.md` never |
| `logs/<session>/` | the assembled prompt and the long outputs, text only | | after 3 days |
| `handoff/<session>.md` | the HANDOFF the session maintains, for whoever resumes | | after 14 days |
| `handoff/coordinator.md` | the coordinator checkpoint (SKILL §8): decisions in progress, next step, live sessions with name and full sessionId | ~2 KB | never |

- The next coordinator reads `queue.md` and `window.md`: that is why they have a cap. When closing a delivery, its diary
  goes to `queue-archive/`, `queue.md` keeps what is open, and the line of a returned resource leaves `window.md`.
- A standing owner approval lives in the project memory, not in `queue.md`.
- Nothing in `$D` goes to git; what stays for real goes to the front's PRD or doc and to memory.
- Each front is closed at once with `coordination-sweep.py --close` ([cleanup.md](cleanup.md)). Nobody deletes state by
  hand.

## What the machine and the branch have only one of

The tree is one, with WIP from other sessions and from the owner. The project's resource table is in the profile
(`$P_DIR/profile.md`); the principles always hold:

- **Git index and branch:** commit by temporary index in a shared tree ([commit-by-index.md](commit-by-index.md)).
  Never stash, reset, checkout or restore of someone else's file, clean, `add -A`/`add .`.
- **Shared generator** (ORM client, build cache, Nx daemon, engine project): one at a time, with notice.
- **Dependencies** (`install`, lockfile): only with the window, with no suite running in another session.
- **The owner's servers:** do not stop or restart them; start another only with the window and the owner's yes.
- **Shared indexes** (i18n, `MEMORY.md`, `CLAUDE.md`, risk doc, skills, PRDs, barrels, routes): a targeted insertion
  reread at that moment, never rewrite from an old read; commit by hunk or by key.

The coordinator grants and records it in `window.md`.
