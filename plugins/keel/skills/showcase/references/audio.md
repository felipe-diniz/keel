# Narration, music and the mix

Read when a piece gets a voice or music: choosing a voice, writing the narration, generating it with `audio.mjs`, checking the speech, budgeting credits, or tuning the mix in `compose.mjs`.

Narration and generated music need the owner's ElevenLabs key ([setup](setup.md)). Without it, a user-provided music file still mixes (`compose.mjs --music <file>`).

## Order (credits are spent once)

1. Captures approved ([capture](capture.md)).
2. Storyboard with `narration.text` per scene; `compose.mjs --only stills` and the owner approves the frames ([storyboard](storyboard.md)). Framing is fixed BEFORE the voice: a narration call costs real credits, and a reframe after it does not need a new voice, a rewrite of the text does.
3. Voice chosen with `voices` and one `preview` line.
4. `audio.mjs narration`, then check the speech (below).
5. `audio.mjs music` (its length follows the narration), or the user's own file.
6. `compose.mjs --narration <out>/audio/narracao.json --music <out>/audio/musica.mp3`.

## Commands

```bash
node <skill>/scripts/audio.mjs voices [--language pt] [--accent brazilian]
node <skill>/scripts/audio.mjs preview --voice <voice_id> --text "One short line." [--model eleven_v4] [--language pt] --out <dir>
node <skill>/scripts/audio.mjs narration --storyboard <deck.json> --out <dir> [--force]
node <skill>/scripts/audio.mjs music --storyboard <deck.json> --out <dir> [--force]
node <skill>/scripts/audio.mjs usage
```

Outputs under `<out>/audio/`: `narracao.mp3`, `narracao.json`, `musica.mp3`, `consumo.json`, `previa/<name>.mp3`. `narration` and `music` skip when their file exists; `--force` asks again and spends again.

## Voices

- `voices` lists the account's own voices and the public library for a language (and accent), sorted by a year of use. A library voice works by its `voice_id` without being saved to the account (saving needs a write permission the key may lack).
- An account's premade voices are often English; for another language, pick from the library with a native accent.
- `preview` speaks one line and saves it to `previa/`: listen for the product name, numbers and the language's stress before the full narration.
- The voice block (`voice_id`, `name`, `model_id`, `language_code`, `settings`, `pronounce`, `seed`) lives in the storyboard, with a default in the config. The source pipeline shipped with `settings.speed` 1.08.

## Models

| Use | Model | Note |
|---|---|---|
| Narration | `eleven_v4` | the one the source pipeline shipped with; set `language_code` |
| Preview default | `eleven_multilingual_v2` | when neither flag nor storyboard says |
| Music | `music_v2_5` | `music_v1` is the script default; always `force_instrumental` |

Model names and prices change: check the ElevenLabs docs before a new project.

## Writing the narration

- One sentence per scene, 6 to 14 words: the retime gives the scene the voice's length, so a long sentence makes a slow scene.
- The text is what the caption shows. The voice receives the same text with `voice.pronounce` applied token by token, punctuation kept attached (`"7,"` becomes `"seven,"`). A replacement may change spelling, never the word count: the script refuses it, because the caption maps word N to word N.
- Use `pronounce` for the product name, acronyms, plan names and digits the voice reads wrong (`{"7": "sete", "PRO": "Pró"}`).
- Avoid a colon before a short word: once the voice dropped the word after the colon; a comma kept it.
- No claim in the voice that is not in the copy: the same check against the sources of truth applies ([social-post](social-post.md), [release-notes](release-notes.md)).

## How the timing is made

The whole narration goes in ONE call to `text-to-speech/{voice}/with-timestamps`, so the intonation runs from sentence to sentence. The API returns the audio and the start and end of every character. For each shown word the script keeps the character range of its core (without the punctuation around it) in the text sent; the word's `start` is the first character's start and its `end` the last character's end. The alignment must spell exactly the text sent, or the run fails.

`narracao.json`: `{voice_id, voice_name, model_id, language_code, characters, voiceText, audio, speechEnd, scenes: [{id, text, words: [{text, spoken, start, end}]}]}`. The compositor retimes the scenes from it ([storyboard](storyboard.md)).

## Check the speech before the video

Listen to `narracao.mp3` whole. When a local transcriber is available (for example `faster-whisper`), transcribe it and diff against `voiceText`: a dropped or swapped word is cheaper to catch here than in the published Reel. Do not send the audio to an external service to check it.

## Music

- `music` asks for `ceil(leadIn + speechEnd + tail + 1)` seconds, so it needs `narracao.json` first.
- A loop of an existing track (`ffmpeg ... acrossfade`) costs no credit; a release video can reuse the Reel's track.
- The user's own file works with or without narration. The user owns its license.

## Credits

- Every call appends to `consumo.json`: the kind, model, characters sent and the `character-cost` header; `totalCharacters` and `totalCost` sum the piece.
- Measured once on `eleven_v4`: about 0.4 credits per character (1308 characters cost 523). Do not budget 1:1, and re-measure on a new model.
- Music returns no `character-cost`; check the account's usage page.
- `usage` needs the `user_read` permission; a key scoped to TTS and Music gets 401, and `consumo.json` is the record.
- No real call from tests or from the agent's own checks: run the stub ([setup](setup.md) has the base URL override for tests only).

## The mix (compose.mjs)

| Key | Default | Why |
|---|---|---|
| `voiceLufs` | -16 | the voice's level, set from a measure of the file, so a new voice needs no hand tuning |
| `musicGapDb` | 11 | music this far under the voice |
| `duckThreshold`, `duckRatio`, `duckRelease` | 0.03, 4, 300 | sidechain on the voice: the music dips while it speaks and returns in the breaths. 0.015 and 6 silenced it |
| `fadeIn`, `fadeOut` | 0.6, 1.6 | music edges |
| `lufs`, `truePeak` | -14, -2 | the platforms' loudness; 1 dB under their -1 dBTP for the AAC encoder's overshoot |
| `leadIn`, `sceneLead`, `tail` | 0.15, 0.18, 1.6 | voice entry, cut before each scene's first word, hold after the last |

The chain: voice highpass 70 Hz, measured gain, delay `leadIn`; music measured gain, fades, ducked; `amix`; a limiter at -6 dBFS; then `loudnorm` in two passes (measure, then linear gain to `lufs` with `truePeak`). The limiter before the measure is what lets the linear gain reach -14 LUFS without passing the peak: without it `loudnorm` falls back to dynamic mode and the AAC overshoots. Without narration the music is the foreground: it starts at `voiceLufs`, same fades, limiter and two passes. The script prints the final LUFS and true peak; check them.
