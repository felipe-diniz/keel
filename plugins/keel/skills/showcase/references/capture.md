# Capture plans

Read when you write or debug a capture plan for `capture.mjs` (scenes for the compositor, or a recorded Reel), or a captured screen came out wrong: wrong theme, skeleton, unmasked data, a sidebar open, a missing point.

## Commands

```bash
node <skill>/scripts/capture.mjs --plan <plan.json> --out <output>/videos/<YYYY-MM-DD>-<slug> [--only a,b] [--theme light]
node <skill>/scripts/capture.mjs record --plan <plan.json> --out <dir> [--seconds 12]
```

- Scenes mode writes `<out>/cenas/<name>.png` and `<out>/cenas/cenas.json`. `cenas.json` is saved after every scene; `--only` reshoots the named scenes and keeps the rest.
- Record mode writes `<out>/<record.name>-reel.mp4`: 1080x1920, 30 fps, silent, the screen as a band under the headline.
- Plans are versioned next to the storyboard (`<output>/decks/<slug>.capture.json`); the PNGs are not.

## Plan

```json
{
  "baseUrl": "http://localhost:3000",
  "viewport": { "width": 390, "height": 844 },
  "dsf": 3,
  "mobile": true,
  "theme": "dark",
  "login": true,
  "clock": false,
  "storage": { "localStorage": { "cookie_consent": "accepted" }, "cookies": [{ "name": "tour_done", "value": "1" }] },
  "hide": [".chat-widget"],
  "mask": true,
  "scenes": [
    { "name": "home", "url": "/app/home", "wait": [{ "selector": "[data-testid=agenda]" }, { "content": true }],
      "points": { "next": "[data-testid=next-appointment]", "title": "h1" } },
    { "name": "history", "url": "/app/history", "full": true, "bar": "nav.bottom-bar",
      "wait": [{ "text": "Last 30 days" }], "points": { "chart": "[data-testid=chart]" } },
    { "name": "reschedule-done", "url": "/app/home",
      "actions": [{ "click": "role=button[name=\"Reschedule\"]" }, { "click": "[data-day='2']" },
                  { "wait": { "selector": "[data-testid=done]" } }],
      "points": { "done": "[data-testid=done]" } }
  ]
}
```

| Key | Default | Meaning |
|---|---|---|
| `baseUrl` | config `baseUrl` | Overridden by `--base-url`. Must be loopback or in `captureHosts` |
| `viewport`, `dsf` | 1024x768, 2 | CSS size and device scale. Phone scenes: 390x844 at 3, so a 1170 px capture stays sharp at 1080. Landscape release video: 1440x810 at 1.25. Desktop art: 1024 wide keeps the desktop layout with legible text |
| `mobile` | false | `isMobile` + `hasTouch`; clicks become taps |
| `theme` | config `theme.default` | Written to the config's storage key and cookie before every navigation; checked against `theme.darkClass` before each shot |
| `login` | true when the config has a recipe | `false` skips it; an object overrides keys of the recipe (another seed persona: other `userEnv`/`passwordEnv`) |
| `clock` | false | Installs Playwright's clock before load; needed by `burst` and `clock` actions |
| `storage` | none | Extra localStorage entries (written before scripts run) and cookies (consent banners, finished tours) |
| `hide` | none | Selectors hidden in every shot, on top of the config's `hideSelectors` |
| `mask` | true | `false` disables masking for a plan with no personal data at all; leave it on |
| `mouse` | bottom-right, 24 px in | `{x, y}` where the cursor parks before a desktop shot; `false` leaves it |

### Scene

