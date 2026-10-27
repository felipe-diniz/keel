---
name: coordinate-sessions
description: Method of the COORDINATOR session — open one `claude --bg` session per front or phase, build the prompt with the rules footer, talk by message, split resources, take decisions to the owner, resume a stalled session and close with a commit of only the session's work. Use when the owner asks to run fronts through sessions, "open sessions", "launch a session", "open the next phase", to coordinate the ones running, or to resume the stalled ones. Not for short work: that runs in the main session.
---

# Coordinate sessions

The coordinator does not implement the front: it writes the prompt, opens the session, hands out the turn on each
resource the machine has only one of, takes approvals and decisions to the owner, checks the commit against the report
and, with the owner's yes, pushes. Each front lives in its own session, with its own context, its own gate and its own
commit.

## 0. The project

- **Checkout and name:** `CHECKOUT=$(git rev-parse --show-toplevel)`, `SLUG=$(basename "$CHECKOUT")`.
- **Coordination state**, outside the repo: `D=~/.claude/coordination/$SLUG/` ([references/state.md](references/state.md)).
- **Project profile** (`profile.md`: name prefix, branch, single resources, focused and integration-gate commands,
  commit/push/PR, deploy list, what is forbidden in production, where debt goes) and **session rules** (`session.md`,
  the block after the footer in every prompt). Use the first folder that has both (`P_DIR`):
  1. `$CHECKOUT/.claude/coordination/` — versioned, for the whole team;
  2. `$D/profile/` — personal, outside the repo;
  3. none: **derive it** from the repo's `CLAUDE.md`, its risk doc, `.claude/settings.json`, the lockfile and git hooks;
     write it to `$D/profile/` following [templates/profile.md](templates/profile.md) and ask the owner only what no
     file answers. Old Portuguese names: [references/legacy-names.md](references/legacy-names.md).

**Read the whole profile before launching or resuming the first session.** What it says wins over this file. Shell
state does not survive between Bash calls: resolve the paths once and use them literally. Nothing in a prompt cites
another project.

## 1. Main session first; a session only for a front

**The default is the main session.** A `--bg` session costs the context baseline, the prompt, the skills, the gate and
the coordinator's messages: for short work it is more expensive and slower than doing it here.

| The work | Goes to |
|---|---|
| Short fix (≲ 5 files, one domain, no PRD phase), a finding to fix, doc, memory, coordination tweak, a question, a measurement | **the main session**, with the gate at the end if it touches critical risk |
| Wide reading, code map, "who calls" | `keel:explore` |
| Web research | `keel:research` |
| Front or phase with its own commit, hours of work, several layers | **`--bg` session** |

- Never open a session to answer a question, fix a review finding, run a test or adjust a front that already closed:
  do it in the main session.
- In doubt between a session and the main session, the main session.
- A front never goes to a subagent: it dies with its answer and has no gate of its own. Agent teams do not isolate the
  worktree nor resume: they do not replace `--bg` sessions.

## 2. Launch, talk, resume, stop

`claude` may not be on the Bash shell's PATH. Find it and run the lines directly, without `bash -c`:

```bash
C=$(command -v claude || ls ~/.local/bin/claude 2>/dev/null || ls -d ~/.vscode{,-server}/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null | sort -V | tail -1)
P=${CLAUDE_SKILL_DIR}/templates/background-session.settings.json
git -C "$CHECKOUT" worktree add --detach "$CHECKOUT/.claude/worktrees/<name>" <remote>/<branch>   # cd into it
"$C" --bg -n <name> --settings "$P" --add-dir "$D" --permission-mode auto "$(cat "$D/logs/<name>.prompt.md")"
"$C" agents --json --cwd "$CHECKOUT"   # name, sessionId, state (busy, idle, working, blocked)
"$C" logs <id|name>                    # recent output (raw TUI: filter the ANSI codes)
"$C" attach <id|name>                  # the owner answers a permission request here
"$C" stop <id>                         # stops and keeps the conversation
"$C" --bg --resume <full sessionId> -n <name> --settings "$P" --add-dir "$D" --permission-mode auto "<what changed and the next step>"
```

- **Each front in its own worktree**, launched from inside it; the checkout only moves by fast-forward. Details (lean
  profile, inherited model and effort, `NX_*`, resume copies, the full sessionId): [references/launch.md](references/launch.md).
- **Name:** `<profile prefix>-<front>[-phase<n>]`, the same in the prompt, in `window.md` and in the report.
- **Talking:** `SendMessage` to the NAME. A message wakes the session and rereads its whole context: send only
  resource, decision and resume. Progress goes to the HANDOFF.
- **Knowing when it ended:** `SendMessage` with `notify_when_idle: true` when launching or resuming (once, expires in
  12 h). Cron only as a net, every 60 min.
- **Closed, stop it and close it:** after the final report and the checked commit, `"$C" stop <id>` and the close
  ([references/cleanup.md](references/cleanup.md)).
- **New front, new session:** `--resume` is only to continue the SAME front.

## 3. State

`queue.md` (only what is open), `window.md` (only the resource table), `prompts/`, `logs/`, `handoff/`, with caps and
ages: [references/state.md](references/state.md). Each front is closed at once with `coordination-sweep.py --close`
([references/cleanup.md](references/cleanup.md)).

