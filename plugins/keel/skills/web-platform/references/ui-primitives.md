# UI primitives and modern CSS

Read when building or reviewing a modal, popover, menu, tooltip, dropdown, custom select, an element positioned next
to another, a component that adapts to its container, entry/exit animation, theme colors, or text wrapping.

Status per [baseline.md](baseline.md), checked on webstatus.dev on 2026-11-15. "Widely" needs no fallback; "newly" and
"limited" ship with the fallback written here.

## Dialog (`<dialog>`, widely)

- A modal is `<dialog>` opened with `showModal()` or `<button command="show-modal" commandfor="id">`.
- Do not add `role="dialog"`, `aria-modal`, a focus trap, `inert` on the page or an Esc handler: the modal dialog
  does all of it. Never `show()` or the `open` attribute for a modal.
- Name it with `aria-labelledby`. `autofocus` on the main control; on a destructive confirmation, on the safe action.
  Do not write focus-return code: the dialog returns focus to the opener.
- Close with `<form method="dialog">`, `command="close"`, or `command="request-close"`/`requestClose()` (fires
  `cancel`, so the screen can refuse it with unsaved changes).
- Intercept Esc through the `cancel` event. Critical logic goes on `close`/`cancel`, never on a button `click`. Read
  and reset `returnValue` on `close`.
- Style with `::backdrop` and `dialog:modal`. Scope `display` to `dialog[open]`; an unconditional `display` shows a
  closed dialog.
- Scroll lock: not `overflow:hidden` or `position:fixed` on `html`/`body`. Use `overscroll-behavior: contain` on
  `dialog:modal` and `::backdrop` (limited: Chromium 144, Firefox 150, not Safari, per the guide; unverified on
  webstatus; `@supports` gives a false positive).
