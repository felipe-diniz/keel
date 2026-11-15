# Crawl, index, metadata, sitemap and hreflang

Read when you touch status codes, canonical, title, description, `<html lang>`, noindex, robots.txt, sitemap, hreflang or framework metadata, or when a page is not indexed.

Time-sensitive facts carry "(checked 2026-10)". Re-verify before hardcoding.

## Crawl and render

- Googlebot crawls, queues for rendering (evergreen headless Chromium), then indexes the rendered HTML. Links found there go back to the crawl queue.
- Status 200 pages are queued for rendering; non-200 pages may skip it.
- Serve title, description, canonical, robots, hreflang, `<html lang>`, JSON-LD and main text in the server HTML (SSR or static). Google still recommends SSR or pre-rendering.
- Links are discovered only as `<a href>`. Use the History API, never URL fragments.
- `noindex` in the original HTML may stop rendering, so removing it with JS may not work.
- Content hidden until JS runs (opacity 0 waiting for an observer) is still read by Google, but visitors without JS, screen readers and LCP pay. Visible by default; animation is a layer on top.

## Status codes

- 4xx: content ignored, the URL drops from the index.
- 429 counts as a server error.
- 2xx does not guarantee indexing.
- A missing resource returns a real 404. A page that looks like an error with status 200 is a soft 404. In an SPA, redirect to a URL that returns 404 or inject `noindex` on error pages.
- In a framework, an unknown dynamic slug must hit the framework's not-found path (a real 404), not render an empty page.

## Size limits (checked 2026-10)

- Googlebot reads the first 2 MB of each HTML file, uncompressed, including the HTTP header. Each referenced CSS or JS file has its own 2 MB. PDFs get 64 MB. Content past the cutoff is ignored.
- The 15 MB figure in circulation is the default of Google's other crawlers.
- Watch HTML size when JSON-LD, inline framework state or multilingual copy ship in the payload. Measure: `curl -s <url> | wc -c`.

## noindex, Disallow, X-Robots-Tag

- `noindex` works only if the crawler can read the page. A URL blocked in robots.txt has its meta robots ignored. To de-index: `noindex`, no `Disallow`.
- `X-Robots-Tag` is the header form, for PDFs and images.
- Google honors robots meta tags in `<body>` too (checked 2026-10).
- Never ship `noindex` on a page you want indexed. Indexable is the default.

## Canonical

- A signal, not a directive: Google may pick another URL.
- Strength: redirects, then `rel=canonical`, then sitemap inclusion (weak). Keep signals consistent: the sitemap lists the canonical, the canonical points to itself.
- One absolute, self-referencing URL, in `<head>` or an HTTP header, not both.
- Ignored: a canonical with `hreflang`, `lang`, `media` or `type` attributes; fragment canonicals.
- Do not change it via JS after load. A JS-injected one must match the HTML one.
- Never use `noindex` to canonicalize inside the site: it removes the page from search.
- A language variant canonicalizes to itself, never to another language (see hreflang below).

## Metadata

| Item | Rule |
|---|---|
| `<title>` | Unique per page. No Google length limit, only truncation to device width. Google rewrites empty, outdated or boilerplate titles. |
| Meta description | Unique per page. No length limit. Used when more accurate than page text. |
| `<h1>` | One per page. |
| Canonical | One absolute, self-referencing URL. |
| `<html lang>` | Matches the route language, never a cookie. |

- Working ruler (convention, not Google): title about 60 chars, brand once; description 70 to 160; no repeats across pages.
- Google ignores hreflang and `lang` to detect language. Keep `<html lang>` correct anyway: screen readers and browser translators use it (accessibility, not a Google doc).
- `data-nosnippet` (boolean, never added by JS) and `max-snippet` limit snippet input (see [ai-search](ai-search.md)).

## Next.js App Router pitfalls

- A page without its own `alternates.canonical` inherits the layout's (usually `/`). Declare it per page.
- Set `metadataBase` from one site-URL constant so canonical and OG URLs come out absolute.
- A title template appends the brand: use `title.absolute` where the title already carries it, or the brand repeats.
- A page's `openGraph` replaces the layout's wholesale: OG without `images` ships no preview, and a page that declares none inherits the layout's `og:url`. Build every public page's metadata through one helper that sets title, canonical, `og:url`, image.
- A root layout owns `<html>` and does not receive the route segment. Pass the language from the proxy/middleware via a request header, or split root layouts per route group (navigating between them reloads the page).
- Reading `cookies()` or `headers()` in the layout makes the HTML per-request. Keep it out of cacheable routes.
- Verify headers and HTML only on a production build; the dev server rewrites `Cache-Control`.

