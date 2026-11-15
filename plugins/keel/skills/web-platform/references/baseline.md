# Baseline support policy

Read when choosing whether a web feature can ship without a fallback, declaring a project's browser support, setting
up browserslist or lint for it, or when another reference says "newly", "widely" or "limited".

## Definitions (web.dev/baseline)

- Newly available: supported in the current stable release of every core browser (Chrome, Edge, Firefox, Safari,
  desktop and mobile).
- Widely available: 30 months after the newly date.
- Limited availability: missing in at least one core browser.
- "Baseline YYYY": the features that became newly available in that year; a project can target a year.

## Policy

- The project declares its target in CLAUDE.md or AGENTS.md: "This project's Baseline target is Baseline widely
  available" (or a year). Without a declaration, assume widely available.
- Pick the target from the real browser mix in analytics or RUM, not from taste. A B2B tool on managed desktops can
  target newer than a public site.
- A feature below the target ships only with feature detection and a working fallback (the references give one per
  feature). Polyfills load conditionally, pinned and self-hosted or with SRI, never unconditionally.
- Progressive enhancements that degrade to the normal behavior (`text-wrap: pretty`, `fetchpriority`,
  `content-visibility`, speculation rules, view transitions) can ship at any status.
- Origin trials and flagged features do not ship by default.
- Baseline is about engines, not assistive technology: accessibility is still tested.
- Restricted runtimes (Electron, Tauri, a kiosk) declare their own engine and skip the policy.

## Check a status

- Source of truth: https://webstatus.dev (API `https://api.webstatus.dev/v1/features/<id>`) and the MDN page's
  Baseline banner. Record the date checked next to the claim.
- When webstatus and MDN disagree (a feature id that aggregates sub-features, as anchor positioning), follow the
  stricter and say so.
- Never state support from memory: statuses move every month.

## Tooling

- Browserslist: `"browserslist": ["baseline widely available"]` (also `baseline newly available`,
  `baseline 2024`; add `with downstream` for Chromium-based browsers).
- CSS lint: `@eslint/css` rule `css/use-baseline` (`available: "widely" | "newly" | <year>`, allow-lists for
  exceptions); or Stylelint `stylelint-browser-compat` with the same browserslist.
- DevTools shows the Baseline status in the Elements panel; Lighthouse audits it.

## Sources

- https://web.dev/baseline
- https://web.dev/articles/use-baseline-with-browserslist
- https://github.com/eslint/css/blob/main/docs/rules/use-baseline.md
- https://webstatus.dev
