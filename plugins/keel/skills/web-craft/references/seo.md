# SEO and AI search

Read when you touch metadata, canonical, hreflang, `<html lang>`, structured data, sitemap, robots.txt, hero or OG images, or when a page is not indexed, ranks badly or is not cited by AI.

Time-sensitive facts carry "(checked 2026-10)". Re-verify before hardcoding.

## Crawl and render

- Googlebot crawls, queues for rendering (evergreen Chromium), then indexes. Status 200 pages are queued; non-200 pages may skip rendering.
- Serve title, description, canonical, robots, hreflang, `<html lang>`, JSON-LD and main text in the server HTML (SSR or static). Google still recommends SSR or pre-rendering.
- Links are discovered only as `<a href>`. Use the History API, never URL fragments.
- Missing resources return a real 404. A 200 error page is a soft 404. In an SPA, redirect to a URL that returns 404 or inject `noindex` on error pages.
- `noindex` in the original HTML may stop rendering, so removing it with JS may not work.
- Googlebot reads only the first 2 MB of each HTML file (uncompressed). Each subresource has its own 2 MB limit. PDFs get 64 MB. Content past the cutoff is ignored (checked 2026-10).
- Watch HTML size when JSON-LD, inline state or multilingual copy ship in the payload.
- Cacheable public pages must not read cookies or per-request headers. Language comes from the route.

## Metadata

| Item | Rule |
|---|---|
| `<title>` | Unique per page. No Google length limit, only truncation to device width. Google rewrites empty, outdated or boilerplate titles. |
| Meta description | Unique per page. No length limit. Used when more accurate than page text. |
| `<h1>` | One per page. |
| Canonical | One absolute, self-referencing URL, in `<head>` only. |
| Robots | Indexable by default. Never ship `noindex` on a page you want indexed. |
| `<html lang>` | Matches the route language, never a cookie. |

- Working ruler (convention, not Google): title about 60 chars, description 70 to 160.
- Canonical strength: redirects, then `rel=canonical`, then sitemap inclusion (weak).
- Canonical goes in `<head>` or an HTTP header, not both. One with `hreflang`, `lang`, `media` or `type` attributes is ignored. Fragment canonicals are ignored.
- Do not change the canonical via JS after load. A JS-injected one must match the HTML one.
- Layout-default frameworks (for example Next.js): a page without its own canonical inherits the layout's. Declare it per page. Set the base URL (`metadataBase`) from one constant so output is absolute.
- `noindex` works only if the crawler can read the page. A URL blocked in robots.txt has its meta robots ignored. To de-index, use `noindex` and do not `Disallow`. Header form: `X-Robots-Tag`.
- Google honors robots meta tags in `<body>` too (checked 2026-10). `data-nosnippet` (boolean, never added by JS) and `max-snippet` limit AI Overviews input.

## International (hreflang)

- One route per language. Never serve two languages on one URL by cookie.
- Return links are required. If two pages do not point to each other, the tags are ignored.
- Each page lists itself plus all alternates. The set is identical on every version.
- `x-default` marks the fallback page. Recommended, not required.
- Codes: ISO 639-1 language, optional ISO 3166-1 alpha-2 region (`en-GB`). A country alone is invalid. `es-419` is unsupported. `UK` and `EU` have no effect. Scripts are allowed (`zh-Hant`).
- Pick one method: HTML `<link rel="alternate">`, HTTP `Link` header (PDFs) or sitemap `xhtml:link`. They are equivalent; several add nothing.
- Each variant canonicalizes to itself. Never canonicalize `/en` to `/`.
- A page with no translation gets its own canonical and no hreflang.
- Google ignores hreflang and `lang` for language detection. Keep `<html lang>` correct anyway: screen readers and browser translators use it (accessibility reasoning, not a Google doc).
- Title, description, JSON-LD `inLanguage` and body copy match the route language.
- Pitfall: a root layout owns `<html>` and may not receive the route segment. Pass the language from the proxy via a request header, or split root layouts per route group (navigating between them reloads the page).

