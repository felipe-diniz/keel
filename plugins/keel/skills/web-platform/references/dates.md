# Dates, times and time zones

Read when storing, computing, comparing or showing a date, time, duration or deadline, scheduling across time zones
or daylight saving, or choosing between `Date`, Temporal and Intl.

Status checked on webstatus.dev on 2026-11-15.

## Rules of the domain

- A moment (log, created at, payment time) is an instant in UTC. A calendar fact (birthday, check-in day, opening
  hours, a booking at 14:00 local) is a plain date or time in a named zone. Never store one as the other.
- Every computation and display names its time zone explicitly: the tenant's or the user's zone from the server,
  an IANA name (`America/Sao_Paulo`), never a fixed offset and never silently the browser's zone.
- An empty or invalid zone falls back to one documented default constant with a warning; it never becomes "whatever
  the browser has". Keep that default in one place and lint against literal zone strings elsewhere.
- A layer between client and server (BFF, proxy) never fills in or overrides the zone the backend sent.
- `new Date("1990-01-01")` is UTC midnight: west of UTC it shows the previous day. Parse date-only strings as plain
  dates.

## Temporal (limited)

- Chromium 144 and Firefox 139 ship it; Safari does not (MDN lists a future 27.3, unverified). Load a polyfill
  conditionally: `if (typeof Temporal === 'undefined')` import `temporal-polyfill` (or `@js-temporal/polyfill`),
  pinned and self-hosted, and assign `globalThis.Temporal`.
- Use the narrowest type: `PlainDate` (birthday, due date), `PlainTime` (opening hours), `PlainDateTime` (local
  agenda without zone), `PlainYearMonth` (card expiry), `PlainMonthDay` (fixed holiday); `Instant` or `ZonedDateTime`
  for moments.
- `ZonedDateTime.from(..., { disambiguation })`: `compatible` (default) or `reject` for times that do not exist or
  repeat at a DST change; convert with `withTimeZone()`.
- Differences: pass `largestUnit` to `since`/`until`/`round` (a `ZonedDateTime` defaults to hours, giving `PT720H`).
  `Duration.compare` needs `relativeTo` with months, years or days. `sign < 0` means overdue.
- Compare with `.equals()`/`compare()`, never strings. Objects are immutable.
- `add({ months: 1 })` on Jan 31 clamps to the end of February; pass `overflow: 'reject'` when that must fail.

## Display

- Format with `Intl.DateTimeFormat` / `toLocaleString(locale, { timeZone })`; durations with `Intl.DurationFormat`
  (newly since 2025-03-04), never by concatenating units. `toString()` is ISO for machines.
- Read parts from the Temporal object (`.year`, `.month`), not from `formatToParts()`.
- Relative times ("in 3 days") with `Intl.RelativeTimeFormat`, computed in the same zone as the display.

## Sources

- Guides `js/support-global-calendar-systems`, `js/calculate-event-differentials`, `js/capture-location-agnostic-data`
  in https://github.com/GoogleChrome/modern-web-guidance (read 2026-11-15)
- https://api.webstatus.dev/v1/features/temporal, /intl-duration-format
- https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Temporal
