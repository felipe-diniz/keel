# Forms

Read when building or reviewing a form: sign-in, sign-up, address, payment, one-time code, search, a custom Enter
handler, validation and error display, auto-growing fields, a switch, or a form that loses input.

Status checked on webstatus.dev on 2026-11-15 ([baseline.md](baseline.md)). Error announcement for screen readers is
in [accessibility.md](accessibility.md); passkey sign-in in [security.md](security.md); React form behavior in
[next-react.md](next-react.md) §Forms and [react-pitfalls.md](react-pitfalls.md).

## Structure

- A real `<form>` with a visible `<button type="submit">`; it works without custom JavaScript.
- Every control has a `<label>` (for/id) and a stable `name` and `id`, never generated per render.
- Format hints go above the field, linked with `aria-describedby`; the keyboard and the autofill popover cover what
  is below. A placeholder is an example, never the label.
- Controls inherit the font (`font: inherit`) with `font-size: max(1rem, 1em)`: under 16px, iOS Safari zooms on focus.
- Touch targets at least 24x24 CSS px (WCAG 2.5.8); larger for work tools.
- Identifiers (user, e-mail, code, search): `autocapitalize="none"`, `spellcheck="false"`, `autocorrect="off"`
  (`autocorrect` newly since 2026-09-11).
- `inputmode` and `enterkeyhint` are widely available: `inputmode="numeric"` for digits that are not numbers,
  `enterkeyhint="next|done|search|send"`.

## Autofill

- Every field gets the right `autocomplete` token. Never `autocomplete="off"` across a form; only on a one-time code
  that must not be stored or a CAPTCHA.
- Sign-in: `username` (or `email`) and `current-password`, `type="password"`, "show password" and "forgot password",
  paste allowed, nothing asked twice. The button names the action ("Sign in").
- Sign-up: `new-password`; one full-name field with `autocomplete="name"`, accepting any Unicode (no Latin-only
  pattern). E-mail, password and submit near the top on mobile.
- Address: one `<textarea autocomplete="street-address">`, or `address-line1/2/3`, `address-level2` (city),
  `postal-code`; only the first line required. Shipping and billing in `<fieldset>`s with the `shipping`/`billing`
  prefix; token order is `section-*`, then `shipping|billing`, then the detail token.
- Payment: `cc-number`, `cc-name`, `cc-exp`, `cc-csc`, as `type="text" inputmode="numeric"`; allow spaces in the card
  number. Never `type="number"` for card, postal code, document numbers or codes; never `type="password"` for the CSC.
- Style autofilled fields with `input:is(:autofill, :-webkit-autofill)` (a plain list drops the whole rule; `:autofill`
  is limited) and keep a non-color focus indicator.

## Validation

- Native constraints (`required`, `type`, `pattern` (anchored), `minlength`) plus server validation; client checks
  are UX, never security.
- Style errors with `:user-invalid` (widely since 2026-05-02), never bare `:invalid` (red before the user typed).
- Timing: on `input` only clear errors; on `blur` validate the edited field; on `submit` block and move focus to the
  first invalid field, or to an error summary on a long form.
- Do not disable the submit button before sending: it hides the native feedback. Disable it after a valid submit to
  stop duplicates.
- An error has visible text that says how to fix it and an icon with a text alternative, not color alone.
- Hide a rules list with `visibility: hidden`, not `display: none`: the layout shift between mousedown and mouseup
  moves the button and loses the click.
- Never put constraint attributes on a field that can be hidden (a collapsed section, an inactive tab, a native input
  behind a custom control): the browser blocks the submit and cannot focus the field to show why. Validate those in
  code and show the reason on screen.
- `maxlength` truncates pasted text to the FIRST N characters before any handler: for "keep the last N" (card last
  four), trim in the handler instead.

## One-time codes

- One field: `<input type="text" inputmode="numeric" autocomplete="one-time-code" pattern="\d{6}" maxlength="6">`.
  Never one box per digit, `type="number"` or `type="tel"`.
- SMS last line `@host #123456`. WebOTP (`'OTPCredential' in window`, `navigator.credentials.get({ otp: { transport:
  ['sms'] }, signal })`) is limited (Chromium, Safari 27); abort it on manual submit, resend and unmount; on success
  fill the field and `form.requestSubmit()`.
- Never log the code. The server binds the code to the session, rate-limits, expires and invalidates it, and checks
  CSRF. SMS is exposed to SIM swap: prefer passkeys as the primary factor.

## Enter key and input methods

- A custom Enter handler (textarea send, inline rename, command palette) checks composition first:
  `if (e.isComposing || e.keyCode === 229) return;` under `e.key === 'Enter'`, then `preventDefault()`. Japanese,
  Chinese and Korean input confirm candidates with Enter; Safari fires `compositionend` before that keydown.
- Shift+Enter in a textarea is a new line. Submit with `form.requestSubmit()` (runs validation and the submit event),
  never `form.submit()`. Keep a visible submit button.

## Field sizing

- `field-sizing: content` is newly available (2026-06-16): treat as enhancement. Inputs:
  `min-inline-size: 15ch; max-inline-size: 50ch`; textareas: explicit width and `min-block-size: 3lh;
  max-block-size: 10lh`. Without support the field keeps its fixed size, which is acceptable.

## Switch

- `<label>Notifications <input type="checkbox" switch></label>`, read `.checked`. Native `switch` is limited (Safari
  17.4 only): polyfill only when `!('switch' in HTMLInputElement.prototype)`, or a checkbox with `role="switch"`.
- Visible focus ring of at least 3px with offset; `accent-color` (limited) needs a 3:1 check because some engines
  render an invisible checkmark.
- The helper text says the current state and its effect ([product-ui copy](../../product-ui/references/copy.md)).

## Not losing input

- A save on leaving the page uses `fetch(url, { keepalive: true })` from `pagehide` or `visibilitychange`, never
  `unload`. The keepalive body budget is 64 KiB per page, summed over in-flight requests and released only when each
  response body is read or cancelled: always `await res.body?.cancel()`.
- Retry network and 5xx failures; never retry 4xx; only the newest save counts.
- Never keep typed personal data in `localStorage`, `sessionStorage` or IndexedDB as a draft
  ([security.md](security.md) §Cookies and browser storage).

## Sources

- Guides `forms/*` (autofill-*, validate-input-after-interaction, required-field-feedback, ime-safe-enter-submit,
  sms-otp-form, switch, form-fields-automatically-fit-contents) in
  https://github.com/GoogleChrome/modern-web-guidance (read 2026-11-15)
- https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/autocomplete
- https://api.webstatus.dev/v1/features/ (user-pseudos, field-sizing, web-otp, switch-control, accent-color,
  autocorrect, inputmode, enterkeyhint)
