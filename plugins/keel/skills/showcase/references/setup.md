# Setup and doctor

Read when the skill runs for the first time on a machine or a project, a script says Playwright, Chromium or ffmpeg is missing, or narration needs the ElevenLabs key.

## Doctor

```bash
node <skill>/scripts/doctor.mjs           # human report, exit 1 if a requirement is missing
node <skill>/scripts/doctor.mjs --json    # the same, as JSON
node <skill>/scripts/doctor.mjs --install # Playwright + Chromium into ~/.cache/keel/showcase/
```

`<skill>` is this skill's folder (the directory of this file's parent). Run the doctor from the project root so it finds `.claude/showcase.json`.

| Check | Needed for | Fix |
|---|---|---|
| Node ≥ 20 | everything | install a current Node |
| ffmpeg with `libx264`, `aac`, `loudnorm`, `sidechaincompress`, `alimiter`, `amix`, `adelay`, `afade` | video, mix | `brew install ffmpeg` (macOS) or the distro's full build |
| ffprobe | checking outputs | ships with ffmpeg |
| Playwright and its Chromium | capture, art, compose | see below |
| `.claude/showcase.json` | brand, login, masking, copy rules | write it from [config](config.md); without it the defaults hold |
| ElevenLabs key | narration, generated music | see below; optional |

## Playwright

Resolution order, so the browser build matches the project's tests when it has them:

1. The project's `node_modules` (`playwright`, else `@playwright/test`). If its Chromium is not downloaded, run the project's own `npx playwright install chromium`.
2. The skill's cache, `~/.cache/keel/showcase/`. `doctor.mjs --install` runs there, and only there, `npm install playwright@<pinned>` and `playwright install chromium`. The pinned version is `PLAYWRIGHT_VERSION` in `scripts/lib/playwright.mjs`.

The skill installs nothing in the project. The scripts import nothing else from npm.

## The ElevenLabs key (optional)

The key is the owner's. The agent never reads, prints, copies or asks for it, and never opens the file below. The owner creates the file in their own terminal, typing the key at the prompt so it lands in no shell history:

```bash
mkdir -p ~/.config/keel && chmod 700 ~/.config/keel
( umask 077; if [ -n "$ZSH_VERSION" ]; then read -rs "k?ElevenLabs key: "; else read -rsp "ElevenLabs key: " k; fi; echo; printf 'ELEVENLABS_API_KEY=%s\n' "$k" > ~/.config/keel/elevenlabs.env; unset k )
chmod 600 ~/.config/keel/elevenlabs.env
```

It works in zsh and bash (checked with a fake key on 2026-10-27), runs in a terminal of the owner's, and the key is not echoed.

- `ELEVENLABS_API_KEY` in the process environment wins over the file; only that one line of the file is read, nothing else in it enters the process.
- The file lives outside every repo, so no commit can carry it.
- Check it with `doctor.mjs`: it prints `ElevenLabs key configured (env|file)` or `not configured`, and warns when the file mode is not 600. It never prints the value or its length.
- A key scoped to Text to Speech, Music and Voices read is enough. `audio.mjs usage` needs `user_read` and returns 401 without it; spend is then the `consumo.json` of each piece (see [audio](audio.md)).

## What works without the key

- Capture, stills, covers, carousel, post art, frames per scene.
- Silent Reel and landscape video with kinetic captions.
- Music under the video from a file the user provides (`compose.mjs --music <file>`): faded, loudness-normalized to -14 LUFS, no ducking because there is no voice.
- Not available: narration, the karaoke caption, the WebVTT track (it needs spoken word times) and generated music.

## Running in a project for the first time

1. `doctor.mjs`; fix what is missing.
2. Write `.claude/showcase.json` ([config](config.md)); add the media lines to `.gitignore`.
3. Start the app locally with seed data (the project's own command; never point a capture at production).
4. Export the seed credentials under the names of `login.userEnv` and `login.passwordEnv`.
5. A first capture plan with one scene ([capture](capture.md)); look at `cenas/<name>.png` before writing a storyboard.
