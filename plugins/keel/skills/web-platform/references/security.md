# Client-side security and sign-in

Read when rendering HTML that came from users or third parties, setting a Content Security Policy, loading a script
or stylesheet from another origin, building a link or redirect from data, checking an origin, setting cookies,
storing anything in the browser, or building sign-in with passwords, passkeys or a federated provider.

Status checked on webstatus.dev and MDN on 2026-11-15 ([baseline.md](baseline.md)). Personal data in logs, tenant
isolation and secrets are the `lgpd` skill's hunt; this file is the browser side.

## Untrusted HTML

- Text goes in with `textContent`. HTML from users goes through a sanitizer, never straight into `innerHTML`.
- HTML Sanitizer API: `el.setHTML(untrusted)` strips scripts, handlers, iframes and embeds by default; a `Sanitizer`
  config only narrows it. Limited: Chromium 146, Firefox 148, no Safari. Fallback: detect
  `'setHTML' in Element.prototype` and import DOMPurify dynamically only when missing.
- Parse with `Document.parseHTML(raw)` and move nodes; never serialize and reassign through `innerHTML` (mutation
  XSS). `setHTMLUnsafe` only with your own sanitizer config and review.
- Client sanitization protects one consumer. Sanitize on the server too when the same HTML reaches e-mail, other
  clients or server rendering.
- Escaping characters is not sanitization: it does not neutralize `javascript:` in a URL attribute.

## URLs, redirects and origins

- Before assigning data to `href`, `src`, `action` or a redirect, parse with `new URL()` inside try/catch and allow
  only listed schemes (`https:`, `mailto:`, `tel:`); reject `javascript:` and `data:`.
- A redirect target from the query string (`?next=`) is allowed only when same-origin or on an allowlist (open
  redirect).
- Compare origins as origins, never with `startsWith`, `includes` or `split`. `Origin.from(x).isSameOrigin()` is
  limited (Chromium 145, Safari 26.5, no Firefox); fallback `new URL(x).origin === expected`. Reject `"null"`.
- `postMessage` receivers check `event.origin` against an allowlist and `event.source`; senders name the target
  origin, never `*` for data.
- A dynamic path segment interpolated into a backend URL is `encodeURIComponent`-encoded: a decoded `..%2F` walks to
  another endpoint with the user's credentials.

## Content Security Policy

- Strict CSP: `script-src 'nonce-{random}' 'strict-dynamic'; object-src 'none'; base-uri 'none'`. Nonce when the HTML
  is rendered per request (new, 128+ bits, per response); hashes when the HTML is static. CSP is widely available.
- Optional legacy fallback in the same policy: `https: 'unsafe-inline'` after the nonce (ignored where
  `strict-dynamic` works).
- Remove inline handlers (`onclick=`) and `javascript:` URLs; avoid `unsafe-inline`, `unsafe-eval` and `data:` in
  `script-src`.
- Roll out with `Content-Security-Policy-Report-Only` and `report-to` + `Reporting-Endpoints` (keep `report-uri` for
  older engines) until violations are zero; a `<meta>` CSP cannot report and must be the first child of `<head>`.
- Egress: `connect-src`, `form-action`, `worker-src 'self'` limit where data can be sent.
- In a framework, the nonce has costs (dynamic rendering): [next-react.md](next-react.md) §CSP.

## Trusted Types (newly since 2026-02-24)

- Create named policies that sanitize: `trustedTypes.createPolicy('sanitize-html', { createHTML: (s) => sanitize(s) })`;
  only their output reaches DOM sinks.
- Roll out: `Content-Security-Policy-Report-Only: require-trusted-types-for 'script'` until zero violations, then
  enforce with `trusted-types <policy names>` (add `dompurify` when DOMPurify returns trusted types, `default` only
  while migrating).
- A `default` policy is a migration tool that logs and sanitizes; returning null throws.
- Third-party libraries that write strings to sinks break under enforcement: audit before enforcing.
- Fallback where unsupported: `window.trustedTypes ??= { createPolicy: (_n, rules) => rules }` keeps the code path
  (sanitizes, does not enforce).

## Third-party scripts and styles (SRI)

