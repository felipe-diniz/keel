#!/usr/bin/env node
/**
 * The COMPOSITOR: turns captured scenes and a storyboard into a vertical Reel (1080x1920, the product in a PHONE) or a
 * landscape video (1920x1080, the product in a BROWSER WINDOW), with scroll, taps, camera moves, screen transitions and
 * captions, plus the stills: covers (1080x1920 and 1080x1350), the carousel, a poster and one frame per scene.
 *
 *   node compose.mjs --storyboard <deck.json> --out <dir>                       silent, kinetic captions
 *   node compose.mjs --storyboard <deck.json> --out <dir> --music <file>        music only (no key needed)
 *   node compose.mjs --storyboard <deck.json> --out <dir> --narration <dir>/audio/narracao.json [--music <file>]
 *   node compose.mjs --validate --storyboard <deck.json> [--out <dir> | --scenes <dir>]
 *   --only all|video|stills|audio     (`audio` redoes the mix over the last silent render, `.composer/video.mp4`)
 *
 * Why a page and not a video editor: the composition is an HTML/CSS page whose state is a pure function of time
 * (`renderAt(t)`). Playwright takes one frame every 1/fps s and ffmpeg encodes them, so the video comes out the same on
 * any machine and never stutters when the CPU is busy.
 *
 * Inputs: the scenes (`<out>/cenas/cenas.json` and its PNGs, from `capture.mjs`); the storyboard (`--storyboard`), whose
 * points and focus are names resolved against `cenas.json`; the narration (`--narration`, from `audio.mjs`): the scenes
 * retime to the SPEECH, not the other way round (scene N starts `audio.sceneLead` before its first word, the last holds
 * `audio.tail` after the speech, and the times inside a scene stretch in the same ratio); the music (`--music`): under
 * the voice with sidechain ducking, or alone when there is no narration, faded in and out, and the mix goes through a
 * two-pass `loudnorm` to `audio.lufs` with the true peak at `audio.truePeak`.
 *
 * Captions are DOM text burned into each frame. Portrait: the kinetic caption (`caption.text`) without narration, the
 * spoken word-by-word caption with it. Landscape: nothing burned under narration; a WebVTT (`legendas.vtt`) for the
 * player's `<track>` instead. Palette, logo and fonts come from `.claude/showcase.json`.
 *
 * Outputs in `--out`: reel.mp4 (or `storyboard.output`), capa-1080x1920.png, capa-1080x1350.png, carrossel-NN.png,
 * frames/NN-<scene>.png; landscape: video.mp4 (or `output`), poster.jpg, legendas.vtt (with narration), frames/.
 */
import { existsSync } from 'node:fs';
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { brandFiles, escapeHtml, loadConfig, paletteOf, parseArgs, rel } from './lib/config.mjs';
import { fontFaces } from './lib/art-html.mjs';
import { loadChromium } from './lib/playwright.mjs';
import { measure, run } from './lib/run.mjs';
import { validateStoryboard } from './lib/storyboard.mjs';

const { flags } = parseArgs();
if (typeof flags.storyboard !== 'string') {
  console.error('usage: compose.mjs --storyboard <deck.json> --out <dir> [--narration <narracao.json>] [--music <file>] [--only all|video|stills|audio] [--validate]');
  process.exit(2);
}
const STORYBOARD = resolve(flags.storyboard);
const OUT = typeof flags.out === 'string' ? resolve(flags.out) : null;
const SCENES_DIR = typeof flags.scenes === 'string' ? resolve(flags.scenes) : OUT && join(OUT, 'cenas');
const ONLY = flags.only ?? 'all';
const NARRATION = typeof flags.narration === 'string' ? resolve(flags.narration) : null;
const MUSIC = typeof flags.music === 'string' ? resolve(flags.music) : null;
const WORK = OUT && join(OUT, '.composer');

const storyboard = JSON.parse(await readFile(STORYBOARD, 'utf8'));
const cenasFile = SCENES_DIR && join(SCENES_DIR, 'cenas.json');
const cenas = cenasFile && existsSync(cenasFile) ? JSON.parse(await readFile(cenasFile, 'utf8')) : null;
const problems = validateStoryboard(storyboard, cenas);
if (flags.validate || problems.length) {
  if (problems.length) {
    for (const problem of problems) console.error(`  ${problem}`);
    console.error(`invalid: ${problems.length} problem(s) in ${rel(STORYBOARD)}`);
    process.exit(1);
  }
  const length = storyboard.scenes.reduce((sum, s) => sum + s.duration, 0);
  console.log(`ok: ${storyboard.scenes.length} scenes, format ${storyboard.format ?? 'portrait'}, ${length.toFixed(2)} s before retime${cenas ? ', every shot and point found in cenas.json' : ''}`);
  process.exit(0);
}
const die = (message) => {
  console.error(`FAILED: ${message}`);
  process.exit(1);
};
if (!OUT) die('missing --out <dir>');
if (!cenas) die(`no ${rel(cenasFile)}: run capture.mjs first`);
if (!['all', 'video', 'stills', 'audio'].includes(ONLY)) die(`--only must be all, video, stills or audio`);
if (ONLY === 'audio' && !NARRATION && !MUSIC) die('--only audio needs --narration or --music');

const loaded = await loadConfig(flags);
const narration = NARRATION ? JSON.parse(await readFile(NARRATION, 'utf8')) : null;
/** Audio defaults; the storyboard's `audio` overrides. Times in seconds, levels in LUFS/dB, `duckThreshold` linear. */
const AUDIO_SPEC = {
  leadIn: 0.15,
  sceneLead: 0.18,
  tail: 1.6,
  lufs: -14,
  truePeak: -2,
  voiceLufs: -16,
  musicGapDb: 11,
  duckThreshold: 0.03,
  duckRatio: 4,
  duckRelease: 300,
  fadeIn: 0.6,
  fadeOut: 1.6,
  ...(storyboard.audio ?? {}),
};
if (narration) retimeToSpeech(storyboard, narration);

/**
 * The scenes by the speech: each scene starts at its first word (minus `sceneLead`, so the cut comes a little before
 * the voice), and the times inside it stretch by the ratio of the new duration. The transition (`dur`) and the tap do
 * not stretch: they are the gesture, not the rhythm.
 */
