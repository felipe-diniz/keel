/**
 * What every capture does before the shutter: a context in the plan's device and the config's locale, the theme set
 * before the first paint, the login, the waits, the plan's actions, the points measured and the personal data masked.
 * Each trap below cost a wrong image once; the comment keeps which.
 */
import { assertCaptureHost } from './config.mjs';
import { maskExpression } from './mask.mjs';

export function contextOptions(plan, config, theme) {
  const viewport = plan.viewport ?? { width: 1024, height: 768 };
  return {
    viewport,
    deviceScaleFactor: plan.dsf ?? 2,
    isMobile: Boolean(plan.mobile),
    hasTouch: Boolean(plan.mobile),
    locale: plan.locale ?? config.locale,
    timezoneId: plan.timezone ?? config.timezone,
    colorScheme: theme,
  };
}

/**
 * The theme goes into storage BEFORE any script of the page runs, on every navigation. Toggling the class on a loaded
 * page loses to the app's theme provider, which rereads its stored preference on hydration and undoes it.
 */
export async function prepareContext(context, { plan, config, theme, baseUrl }) {
  const local = { ...(plan.storage?.localStorage ?? {}) };
  if (config.theme.localStorage) local[config.theme.localStorage] = theme;
  if (Object.keys(local).length) {
    await context.addInitScript((entries) => {
      try {
        for (const [k, v] of Object.entries(entries)) window.localStorage.setItem(k, typeof v === 'string' ? v : JSON.stringify(v));
      } catch {
        /* a page with no storage (about:blank) */
      }
    }, local);
  }
  const cookies = [...(plan.storage?.cookies ?? [])];
  if (config.theme.cookie) cookies.push({ name: config.theme.cookie, value: theme });
  if (cookies.length) await context.addCookies(cookies.map((c) => ({ url: baseUrl, ...c })));
}

export function credentials(recipe) {
  const user = process.env[recipe.userEnv];
  const password = process.env[recipe.passwordEnv];
  const missing = [[recipe.userEnv, user], [recipe.passwordEnv, password]].filter(([, v]) => !v).map(([n]) => n);
  if (missing.length) throw new Error(`login needs the seed credentials in the environment: ${missing.join(', ')} (names from login.userEnv/passwordEnv)`);
  return { user, password };
}

/**
 * Logs in ONCE per run. The fields are refilled in a loop until the submit button enables: the server HTML arrives
 * before the framework hydrates, and a value typed in that window is in the DOM but not in the form state. A second
 * login as the same user usually ends the first session, so a token taken before it is dead.
 */
export async function login(page, { baseUrl, recipe }) {
  const { user, password } = credentials(recipe);
  await page.goto(baseUrl + (recipe.url ?? '/login'), { waitUntil: 'domcontentloaded', timeout: 120_000 });
  const userField = page.locator(recipe.user ?? 'input[type="email"]').first();
  const passwordField = page.locator(recipe.password ?? 'input[type="password"]').first();
  const submit = page.locator(recipe.submit ?? 'button[type="submit"]').first();
  await passwordField.waitFor({ timeout: 60_000 });
  let enabled = false;
  for (let attempt = 0; attempt < 30 && !enabled; attempt++) {
    await userField.fill(user);
    await passwordField.fill(password);
    enabled = await submit.isEnabled().catch(() => false);
    if (!enabled) await page.waitForTimeout(500);
  }
  if (!enabled) throw new Error('the login button stayed disabled for 15 s: check the seed user exists and that no captcha gates the form in this environment');
  await submit.click();
  const success = recipe.success ?? null;
  if (success) await page.waitForURL((url) => url.href.includes(success), { timeout: 180_000, waitUntil: 'commit' });
  else await page.waitForLoadState('domcontentloaded');
}

const SKELETON = '[class*="animate-pulse"], [class*="shimmer"], [class*="skeleton" i], [aria-busy="true"]';

