/**
 * The static art: brand type and an optional real screen in a window that bleeds off the right edge. Used by `art.mjs`
 * (post, carousel, story) and by `capture.mjs record` (the Reel background, text in the top third).
 */
import { escapeHtml } from './config.mjs';

/** The ratios the feed and the story use. 4:5 is the feed default because it takes more height in the scroll. */
export const FORMATS = {
  feed: { width: 1080, height: 1350 },
  square: { width: 1080, height: 1080 },
  story: { width: 1080, height: 1920 },
};

export function fontFaces(fonts) {
  return [
    fonts.display && `@font-face{font-family:'SCDisplay';src:url(${fonts.display});font-weight:100 900;font-display:block}`,
    fonts.body && `@font-face{font-family:'SCBody';src:url(${fonts.body});font-weight:100 900;font-display:block}`,
  ]
    .filter(Boolean)
    .join('');
}

export function artHtml({ shot, shotSize, logo, fonts, palette, format, product, options }) {
  const isStory = format === 'story';
  /** A story is 570 px taller than the feed: the breathing room grows there, the type does not. */
  const padTop = isStory ? 140 : 64;
  const padBottom = isStory ? 120 : 56;
  /**
   * No screen means a typographic art: the text becomes the piece. A product has a finite set of screens, and a feed
   * that only rotates them tires in two weeks; a post about a pain point has no screen to show.
   */
  const noShot = !shot;
  const windowWidth = FORMATS[format].width - 64;
  /**
   * The window keeps the capture's RATIO instead of stretching to the footer. With `flex: 1` and `cover`, a near-square
   * story frame scaled a 4:3 capture by its height and pushed the last column out of the art. At its natural height the
   * image is never enlarged; when it does not fit, `cover` from the top left crops the bottom of the screen.
   */
  const naturalHeight = noShot ? 0 : Math.round((windowWidth * shotSize.height) / shotSize.width);
  return `<!doctype html><html><head><meta charset="utf-8"><style>
${fontFaces(fonts)}
*{margin:0;padding:0;box-sizing:border-box}
body{width:${FORMATS[format].width}px;height:${FORMATS[format].height}px;background:${palette.bg};color:${palette.text};font-family:'SCBody',system-ui,-apple-system,sans-serif;display:flex;flex-direction:column;overflow:hidden}
.top{padding:${padTop}px 64px 0}
.logo{height:40px;width:auto;display:block;margin-bottom:${isStory ? 56 : 40}px}
.wordmark{font:700 34px/1 'SCDisplay',system-ui,sans-serif;letter-spacing:-.01em;margin-bottom:${isStory ? 56 : 40}px}
.eyebrow{font-family:'SCDisplay',system-ui,sans-serif;font-size:22px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:${palette.accent};margin-bottom:20px}
.headline{font-family:'SCDisplay',system-ui,sans-serif;font-size:${noShot ? (isStory ? 92 : 82) : isStory ? 76 : 64}px;font-weight:700;line-height:1.1;letter-spacing:-.02em;max-width:${noShot ? 13 : 16}ch}
.sub{font-size:${noShot ? 34 : 30}px;line-height:1.45;color:${palette.muted};margin-top:${noShot ? 40 : 24}px;max-width:30ch}
.solo{flex:1;display:flex;flex-direction:column;justify-content:${options.align === 'top' ? 'flex-start' : 'center'};padding:0 64px}
.rule{width:96px;height:4px;background:${palette.accent};border-radius:2px;margin-bottom:40px}
.stage{flex:1;min-height:0;display:flex;align-items:${isStory ? 'center' : 'flex-start'};padding-left:64px;margin-top:${isStory ? 48 : 56}px}
.window{width:100%;height:min(${naturalHeight}px,100%);background:${palette.frame};border:1px solid ${palette.border};border-right:0;border-radius:10px 0 0 10px;overflow:hidden}
.window img{display:block;width:100%;height:100%;object-fit:cover;object-position:top left}
.footer{padding:${isStory ? 48 : 32}px 64px ${padBottom}px;font-size:24px;font-weight:600;letter-spacing:.02em;color:${palette.tertiary}}
</style></head><body>
<div class="top">${logo ? `<img class="logo" src="${logo}" alt="${escapeHtml(product)}">` : product ? `<div class="wordmark">${escapeHtml(product)}</div>` : ''}</div>
<div class="${noShot ? 'solo' : 'top'}">
  ${noShot ? '<div class="rule"></div>' : ''}
  ${options.eyebrow ? `<div class="eyebrow">${escapeHtml(options.eyebrow)}</div>` : ''}
  ${options.headline ? `<h1 class="headline">${escapeHtml(options.headline)}</h1>` : ''}
  ${options.sub ? `<p class="sub">${escapeHtml(options.sub)}</p>` : ''}
</div>
${noShot ? '' : `<div class="stage"><div class="window"><img src="${shot}" alt=""></div></div>`}
<div class="footer">${escapeHtml(options.footer ?? '')}</div>
</body></html>`;
}

/** Renders one art page to a PNG, waiting for the embedded fonts (async even as data URIs). */
export async function renderArt(browser, html, format, path) {
  const page = await browser.newPage({ viewport: FORMATS[format], deviceScaleFactor: 1 });
  try {
    await page.setContent(html, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(200);
    await page.screenshot({ path, type: 'png' });
  } finally {
    await page.close();
  }
}
