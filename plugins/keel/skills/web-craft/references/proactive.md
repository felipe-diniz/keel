# Proactive ideas and the finished delivery

Read when you build, redesign or modernize a public page: the ideas to bring without being asked, the share-ready delivery that closes every page, and the checks that prove it before the owner sees it.

## Posture

- The owner asks for "a nice site"; the agent brings the ideas. Do not wait for "you did not ask": an idea that serves the page's one action and keeps the brand is built, then reported in one line at the end.
- Ask only for what is the owner's: business rules, a claim the sources do not back, a cost (paid service, credits), infra, secrets, deploy, anything external or irreversible.
- Every page closes share-ready (below). A link sent to the client that previews an old logo is an unfinished delivery.
- When the owner reports a layout defect, fix its cause and measure again with a script. Small tweaks shown one at a time burn the owner's patience.

## Ideas to bring

Pick what fits the page; each one already shipped on a real landing.

| Idea | How |
|---|---|
| Full-screen scenes | Each section `min-height: calc(100svh + overlap)`; the next one covers the band with a rounded top (`margin-top: -overlap`), which reads as a parallax hand-off. Measure fit against the min-height, not `innerHeight`. Phone: sections grow naturally |
| Fit on short laptops | Above about 1024px, scale an inner that overflows by `zoom` down to a floor (about 0.78); below the floor the section grows. Refresh ScrollTrigger after a change |
| Varied backgrounds | Alternate surfaces taken from the brand's own hues (cream, beige, a deep brand tone for one statement section), never a single flat page color |
| Header | Fixed; hides on scroll down past about 100px and comes back on scroll up (rAF, 4px threshold, passive listener); `focus-within` shows it; no transition under reduced motion |
| Contact always at hand | A floating WhatsApp or chat button with a prefilled message, safe-area aware, off the footer links |
| Credential and trust | The professional or legal badge (CRP, CRM, OAB, CNPJ) in the hero and in the share card; payment processor named next to the payment step |
| Icons with life | A real icon set on each list item, chip and step, one stroke width |
| FAQ | Exclusive accordion (one open), real questions from the business; it serves readers and AI answers, not a rich result |
| Booking or form | Title on one line with the subtitle under it; summary and form side by side at the same height; an empty column gets useful content (what happens after paying, who processes the payment, a help link), never a void; inputs filter and mask (name letters only, CPF, phone) |
| Final CTA | A last scene that repeats the one action with the facts that remove doubt (duration, format, payment) |

## Share-ready delivery

Do all of it without being asked, on every new page or redesign:

- **Share card from the brand.** Compose an HTML at 1200x630 with the real photo or product, the name, the credential badge, the page's headline, two or three fact chips and the action; render it with Playwright (wait for `document.fonts.ready`), encode JPEG under about 300 KB, save under a versioned path (`/og/share-2026-10.jpg`) and look at it. Every text in it already appears on the page.
- **Metadata.** `metadataBase` from the one `SITE_URL` constant; `og:url` equals the canonical; `og:image` with width, height, type and alt; `twitter:card` `summary_large_image` with `twitter:image:alt`; title and description that say who, what and how in facts ([seo](seo.md) "Open Graph").
- **Preview before deploy.** The card URL is absolute. Take its origin from an env (`SHARE_ORIGIN`) that falls back to `SITE_URL`, build the preview with the tunnel or staging origin, and the client's link previews the new card before production. Facebook's debugger follows `og:url` to production; WhatsApp uses the page it fetched.
- **Crawl hygiene.** Sitemap with canonical URLs only, never `#section` anchors; robots.txt disallows transactional routes (payment, API); those pages also carry `noindex`; structured data image points to the new card; node `@id`s are `${SITE_URL}/#name`.
- **Check as the crawler.** `curl -A "WhatsApp/2" "<preview>/?v=2"` shows every og and twitter tag; the image URL returns 200 with `image/jpeg`. Tell the owner to share with `?v=N`, since messengers cache previews by URL.
- **Hand-off list.** The env var names the host needs (never values), the demo or test flags to remove before production, and what the client must do (release hours, approve copy).

## Prove it by script

Before showing the owner, run a Playwright probe at two desktop sizes (for example 1440x900 and 1920x1080) and one phone:
- each scene's height against the viewport and the overlap (full, or the zoom applied);
- the header hides after a scroll down and returns after a scroll up;
- side-by-side cards share a height and no card has a blank block over about 80px;
- no horizontal scroll, no console error.

The owner may be looking at a stale build: after a rebuild, say to reload with cache bypass.