/**
 * Real content, or a failure. No skeleton is not the same as content: the signal that does not lie is text (a
 * skeleton is boxes). The ceiling is minutes because a dev server compiles a route on its first visit.
 */
export async function waitForContent(page, label, timeoutMs) {
  const begin = Date.now();
  let lastNote = 0;
  for (;;) {
    const state = await page.evaluate((sel) => {
      const root = document.querySelector('main') ?? document.body;
      return { skeleton: document.querySelectorAll(sel).length, chars: root.innerText.trim().length };
    }, SKELETON);
    if (state.skeleton === 0 && state.chars > 40) break;
    const elapsed = Date.now() - begin;
    if (elapsed > timeoutMs) throw new Error(`${label} did not load in ${Math.round(timeoutMs / 1000)} s (${state.skeleton} skeleton elements, ${state.chars} characters)`);
    if (elapsed - lastNote >= 15_000) {
      lastNote = elapsed;
      console.log(`  ...${label} loading for ${Math.round(elapsed / 1000)} s`);
    }
    await page.waitForTimeout(500);
  }
  await page.waitForTimeout(300);
}

export async function runWait(page, wait, { label, config }) {
  if (typeof wait === 'number') return page.waitForTimeout(wait);
  if (wait.ms != null) return page.waitForTimeout(wait.ms);
  if (wait.selector) return page.locator(wait.selector).first().waitFor({ timeout: wait.timeout ?? 60_000 });
  if (wait.text) return page.getByText(wait.text, { exact: Boolean(wait.exact) }).first().waitFor({ timeout: wait.timeout ?? 60_000 });
  if (wait.url) return page.waitForURL((url) => url.href.includes(wait.url), { timeout: wait.timeout ?? 60_000 });
  if (wait.content) return waitForContent(page, label, wait.timeout ?? config.contentTimeoutMs);
  if (wait.networkidle) return page.waitForLoadState('networkidle', { timeout: wait.timeout ?? 60_000 });
  throw new Error(`unknown wait in ${label}: ${JSON.stringify(wait)}`);
}

/** Scrolls the nearest scrollable ancestor until the element sits `top` px from the top of the window. */
export async function scrollToElement(page, selector, top = 120) {
  const target = page.locator(selector).first();
  await target.waitFor();
  await target.evaluate((element, offset) => {
    let scroller = document.scrollingElement;
    for (let node = element.parentElement; node; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (/(auto|scroll)/.test(style.overflowY) && node.scrollHeight > node.clientHeight) {
        scroller = node;
        break;
      }
    }
    scroller.scrollTop += element.getBoundingClientRect().top - offset;
  }, top);
  await page.waitForTimeout(300);
}

export async function runAction(page, action, ctx) {
  const touch = ctx.plan.mobile;
  if (action.click) return touch ? page.locator(action.click).first().tap() : page.locator(action.click).first().click();
  if (action.tap) return page.locator(action.tap).first().tap();
  if (action.fill) {
    const value = action.valueEnv ? process.env[action.valueEnv] : action.value;
    if (value == null) throw new Error(`fill ${action.fill}: no value${action.valueEnv ? ` in ${action.valueEnv}` : ''}`);
    return page.locator(action.fill).first().fill(String(value));
  }
  if (action.select) return page.locator(action.select).first().selectOption(action.option);
  if (action.press) return action.selector ? page.locator(action.selector).first().press(action.press) : page.keyboard.press(action.press);
  if (action.scroll) {
    const s = action.scroll;
    if (s.to) return scrollToElement(page, s.to, s.top ?? 120);
    if (s.y != null) return page.evaluate((y) => (document.scrollingElement ?? document.documentElement).scrollTo(0, y), s.y);
    /** Scrolled by script and never by the wheel: `mouse.wheel` needs the cursor, and a moved cursor triggers hover. */
    for (let step = 0; step < (s.steps ?? 1); step++) {
      await page.evaluate((by) => (document.scrollingElement ?? document.documentElement).scrollBy({ top: by, behavior: 'smooth' }), s.by ?? 90);
      await page.waitForTimeout(s.pause ?? 1200);
    }
    return;
  }
  if (action.wait != null) return runWait(page, action.wait, ctx);
  if (action.clock) {
    if (action.clock === 'pause') return page.clock.pauseAt(new Date(Date.now() + (action.ahead ?? 5000)));
    if (action.clock === 'resume') return page.clock.resume();
    if (action.clock === 'run') return page.clock.runFor(action.ms ?? 1000);
  }
  if (action.goto) return page.goto(ctx.baseUrl + action.goto, { waitUntil: action.waitUntil ?? 'domcontentloaded' });
  throw new Error(`unknown action in ${ctx.label}: ${JSON.stringify(action)}`);
}

