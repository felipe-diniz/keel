#!/usr/bin/env node
/**
 * CAPTURE by a JSON plan, against the project's local app with seed data.
 *
 *   node capture.mjs --plan <plan.json> --out <dir> [--only a,b] [--theme dark|light] [--base-url http://localhost:3000]
 *   node capture.mjs record --plan <plan.json> --out <dir> [--seconds 12]
 *
 * Scenes mode writes `<out>/cenas/<name>.png` and `<out>/cenas/cenas.json` in the shape `compose.mjs` reads:
 * `{viewport, dsf, theme, scenes: {name: {file, width, height, scrollY, url, points, bar?, masked} | {dir, count, clip}}}`.
 * `cenas.json` is saved after every scene, so a run that breaks halfway keeps what it took; `--only` reshoots some
 * scenes and keeps the others.
 *
 * Record mode is the quick Reel: a Playwright screen recording of the plan's scenes, trimmed from the END by `-sseof`
 * (login and load time drop out without knowing how long they took), laid as a band on a brand background with the
 * headline in the top third. 1080x1920, 30 fps, yuv420p (without it the MP4 opens on a computer and fails on a phone).
 *
 * The plan format, the actions and the traps are in `references/capture.md`. The base URL must be local or listed in
 * the config's `captureHosts`: captures are of seed data, never production.
 */
import { existsSync, readdirSync } from 'node:fs';
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { FORMATS, artHtml, renderArt } from './lib/art-html.mjs';
import { contextOptions, enterScene, openSession, rectOf, runAction, settle } from './lib/browser.mjs';
import { brandFiles, dataUri, fail, loadConfig, paletteOf, parseArgs, rel } from './lib/config.mjs';
import { loadChromium } from './lib/playwright.mjs';
import { run } from './lib/run.mjs';

const { flags, positional } = parseArgs();
const MODE = positional[0] ?? 'scenes';

async function setup() {
  if (typeof flags.plan !== 'string' || typeof flags.out !== 'string') throw new Error('usage: capture.mjs [record] --plan <plan.json> --out <dir>');
  const loaded = await loadConfig(flags);
  const plan = JSON.parse(await readFile(resolve(flags.plan), 'utf8'));
  if (!Array.isArray(plan.scenes) || !plan.scenes.length) throw new Error('the plan has no scenes');
  const theme = flags.theme ?? plan.theme ?? loaded.config.theme.default ?? 'dark';
  const baseUrl = (flags['base-url'] ?? plan.baseUrl ?? loaded.config.baseUrl).replace(/\/$/, '');
  return { loaded, plan, theme, baseUrl, out: resolve(flags.out), ctx: { plan, config: loaded.config, theme, baseUrl } };
}

