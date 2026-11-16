# Measuring: crapper, dryer, mutator

Read when you run `crap`, `dry` or `mutate`, read their output, decide whether a finding is real or noise, or a run
stops with an error.

## What the wrapper does

`clean-code-measure.py` (path in the skill core) runs from the project root:

1. Checks the tools: each checkout at its pinned SHA with no local change, the grammar libraries matching keel's
   sha256 ([tools.md](tools.md)). Anything off stops the run with the fix.
2. Checks that `.metrics/`, `target/mutation-workers/` and `target/mutator-backup/` are ignored by git, so the
   tools' outputs never dirty the repo. `/keel:clean-code` adds them.
3. Picks the network sandbox: macOS `sandbox-exec` with outbound traffic denied except to loopback; Linux `bwrap
   --unshare-net` (loopback up), else `unshare --user --net` (loopback down: a test that binds localhost fails). No
   sandbox: it refuses unless the user accepts `--no-sandbox`.
4. Finds each source file's test, runs it once with coverage inside the sandbox, and hands the tools that report and
   nothing else. crapper, left alone, merges every `coverage/**/lcov.info` on disk, and a stale report would score
   code the tests no longer cover.

## Test discovery

| Source | Test looked for |
|---|---|
| `src/x.ts` (`.tsx`, `.js`, `.mts`...) | `src/x.spec.ts`, `src/x.test.ts`, any JS/TS extension, also under `src/__tests__/` |
| `pkg/x.py` | `pkg/test_x.py`, `pkg/x_test.py`, then `tests/test_x.py` in each folder up to the root |

Another layout: pass `--test <path>` with a single file. No test found: `crap` scores its functions at 0% coverage
and `mutate` reports `no test`. Write the test first.

## Coverage per runner (never installed by keel)

| Runner | Found by | Coverage command (LCOV) | Needs |
|---|---|---|---|
| Jest | nearest `jest.config.*` up from the test, `node_modules/.bin/jest` | `jest -c <config> <test> --ci --silent --runInBand --coverage --coverageReporters=lcov --coverageDirectory=<out>` | nothing extra: Jest ships coverage |
| Vitest | nearest `vitest.config.*` or `vite.config.*` (and no Jest config) | `vitest run --config <config> <test> --no-file-parallelism --coverage.enabled=true --coverage.reporter=lcov --coverage.reportsDirectory=<out>` | `@vitest/coverage-v8` or `-istanbul` in the project |
| pytest | `.venv/bin/python`, `venv/bin/python`, else `python3` | `python -m coverage run -m pytest -q -x <test>`, then `python -m coverage lcov` | `pytest` and `coverage` in the project's environment |

The mutator kills a mutant with the same command without coverage (`jest ... --runInBand`, `vitest run ...`,
`python -m pytest -q -x <test>`). The Jest path was measured; the Vitest and pytest commands follow each tool's
documented flags and were not measured on a real project yet.

## What each number is

- **CRAP** (crapper): `CC² × (1 − coverage)³ + CC` per function. `CC` is cyclomatic complexity: `if`, loops,
  `catch`, `?:`, each `case`, `&&`, `||`, `??` and `?.` in TS/JS; `if`, `elif`, loops, `except`, each `match` case,
  comprehension filters, conditional expressions, `and`/`or` in Python. Coverage uses the LCOV branch records inside
  the function when there are any, else line hits. Since CRAP >= CC, a function with CC >= 10 fails even fully
  covered: it has to split. Top-level arrow functions, class methods and inline Express handlers are entries;
  other nested callbacks count in their enclosing function.
