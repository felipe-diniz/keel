# Changelog

## 3.4.1 — 2026-10-25

- **Each front works in its own worktree, never in the checkout.** The coordinator makes it detached at the remote branch (`.claude/worktrees/<session>`) and launches the session from inside it; the front commits there directly. Before, fronts wrote in the checkout and committed with the remote branch as parent, and the push by sha moved the remote but not the checkout: after nine fronts the checkout showed 339 files that were already pushed.
- **`--close` checks the checkout.** It refuses while the checkout's `git status` lists a file the front's `--sha` commits touched, and fast-forwards the checkout's branch to its upstream when no tracked file changed in it.
- **`--close` removes the front's worktree for good.** A worktree named after the session, or given by `--worktree`, is forced out when each of its commits is on a remote branch, was picked onto the upstream or is one of the `--sha`, and no tracked file changed; untracked files that are not ignored need `--force-worktree`. A detached worktree with unintegrated commits stays: removing it would leave them only in the reflog.
- The integration gate always runs in its own worktree, picking each front's commits in closing order onto the remote branch.

## 3.4.0 — 2026-10-25

- **One integration gate, in the coordinator.** A front commits with focused proof (the tests of what changed, red seen, lint/typecheck of its files). The full suites, build, E2E, bench and screens run once per round, over every front's commits; the profile names the commands in its `## Commands` section.
- **The tick is a script that turns itself off.** The coordinator's cron runs `scripts/coordination-tick.py`. With no live front it prints `stop` and the cron is deleted, so an idle coordinator stops paying for ticks. A front stopped by the usage limit is resumed by the tick after the reset, without waiting for a message.
- **Cleanup at front close.** `coordination-sweep.py --close <session>` removes, in one pass, what the closed front left: handoff, prompt, logs, scratch and worktree, and its queue lines become one `closed` line; the owner's prints and videos stay until they were sent (`--sent`). The profile's `## Cleanup at front close` section adds the project's own commands.
- **New skill `web-craft`.** Public sites and landing pages: design, copy, motion with GSAP/ScrollTrigger/Lenis, Three.js, SEO and AI search, performance and verification on the rendered page. A short core and one reference per topic.
- **Leaner context.** `coordinate-sessions` keeps a core and moves the launch details, cleanup, relay and old names to references, each with a "Read when" line and an index in the core. Rules that lived in two places now live in one.

What enters the context, in bytes (`tests/test_sizes.py` pins the caps):

| | 3.3.0 | 3.4.0 |
|---|---:|---:|
| `rules.md` (every session, every call) | 9,698 | 9,249 |
| output style | 1,966 | 1,966 |
| agent, skill and command descriptions | 2,181 | 2,603 (one skill more) |
| **every session** | **13,845** | **13,818** |
| `coordinate-sessions` core (coordinator) | 23,395 | 19,693 |
| rules footer (every front's prompt) | 5,450 | 5,776 (proof and close rules added) |
| **coordinator, skill and footer** | **28,845** | **25,469** |

The 3.3.0 core passed the 20,000 characters that come back after compaction, so its end was cut; the 3.4.0 core comes back whole.

Measured tick cost: a tick that answers without a tool is one call that rereads the whole cached context; a tick that runs one tool is two calls, about twice that. A cache miss costs about as much as 10 to 40 ticks.
