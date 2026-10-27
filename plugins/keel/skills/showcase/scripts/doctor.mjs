#!/usr/bin/env node
/**
 * Checks what the showcase scripts need, and says how to fix what is missing.
 *
 *   node doctor.mjs            human report
 *   node doctor.mjs --json     the same as JSON (the tests read it)
 *   node doctor.mjs --install  installs the pinned Playwright and its Chromium in ~/.cache/keel/showcase/ (nothing else)
 *
 * The ElevenLabs key is reported as configured or not, and where from (env or the owner's file). Its value and its
 * length are never read into the report: the file is opened only to know whether the key line has a value.
 */
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { loadConfig, parseArgs } from './lib/config.mjs';
import { keyFile } from './lib/key.mjs';
import { PLAYWRIGHT_VERSION, cacheDir, resolvePlaywright } from './lib/playwright.mjs';

const { flags } = parseArgs();

function ffmpegCheck() {
  const probe = (args) => spawnSync('ffmpeg', ['-hide_banner', ...args], { encoding: 'utf8' });
  const version = probe(['-version']);
  if (version.error || version.status !== 0) return { ok: false, missing: ['ffmpeg'] };
  const encoders = probe(['-encoders']).stdout ?? '';
  const filters = probe(['-filters']).stdout ?? '';
  const missing = [
    ...['libx264', 'aac'].filter((e) => !new RegExp(`\\s${e}\\s`).test(encoders)),
    ...['loudnorm', 'sidechaincompress', 'alimiter', 'amix', 'adelay', 'afade'].filter((f) => !new RegExp(`\\s${f}\\s`).test(filters)),
  ];
  const ffprobe = !spawnSync('ffprobe', ['-version']).error;
  return { ok: missing.length === 0, version: version.stdout.split('\n')[0], missing, ffprobe };
}

async function playwrightCheck(root) {
  const found = resolvePlaywright(root);
  if (!found) return { ok: false, source: null, hint: 'node doctor.mjs --install' };
  try {
    const mod = await import(pathToFileURL(found.entry).href);
    const chromium = mod.chromium ?? mod.default?.chromium;
    const downloaded = existsSync(chromium.executablePath());
    return {
      ok: downloaded,
      source: found.source,
      name: found.name,
      version: found.version,
      chromium: downloaded,
      hint: downloaded ? null : found.source === 'cache' ? 'node doctor.mjs --install' : 'npx playwright install chromium (in the project)',
    };
  } catch (error) {
    return { ok: false, source: found.source, version: found.version, hint: error.message.split('\n')[0] };
  }
}

/** Configured or not, and from where. The value is only tested for being non-empty. */
function keyCheck() {
  if (process.env.ELEVENLABS_API_KEY) return { configured: true, source: 'env' };
  const file = keyFile();
  if (!existsSync(file)) return { configured: false, source: null, file };
  const has = readFileSync(file, 'utf8')
    .split('\n')
    .some((l) => /^\s*ELEVENLABS_API_KEY\s*=\s*\S/.test(l));
  const mode = (statSync(file).mode & 0o777).toString(8);
  return { configured: has, source: has ? 'file' : null, file, fileMode: mode, fileModeOk: mode === '600' };
}

function install() {
  const dir = cacheDir();
  mkdirSync(dir, { recursive: true });
  if (!existsSync(join(dir, 'package.json'))) writeFileSync(join(dir, 'package.json'), '{ "private": true, "name": "keel-showcase-cache" }\n');
  const step = (cmd, args) => {
    console.log(`$ ${cmd} ${args.join(' ')}   (in ${dir})`);
    const r = spawnSync(cmd, args, { cwd: dir, stdio: 'inherit' });
    if (r.status !== 0) throw new Error(`${cmd} exited with ${r.status}`);
  };
  step('npm', ['install', '--no-audit', '--no-fund', `playwright@${PLAYWRIGHT_VERSION}`]);
  step(join(dir, 'node_modules', '.bin', 'playwright'), ['install', 'chromium']);
}

if (flags.install) install();

const loaded = await loadConfig(flags);
const major = Number(process.versions.node.split('.')[0]);
const key = keyCheck();
const report = {
  node: { ok: major >= 20, version: process.versions.node },
  ffmpeg: ffmpegCheck(),
  playwright: await playwrightCheck(loaded.root),
  config: { ok: Boolean(loaded.file), file: loaded.file, root: loaded.root, product: loaded.config.product || null, login: Boolean(loaded.config.login) },
  elevenlabsKey: key.configured,
  elevenlabs: { source: key.source, file: key.file ?? keyFile(), fileMode: key.fileMode ?? null, fileModeOk: key.fileModeOk ?? null },
};
report.ok = report.node.ok && report.ffmpeg.ok && report.playwright.ok;

if (flags.json) {
  console.log(JSON.stringify(report, null, 2));
} else {
  const mark = (ok) => (ok ? 'ok  ' : 'MISS');
  console.log(`${mark(report.node.ok)} node ${report.node.version} (needs >= 20)`);
  console.log(`${mark(report.ffmpeg.ok)} ffmpeg${report.ffmpeg.missing.length ? `: missing ${report.ffmpeg.missing.join(', ')}` : ''}`);
  const pw = report.playwright;
  console.log(`${mark(pw.ok)} Playwright${pw.source ? ` ${pw.version} from the ${pw.source}` : ''}${pw.hint ? `: ${pw.hint}` : ''}`);
  console.log(`${report.config.ok ? 'ok  ' : 'none'} config ${report.config.file ?? `.claude/showcase.json not found from ${process.cwd()} (defaults in use)`}`);
  const k = report.elevenlabs;
  console.log(
    `${key.configured ? 'ok  ' : 'none'} ElevenLabs key ${key.configured ? `configured (${k.source})` : 'not configured: video, stills and captions work; narration and generated music do not'}` +
      (k.fileModeOk === false ? `; ${k.file} has mode ${k.fileMode}, run chmod 600` : ''),
  );
}
process.exitCode = report.ok ? 0 : 1;
