#!/usr/bin/env node
/**
 * STATIC post art: brand type and, optionally, a real screen of the product in a window that bleeds off the right edge.
 *
 *   node art.mjs --path /schedule --headline "..." --sub "..." --out <dir> [--format feed|square|story] [--theme dark|light]
 *                [--focus <selector>] [--eyebrow X] [--footer site.com] [--name post] [--viewport 1280x800] [--raw]
 *   node art.mjs --no-shot --headline "..." --out <dir>          typographic art, the app is never opened
 *   node art.mjs --deck <deck.json> --out <dir> [--name x]        a carousel: one PNG per slide, numbered from 01
 *
 * Deck: `{eyebrow?, footer?, format?, theme?, shot?: {path, focus?}, slides: [{headline, sub?, eyebrow?, withShot?}]}`.
 * The screen is captured ONCE and shared by every slide that asks for it; with no slide asking, the app is not opened.
 *
 * Why 1024 px: the capture stays a desktop layout with the UI text legible in the art; 2x so the text is not blurry
 * after the composition. A missing `--focus` element FAILS: the modal did not open or the selector changed, and going on
 * would publish the list behind it as if it were the panel.
 *
 * Outputs: `<name>-<format>.png` (one slide) or `<name>-01.png`, `-02.png`... (deck), and `<name>-tela.png` (raw screen).
 */
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { FORMATS, artHtml, renderArt } from './lib/art-html.mjs';
import { contextOptions, enterScene, openSession, settle } from './lib/browser.mjs';
import { brandFiles, dataUri, fail, loadConfig, paletteOf, parseArgs, rel } from './lib/config.mjs';
import { loadChromium } from './lib/playwright.mjs';

const { flags } = parseArgs();
const str = (name, fallback = '') => (typeof flags[name] === 'string' ? flags[name] : fallback);

/** A clip centred on an element, for a panel over a list: the whole viewport would leave the panel small in the middle. */
async function focusClip(page, selector) {
  const target = page.locator(selector).first();
  if (!(await target.count())) return undefined;
  const box = await target.boundingBox();
  if (!box) return undefined;
  const viewport = page.viewportSize();
  const margin = 16;
  const width = Math.min(viewport.width, box.width + margin * 2);
  const height = Math.min(viewport.height, box.height + margin * 2);
  const x = Math.max(0, Math.min(viewport.width - width, box.x - margin));
  const y = Math.max(0, Math.min(viewport.height - height, box.y - margin));
  return { x, y, width, height };
}

async function main() {
  const loaded = await loadConfig(flags);
  const { config } = loaded;
  const deck = typeof flags.deck === 'string' ? JSON.parse(await readFile(resolve(flags.deck), 'utf8')) : null;
  if (deck && (!Array.isArray(deck.slides) || !deck.slides.length)) throw new Error(`deck without "slides": ${flags.deck}`);
  const slides = deck ? deck.slides : [{ headline: str('headline'), sub: str('sub'), withShot: !flags['no-shot'] }];
  const eyebrow = deck?.eyebrow ?? str('eyebrow');
  const footer = deck?.footer ?? str('footer', config.site);
  const format = deck?.format ?? str('format', 'feed');
  const theme = deck?.theme ?? str('theme', config.theme.default ?? 'dark');
  const target = deck?.shot ?? (typeof flags.path === 'string' ? { path: flags.path, focus: flags.focus } : null);
  const needsShot = slides.some((slide) => slide.withShot);
  const name = str('name', 'post');

  if (needsShot && !target?.path) throw new Error('a slide asks for withShot, but there is no shot.path (nor --path)');
  if (!needsShot && !deck && !flags['no-shot']) throw new Error('missing --path, or use --no-shot for a typographic art');
  if (typeof flags.out !== 'string') throw new Error('missing --out <dir>');
  if (!FORMATS[format]) throw new Error(`unknown format: ${format} (feed, square or story)`);
  const palette = paletteOf(config, theme);
  const viewport = (() => {
    const m = str('viewport').match(/^(\d{3,4})x(\d{3,4})$/);
    return m ? { width: Number(m[1]), height: Number(m[2]) } : { width: 1024, height: 768 };
  })();

  const outDir = resolve(flags.out);
  await mkdir(outDir, { recursive: true });
  const chromium = await loadChromium(loaded.root);
  const browser = await chromium.launch();
  try {
    let png = null;
    let clip;
    if (needsShot) {
      const baseUrl = (str('base-url') || config.baseUrl).replace(/\/$/, '');
      const plan = { viewport, dsf: 2 };
      const ctx = { plan, config, theme, baseUrl };
      const context = await browser.newContext(contextOptions(plan, config, theme));
      const page = await openSession(context, ctx);
      console.log(`capturing ${target.path} (${theme}, ${viewport.width} px)`);
      /** Load FIRST, settle after: a control that only exists on the loaded screen is not found during the skeleton. */
      await enterScene(page, { name: target.path, url: target.path, wait: [{ content: true }, ...(target.wait ?? [])], actions: target.actions }, ctx);
      const { masked } = await settle(page, ctx);
      clip = target.focus ? await focusClip(page, target.focus) : undefined;
      if (target.focus && !clip) throw new Error(`focus "${target.focus}" not found on ${target.path}`);
      png = await page.screenshot({ type: 'png', clip });
      const raw = join(outDir, `${name}-tela.png`);
      await writeFile(raw, png);
      console.log(`  raw screen -> ${rel(raw)}${masked ? ` (${masked} value(s) masked)` : ''}`);
      await context.close();
      if (flags.raw) return;
    }
    const brand = brandFiles(loaded, theme);
    const shotUri = png ? `data:image/png;base64,${png.toString('base64')}` : null;
    for (const [index, slide] of slides.entries()) {
      const html = artHtml({
        shot: slide.withShot ? shotUri : null,
        /** CSS px of the viewport or the clip, not the PNG's pixels: the device scale only doubles the file. */
        shotSize: clip ? { width: clip.width, height: clip.height } : viewport,
        logo: dataUri(brand.logo),
        fonts: { display: dataUri(brand.display), body: dataUri(brand.body) },
        palette,
        format,
        product: config.product,
        options: { eyebrow: slide.eyebrow ?? eyebrow, headline: slide.headline, sub: slide.sub, footer },
      });
      /** Numbered from 01 with a leading zero: the carousel upload orders by file name. */
      const suffix = slides.length > 1 ? `-${String(index + 1).padStart(2, '0')}` : `-${format}`;
      const path = join(outDir, `${name}${suffix}.png`);
      await renderArt(browser, html, format, path);
      console.log(`  slide ${String(index + 1).padStart(2, '0')} -> ${rel(path)} (${FORMATS[format].width}x${FORMATS[format].height})`);
    }
  } finally {
    await browser.close();
  }
}

await main().catch(fail);