| Key | Meaning |
|---|---|
| `name` | Required; the key in `cenas.json` and the file name |
| `url` | Path joined to `baseUrl`; omitted, the scene continues on the current page |
| `waitUntil` | `domcontentloaded` by default. Do not use `networkidle` on an app with realtime: it never arrives |
| `wait` | List, in order: `{selector}`, `{text, exact?}`, `{url}` (fragment), `{content: true}` (no skeleton and > 40 chars of text in `main`), `{networkidle: true}`, `{ms}` or a number; each takes `timeout` |
| `actions` | List, in order: `{click}`, `{tap}`, `{fill, value}` or `{fill, valueEnv}`, `{select, option}`, `{press, selector?}`, `{scroll: {to, top}}` (nearest scrollable ancestor), `{scroll: {y}}`, `{scroll: {by, steps, pause}}` (smooth, by script), `{wait: <wait>}`, `{clock: "pause"|"run"|"resume", ms?}`, `{goto}` |
| `points` | `{name: selector}` measured as `{x, y, w, h}` in page coordinates (scroll included): what the storyboard taps, focuses and scrolls to |
| `full` | Full-page capture, for the compositor to scroll through; `height` is the document height |
| `bar` | With `full`: a fixed bar shot apart as `<name>-barra.png` and hidden on the page; the compositor pins it to the bottom |
| `burst` | Frame-exact animation: `{clip, frames, stepMs, actions, points, name?}`; see below |

Selectors are CSS or any Playwright selector (`role=button[name="Save"]`, `text=Done`), so a scene can be written against what the user sees.

### Burst (frame-exact animation)

With `"clock": true`, a scene's `burst` measures `clip` (and its `points`, BEFORE the trigger), pauses the page clock, runs its `actions` (the trigger), then shoots `frames` clipped screenshots, `stepMs` of page time apart, into `cenas/<name>/000.png...`. `cenas.json` gets `{dir, count, clip}` under `<scene>-quadros` (or `burst.name`) and a point of the same name. The storyboard plays it with `shots[].burst`. Wall-clock recording of an animation drops frames whenever the CPU is busy; the paused clock does not.

## `cenas.json`

```json
{ "viewport": { "width": 390, "height": 844 }, "dsf": 3, "theme": "dark",
  "scenes": {
    "home": { "file": "home.png", "width": 390, "height": 844, "scrollY": 0, "url": "/app/home",
              "points": { "next": { "x": 16, "y": 212, "w": 358, "h": 96 } }, "masked": 2 },
    "history": { "file": "history.png", "width": 390, "height": 2210, "scrollY": 0, "url": "/app/history",
                 "bar": { "file": "history-barra.png", "h": 64 }, "points": {} },
    "history-quadros": { "dir": "history-quadros", "count": 52, "clip": { "x": 16, "y": 140, "w": 358, "h": 300 } } } }
```

`masked` counts the values the masking replaced in that shot; zero on a screen with people on it means the format is not covered: add a `mask.patterns` entry.

## Record mode

`record`: `{seconds, name, eyebrow, headline, sub, footer, hold, top}`. Each scene opens, waits, is masked, holds `hold` ms (1200), then plays its `actions` while the video records. The last scene is held until `seconds` have passed since its start. ffmpeg keeps the last `seconds` (`-sseof`) and lays the recording 1016 px wide at a fixed top (1000, raised for a taller ratio) on the story art. Keep the motion simple: entry, settle, a slow scripted scroll. In 12 s the viewer must READ the screen.

## Traps

- Never production: the host guard refuses a non-local host not in `captureHosts`. Seed users only; their credentials come from the environment by the names in the config.
- The cursor never touches an edge: a pointer at the top-left corner opened a sidebar over the page. Desktop shots park it near the bottom-right; record mode never moves it, and scrolls by script, not by wheel.
- Measure points before masking or any text change: a locator by text stops matching once the text is cleaned. `settle` measures, then masks.
- Wait for real content before the shot; no skeleton is not content. The ceiling is minutes on a dev server's first visit to a route.
- A control that only exists on the loaded screen (a privacy toggle, a tab) is reachable only after the content wait: put the click after it in `actions`.
- Check the theme after applying it (`theme.darkClass`): a provider that rereads storage on hydration undoes a class toggle.
- A missing focus or point selector fails the run: a silent fallback publishes the wrong screen.
- A login button can stay disabled while the page hydrates; the login refills in a loop. A captcha on the login form blocks headless runs: disable it in the local environment, by the project's own switch.
- A second login as the same user usually ends the first session: a token taken before is dead. One login per run; for an API call after it, take a fresh token.
- An action that writes (reschedule, send, release) changes the seed: a re-run may need the seed reset. Note it in the plan's scene name or comment.
- `context.close()` finishes the webm; reading before it gets a truncated file.
- `yuv420p` on every MP4: without it the file opens on a computer and fails on a phone.
- Masking covers formats, not names or free text. Look at every PNG before composing; a published image has no undo.
