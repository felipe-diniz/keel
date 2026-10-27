# Project config

Read when you create or change `.claude/showcase.json`, a script picks the wrong brand, URL, login or output folder, or you need to know which key does what.

Every script finds the config by walking up from the current directory to the first `.claude/showcase.json`; that directory is the project root and every path in the file is relative to it. `--config <file>` points elsewhere. Without a file the defaults below hold: a neutral palette, the system fonts, the product name as the wordmark, `http://localhost:3000`. CLI flags override the config (`--base-url`, `--theme`, `--footer`); the storyboard's `voice`, `music` and `theme` override the config's.

## Example

```json
{
  "product": "Acme",
  "site": "acme.example",
  "locale": "pt-BR",
  "timezone": "America/Sao_Paulo",
  "baseUrl": "http://localhost:3000",
  "captureHosts": ["staging.acme.example"],
  "palette": {
    "dark":  { "bg": "#0f141b", "frame": "#19202a", "text": "#e6e9ee", "muted": "#9aa5b5", "tertiary": "#6e7a8c",
               "accent": "#f5a524", "onAccent": "#1d1300", "glow": "#5b8cff" },
    "light": { "bg": "#fbfaf7", "frame": "#ffffff", "text": "#0b0d12", "muted": "#4a5363", "tertiary": "#677083",
               "accent": "#b25e00", "onAccent": "#ffffff", "glow": "#3a5bd9" }
  },
  "logo": { "dark": "public/brand/logo-dark.svg", "light": "public/brand/logo-light.svg" },
  "fonts": { "display": "public/fonts/display.woff2", "body": "public/fonts/body.woff2" },
  "theme": { "default": "dark", "localStorage": "acme_theme", "cookie": "acme_theme", "darkClass": "dark" },
  "login": {
    "url": "/login", "user": "#email", "password": "#password", "submit": "button[type=submit]",
    "success": "/dashboard", "userEnv": "SHOWCASE_USER", "passwordEnv": "SHOWCASE_PASSWORD"
  },
  "mask": {
    "presets": ["cpf", "cnpj", "phone-br", "email"],
    "patterns": [{ "regex": "\\s*zzseed\\s*", "replace": " " }],
    "hide": ["[data-testid=dev-banner]"]
  },
  "hideSelectors": ["nextjs-portal"],
  "contentTimeoutMs": 180000,
  "copy": {
    "sources": ["docs/commercial-guide.md", "docs/pricing.md"],
    "notDo": "docs/what-we-do-not-do.md",
    "releaseNotes": "docs/release-notes/",
    "rules": ["no em dash", "never promise a roadmap item", "prices only from docs/pricing.md"]
  },
  "output": "marketing",
  "voice": { "voice_id": "<id from audio.mjs voices>", "name": "Narrator", "model_id": "eleven_v4",
             "language_code": "pt", "settings": { "speed": 1.08 }, "pronounce": { "Acme": "Ácme" } },
  "music": { "model_id": "music_v2_5", "prompt": "warm minimal electronic, 100 bpm, no vocals" }
}
```

## Keys

| Key | Used by | Meaning |
|---|---|---|
| `product` | art, compose, audio | Name for the wordmark (when there is no logo), the logo's alt text and the default preview line |
| `site` | art, capture record | Default footer of the art |
| `locale`, `timezone` | capture, art | Browser locale and time zone of the capture: dates and numbers render as the audience reads them |
| `baseUrl` | capture, art | The app under capture. Overridden by the plan's `baseUrl` and by `--base-url` |
| `captureHosts` | capture, art | Non-local hosts allowed (a staging with seed data). Loopback, `*.localhost` and `*.test` are always allowed; anything else is refused, so production is never captured by accident |
| `palette.dark`, `palette.light` | all | Brand colors per theme, merged over the neutral defaults key by key. `onAccent` is text drawn on the accent; `glow` is the second background light; `chrome` and `field` are the browser bar and URL field of the landscape window |
| `logo` | art, compose | A path, or one per theme. SVG, PNG or WebP. Missing: the product name is drawn as a wordmark |
| `fonts.display`, `fonts.body` | art, compose | Font files (woff2 preferred). Missing: the system UI font |
| `theme.default` | all | Theme when neither the plan, the deck nor `--theme` says |
| `theme.localStorage`, `theme.cookie` | capture, art | Storage key and cookie the app reads before its first paint; written before every navigation. Toggling a class on a loaded page loses to the app's theme provider |
| `theme.darkClass` | capture, art | Class on `<html>` that proves the theme took. Set it: a capture in the wrong theme fails instead of shipping |
| `login` | capture, art | The recipe: page `url`, CSS or Playwright selectors for `user`, `password`, `submit`, the `success` URL fragment, and the NAMES of the environment variables that hold the seed user and password. Never the values |
| `mask.presets` | capture, art | Default all four: Brazilian CPF and CNPJ, Brazilian phone (with or without +55, last 4 digits kept), e-mail (domain kept). `[]` turns the presets off |
| `mask.patterns` | capture, art | The project's own text replacements (`regex`, `flags`, `replace`), e.g. a seed marker or another country's document |
| `mask.hide` | capture, art | Selectors set invisible before the shot (a dev banner, an avatar with a real face) |
| `hideSelectors` | capture, art | Dev overlays hidden by CSS (framework badges, toasts) |
| `contentTimeoutMs` | capture, art | Ceiling of the "real content" wait; minutes, because a dev server compiles a route on its first visit |
| `copy.sources` | method | Sources of truth for claims: commercial guide, pricing, docs |
| `copy.notDo` | method | What the product does not do; a claim against it is a lie |
| `copy.releaseNotes` | method | Folder of the published release notes |
| `copy.rules` | method | The project's hard copy rules, applied to every text the skill writes |
| `output` | method | Root of the media folders (default `marketing/`). Media is gitignored; copy and storyboards are versioned |
| `voice`, `music` | audio | Default voice and music blocks; a storyboard's own blocks win key by key |

## Secrets stay out

- The seed credentials are read by the scripts from the process environment at run time, by the names in `login.userEnv` and `login.passwordEnv`. Export them in the shell or run the script with the project's own env loader; the agent does not open env files.
- The ElevenLabs key never goes in this file: see [setup](setup.md).
- This file is versioned. Nothing in it may be a value someone could log in with.

## Gitignore

Add to the project's `.gitignore`, adjusting the root to `output`:

```
marketing/**/*.png
marketing/**/*.jpg
marketing/**/*.mp4
marketing/**/*.mp3
marketing/**/*.wav
marketing/**/*.webm
marketing/**/cenas/
marketing/**/frames/
marketing/**/audio/
marketing/**/.composer/
```
