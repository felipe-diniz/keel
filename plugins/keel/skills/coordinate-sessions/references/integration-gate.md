# The integration gate

Read when the fronts of a round have committed and the coordinator runs the single gate, when that gate fails, or
before a push.

The fronts commit with the focused proof only (SKILL §7). The full proof (suites, build, E2E, measurement bench,
screens, what the profile lists under the integration gate) runs once, in the coordinator, over the stack of commits of
every closed front. Nine fronts, one gate.

## The stack

- The stack is the working branch itself: every front commits on it as before (direct or split mode, §6), and the
  stack is `<last gated sha>..<branch>`. No integration branch, no cherry-pick, no merge of front branches.
- The last gated sha lives in `queue.md` (`gate: <sha> green <date>`); with none, it is the remote branch
  (`@{upstream}`).
- Each front's line in `queue.md` carries `<session> <sessionId> <shas>`: that maps each commit to its front for the
  return by `--resume`.
- A project with a branch per front (profile): the integration worktree is born at the base and merges the front
  branches in closing order; the stack is those merges.

## Where the gate runs

- In the checkout itself when `git status --porcelain` is empty and no front is alive: nothing else moves the tree.
- Otherwise in an integration worktree, detached at the tip, outside the repo:
  ```bash
  TIP=$(git rev-parse <branch>)
  git worktree add --detach "$D/gate" "$TIP"
  ```
  then the steps the profile lists to prepare a worktree (install, generated files). Never copy `.env*` or credentials
  into it; when a suite needs them, the profile says how the project provides them.
- The gate holds the single-holder resources it uses (heavy suite, measurement bench, test database, ports): the
  coordinator records them in `window.md` under the gate, and nobody else takes them while it runs. A front never runs
  a full suite or measures, so there is no parallel run to split.
- Output to `$D/logs/gate-<YYYY-MM-DD>/`, one file per command; only the count and the failures enter the context.

## Green

- Write `gate: <TIP> green <date>` in `queue.md`, with the command and the log of each number.
- The push takes exactly the gated sha, `git push <remote> <TIP>:<branch>`, with the owner's yes and by the profile's
  path (§6). A commit that landed on top after the gate goes to the next gate.
- Then close each front of the stack (§3, `--close`) and remove the integration worktree
  (`git worktree remove "$D/gate"`).

## Red: find the culprit, return it, hold nobody

1. **Attribute without rerunning.** For each failing test, take the test file and the files it covers, and list the
   commits of the stack that touched them: `git log --format='%h %s' <base>..<TIP> -- <paths>`. One commit, one front:
   that is the culprit.
2. **Bisect only when attribution is ambiguous** (several fronts on the paths, or a failure with no path, such as the
   build or the bench). Bisect over the stack with only the failing command, never the whole gate:
   ```bash
   cd "$D/gate"
   git bisect start <TIP> <base>
   git bisect run <the failing command, from the profile>
   git bisect reset
   ```
   With N commits that is about log2(N) runs of one command. A commit where the command cannot run (it depends on a
   later commit of the stack) exits 125 (skip).
3. **Return it to its front.** The culprit's front is resumed with `--resume <sessionId>` (§2) and a prompt with the
   failing command, the log path, the culprit sha and "fix on top, a new commit, no amend, no rewrite". It runs its
   focused proof on the fix and reports the new sha. A front whose session cannot continue (limit, context) gets a new
   session from its HANDOFF.
4. **Hold nobody.** The other fronts keep working and committing. The next gate runs at the new tip; only the push
   waits for green.
5. **Rerun only what failed** at the new tip, plus what the fix's paths reach. The rest passed at the previous tip and
   nothing else touched those paths; when something else did, it goes in too.

## When the push goes

- After a green gate over the round, with the owner's yes, not at each front's close.
- Earlier only for what the owner marks as urgent: that front runs its own gate (as a critical front does) and the
  coordinator pushes its sha alone.

## Gate interrupted

The machine died or the limit cut it: rerun at the same TIP from the first command whose log is incomplete; the
complete logs of the same TIP count.