function retimeToSpeech(board, speech) {
  const byId = new Map(speech.scenes.map((s) => [s.id, s]));
  const starts = board.scenes.map((scene, i) => {
    const seg = byId.get(scene.id);
    if (!seg) throw new Error(`the narration has no scene ${scene.id}`);
    return i === 0 ? 0 : AUDIO_SPEC.leadIn + seg.words[0].start - AUDIO_SPEC.sceneLead;
  });
  const lastSeg = byId.get(board.scenes.at(-1).id);
  const end = AUDIO_SPEC.leadIn + lastSeg.words.at(-1).end + AUDIO_SPEC.tail;
  board.scenes.forEach((scene, i) => {
    const duration = (i + 1 < starts.length ? starts[i + 1] : end) - starts[i];
    const k = duration / scene.duration;
    const scale = (v) => (typeof v === 'number' ? v * k : v);
    scene.duration = duration;
    if (scene.frameAt != null) scene.frameAt *= k;
    for (const shot of scene.shots ?? []) {
      shot.at = scale(shot.at ?? 0);
      if (shot.scrollAt) shot.scrollAt = shot.scrollAt.map(scale);
      if (shot.burst) shot.burst.at = shot.burst.at.map(scale);
    }
    for (const tap of scene.taps ?? []) tap.at = scale(tap.at);
    for (const key of scene.camera ?? []) key.at = scale(key.at);
    if (scene.cta?.delay != null) scene.cta.delay *= k;
    const seg = byId.get(scene.id);
    scene.spoken = {
      words: seg.words.map((w) => ({ text: w.text, start: AUDIO_SPEC.leadIn + w.start - starts[i], end: AUDIO_SPEC.leadIn + w.end - starts[i] })),
      sub: scene.narration?.sub ?? null,
    };
  });
}
const LANDSCAPE = storyboard.format === 'landscape';
/**
 * The device, in CSS px of the captured page: the phone of the Reel (the captured viewport, status bar of 44) or, in
 * landscape, the browser window at the size of the capture with an address bar of 40.
 */
const DEVICE = LANDSCAPE
  ? { W: 1920, H: 1080, VW: cenas.viewport.width, VH: cenas.viewport.height, STATUS: 40 }
  : { W: 1080, H: 1920, VW: cenas.viewport?.width ?? 390, VH: cenas.viewport?.height ?? 844, STATUS: 44 };
const SCREEN_H = DEVICE.VH + DEVICE.STATUS;
const theme = storyboard.theme ?? loaded.config.theme.default ?? 'dark';
const palette = paletteOf(loaded.config, theme);
const brand = brandFiles(loaded, theme);
const fileUrl = (path) => (path ? pathToFileURL(path).href : null);

/** Image and font paths become file URLs: the composition page opens by `file://`, next to the scenes. */
const assets = {
  logo: fileUrl(brand.logo),
  faces: fontFaces({ display: fileUrl(brand.display), body: fileUrl(brand.body) }),
  base: fileUrl(SCENES_DIR) + '/',
  product: escapeHtml(loaded.config.product ?? ''),
};

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
${assets.faces}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:${palette.bg};overflow:hidden}
#stage{position:relative;width:${DEVICE.W}px;height:var(--h);overflow:hidden;background:${palette.bg};font-family:'SCBody',system-ui,sans-serif;color:${palette.text}}
.glow{position:absolute;border-radius:50%;filter:blur(90px);pointer-events:none}
#g1{width:900px;height:900px;background:radial-gradient(circle,color-mix(in srgb,${palette.accent} 22%,transparent),transparent 65%)}
#g2{width:760px;height:760px;background:radial-gradient(circle,color-mix(in srgb,${palette.glow} 20%,transparent),transparent 65%)}
#vignette{position:absolute;inset:0;background:radial-gradient(120% 80% at 50% 45%,transparent 55%,#0008 100%)}
#phone{position:absolute;left:0;top:0;transform-origin:0 0;padding:var(--bezel);border-radius:${LANDSCAPE ? '14px' : 'calc(var(--sw) * 0.13)'};background:linear-gradient(160deg,#2a313b,#0b0f14 40%,#161b22);box-shadow:0 0 0 2px #ffffff22,0 60px 120px #000a,0 0 0 1px #000 inset}
#screen{position:relative;width:var(--sw);height:calc(var(--sw) * ${SCREEN_H} / ${DEVICE.VW});border-radius:${LANDSCAPE ? '14px' : 'calc(var(--sw) * 0.105)'};overflow:hidden;background:${palette.bg}}
#vp{position:absolute;left:0;top:0;width:${DEVICE.VW}px;height:${SCREEN_H}px;transform-origin:0 0;transform:scale(var(--s))}
#status{position:absolute;left:0;top:0;width:${DEVICE.VW}px;height:${DEVICE.STATUS}px;z-index:5;display:flex;align-items:center;justify-content:space-between;padding:0 30px 0 34px;font:600 15px 'SCBody',system-ui,sans-serif;color:${palette.text};background:${palette.bg}}
#island{position:absolute;left:50%;top:11px;width:112px;height:32px;margin-left:-56px;border-radius:20px;background:#000;z-index:6}
.icons{display:flex;gap:6px;align-items:center}.bars{display:flex;gap:2px;align-items:flex-end}.bars i{display:block;width:3px;background:${palette.text};border-radius:1px}
.batt{width:25px;height:12px;border:1.5px solid ${palette.text};border-radius:3px;padding:1.5px;opacity:.95}.batt b{display:block;height:100%;width:78%;background:${palette.text};border-radius:1px}
#content{position:absolute;left:0;top:${DEVICE.STATUS}px;width:${DEVICE.VW}px;height:${DEVICE.VH}px;overflow:hidden}
#status.browser{justify-content:flex-start;gap:18px;padding:0 18px;background:${palette.chrome};border-bottom:1px solid #ffffff1a}
#status .lights{display:flex;gap:8px}#status .lights i{display:block;width:12px;height:12px;border-radius:50%;background:#ffffff2e}
#status .url{flex:1;max-width:620px;margin:0 auto;height:26px;border-radius:7px;background:${palette.field};border:1px solid #ffffff14;display:flex;align-items:center;justify-content:center;font:500 13px 'SCBody',system-ui,sans-serif;color:${palette.muted};letter-spacing:.01em}
.layer{position:absolute;inset:0;overflow:hidden;display:none;background:${palette.bg}}
.layer img.page{position:absolute;left:0;top:0;width:${DEVICE.VW}px;display:block}
.layer img.bar{position:absolute;left:0;bottom:0;width:${DEVICE.VW}px;display:block}
.burst{position:absolute;display:none}
#tap{position:absolute;left:0;top:0;width:52px;height:52px;margin:-26px 0 0 -26px;border-radius:50%;z-index:8;pointer-events:none;opacity:0}
#tap .dot{position:absolute;inset:8px;border-radius:50%;background:#ffffffb0;box-shadow:0 0 0 2px #ffffff55}
#tap .ring{position:absolute;inset:0;border-radius:50%;border:3px solid #fff}
#scrim{position:absolute;left:0;right:0;top:0;display:none;z-index:9;pointer-events:none;background:linear-gradient(to bottom,${palette.bg} 0%,${palette.bg} calc(100% - 110px),${palette.bg}00 100%)}
#caption{position:absolute;left:60px;right:60px;top:var(--capTop);display:flex;flex-direction:column;align-items:center;text-align:center;gap:22px;z-index:10}
#words{display:flex;flex-wrap:wrap;justify-content:center;column-gap:.26em;row-gap:.06em;font:800 var(--capSize)/1.04 'SCDisplay',sans-serif;letter-spacing:-.025em;text-shadow:0 6px 30px #000a}
.w{display:inline-block;position:relative;will-change:transform}
.w .hl{position:absolute;left:-.12em;right:-.12em;top:.06em;bottom:.02em;background:${palette.accent};border-radius:10px;transform-origin:0 50%;z-index:-1}
.w.acc{color:${palette.onAccent};text-shadow:none}
#sub{font:500 var(--subSize)/1.3 'SCBody',system-ui,sans-serif;color:${palette.muted};text-shadow:0 4px 20px #000c}
#words.spoken{font-size:var(--spokenSize);line-height:1.12;row-gap:.1em;text-shadow:0 3px 0 #000a,0 6px 26px #000c}
#words.spoken .w .hl{top:-.02em;bottom:-.06em;left:-.16em;right:-.16em;border-radius:12px;transform:none}
#words.spoken .w.on{color:${palette.onAccent};text-shadow:none}
#cta .k{display:inline-block;transition:none}
#cta{position:absolute;left:70px;right:70px;top:var(--ctaTop);display:none;flex-direction:column;align-items:center;text-align:center;gap:26px;z-index:11}
#cta img{height:var(--logoH)}
#cta .mark{font:800 calc(var(--logoH) * .9)/1 'SCDisplay',sans-serif;letter-spacing:-.02em}
#cta .title{font:800 var(--ctaSize)/1.02 'SCDisplay',system-ui,sans-serif;letter-spacing:-.03em}
#cta .title em{font-style:normal;color:${palette.accent}}
#cta .line{font:500 var(--ctaLine)/1.35 'SCBody',system-ui,sans-serif;color:${palette.muted}}
#cta .pill{margin-top:10px;font:700 var(--ctaLine)/1 'SCBody',system-ui,sans-serif;color:${palette.onAccent};background:${palette.accent};border-radius:999px;padding:22px 40px}
#cta .foot{font:600 calc(var(--ctaLine) * .9)/1 'SCBody',system-ui,sans-serif;color:${palette.text};opacity:.85;letter-spacing:.02em}
#slide{position:absolute;left:72px;right:72px;top:72px;display:none;flex-direction:column;gap:18px;z-index:12}
#slide .eyebrow{font:700 26px/1 'SCBody',system-ui,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:${palette.accent}}
#slide .title{font:800 64px/1.04 'SCDisplay',system-ui,sans-serif;letter-spacing:-.025em}
#slide .sub{font:500 30px/1.3 'SCBody',system-ui,sans-serif;color:${palette.muted}}
#slide .count{position:absolute;right:0;top:0;font:600 24px/1 'SCBody',system-ui,sans-serif;color:${palette.tertiary}}
#pre{position:absolute;left:-99999px;top:0;width:1px;height:1px;overflow:hidden}
</style></head><body><div id="stage">
<div id="g1" class="glow"></div><div id="g2" class="glow"></div><div id="vignette"></div>
<div id="phone"><div id="screen"><div id="vp">
${
   LANDSCAPE
     ? ' <div id="status" class="browser"><span class="lights"><i></i><i></i><i></i></span><span class="url" id="url"></span></div>'
     : ' <div id="status"><span>9:41</span><span class="icons"><span class="bars"><i style="height:5px"></i><i style="height:7px"></i><i style="height:9px"></i><i style="height:11px"></i></span><span class="batt"><b></b></span></span></div>\n <div id="island"></div>'
 }
 <div id="content"></div>
 <div id="tap"><div class="ring"></div><div class="dot"></div></div>
