# Changelog

## 3.5.1 — 2026-10-27

- **`web-craft` is proactive: modern by default.** A new site, a redesign or "modernize" now delivers, without being asked, GSAP + ScrollTrigger + SplitText acts, light parallax, Lenis, pointer tilt and a Three.js scene behind the hero, each behind the gate. A sober page with no motion fails the review; leaving a layer out is the owner's call. Before, "decide the motion budget" and "a scene only when depth carries meaning" read as permission to ship none, and a redesign came out static.
- **Keep the brand.** A redesign starts from the current site rendered and keeps its palette, gradients, type and signature elements (credential badge, shapes, floating contact button). Swapping them for neutral tokens fails the review; the brand wins over the generic-pattern table.
- **Ideas and share-ready, unasked.** New reference `proactive.md`: the posture (bring the ideas, ask only what is the owner's), a catalog of ideas shipped on a real landing (full-screen scenes with an overlap hand-off, fit zoom on short laptops, header that hides on scroll, floating contact, credential badge, booking with no void), the share-ready delivery (share card rendered from the brand with Playwright, OG with alt, `SHARE_ORIGIN` for the preview link, sitemap without anchors, robots off transactional routes, check as the crawler, the `?v=N` hint) and the layout probe by script. A link that previews no card or an old logo fails the review.
- **New reference `stack.md`.** The ready recipe from a shipped landing: default delivery per device, the files (gate, boot, engine, scene), the boot and engine skeletons, the `data-*` markup contract, one act per section type, hero scene concepts tied to the brand and the delivery check. The session no longer has to study another repo to build the layer.

## 3.5.0 — 2026-10-27

- **New skill `showcase`.** Reel (1080x1920), landscape release video (1920x1080 with WebVTT), post art, carousel and covers, from the project's real screens with seed data.
  - Capture by a JSON plan with login, theme and masking of CPF, CNPJ, phone and e-mail by default; only local hosts or the config's `captureHosts`.
  - A frame-exact compositor with camera, taps, transitions, and kinetic or word-timed captions; covers and posters only when the text has settled.
  - Optional ElevenLabs narration and music. The key comes from the environment or the owner's `~/.config/keel/elevenlabs.env` (chmod 600), never read by the agent. Without a key: a silent video with kinetic captions, or a music file mixed to -14 LUFS.
  - The copy method for social posts and release notes, with the WhatsApp message.
  - Project config in `.claude/showcase.json`. Node ≥ 20, ffmpeg and Playwright (the project's, or `doctor.mjs --install` into `~/.cache/keel/showcase/`). Ported and generalized from a product's marketing pipeline; the plugin names no project.
- **New agent `keel:test`.** Writes and fixes tests from the behaviors the main session lists: the red-first test, the regression test of a bug or a gate finding, the cases of an approved change. It loads the project's test skill, runs only the focused command, never touches production code and returns red/green evidence; critical paths are allowed, and the main session reviews the diff and sees the red. `keel:implement` no longer writes tests.
- **Short work stays in the main session.** The rules and `coordinate-sessions` now say it first: a fix of a few files, a review finding, a question, a test run or a doc never opens a `--bg` session; in doubt, the main session. The skill's description says it is not for short work.
- **`coordinate-sessions` core from 19,987 to 11,508 bytes.** The state table and the single-resource principles moved to `references/state.md`; the gate that died midway moved to `references/launch.md`. The cap in `tests/test_sizes.py` drops to 12,000.
- **`--resume` takes the full sessionId.** A short id opens the "Resume session" picker, the session sits there with no model, and messages to it are held until they expire. The launch reference says it and asks to check `logs` right after.
- `keel:implement` no longer says "in doubt between loading a skill and not, load": a skill loads when the task matches it.

| | 3.4.1 | 3.5.0 |
|---|---:|---:|
| `rules.md` | 9,249 | 9,471 |
| agent, skill and command descriptions | 2,603 | 3,537 (one agent and one skill more) |
| **every session** (with the 1,966 B output style) | **13,818** | **14,974** |
| `coordinate-sessions` core (coordinator) | 19,987 | 11,508 |
| `showcase` core (on invocation) | — | 5,867 |

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