## 4. A session's prompt

```bash
cat "$D/prompts/<front>.md" ${CLAUDE_SKILL_DIR}/templates/footer.md "$P_DIR/session.md" > "$D/logs/<name>.prompt.md"
```

Replace `<COORDINATOR-NAME>`, `<SESSION-NAME>`, `<D>`, `<SKILL_DIR>` (= `${CLAUDE_SKILL_DIR}`) and the `<...>` of the
front part, which follows [templates/front.md](templates/front.md):

1. The owner's request **in their words**, with the date, and their literal decision or approval with scope.
2. The contract (PRD, plan, ADR) and the code map already checked, so the session does not rediscover them.
3. Numbered scope, with "decide and record the why" where there is a technical choice, and what is NOT in.
4. Only the skills and references the front touches, the critical-risk doc and the domain's reference and memories.
5. The proof (§6) and the close: fixes, commit (or "DO NOT COMMIT") and the report.
6. The decisions already made (below).

**Before launching, clear up every doubt.** List what the front may need to decide (acceptance criterion, scope
boundary, product choice, business rule, customer text, each item that needs the owner's yes) and ask the owner all at
once with the question tool, the recommended option first. Answers go in literally, with date and scope, in the prompt
and in `queue.md`. A decision that comes up midway goes to the coordinator with the case, the options and the
recommendation; the coordinator asks the owner and returns the literal answer. What the profile and `CLAUDE.md` list
(database, backfill, mass script, secret/env, business rule, guard, production) always needs the owner's yes first.

## 5. Commit and push

- **The session commits** only its own work, after its focused proof, in the mode the profile declares:
  **direct** in its own worktree (`git commit -m "<msg>" -- <explicit list>`), or **split** by temporary index in a
  shared tree ([references/commit-by-index.md](references/commit-by-index.md)). One line, the project's rule, no body,
  no trailer, no co-authoring, no amend.
- **The commits stack** in the integration worktree and wait for the integration gate
  ([references/integration-gate.md](references/integration-gate.md)).
- **Before a rebase or history rewrite:** `git update-ref refs/keel/backup/<YYYY-MM-DD>-<what> HEAD`, never a branch.
- **The push is the coordinator's, with the owner's yes**, of the gated sha, after `git show --stat` of each commit
  against its report, by the profile's path. Never `--no-verify` without the owner's word. Merge and deploy are the
  owner's.

## 6. Proof: focused in the front, one gate in the coordinator

| Who | When | Runs |
|---|---|---|
| **Front** | before its commit | the tests of what changed (test first, red seen), lint/typecheck of its files, its request × done check; no full suite, E2E, build, bench or measurement unless its prompt names one |
| **Critical front** | before its commit | the above, the affected suites and the profile's probes (with the window), then `keel:critical-review` |
| **Coordinator** | once, when the round's fronts have committed, before the push | the profile's integration-gate commands over the stack ([references/integration-gate.md](references/integration-gate.md)) |

A red gate holds nobody: the culprit is found by attribution or bisect and its front is resumed to fix on top. The
coordinator says in the prompt whether the front is critical; the session may raise it, never lower it.

## 7. What the coordinator checks on its own

The git state (branch, `git log`, nothing staged by whoever committed), the report against the code (each "done" by the
count in the log, not rerun), the owner's approvals against what the session did, and the deploy list. Production:
only what the profile allows, read-only, count or id, never PII or secret. A 2nd `keel:critical-review` in a session
asks the owner's confirmation: the owner answers through `attach`; never work around it.

## 8. Economy

- **One front session at a time**, unless the owner asks otherwise.
- **Checkpoint and `/clear`:** at the end of each round, when closing a delivery, after an automatic compaction or once
  three fronts closed, update `queue.md`, `window.md` and `handoff/coordinator.md` and tell the owner in one line:
  "state saved; you can `/clear` and resume with `/keel:coordinate-sessions`".
- **The tick:** with a front live, one cron every 30 min runs `scripts/coordination-tick.py`; act on its one line
  ([references/tick.md](references/tick.md)).
- **Resuming after `/clear`:** read the profile, `queue.md`, `window.md` and `handoff/coordinator.md`, not the old
  conversation; check `agents --json`, renew each `notify_when_idle`, arm the tick; warn the live sessions if the
  coordinator's name changed.
- **Autonomous run:** relay instead of `/clear` ([references/relay.md](references/relay.md)).
- **Long output to a file** in `$D/logs/<session>/`; only the summary enters the context.
- **A skill comes in through its core** and only the topic's references.

## References (read when…)

- [launch](references/launch.md): opening or resuming a front, or a session born wrong or stuck.
- [state](references/state.md): writing the state files, closing a delivery, or sharing a single resource.
- [cleanup](references/cleanup.md): a front closes, or the state grows.
- [commit-by-index](references/commit-by-index.md): committing in a shared tree, or pushing.
- [integration-gate](references/integration-gate.md): the round's fronts committed, the gate failed, or before a push.
- [tick](references/tick.md): arming or deleting the cron, or a front stopped at the limit.
- [relay](references/relay.md): an autonomous run, or taking over a relay.
- [context-baseline](references/context-baseline.md): a session compacts too often, or trimming what it loads.
- [legacy-names](references/legacy-names.md): a profile or state file under a Portuguese name.
