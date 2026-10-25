---
name: coordinate-sessions
description: Method of the COORDINATOR session — open one `claude --bg` session per front or phase, build the prompt with the rules footer, talk by message, split resources, take decisions to the owner, resume a stalled session and close with a commit of only the session's work. Use ALWAYS when the owner asks to run fronts through sessions, "open sessions", "launch a session", "open the next phase", to coordinate the ones running, or to resume the stalled ones.
---

# Coordinate sessions

The coordinator does not implement the front: it writes the prompt, opens the session, hands out the turn on each
resource the machine has only one of, takes approvals and decisions to the owner, checks the commit against the report
and, with the owner's yes, pushes. Each front lives in its own session, with its own context, its own gate and its own
commit.

## 0. The project

The method is this file; the project comes in through three things, resolved at the start:

- **Checkout and name:** `CHECKOUT=$(git rev-parse --show-toplevel)`, `SLUG=$(basename "$CHECKOUT")`.
- **Coordination state**, outside the repo: `D=~/.claude/coordination/$SLUG/` (§3).
- **Project profile** (`profile.md`) — the session name prefix, the branch, the table of what exists only once, the
  focused and integration-gate commands, commit/push/PR, the deploy list, what is forbidden in production and where debt goes —
  and the **session rules** (`session.md`), the block that goes in every prompt after the global footer (§4). Look in
  this order and use the first folder that has both (`P_DIR`):
  1. `$CHECKOUT/.claude/coordination/` — versioned, applies to the whole team (project with more than one dev);
  2. `$D/profile/` — personal, outside the repo (a project that is only yours, or that should not carry a coordination
     file);
  3. none: **derive it yourself** before opening the first session, from the repo's `CLAUDE.md`, the risk doc it points
     to, `.claude/settings.json`, the lockfile/`package.json`/git hooks and `.husky/` or equivalent; write it to
     `$D/profile/` following [templates/profile.md](templates/profile.md) and ask the owner only what no file answers
     (working branch, whether there is another dev on the remote, who pushes, what is forbidden in production).
  Old Portuguese names: [references/legacy-names.md](references/legacy-names.md).
  **Read the whole profile before launching or resuming the first session.** What it says wins over this file.

Shell state does not survive from one Bash tool call to the next: resolve `CHECKOUT`, `SLUG`, `D` and `P_DIR` once and
use the literal paths in the following commands. Nothing here names a project; nothing in a session's prompt cites
another project.

## 1. Session, subagent or direct

| The work | Goes to | Why |
|---|---|---|
| Front or phase with its own commit, hours of work, several layers | **`--bg` session** | own context, gate and commit; does not bloat the coordinator |
| Wide reading, code map, "who calls" | `keel:explore` (subagent) | the coordinator only needs the synthesis |
| Web research | `keel:research` (subagent) | same |
| Short fix (≲ 5 files, one domain, no PRD phase), doc, memory, coordination tweak | **directly in the coordinator**, with the gate at the end if it touches critical risk | a new session costs the context baseline, the prompt, the skills and the gate; for little work it is more expensive and slower |

A front never goes to a subagent: it dies with its answer, shares its caller's context and has no gate of its own.
Agent teams (experimental) do not isolate the worktree nor resume: they do not replace `--bg` sessions.

## 2. Launch, talk, resume, stop

**The binary.** `claude` may not be on the Bash tool shell's PATH. Find it and run the lines directly, without `bash -c`
(the security check blocks a script in `-c` that it cannot read):

```bash
C=$(command -v claude || ls ~/.local/bin/claude 2>/dev/null || ls -d ~/.vscode{,-server}/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null | sort -V | tail -1)
P=${CLAUDE_SKILL_DIR}/templates/background-session.settings.json
"$C" --bg -n <name> --settings "$P" --add-dir "$D" --permission-mode auto "$(cat "$D/logs/<name>.prompt.md")"
"$C" agents --json --cwd "$CHECKOUT"   # name, sessionId, state (busy, idle, working, blocked: waiting for permission or stopped)
"$C" logs <id|name>                    # recent output (raw TUI: filter the ANSI codes)
"$C" attach <id|name>                  # opens in the terminal (the owner answers a permission request here)
"$C" stop <id>                         # stops and keeps the conversation
"$C" --bg --resume <sessionId> -n <name> --settings "$P" --add-dir "$D" --permission-mode auto "<what changed and the next step>"
```

