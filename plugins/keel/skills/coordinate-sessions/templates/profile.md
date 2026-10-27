# Coordination profile — <project>

What this project adds to the method of the global skill `coordinate-sessions`. The skill is the method; this file wins
where they diverge. The rules that go into every prompt are in `session.md`, next to it. Derived from: <CLAUDE.md,
settings, hooks…>, on <date>; what came from the owner is marked with the date and the literal text.

## Identity

- Checkout: `<path>`, branch `<working branch>`, <no new branch | branch per front>, one worktree per front detached at the remote branch (`.claude/worktrees/<session>`, `worktree.bgIsolation: none`); the checkout only fast-forwards.
- Coordination state: `~/.claude/coordination/<slug>/`. Session names: `<prefix>-<front>[-phase<n>]`.
- How many front sessions at the same time: <1, owner's rule | N>.
- Front contract: <PRDs, plans, ADRs — where they live>. Tasks: <ClickUp/Jira/none, and who writes>.
- Memory: <`.claude/memory/<dev>/`, one folder per developer, auto memory linked by `/keel:memory` | where else it lives>.
- Critical risk: <doc or skill, and whether it has references per domain>.

## Commit

<direct | split> mode (skill §5 and `references/commit-by-index.md`), with these project steps: <sync with the
remote first? generate a file that only the tool writes?>. Message: <commitlint rule, language>.

## Commands (data only; who runs what is the skill's §6)

- Focused, for a front: test of one file or spec `<command>`; lint of files `<command>`; typecheck of one project
  `<command>`.
- Critical front, in addition: suites of the affected projects `<command>`; risk probes `<the risk doc's list>`.
- Integration gate, in this order, with the usual duration: `<suite: command, ~min>`, `<build>`, `<E2E>`,
  `<measurement bench>`, `<screens>`. Pre-push hook: `<command>`.
- Integration worktree: what a fresh worktree needs to run them `<install, generated files, how the suites get their
  env without copying `.env*`>`.
- Ports: `<service: port>`; what the gate starts and stops.

## What the machine and the branch have only one of

| Resource | Why there is only one | Rule |
|---|---|---|
| Git index and branch | `.git/index` is one for everybody | the mode in §Commit |
| <generator: ORM client, build cache, engine project> | <…> | <…> |
| <dependencies: install, lockfile> | rewrite everybody's environment | only with the window |
| <the owner's servers and ports> | <…> | <…> |
| <heavy suite, measurement bench, test database> | <one machine, results disturbed by a parallel run> | the integration gate's; a critical front only with the window |
| <shared indexes: i18n, MEMORY.md, CLAUDE.md, risk doc, barrels> | several sessions in the same file | surgical insertion reread on the spot; commit per hunk |

## Cleanup at front close

<!-- One backticked command per line, printed (never run) by `coordination-sweep.py --close`; `<SESSION-NAME>` is
replaced. What the front leaves outside the coordination state: test databases, Redis/queue keys, servers or
containers it started, generated files outside git. -->
- `<command>`: <what it removes>

## Owner approval first, always through the coordinator

<database change, backfill, bulk script, secret/env, business rule, guard, production — what CLAUDE.md lists>.

## Push, PR and deploy

- Push: <who, from where (worktree at the sha or clean checkout), hook, remote>. PR: <to where; CI>. Merge and deploy: <the owner's>.
- Deploy list: <migrations, envs, templates, infra, order>.

## Production

<what is allowed: read-only, count/id only, never PII or secret>.
