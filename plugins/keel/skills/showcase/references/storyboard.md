# Storyboards

Read when you write or change a storyboard for `compose.mjs` (Reel, landscape release video, covers, carousel, poster), time scenes, or a render fails validation or looks wrong.

## Commands

```bash
node <skill>/scripts/compose.mjs --validate --storyboard <deck.json> [--out <dir>]   # schema; with --out, names vs cenas.json
node <skill>/scripts/compose.mjs --storyboard <deck.json> --out <dir> --only stills   # covers, carousel, poster, frames
node <skill>/scripts/compose.mjs --storyboard <deck.json> --out <dir>                 # + silent video, kinetic captions
node <skill>/scripts/compose.mjs --storyboard <deck.json> --out <dir> --music <file>  # + music, no key needed
node <skill>/scripts/compose.mjs --storyboard <deck.json> --out <dir> \
  --narration <dir>/audio/narracao.json [--music <dir>/audio/musica.mp3]             # voice, karaoke caption, VTT
```

- `--only video` renders the frames and the video; `--only audio` redoes only the mix over `.composer/video.mp4` (after a video render with `--narration` or `--music`).
- Every render validates first. With `--out` (or `--scenes <dir>`), every shot, burst and point name is checked against `cenas.json`.
- Storyboards are versioned (`<output>/decks/<slug>.json`); the outputs are not.

## Outputs

| Format | Files in `--out` |
|---|---|
| portrait (default) | `reel.mp4` (or `output`), `capa-1080x1920.png`, `capa-1080x1350.png`, `carrossel-NN.png`, `frames/NN-<scene>.png` |
| landscape | `video.mp4` (or `output`), `poster.jpg`, `legendas.vtt` (with narration), `frames/NN-<scene>.png` |

H.264 high, CRF 18, yuv420p limited range, `+faststart`; audio AAC 192k 48 kHz when present.

## Schema

```text
format      "portrait" | "landscape"       portrait: 1080x1920 phone; landscape: 1920x1080 browser window
theme       "dark" | "light"               palette from the config
fps         1..60 (30)
output      "name.mp4"
cover       {scene, at}                    portrait covers: scene id and seconds inside it
poster      {scene, at}                    landscape poster.jpg
voice       {voice_id, name, model_id, language_code, settings, pronounce, seed}   see audio.md
music       {model_id, prompt}
audio       {leadIn .15, sceneLead .18, tail 1.6, lufs -14, truePeak -2, voiceLufs -16, musicGapDb 11,
             duckThreshold .03, duckRatio 4, duckRelease 300, fadeIn .6, fadeOut 1.6}
scenes[]    (required, in order)
  id          unique; ties the scene to its narration
  duration    seconds (rewritten by the retime when narrating)
  device      false: no phone or window, only the background and the CTA (opening, closing)
  frameAt     seconds of the scene's still in frames/ (default duration - 0.45)
  narration   {text, sub}                  text: what the voice says and the karaoke shows; sub: a line under it
  caption     {text, accent[], sub, delay .1, size}   kinetic caption, when there is no narration
  cta         {title, lines[], pill, footer, delay .35}  title is HTML; <em> takes the accent color
  shots[]     {shot, at 0, in, dur .42, scroll, scrollAt, scrollEase, burst, url}
    shot        a scene name in cenas.json
    in          push | rise | fade | cut   transition from the previous screen (of this or the previous scene)
    scroll      number | {point, top 80} | [from, to]   for a `full` capture; px, or a point placed `top` px from the top
    scrollAt    [t0, t1] seconds of the scroll, eased by scrollEase (inOut | out | back | linear)
    burst       {name, at: [t0, t1], ease}  plays a captured frame set over the shot
    url         the address shown in the landscape window bar
  taps[]      {at, point, shot?}           a ring and dot on the point (0.62 s)
  camera[]    {at, s 1, fx, fy, ay 0, rot 0, ease, focus: {point, shot?}}
              keyframes: scale, focus x/y in screen px (or a captured point), vertical anchor offset, rotation
carousel[]  {eyebrow, title, sub, shots[], camera[]}   portrait only: 1080x1350 slides
```

Points and focus are names, resolved against `cenas.json`. The camera interpolates from the previous key to this one with this key's `ease` (inOut by default).

## Portrait Reel example

