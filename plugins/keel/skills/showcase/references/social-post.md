# Social post copy

Read when the owner asks for a post, social content or feature promotion for Instagram, Facebook or story. Covers subject choice, claim checking, copy rules, forms, format priority, files and the final checklist.

The skill produces copy plus media. It never publishes: the owner publishes (Meta Business Suite or equivalent). Media comes from real product screens with seed or demo data, never a mockup and never production data.

Config used here (see [config](config.md)): `copy.sources`, `copy.notDo`, `copy.releaseNotes`, `copy.rules`, `product`, `site`, `locale`, `output`.

## 1. Flow

1. Pick the subject (section 2). If the owner gave none, propose three and let the owner choose.
2. Check the subject against reality (section 3). Do this before writing a sentence.
3. Write the copy (sections 4 and 5): Instagram feed, Facebook, story.
4. Choose the format and produce the media (section 6).
5. Save under `<output>/posts/<YYYY-MM-DD>-<slug>/` (section 7).
6. Run the checklist (section 9).
7. Hand over to the owner for approval and publishing (section 8).

Why the last checks matter: a published image cannot be swapped and a viewer cannot unsee it. A caption can be edited; the image cannot.

## 2. Pick the subject

Read the files. Never work from memory.

| Source | Take from it |
|---|---|
| `copy.sources` (e.g. a commercial guide, product docs) | What the product does, per audience; plans, prices, quotas |
| `copy.notDo` | What the product does NOT do. Read it BEFORE writing |
| `copy.releaseNotes` folder | What is new. The three newest notes are still news |
| `git log --oneline -40` | Delivered features not yet in a release note |

- Do not repeat a subject. `ls <output>/posts/` lists what exists. The same feature twice in a month makes the profile look like the product has five features.
- Skip subjects that the project's `copy.sources` do not cover. Ask the owner instead of guessing.

### Angles, best first

1. Named pain. A precise situation the reader recognizes beats a generic benefit ("the client confirmed at 10pm and nobody saw it" beats "efficient scheduling").
2. The number the reader already counts. Time lost, money lost, no-shows, rework. Talk about money and time.
3. Before and after of the process, not of the software. The old routine is the before; the screen is the after.
4. Proof. A measured result with a named, authorized source. No data, no angle.
5. How-to. One task in three steps, shown on a real screen.
6. Behind-the-scenes. How a feature came to exist, only if the source documents it.
7. New feature, when it solves something customers asked for.
8. Feature list. Weakest: nobody buys from a list and every competitor posts one.

## 3. Check the claims (mandatory)

Before any affirmative sentence about the product, confirm it in code or in `copy.sources`.

- Which plan has it? If gated by plan, name the plan or pick another subject. A post that shows a paid feature without saying so attracts customers who do not have it.
- Is it an add-on or a quota? Metered features (messaging, AI, signatures, storage) have limits. "Send as many as you want" is false.
- Does it exist today or only in the roadmap? Roadmap and design docs are not product. A post about them is a promise the customer collects next week.
- Who can do it? A role-restricted action cannot be shown as "anyone on your team does it in two clicks" without checking the access matrix.
- Is it in `copy.notDo`? Then do not write it.
- Is the label, limit or default what the screen says? Copy it from the UI dictionary, not from memory.

Record the source of every claim in `copy.md` (section 7).

## 4. Hard copy rules

Each rule has a real consequence. They are not style preferences.

- Apply the project's hard copy rules from the config (`copy.rules`) to every variant. They are not optional.
- Write in the `locale` of the config, active voice, words the audience uses. Avoid corporate filler ("stakeholder", "workflow", "complete solution").
- Never promise anything listed in `copy.notDo`. Those are the questions customers ask; a promise there produces cancellations, not sales.
- Copy prices from `copy.sources`, with the plan name beside the price. A price without its plan becomes a complaint. If the source changed after the post, the post is wrong.
- No result claim without data. "Cut no-shows by 40%" needs a measured number, an identifiable customer and written authorization. Without them it is misleading advertising under consumer-protection law.
- No testimonial, chat screenshot or customer name without written authorization. Naming a customer discloses business information about them.
- No personal data in any asset: mask names, document numbers, phones, emails. Use invented people and companies ("Acme", "Jane Doe").
- Do not claim AI capabilities the product lacks. Describe only what the code does (e.g. transcribe and organize), never advice or decisions the product does not make.
- Do not name licensed or trademarked third-party items in a way that suggests the product ships them.
- Emoji sparingly: at most one per block, never mid-sentence, none on the first line (it competes with the hook).

## 5. Shape of the copy

### Instagram feed

```
[HOOK: 1 line, up to ~60 characters]   <- shown before "more"
                                        <- mandatory blank line
[BODY: 2 to 4 short sentences, one idea per line]

[CTA: 1 line, one verb, one destination]

[3 to 5 hashtags]
```

- The hook is the only guaranteed line. It carries the pain or a question, never the product name. "Acme: scheduling for teams" wastes the hook.
- One idea per line. Dense paragraphs do not read on a phone.
- The CTA points to a real destination. "Link in bio" only works if the bio has the link. Use an offer that is true per `copy.sources` (a trial, a demo) or "message us".
- Hashtags: niche, not volume. A niche tag reaches buyers; a tag with tens of millions of posts reaches no one. Three to five, at the end, never mid-text.