- **Duplication** (dryer): per function, the structural fingerprint keeps called names, operators and tree shape and
  drops locals, fields, literals and keywords; the score is the Jaccard similarity of two fingerprints. Pairs >= 0.8,
  forms of at least 4 lines (the tool's default). The wrapper leaves out pairs where both sides are constructors that
  only declare injected dependencies: wiring, not logic.
- **Mutants** (mutator): `true`/`false`, `==`/`!=`, `===`/`!==`, `<`/`<=`, `>`/`>=`, `+`/`-`, `*`/`/`,
  `&&`/`||`, `??` to `||`, `?.` to `.`, deleting `!` and unary `-`, `0`/`1`; Python spelled `and`/`or`, `not`,
  `True`/`False`. Killed when the test fails or times out (10× the baseline, at least 2 s); survived when it passes;
  uncovered sites are not run. After the first run it is differential: it reruns survivors and the functions whose
  text changed. `mutate --diff` restricts the run to the functions the diff touches (untracked files: all of them).

## Outputs

- `.metrics/crap.edn`, `.metrics/dry.edn`, `.metrics/mutate/*.edn` (the mutator's history, which makes the next run
  differential), `.metrics/keel/coverage/` (the reports generated here).
- `target/mutation-workers/run-*`: one overlay per file being mutated (a private copy of that file and of what
  imports it relatively, the rest linked); removed when the file finishes, and by the wrapper after a timeout.
- `--json` prints the summary the gate reads: per file, status, sites, killed, survivors with line and mutation,
  uncovered and seconds.

## Measured cost (TypeScript monorepo, Jest, 10 cores, Nov 2026)

| File | Functions | CRAP >= 10 | Pairs in its folder | Mutants | Mutator time |
|---|---|---|---|---|---|
| backend service, 264 lines, 28 tests | 6 | 0 | 5 (34 constructors left out) | 43: 21 killed, 22 survived | 25 s first run, 19.5 s rerun, 14.7 s one function |
| pure helper, 65 lines, 10 tests | 3 | 0 | 13 | 28: 20 killed, 6 survived, 2 uncovered | 17.5 s |
| React component, 88 lines, 6 tests | 1 | 1 (CC 12, 90.9% → 12.1) | 79 | 12: 7 killed, 2 survived, 3 uncovered | 17.6 s |

- Coverage of one test file: under 1.5 s. crapper: 0.08 s. dryer: under 1 s for a 14,000-line library, 75 s and
  about 8,000 raw pairs for 229,000 lines (run it on the change, not on the whole repo).
- Workers: 10 parallel Jest runs peaked at 8.4 GB for the same 28 s as 4; 4 workers with `--runInBand` peaked at
  1.4 GB in 24 s. The wrapper uses `min(4, cores / 2)` workers and runs each test in band.
- Most of the per-file time is the test runner's start-up, paid per mutant batch; a function alone still costs
  about 15 s. The gate's default budget is 600 s for at most 10 files.

## Noise to triage before acting

- **Projection under a mocked client**: `select: { field: true }` mutated to `false` survives when the test mocks
  the database client, because the mock ignores the projection. Kill it with an assertion on the query the code
  sends only when the projection matters (a field that must not leak, a field the caller needs); otherwise it is
  known noise. In the measured service, 12 of 22 survivors were this.
- **Equivalent mutant**: a change that can't alter behavior (`>=` vs `>` on a value that never equals the bound).
  Justify it in one line where you report the run; don't write a test that asserts nothing to kill it.
- **Wiring**: constructors, module registration, re-exports. Duplication there is structure, not logic.
- **A component with CC >= 10**: coverage can't save it; split the rendering branches into smaller components or
  move the decisions into a tested pure function.

## When it stops

| Message | Fix |
|---|---|
| tools not ready | `/keel:clean-code` (step 5), or `python3 <measure> install` with the user's yes |
| `.metrics/` not ignored by git | `/keel:clean-code` adds the lines |
| no network sandbox | install bubblewrap (Linux), or the user accepts `--no-sandbox` |
| the test fails or doesn't run | fix the test first; a red baseline measures nothing |
| Vitest has no coverage provider / Python lacks coverage | the project adds the dev dependency; keel never installs it |
