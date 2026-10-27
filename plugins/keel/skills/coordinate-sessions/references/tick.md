# The coordinator's tick: warm cache, self-off, resume after the usage limit

Read when arming, handling or deleting the coordinator's recurring cron (§8), or when a front stopped at the usage
limit.

## What the tick is for

1. **Warm cache.** Each call reads the whole context from the prompt cache. In Claude Code the cache lives 1 h (5 min
   when the account is in usage overage), and every read restarts the timer at no extra cost. A front often runs longer
   than that with the coordinator idle, so the call that handles the front's notice would pay a cold rewrite of the
   whole context: 2× the input price (the 1-hour write). A cache read costs 0.05× on Opus 5.5, 0.1× on most models and
   0.025× on Fable 5.1.
2. **Self-off.** With no live front the tick has nothing to keep warm: the script prints `stop` and the coordinator
   deletes the cron. No tick runs while nothing is live.
3. **Resume after the usage limit.** When the limit cuts the account, every session stops at the same time and none
   retries on its own; a front that was cut stays stopped after the reset until someone sends it something. The script
   finds those fronts and resumes them once the reset time has passed.

## Arm it

When it launches the first front (and after a `/clear` or a relay, with a front live), the coordinator checks
`CronList` and, if no keel tick is armed, creates one recurring `CronCreate` with `cron: "13,43 * * * *"` and this
prompt, every `<...>` replaced by the literal value:

```text
keel tick: run `python3 <SKILL_DIR>/../../scripts/coordination-tick.py --self <COORDINATOR-NAME> --checkout <CHECKOUT> --state <D>` (if that path is gone after an update, the newest ~/.claude/plugins/cache/*/keel/*/scripts/coordination-tick.py). By its one line: "stop" -> CronList and CronDelete this tick; "wake <name>" -> SendMessage <name> "the usage limit has reset; continue the interrupted step"; "self" -> continue your interrupted step from handoff/coordinator.md; otherwise reply only "ok". No other tool call.
```

Use 30 minutes, not 50 or 60: cron cannot express a 50-minute period, a 60-minute gap leaves no margin over the TTL,
and the scheduler shifts each job by a fixed offset. A tick that lands while the coordinator is busy waits for idle,
and the cache is already warm then.

## What the script decides

`scripts/coordination-tick.py` reads `claude agents --json --all` and the tail of each front's transcript
(`~/.claude/projects/*/<sessionId>.jsonl`). A front is a background session, not the coordinator, whose cwd is the
checkout or whose name the open state cites (`queue.md`, `window.md`, `handoff/coordinator.md`). With several
sessions of the same name, the newest wins.

| The front | The line | Who acts |
|---|---|---|
| live, not cut | `N live (names)` | nobody: "ok" |
| live, `blocked`, last turn a limit error whose reset passed | `wake <name>` (at most every 30 min) | the coordinator, by `SendMessage` |
| stopped or failed, last turn a limit error whose reset passed, still cited in the open state | `resumed <name>` (at most every 30 min) | the script: `claude --bg --resume <sessionId> -n <name>` with the lean profile, `--add-dir <D>` and a prompt pointing to its HANDOFF |
| cut, reset still ahead | `waiting <name> until HH:MM` | nobody: the tick goes on |
| cut by a billing error (no reset time) | `resumed`/`wake`, at most every 2 h | as above |
| stopped normally, done, or no longer cited | ignored | nobody |
| nothing live, waiting, resumed or woken | `stop, no live front; delete this cron` | the coordinator, `CronDelete` |
| the coordinator's previous turn ended in a limit error | `self: …` | the coordinator resumes its step |
| `agents --json` unreadable | `agents list unreadable; keep the cron` | nobody; never `stop` |

The retry memory is `$D/tick.json` (name → last attempt). `--dry-run` lists without launching or writing: it is the
only way to run it by hand against a real `$D`. A front closed and removed from the open state is never resumed: the
close (§3) takes it out.

## Cost, measured on 2026-10-25

- A tick with no tool call is 1 API call (cache read of the whole context, ~4 output tokens).
- A tick with one tool call is 2 API calls, each reading the whole context, plus ~100 to 200 output tokens: about 2×
  the no-tool tick. One cache miss (2× input) still pays for 10 to 40 tool ticks, 5 to 20 hours at the 30-minute
  cadence.
- A call refused by the usage limit is recorded with model `<synthetic>` and all-zero usage: ticks during the limit
  cost 0 tokens.
- With no live front there are no ticks at all (`stop`): before, the "ok" tick ran until the cron expired.

## The usage limit: measured and inferred

- **Measured** in real transcripts: the cut turn is an assistant entry with `isApiErrorMessage: true`,
  `error: "rate_limit"`, `apiError: "usage_limit_reached"`, `apiErrorStatus: 429` and the reset in
  `apiErrorParams.rate_limit_info.resetsAt` (epoch seconds; `rateLimitType` five_hour or seven_day). A billing cut is
  `error: "billing_error"`, status 400, with no reset time. The background job ends as `blocked`, `stopped` or
  `failed` and does not retry.
- **Inferred, not reproduced:** that a live session waiting at the limit shows `state: blocked` like a permission
  wait (the transcript tail tells them apart), that a message wakes it, and that `--bg --resume` after the reset
  continues the step as it does after any stop.

## Limits

- In usage overage the TTL drops to 5 min, and the tick no longer prevents the miss (the coordinator cannot see this;
  accept it).
- The cron lives only in the open session and expires after 7 days: a coordinator open longer re-arms it.
- The coordinator also deletes the cron before the `/clear` notice and before the relay of an autonomous run; the
  successor arms its own when it takes over with fronts live.
