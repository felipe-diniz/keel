---
name: web-craft
description: Public website, landing page or hero — design that does not look generic and keeps the brand, GSAP/ScrollTrigger/Lenis motion and a Three.js scene delivered by default on a new site or redesign, SEO and AI search, copy, Core Web Vitals, verification on the rendered page. Use when creating, redesigning, modernizing, changing or auditing a public page, its motion, 3D scene, metadata, structured data or marketing text. A project's own design, SEO or frontend skill wins where it is more specific.
---

# Web craft

A public page is read in seconds, indexed by machines and judged on a phone. It has to be fast, legible, findable,
specific and memorable. The detail lives in `references/`: open only the one the step needs.

## Be proactive: modern by default

A new site, a redesign or "modernize" delivers, without being asked, the brand kept and the full stack behind the gate:
GSAP + ScrollTrigger + SplitText acts, light parallax, Lenis, pointer tilt and a Three.js scene behind the hero
([stack](references/stack.md)). A sober page with no motion is not the safe choice, it is an unfinished delivery.
Leaving a layer out is the owner's decision: ask, with its cost. Bring the ideas unasked and close every page
share-ready, a share card from the brand checked as the crawler ([proactive](references/proactive.md)); report each in
one line.

## The rules that always hold

1. **Static first.** The page is complete and indexable as server-rendered HTML and CSS: the hero headline, the main
   image, the call to action. Motion, WebGL and smooth scroll are enhancements that arrive later and can fail without a
   trace.
2. **Gate before download.** A pure function decides, from the environment, which enhancement runs: a wide viewport
   and no `prefers-reduced-motion` for authored motion, plus a fine pointer with hover for smooth scroll and pointer
   effects, plus WebGL2 without a major performance caveat for a scene. A refused
   gate downloads nothing. The heavy modules come by dynamic `import()` after `load` and idle.
3. **LCP never waits for JavaScript.** The largest element is real HTML or an `<img>` with its preload, not a canvas,
   a CSS background or text revealed by a script.
4. **Every enhancement has a teardown.** Listeners, tickers, observers, ScrollTriggers, Lenis and the WebGL context are
   removed on unmount or navigation, and the scene pauses off screen and in a hidden tab.
5. **Keep the brand.** Before designing, extract the existing site's palette (hex), gradients, type and signature
   elements (badges, shapes, photo, floating contact button). The redesign refines them; it never swaps them for neutral
   tokens. The brand wins over the generic-pattern table.
6. **Specific over impressive.** The design and the copy say what the product does, for whom, with proof. A page that
   could belong to any company fails the review, however polished.
7. **Verify the rendered page.** Screens in the matrix (viewports, themes, reduced motion, no WebGL, slow network,
   keyboard), not the code, decide "done".
8. **Facts from the docs.** Library behavior and search rules change by version: check the official doc for the version
   the project uses. The references carry the version and date they were checked against.

## The flow

1. **Read the surface.** Purpose of the page, audience, the one action it asks for, the current site rendered (screens)
   and its brand tokens, and the project's own skills. A project skill for design, SEO or frontend wins over this one where it is more specific.
2. **Compose the static page.** Hierarchy, type, sections, imagery and copy ([design](references/design.md),
   [copy](references/copy.md)). Metadata, canonical, `lang`, structured data and the social image
   ([seo](references/seo.md)).
3. **Plan the acts.** One act per section from the catalog, at least 4 families, and the hero scene concept
   ([stack](references/stack.md)).
4. **Build the layers behind the gate**: boot, engine, scene, teardown, tests of the gate and of the CSS contract
   ([motion](references/motion.md), [three](references/three.md)).
5. **Measure** LCP, INP and CLS in the lab on a throttled profile, and the bundle the enhancement adds
   ([performance](references/performance.md)).
6. **Verify on screen** across the matrix, and report each finding as what, where, impact, fix
   ([verification](references/verification.md)).

## References (read when…)

| File | Read when |
|---|---|
| [references/design.md](references/design.md) | composing or auditing layout, type, color, sections, hero or imagery, or the page looks generic |
| [references/copy.md](references/copy.md) | writing or reviewing a headline, subhead, call to action, section text or microcopy |
| [references/proactive.md](references/proactive.md) | building or redesigning a page: ideas to bring unasked, the share-ready delivery, the layout probe |
| [references/stack.md](references/stack.md) | building or redesigning a page: default delivery, files, markup contract, act per section, hero scene, delivery check |
| [references/motion.md](references/motion.md) | adding or reviewing GSAP, ScrollTrigger, SplitText, Lenis or CSS scroll-driven motion, its gate or its teardown |
| [references/three.md](references/three.md) | adding or reviewing a Three.js/WebGL scene, its capability probe, render loop or disposal |
| [references/seo.md](references/seo.md) | touching metadata, canonical, hreflang, structured data, sitemap, robots, social images, AI crawlers, or auditing search |
| [references/performance.md](references/performance.md) | a page is slow, a budget is set, or an enhancement adds JavaScript, fonts, images or WebGL |
| [references/verification.md](references/verification.md) | declaring a page done, capturing screens, checking accessibility, or reporting a visual review |

## What fails a review

- A redesign with no motion layer, no Lenis or no scene, when the owner did not decline them.
- The brand's palette, gradient or signature elements replaced by neutral tokens.
- A page handed to the client whose link previews no card, an old logo or a card the brand did not shape.
- The hero is a canvas, a background image or script-revealed text: LCP and indexing depend on JavaScript.
- Motion runs with `prefers-reduced-motion` or before `load`; smooth scroll or pointer effects run on touch.
- No teardown: a second visit to the page doubles listeners or leaks the WebGL context.
- `devicePixelRatio` passed raw to the renderer, or the render loop runs off screen.
- Text that names no product, audience or proof; adjectives where a number or a case should be.
- An image that must be found by search shipped as a CSS background.
- Rich results promised for structured data types search engines no longer show.
- "Done" without screens of the matrix.
