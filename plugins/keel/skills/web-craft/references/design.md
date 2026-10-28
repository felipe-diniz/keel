# Design for marketing sites

Read when you create, change or review the visual design of a landing page, home page or any public marketing page.

## A marketing site is not a work tool

- A work-tool ruler (small titles, high density, color only for decisions) makes a marketing page dry.
- The marketing page needs display-scale type, more air between sections and authored motion.
- Keep one brand shared with the app: same palette, fonts and tokens in both themes.
- Why: a product screenshot on a page with another visual language looks like another system. Drift between pages is the signature of generated pages.
- Shared with the app: rectangular buttons, no em dash, AA contrast, 44px touch targets, zero horizontal scroll.

## Keep the brand

- A redesign starts from the current site rendered: capture it, then list the palette in hex (from the stylesheet and the screen), gradients, fonts, the photo and every signature element (credential badge, decorative shapes, floating contact button, CTA style).
- The new page refines that list. It does not replace it with neutral or "safer" tokens. Dark mode derives from the same hues.
- The brand wins over the rules below: a brand gradient on the CTA stays, a warm accent used in several places stays. Fix contrast inside the brand's hues, not by leaving them.
- Show the owner the old and new hero side by side before building the rest.

## Hierarchy and type

- Use a display scale. Size follows the width of the text column, not the screen.

| Role | Phone | Tablet | Wide |
|---|---|---|---|
| h1 | 34px | 44px | 40px to 50px when the hero has two columns |
| Section title | 28px | 36px | 36px |

- Pick one unit system (px or rem) and make the class deliver exactly the table value.
- `text-wrap: balance` on titles, `pretty` on paragraphs.
- Flat hierarchy is a defect: title, label and body must differ in size or weight.
- Never set body text in uppercase or with wide tracking. Uppercase is for 12px labels only.
- Keep prose to about 75 characters per line. No justified text.
- Do not skip heading levels.
- Use `tabular-nums` for counters, prices and columns.
- Editable fields are at least 16px on phones, or iOS Safari zooms on focus.
- Check on the rendered page that the declared font actually loaded.

## Color, surfaces, theme

- Color only where there is a decision. Brand accent in at most 1 or 2 saturated places per screen, unless the existing brand uses more (Keep the brand).
- Status colors are separate from the brand accent. Status is never color alone; add a text label.
- Stay away from purple or blue gradients and neon accents.
- Surfaces are opaque. Translucency and blur are only for temporary overlays (dropdown, sheet, backdrop).
- A translucent text panel over an animated background is a deliberate exception. Justify it and measure contrast on the rendered background.
- Gray text on a colored surface disappears. Use that hue's own on-color token.
- Do not dim inactive items with `opacity` to highlight the active one (35% text fell to 1.7:1 in axe). Highlight the active one by color.
- Dark base is not pure black and text is not pure white. Raise elevation by luminosity in short steps.
- AA in both themes: 4.5:1 normal text, 3:1 large text.
- Elevation is a 1px border plus one luminosity step, not shadow. Shadow is for what really floats.
- Do not dilute a border token that is already subtle.
- Radius: one radius family. Cards 12px, buttons 6px. Pills only for chips and badges.
- Buttons: filled, color-only hover, no translate, no outline-only. Use `transition-colors`, never `transition-all` (it animates inherited `visibility` and flickers).

### Theme policy

- With no visitor choice, follow `prefers-color-scheme`. Forced dark on someone who did not ask is a generated-page sign.
- Order: stored choice, then device preference, then product default.
- The server marks `<html>` from the path only. Do not read cookies or headers in cacheable routes, or the edge cache breaks.
- A head script resolves the theme before paint. Write storage only when the visitor toggles.
- Theme-dependent images: CSS background via variable, or two `<picture>` elements hidden by the theme class. One `<picture media>` follows the device, not the toggle.
- Do not make one section fixed-dark inside a light page.
- Do not reveal a screenshot with a page-colored curtain. Reveal by transform only.

## Sections and rhythm

- Air between sections (64px to 96px on desktop), density inside them (4 to 16px steps).
- A grid of identical cards for items of unequal importance is a defect. Give the main one weight or position.
- Number items only for real sequences.
- Pricing: compare what differs between plans, from the same source the product gates use. Full list on demand.
- Feature area: one tile per real area, each with a crop of real UI.
- Proof strip: verifiable facts only (security, integrations). Remove vanity numbers.
- Signature section: a sticky multi-step walk-through of the product flow, all text in server HTML. On phones stack the steps with their own screenshot, no pin. The section owners praise has real information and real UI.
- Final CTA: centered, with a wide product crop touching the footer.
- Vary the effect family between neighbouring sections.
- Empty state is one line. State a repeated rule once per section, not per row.

## Hero composition

