/**
 * The project config (`.claude/showcase.json`) and the CLI. Every script reads the config first and lets its flags
 * override it. Paths in the config are relative to the project root, the directory that holds `.claude/`.
 *
 * Nothing here names a product: with no config, the defaults are a neutral palette, the system fonts and no logo.
 */
import { existsSync, readFileSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { dirname, isAbsolute, join, resolve } from 'node:path';

/** `--name value`, `--flag` and positionals. A value that starts with `--` is the next flag, not a value. */
export function parseArgs(argv = process.argv.slice(2)) {
  const flags = {};
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith('--')) {
      positional.push(token);
      continue;
    }
    const name = token.slice(2);
    const next = argv[i + 1];
    if (next != null && !next.startsWith('--')) {
      flags[name] = next;
      i++;
    } else flags[name] = true;
  }
  return { flags, positional };
}

/** Neutral defaults: the project's palette replaces them key by key. `onAccent` is the text drawn over the accent. */
export const DEFAULT_PALETTE = {
  dark: {
    bg: '#111318',
    frame: '#1a1d24',
    border: 'rgba(255, 255, 255, 0.16)',
    text: '#e8eaee',
    muted: '#a0a7b4',
    tertiary: '#707887',
    accent: '#8ab4ff',
    onAccent: '#0b1220',
    glow: '#c4a3ff',
    chrome: '#1d2129',
    field: '#0f1217',
  },
  light: {
    bg: '#f7f8fa',
    frame: '#ffffff',
    border: 'rgba(15, 23, 42, 0.18)',
    text: '#0b0d12',
    muted: '#4a5363',
    tertiary: '#677083',
    accent: '#2457d6',
    onAccent: '#ffffff',
    glow: '#7c4dff',
    chrome: '#e9ecf1',
    field: '#ffffff',
  },
};

export const DEFAULTS = {
  product: '',
  site: '',
  locale: 'en-US',
  timezone: 'UTC',
  baseUrl: 'http://localhost:3000',
  captureHosts: [],
  theme: { default: 'dark' },
  login: null,
  mask: { presets: ['cpf', 'cnpj', 'phone-br', 'email'], patterns: [], hide: [] },
  hideSelectors: [],
  contentTimeoutMs: 180000,
  copy: { sources: [], notDo: null, releaseNotes: null, rules: [] },
  output: 'marketing',
  voice: null,
  music: null,
};

/** The project root: the nearest directory, from `start` up, that has `.claude/showcase.json`; else `start`. */
export function findRoot(start = process.cwd()) {
  for (let dir = resolve(start); ; dir = dirname(dir)) {
    if (existsSync(join(dir, '.claude', 'showcase.json'))) return dir;
    if (dirname(dir) === dir) return resolve(start);
  }
}

export async function loadConfig(flags = {}) {
  const file = flags.config ? resolve(flags.config) : join(findRoot(), '.claude', 'showcase.json');
  const root = flags.config ? dirname(dirname(file)) : findRoot();
  const raw = existsSync(file) ? JSON.parse(await readFile(file, 'utf8')) : {};
  const config = {
    ...DEFAULTS,
    ...raw,
    theme: { ...DEFAULTS.theme, ...(raw.theme ?? {}) },
    mask: { ...DEFAULTS.mask, ...(raw.mask ?? {}) },
    copy: { ...DEFAULTS.copy, ...(raw.copy ?? {}) },
  };
  if (flags['base-url']) config.baseUrl = flags['base-url'];
  return { root, file: existsSync(file) ? file : null, config, path: (p) => (p ? (isAbsolute(p) ? p : join(root, p)) : null) };
}

export function paletteOf(config, theme) {
  if (!DEFAULT_PALETTE[theme]) throw new Error(`unknown theme: ${theme} (dark or light)`);
  return { ...DEFAULT_PALETTE[theme], ...(config.palette?.[theme] ?? {}) };
}

/** Logo per theme (a string is the same file for both) and the two font files; a missing file is null. */
export function brandFiles(loaded, theme) {
  const { config, path } = loaded;
  const logo = typeof config.logo === 'string' ? config.logo : config.logo?.[theme];
  const pick = (p) => (p && existsSync(path(p)) ? path(p) : null);
  return { logo: pick(logo), display: pick(config.fonts?.display), body: pick(config.fonts?.body) };
}

const MIME = { svg: 'image/svg+xml', png: 'image/png', webp: 'image/webp', jpg: 'image/jpeg', jpeg: 'image/jpeg', woff2: 'font/woff2', woff: 'font/woff', ttf: 'font/ttf', otf: 'font/otf' };

/** A data URI, because a page built with `setContent` has no base URL to resolve a relative path against. */
export function dataUri(file) {
  if (!file) return null;
  const mime = MIME[file.split('.').pop().toLowerCase()] ?? 'application/octet-stream';
  return `data:${mime};base64,${readFileSync(file).toString('base64')}`;
}

export function escapeHtml(text) {
  return String(text ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
}

/** Loopback hosts are always allowed; any other host must be listed in `captureHosts` (a staging with seed data). */
export function assertCaptureHost(baseUrl, config) {
  const host = new URL(baseUrl).hostname;
  const local = ['localhost', '127.0.0.1', '::1', '[::1]'].includes(host) || host.endsWith('.localhost') || host.endsWith('.test');
  if (!local && !(config.captureHosts ?? []).includes(host)) {
    throw new Error(`${host} is not a local host and is not in captureHosts: captures run against seed data only, never production`);
  }
}

export const rel = (p) => String(p).replace(`${process.cwd()}/`, '');

export function fail(error) {
  console.error(`FAILED: ${error.message}`);
  process.exitCode = 1;
}
