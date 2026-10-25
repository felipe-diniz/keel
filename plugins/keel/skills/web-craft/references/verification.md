# Verification on the rendered page

Read when you finish a page, section or effect and must prove it works, or when you audit a page you did not build.

## Principle

- Verify on the rendered page, not on the code. Unit tests cannot see cut-off text, a wrong theme, invisible focus or a small tap target.
- Batch it: go through everything, note, fix at once, then look again.
- A capture is for looking. No test catches a phrase cut off in a phone card.

## Matrix

| Axis | Values | How |
|---|---|---|
| Viewport | 390, 768, 1024, 1280 or 1440, 1920 | Full-page capture at each |
| Theme | light and dark | Force every source the app reads (storage and cookie); otherwise "dark" renders light |
| Language | Every shipped locale | The longest one breaks layouts |
| Long text | 100-char name, long email, large numbers | Edit the content |
| Zoom | 200% | Text legible, container grows, nothing hidden by `overflow:hidden` |
| Reduced motion | `reduce` on | Content visible, no displacement, meaning kept |
| No WebGL | Block WebGL2 | Static composition intact, no WebGL chunk requested |
| Slow network | CPU 4x throttle, limited network | Lab run on the public page |
| Keyboard | Tab through everything | Order, visible focus, Esc closes what opened |
| Touch | Phone profile | Targets at least 44px |
| States | Loading, empty, error, success, disabled, missing content | Trigger each |
| JS off | Disable JS | Content still readable; effects are layers |

## Capture approach

- Use Playwright or similar. Do not install anything the project lacks; ask first.
- Per screen x width x theme, record: full-page screenshot, horizontal scroll, smallest touch target, clipped text, button count, axe violations.
- Axe: inject the source with `page.addScriptTag({ content })` and run `axe.run` with tags `wcag2a`, `wcag2aa`, `wcag21aa`.
- Emulate: `colorScheme`, `reducedMotion`, viewport, device scale factor.
- Block WebGL via launch args or by stubbing `getContext` to return `null`.
- Throttle CPU and network through the browser's CDP session.
- For motion, record video or a frame series while scrolling; one still cannot show jank.
- Check scroll states: top, mid-page, each pinned section, bottom.
- Put outputs outside the repo and out of the public folder, in a dated directory.
- Measure the production build, not the dev server. Dev compiles on demand and lies about cache headers.
- A local server with compression off gives sizes that are not production.
- Normalize non-breaking spaces before comparing text.
- Role queries do not find content under `visibility:hidden`.

## What to check in each

- Layout: no horizontal scroll, no clipped or overlapped text, no layout jump after load.
- Hero: the main image or heading is painted without waiting for JS. No flash of the wrong theme.
- Theme: no section stuck in one theme, no element invisible after toggle.
- Fonts: the declared font loaded, not the fallback.
- Motion: reduced motion shows all content; no pointer effect on touch; the page works with the effect failing.
- Images: right variant per theme, none missing, none distorting.
- Console: no errors on load, even silent ones.
- Network: no heavy library requested where the plan said it would not be.

## Accessibility checks

- Contrast: 4.5:1 normal text, 3:1 large text, in both themes. Measure on the rendered background, not on the token.
- Focus: visible on every interactive element, in order, never trapped.
- Landmarks: one `main`, plus header, nav and footer as they apply.
- Headings: one h1, no skipped levels.
- Alt: informative images have descriptive alt; decorative ones are empty or `aria-hidden`. A CSS-background image that carries meaning has `role="img"` and a label.
- Targets: at least 44px on touch.
- Status never by color alone.
- Labels on every field; errors announced beside the field.
- Repeated decorative content (a duplicated marquee) hidden from screen readers.
- Reduced motion is honored, including when it changes while the page is open.

## Done means

- The matrix ran on the rendered page, with evidence (captures, numbers).
- Axe is clean for the measured widths and themes.
- Lab LCP and CLS are not worse than baseline (see performance.md).
- Console is clean.
- Tests that guard the gating pass (who gets which effect, and that blocked devices do not request the chunk).
- You stated what was not verified.

## Not verified is information

- Say what you could not check: physical-device gestures, a real screen reader, Safari on iPhone when the runner has no WebKit, OS-level zoom.
- Silence looks like approval.

## Testing patterns for gated effects

- Put the "who gets what" decision in a pure function with an injected environment (a media-query answer map plus a WebGL probe). Table-test it without a browser.
- Assert the probe is not called on phones.
- Mock the heavy modules and assert each teardown runs exactly once.
- Fake the idle and load timing; assert nothing loads before `load`.
- Fake `getContext` for GPU, software and none; assert the exact options.
- Test a live reduced-motion toggle by firing the captured `change` listener.
- Test server HTML: no `opacity-0` or inline styles on content that must be visible by default.
- Guard CSS contracts by parsing the stylesheet (for example, that reveal animations live only inside `@supports (animation-timeline: view())`).
- A token guard test beats a document: it fails when the pattern is broken. Ceilings only move down.

## Reporting findings

Each finding states four things.

| Field | Content |
|---|---|
| What | The defect, named |
| Where | Screen or file:line, width, theme, language |
| Impact | Who is hurt and how |
| Fix | A specific change, not "improve contrast" |

- Order by severity: P0 blocks the task; P1 greatly hinders or violates AA; P2 has a workaround; P3 polish.
- Give before and after numbers (buttons, contrast ratios, smallest target, clipped pixels, scroll).
- Group repeating patterns. Note what is good so the next person does not undo it.
- Do not report a finding you did not see on the screen.
- End with the not-verified list.

## Sources

Verification matrix and audit method adapt impeccable (Apache-2.0) and avoid-ai-design (MIT). Testing patterns come from observed project practice, generalized.