</div></div></div>
<div id="scrim"></div><div id="caption"><div id="words"></div><div id="sub"></div></div>
<div id="cta"></div>
<div id="slide"></div>
<div id="pre"></div>
</div>
<script>
const SB = ${JSON.stringify(storyboard)};
const CENAS = ${JSON.stringify(cenas)};
const BASE = ${JSON.stringify(assets.base)};
const LOGO = ${JSON.stringify(assets.logo)};
const PRODUCT = ${JSON.stringify(assets.product)};
const STATUS = ${DEVICE.STATUS}, VW = ${DEVICE.VW}, VH = ${DEVICE.VH}, SCREEN_H = ${SCREEN_H}, STAGE_W = ${DEVICE.W}, LANDSCAPE = ${LANDSCAPE};
/**
 * The Reel with speech: the caption and the phone are ONE block, centred vertically inside the Reel's safe area ('safe':
 * under the Instagram header, above the post caption and the buttons). The caption box ('capBox') sits right above the
 * phone with the text at its bottom, so the phone does not move between scenes; a caption that does not fit shrinks its
 * font. 'cy' (the phone centre, where the camera anchors the focus) and the caption top come from there.
 */
function centered(layout) {
  const phoneH = (layout.sw * SCREEN_H) / VW + 2 * layout.bezel;
  const top = layout.safe[0] + (layout.safe[1] - layout.safe[0] - (layout.capBox + layout.capGap + phoneH)) / 2;
  return { ...layout, spokenTop: top, cy: top + layout.capBox + layout.capGap + phoneH / 2 };
}
const LAYOUTS = {
  1920: centered({ sw: 510, bezel: 12, cx: 540, safe: [150, 1600], capBox: 200, capGap: 28, capTop: 150, capSize: 84, subSize: 34, ctaTop: 230, ctaSize: 108, ctaLine: 38, logoH: 54, spokenSize: 66 }),
  1350: { sw: 430, bezel: 11, cx: 540, cy: 860, capTop: 70, capSize: 64, subSize: 28, ctaTop: 150, ctaSize: 84, ctaLine: 32, logoH: 44, spokenTop: 90, spokenSize: 54 },
  /** Landscape: the browser window centred, 40 px of air above and below; the CTA takes the middle of the frame. */
  1080: { sw: 1680, bezel: 0, cx: 960, cy: 540, capTop: 60, capSize: 64, subSize: 28, ctaTop: 300, ctaSize: 92, ctaLine: 34, logoH: 56, spokenTop: 60, spokenSize: 48 },
};
let L = LAYOUTS[1920];
const $ = (id) => document.getElementById(id);
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const lerp = (a, b, p) => a + (b - a) * p;
const ease = { inOut: (p) => (p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2), out: (p) => 1 - Math.pow(1 - p, 3), back: (p) => { const c = 1.6; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); }, linear: (p) => p };