- Show the product: a real screenshot with synthetic data, not a stock photo.
- Desktop: asymmetric. Text left (h1, one support sentence, one primary and one secondary CTA), dominant screenshot right.
- Phone: the screenshot comes right under the CTA as a crop readable at device width, not the whole screen shrunk.
- No fake browser chrome, no hand holding a phone, no 3D illustration instead of the product.
- A static composition (HTML, CSS, image) must be complete without JS. Effects are layers on top. See performance.md and motion.md.
- A background effect is acceptable only as background, never over text or product, always with a static CSS fallback. A still two-glow gradient in the brand color works.
- Capture screenshots with a script against a seeded local app, per theme, language and width.
- Version the filename when a screenshot changes; edges cache images.

## Responsive

- Widths: 390, 768, 1024, 1280 or 1440, 1920. Phone is first class: a desktop-only technique cannot carry the page's meaning.
- No text glued to the edge of a card, button or screen.
- Overlays go through a portal; a parent `overflow:hidden` clips menus.
- Skeletons use the real geometry, or the layout jumps.
- No emoji or Unicode glyph as icon. Use a real icon set.

## Anti-patterns that look generic or AI-made

- These signs do not prove generation. They show a pattern nobody chose. The fix is to choose.
- The combination weighs more than one item. An explicit owner request beats this list.
- Severity by who notices: P0 layperson, P1 designer or front-end person, P2 polish. Accessibility failures rise one level.

| Level | Sign | Fix |
|---|---|---|
| P0 | Purple or blue gradient, gradient-clipped title | Solid brand color |
| P0 | Centered hero, pill badge, three equal cards | Asymmetric hero, product dominant |
| P0 | 3, 6 or 8 identical cards with icon in a square | Real count, main one heavier, UI crop |
| P0 | Stock photo or generic illustration | Real screenshot |
| P0 | Testimonial, logo, counter or rating that does not exist | Verifiable facts only |
| P1 | One title word in color or italic | A title that holds without emphasis |
| P1 | Uppercase spaced eyebrow over every title | Label only where it informs |
| P1 | Arrow on every button and link | Arrow only for "advance" |
| P1 | Decorative numbering, generic number strip | Real steps; sourced fact or nothing |
| P1 | Forced dark with neon accent | Device theme, accent on decision |
| P1 | Large radius plus wide shadow everywhere, decorative blur | One radius, border elevation |
| P1 | Emoji or sparkle as icon | Domain icon or none |
| P1 | Brochure copy | See copy.md |
| P1 | Font declared but not loaded | Check on the rendered page |
| P2 | Same fade-up on every section, count-up, cursor glow | One reason and family per act |
| P2 | Plan grid with "Most popular" and long equal lists | Compare what differs |
| P2 | Four-column footer with a slogan | Useful links, what the company is |
| P2 | Cream background with high-contrast serif and terracotta, or near-black with acid green | The brand palette |

- Also avoid: pulsing dot when nothing changed, self-scrolling strip without pause, bounce or elastic easing, thick colored left border on a regular card, glow behind content as "elevation", a spinner in the middle of content.

## Process for a new section

1. Plan first: tokens named, type roles, a text sketch, one sentence on how it differs from a competitor.
2. Review the plan against the anti-pattern table; swap generic parts.
3. Build, then look at the rendered page (verification.md).
4. Remove one ornament before delivering.
5. Silhouette test: capture at 200px wide, grayscale, next to competitors. If indistinguishable, the structure is a template.

## Audit rubric

- An audit documents; it does not fix. Findings become work items.
- Choose the ruler for the surface. A ruler for one surface gives false findings on another (density is a virtue in an app and a defect on a home page).
- Score five axes 0 to 4. Scores 1 and 3 sit between anchors. Each score cites evidence (measurement, capture, file:line).

| Axis | 0 | 4 |
|---|---|---|
| Accessibility | Fails WCAG A, no keyboard | Full AA, axe clean across widths and themes |
| Performance | Freezes or shifts layout | Lab LCP and CLS in target |
| Theme | Fixed colors everywhere | Both themes right, exceptions documented |
| Responsive | Desktop only | Fluid, right targets |
| Ruler fidelity | Systemic deviation | Coherent and intentional |

- Total /20: 18-20 polish; 14-17 good; 10-13 significant work; 6-9 major overhaul; 0-5 foundation.
- Severity: P0 blocks the task, fix now. P1 greatly hinders or violates AA, fix before publishing. P2 has a workaround, next round. P3 polish, keep few.
- Report: surface, ruler, date, commit, environment; score table; findings by severity (location, user impact, rule, specific fix); repeating patterns; what is good; attack order; what was not verified.
- Do not: finding without impact, generic advice ("improve contrast"), everything P0, a finding not checked on the rendered page.

## Sources

Lists adapted from impeccable (Apache-2.0), avoid-ai-design (MIT) and frontend-design (Anthropic, Apache-2.0). Keep these attributions and licenses.