- **The details** (variadic `--add-dir`, the lean profile, inherited model and effort, no worktree, `NX_*`, resume
  copies): [references/launch.md](references/launch.md). Never `--model` or `--effort` on a front.
- **Name:** `<profile prefix>-<front>[-phase<n>]`, the same in the prompt, in `window.md` and in the report.
- **Talking:** `SendMessage` to the NAME; `ListAgents` shows the names, the coordinator's included (it changes with each
  session: check before building a prompt and warn the active ones if it changes). A message to an idle session wakes it
  and opens a turn that rereads its whole context: send only resource, decision and resume.
- **Knowing when it ended, without a loop or cron:** when launching, send the session a `SendMessage` with
  `notify_when_idle: true` (the notice arrives once when it goes idle or exits, without spending its tokens, and expires
  in 12 h; renew it when resuming). Cron only as a net when the notice is not possible, every 60 min, deleted when the
  last session closes. The tick (§9) is a different cron.
- **Closed, stop it and close it:** a session that delivered the final report and whose commit was checked exits with
  `"$C" stop <id>`, and then its state goes at once with the close (§3). A closed session that stays `blocked` in the
  list confuses the next coordinator and the duplicate check.
- **New front, new session:** never send a second front to a session that already closed its own, nor reopen it by
  `--resume` for another front: it would reread the whole context of the previous one on every call. `--resume` is only
  to continue the SAME front.

## 3. The coordination state (`$D`)

| Path | What it is | Cap | Removed by the sweep |
|---|---|---|---|
| `queue.md` | **only what is open**: owner decisions and approvals still valid (literal, date, scope), active front, queue, owner pending items, the line of each committed front (`<session> <sessionId> <shas>`) and the last green integration gate | ~8 KB | never |
| `queue-archive/YYYY-MM.md` | the closed diary, moved out of `queue.md` when the delivery closes | never read whole; `grep` | after 90 days |
| `window.md` | **only the table** of who holds each resource that exists only once, and each one's queue | ~2 KB | never |
| `prompts/` | the front part of each session's prompt (§4); `_*.md` are shared blocks | | after 14 days; `_*.md` never |
| `logs/<session>/` | the assembled prompt and the long outputs, text only | | after 3 days |
| `handoff/<session>.md` | the HANDOFF the session maintains, for whoever resumes | | after 14 days |
| `handoff/coordinator.md` | the coordinator checkpoint (§9): decisions in progress, next step, live sessions with name and id | ~2 KB | never |

**Close each front at once** when it is stopped and its commit checked (in a stacked round, after the green gate):
`coordination-sweep.py --close <name> --dry-run`, then without it. It removes the front's logs, prompt, HANDOFF, job
scratch, worktree and `window.md` lines, leaves one `<name> <sessionId> <shas> closed` line in `queue.md`, keeps prints
and videos until they are sent with `SendUserFile`, and prints the profile's cleanup list to run. The sweep hook at every
session start removes by age what the table marks, as the net. Command and rules:
[references/cleanup.md](references/cleanup.md). Nobody deletes state by hand.

The next coordinator reads `queue.md` and `window.md` — that is why they have a cap. When closing a delivery: its diary
goes to `queue-archive/`, `queue.md` keeps what is open, and the line of a returned resource leaves `window.md`.
A standing owner approval lives in the project memory, not in `queue.md`. Nothing in `$D` goes to git; what stays for
real goes to the front's PRD or doc and to memory.

## 4. A session's prompt

```bash
cat "$D/prompts/<front>.md" ${CLAUDE_SKILL_DIR}/templates/footer.md "$P_DIR/session.md" > "$D/logs/<name>.prompt.md"
```

In the assembled file replace `<COORDINATOR-NAME>`, `<SESSION-NAME>`, `<D>`, `<SKILL_DIR>` (= `${CLAUDE_SKILL_DIR}`) and the `<...>` of the front part. The front part
follows [templates/front.md](templates/front.md):

1. The owner's request **in their words**, with the date, and their decision or approval when there was one (literal text
   and scope). Implicit approval does not count.
2. The contract (PRD, plan, ADR) and the code map already checked by the coordinator, so the session does not
   rediscover them.
3. Numbered scope, with "decide and record the why" where there is a technical choice, and what is NOT in.
4. The skills of the layer (only those the front touches, and only the references of the topic), the project's
   critical-risk doc and only the reference of the domain touched, and the domain's memories.
