#!/usr/bin/env node
/**
 * The optional AUDIO layer, by the ElevenLabs REST API (no SDK): narration with the time of every word (for the
 * karaoke caption and the WebVTT) and instrumental music. `compose.mjs --narration --music` mixes them.
 *
 *   node audio.mjs voices [--language pt] [--accent brazilian]
 *   node audio.mjs preview --voice <voice_id> --text "A short line." [--model eleven_v4] [--language pt] [--name x]
 *   node audio.mjs narration --storyboard <deck.json> --out <dir> [--force]
 *   node audio.mjs music --storyboard <deck.json> --out <dir> [--force]
 *   node audio.mjs usage
 *
 * Why one call for the whole narration: the intonation runs from one sentence into the next, and the scenes adapt to
 * the speech (the compositor retimes them), not the other way round. Music is asked AFTER the narration, with the
 * length of the retimed piece (`leadIn` + the speech + `tail`).
 *
 * The key comes from `lib/key.mjs` (env, else the owner's file) and only goes into the `xi-api-key` header; errors
 * leave with it replaced by `***`. `ELEVENLABS_BASE_URL` exists only for the tests' local stub.
 *
 * Credits: narration and music are NOT redone when the file exists; `--force` asks again (and spends again). Each call
 * appends to `<out>/audio/consumo.json` the characters sent and the `character-cost` header the API returns.
 *
 * Outputs: `<out>/audio/narracao.mp3`, `narracao.json`, `musica.mp3`, `consumo.json`, `previa/<name>.mp3`.
 */
import { existsSync } from 'node:fs';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { loadConfig, parseArgs } from './lib/config.mjs';
import { readKey, redactor } from './lib/key.mjs';

const API = process.env.ELEVENLABS_BASE_URL || 'https://api.elevenlabs.io';
const { flags, positional } = parseArgs();
const COMMAND = positional[0];
const FORCE = Boolean(flags.force);
const KEY = readKey();
const redact = redactor(KEY);
const loaded = await loadConfig(flags);