/** A point is a rect in page coordinates (scroll included), the shape `cenas.json` keeps. */
export async function rectOf(page, selector) {
  const target = page.locator(selector).first();
  await target.waitFor();
  return target.evaluate((el) => {
    const r = el.getBoundingClientRect();
    return { x: r.x + window.scrollX, y: r.y + window.scrollY, w: r.width, h: r.height };
  });
}

/**
 * Points are measured BEFORE masking: a locator that finds an item by its text stops matching once the text changes.
 * The mouse goes near the bottom-right corner, never onto an edge: an edge can open a sidebar over the page.
 */
export async function settle(page, ctx, points = {}) {
  if (!ctx.plan.mobile && ctx.plan.mouse !== false) {
    const { width, height } = page.viewportSize();
    const at = ctx.plan.mouse ?? { x: width - 24, y: height - 24 };
    await page.mouse.move(at.x, at.y);
    await page.waitForTimeout(300);
  }
  const measured = {};
  for (const [key, selector] of Object.entries(points)) measured[key] = await rectOf(page, selector);
  const masked = ctx.plan.mask === false ? 0 : await page.evaluate(maskExpression(ctx.config.mask));
  const hide = [...(ctx.config.hideSelectors ?? []), ...(ctx.plan.hide ?? [])];
  if (hide.length) await page.addStyleTag({ content: `${hide.join(',')}{visibility:hidden !important}` });
  await assertTheme(page, ctx);
  return { points: measured, masked };
}

export async function assertTheme(page, { config, theme }) {
  const cls = config.theme.darkClass;
  if (!cls) return;
  const dark = await page.evaluate((c) => document.documentElement.classList.contains(c), cls);
  if (dark !== (theme === 'dark')) throw new Error(`the theme slipped: asked ${theme}, the page paints ${dark ? 'dark' : 'light'}`);
}

/** Login (if the plan asks and the config has a recipe), then the base URL guard already passed. */
export async function openSession(context, ctx) {
  assertCaptureHost(ctx.baseUrl, ctx.config);
  await prepareContext(context, ctx);
  const page = await context.newPage();
  if (ctx.plan.clock) await page.clock.install();
  if (ctx.plan.login !== false && (ctx.plan.login || ctx.config.login)) {
    const recipe = { ...(ctx.config.login ?? {}), ...(typeof ctx.plan.login === 'object' ? ctx.plan.login : {}) };
    if (!recipe.userEnv || !recipe.passwordEnv) throw new Error('the login recipe needs userEnv and passwordEnv (the NAMES of the variables)');
    await login(page, { baseUrl: ctx.baseUrl, recipe });
  }
  return page;
}

/** Opens the scene's URL, waits and plays its actions. */
export async function enterScene(page, scene, ctx) {
  const label = scene.name ?? scene.url;
  if (scene.url) await page.goto(ctx.baseUrl + scene.url, { waitUntil: scene.waitUntil ?? 'domcontentloaded', timeout: 120_000 });
  for (const wait of scene.wait ?? []) await runWait(page, wait, { ...ctx, label });
  for (const action of scene.actions ?? []) await runAction(page, action, { ...ctx, label });
}