async function scenesMode() {
  const { loaded, plan, theme, out, ctx } = await setup();
  const dir = join(out, 'cenas');
  await mkdir(dir, { recursive: true });
  const only = typeof flags.only === 'string' ? new Set(flags.only.split(',')) : null;
  const cenasFile = join(dir, 'cenas.json');
  const kept = only && existsSync(cenasFile) ? JSON.parse(await readFile(cenasFile, 'utf8')).scenes : {};
  const options = contextOptions(plan, loaded.config, theme);
  const scenes = { ...kept };
  const save = () => writeFile(cenasFile, `${JSON.stringify({ viewport: options.viewport, dsf: options.deviceScaleFactor, theme, scenes }, null, 2)}\n`);

  const chromium = await loadChromium(loaded.root);
  const browser = await chromium.launch();
  try {
    const context = await browser.newContext(options);
    const page = await openSession(context, ctx);
    for (const scene of plan.scenes) {
      if (!scene.name) throw new Error(`a scene without name: ${JSON.stringify(scene).slice(0, 80)}`);
      if (only && !only.has(scene.name)) continue;
      await enterScene(page, scene, ctx);
      const early = scene.burst ? await burst(page, scene, ctx, dir, scenes) : {};
      const settled = await settle(page, ctx, scene.points ?? {});
      const points = { ...early, ...settled.points };
      const { masked } = settled;
      const url = new URL(page.url()).pathname;
      if (scene.full) {
        /**
         * The whole page, for the compositor to scroll through. A FIXED bar would land at the bottom of a full-page
         * image, so it is shot apart (`<name>-barra.png`) and hidden for the page; the compositor pins it to the screen.
         */
        await page.evaluate(() => window.scrollTo(0, 0));
        const meta = { file: `${scene.name}.png`, width: options.viewport.width, scrollY: 0, url, points, masked };
        if (scene.bar) {
          const bar = page.locator(scene.bar).first();
          const box = await bar.boundingBox();
          await bar.screenshot({ path: join(dir, `${scene.name}-barra.png`) });
          await bar.evaluate((el) => (el.style.visibility = 'hidden'));
          meta.bar = { file: `${scene.name}-barra.png`, h: box?.height ?? 0 };
        }
        await page.screenshot({ path: join(dir, `${scene.name}.png`), fullPage: true });
        if (scene.bar) await page.locator(scene.bar).first().evaluate((el) => (el.style.visibility = ''));
        meta.height = await page.evaluate(() => document.documentElement.scrollHeight);
        scenes[scene.name] = { file: meta.file, width: meta.width, height: meta.height, scrollY: 0, url, ...(meta.bar ? { bar: meta.bar } : {}), points, masked };
      } else {
        await page.screenshot({ path: join(dir, `${scene.name}.png`) });
        const scrollY = await page.evaluate(() => window.scrollY);
        scenes[scene.name] = { file: `${scene.name}.png`, width: options.viewport.width, height: options.viewport.height, scrollY, url, points, masked };
      }
      await save();
      console.log(`  scene ${scene.name}${scene.full ? ` (full page, ${scenes[scene.name].height} px)` : ''}${masked ? `, ${masked} value(s) masked` : ''}`);
    }
    await context.close();
  } finally {
    await browser.close();
  }
  console.log(`cenas.json in ${rel(cenasFile)}`);
}

/**
 * A frame-exact animation (a chart that morphs, a counter): the page clock is paused, the trigger actions run, then a
 * clipped screenshot is taken every `stepMs` of page time. Needs `"clock": true` in the plan (installed before load).
 */
async function burst(page, scene, ctx, dir, scenes) {
  const spec = scene.burst;
  if (!ctx.plan.clock) throw new Error(`${scene.name}: a burst needs "clock": true in the plan`);
  const target = page.locator(spec.clip).first();
  await target.waitFor();
  const clip = await target.evaluate((el) => {
    const r = el.getBoundingClientRect();
    return { x: r.x, y: r.y, width: r.width, height: r.height };
  });
  const scrollY = await page.evaluate(() => window.scrollY);
  /** Points of the trigger are measured before it runs: an open menu or a moved element would measure elsewhere. */
  const points = { [spec.name ?? `${scene.name}-quadros`]: { x: clip.x, y: clip.y + scrollY, w: clip.width, h: clip.height } };
  for (const [key, selector] of Object.entries(spec.points ?? {})) points[key] = await rectOf(page, selector);
  const name = spec.name ?? `${scene.name}-quadros`;
  await mkdir(join(dir, name), { recursive: true });
  await page.clock.pauseAt(new Date(Date.now() + 5000));
  for (const action of spec.actions ?? []) await runAction(page, action, { ...ctx, label: scene.name });
  const count = spec.frames ?? 52;
  for (let i = 0; i < count; i++) {
    await page.screenshot({ path: join(dir, name, `${String(i).padStart(3, '0')}.png`), clip });
    await page.clock.runFor(spec.stepMs ?? 10);
  }
  await page.clock.runFor(2000);
  await page.clock.resume();
  await page.waitForTimeout(600);
  await page.evaluate((y) => window.scrollTo(0, y), scrollY);
  scenes[name] = { dir: name, count, clip: { x: clip.x, y: clip.y, w: clip.width, h: clip.height } };
  return points;
}