## Structured data

- JSON-LD is recommended; Microdata and RDFa are equally valid. It may sit in `<head>` or `<body>` and may be JS-injected. Prefer server HTML.
- Markup matches visible content. Never invent ratings, reviews, prices or FAQ text.
- Link nodes by `@id` (for example `${SITE_URL}/#organization`).
- Gallery has 25 features (checked 2026-10), including Article, Breadcrumb, Event, Image metadata, Job posting, Local business, Organization, Product, Profile page, Q&A, Recipe, Review snippet, Software app, Video.

| Type | Requirements (checked 2026-10) |
|---|---|
| Organization | No required properties. Home-page markup helps logo and knowledge panel. Recommended: `sameAs` (real, active profiles only), `logo`. |
| WebSite | Home page only. `name` and `url` required, `alternateName` recommended. The Rich Results Test does not support it; use the Schema Markup Validator. |
| SoftwareApplication | Required: `name`, `offers.price`, plus `aggregateRating` or `review`. Recommended: `applicationCategory`, `operatingSystem`. `WebApplication` and `MobileApplication` are supported. No real ratings, no rich result. |
| Review snippet | Self-serving reviews on LocalBusiness or Organization get no stars. Fake or undisclosed incentivized reviews are prohibited. |
| Article | Named real `author`, or `Organization` for a brand. Real `datePublished` and `dateModified`. |
| ProfilePage | `mainEntity` is a Person or Organization. Suits author pages. |

- Gone (checked 2026-10):
  - FAQPage: restricted to a few well-known authority sites since 2023-09-14, stopped showing 2026-05-07, docs removed 2026-06-15. Treat as zero value.
  - HowTo: gone on desktop and mobile; docs removed 2023-09-14.
  - Sitelinks search box: removed from 2024-11-21. Leftover markup causes no errors.
  - Practice problems: docs removed 2026-01-06.
  - Validate with the Rich Results Test, Search Console rich-result reports, URL Inspection, and the Schema Markup Validator (WebSite).

## Sitemap and robots.txt

- Limits: 50,000 URLs or 50 MB uncompressed per file, UTF-8. Beyond that use a sitemap index (up to 50,000 sitemaps).
- A sitemap covers only its own directory and below, unless submitted via Search Console. Submission is a hint.
- List only canonical, 200, indexable URLs. Leave out redirects, `noindex` and non-canonical variants.
- `priority` and `changefreq` are ignored. Do not tune them.
- `lastmod` counts only if consistently and verifiably accurate. Source it from a real content date (CMS `updatedAt`, last commit of the content file). Never `new Date()` at generation time. No real date: omit it.
- robots.txt allows any number of `Sitemap:` lines. Set the file in one place.
- A CDN or edge bot-blocker can override robots.txt and 403 crawlers. Verify the live file and bot responses.

## Images

- Google indexes `<img>` (also inside `<picture>`), not CSS images. A hero or product image that must be indexed is an `<img>`, never a CSS `background-image`.
- Responsive: `srcset` with `sizes`, or `<picture>`, always with a fallback `<img src>`.
- `alt` is the most important image attribute. Describe what the image shows, no keyword stuffing. Decorative images use `alt=""`.
- Lazy-load only below the fold. Never depend on scroll or click to load.
- The LCP image is never lazy, gets `fetchpriority="high"`, and has `width` and `height`. Many high-priority images cancel the effect.
- Serve variants at the box's aspect ratio, not only its width (how: `performance.md`).

## Open Graph and Twitter/X

