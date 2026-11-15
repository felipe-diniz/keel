# E-E-A-T, YMYL and content quality

Read when you write or review articles, authorship, product claims, health or other YMYL content, bulk or AI-generated content, or aging posts.

Time-sensitive facts carry "(checked 2026-10)". Re-verify before hardcoding.

## What Google says (checked 2026-10)

- E-E-A-T is experience, expertise, authoritativeness and trust. Trust is the most important part. It is not a single ranking factor: systems look for signals that align with it.
- YMYL ("Your Money or Your Life"): topics that affect health, financial stability, safety or well-being. Systems weight strong E-E-A-T signals higher there. Health content is YMYL, and software sold to health professionals that talks about records, prescriptions and patient data is best treated as YMYL as a whole.
- Who, how, why. Who wrote it (visible byline, author page). How it was made (disclose automation or AI where readers would wonder). Why it exists (to help the reader, not to attract a search engine).
- Quality raters (Search Quality Rater Guidelines) do not rank pages; their data calibrates the systems.
- AI-generated content is allowed, but needs fact-checking and review, including title, description, structured data and `alt`. Say how it was made.
- Scaled content abuse is spam (policy since 2024-03-05): many pages made to manipulate ranking, by automation, people or both. Spam policies also cover attempts to manipulate generative AI responses in Search (changelog 2026-05-15).

## Authorship

- Real author or none. A post signed by a person carries a name and a verifiable credential.
- Clinical text is reviewed by a named professional, shown with council and registration number.
- An organization signs as `Organization`.
- Never an AI agent as visible author, in the byline or as `Person` in JSON-LD.
- Never `Person` with the brand name.
- No author data in the CMS: the JSON-LD falls back to `Organization`; fix the source, not the markup.

## Claims

- Product capability claims are checked against the code before they ship. A claim the product does not back is liability with the customer and a low-trust signal. A spec can lock a verified claim and fail on a forbidden pattern.
- Copy for one professional category does not claim what the product excludes for that category.
- No unproven business outcome ("cuts no-shows by 60%") without measured data, an identifiable customer and consent.
- No borrowed authority: "experts recommend", "approved by a council", a seal or certificate only with the document that proves it. Do not imply a seal that does not exist.
- Licensed instruments, tests or trademarks are not named without license.
- Cite a regulation (resolution, law) only with number and year checked, plus a link to the text. A compliance claim with no link is a finding.

## Health content

- No promise of clinical outcome ("cures", "reduces crises by X%").
- Prescribing, diagnosing and similar acts are restricted by profession: copy must not say a profession may do what its council does not allow.
- A number needs a source.
- Medical and legal norms change: an aging post is updated or unpublished.

## Bulk and AI-generated content

- Content in volume passes human review before publishing. An unreviewed clinical post is the double risk: weak YMYL and scaled abuse.
- Variants that differ only by keyword, city or specialty ("topic for specialty A", "topic for specialty B") with no information of their own are the pattern the spam policy describes.
- One post per topic; consolidate near-duplicate slugs with a 301 to the best one.
- A generator that publishes daily on a few repeated topics is an owner decision to pause, not a code fix.
- Machine-translated copy ships only after review by a speaker of the language.

## Dates

- Real `datePublished` and `dateModified`, visible on the post. Never change dates to fake freshness.
- Update or unpublish the post that aged.

## Anti-patterns

- An AI agent or the brand name as author.
- "Experts recommend", an invented seal or certificate.
- Clinical promise; business result with no data.
- Mass template pages; unreviewed bulk posts.
- A regulation cited without number, year or link.
- A capability claim that the code contradicts.
- Fake freshness.

## Sources

- Google Search Central: `https://developers.google.com/search/docs/fundamentals/creating-helpful-content`, `…/fundamentals/using-gen-ai-content`, `…/essentials/spam-policies`
- Search Quality Rater Guidelines (Google, public PDF).
- The "who, how, why" test and per-page E-E-A-T scoring were adapted from claude-seo by AgriciDaniel (MIT), https://github.com/AgriciDaniel/claude-seo.