- `closedby="any"` (click outside closes; limited: Chromium 134, Firefox 141, no Safari). Fallback: detect
  `'closedBy' in HTMLDialogElement.prototype`; close on `pointerup` only when `pointerdown` was also outside, by
  `getBoundingClientRect()` (a click on the dialog's padding also has `event.target === dialog`).
- A nested component that uses Esc (menu, combobox) must stop it, or it closes the dialog.
- Moving an open dialog or popover with `appendChild` closes it. `moveBefore()` keeps state (limited: Chromium 133,
  Firefox 144, no Safari); fallback: insert, then `showModal()` again.
- Non-blocking panel: `<dialog popover>` or `show()`. Menus, tooltips and toasts are popovers, not dialogs.

## Popover (`popover`, newly since 2025-01-27)

- `popover="auto"`: top layer, light dismiss, closes other auto popovers. `manual`: closes only by code or button.
  `popover="hint"`: unverified, do not rely on it.
- Trigger with `popovertarget` or `commandfor`; never both on one button (it toggles twice).
- `auto` does not close when keyboard focus leaves; a tooltip must not cover the focused element (WCAG 2.4.11).
- Closing from a button inside loses focus: return it to the trigger by script.
- An action dropdown is a group of buttons, not `role="menu"` (which promises arrow-key navigation). `aria-haspopup`
  only with the matching role.
- Fallback for older engines: `@oddbird/popover-polyfill`, loaded only when
  `!Object.hasOwn(HTMLElement.prototype, 'popover')`, pinned version, self-hosted or with SRI
  ([security.md](security.md)).

## Invoker Commands (`command`/`commandfor`, newly since 2025-12-12)

- Values: `show-modal`, `close`, `request-close`, `toggle-popover`, `show-popover`, `hide-popover`; custom values start
  with `--`.
- The `command` event does not bubble: listen on the target (`event.command`, `event.source`).
- Detect with `'commandForElement' in HTMLButtonElement.prototype`; polyfill only when missing, and then manage
  `aria-expanded` yourself.
- React typings lack these attributes ([next-react.md](next-react.md) §Dialog).

## Anchor positioning (limited)

- Status conflict, checked 2026-11-15: webstatus marks the whole feature limited (Chromium 157, Safari 27, no
  Firefox) because it aggregates sub-features; MDN data shows the core (`anchor-name`, `position-anchor`,
  `position-area`, `position-try-fallbacks`) in all three engines since 2025-2026. Treat as limited: progressive
  enhancement with `@supports`.
- A `popover` opened by `popovertarget`/`commandfor` gets an implicit anchor: no `anchor-name` needed.
- Use `position-area` with logical keywords (`block-end span-inline-end`) and
  `position-try-fallbacks: flip-block, flip-inline, flip-block flip-inline`. Do not mix physical and logical keywords.
- Reset `inset: auto; margin: 0` only inside `@supports (position-area: block-end)`; without support the popover sits
  at (0,0) or over the trigger.
- Fallback: `@supports not (position-area: block-end)` with a fixed bottom sheet (`position: fixed; inset: auto 0 0`),
  or `@oddbird/css-anchor-positioning` (needs explicit `anchor-name`/`position-anchor` and `anchor()`; do not wrap its
  rules in `@supports`).

## Customizable select (`appearance: base-select`, limited)

- Chromium 135, Safari 27, no Firefox. Unsupported engines show the native select: that is the fallback.
- `appearance: base-select` on `select` and `::picker(select)`; `<button><selectedcontent>`, `option::checkmark`.
  Keep `<label>`, `name`, `value`.
- Set an explicit width (it no longer sizes to the longest option); 3:1 contrast for the control.
- Option text must read well without its inner markup (old engines strip tags).
- Prefer it to a JavaScript select when the design needs styling: it keeps keyboard, autofill, form submission and
  mobile pickers.

## Layout and selection

- Container size queries (widely): `container-type: inline-size` on the ancestor; a component adapts to its slot,
  not to the window. `size` needs explicit dimensions.
- Container style queries (newly since 2026-05-19): `@container style(--x: v)`; reach descendants only. Fallback:
  base style, then `:where(.ctx) .x`, then the query last.
- `:has()` (widely): scope to the component, never `body:has(...)`; no `:has()` inside `:has()`. Critical layout
  keeps `@supports not selector(:has(*))`.
- Subgrid (widely): one axis; declare an explicit `grid-template-*` before it.
- `@layer` (widely): declare the order once at the top (`@layer reset, base, theme, components, utilities;`).
- Nesting (widely): only where it helps maintenance.
- `@scope` (newly since 2026-03-24): `@scope (.card) to (.content)` for nested components; webstatus versions
  conflict with earlier Chromium releases (unverified).

## Color and type

- `color-scheme: light dark` and `light-dark(a, b)` for colors only (newly from 2024-05-13; the widely flip is due
  2026-11-13 and was not yet shown: unverified). Fallback: custom properties per mode under
  `@media (prefers-color-scheme: dark)`, refined with `@supports (color: light-dark(white, black))`. Registering a
  token as an inherited `<color>` breaks it. Safari ignores `color-scheme` in iframes: pass the theme.
- `color-mix()` (widely): mix in `oklab`; check for an existing token first.
- `text-wrap: balance` (newly) on headings and table headers; `pretty` (limited: Chromium 117, Safari 26) on long
  paragraphs. Never on `*`. Without support the text wraps normally.

## Entry, exit and size animation

- `@starting-style` (newly since 2024-08-06) for entry; exit is the hidden state.
- Write `transition-behavior: allow-discrete` apart from the `transition` shorthand (old engines drop the shorthand),
  and list `overlay` and `display` so dialogs and popovers stay in the top layer while leaving.
- Firefox reports `CSS.supports('transition-behavior', 'allow-discrete')` true but does not transition `display`:
  wait for `getAnimations()` with a ~2 s timeout before removing an element.
- `interpolate-size: allow-keywords` / `calc-size()` (limited: Chromium 129) to animate to `auto`. Declare
  `block-size: auto` before `calc-size(auto, size)`; without support it snaps, which is acceptable. Sync
  `aria-expanded` and hide the collapsed content from assistive tech.
- `prefers-reduced-motion: reduce` turns transitions to none or opacity only.

## Sources

- Guides `ui-components/dialog`, `ui-behaviors/*`, `ui-atoms/*`, `forms/branded-select-styling`, `css/*` in
  https://github.com/GoogleChrome/modern-web-guidance (read 2026-11-15)
- https://api.webstatus.dev/v1/features/<id> for each feature above (2026-11-15)
- https://developer.chrome.com/docs/css-ui/anchor-positioning-api
- https://github.com/oddbird/popover-polyfill