// ── scenes and layers ─────────────────────────────────────────────────────────────
let cursor = 0;
for (const scene of SB.scenes) { scene.start = cursor; cursor += scene.duration; }
const TOTAL = cursor;
const layers = new Map();
const preload = [];
function img(src, cls) { const el = new Image(); el.src = BASE + src; if (cls) el.className = cls; preload.push(el.decode().catch(() => new Promise((ok, fail) => { if (el.complete && el.naturalWidth) ok(); else { el.onload = ok; el.onerror = () => fail(new Error('image: ' + src)); } }))); return el; }
function layerOf(name) {
  if (layers.has(name)) return layers.get(name);
  const meta = CENAS.scenes[name];
  if (!meta) throw new Error('scene not captured: ' + name);
  const el = document.createElement('div'); el.className = 'layer';
  const page = img(meta.file, 'page'); el.appendChild(page);
  let bar = null; if (meta.bar) { bar = img(meta.bar.file, 'bar'); el.appendChild(bar); }
  $('content').appendChild(el);
  const entry = { el, page, meta, bursts: new Map() };
  layers.set(name, entry); return entry;
}
function burstOf(layer, name) {
  if (layer.bursts.has(name)) return layer.bursts.get(name);
  const meta = CENAS.scenes[name];
  const box = document.createElement('div'); box.className = 'burst';
  box.style.cssText += 'left:' + meta.clip.x + 'px;top:' + meta.clip.y + 'px;width:' + meta.clip.w + 'px;height:' + meta.clip.h + 'px';
  const frames = [];
  for (let i = 0; i < meta.count; i++) { const f = img(meta.dir + '/' + String(i).padStart(3, '0') + '.png'); f.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;display:none'; box.appendChild(f); frames.push(f); }
  layer.el.appendChild(box);
  const entry = { box, frames, meta }; layer.bursts.set(name, entry); return entry;
}
for (const scene of [...SB.scenes, ...(SB.carousel ?? [])]) for (const s of scene.shots ?? []) { const layer = layerOf(s.shot); if (s.burst) burstOf(layer, s.burst.name); }

// ── scroll, points and camera ────────────────────────────────────────────────────
function maxScroll(meta) { return Math.max(0, meta.height - VH); }
/** A full-page capture scrolls inside the screen: taller than the viewport, or with its fixed bar shot apart. */
function tall(meta) { return Boolean(meta.bar) || meta.height > VH; }
function resolveScroll(meta, value) {
  if (value == null) return 0;
  if (typeof value === 'number') return clamp(value, 0, maxScroll(meta));
  const rect = meta.points[value.point]; if (!rect) throw new Error('point not captured: ' + value.point);
  return clamp(rect.y - (value.top ?? 80), 0, maxScroll(meta));
}
function scrollAt(shot, u) {
  const meta = CENAS.scenes[shot.shot];
  if (!tall(meta)) return 0;
  const [a, b] = Array.isArray(shot.scroll) ? shot.scroll : [shot.scroll, shot.scroll];
  const from = resolveScroll(meta, a), to = resolveScroll(meta, b);
  const [t0, t1] = shot.scrollAt ?? [0, 0.001];
  return lerp(from, to, ease[shot.scrollEase ?? 'inOut'](clamp((u - t0) / Math.max(.001, t1 - t0))));
}
/** A captured point in CSS px of the SCREEN (status bar included), at the layer's current scroll. */
function screenPoint(shotName, pointName, scroll) {
  const meta = CENAS.scenes[shotName]; const rect = meta.points[pointName];
  if (!rect) throw new Error('point not captured: ' + shotName + '.' + pointName);
  const offset = tall(meta) ? scroll : meta.scrollY;
  return { x: rect.x + rect.w / 2, y: rect.y + rect.h / 2 - offset + STATUS };
}
function activeShots(scene, u) {
  const shots = scene.shots ?? []; let index = -1;
  shots.forEach((s, i) => { if ((s.at ?? 0) <= u) index = i; });
  return { index, shots };
}
function cameraAt(scene, u) {
  const keys = scene.camera ?? [{ at: 0 }];
  const resolveKey = (k) => {
    let fx = VW / 2, fy = SCREEN_H / 2;
    if (k.focus) {
      const { shots } = activeShots(scene, k.at);
      const shot = shots.filter((s) => (s.at ?? 0) <= k.at).pop() ?? shots[0];
      const p = screenPoint(k.focus.shot ?? shot.shot, k.focus.point, scrollAt(shot, k.at - (shot.at ?? 0)));
      fx = p.x; fy = p.y;
    }
    if (k.fx != null) fx = k.fx; if (k.fy != null) fy = k.fy;
    return { s: k.s ?? 1, fx, fy, ay: k.ay ?? 0, rot: k.rot ?? 0 };
  };
  if (u <= keys[0].at) return resolveKey(keys[0]);
  for (let i = 0; i < keys.length - 1; i++) {
    const a = keys[i], b = keys[i + 1];
    if (u <= b.at) { const p = ease[b.ease ?? 'inOut'](clamp((u - a.at) / Math.max(.001, b.at - a.at))); const A = resolveKey(a), B = resolveKey(b); return { s: lerp(A.s, B.s, p), fx: lerp(A.fx, B.fx, p), fy: lerp(A.fy, B.fy, p), ay: lerp(A.ay, B.ay, p), rot: lerp(A.rot, B.rot, p) }; }
  }
  return resolveKey(keys[keys.length - 1]);
}

// ── drawing ─────────────────────────────────────────────────────────────────────
function setLayout(height) {
  L = LAYOUTS[height];
  const st = $('stage').style;
  st.setProperty('--h', height + 'px'); st.setProperty('--sw', L.sw + 'px'); st.setProperty('--s', L.sw / VW); st.setProperty('--bezel', L.bezel + 'px');
  for (const k of ['capTop', 'capSize', 'subSize', 'ctaTop', 'ctaSize', 'ctaLine', 'logoH', 'spokenSize']) st.setProperty('--' + k, L[k] + 'px');
  document.body.style.width = STAGE_W + 'px'; document.body.style.height = height + 'px';
}
function drawPhone(cam) {
  const S = L.sw / VW;
  const lx = L.bezel + cam.fx * S, ly = L.bezel + cam.fy * S;
  const ax = L.cx, ay = L.cy + cam.ay;
  $('phone').style.transform = 'translate(' + (ax - lx * cam.s) + 'px,' + (ay - ly * cam.s) + 'px) scale(' + cam.s + ')' + (cam.rot ? ' rotate(' + cam.rot + 'deg)' : '');
}
function drawScreen(scene, u) {
  for (const layer of layers.values()) { layer.el.style.display = 'none'; layer.el.style.transform = ''; layer.el.style.opacity = '1'; layer.el.style.filter = ''; }
  const { index, shots } = activeShots(scene, u);
  if (index < 0) return;
  /** The outgoing screen: the previous one of the scene or, for the first, the last of the previous scene, frozen where it ended. */
  const prevScene = SB.scenes[SB.scenes.indexOf(scene) - 1];
  const outgoing = index > 0 ? { shot: shots[index - 1], local: u - (shots[index - 1].at ?? 0) }
    : prevScene && prevScene.shots?.length ? { shot: prevScene.shots[prevScene.shots.length - 1], local: prevScene.duration - (prevScene.shots[prevScene.shots.length - 1].at ?? 0) } : null;
  const show = (shot, local, z, transform, opacity, dim) => {
    const layer = layers.get(shot.shot);
    layer.el.style.display = 'block'; layer.el.style.zIndex = String(z);
    layer.el.style.transform = transform ?? ''; layer.el.style.opacity = String(opacity ?? 1);
    layer.el.style.filter = dim ? 'brightness(' + (1 - dim) + ')' : '';
    if (tall(layer.meta)) layer.page.style.transform = 'translateY(' + -scrollAt(shot, local) + 'px)';
    for (const [name, burst] of layer.bursts) {
      const active = shot.burst && shot.burst.name === name;
      burst.box.style.display = active && local < shot.burst.at[1] ? 'block' : 'none';
      if (!active) continue;
      const p = clamp((local - shot.burst.at[0]) / (shot.burst.at[1] - shot.burst.at[0]));
      const k = Math.min(burst.frames.length - 1, Math.floor(ease[shot.burst.ease ?? 'linear'](p) * burst.frames.length));
      burst.frames.forEach((f, j) => (f.style.display = j === k ? 'block' : 'none'));
    }
  };
  const current = shots[index]; const local = u - (current.at ?? 0); const d = current.dur ?? .42;
  if (LANDSCAPE) $('url').textContent = current.url ?? '';
  const p = ease.out(clamp(local / d));
  const sameLayer = outgoing && outgoing.shot.shot === current.shot;
  if (outgoing && !sameLayer && p < 1 && current.in && current.in !== 'cut') {
    if (current.in === 'push') { show(outgoing.shot, outgoing.local, 1, 'translateX(' + (-120 * p) + 'px)', 1, .35 * p); show(current, local, 2, 'translateX(' + (VW * (1 - p)) + 'px)'); }
    else if (current.in === 'rise') { show(outgoing.shot, outgoing.local, 1, '', 1, .3 * p); show(current, local, 2, 'translateY(' + (VH * (1 - p)) + 'px)'); }
    else { show(outgoing.shot, outgoing.local, 1); show(current, local, 2, '', p); }
  } else show(current, local, 2);
}
function drawTap(scene, u) {
  const tap = $('tap'); tap.style.opacity = '0';
  for (const t of scene.taps ?? []) {
    const local = u - t.at; if (local < 0 || local > .62) continue;
    const { shots } = activeShots(scene, t.at); const shot = shots.filter((s) => (s.at ?? 0) <= t.at).pop();
    const p = screenPoint(t.shot ?? shot.shot, t.point, scrollAt(shot, t.at - (shot.at ?? 0)));
    tap.style.left = p.x + 'px'; tap.style.top = p.y + 'px';
    const press = clamp(local / .14), release = clamp((local - .14) / .48);
    tap.style.opacity = String(local < .14 ? press : 1 - release);
    tap.querySelector('.dot').style.transform = 'scale(' + (local < .14 ? lerp(.6, 1, press) : lerp(1, .8, release)) + ')';
    const ring = tap.querySelector('.ring'); ring.style.transform = 'scale(' + lerp(.9, 2.1, ease.out(release)) + ')'; ring.style.opacity = String(local < .14 ? .9 : .9 * (1 - release));
  }
}
let captionKey = null;
/**
 * The spoken caption, word by word: each word comes in when it starts being said and stays; the one being said gets the
 * accent background until the next starts. Every word's place is reserved from the start of the scene (the ones still
 * to come are transparent), so the line does not jump when a word comes in.
 */
function drawSpoken(scene, u) {
  const spoken = scene.spoken; const words = $('words'); const sub = $('sub');
  $('caption').style.display = 'flex'; $('scrim').style.display = 'block';
  const caption = $('caption');
  caption.style.top = L.spokenTop + 'px';
  if (captionKey !== scene.id) {
    captionKey = scene.id; words.innerHTML = ''; words.className = 'spoken'; words.style.fontSize = '';
    for (const w of spoken.words) {
      const span = document.createElement('span'); span.className = 'w'; span.textContent = w.text;
      const hl = document.createElement('span'); hl.className = 'hl'; span.appendChild(hl);
      words.appendChild(span);
    }
    sub.textContent = spoken.sub ?? '';
    if (L.capBox) {
      caption.style.height = 'auto';
      for (let size = L.spokenSize; size > 40 && caption.offsetHeight > L.capBox; size -= 2) words.style.fontSize = size - 2 + 'px';
      caption.style.height = L.capBox + 'px'; caption.style.justifyContent = 'flex-end';
    }
  }
  /** With the box, the scrim is solid down to the caption's foot and fades in the gap to the phone: zoomed in, the phone passes under it. */
  $('scrim').style.height = (L.capBox ? L.spokenTop + L.capBox + 100 : caption.offsetTop + caption.offsetHeight + 110) + 'px';
  const out = clamp((u - (scene.duration - .25)) / .25);
  const list = spoken.words;
  [...words.children].forEach((el, i) => {
    const w = list[i]; const next = list[i + 1];
    const p = clamp((u - (w.start - .05)) / .16);
    const on = u >= w.start - .05 && u < (next ? next.start - .05 : w.end + .3);
    el.style.opacity = String(clamp(p * 1.6) * (1 - out));
    el.style.transform = 'translateY(' + ((1 - ease.out(p)) * 16 - out * 30) + 'px) scale(' + lerp(.88, 1, ease.back(p)) + ')';
    el.style.filter = '';
    el.classList.toggle('on', on);
    el.querySelector('.hl').style.opacity = on ? '1' : '0';
  });
  const ps = clamp((u - .2) / .4);
  sub.style.opacity = String(ps * (1 - out)); sub.style.transform = 'translateY(' + ((1 - ease.out(ps)) * 24) + 'px)';
}
function drawCaption(scene, u) {
  if (scene.spoken && !scene.cta && LANDSCAPE) { $('caption').style.display = 'none'; $('scrim').style.display = 'none'; return; }
  if (scene.spoken && !scene.cta) return drawSpoken(scene, u);
  const cap = scene.caption; const words = $('words'); const sub = $('sub');
  $('caption').style.top = ''; $('caption').style.height = ''; $('caption').style.justifyContent = ''; words.className = '';
  $('caption').style.display = cap ? 'flex' : 'none';
  $('scrim').style.display = cap ? 'block' : 'none';
  if (!cap) return;
  if (captionKey !== scene.id) {
    captionKey = scene.id; words.innerHTML = '';
    const accent = new Set((cap.accent ?? []).flatMap((a) => a.split(' ')));
    for (const word of cap.text.split(' ')) {
      const span = document.createElement('span'); span.className = 'w' + (accent.has(word) ? ' acc' : ''); span.textContent = word;
      if (accent.has(word)) { const hl = document.createElement('span'); hl.className = 'hl'; span.appendChild(hl); }
      words.appendChild(span);
    }
    sub.textContent = cap.sub ?? '';
    words.style.fontSize = cap.size ? cap.size + 'px' : '';
  }
  $('scrim').style.height = '';
  /** The scrim behind the caption: the zoomed phone passes under it instead of crossing the text. */
  $('scrim').style.height = ($('caption').offsetTop + $('caption').offsetHeight + 110) + 'px';
  const out = clamp((u - (scene.duration - .3)) / .3);
  [...words.children].forEach((w, i) => {
    const p = clamp((u - (cap.delay ?? .1) - i * .075) / .45);
    const e = ease.back(p);
    w.style.opacity = String(clamp(p * 2.2) * (1 - out));
    w.style.transform = 'translateY(' + ((1 - e) * 70 - out * 40) + 'px) scale(' + lerp(.86, 1, clamp(e, 0, 1.2)) + ')';
    w.style.filter = 'blur(' + ((1 - clamp(p * 1.6)) * 12) + 'px)';
    const hl = w.querySelector('.hl'); if (hl) hl.style.transform = 'scaleX(' + ease.out(clamp((u - (cap.delay ?? .1) - i * .075 - .25) / .35)) + ')';
  });
  const ps = clamp((u - (cap.delay ?? .1) - words.children.length * .075 - .15) / .4);
  sub.style.opacity = String(ps * (1 - out)); sub.style.transform = 'translateY(' + ((1 - ease.out(ps)) * 24) + 'px)';
}
function drawCta(scene, u) {
  const cta = $('cta'); const c = scene.cta;
  cta.style.display = c ? 'flex' : 'none'; if (!c) return;
  if (cta.dataset.key !== scene.id) {
    cta.dataset.key = scene.id;
    cta.innerHTML = (LOGO ? '<img class="brand" src="' + LOGO + '" alt="">' : PRODUCT ? '<div class="brand mark">' + PRODUCT + '</div>' : '') + '<div class="title">' + c.title + '</div>' + (c.lines ?? []).map((l) => '<div class="line">' + l + '</div>').join('') + (c.pill ? '<div class="pill">' + c.pill + '</div>' : '') + (c.footer ? '<div class="foot">' + c.footer + '</div>' : '');
    if (scene.spoken) karaokeCta(cta, scene.spoken.words);
  }
  [...cta.children].forEach((el, i) => {
    const start = scene.spoken ? (el.dataset.at != null ? Number(el.dataset.at) - .12 : (c.delay ?? .35) + i * .12) : (c.delay ?? .35) + i * .12;
    const p = clamp((u - start) / .5);
    el.style.opacity = String(clamp(p * 1.8)); el.style.transform = 'translateY(' + ((1 - ease.back(p)) * 50) + 'px)';
  });
  if (!scene.spoken) return;
  /** The CTA is its own caption: a said word lights up (from dim to full) and the one being said rises a little (no scale, which would eat the space between words). */
  for (const k of cta.querySelectorAll('.k')) {
    const s = Number(k.dataset.s), n = Number(k.dataset.n);
    const lit = clamp((u - (s - .05)) / .14);
    const on = u >= s - .05 && u < n;
    k.style.opacity = String(lerp(.28, 1, lit));
    k.style.transform = on ? 'translateY(-.07em)' : '';
  }
}
/**
 * Matches the words of the CTA texts with the spoken words, in order: each CTA word becomes a span.k with its start and
 * the next one's, and each CTA line comes in when its first word is said. "7" matches "7" because the caption keeps the
 * shown text, not the one sent to the voice.
 */
function karaokeCta(cta, words) {
  const norm = (t) => t.toLowerCase().normalize('NFD').replace(/[^\\p{L}\\p{N}%]/gu, '');
  let cursor = 0;
  const walk = (node) => {
    for (const child of [...node.childNodes]) {
      if (child.nodeType === 1) { walk(child); continue; }
      if (child.nodeType !== 3 || !child.nodeValue.trim()) continue;
      const frag = document.createDocumentFragment();
      for (const part of child.nodeValue.split(/(\\s+)/)) {
        if (!part.trim()) { frag.appendChild(document.createTextNode(part)); continue; }
        let hit = -1;
        for (let j = cursor; j < words.length; j++) if (norm(words[j].text) === norm(part)) { hit = j; break; }
        if (hit < 0) { frag.appendChild(document.createTextNode(part)); continue; }
        cursor = hit + 1;
        const k = document.createElement('span'); k.className = 'k'; k.textContent = part;
        k.dataset.s = String(words[hit].start); k.dataset.n = String(words[hit + 1] ? words[hit + 1].start - .05 : words[hit].end + .3);
        frag.appendChild(k);
      }
      child.replaceWith(frag);
    }
  };
  for (const el of cta.children) {
    if (el.classList.contains('brand')) continue;
    walk(el);
    const first = el.querySelector('.k');
    if (first) el.dataset.at = first.dataset.s;
  }
  const lastEnd = words[words.length - 1].end;
  for (const el of cta.children) if (el.dataset.at == null && !el.classList.contains('brand')) el.dataset.at = String(lastEnd + .1);
  const img = cta.querySelector('.brand'); if (img) img.dataset.at = String(Math.max(0, words[0].start - .25));
}
function drawBackground(t) {
  $('g1').style.left = (-200 + Math.sin(t * .35) * 120) + 'px'; $('g1').style.top = (L.cy - 900 + Math.cos(t * .27) * 140) + 'px';
  $('g2').style.left = (560 + Math.cos(t * .3) * 110) + 'px'; $('g2').style.top = (L.cy - 120 + Math.sin(t * .22) * 160) + 'px';
}
function sceneAt(t) { return SB.scenes.find((s) => t < s.start + s.duration) ?? SB.scenes[SB.scenes.length - 1]; }
window.renderAt = (t) => {
  const scene = sceneAt(t); const u = t - scene.start;
  $('slide').style.display = 'none';
  $('phone').style.display = scene.device === false ? 'none' : 'block';
  drawBackground(t); drawPhone(cameraAt(scene, u)); drawScreen(scene, u); drawTap(scene, u); drawCaption(scene, u); drawCta(scene, u);
};
/** A static carousel slide (1080x1350): the text on top, the phone with the asked screen below. */
window.renderSlide = (index) => {
  const slide = SB.carousel[index];
  const scene = { id: 'slide-' + index, duration: 10, shots: slide.shots, camera: slide.camera, taps: [] };
  $('caption').style.display = 'none'; $('scrim').style.display = 'none'; $('cta').style.display = 'none';
  drawBackground(index * 2.3); drawPhone(cameraAt(scene, 5)); drawScreen(scene, 5); $('tap').style.opacity = '0';
  const el = $('slide'); el.style.display = 'flex';
  el.innerHTML = '<div class="count">' + (index + 1) + '/' + SB.carousel.length + '</div>' + (slide.eyebrow ? '<div class="eyebrow">' + slide.eyebrow + '</div>' : '') + '<div class="title">' + slide.title + '</div>' + (slide.sub ? '<div class="sub">' + slide.sub + '</div>' : '');
};
window.setLayout = setLayout;
window.TOTAL = TOTAL;
window.SCENES = SB.scenes.map((s) => ({ id: s.id, start: s.start, duration: s.duration, frameAt: s.frameAt }));
setLayout(${DEVICE.H});
window.ready = Promise.all([...preload, document.fonts.ready]).then(() => true);
</script></body></html>`;

/**
 * The mix: the voice at `voiceLufs`, the music `musicGapDb` below it and ducked by a sidechain compressor while the
 * voice speaks (present in the breaths), fade in and out, and a two-pass `loudnorm`: the first measures the mix, the
 * second applies a linear gain to `lufs` with the true peak at `truePeak` (-2 dBTP, 1 dB under the -1 the platforms ask,
 * the encoder's margin). The limiter BEFORE the measure (peak at -6 dBFS) is what lets the linear gain reach -14 LUFS
 * without passing the true peak: without it, `loudnorm` falls back to dynamic mode and the AAC overshoots the ceiling.
 * The starting levels come from measuring each track, so changing the voice or the music needs no hand tuning.
 *
 * With music and no narration (the path without an ElevenLabs key), the music is the foreground: it starts at
 * `voiceLufs`, with the same fades, the same pre-limiter and the same two passes.
 */
async function mixAudio(total, silentVideo, outVideo) {
  const A = AUDIO_SPEC;
  const voiceFile = narration ? join(dirname(NARRATION), narration.audio) : null;
  const voiceGain = voiceFile ? A.voiceLufs - Number((await measure(voiceFile)).input_i) : 0;
  const musicGain = MUSIC ? A.voiceLufs - (voiceFile ? A.musicGapDb : 0) - Number((await measure(MUSIC)).input_i) : 0;
  const delay = Math.round(A.leadIn * 1000);
  const limiter = 'alimiter=limit=0.5:attack=3:release=60:level=0';
  const len = total.toFixed(3);
  const musicChain = (input) => `[${input}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:${len},volume=${musicGain.toFixed(2)}dB,afade=t=in:d=${A.fadeIn},afade=t=out:st=${(total - A.fadeOut).toFixed(3)}:d=${A.fadeOut}`;
  const graph = voiceFile
    ? [
        `[1:a]aresample=48000,aformat=channel_layouts=stereo,highpass=f=70,volume=${voiceGain.toFixed(2)}dB,adelay=${delay}:all=1,apad,atrim=0:${len}${MUSIC ? ',asplit=2[v][key]' : '[v]'}`,
        ...(MUSIC
          ? [
              `${musicChain(2)}[m]`,
              `[m][key]sidechaincompress=threshold=${A.duckThreshold}:ratio=${A.duckRatio}:attack=20:release=${A.duckRelease}:makeup=1[md]`,
              `[v][md]amix=inputs=2:normalize=0,${limiter}[mix]`,
            ]
          : [`[v]${limiter}[mix]`]),
      ]
    : [`${musicChain(1)},${limiter}[mix]`];
  const inputs = [...(voiceFile ? ['-i', voiceFile] : []), ...(MUSIC ? ['-i', MUSIC] : [])];
  const pre = join(WORK, 'mix.wav');
  await run('ffmpeg', ['-y', '-f', 'lavfi', '-t', len, '-i', 'anullsrc=r=48000:cl=stereo', ...inputs, '-filter_complex', graph.join(';'), '-map', '[mix]', '-t', len, pre]);
  const m = await measure(pre);
  const norm = `loudnorm=I=${A.lufs}:TP=${A.truePeak}:LRA=11:measured_I=${m.input_i}:measured_TP=${m.input_tp}:measured_LRA=${m.input_lra}:measured_thresh=${m.input_thresh}:offset=${m.target_offset}:linear=true,aresample=48000`;
  await run('ffmpeg', ['-y', '-i', silentVideo, '-i', pre, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-af', norm, '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', len, '-movflags', '+faststart', outVideo]);
  const final = await measure(outVideo);
  console.log(`audio: ${voiceFile ? `voice ${voiceGain.toFixed(1)} dB` : 'no voice'}${MUSIC ? `, music ${musicGain.toFixed(1)} dB` : ''}; final ${final.input_i} LUFS, true peak ${final.input_tp} dBTP`);
}

const withAudio = Boolean(narration || MUSIC);
await rm(join(WORK, 'raw'), { recursive: true, force: true });
await mkdir(join(WORK, 'raw'), { recursive: true });
await mkdir(join(OUT, 'frames'), { recursive: true });
const pagePath = join(WORK, 'index.html');
await writeFile(pagePath, html);
const silentVideo = join(WORK, 'video.mp4');
const video = join(OUT, storyboard.output ?? (LANDSCAPE ? 'video.mp4' : 'reel.mp4'));
if (ONLY === 'audio' && !existsSync(silentVideo)) die(`no ${rel(silentVideo)}: render with --only video (and --narration or --music) first`);

const chromium = await loadChromium(loaded.root);
const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
let total = 0;
try {
  const page = await browser.newPage({ viewport: { width: DEVICE.W, height: DEVICE.H }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(fileUrl(pagePath));
  await page.evaluate(() => window.ready);
  if (errors.length) throw new Error(`composition page: ${errors.join('; ')}`);
  total = await page.evaluate(() => window.TOTAL);
  const scenes = await page.evaluate(() => window.SCENES);
  const fps = storyboard.fps ?? 30;
  const render = async (t) => page.evaluate((time) => window.renderAt(time), t);

  if (ONLY !== 'audio') {
    for (const [i, scene] of scenes.entries()) {
      await render(scene.start + (scene.frameAt ?? Math.max(0.1, scene.duration - 0.45)));
      await page.screenshot({ path: join(OUT, 'frames', `${String(i + 1).padStart(2, '0')}-${scene.id}.png`) });
    }
    console.log(`${scenes.length} scene frames in ${rel(join(OUT, 'frames'))}`);
  }

  if (LANDSCAPE && (ONLY === 'all' || ONLY === 'stills')) {
    const poster = storyboard.poster ?? { scene: scenes[0].id, at: 1.5 };
    const posterScene = scenes.find((s) => s.id === poster.scene);
    await render(posterScene.start + poster.at);
    await page.screenshot({ path: join(OUT, 'poster.jpg'), type: 'jpeg', quality: 86 });
    console.log(`poster in ${rel(join(OUT, 'poster.jpg'))}`);
  }

  if (!LANDSCAPE && (ONLY === 'all' || ONLY === 'stills')) {
    const cover = storyboard.cover ?? { scene: scenes[0].id, at: 1.5 };
    const coverScene = scenes.find((s) => s.id === cover.scene);
    await render(coverScene.start + cover.at);
    await page.screenshot({ path: join(OUT, 'capa-1080x1920.png') });
    await page.setViewportSize({ width: 1080, height: 1350 });
    await page.evaluate(() => window.setLayout(1350));
    await render(coverScene.start + cover.at);
    await page.screenshot({ path: join(OUT, 'capa-1080x1350.png') });
    for (let i = 0; i < (storyboard.carousel ?? []).length; i++) {
      await page.evaluate((index) => window.renderSlide(index), i);
      await page.screenshot({ path: join(OUT, `carrossel-${String(i + 1).padStart(2, '0')}.png`) });
    }
    await page.setViewportSize({ width: 1080, height: 1920 });
    await page.evaluate(() => window.setLayout(1920));
    console.log(`covers and carousel in ${rel(OUT)}`);
  }

  if (ONLY === 'all' || ONLY === 'video') {
    const frames = Math.round(total * fps);
    for (let f = 0; f < frames; f++) {
      await render(f / fps);
      await page.screenshot({ path: join(WORK, 'raw', `${String(f).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 94 });
      if (f % fps === 0 && process.stdout.isTTY) process.stdout.write(`\r  frame ${f}/${frames}`);
    }
    if (process.stdout.isTTY) process.stdout.write('\n');
    /** JPEG frames are full range; without the range conversion the encoder tags the stream `yuvj420p`, which phones may refuse. */
    await run('ffmpeg', ['-y', '-framerate', String(fps), '-i', join(WORK, 'raw', '%05d.jpg'), '-vf', 'scale=in_range=full:out_range=tv,format=yuv420p', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-color_range', 'tv', '-profile:v', 'high', '-movflags', '+faststart', withAudio ? silentVideo : video]);
    console.log(`video of ${total.toFixed(2)} s, ${frames} frames${withAudio ? '' : `, silent, in ${rel(video)}`}`);
  }
  if (errors.length) throw new Error(`composition page: ${errors.join('; ')}`);
} finally {
  await browser.close();
}
await rm(join(WORK, 'raw'), { recursive: true, force: true });
if (withAudio && ONLY !== 'stills') {
  await mixAudio(total, silentVideo, video);
  console.log(`${LANDSCAPE ? 'video' : 'reel'} in ${rel(video)} (${total.toFixed(2)} s, with ${narration ? 'narration' : 'music'})`);
}
if (narration && LANDSCAPE && ONLY !== 'stills') {
  await writeFile(join(OUT, 'legendas.vtt'), webVtt(storyboard.scenes));
  console.log(`captions in ${rel(join(OUT, 'legendas.vtt'))}`);
}

