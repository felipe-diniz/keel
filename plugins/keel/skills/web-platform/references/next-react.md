# Platform guidance in Next.js App Router and React 19

Read when applying any rule of this skill in a Next.js App Router or React 19 project: where the framework already
does it, where raw platform advice conflicts, and the rule to follow. Checked on 2026-11-15 against Next 16.4 (16.4.5
is the current patch) and React 19.3; re-check on upgrade.

## Version facts that change the rules

- Cache Components (`cacheComponents: true`) is the default for new 16.4 apps and becomes the default in Next 17; it
  implements partial prerendering. Several rules below differ with it on.
- The 2026-11-03 security release fixed cross-tenant cache leaks in `use cache` (high severity). A multi-tenant app
  with Cache Components runs >= 16.4.5, and every cached function takes the tenant as an argument or a cache tag.
- `middleware.ts` is deprecated in 16 and renamed `proxy.ts` (export `proxy`, Node runtime).

## Streaming

- React already streams out of order per `<Suspense>` boundary; `loading.js` is an implicit Suspense around the page.
  Do not add native `<template for>` streaming.
- Status and headers go with the first chunk. `notFound()` after streaming starts becomes a `noindex` meta and
  `redirect()` a client redirect: decide 404 and redirects before the first boundary, or in `proxy.ts`/config.
- A proxy, CDN or compression that buffers defeats streaming (`X-Accel-Buffering: no` for nginx).
- Keep the LCP element outside and above Suspense boundaries; skeletons have the content's dimensions.
- Prefer granular boundaries near the dynamic access; a high `loading.js` paints a whole-page skeleton. Do not
  `await` `params` or `cookies()` at the top of a layout.

## Prefetch

- `<Link>` prefetches RSC payloads in memory when the link enters the viewport, in production only. `prefetch` is
  `auto` by default (static route full, dynamic route up to the nearest `loading.js`), `true` for the full route,
  `false` never. With partial prefetching on, `auto` fetches the route's shell once.
- Next has no Speculation Rules integration (no doc found; unverified absence). Keep `<Link>` as the mechanism for
  soft navigations. Add speculation rules only for hard navigations (links to other apps, full reloads), never for
  the URLs `<Link>` already prefetches, and never for routes with side effects
  ([performance.md](performance.md) §Speculation Rules).
- Prefetch executes layouts and pages: they must be pure (no analytics or writes in render).

## Images

- Use `next/image`, not a raw `<img>` with a hand-written `srcset`. Always pass `sizes` with `fill` or responsive CSS
  (without it the browser assumes `100vw`).
- `priority` is deprecated since 16 in favor of `preload`. For the LCP image use `fetchPriority="high"` or
  `loading="eager"`; `preload` only when there is a single LCP candidate on every viewport; never `preload` together
  with `loading` or `fetchPriority`.
- 16 defaults: `images.qualities` `[75]` (other values are coerced; an invalid `q` returns 400), `remotePatterns`
  instead of `domains`, `dangerouslyAllowLocalIP` false (keep it: SSRF).

## CSP, Trusted Types and SRI

- Nonce CSP: generate the nonce in `proxy.ts`, set the CSP request header; Next applies it to its scripts and to
  `<Script nonce>`. Cost: every page renders dynamically (no static, no ISR, no CDN cache) and it is incompatible with
  partial prerendering/Cache Components. Exclude `_next/static`, `_next/image` and prefetch requests in the matcher.
- With Cache Components or static pages, prefer hash-based CSP with `experimental.sri` (`sha256|384|512`, build-time,
  App Router; still experimental) or a static policy without nonce.
- Development needs `'unsafe-eval'`; production does not.
- React 19.3 passes Trusted Types objects to the DOM intact; the app creates the policies. Next documents no Trusted
  Types guide (unverified behavior of its inline RSC scripts): roll out in report-only first.
- This is a security architecture decision: choose with the project's caching model, and record it.

## View transitions

- `<ViewTransition>` and `addTransitionType` are stable in React 19.3. `experimental.viewTransition` was removed in
  Next 16.3: delete the flag. `<Link transitionTypes={[...]}>` since 16.2.
- React calls `document.startViewTransition` itself; never call it by hand (React interrupts it).
- Only Transitions, Suspense reveals and `useDeferredValue` trigger it; a plain `setState` does not. Browser
  back/forward carries no transition type.
- Put the wrapper in `page.tsx`, not `layout.tsx` (layouts persist). One element per `name` at a time.

## Forms

- `<form action={fn}>` runs in a Transition and resets uncontrolled fields after success, also when the action returns
  a validation error. Return the submitted values and feed `defaultValue`, or use `key`, to keep the input.
- `useActionState(fn, initial)` returns `[state, action, isPending]`; `useFormStatus` only in a child of the form.
- Native validation runs before submit and stops the action; `:user-invalid` styling works as on the platform
  (interplay with the post-action reset unverified). Validate again on the server, always with authorization.
- Server Actions return a structured result (`{ ok, data } | { ok: false, errorCode }`); a thrown message is masked
  in production. Translate by code on the client.

## Dialog, popover, invoker commands

- `<dialog>` with `ref.current.showModal()` in a client component.
- `@types/react` lacks `command`/`commandFor` (open issue on 2026-11-11): write the lowercase attributes
  (`commandfor`, `command`) with a module augmentation. `popoverTarget` support in React DOM is unverified: test it.
- With Cache Components, recent routes stay mounted hidden in `<Activity>`: an open dialog or dropdown can survive
  navigation; close it on route change.

## Custom elements

- React 19 sets a prop as a property when the element's class defines it at construction, otherwise as an attribute
  (non-strings serialized). Events: `on` + the exact event name (`onsay-hi`).
- Registration (`customElements.define`) runs only in the browser: wrap elements that need properties or events in a
  `'use client'` component. Server rendering of custom elements is undocumented.

## Back/forward

- Next documents nothing about the browser bfcache. With Cache Components, client-side Back restores hidden
  `<Activity>` routes; a full reload Back uses the bfcache. Two mechanisms: test both.
- The Router Cache can replay an old RSC payload on soft Back or reopen inside `staleTimes`: a screen that edits data
  must refetch or `router.refresh()` before showing it, or a later save overwrites newer data with stale data.

## Sources

- https://nextjs.org/docs/app/guides/streaming, /prefetching, /content-security-policy, /view-transitions,
  /upgrading/version-16
- https://nextjs.org/docs/app/api-reference/components/link, /components/image,
  /config/next-config-js/cacheComponents, /config/next-config-js/reactCompiler
- https://react.dev/blog/2026/09/09/react-19-3, https://react.dev/reference/react/ViewTransition,
  https://react.dev/reference/react-dom/components/form, https://react.dev/reference/react-dom/components
- https://github.com/DefinitelyTyped/DefinitelyTyped/issues/74664
