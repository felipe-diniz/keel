# When a number breaks, and how to refactor

Read when a function is at or above CRAP 10, dryer reports a pair at or above 0.8, a mutant survives, or before any
refactoring.

The order follows ub-mode: first make it work (the change and its tests), then make it right (these numbers), then
practice (small commits that say why and how it was proven). Don't chase numbers before the behavior is right.

## Refactoring protocol

1. **Pin** what the code does: a test that calls it the way its user does and asserts what the user sees. When the
   code has no test, write a characterization test of the current behavior first, including the odd parts.
2. **Change the structure** in small steps, each one green. No behavior change mixed into a refactoring commit.
3. **Prove** nothing changed: the same tests, unchanged, pass; `crap` and `mutate --diff` on the touched files are
   no worse than before.

Moving code between files keeps its tests passing without edits to their assertions. If an assertion has to change,
behavior changed: stop and separate the two.

## CRAP at or above 10

CRAP grows with complexity squared and with what the tests don't reach. Two levers, often both:

| Situation | Do |
|---|---|
| CC small (< 10), coverage low | Test the uncovered branches through the public behavior. The cheapest fix. |
| CC >= 10 | Split: coverage alone can't bring CRAP under CC. Extract each decision into a named function that does one thing, or replace the conditional chain with data (a lookup table, a map of handlers). |
| A long `switch`/`case` on a closed set | Consider whether it is worth reducing: one case per value, each trivial, reads well. If the cases carry logic, move each into its own function or a table. |
| Nested conditionals | Guard clauses for the edge cases first, then the main path flat. |
| A React/Angular component | Move the decisions out of the render into a pure, tested function; split independent branches into child components. |

A split that only moves the complexity into one private helper with the same CC fixes nothing; each piece must be
simpler and nameable.

## Duplication at or above 0.8

First decide whether it is one decision or a coincidence:

- **The same decision in two places** (same rule, same reason to change): remove it. The decision lives in one place
  and the others call it. Typical case: several request functions that each repeat "send, check the status, read the
  error body, throw a message" become one request helper; each caller keeps only what differs (the URL, the payload,
  the message).
- **Coincidental shape** (two flows that look alike today but change for different reasons): keep both and justify
  it in one line in the commit or the delivery summary. Merging them couples two things that will diverge.
- **Wiring** (constructors that only receive dependencies, module registration): not duplication; the wrapper already
  leaves injection-only constructors out.

Removing duplication is a refactoring: pin both callers' behavior first. Never "fix" a pair by renaming locals or
reordering lines to fool the fingerprint.

## Surviving and uncovered mutants

| Result | Means | Do |
|---|---|---|
| Survived | the tests run that line and pass with it broken | add the assertion that fails with the mutant: the case at the boundary (`<` vs `<=`), the branch the `&&`/`||` changes, the value `0`/`1` decides |
| Uncovered | no test reaches the line | cover it through public behavior, or, if nothing can reach it, it is dead code: delete it |
| Survived, can't be observed | an equivalent mutant (no input changes the result) or code that has no effect | if equivalent, justify in one line; if no effect, delete the code |
| Survived on a projection under a mocked client | the mock ignores the field list | assert on the query only when the projection matters (a field that must not leak, a field the caller uses) |

- Kill a mutant with an assertion on behavior, never on implementation details (call counts, private state) unless
  the call is the behavior (a payment request sent once).
- Tests are double-entry bookkeeping: the code says what it does, the test says it again from the outside. A test
  that would still pass if every function returned nothing proves nothing: throw it out (ub-mode).
- If an honest test is impractical, don't write a bad one: say what is not covered and why.

## Fix the cause, then subtract

- Reproduce the failure, fix its cause, and keep the reproduction as a test. A guard that hides the crash is not a
  fix.
- When two fixes built on the same premise fail the same check, write the premise in one sentence and question it
  before a third attempt.
- Before adding, take out: dead code the mutator found, duplication, a layer that only forwards. A new requirement
  doesn't get bolted on: ask what the design would be if it had been there from the start, and get there in pieces.

## Before saying it is done

On the files the change touched: their tests green; `crap` with nothing at or above 10 that the change introduced or
made worse; `dry` on the change with each pair removed or justified; `mutate --diff` with the survivors killed,
deleted or justified; the size warning silent. Report each number with the command that produced it. Pre-existing
debt found on the way follows "clean as you pass" in [size.md](size.md).