## Edge-cacheable pages

- A cacheable public page must not read cookies or per-request headers (or a nonce). Language comes from the route.
- Reading one makes the HTML personal and breaks the cache.
- Check your CDN's cache semantics: some honor `stale-while-revalidate` next to `s-maxage`, some disable it; purge on deploy where it is the only invalidation.

## Sitemap

- Limits: 50,000 URLs or 50 MB uncompressed per file, UTF-8. Beyond that, a sitemap index (up to 50,000 sitemaps). Split into an index before about 40,000 URLs as margin.
- A sitemap covers only its own directory and below, unless submitted via Search Console. Submission is a hint.
- List only canonical, 200, indexable URLs. Leave out redirects, `noindex` and non-canonical variants.
- `priority` and `changefreq` are ignored. Do not tune them; drop them.
- `lastmod` counts only if consistently and verifiably accurate; when it lies often, Google stops trusting it. Source it from a real content date (CMS `updatedAt`, a date field kept next to the copy, last commit of the content file). Never `new Date()` at generation time. No real date: omit it.
- Dynamic pages (user profiles, listings) enter only with their own content; an empty or test page is thin.
- A `sitemap.ts` (or equivalent) that reads data not available at build time must be dynamic, or it ships without those URLs. Cache the slug lookups on their own.
- A new route enters the sitemap and any cache-route list the project keeps.

## robots.txt

- One owner. Set the file in one place; any number of `Sitemap:` lines is allowed.
- A CDN or edge bot layer can override robots.txt and answer 403 to crawlers, including search bots. Verify the live file and bot responses.
- Live test: `curl -sI -A "<official user agent>" https://site/` must return 200. A 403 comes from the edge, not the code.
- AI bot rules: see [ai-search](ai-search.md).

## International (hreflang)

- One route per language. Never serve two languages on one URL by cookie.
- Reciprocal: if A points to B, B points to A; without the return, the tags may be ignored.
- Each page lists itself plus all alternates. The set is identical on every version.
- `x-default` marks the fallback page. Recommended, not required.
- Codes: ISO 639-1 language, optional ISO 3166-1 alpha-2 region (`en-GB`, `pt-BR`). A country alone is invalid. `es-419` is unsupported. `UK` and `EU` have no effect. Scripts are allowed (`zh-Hant`).
- One method: HTML `<link rel="alternate">`, HTTP `Link` header (PDFs) or sitemap `xhtml:link`. They are equivalent; several add nothing.
- Each variant canonicalizes to its own language. Never canonicalize `/en` to `/`.
- A page with no translation gets its own canonical and no hreflang.
- Title, description, JSON-LD `inLanguage` and body copy match the route language; a localized page does not serve the default language's graph.
- One language map (route by locale) read by the metadata, the proxy and the language switcher.
- Machine translation published without review by a speaker of the language is a content-quality finding ([eeat](eeat.md)).
- Proof: the crawler view of `/en` shows `<html lang="en…">`, hreflang with return and `x-default`.

New-language checklist:
- [ ] Own route.
- [ ] Title, description, JSON-LD and `<html lang>` in the route language.
- [ ] Reciprocal hreflang on EVERY version, with `x-default`.
- [ ] Copy reviewed by a speaker.
- [ ] Route in the sitemap and in the cache-route lists.

## Anti-patterns

- Indexable content rendered only on the client.
- Canonical inherited from the layout, injected by JS, relative, or on the wrong page.
- hreflang without return links; language chosen by cookie.
- `noindex` plus `Disallow` on one URL.
- `lastmod` set to generation time; tuning `priority` and `changefreq`.
- A 200 error page; an unknown slug that renders.

## Sources

- Google Search Central, base `https://developers.google.com/search/docs/`: `crawling-indexing/javascript/javascript-seo-basics`, `crawling-indexing/http-network-errors`, `crawling-indexing/googlebot`, `crawling-indexing/consolidate-duplicate-urls`, `crawling-indexing/robots-meta-tag`, `specialty/international/localized-versions`, `crawling-indexing/sitemaps/build-sitemap`, `appearance/title-link`; blog `search/blog/2026/03/crawler-blog-post`; changelog `https://developers.google.com/search/updates`