async function call(path, { method = 'GET', body, binary = false } = {}) {
  if (!KEY) throw new Error('ElevenLabs key not configured: see references/setup.md (the owner creates ~/.config/keel/elevenlabs.env)');
  const response = await fetch(`${API}${path}`, {
    method,
    headers: { 'xi-api-key': KEY, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) throw new Error(`${method} ${path.split('?')[0]} -> ${response.status}: ${(await response.text()).slice(0, 600)}`);
  const cost = response.headers.get('character-cost');
  return { data: binary ? Buffer.from(await response.arrayBuffer()) : await response.json(), cost: cost == null ? null : Number(cost) };
}

async function loadStoryboard(required = true) {
  if (!flags.storyboard) {
    if (required) throw new Error('missing --storyboard <deck.json>');
    return {};
  }
  return JSON.parse(await readFile(resolve(flags.storyboard), 'utf8'));
}
/** The storyboard's voice and music blocks win over the config's defaults, key by key. */
const voiceOf = (board) => ({ ...(loaded.config.voice ?? {}), ...(board.voice ?? {}) });
const musicOf = (board) => ({ ...(loaded.config.music ?? {}), ...(board.music ?? {}) });
const OUT = flags.out ? resolve(flags.out) : null;
const audioDir = () => {
  if (!OUT) throw new Error('missing --out <dir>');
  return join(OUT, 'audio');
};

async function logUsage(entry) {
  const file = join(audioDir(), 'consumo.json');
  await mkdir(audioDir(), { recursive: true });
  const usage = existsSync(file) ? JSON.parse(await readFile(file, 'utf8')) : { entries: [] };
  usage.entries.push({ at: new Date().toISOString(), ...entry });
  usage.totalCharacters = usage.entries.reduce((sum, e) => sum + (e.characters ?? 0), 0);
  usage.totalCost = usage.entries.reduce((sum, e) => sum + (e.cost ?? 0), 0);
  await writeFile(file, `${JSON.stringify(usage, null, 2)}\n`);
  console.log(`  ${entry.kind}: ${entry.characters ?? 0} characters${entry.cost != null ? ` (character-cost ${entry.cost})` : ''}; piece total ${usage.totalCharacters} characters, cost ${usage.totalCost}`);
}

/** Word by word, punctuation kept attached: "7," becomes "seven,". The word count never changes. */
function toVoice(text, pronounce = {}) {
  return text
    .split(' ')
    .map((token) => {
      const match = token.match(/^([\p{L}\p{N}%]+)(.*)$/u);
      return match && pronounce[match[1]] ? pronounce[match[1]] + match[2] : token;
    })
    .join(' ');
}

async function tts(voice, text) {
  const body = { text, model_id: voice.model_id, voice_settings: voice.settings };
  if (voice.language_code) body.language_code = voice.language_code;
  if (voice.seed != null) body.seed = voice.seed;
  return call(`/v1/text-to-speech/${encodeURIComponent(voice.voice_id)}/with-timestamps?output_format=mp3_44100_128`, { method: 'POST', body });
}

async function voices() {
  const language = flags.language ?? 'pt';
  const accent = flags.accent ?? null;
  const mine = await call('/v2/voices?page_size=100&include_total_count=true');
  console.log(`# my voices (${mine.data.total_count ?? mine.data.voices.length})`);
  for (const v of mine.data.voices) {
    const langs = (v.verified_languages ?? []).filter((l) => l.language === language).map((l) => l.accent ?? l.locale).join(',');
    console.log([v.voice_id, v.name, v.category, JSON.stringify(v.labels ?? {}), langs ? `${language}:${langs}` : ''].join(' | '));
  }
  const params = new URLSearchParams({ language, page_size: '60', sort: 'usage_character_count_1y' });
  if (accent) params.set('accent', accent);
  const shared = await call(`/v1/shared-voices?${params}`);
  console.log(`# library (${language}${accent ? `, ${accent}` : ''}): ${shared.data.voices.length}`);
  for (const v of shared.data.voices) {
    console.log([v.voice_id, v.name, v.gender, v.age, v.accent, v.locale, v.use_case, v.descriptive, v.category, `free_users_allowed=${v.free_users_allowed}`, `rate=${v.rate ?? ''}`, (v.description ?? '').replace(/\s+/g, ' ').slice(0, 120)].join(' | '));
  }
}

async function preview() {
  const board = await loadStoryboard(false);
  const base = voiceOf(board);
  const voice = { ...base, voice_id: flags.voice ?? base.voice_id, model_id: flags.model ?? base.model_id ?? 'eleven_multilingual_v2' };
  if (!voice.voice_id) throw new Error('missing --voice <voice_id> (or voice.voice_id in the storyboard or config)');
  if (flags.language) voice.language_code = flags.language;
  const text = typeof flags.text === 'string' ? flags.text : `${loaded.config.product || 'This is the product'}.`;
  const { data, cost } = await tts(voice, text);
  const dir = join(audioDir(), 'previa');
  await mkdir(dir, { recursive: true });
  const name = typeof flags.name === 'string' ? flags.name : `${voice.voice_id}-${voice.model_id}`;
  await writeFile(join(dir, `${name}.mp3`), Buffer.from(data.audio_base64, 'base64'));
  const chars = data.alignment?.characters ?? [];
  const end = data.alignment?.character_end_times_seconds?.at(-1) ?? 0;
  console.log(`preview ${name}.mp3: ${end.toFixed(2)} s, alignment ${chars.join('') === text ? 'matches the text' : 'does NOT match the text'}`);
  await logUsage({ kind: 'preview', voice_id: voice.voice_id, model_id: voice.model_id, characters: text.length, cost });
}

async function narration() {
  const board = await loadStoryboard();
  const voice = voiceOf(board);
  if (!voice.voice_id || !voice.model_id) throw new Error('no voice.voice_id and voice.model_id in the storyboard or config');
  const mp3 = join(audioDir(), 'narracao.mp3');
  if (existsSync(mp3) && !FORCE) {
    console.log('narracao.mp3 already exists; --force generates it again (and spends again)');
    return;
  }
  /** The text sent to the voice and, for each caption word, its character range in that text. */
  let voiceText = '';
  const scenes = board.scenes.map((scene) => {
    const text = scene.narration?.text;
    if (!text) throw new Error(`scene without narration.text: ${scene.id}`);
    const shown = text.split(' ');
    const spoken = toVoice(text, voice.pronounce).split(' ');
    if (shown.length !== spoken.length) throw new Error(`the pronounce map changed the word count: ${scene.id}`);
    if (voiceText) voiceText += ' ';
    const words = spoken.map((token, i) => {
      const from = voiceText.length;
      voiceText += token + (i < spoken.length - 1 ? ' ' : '');
      const core = token.match(/^[^\p{L}\p{N}]*(.*?)[^\p{L}\p{N}%]*$/u)[1] || token;
      const start = from + token.indexOf(core);
      return { text: shown[i], spoken: token, chars: [start, start + core.length - 1] };
    });
    return { id: scene.id, text, words };
  });

  const { data, cost } = await tts(voice, voiceText);
  const alignment = data.alignment;
  if (!alignment || alignment.characters.join('') !== voiceText) throw new Error('the returned alignment does not match the text sent');
  const starts = alignment.character_start_times_seconds;
  const ends = alignment.character_end_times_seconds;
  for (const scene of scenes) {
    scene.words = scene.words.map(({ text, spoken, chars }) => ({ text, spoken, start: starts[chars[0]], end: ends[chars[1]] }));
  }
  await mkdir(audioDir(), { recursive: true });
  await writeFile(mp3, Buffer.from(data.audio_base64, 'base64'));
  const meta = {
    voice_id: voice.voice_id,
    voice_name: voice.name ?? null,
    model_id: voice.model_id,
    language_code: voice.language_code ?? null,
    characters: voiceText.length,
    voiceText,
    audio: 'narracao.mp3',
    speechEnd: ends.at(-1),
    scenes,
  };
  await writeFile(join(audioDir(), 'narracao.json'), `${JSON.stringify(meta, null, 2)}\n`);
  console.log(`narration: ${meta.speechEnd.toFixed(2)} s of speech, ${scenes.length} scenes`);
  for (const scene of scenes) console.log(`  ${scene.id}: ${scene.words[0].start.toFixed(2)} to ${scene.words.at(-1).end.toFixed(2)} s`);
  await logUsage({ kind: 'narration', voice_id: voice.voice_id, model_id: voice.model_id, characters: voiceText.length, cost });
}

async function music() {
  const board = await loadStoryboard();
  const spec = musicOf(board);
  if (!spec.prompt) throw new Error('no music.prompt in the storyboard or config');
  const file = join(audioDir(), 'musica.mp3');
  if (existsSync(file) && !FORCE) {
    console.log('musica.mp3 already exists; --force generates it again (and spends again)');
    return;
  }
  const narrationFile = join(audioDir(), 'narracao.json');
  if (!existsSync(narrationFile)) throw new Error('music follows the narration length: run `narration` first');
  const meta = JSON.parse(await readFile(narrationFile, 'utf8'));
  const total = (board.audio?.leadIn ?? 0.15) + meta.speechEnd + (board.audio?.tail ?? 1.6);
  const length = Math.ceil(total + 1) * 1000;
  const body = { prompt: spec.prompt, music_length_ms: length, model_id: spec.model_id ?? 'music_v1', force_instrumental: true };
  const { data, cost } = await call('/v1/music?output_format=mp3_44100_128', { method: 'POST', body, binary: true });
  await writeFile(file, data);
  console.log(`music: ${(length / 1000).toFixed(0)} s asked for a piece of ${total.toFixed(2)} s`);
  await logUsage({ kind: 'music', model_id: body.model_id, seconds: length / 1000, characters: 0, cost });
}

/** Often 401 (`user_read` missing) on a key scoped to TTS and Music: then `consumo.json` is the record. */
async function usage() {
  const { data } = await call('/v1/user/subscription');
  console.log(`plan ${data.tier}: ${data.character_count} of ${data.character_limit} credits used in the cycle`);
}

const commands = { voices, preview, narration, music, usage };
if (!commands[COMMAND]) {
  console.error(`usage: audio.mjs <${Object.keys(commands).join('|')}> [options]`);
  process.exit(2);
}
await commands[COMMAND]().catch((error) => {
  console.error(redact(error.message));
  process.exit(1);
});