async function recordMode() {
  const { loaded, plan, theme, out, ctx } = await setup();
  const spec = plan.record ?? {};
  const seconds = Number(flags.seconds ?? spec.seconds ?? 12);
  const name = spec.name ?? 'reel';
  await mkdir(out, { recursive: true });
  const work = join(out, `.record-${name}`);
  await rm(work, { recursive: true, force: true });
  await mkdir(work, { recursive: true });
  const options = { ...contextOptions({ ...plan, dsf: 1 }, loaded.config, theme) };
  const chromium = await loadChromium(loaded.root);
  const browser = await chromium.launch();
  try {
    const context = await browser.newContext({ ...options, recordVideo: { dir: work, size: options.viewport } });
    try {
      const page = await openSession(context, ctx);
      for (const scene of plan.scenes) {
        const { actions, ...still } = scene;
        await enterScene(page, still, ctx);
        await settle(page, { ...ctx, plan: { ...plan, mouse: false } });
        /**
         * From here on is what enters the cut. The cursor is NEVER moved: any `mouse.move` fires a real hover, and a
         * move to a corner once opened a sidebar over a third of the screen mid-recording. Scrolling is by script.
         */
        const begin = Date.now();
        await page.waitForTimeout(spec.hold ?? 1200);
        for (const action of actions ?? []) await runAction(page, action, { ...ctx, label: scene.name });
        const left = seconds * 1000 + 400 - (Date.now() - begin);
        if (left > 0 && scene === plan.scenes.at(-1)) await page.waitForTimeout(left);
      }
    } finally {
      /** The webm is only finished when the context closes: read before that, it is truncated or empty. */
      await context.close();
    }
    const webm = readdirSync(work).find((f) => f.endsWith('.webm'));
    if (!webm) throw new Error('Playwright wrote no recording');
    const palette = paletteOf(loaded.config, theme);
    const brand = brandFiles(loaded, theme);
    const background = join(work, 'fundo.png');
    /** `align: 'top'` keeps the headline in the top third: the bottom half is the video's, and it would cover the text. */
    await renderArt(
      browser,
      artHtml({
        shot: null,
        shotSize: options.viewport,
        logo: dataUri(brand.logo),
        fonts: { display: dataUri(brand.display), body: dataUri(brand.body) },
        palette,
        format: 'story',
        product: loaded.config.product,
        options: { eyebrow: spec.eyebrow, headline: spec.headline, sub: spec.sub, footer: spec.footer ?? loaded.config.site, align: 'top' },
      }),
      'story',
      background,
    );
    /** A FIXED top for the band, not centred: centred, the band climbs over the headline. It drops to fit a taller ratio. */
    const bandW = FORMATS.story.width - 64;
    const bandH = Math.round((bandW * options.viewport.height) / options.viewport.width / 2) * 2;
    const top = Math.max(560, Math.min(spec.top ?? 1000, FORMATS.story.height - bandH - 140));
    const output = join(out, `${name}-reel.mp4`);
    await run('ffmpeg', [
      '-y', '-loop', '1', '-i', background, '-sseof', `-${seconds}`, '-i', join(work, webm),
      '-filter_complex', `[1:v]scale=${bandW}:-2,setsar=1[screen];[0:v][screen]overlay=32:${top}:shortest=1[v]`,
      '-map', '[v]', '-t', String(seconds), '-r', '30', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', output,
    ]);
    console.log(`reel in ${rel(output)} (1080x1920, ${seconds} s, silent)`);
  } finally {
    await browser.close();
    await rm(work, { recursive: true, force: true });
  }
}

const modes = { scenes: scenesMode, record: recordMode };
if (!modes[MODE]) {
  console.error('usage: capture.mjs [record] --plan <plan.json> --out <dir>');
  process.exit(2);
}
await modes[MODE]().catch(fail);
