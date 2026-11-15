# Accessibility

Read when a control, error, dialog, icon, custom component or theme must work with a screen reader, keyboard, OS text
scaling, high-contrast (forced colors) mode or reduced motion, or when reviewing a screen for WCAG 2.2 AA.

Status checked on webstatus.dev on 2026-11-15 ([baseline.md](baseline.md)). Baseline does not measure assistive
technology support: test with it. Checks on the rendered screen (axe, keyboard pass, 200% zoom) are in web-craft's
[verification.md](../../web-craft/references/verification.md).

## Errors that are announced

- Start every field with `aria-invalid="false"`; set `"true"` and add the error's id to `aria-describedby` only while
  the field matches `:user-invalid`; remove both on recovery.
- Do not reference a hidden error from `aria-describedby`: hidden referenced text is still read.
- One `aria-live="polite"` region per page, updated after ~500 ms; not one live region per message (a region that
  appears, instead of changing, is not reliably announced).
- `role="alert"` or `assertive` only for critical events (session expiring, save failed); WCAG 4.1.3.
- Listen for `invalid` in the capture phase (it does not bubble); handle `change` for checkboxes and radios; do not
  overwrite a server-set `aria-invalid="true"`.
- On a failed submit move focus to the first invalid field or the error summary; on a step change move focus to the
  step heading (`tabindex="-1"`) and hide inactive steps with `hidden` or `inert`.
- Hide the live region visually (clip pattern), never with `display: none`.

## Names and roles

- Native elements first (`button`, `a`, `dialog`, `select`, `input type=checkbox switch`); ARIA only where no element
  exists.
- An icon font is text: its ligature enters the accessible name. Icon-only buttons get `aria-label`; an icon next to
  a visible label gets `aria-hidden="true"`.
- A custom dropdown labels its trigger (`<label for>` pointing at the button); wrapping the component in a `<label>`
  labels the hidden native select instead and the button has no name.
- Fix the component when an accessibility test fails, never the test.
- `<html lang>` matches the content language: screen readers pick the pronunciation from it.

## OS text scale and zoom

- `font-size` in `rem`/`em`, unitless `line-height`; no fixed `height` or tight `max-height` on text containers (use
  `min-block-size`); no `white-space: nowrap` on running text.
- Fluid type with a cap: `clamp(2rem, 1.25rem + 2vw, 4rem)` (max at most 2.5x min); never `vw` alone.
- Grids that reflow: `repeat(auto-fit, minmax(min(100%, 16rem), 1fr))`; breakpoints in `em` or container queries.
- `<meta name="text-scale" content="scale">` makes the root font follow the OS setting on mobile (limited: Chromium
  146; it also disables some page zoom behaviors). With it, do not set `font-size` on `html`/`:root`, and never combine
  it with `env(preferred-text-scale)` (double scaling).
- Required checks: 200% text without loss (1.4.4), reflow at 320 CSS px (1.4.10), text spacing (1.4.12), OS scale and
  browser zoom.

## Forced colors (high contrast)

- `@media (forced-colors: active)` is widely available. The browser drops `box-shadow`, `text-shadow`, background
  gradients and may drop `background-image` and `border-image`.
- Borders, separators, focus rings and states never rely only on shadows or background images: provide `border` or
  `outline` in system colors (`CanvasText`, `ButtonText`, `LinkText`, `Highlight`, `GrayText`, `Canvas`).
- A focus ring drawn with `box-shadow` gets an `outline` fallback under forced colors.
- `forced-color-adjust: none` only where color is the information (swatch, syntax highlight), never for looks; then
  set both text and background with 4.5:1.
- `prefers-contrast: more` only strengthens colors that already meet the minimums.

## Focus

- Style `:focus-visible` (widely); never remove the native ring without a replacement of 3:1 against the adjacent
  color (2.4.7, 1.4.11); prefer `outline` with `outline-offset`.
- A sticky header or a tooltip must not cover the focused element (2.4.11): `scroll-padding-top` for sticky headers.
- Every action reachable by keyboard in a logical order; no positive `tabindex`.

## Motion

- Motion that should not exist goes inside `@media (prefers-reduced-motion: no-preference)`; motion that should
  soften overrides only the moving properties under `reduce`.
- Never a global `animation-duration: 0.01ms`: it kills feedback (save confirmation, color changes) along with
  movement.
- Auto-moving content longer than 5 s has a visible pause; nothing flashes more than 3 times per second.

## Sources

- Guides `accessibility/*` (accessible-error-announcement, respect-os-text-scale), `visual-design/color`,
  `ui-behaviors/motion` in https://github.com/GoogleChrome/modern-web-guidance (read 2026-11-15)
- https://developer.chrome.com/release-notes/146
- https://developer.mozilla.org/en-US/docs/Web/CSS/forced-color-adjust
- https://api.webstatus.dev/v1/features/ (forced-colors, focus-visible, prefers-reduced-motion, meta-text-scale,
  user-pseudos)
- https://www.w3.org/TR/WCAG22/