```json
{
  "theme": "dark", "fps": 30, "cover": { "scene": "hook", "at": 1.6 },
  "scenes": [
    { "id": "hook", "duration": 2.6,
      "narration": { "text": "Your patients book alone, at 2 in the morning." },
      "caption": { "text": "They book alone, at 2 a.m.", "accent": ["alone,"] },
      "shots": [{ "shot": "home", "at": 0 }],
      "camera": [{ "at": 0, "s": 1 }, { "at": 2.2, "s": 1.35, "focus": { "point": "next" } }] },
    { "id": "pick", "duration": 3.0,
      "narration": { "text": "They pick the day, the time, and confirm." },
      "caption": { "text": "Day, time, confirm." },
      "shots": [{ "shot": "booking", "at": 0, "in": "push" }, { "shot": "booking-done", "at": 1.9, "in": "rise" }],
      "taps": [{ "at": 0.9, "point": "day" }, { "at": 1.6, "point": "confirm" }] },
    { "id": "history", "duration": 3.2,
      "narration": { "text": "And the history is one scroll away." },
      "caption": { "text": "History, one scroll away." },
      "shots": [{ "shot": "history", "at": 0, "in": "push", "scroll": [0, { "point": "chart", "top": 90 }], "scrollAt": [0.6, 2.4] }] },
    { "id": "cta", "device": false, "duration": 3.0,
      "narration": { "text": "Try it free for 7 days." },
      "cta": { "title": "Online booking <em>in Acme</em>", "lines": ["Free for 7 days"], "pill": "acme.example", "footer": "acme.example" } }
  ],
  "carousel": [
    { "eyebrow": "Booking", "title": "They book alone", "sub": "Day, time and confirmation, from the phone.",
      "shots": [{ "shot": "booking", "at": 0 }], "camera": [{ "at": 0, "s": 1.1, "ay": 120 }] }
  ]
}
```

## Landscape release video example

```json
{
  "format": "landscape", "theme": "dark", "fps": 30, "output": "whats-new-2026.10.24.mp4",
  "poster": { "scene": "opening", "at": 2.2 },
  "voice": { "voice_id": "<id>", "model_id": "eleven_v4", "language_code": "pt", "settings": { "speed": 1.08 } },
  "scenes": [
    { "id": "opening", "device": false, "duration": 4,
      "narration": { "text": "What is new in Acme this week." },
      "cta": { "title": "What is new in <em>Acme</em>", "lines": ["October 24"], "footer": "acme.example" } },
    { "id": "access", "duration": 7,
      "narration": { "text": "The patient record now has an access button." },
      "shots": [{ "shot": "record-access", "at": 0, "in": "fade", "url": "/records/patients" }],
      "taps": [{ "at": 3.2, "point": "access" }],
      "camera": [{ "at": 0, "s": 1 }, { "at": 3.0, "s": 1.4, "focus": { "point": "access" } }, { "at": 6.5, "s": 1 }] },
    { "id": "closing", "device": false, "duration": 4,
      "narration": { "text": "Open Acme to see it." },
      "cta": { "title": "Open <em>Acme</em>", "lines": [], "footer": "acme.example" } }
  ]
}
```

In landscape the window takes the captured viewport (1440x810 at dsf 1.25 fills the 1680 px window sharply), with the address bar fed by `shots[].url`. Under narration nothing is burned in: the player shows `legendas.vtt`.

## Timing

- Without narration the durations are the cut. A kinetic caption needs about 0.45 s plus 0.075 s per word to land, and the last 0.3 s of a scene fades it out: a scene shorter than its caption cuts it mid-air.
- Stills sit where the text is still. A scene's text settles at `delay + (words - 1) * 0.075 + 0.45` (an accent's highlight 0.6 s after its word starts, the sub 0.55 s after the last word; a CTA part every 0.12 s plus 0.5 s, the brand mark included) and a kinetic caption leaves from `duration - 0.3`. `--validate` refuses a `cover.at` or `poster.at` outside that window; the scene frames default inside it, and the render warns when a scene is too short for its text.
- The title wraps inside the side margins (90 px in the Reel, 80 in the feed, 160 in landscape) and shrinks when one word alone passes the width or the title passes its height budget.
- Read time: 2.5 to 4 s per scene for a Reel, 5 to 9 s for a release video scene with a tap and a zoom. A Reel of 15 to 30 s; a release video of 60 to 90 s.
- Taps land after the screen settles (at + dur), and the camera reaches the focus before the tap, not with it.
- The first scene carries the hook: the claim of the piece in the first 1.5 s, with the screen already visible.

## Retime to speech

With `--narration`, the speech sets the clock, not the storyboard:

- Scene N starts `sceneLead` (0.18 s) before its first word; the first scene starts at 0; the voice enters after `leadIn` (0.15 s).
- The last scene ends `tail` (1.6 s) after the last word.
- Times inside a scene (`at` of shots, taps and camera keys, `scrollAt`, `burst.at`, `frameAt`, `cta.delay`) stretch by the ratio new/old duration. Transition `dur` and the tap gesture do not stretch.
- So write the storyboard durations in the proportion you want inside each scene; the absolute values come from the voice.
- The spoken caption replaces the kinetic one; `narration.sub` stays under it only where it says what the voice does not (a disclaimer that the data is illustrative). On a CTA scene the CTA text is the caption: each word lights up when said.
- Landscape gets a WebVTT: a cue per sentence, pause over 0.6 s or 84 characters, at most two lines of 42, ending 0.2 s after its last word.

## Review the frames

Before the video, render `--only stills` and look at every `frames/NN-<scene>.png`, the covers and the carousel: personal data, wrong theme, a skeleton, a caption over the screen, a tap off its target, text cut by the safe area (Reel safe area: 150 px from the top, 320 px from the bottom). Fix the plan or the storyboard, not the output.