### Facebook

- Same message, more room, fewer hashtags (zero to two).
- The audience reads longer text and the link is clickable in the body, so the CTA is a real link (`site`).
- Include the context sentence that Instagram cut for space.

### Story

- Three to five words per screen, imperative verb.
- The CTA is the sticker (link, poll, question box).
- A story is not the feed post squeezed. It asks something and waits for an answer.

## 6. Media

Production is done by the skill's scripts. Examples below; flags and plan format are in [capture](capture.md) and [storyboard](storyboard.md).

- `art.mjs`: static art. 1080x1350 feed (default), 1080x1080 square, 1080x1920 story. `--deck` builds a carousel. `--no-shot` makes a typographic art without opening the product.
- `capture.mjs`: captures scenes from a JSON plan, for art or video.
- `compose.mjs`: Reel 1080x1920 from the captured scenes, with kinetic captions.
- `audio.mjs`: optional narration or music. See [audio](audio.md).

### Format priority: Reel, then carousel, then single image

- Platform data, 2026: single images lost 21.96% of reach and 45.98% of engagement year over year (Metricool, 24.3M posts). Reels reach 2.25x a single image and carousels generate 9x more saves (Buffer, 52M+ posts).
- Reel brings people who do not know the account. Carousel deepens with people already there. A single image does neither well.
- This matters double for small or misaligned accounts: reach to non-followers is decided by signals from viewers (watch time, shares by DM), not by followers.
- Use a single image only for a short announcement, or when the owner asks.
- A Reel needs a storyboard first. Approve stills before narration, see [storyboard](storyboard.md).

### Cadence

- Plan 3 to 5 feed posts per week and do not skip weeks.
- Why: the largest measured effect is regularity, not posting time.

### Choose the screen

- An empty screen sells the opposite. If the screen is empty, advance the date, apply a filter, or seed more demo data.
- Never capture a screen that shows a paywall or upsell page. The art would advertise the paywall. Check what the login user sees.
- Never capture an error state. A table of red error rows sells the opposite.
- The login user decides what shows: catalog, plan, company name in the header. Use the demo account whose reality matches the post.
- Odd visuals (red banners, hatched bands, test records named `zz...`) come from the data, not from volume. Fix the seed data before blaming the tool.
- In video, do not move the cursor to a screen corner: it can open a sidebar that covers the frame. Scroll by script.
- Open the generated image and look at it. No test catches cut text, wrong theme or an unreadable line.

### Before seeding or capturing

- Run against a local or demo environment with seed data. Never against production.
- Turn off background jobs, schedulers, notifications and outbound integrations (messaging, billing, email) before seeding. Seeded records can trigger real sends or charges. Use the project's own switch for this.
- A slow dev server can take minutes to render a route. Distinguish slow from down with the project's health endpoint before killing the process.

### Privacy

- Masking handles known formats (document numbers, phones, emails). It does not mask free-text names or notes.
- Review every frame for personal data. A published image cannot be taken back.

## 7. Files

`<output>/posts/<YYYY-MM-DD>-<slug>/`. `output` comes from the config (default `marketing/`).

| File | Content |
|---|---|
| `copy.md` | The three variants (Instagram, Facebook, story), the subject, the source behind each claim, the hashtags and the alt text |
| `post-feed.png` (plus square, story, deck slides as produced) | Final art |
| `post-tela.png` | Raw capture, to rebuild the art without repeating navigation |
| storyboard (JSON) | The plan for a Reel or deck, see [storyboard](storyboard.md) |

- Media is gitignored. Only the copy and the storyboard are versioned. The copy history prevents repeated subjects and keeps the tone between posts.
- Write the alt text for each image: describe what the screen shows ("weekly calendar with 12 booked sessions"), not "screenshot of the system". It serves accessibility and readers with images off.

## 8. Approval and publishing

- Show the owner the copy and the media. Wait for explicit approval.
- The owner publishes (Meta Business Suite or equivalent). It posts to both networks, schedules for free and shows the real crop preview before confirming.
- The skill does not post, schedule or call a publishing API.
- If volume ever justifies automation, that is a separate project decision. Use a separate app from any app that delivers transactional messages, so a permission change for posts cannot break them.

## 9. Final checklist

- [ ] Every claim about the product was checked against code or `copy.sources`, not memory.
- [ ] Nothing promised that is in `copy.notDo` or in the roadmap.
- [ ] Price, if any, came from the source and has the plan name beside it.
- [ ] Plan-gated, quota or add-on features are labelled as such.
- [ ] The project's hard copy rules (`copy.rules`) are met in every variant.
- [ ] No result claim without data. No customer name or testimonial without written authorization.
- [ ] Media came from seed or demo data and I looked at the generated image.
- [ ] The captured screen is full, in the right theme, with no paywall and no error state.
- [ ] Personal data is masked or invented in every frame.
- [ ] The hook fits before "more" and does not start with the product name.
- [ ] Format follows the priority (Reel, carousel, single image) or the owner chose otherwise.
- [ ] Alt text written.
- [ ] Files saved under `<output>/posts/<YYYY-MM-DD>-<slug>/`; nothing published by the agent.
