# Responsiveness and navigation

Read when an interaction feels slow, INP is over budget, a long list or heavy screen janks, a handler does a lot of
work, or when adding prefetch/prerender, view transitions, scroll-driven effects, image or script priority, or
anything that may block the back/forward cache.

Status checked on webstatus.dev on 2026-11-15 ([baseline.md](baseline.md)). Page-load budgets for public pages
(LCP, CLS, fonts, hero image, WebGL) are in web-craft's
[performance.md](../../web-craft/references/performance.md); thresholds live there.

## Diagnose INP before changing code

- INP is judged at p75 of field data, per device class.
- Split each slow interaction into input delay (other JavaScript running), processing (the handlers) and presentation
  delay (style, layout, paint until the next frame). Fix the largest part.
- Field attribution: `web-vitals/attribution` `onINP`, sent with `navigator.sendBeacon`; use `interactionTarget` and
  `longestScript` (`sourceURL`, `sourceFunctionName`, `forcedStyleDuration`, `forcedLayoutDuration`).
- Long Animation Frames (limited: Chromium 123; feature-detect in `PerformanceObserver`): aggregate by `sourceURL` in
  a bounded `Map`, send a summary. Fixing what Chromium shows helps every engine.
- Event Timing is newly available (Safari 26.2, 2025-12-12); INP is not measurable without it.
- High style time: expensive selectors or wide invalidation. High layout time: thrashing (batch reads before writes),
  a large DOM, missing containment.
- Lab data finds causes; it does not replace field data.

## Keep handlers short

- In the handler do only what the next frame needs (the visible state change); defer the rest (counting, saving,
  analytics, spellcheck).
- Break tasks over 50 ms: inside a loop, `await scheduler.yield()` against a 50 ms budget recomputed after each yield.
  Without `await` it does not yield.
- `scheduler` is limited (Chromium 129, Firefox 142, no Safari): detect `'scheduler' in window && 'yield' in scheduler`,
  fall back to `await new Promise((r) => setTimeout(r, 0))`.
- `scheduler.postTask(fn, { priority })`: `user-blocking` for input and critical render, `user-visible` (default),
  `background` for analytics and prefetch. Detect `'postTask' in scheduler`.
- Use `scrollend` (newly) for heavy work after scrolling; `scroll` only for light feedback.

## Render less

- `content-visibility: auto` (newly since 2025-09-15) on large, self-contained blocks fully below the fold, always
  with `contain-intrinsic-size: auto <estimate>`; never above the fold.
- `content-visibility: hidden` for inactive cached views keeps their state but removes them from the accessibility
  tree and find-in-page; use `hidden="until-found"` when they must stay searchable. Cached SPA views need an eviction
  limit.
- Test Tab navigation across skipped blocks.
- Long tables and lists: paginate or virtualize; containment helps visible heavy items (kanban columns, drag and drop).

## Priority of images and scripts

- `fetchpriority` is newly available (2024-10-29). `high` on the LCP image only (one or two at most); never with
  `loading="lazy"`. `low` for hidden above-the-fold images (carousel slides). Omit for normal priority.
- `loading="lazy"` on images and iframes below the fold (widely). On `<video>`/`<audio>` it is limited (Chromium):
  combine with `preload="none|metadata"` and an IntersectionObserver fallback.
- Always set `width` and `height` (or a fixed aspect box).
- Scripts: `fetchpriority="low"` with `async`/`defer` for analytics, ads and widgets; `high` on at most one or two
  async scripts critical to interaction.

## Back/forward cache

- Every engine has one; a page that is not eligible reloads on Back.
- Blockers: `unload` listeners, `Cache-Control: no-store` on the document, open IndexedDB/WebSocket/WebRTC
  connections or in-flight requests (varies by engine), `window.opener` links, an unconditional `beforeunload`.
- Use `pagehide` instead of `unload`; `Permissions-Policy: unload=()` forbids it in Chromium.
- Add `beforeunload` only while there are unsaved changes, and remove it after saving.
- Close connections on `pagehide` and reopen on `pageshow`. On `pageshow` with `event.persisted`, refresh what may be
  stale or sensitive (a session that ended, a tenant switch).
- `no-store` stays on pages with personal data when a restored copy would show it after logout; the cost is the
  bfcache.
- Test: DevTools Application > Back/forward cache > Run test; `NotRestoredReasons`. Count restores as page views.

## Speculation Rules (limited: Chromium)

- Progressive enhancement: other engines ignore the rules.
- Prefer document rules (`where` + `href_matches`/selectors) with `moderate` or `conservative` eagerness; start with
  `prefetch`, measure, then consider `prerender`.
- Never speculate URLs that change state (logout, add to cart, accept, mark as read) or whose GET has side effects;
  exclude with `not` and a `.no-prerender` class.
- Prerender runs the page: defer analytics, sign-in prompts and writes until activation (`document.prerendering`,
  `prerenderingchange`). The server sees `Sec-Purpose: prefetch` or `prefetch;prerender`.
- Authenticated, per-tenant pages: prerender only what the same session would render; a tenant switch or logout must
  clear speculations (`Clear-Site-Data: "prefetchCache", "prerenderCache"`).
- Inline rules need the CSP nonce or hash. Not for SPA soft navigations. In Next, read
  [next-react.md](next-react.md) §Prefetch first.

## View transitions

- Same-document `document.startViewTransition` is newly available (2025-10-14). Fallback:
  `if (!document.startViewTransition) update()`.
- Cross-document `@view-transition { navigation: auto }` is limited (Chromium 126, Safari 18.2): opt in on both pages,
  same origin; without support the navigation is normal.
- `view-transition-name` unique per element (duplicates silently cancel); remove temporary names on `finished`;
  animate only primary content; move focus to the new heading after.
- Wrap in `prefers-reduced-motion: no-preference`.
- In React, the framework calls it ([next-react.md](next-react.md) §View transitions).

## Scroll-driven animations

- Newly available since 2026-10-27 (Firefox 159): keep the fallback for a while. Wrap in
  `@supports ((animation-timeline: view()) and (animation-range: entry))` and `prefers-reduced-motion: no-preference`.
- Animate only `transform` and `opacity`; declare `animation-timeline` after the `animation` shorthand.
- Fallback: IntersectionObserver for view progress, or nothing for decoration. The content is visible without it.

## Streaming HTML

- Native out-of-order HTML (`<template for>`) is limited (Chromium 150). Frameworks with streaming (React Suspense)
  already do it; do not add it on top ([next-react.md](next-react.md) §Streaming).
- Stream the above-the-fold content first; placeholders keep the final size; `aria-busy` on the container.

## Sources

- Guides `performance/*` and `ui-behaviors/*-transitions`, `scroll-entry-exit-effects` in
  https://github.com/GoogleChrome/modern-web-guidance (read 2026-11-15)
- https://web.dev/articles/inp, https://web.dev/articles/optimize-inp, https://web.dev/articles/bfcache
- https://developer.chrome.com/docs/web-platform/prerender-pages
- https://api.webstatus.dev/v1/features/ (scheduler, long-animation-frames, event-timing, content-visibility,
  speculation-rules, view-transitions, cross-document-view-transitions, scroll-driven-animations, template-for)