5. The proof (§7): focused, or critical with its own gate; the close: fixes, commit (or "DO NOT COMMIT") and the report.
6. The decisions already made: the owner's literal answers to the questions raised before launch (below).

**Before launching, clear up every doubt.** The front runs with nobody watching: a doubt that only shows up midway
leaves it stalled or wakes the owner. When building the front part, list everything it may need to decide: acceptance
criterion, scope boundary, a design choice that changes the product, business rule, text the customer reads, and each
item that needs the owner's yes (database, backfill, mass script, secret/env, guard, production, push). Ask the owner
everything at once, through the question tool (up to 4 per call, the recommended one first). The answers go in literally,
with date and scope, in the prompt's decisions block and in `queue.md`. Launch only with the block closed; what could
not be foreseen follows the don't-block rule.

A decision that comes up midway, outside the block, goes back to the coordinator with the real case, the options and the
recommendation; it asks the owner through the question tool, with one option marked as recommended, and returns the
literal answer. These need the owner's yes BEFORE, always through the coordinator: what the project's profile and
`CLAUDE.md` list (database change, backfill, mass script, secret/env, business rule, a guard that blocks a response or
a sale, production). The session asks and proceeds with the rest.

## 5. What the machine and the branch have only one of

The tree is one, with WIP from other sessions and from the owner. The project's resource table is in the profile
(`$P_DIR/profile.md`); the principles always hold:

- **Git index and branch:** commit by temporary index (§6). Never stash, reset, checkout or restore of someone else's
  file, clean, `add -A`/`add .`.
- **Shared generator** (ORM client, build cache, Nx daemon, engine project): one at a time, with notice.
- **Dependencies** (`install`, lockfile): only with the window, with no suite running in another session.
- **The owner's servers:** do not stop or restart them; start another only with the window and the owner's yes.
- **Shared indexes** (i18n, `MEMORY.md`, `CLAUDE.md`, risk doc, skills, PRDs, barrels, routes): a targeted insertion
  reread at that moment, never rewrite from an old read; commit by hunk or by key.

The coordinator grants and records it in `window.md`.

## 6. Commit, proof and push

- **The session commits** only what is its own, after its focused proof (§7), in the mode the profile declares
  ([references/commit-by-index.md](references/commit-by-index.md), with the holes already paid for):
  - **direct** — the front session is the only one alive and the tree has no one else's WIP on its paths: proof in the
    tree itself and `git commit -m "<msg>" -- <explicit list>` (the `--` with paths takes only those, even with
    something else staged). It is the fastest: no worktree.
  - **split** — there is another live session or someone else's WIP: temporary index + `commit-tree`, the focused
    proof in a clean worktree at the sha and `update-ref` with CAS over the checked parent.
  Message: the project's commit rule, one line, no body, no trailer, no co-authoring, no amend.
- **The commits stack on the working branch** and wait for the coordinator's integration gate; the push goes only
  after it is green ([references/integration-gate.md](references/integration-gate.md)).
- **Safety point before a rebase or any history rewrite:** a ref, never a branch:
  `git update-ref refs/keel/backup/<YYYY-MM-DD>-<what> HEAD`. It does not show in `git branch`, and the sweep removes it
  after 14 days; delete it earlier with `git update-ref -d` once the result is checked.
- **The push is the coordinator's, with the owner's yes**, of the gated sha, after `git show --stat` of each commit
  against its report, by the path the profile describes (where to push from, hook, remote). Never `--no-verify` without
  the owner's word. PR, CI, merge and deploy: what the profile says; merge and deploy are the owner's.

## 7. Proof: focused in the front, one gate in the coordinator

| Who | When | Runs |
|---|---|---|
| **Front** (every one) | before its commit | the tests of what changed (the test first, the red seen), the lint/typecheck of the files, its own request × done check. Nothing else: no full suite, E2E, build, bench, measurement or screen pass unless its prompt names one |
| **Critical front** (changes a critical-risk invariant) | before its commit | the above, the suites of the affected projects and the probes the profile asks for, then `keel:critical-review`; its commit does not wait for anyone |
| **Coordinator: integration gate** | once, when the round's fronts have committed, before the push | the profile's integration-gate commands (suites, build, E2E, bench, screens) over the stack, in the checkout or an integration worktree ([references/integration-gate.md](references/integration-gate.md)) |