- OG required: `og:title`, `og:type`, `og:image`, `og:url`. Optional: `og:description`, `og:site_name`, `og:locale`, `og:image:width`, `og:image:height`, `og:image:alt`. Set `og:image:alt` whenever `og:image` is set.
- `og:url` equals the canonical.
- Every public page declares its own OG. In Next.js a page's `openGraph` replaces the layout's wholesale: OG without an image ships no preview.
- Share image: 1200x630, JPEG, own `alt` in the page language. Google gives no official `og:image` pixel size.
- House heuristics (unsourced): card under about 300 KB; version the filename because messengers cache previews by URL; re-scrape after deploy (Facebook Sharing Debugger, LinkedIn Post Inspector).
- Twitter/X (secondary, unverified; official pages were inaccessible): `twitter:card` required (`summary_large_image` or `summary`), no OG fallback; `twitter:title` up to 70 chars, `twitter:description` 200, `twitter:image:alt` 420; large card 2:1, min 300x157, max 4096x4096, under 5 MB; other tags fall back to OG.

## Core Web Vitals

| Metric | Good | Poor |
|---|---|---|
| LCP | 2.5 s or less | over 4.0 s |
| INP | 200 ms or less | over 500 ms (unverified) |
| CLS | 0.1 or less | over 0.25 (unverified) |

- A page passes only if all three are good at the 75th percentile of loads, split by mobile and desktop. INP replaced FID in March 2024.
- Field metrics (CrUX, PageSpeed Insights, Search Console) are the number that counts. Lighthouse cannot measure INP (TBT proxy). Lab data finds causes.
- Unverified: a claim that PageSpeed Insights will stop carrying CrUX data has no source. Use the CrUX API for field data.
- The how-to-fix lives in `performance.md`.

## AI search

- AI Overviews and AI Mode have no additional requirements (checked 2026-10). The page must be indexed and snippet-eligible. No special file, markup or schema.
- A site-wide Search Console generative AI control can exclude the site from AI Overviews and AI Mode. New, rolling out gradually (checked 2026-10). Extra details (Discover, training) are unconfirmed.
- `Google-Extended` is a robots.txt token with no user agent. It controls Gemini training and grounding. It does not affect Search inclusion, ranking or AI Overviews.
- `llms.txt`: Google Search does not use it and it does not affect rankings (changelog 2026-06-15). No official OpenAI, Anthropic or Perplexity statement that their crawlers read it (unverified). If you publish one, generate it from the same data as the page, state only verified facts, serve it static. Otherwise skip it.

| Bot | Role | Blocking it (checked 2026-10) |
|---|---|---|
| Googlebot | Search, AI Overviews | Leaves Search |
| Google-Extended | Gemini training, grounding | No effect on Search |
| OAI-SearchBot | ChatGPT search | Not shown in ChatGPT search (about 24 h) |
| GPTBot | OpenAI training | Opts out of training |
| ChatGPT-User | User fetches | robots rules "may not apply" |
| ClaudeBot | Anthropic training | Honored; opts out |
| Claude-SearchBot | Claude search indexing | May reduce search visibility |
| Claude-User | User-requested fetches | May reduce visibility in user-directed search |
| PerplexityBot | Perplexity search, not model training | Honored; drops from results |
| Perplexity-User | User-initiated | "Generally ignores robots.txt" |
| Applebot | Spotlight, Siri, Safari | Follows Googlebot rules if none for Applebot |
| Applebot-Extended | Apple training opt-out | No effect on search |

- Training opt-out: GPTBot, ClaudeBot, Google-Extended, Applebot-Extended. Search visibility: Googlebot, OAI-SearchBot, Claude-SearchBot, PerplexityBot, Applebot.
- Blocking training while allowing search is a business decision for the owner. Vendor lists change; read the vendor page.
- Live test: `curl -sI -A "<official UA>" https://site/` must return 200. A 403 comes from the edge.

## E-E-A-T for content pages

- Trust is the most important part. E-E-A-T is not a single ranking factor. Systems weight it more for high-impact (YMYL) topics: finances, safety, well-being.
- Show who wrote it (visible byline, author page), how it was made, why it exists.
- Disclose automation or AI use where readers would wonder. Fact-check AI content, including title, description, schema and `alt`.
- Never fabricate credentials or borrowed authority (seals, "experts recommend") without proof.
- Real `datePublished` and `dateModified`. Never change dates to fake freshness. Update or unpublish aged posts.
- Scaled content abuse is spam: many near-identical pages varied by city or category. Spam policies cover generative AI responses (2026-05-15).

