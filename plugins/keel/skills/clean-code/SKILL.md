---
name: clean-code
description: Clean code with numbers, equal in every project. One responsibility per file, new files up to 1,000 lines and a ratchet for existing ones, functions doing one thing with grep-able names, CRAP < 10, structural duplication >= 0.8 removed or justified, behavior tests, surviving mutants killed, refactoring with behavior pinned first. Measured by Robert C. Martin's crapper, dryer and mutator, pinned and offline. Use when writing, refactoring or reviewing code. A project's architecture skill wins where more specific.
---

# Clean code

Principles adapted from Robert C. Martin's ub-mode (github.com/unclebob/ub-mode, MIT) and measured with his tools
(crapper, dryer, mutator; 0BSD). The project's own architecture or test skill wins where it is more specific; this
skill gives the floor every project shares. Security, tenant isolation, data safety and performance come before any
of these numbers.

## The rules and their numbers

| Rule | Limit | Measured by | When it breaks |
|---|---|---|---|
| File size | new file <= 1,000 lines; a file already above keeps its own ceiling, which only goes down | `size-budget.json`, the lint's `max-lines`, `python3 scripts/size-budget.py`, a warning after each edit | [size.md](references/size.md) |
| Function | CRAP < 10 (`CC² × (1 − coverage)³ + CC`) | `crap` below | test it or split it ([refactor.md](references/refactor.md)) |
| Function alarms | 150 lines, cognitive complexity 15 | lint warnings only | read them as "probably does more than one thing"; CRAP decides |
| Duplication | structural similarity >= 0.8 | `dry` below | remove it, or justify it in the commit |
| Tests | every covered mutant killed | `mutate` below | kill the survivor, cover the uncovered, or delete the dead code |

## Principles

1. **One responsibility per file.** The file's name says it. A new responsibility goes to a new file, even when the
   current one has room. Size is the symptom; the defect is a file that answers two questions.
2. **A function does one thing**, and its name says which, specific enough that `grep` finds it and only it. No
   `handle`, `process`, `data`, `utils`, `helper`, `manager`. One decision lives in one place: two functions answering
   the same question with different criteria is a bug, not a style.
3. **Data shape before logic.** Make the illegal state impossible to write. Parse outside data once, where it enters;
   inside, trust it. Business logic lives in pure functions; I/O at the edges.
4. **Test behavior, not implementation.** The test calls the code the way its user does and checks what that user
   would see. If the test would still pass when every function returned nothing, throw it out (ub-mode). Mock the
   boundary, not the unit under test.
5. **Refactor with behavior pinned.** Pin what the code does with a test, change the structure, prove the behavior
   did not change. Subtract before you add. Fix the root cause; a guard that hides the crash is not a fix.
6. **Numbers are evidence, not the goal.** Never split a file in "part 1/part 2", hide code in an ignored folder,
   raise a ceiling or write a test that only executes lines to move a number.

## Measuring

The tools run through keel's wrapper, from the project root. It checks the pinned checkouts and grammar hashes,
cuts the network (macOS `sandbox-exec`, Linux `bwrap`/`unshare`), generates coverage from each file's own test with
the project's runner (Jest, Vitest, pytest; it never installs anything) and keeps outputs in git-ignored folders.

```bash
M="${CLAUDE_SKILL_DIR}/../../scripts/clean-code-measure.py"
python3 "$M" status                      # tools installed and verified? sandbox?
python3 "$M" crap src/a.ts src/b.ts      # CRAP per function; lists the ones >= 10
python3 "$M" dry                         # pairs >= 0.8 among the files changed vs HEAD (or name paths)
python3 "$M" mutate --diff src/a.ts      # mutants in the functions the diff touches
```

When: after the code works and its tests pass, before saying it is done, on the files you changed: `crap` and
`mutate --diff` on production files, `dry` on the change. Cost measured on a TypeScript monorepo (10 cores): `crap`
about 1 s per file with its test, `dry` under 1 s per library, `mutate` 15 to 30 s per file. Not installed or not
ready: say so and suggest `/keel:clean-code`; never install on your own, never pass `--no-sandbox` without the user.
How each number is computed, the coverage formats, the known noise and the measured costs: [measure.md](references/measure.md).

## Gate step (for `keel:critical-review`)

On the T2 production files of the slice, at most 10, the most changed first:

```bash
python3 "${CLAUDE_SKILL_DIR}/../../scripts/clean-code-measure.py" mutate --diff --json --budget 600 <files>
```

Severity of a survivor in a T2 function: **P1** when the mutated line carries the invariant (a tenant filter, an
amount, a limit comparison, a lock or idempotency check, an authorization guard); **P2** otherwise; **P3** for a
projection field (`select`/`include` `true -> false`) under a mocked client, unless the projection is the invariant.
Status `no test` on a T2 file is the finding "T2 change without a test that fails when the invariant falls";
`baseline failed` means the test is red; `not finished (budget)` goes to Scope as not measured.

## References

- [size.md](references/size.md): the 1,000-line rule and why, the ratchet, `size-budget.json`, the lint per stack,
  how to split a file that crossed its ceiling.
- [measure.md](references/measure.md): what each tool computes, coverage per runner, test discovery, outputs,
  sandbox, measured costs and the noise to triage.
- [refactor.md](references/refactor.md): what to do when CRAP, duplication or a mutant breaks, and the refactoring
  protocol.
- [tools.md](references/tools.md): the audit of crapper, dryer and mutator, the pins, the install and how to update.