/**
 * The player caption (WebVTT) from the spoken words, in video time: a cue gathers words up to the end of a sentence, a
 * pause over 0.6 s or 84 characters, in at most two lines of up to 42, and leaves 0.2 s after its last word (or when
 * the next cue starts).
 */
function webVtt(scenes) {
  const words = [];
  let start = 0;
  for (const scene of scenes) {
    for (const w of scene.spoken?.words ?? []) words.push({ text: w.text, start: start + w.start, end: start + w.end });
    start += scene.duration;
  }
  const cues = [];
  let current = [];
  const flush = () => {
    if (current.length) cues.push(current);
    current = [];
  };
  words.forEach((w, i) => {
    const next = words[i + 1];
    current.push(w);
    const text = current.map((c) => c.text).join(' ');
    const sentenceEnd = /[.!?]$/.test(w.text);
    const pause = next && next.start - w.end > 0.6;
    const nextTooLong = next && (text + ' ' + next.text).length > 84;
    if (!next || sentenceEnd || pause || nextTooLong) flush();
  });
  const stamp = (t) => {
    const ms = Math.max(0, Math.round(t * 1000));
    const h = Math.floor(ms / 3600000), m = Math.floor((ms % 3600000) / 60000), s = Math.floor((ms % 60000) / 1000);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms % 1000).padStart(3, '0')}`;
  };
  const twoLines = (text) => {
    if (text.length <= 42) return text;
    let cut = -1;
    for (let i = 0; i < text.length; i++) if (text[i] === ' ' && Math.abs(i - text.length / 2) < Math.abs(cut - text.length / 2)) cut = i;
    return cut > 0 ? `${text.slice(0, cut)}\n${text.slice(cut + 1)}` : text;
  };
  const body = cues.map((cue, i) => {
    const nextStart = cues[i + 1]?.[0].start ?? Infinity;
    const end = Math.min(cue.at(-1).end + 0.2, nextStart);
    return `${i + 1}\n${stamp(cue[0].start)} --> ${stamp(end)}\n${twoLines(cue.map((c) => c.text).join(' '))}`;
  });
  return `WEBVTT\n\n${body.join('\n\n')}\n`;
}