- Nine fronts, one gate. A red gate does not hold the others: the culprit commit is found by attribution or by bisect
  over the stack, and its front is resumed to fix on top.
- The machine's single resources (heavy suite, measurement bench, test database, ports) belong to the gate: a front
  never measures or runs a full suite, so nobody splits them in parallel. A critical front asks the coordinator for
  the window before its own suites.
- The coordinator puts in the prompt whether the front is critical. The session raises it when it sees it touches a
  critical invariant, and never lowers it.

## 8. What the coordinator checks on its own

The git state (branch, `git log`, nothing staged in the shared index by whoever committed), the report against the code
(every "done" is checked by the count in the log, not rerun), the owner's approvals against what the session did, and
the profile's deploy list. Production: only what the profile allows, read-only, only a count or id, never PII or secret.

**A gate that died midway:** the hook asks the owner to confirm the 2nd call to `keel:critical-review` in the session.
If the 1st dropped with no report, the owner confirms through `attach`, or authorizes closing the session and opening
another that continues from the HANDOFF and runs the gate once. Never work around it without the owner's word.

## 9. Coordination economy

Each call rereads the whole context, the coordinator's included. What fills it: skills invoked whole, raw Bash output,
messages between sessions and state files with no cap.

- **One front session at a time**, unless the owner asks otherwise; the next opens when the previous one has committed.
- **Coordinator checkpoint and `/clear`:** at the end of each round (the fronts of the moment closed, or run with the
  requested notice) and always when closing a delivery (commit and push), the coordinator updates `queue.md` and
  `window.md` (§3) and `handoff/coordinator.md`, and warns the owner in one line: "state saved; you can `/clear` and
  resume with `/keel:coordinate-sessions`". The `/clear` is the owner's command: it does not wait for it to proceed. The
  front session does not need this: it is born clean and exits with the `stop` (§2).
- **Checkpoint earlier, without waiting for the round:** after an automatic compaction, or once three fronts have
  closed since the last `/clear`, save the checkpoint at the next quiet point (no question open with the owner, no gate
  or commit being checked) and give the same notice, even with fronts live: every call costs more as the context grows.
- **The tick: warm cache, self-off, resume after the usage limit.** With the first front live, the coordinator arms one
  recurring cron every 30 minutes that runs `scripts/coordination-tick.py` and acts on its one line: `stop` (no live
  front) deletes the cron; `wake <name>` is a message to a live front the limit had blocked; `resumed <name>` was
  already reopened by the script after the reset; `self` resumes the coordinator's own cut step; otherwise "ok". The
  prompt, the decision table, the measured cost and the limits are in [references/tick.md](references/tick.md).
- **Resuming after the `/clear`** (or in a new coordinator): read the profile, `queue.md`, `window.md` and
  `handoff/coordinator.md`, not the previous conversation; check the live sessions in `agents --json` and renew the
  `notify_when_idle` of each (the notice requested before the `/clear` may not arrive), arm the tick
  (above) when one is live; if the coordinator's name changed, warn the active ones.
- **Autonomous run (nobody supervising for hours): relay instead of `/clear`**, with the coordinator itself as a
  background session: [references/relay.md](references/relay.md).
- **Messages only for resource, decision and report.** Progress goes to the HANDOFF; the coordinator reads it when it
  needs to.
- **Long output to a file** (`$D/logs/<session>/`), only the summary in the context (`tail -n 5`, the grep of the count
  and the failures).
- **A skill comes in through its core** and only through the references of the topic; after compaction, only the first
  20k characters of each invoked skill come back, up to about 100k in total, and the one the next step
  asks for is reinvoked.

## References (read when…)

- [launch](references/launch.md): opening or resuming a front, or a session born wrong.
- [cleanup](references/cleanup.md): a front closes, or the state grows.
- [commit-by-index](references/commit-by-index.md): committing in a shared tree, or pushing.
- [integration-gate](references/integration-gate.md): the round's fronts committed, the gate failed, or before a push.
- [tick](references/tick.md): arming or deleting the cron, or a front stopped at the limit.
- [relay](references/relay.md): an autonomous run, or taking over a relay.
- [context-baseline](references/context-baseline.md): a session compacts too often, or trimming what it loads.
- [legacy-names](references/legacy-names.md): a profile or state file under a Portuguese name.
