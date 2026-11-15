---
name: web-platform
description: Modern web platform for any web screen, product or site: Baseline support policy, forms and autofill, accessibility (announced errors, text scale, forced colors), INP, bfcache, Speculation Rules, view transitions, dialog/popover/anchor positioning, modern CSS, Temporal and time zones, client security (CSP, Trusted Types, SRI, sanitizing, passkeys), mapped to Next.js App Router and React 19. Use when writing or reviewing HTML, CSS or client JavaScript. A project's own frontend skill wins where it is more specific.
---

# Web platform

The browser already ships most of what teams hand-build: modals, popovers, positioning, validation, transitions,
sanitizing, scheduling. Using the platform gives accessibility and performance for free and removes code. The detail
lives in `references/`: open only the one the step needs.

## The rules that always hold

1. **Platform before library.** Before writing JavaScript for a modal, popover, tooltip, select, validation,
   animation, date math or sanitizer, check the native feature and its status ([baseline](references/baseline.md)).
2. **Status from the source, with a date.** A support claim comes from webstatus.dev or MDN, checked that day. The
   project's declared Baseline target decides; without one, "widely available". Below it, feature detection and a
   working fallback, polyfills loaded only when missing, pinned and self-hosted or with SRI.
3. **Security and isolation first.** In doubt: security, tenant isolation, data protection, then performance. No
   token or personal data in browser storage, URLs, logs or analytics; HTML from users is sanitized; every client
   cache key carries the tenant ([security](references/security.md)).
4. **Accessible by construction.** Native elements first, names on every control, errors announced, focus managed,
   text that scales, forced colors and reduced motion respected ([accessibility](references/accessibility.md)).
5. **Interaction under 200 ms.** Handlers do the next frame's work and yield the rest; measure INP in the field before
   and after ([performance](references/performance.md)).
6. **The user's input is never lost.** Not by a reset, a stale cache, a failed read turned into a default, a
   navigation or a closed tab ([forms](references/forms.md), [react-pitfalls](references/react-pitfalls.md)).
7. **Explicit time zones.** Moments in UTC, calendar facts as plain dates, every display in a named zone
   ([dates](references/dates.md)).
8. **Translate to the framework.** In Next.js or React, read how the framework already does it before adding the raw
   platform version ([next-react](references/next-react.md)).
9. **Verify on the rendered screen**, keyboard and screen reader included, per web-craft's
   [verification](../web-craft/references/verification.md).

## The flow

1. Read the project's Baseline target, framework version and its own frontend skill.
2. For each feature the change needs, open the reference, take the platform path and its status.
3. In a framework, check [next-react](references/next-react.md) for conflicts.
4. Write the fallback where the status is below the target; test with the feature off.
5. Verify: keyboard, screen reader names, 200% zoom, forced colors, reduced motion, slow device for INP.

## References (read when…)

| File | Read when |
|---|---|
| [references/baseline.md](references/baseline.md) | deciding if a feature can ship, declaring browser support, browserslist or lint for it |
| [references/forms.md](references/forms.md) | any form: autofill, validation, one-time codes, Enter with IME, field sizing, switch, not losing input |
| [references/accessibility.md](references/accessibility.md) | announced errors, names and roles, text scale and zoom, forced colors, focus, motion |
| [references/ui-primitives.md](references/ui-primitives.md) | dialog, popover, invoker commands, anchor positioning, custom select, container queries, `:has()`, subgrid, layers, color, entry/exit animation |
| [references/performance.md](references/performance.md) | INP, long tasks, yielding, `content-visibility`, image/script priority, bfcache, Speculation Rules, view transitions, scroll-driven animation |
| [references/security.md](references/security.md) | untrusted HTML, URLs and origins, CSP, Trusted Types, SRI, cookies and storage, passwords, passkeys, federated sign-in |
| [references/dates.md](references/dates.md) | storing, computing or showing dates, times, durations, time zones, Temporal and Intl |
| [references/next-react.md](references/next-react.md) | applying any of the above in Next.js App Router or React 19 |
| [references/react-pitfalls.md](references/react-pitfalls.md) | React Compiler, react-hook-form, Server Actions, route handlers, client data layer, forms that lose input, tests |

## What fails a review

- A hand-built modal, focus trap or Esc handler where `<dialog>` does it; `role="dialog"` on a native dialog.
- A feature below the project's Baseline target with no fallback, or a support claim with no source and date.
- A polyfill or script from a CDN without a pinned version and SRI.
- `innerHTML` with user content; a URL from data without a scheme allowlist; a token in `localStorage`.
- A client cache key, realtime room or query without the tenant.
- `:invalid` styling before the user typed; an error that is only red; focus not moved on a failed submit.
- An `unload` listener; speculation or prefetch of a URL that changes state.
- A date shown in the browser's zone by accident; date math with `Date` across DST.
- `{...register()}` or `watch()` under the React Compiler; a Server Action that throws for an expected failure.
