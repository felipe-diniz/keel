# React and App Router pitfalls

Read when a React 19 or Next.js App Router screen loses typed input, shows stale data, freezes a field, works in dev
but not in production, or when turning on the React Compiler, writing a form with react-hook-form, a Server Action, a
route handler or a client data layer.

Lessons from production incidents, generic to any project on these stacks. Version-tied items say the version; re-check
on upgrade. Framework facts checked on 2026-11-15 are in [next-react.md](next-react.md).

## React Compiler (1.0 stable since 2025-10; opt-in)

- Run it in development exactly as in production. Rules-of-React violations fail no lint, build or unit test; they
  break silently in the running app.
- New code does not add `useMemo`/`useCallback`/`memo` by hand; existing ones stay until measured.
- `'use no memo'` is a temporary debugging tool, not a fix; `compilationMode: 'annotation'` turns the gain off.
- Render must be pure: no impure call (`Date.now()`, `Math.random()`, registering into a library map) during render;
  the compiler memoizes a call to a stable function and runs it once.
- Refs: write the "latest value" ref in an effect, never in the body; a ref read during render is state in disguise
  (`useState`).
- Bail-outs are silent and per component: `??=` inside a component, `try/finally` (babel plugin 1.x), and a library
  flagged as incompatible skip the whole component. The compiler reports the first problem only; a second one hides
  behind it. Measure with the plugin's logger (what compiled, why the rest did not), never by reading code.
- Do not rewrite `try/finally` to `try/catch` without a measured gain: an early `return` inside `try` then skips the
  cleanup (a button stuck on "Saving...").
- Lint with `eslint-plugin-react-hooks` v6+ (rules `purity`, `refs`, `immutability`, `incompatible-library`,
  `set-state-in-render`, `static-components`); start as warnings, measure, then gate.
- Unit tests usually transform without the compiler and pass where production fails. Add a test target that runs the
  compiler, with a negative-control probe that must fail with the real symptom.
- Experimental Rust compiler in Next 16.x (`experimental.turbopackRustReactCompiler`): two miscompiles were observed
  (a JSX tag shadowed by a variable rendered as `<section_2>`; a form with `watch` compiled wrong). Off unless tested.
- `panicThreshold` above `'none'` in CI fails on correct code.

## react-hook-form 7.x with the compiler

- Bind fields with `<Controller>`; ban `{...register()}`. `register()` writes to a library map during render; the
  compiler runs it once, `reset()` clears the map, and the field is orphaned: it looks filled, submit says "required".
- `watch()` in render makes the compiler skip the whole component, which hides the `register` bug until `watch` is
  removed. Migrate to `useWatch({ control, name })` and `useFormState({ control })`, placed before any early return.
- Lint the ban with `no-restricted-syntax` covering spread, qualified spread, assignment, alias
  (`{ register: field }`) and computed keys; add a grep guard.
- Do not call `useController` in the form body (re-renders the whole form per keystroke); `<Controller>` isolates it.
- Optional field `value={field.value ?? ''}`; checkbox `checked={field.value}` with
  `onChange={(e) => field.onChange(e.target.checked)}`, not `{...field}`.
- A step with its own `useForm` is its own component: two forms in one component with the second in a branch freeze
  the field, with no error.
- One validation source (the schema), not native constraints inside custom controls. Map API errors with
  `setError(field | 'root')`. Disable submit on `isSubmitting`. Type the form from the schema or shared contract.

## Server and client boundary

- A function exported from a `'use client'` module cannot be called on the server (runtime error, invisible to `tsc`
  and jsdom). Shared pure helpers live in a module without a directive.
- Server-only data code imports `server-only` so a leak into the client bundle fails the build.
- Pass a promise to a client island and let it suspend instead of awaiting in the page.
- A barrel that re-exports a `'use server'` file breaks jsdom suites (`Request is not defined`): import by sub-path.
- `redirect()` and `notFound()` throw: no `catch` may swallow them; rethrow navigation errors first in every `catch`.
- A Server Action never throws for an expected failure (the message is masked in production); it returns
  `{ ok: false, errorCode }` and the client translates by code. An expired session in an action returns a structured
  result, not a proxy redirect (the client expects a Flight response and crashes).
- 401 is session loss, 403 is a message on screen. Do not navigate away on session loss when the screen holds unsaved
  work: open sign-in over it, and restore the work only for the same user and tenant.

## Route handlers and the backend-for-frontend

- `encodeURIComponent` every dynamic param interpolated into a backend path: Next delivers params decoded, and
  `..%2F` reaches another endpoint with the user's credentials.
- Forward payloads whole (validated), not field by field: a new contract field is silently dropped and the form
  "saves". The same for errors: forward the error code, not only the message. Only an end-to-end test across the BFF
  catches both.
- Errors expose an allowlist of public scalar fields; never raw backend text or the exception object.
- Session renewal happens on user use, by the BFF swapping the cookie; background requests and prefetch do not renew.
- Private requests: `cache: 'no-store'`. A second read in the same render needs its own `signal`, or Next dedupes it
  and returns the first response.

## Client data layer

- Components call a service, never `fetch` directly.
- Every client cache key includes the tenant, plus page, limit and filters; clear per tenant on switch. A key without
  the tenant shows one company's data to another (the `lgpd` skill's isolation hunt).
- Short TTL with in-flight dedupe; invalidate on domain events and immediately on local mutation.
- "Does not exist" is only what the server said. A failed read locks the UI with retry; it never becomes "empty" or a
  default that a later save writes back (a failed preference read saved as "off").
- Gates derived from loaded data fail closed on failure and show an error with retry, never the upsell; they may
  render optimistically only while loading.
- Apply overlapping responses in order (a request counter ref); discard a response from an older request.
- A global loading flag that swaps the tree is for the first load only; on background reloads it unmounts the page
  with its open modal and typed input.
- A realtime event merges into local state or bumps a refetch key; it never triggers `router.refresh()` or
  `revalidatePath`.

## Forms that keep the user's input

- Seed a form in the `useState` initializer from what exists at mount; an effect leaves one empty render that a fast
  user or an autosave catches.
- An async seed respects a per-field "edited" ref written in the handler; render state is too late.
- `setState` updaters stay pure: StrictMode calls them twice. Test under `<StrictMode>`.
- A component that emits its state to the parent and receives it back must not emit the empty state at mount.
- An autosave that skips empty forms must still send "empty" when the server may hold content.
- Do not open an editor over data that has not arrived: start in loading, with a deadline and a visible label.
- Leaving the page saves with `keepalive` ([forms.md](forms.md) §Not losing input).

## Time zones

- Every date uses an explicit zone from the server (tenant or user); never `timezone || local`
  ([dates.md](dates.md)).

## Accessibility in components

- Icon fonts are text in the accessible name; custom selects label the trigger ([accessibility.md](accessibility.md)).
- Warnings in a filter row go below the row, not inside it (they move the next control under the cursor).

## Bundle

- Import heavy shared components by sub-path; read-only screens do not import an editor; lazy-load editors.
- Split i18n dictionaries between public and app bundles by weight.

## Tests that see these bugs

- jsdom does not apply `maxlength`, does not separate server and client, runs effects together under `act`: races and
  boundary errors need end-to-end tests, repeated N times against the measured failure rate.
- End-to-end form tests assert the payload that leaves the browser, not only the screen.
- Fire realtime-style events outside `act` to reproduce timing windows.
- An error-path test carries a positive control.
