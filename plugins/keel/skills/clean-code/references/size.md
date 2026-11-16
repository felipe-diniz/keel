# File size

Read when a file is close to or above its ceiling, when the size warning fires after an edit, when you create or
change `size-budget.json` or the lint block, or before splitting a file.

## The rule

- A new file is born with one responsibility and up to **1,000 lines**.
- A file that was already above that on the day of the baseline keeps its own ceiling in `size-budget.json`, and the
  ceiling only goes **down**. What fails is regression, not history.
- Lines are counted as ESLint's `max-lines` counts them with blank lines and comments included: the file's lines,
  without the empty line after the final newline. A comment diet also shows in the number.
- Function length (150 lines) and cognitive complexity (15) are warnings: they measure, they don't block. The
  function's measure is CRAP < 10 ([measure.md](measure.md)).

## Why 1,000

- The agent reads a file through a tool that returns at most about 25,000 tokens per call (256 KB for a whole file);
  1,000 lines of typical TypeScript or Python fit in one read and one review. Above that the agent reads in pieces
  and loses the middle.
- After compaction, only files of up to about 5,000 tokens are re-read on their own; a big file has to be reopened.
- Long inputs degrade recall of their middle ("Lost in the Middle", Liu et al.; context rot, Chroma 2025), and a
  preprint found file length matters more than cyclomatic complexity for LLM code tasks. Obfuscated or generic names
  hurt as much.
- No study fixes 1,000 as the ideal: it is a decision (the plugin owner's, Nov 2026) that keeps every file readable
  whole. Robert C. Martin keeps the principles and says the thresholds may move for agents; he has not stated a
  file size.

## `size-budget.json`

At the project root, versioned, read by the lint, the ratchet script and keel's edit hook:

```json
{
  "keel": 1,
  "defaultMax": 1000,
  "extensions": [".ts", ".tsx", ".js", ".py"],
  "ignore": ["**/node_modules/**", "**/generated/**", "**/migrations/**/*.sql", "**/*.spec.*", "**/tests/**"],
  "script": "scripts/size-budget.py",
  "files": { "src/legacy/big-service.ts": 1412 }
}
```

- `ignore` is the project's call: by default it skips dependencies, build output, generated code, lock files, SQL
  migrations, minified files, type declarations and tests. Remove a pattern to count it.
- `files` holds only files above `defaultMax`. An entry never goes up by a tool: raising one is a hand edit, visible
  in the diff, with the reason in the commit message.

```bash
python3 scripts/size-budget.py            # report; exit 1 when a file is above its ceiling
python3 scripts/size-budget.py --update   # lower ceilings after shrinking, drop entries that fit the default
python3 scripts/size-budget.py --init     # first baseline (refuses when the JSON exists)
```

`/keel:clean-code` writes the budget, the script and the `.gitignore` lines. Rerunning it keeps every ceiling already
lowered; a file that grew past its ceiling is reported, never re-baselined. Adopting a budget written before the
package (no `keel` key) adds the files above 1,000 that the old scope didn't cover, and lists them.

## Enforcement per stack

| Stack | What fails | Where |
|---|---|---|
| ESLint flat (TS, Angular, Next, React, Vue) | `max-lines` error from the budget, one override per own ceiling | the block `/keel:clean-code` prints, in `eslint.config.*` |
| ESLint legacy (`.eslintrc.js`) | the same through `overrides` | idem; a JSON/YAML config can't read the budget: convert it to `.js` or regenerate the overrides after each `--update` |
| Python, or any stack without ESLint | `python3 scripts/size-budget.py` | the project's pre-commit and CI |

- The lint block reads `ignores` from the budget, so the lint and the script count the same files.
- `sonarjs/cognitive-complexity` needs `eslint-plugin-sonarjs`; without it the block leaves the rule out. Adding the
  dependency is the project's decision.
- With a lint cache keyed on inputs (Nx, Turborepo), `size-budget.json` must be an input of the lint target, or a
  lowered ceiling won't re-run the lint.
- After each edit, keel's hook counts the edited file against its ceiling (or 1,000 without a budget) and tells the
  agent when it passed it, or when a file without its own ceiling reached 90%. It never blocks.

## When a file crossed, or is about to cross, its ceiling

1. Don't add to it. What you were adding goes to its own file when it is another responsibility, and that is
   usually the case: a file at its ceiling already does too much.
2. Find the seams by responsibility, not by line count: a group of functions that change for the same reason and
   share data. Candidates: a sub-flow with its own name (billing inside an appointment service), a pure helper
   (formatting, parsing, calculation), a read-only query or report, an adapter to an external system.
3. Extract a module only when the group is cohesive and stands on its own. A private step of one flow stays with the
   flow's owner; extracting early trades complexity for indirection. Lowering a line count is not a reason to
   extract.
4. Pin the behavior before moving code ([refactor.md](refactor.md)), move, run the same tests, then
   `python3 scripts/size-budget.py --update` to lower the ceiling in the same commit.
5. Never: split into `part1`/`part2`, move code to an ignored folder, mark it generated, minify it, or raise the
   ceiling to fit the change.

## Clean as you pass

Duplication, misplaced code or a broken rule found on the way of the task:
- Small (about 30 lines or fewer, at most 2 files, outside critical risk): fix it with the task and list it in the
  delivery summary.
- Large (a change in many places, a module extraction, a new owner for some data): don't do it inline unasked;
  record it where the project keeps technical debt, with `file:line` and the proposal, and say so in the delivery.
- Never silent: fix and tell, or record and tell.
- In a critical-risk domain this doesn't apply: changes there go through the project's critical review.
