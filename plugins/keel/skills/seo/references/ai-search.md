# AI search and AI crawlers

Read when you work on AI Overviews or AI Mode, `llms.txt`, AI crawlers, robots rules for AI bots, snippet controls, or when a site is not cited by AI.

Time-sensitive facts carry "(checked 2026-10)". Vendor lists change: read the vendor page before allowing or blocking.

## Google AI features

- AI Overviews and AI Mode have no additional requirements (checked 2026-10). The page must be indexed and snippet-eligible. No special file, markup or schema.
- The controls are the usual ones: `nosnippet`, `data-nosnippet` (boolean, never added by JS), `max-snippet`, `noindex`.
- Optimizing for generative features is SEO (Google guide, 2026-05-15). No need to chop text into blocks; structured data is not required for it; inauthentic mentions help less than they seem.
- A site-wide Search Console generative AI control can exclude the site from AI Overviews and AI Mode. New, rolling out gradually (checked 2026-10); extra details (Discover, training) are unconfirmed.
- `Google-Extended` is a robots.txt token with no user agent. It controls Gemini training and grounding. It does not affect Search inclusion or ranking (checked 2026-11-15); the page does not mention AI Overviews, which run on Search's index (inference).
- User-triggered fetchers generally ignore robots.txt, because a person made the request. Google's list (checked 2026-11-15) includes Google-Agent and Google-GeminiNotebook (which replaced Google-NotebookLM).

## llms.txt

- Google Search ignores it; it neither helps nor hurts visibility (changelog 2026-06-15). Creating and keeping one is acceptable.
- No official OpenAI, Anthropic or Perplexity statement that their crawlers read it (unverified).
- Publish one only if all three hold, else skip it (a stale file is the wrong source an agent will cite):
  1. Generated from the same data as the pages (plans, landing configs), never hand-written text that ages.
  2. Only facts the code confirms: no "best system", no number without a source, no roadmap capability.
  3. Served as static, cacheable, outside the HTML path; a spec locks that prices and descriptions come from the data.

## AI crawlers (checked 2026-10)

| Bot | Role | Blocking it |
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

- Training opt-out: GPTBot, ClaudeBot, Google-Extended, Applebot-Extended.
- Search and citation visibility: Googlebot, OAI-SearchBot, Claude-SearchBot, PerplexityBot, Applebot.
- User-triggered fetchers (ChatGPT-User, Perplexity-User, Google's) do not follow robots.txt reliably: a person asked for the page.
- Blocking training while allowing search is a business decision of the owner (the content becomes training data or not), not of the technical front.
- Live test: `curl -sI -A "<official UA>" https://site/` must return 200. A 403 comes from the edge: a CDN bot layer can block AI and search bots regardless of robots.txt. Re-test after any CDN setting change.

## What moves citation

Same as ranking:
- A recognized entity (an unambiguous brand name, no collision with a homonym).
- Real profiles with the exact spelling of the name.
- Independent mentions (directories, press, partners).
- Pages that answer the reader's question with verifiable facts, in the server HTML.

Off-code actions go in the audit's entity block ([audit](audit.md)).

## Anti-patterns

- Blocking search bots when only opting out of training.
- A hand-written, stale `llms.txt`.
- Treating `llms.txt` or special markup as a ranking lever.
- Trusting a third party's bot list instead of the vendor page.

## Sources

- Google Search Central: `https://developers.google.com/search/docs/appearance/ai-features`, `…/fundamentals/ai-optimization-guide`, `…/crawling-indexing/control-what-you-share`; crawlers: `https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers` and `…/google-user-triggered-fetchers`
- https://llmstxt.org/
- https://developers.openai.com/api/docs/bots
- https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler
- https://docs.perplexity.ai/guides/bots and https://support.apple.com/en-us/119829
- The training-versus-search split was adapted from claude-seo by AgriciDaniel (MIT), https://github.com/AgriciDaniel/claude-seo.