- Cross-origin scripts, stylesheets and `modulepreload` carry `integrity="sha384-..."` plus `crossorigin="anonymous"`
  and `referrerpolicy="no-referrer"`. SRI is widely available; without `crossorigin` the resource is blocked.
- Compute the hash at build time from known bytes; pin a versioned immutable URL, never `latest`.
- A vendor tag that changes without notice cannot carry SRI: restrict it by CSP (`strict-dynamic` with the nonce on
  the loader) or isolate it in a sandboxed iframe.
- `fetch(url, { integrity })` rejects on mismatch. Import maps accept an `integrity` map for modules (documented on
  MDN; its Baseline is unverified).
- Polyfills come pinned and self-hosted or with SRI; guides that load them from a CDN without a version are not
  copied as written.

## Cross-origin isolation

- Only when `SharedArrayBuffer` or precise timers are needed: `Cross-Origin-Opener-Policy: same-origin` and
  `Cross-Origin-Embedder-Policy: require-corp` (or `credentialless`); check `crossOriginIsolated`.
- OAuth and payment popups break with `same-origin`: use `same-origin-allow-popups`. Test with the report-only
  headers first. Support details are unverified.

## Cookies and browser storage

- Session cookie: `__Host-` prefix, `Path=/`, `Secure`, `HttpOnly`, `SameSite=Lax` (or `Strict`), short `Max-Age`.
  `__Host-` forbids `Domain`.
- Cross-site embed cookie: `SameSite=None; Secure; Partitioned` (CHIPS; webstatus lists Chromium only, other engines
  unverified).
- No token and no personal data in `localStorage`, `sessionStorage` or IndexedDB: any XSS reads them, and shared
  devices keep them. Tokens live in `HttpOnly` cookies, renewed server side.
- Logout clears server session, cookies and client caches; `Clear-Site-Data` helps where supported (limited).
- Keep CSRF protection on cookie-authenticated mutations: `SameSite` plus a token or an origin check on the server.

## Passwords and passkeys

- Sign-in form: a real `<form>`, stable `name`/`id`, `autocomplete="username"` and `current-password` (sign-up
  `new-password`), paste allowed ([forms.md](forms.md) §Autofill).
- Passkeys: native WebAuthn in the client (widely), libraries only on the server. `rpId` comes from the server
  options, never `location.hostname`; the challenge is random, server-held, single use; `userVerification` is decided
  by the server.
- Passkey autofill: `<input autocomplete="username webauthn">`; check
  `PublicKeyCredential.getClientCapabilities()` (newly, 2025) for `conditionalGet`; call
  `navigator.credentials.get({ mediation: 'conditional', signal })` with empty `allowCredentials`; abort it before a
  button-started flow; `NotAllowedError` and `AbortError` are expected. Conditional mediation's Baseline is unverified.
- Re-authentication: non-empty `allowCredentials`, and the server checks that the credential belongs to the session's
  user (IDOR).
- Offer to create a passkey after a full password sign-in (all MFA done), with `excludeCredentials`.
- Signal API (limited: Chromium 132, Safari 26) keeps the provider's list in sync after delete or rename; feature
  detect and skip silently.
- Related origins: `/.well-known/webauthn` with the allowed origins; unsupported engines throw `SecurityError`.
- AAGUID is for display, never a security decision.

## Federated sign-in

- FedCM (`navigator.credentials.get({ identity })`) is limited (Chromium 136); fallback is the provider's OIDC
  redirect or popup. An iframe needs `allow="identity-credentials-get"`.

## Sources

- Guides `security/*`, `privacy/privacy`, `forms/autofill-sign-in-form` in
  https://github.com/GoogleChrome/modern-web-guidance (read 2026-11-15)
- https://web.dev/articles/strict-csp
- https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/CSP
- https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/Cookies
- https://developer.mozilla.org/en-US/docs/Web/API/Element/setHTML
- https://developer.mozilla.org/en-US/docs/Web/API/PublicKeyCredential/getClientCapabilities_static
- https://web.dev/articles/webauthn-related-origin-requests
- https://api.webstatus.dev/v1/features/ (trusted-types, sanitizer, csp, webauthn-signals, fedcm, partitioned-cookies)