## Audit rubric

Document, do not fix. Compare rounds only with the same URL set (home, one landing, latest post, one alternate-language home), tool version and lab mode.

| Axis | Weight |
|---|---|
| Content and E-E-A-T | 23 |
| Technical and indexing (status, redirects, robots, noindex, canonical, HTML size, SSR, sitemap) | 22 |
| On-page (title, description, h1, `<html lang>`, hreflang) | 20 |
| Structured data | 10 |
| Performance | 10 |
| AI search (text in HTML, direct answers, search bots allowed) | 10 |
| Images (LCP, aspect ratio, weight, `alt`, OG) | 5 |

- Severity: P0 removes a page from the index or risks a manual action. P1 loses a relevant signal (wrong language, hreflang without return, wrong canonical, bad field CWV). P2 is opportunity (false `lastmod`, weak `alt`). P3 polish. Info changes nothing in Google (retired type).
- Axis score: start at 100, deduct P0 40, P1 15, P2 5, P3 2. Floor 0. A P0 caps the axis at 40. A defect on many URLs counts once, with the count noted.
- Performance: each metric scores 100 good, 60 needs improvement, 20 poor. Axis is the mean over URLs and viewports.
- Unmeasured axis: "not measured", left out. Total = sum(weight x score) / sum(measured weights). State the covered share.
- Entity block outside the score: brand query returns the site first, knowledge panel owner, real `sameAs` profiles, independent mentions.

## How to measure

- Search Console: indexing, rich-result and CWV reports, URL Inspection.
- Rich Results Test and Schema Markup Validator for structured data.
- Lighthouse and PageSpeed Insights for lab; CrUX for field.
- Crawler view: `curl -s -A "Googlebot" <url> | grep -i -E "<title|canonical|hreflang|robots|<h1|ld\+json"`. HTML size: `curl -s <url> | wc -c` (under 2 MB). Redirects: `curl -sIL`.

## Anti-patterns

- Indexable content rendered only on the client; indexable hero as CSS background; LCP image lazy-loaded.
- Canonical inherited from the layout, injected by JS, or on the wrong page; `/en` canonicalized to `/`.
- hreflang without return links; language chosen by cookie.
- `noindex` plus `Disallow` on one URL.
- FAQPage, HowTo or sitelinks markup added for rich results; invented ratings or reviews.
- `lastmod` set to generation time; tuning `priority` and `changefreq`.
- Blocking search bots when only opting out of training.
- Hand-written, stale `llms.txt`; fake freshness or authors; mass template pages.

## Sources

- Google Search Central, base `https://developers.google.com/search/docs/`: `crawling-indexing/javascript/javascript-seo-basics`, `crawling-indexing/googlebot`, `crawling-indexing/consolidate-duplicate-urls`, `crawling-indexing/robots-meta-tag`, `specialty/international/localized-versions`, `appearance/structured-data/{search-gallery,intro-structured-data,organization,software-app,review-snippet}`, `appearance/site-names`, `crawling-indexing/sitemaps/build-sitemap`, `appearance/google-images`, `appearance/title-link`, `appearance/core-web-vitals`, `appearance/ai-features`, `fundamentals/ai-optimization-guide`, `fundamentals/creating-helpful-content`, `crawling-indexing/control-what-you-share`, `crawling-indexing/google-common-crawlers`; changelog `https://developers.google.com/search/updates`
- https://web.dev/articles/vitals
- https://ogp.me/ and https://llmstxt.org/
- https://developers.openai.com/api/docs/bots
- https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler
- https://docs.perplexity.ai/guides/bots and https://support.apple.com/en-us/119829
- Audit rubric weights adapted from claude-seo by AgriciDaniel (MIT), https://github.com/AgriciDaniel/claude-seo
