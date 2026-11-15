---
name: seo
description: SEO and AI search of any public site — metadata, canonical, hreflang, structured data, sitemap, robots, social preview images, AI crawlers and AI search, content quality, E-E-A-T and YMYL health content, search performance and the audit rubric. Use when touching or auditing any of these on a public page, or when a page is not indexed, ranks badly or is not cited by AI. A project's own SEO skill wins where it is more specific.
---

# SEO

Search reads the server HTML, not the screen. A page is findable when it is indexable, unambiguous about its URL and
language, honest about what it is and fast. The detail lives in `references/`: open only the one the step needs.

## The rules that always hold

1. **What search needs comes in the server HTML, with status 200.** Title, description, canonical, robots, hreflang,
   `<html lang>`, JSON-LD and the main text. Never rely on client JavaScript for them.
2. **One absolute canonical per page, pointing to itself,** in its own language. Language variants link by hreflang
   (reciprocal, self-listed), never by canonicalizing to another language.
3. **`noindex` to de-index, never `Disallow`.** A blocked URL's meta robots is never read.
4. **Structured data describes what the page shows, and nothing else.** No invented ratings, reviews or FAQ; no retired
   type added for a rich result.
5. **The sitemap lists only canonical, 200, indexable URLs,** with `lastmod` from a real content date or none.
6. **Real author or none.** Content that claims expertise, health content above all, shows a verifiable author, makes
   no promise the product or the evidence cannot back, and bulk content passes human review.
7. **Every public page declares its own social card:** image, `alt`, `og:url` equal to the canonical.
8. **Measure before and after,** field data over lab. Thresholds and lab method live in
   [performance](../web-craft/references/performance.md); this skill does not restate them.
9. **Facts from the docs.** Search rules change: time-sensitive facts carry "(checked YYYY-MM)"; re-verify before
   hardcoding.

## The flow

**Build or change a page**
1. Read the project's own skills and the neighboring pages' metadata pattern.
2. Metadata, canonical, `lang`, robots, sitemap entry ([crawl-index](references/crawl-index.md)).
3. Language variants, if any (same file, hreflang section).
4. Structured data ([structured-data](references/structured-data.md)); images and card
   ([images-social](references/images-social.md)).
5. Text and claims ([eeat](references/eeat.md)).
6. Check the crawler's view: `curl -s -A "Googlebot" <url>` shows title, canonical, hreflang, robots, `<h1>`, JSON-LD.

**Audit** (document, do not fix)
1. Fix the URL set and the tool version ([audit](references/audit.md)).
2. Run the crawler view and the lab and field measures.
3. Score each axis, record findings as what, where, impact, proof, owner.
4. Write the report, with the entity block and what was not measured.

## References (read when…)

| File | Read when |
|---|---|
| [references/crawl-index.md](references/crawl-index.md) | touching status codes, canonical, title, description, `lang`, noindex, robots.txt, sitemap, hreflang, framework metadata, or a page is not indexed |
| [references/structured-data.md](references/structured-data.md) | adding or reviewing JSON-LD, a schema type or a rich result |
| [references/ai-search.md](references/ai-search.md) | AI Overviews or AI Mode, `llms.txt`, AI crawlers, robots rules for AI bots, or citation by AI |
| [references/eeat.md](references/eeat.md) | writing or reviewing articles, authorship, claims, health or other YMYL content, bulk content |
| [references/images-social.md](references/images-social.md) | image `alt`, formats, `srcset`, hero images, Open Graph or Twitter cards |
| [references/audit.md](references/audit.md) | auditing, scoring or reporting the search health of a site |
| [performance](../web-craft/references/performance.md) | Core Web Vitals thresholds, LCP image priority and preload, lab measurement |

## What fails a review

- Title, canonical, hreflang or JSON-LD that exist only after client JavaScript.
- A canonical inherited from the layout, relative, or pointing a language variant to another language.
- `noindex` together with `Disallow` on one URL; `noindex` used to canonicalize.
- hreflang without return links; two languages on one URL chosen by cookie; `<html lang>` that differs from the route.
- `lastmod` set to generation time; a sitemap with redirects, `noindex` or non-canonical URLs.
- FAQPage, HowTo or sitelinks markup added for a rich result; invented ratings or reviews.
- An AI agent or the brand name as visible author; a clinical promise or an unproven business result.
- Mass pages varying only by keyword, city or specialty; machine translation published unreviewed.
- A page with `openGraph` and no image; a hero that must be indexed shipped as a CSS background.
- Search bots blocked when only training was meant to be opted out.
- An audit score with an unmeasured axis counted, or a changed weight compared with an older round.
