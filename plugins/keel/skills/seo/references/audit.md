# SEO audit rubric

Read when you audit, score or report the search health of a site, or compare two audit rounds.

An audit documents; it does not fix. A fix becomes a front's work. The score exists to compare rounds, not to impress: two rounds compare only with the same URL set, tool version and lab mode.

## Fixed URL set

- Home, one landing page, the latest post, one alternate-language home.
- Add URLs freely; do not swap the fixed ones without recording it in the report.

## Axes and weights

| Axis | Weight | What enters |
|---|---|---|
| Content and E-E-A-T | 23 | Verified claims, real author, YMYL, scaled content, reviewed translation ([eeat](eeat.md)) |
| Technical and indexing | 22 | Status, redirects, robots, noindex, canonical, HTML size, server rendering, sitemap ([crawl-index](crawl-index.md)) |
| On-page | 20 | Title, description, h1, `<html lang>`, reciprocal hreflang, the project's own copy rules |
| Structured data | 10 | Valid JSON, live type, required props, language, nothing invented ([structured-data](structured-data.md)) |
| Performance | 10 | Field Core Web Vitals; with no field data, lab, marked as lab |
| AI search | 10 | Citable page (text in HTML, direct answer), search bots allowed, `llms.txt` only if correct ([ai-search](ai-search.md)) |
| Images | 5 | LCP, aspect ratio, weight, `alt`, OG ([images-social](images-social.md)) |

- The weights are the project's own once adopted. Changing a weight invalidates comparison with earlier rounds: recompute the whole round.

## Score per axis (0 to 100)

1. Start at 100.
2. Each CONFIRMED finding deducts by severity: P0 40, P1 15, P2 5, P3 2, Info 0. Floor 0.
3. A P0 caps the axis at 40.
4. The same defect on many URLs counts once, with the count noted ("on 40 landings").
5. Performance uses another formula: each metric scores 100 good, 60 needs improvement, 20 poor, against the thresholds in [performance](../../web-craft/references/performance.md) (field: LCP, INP, CLS; lab: LCP, CLS, TBT). Lab TBT: good up to 200 ms, poor over 600 ms. The axis is the mean over all URLs and viewports measured.
6. An unmeasured axis is "not measured", with no number, and stays out of the total. Never guess a score.

**Total** = sum(weight x score) / sum(measured weights). State what share of the weight the total covers.

## Severity

| Level | When | Example |
|---|---|---|
| P0 | Removes a page from the index or risks a manual action; or claims to customers what the code contradicts | accidental `noindex`, wrong status, blocked crawl, scaled content |
| P1 | Loses a relevant signal | wrong language, hreflang without return, wrong canonical, false or missing author in YMYL, bad field CWV |
| P2 | Opportunity | false `lastmod`, repeated brand in titles, JSON-LD in the wrong language, weak `alt` |
| P3 | Polish | |
| Info | Changes nothing in Google, still worth recording | retired type, `priority` in the sitemap |

## Finding format

- What.
- Where (`file:line` or URL).
- Impact.
- How the fix is proven (the command or check that goes green).
- Who fixes (a front, the owner, nobody).

## Report format

1. Header: date, code sha measured, environment (production, or local build and port), tool version, URLs.
2. Score table by axis, the total, and the delta against the previous round.
3. Findings by severity, in the format above.
4. Raw measures: the crawler-view output, lab (median and method), and with a key, PageSpeed Insights and CrUX; keep the raw files beside the report.
5. Entity and authority block (outside the score).
6. Attack order, by impact on ranking and conversion.
7. What was not measured, and why.

## Entity and authority block (outside the score)

Code does not measure it, and for a brand with a homonym it often weighs most. Answer with the fact and the date:
- Does the brand query return the site first? Does Google correct the spelling? Who owns the knowledge panel?
- Does `Organization` list in `sameAs` only real, active profiles? Does a real profile exist that is missing from the JSON-LD?
- How many independent mentions with the exact spelling (software directories, press, partners)?
- Search Console: clicks, impressions, the queries that bring people (the owner reads it).
- Off-code actions for the owner, without inventing a profile URL: what to create, where, and what to check afterwards.

## How to measure

- Search Console: indexing, rich-result and CWV reports, URL Inspection.
- Rich Results Test and Schema Markup Validator for structured data.
- Lighthouse and PageSpeed Insights for lab; CrUX for field (the CrUX API). A claim that PageSpeed Insights will stop carrying CrUX data is unverified: use the CrUX API for field data either way.
- Lab differs between runs and environments: decide by the median of 3 or more runs.
- Crawler view: `curl -s -A "Googlebot" <url> | grep -i -E "<title|canonical|hreflang|robots|<h1|ld\+json"`. HTML size: `curl -s <url> | wc -c` (under 2 MB). Redirects: `curl -sIL`.
- A project's measurement script, when it exists, replaces the ad-hoc curls; record its version.
- API keys live only in the process environment, never in a file or in the report.

## Anti-patterns

- Scoring an axis that was not measured; changing a weight and comparing with the old round.
- A different URL set or lab mode between rounds.
- A defect on many URLs counted many times.
- Fixing during the audit instead of recording.
- Findings with no proof of resolution or no owner.
- A number in a decision without the measurement that produced it.

## Sources

- Axes and weights (23/22/20/10/10/10/5), the rule of not scoring what was not measured, and severity by impact were adapted from claude-seo by AgriciDaniel (MIT), https://github.com/AgriciDaniel/claude-seo. The per-axis formula is local: that source defines none.
