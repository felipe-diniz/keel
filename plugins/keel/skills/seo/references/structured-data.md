# Structured data (JSON-LD)

Read when you add or review JSON-LD, a schema type, a rich result, or markup for organization, website, software, breadcrumb, article, local business or profile pages.

Time-sensitive facts carry "(checked 2026-10)". Re-verify before hardcoding.

## Rules

- JSON-LD is the recommended format; Microdata and RDFa are equally valid.
- Put it in the server HTML, in `<head>` or `<body>`. Google reads markup present in the rendered DOM (and warns that dynamic Product markup makes Shopping crawls less frequent and reliable), but other crawlers and AI fetchers may not run JS: never rely on client injection.
- Markup describes what the page shows. Never invent ratings, reviews, prices, counters or FAQ text. Fake or undisclosed incentivized reviews violate policy (and are misleading advertising).
- Link nodes by `@id` (for example `${SITE_URL}/#organization`). `@graph` is valid JSON-LD and read in practice, but the official docs show objects linked by `@id`.
- Language: `inLanguage` and the texts (description, FAQ) follow the route language.
- A retired type earns nothing and is not penalized. Keeping or dropping it is an HTML-weight decision, not a ranking one.
- What the markup lists about the product (features, plans) is a product claim: it follows the claims rules in [eeat](eeat.md).
- The gallery has 25 features (checked 2026-10), including Article, Breadcrumb, Event, Image metadata, Job posting, Local business, Organization, Product, Profile page, Q&A, Recipe, Review snippet, Software app, Video.

## Types and required properties (checked 2026-10)

| Type | Rule |
|---|---|
| Organization | No required properties. Home-page markup helps logo and knowledge panel, with no display guarantee. Recommended: `logo`, `sameAs` (real, active profiles only). When the brand name collides with another entity, add disambiguation props: `disambiguatingDescription`, `legalName`, `taxID`, accurate `sameAs`. |
| WebSite | Home page only, not a subdirectory. `name` and `url` required, `alternateName` recommended. Drives the site name in results. The Rich Results Test does not support it; use the Schema Markup Validator. |
| SoftwareApplication | Rich result requires `name`, `offers.price`, plus `aggregateRating` or `review`. Recommended: `applicationCategory`, `operatingSystem`. `WebApplication` and `MobileApplication` are supported. No real ratings, no rich result: that is correct, never invent them. |
| BreadcrumbList | Trail in results, desktop only. |
| LocalBusiness | Use the most specific subtype (for example a health or dental subtype), as the local-business page asks. No `aggregateRating` without real reviews. |
| Review snippet | Self-serving reviews on LocalBusiness or Organization get no stars. |
| Article / BlogPosting | Named real `author` (a signal of authorship), or `Organization` for a brand. Real `datePublished` and `dateModified`. |
| ProfilePage | `mainEntity` is a Person or Organization. Suits author pages and profile pages. |
| ItemList | No rich result of its own for most uses; serves as description. |

- Brand authorship: `Organization`, never `Person` with the brand name.

## Retired types (checked 2026-11-15 on the Search Central changelog and blog)

| Type | What changed | When |
|---|---|---|
| FAQPage | Restricted to well-known government and health authority sites (docs updated 2023-09-14) | 2023-08-08 |
| FAQPage | No rich result for anyone; docs removed 2026-06-15 | 2026-05-07 |
| HowTo | Mobile dropped 2023-08-08; desktop dropped 2023-09-13; docs removed 2023-09-14 | 2023-09-13 |
| Sitelinks search box | No longer shown 2024-11-21; docs removed 2024-11-29 | 2024-11-21 |
| Book actions, Course info, Estimated salary, ClaimReview, Learning video, Special announcement, Vehicle listing | Phase-out announced in the results-page simplification | 2025-06-12 |
| Course info, Estimated salary, Learning video, Special announcement, Vehicle listing | Docs removed | 2025-09-09 |
| ClaimReview | Docs kept with a phase-out notice; still used by Fact Check Explorer | 2025-06-12 |
| Practice problem | Discontinued 2025-11-05; docs removed 2026-01-06 | 2026-01-06 |
| Dataset | Used only by Dataset Search, not Google Search | 2025-11-05 |

- Book actions stays in the gallery (its deprecation notice was withdrawn 2025-11-05).
- Leftover sitelinks-search-box markup causes no errors.
- Do not add FAQPage, HowTo or sitelinks markup for a rich result. A visible FAQ still helps the reader.
- Always check the changelog before relying on a type: `https://developers.google.com/search/updates`.

## Validation

- Rich Results Test: eligibility for rich results (it does not test WebSite).
- Schema Markup Validator: general schema.org validity, including WebSite.
- Search Console rich-result reports and URL Inspection: what Google saw live.
- Crawler view: `curl -s -A "Googlebot" <url> | grep -c 'ld+json'` confirms the markup is in the server HTML.
- Check valid JSON, `@context`, the types, `inLanguage` against the page language, retired types, missing required props.

## Anti-patterns

- JSON-LD injected by a client component.
- FAQPage, HowTo or sitelinks markup for SERP features; invented ratings or reviews; a counter that is not on the page.
- `Person` with the brand name as author; an AI agent as `author`.
- The default-language graph served on a translated route.
- WebSite markup outside the home.

## Sources

- Google Search Central, base `https://developers.google.com/search/docs/`: `appearance/structured-data/{intro-structured-data,search-gallery,organization,software-app,review-snippet,breadcrumb,local-business}`, `appearance/site-names`; changelog `https://developers.google.com/search/updates`
- https://validator.schema.org/ and https://search.google.com/test/rich-results
- The retired-types table was adapted from claude-seo by AgriciDaniel (MIT), https://github.com/AgriciDaniel/claude-seo, each date checked against the Google changelog.
