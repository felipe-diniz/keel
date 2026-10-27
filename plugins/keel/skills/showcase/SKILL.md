---
name: showcase
description: Marketing and release-note media for any project from its real screens with seed data - vertical Reel 1080x1920, landscape release video 1920x1080, post art, carousel, covers - with kinetic or word-timed captions, optional ElevenLabs narration and music, plus the copy method for social posts and release notes (WhatsApp message included). Use when asked for a Reel, a video of what is new, post art or a carousel, a social post, or a release note. The owner publishes; the skill never does.
---

# Showcase

Media that sells a product shows the real product, says only what it does, and never shows a real person's data. The
scripts in `scripts/` capture the project's local app by a JSON plan, compose frame by frame from a storyboard, and mix
audio with ffmpeg. The detail lives in `references/`: open only the one the step needs.

## Hard rules

1. **Never production data.** Capture the local app or a listed staging, with seed users whose credentials the
   scripts read from the environment by name. The host guard refuses anything else.
2. **Mask by default.** CPF, CNPJ, phone and e-mail are replaced in the DOM before every shot; the project adds its
   own patterns. Masking covers formats, not names: look at every frame.
3. **Every claim checked** against code or the project's sources of truth (`copy.sources`, `copy.notDo`) before it
   goes into copy, caption or voice. The project's hard copy rules (`copy.rules`) apply to every text.
4. **Stills before narration.** Approve frames and covers silent; the voice costs credits and is generated once.
5. **The ElevenLabs key is the owner's.** The agent never reads, prints, copies or asks for it, nor opens
   `~/.config/keel/elevenlabs.env`; only `audio.mjs` reads it at run time. No real API call in tests or checks.
6. **The owner publishes.** The skill delivers files and text; it never posts, uploads or sends.

## Flow

1. **Subject** from the sources of truth: the release-notes folder, the commercial guide, the commits since the last
   note ([social-post](references/social-post.md), [release-notes](references/release-notes.md)).
2. **Check every claim** against code or docs; drop what does not hold.
3. **Copy**: the post variants or the release note and its WhatsApp message.
4. **Capture plan** of the screens that prove the copy ([capture](references/capture.md)); look at `cenas/*.png`.
5. **Storyboard**, validated, then `--only stills`: frames, covers, carousel or poster
   ([storyboard](references/storyboard.md)). Review every image (data, theme, skeleton, cut text, tap target).
6. **Narration**, only after the stills are approved and only with a key; check the speech
   ([audio](references/audio.md)). Without a key: silent with kinetic captions, or a music file the user provides.
7. **Render** the video; check size, fps, duration and loudness; look at the frames again.
8. **Deliver**: paths of the media, the copy, alt text, and what the owner must approve. The owner publishes.

## Scripts

| Script | Does |
|---|---|
| `doctor.mjs [--json] [--install]` | Node, ffmpeg, Playwright and Chromium, the config, the key (configured or not, never its value) |
| `capture.mjs --plan p.json --out d` | Scenes to `cenas/` + `cenas.json`; `record` mode: a 12 s Reel from a screen recording |
| `compose.mjs --storyboard s.json --out d` | Reel or landscape video, covers, carousel, poster, frames, WebVTT; `--validate`, `--only`, `--music`, `--narration` |
| `audio.mjs voices\|preview\|narration\|music\|usage` | ElevenLabs voice with per-word timing, music, `consumo.json` |
| `art.mjs` | Post art (feed, square, story), `--deck` carousel, `--no-shot` typographic |

Run them as `node <skill>/scripts/<name>` from the project root. Node ≥ 20, ffmpeg, and Playwright (the project's,
else the skill's cache at `~/.cache/keel/showcase/`); no other dependency.

## Project config

`.claude/showcase.json` in the project: product and site, locale and time zone, palette per theme, logo and fonts,
base URL and allowed hosts, theme storage keys, the login recipe with the NAMES of the env vars of the seed user,
masking, the copy sources and hard rules, the output folder (default `marketing/`, media gitignored), and the default
voice. Flags override it; nothing in the plugin names a project ([config](references/config.md)).

## References (read when…)

| File | Read when |
|---|---|
| [references/setup.md](references/setup.md) | first run on a machine or project, something is missing, or the ElevenLabs key must be configured |
| [references/config.md](references/config.md) | writing or changing `.claude/showcase.json`, or the brand, login or output is wrong |
| [references/capture.md](references/capture.md) | writing a capture plan, recording a Reel, or a captured screen came out wrong |
| [references/storyboard.md](references/storyboard.md) | writing a storyboard, timing scenes, covers, carousel, poster, or a render fails |
| [references/audio.md](references/audio.md) | voice, narration, music, credits, checking the speech, or the mix |
| [references/social-post.md](references/social-post.md) | writing a social post: subject, claims, Instagram, Facebook, story, format, cadence, alt text |
| [references/release-notes.md](references/release-notes.md) | writing a release note, its WhatsApp message and its video |

## What fails a review

- A frame with a real person's data, a production URL, a skeleton or the wrong theme.
- A claim the code or the sources of truth do not back, or one that breaks `copy.rules`.
- Narration generated before the stills were approved, or regenerated to fix framing.
- A video not `yuv420p`, a caption cut by the safe area, a landscape video with narration and no WebVTT.
- The key, its length or the seed password in any output, log or message.
- Anything posted, uploaded or sent by the agent.
