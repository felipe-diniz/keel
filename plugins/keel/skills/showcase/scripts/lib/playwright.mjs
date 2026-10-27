/**
 * Playwright, from the project first and from the skill's cache second. The project's own copy (`playwright` or
 * `@playwright/test` in its `node_modules`) wins, so the browser build is the one its tests already use. Without it,
 * `doctor.mjs --install` puts the pinned version in `~/.cache/keel/showcase/`, the only place the skill installs to.
 */
import { existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

export const PLAYWRIGHT_VERSION = '1.61.1';
export const cacheDir = () => join(homedir(), '.cache', 'keel', 'showcase');

export function resolvePlaywright(root = process.cwd()) {
  const places = [
    ['project', join(root, 'package.json')],
    ['cache', join(cacheDir(), 'package.json')],
  ];
  for (const [source, anchor] of places) {
    const require = createRequire(anchor);
    for (const name of ['playwright', '@playwright/test']) {
      try {
        const entry = require.resolve(name);
        const pkg = require.resolve(`${name}/package.json`);
        return { source, name, entry, version: require(pkg).version };
      } catch {
        /* not here */
      }
    }
  }
  return null;
}

export async function loadChromium(root) {
  const found = resolvePlaywright(root);
  if (!found) throw new Error('Playwright not found in the project nor in the cache: run `node <skill>/scripts/doctor.mjs --install`');
  const mod = await import(pathToFileURL(found.entry).href);
  const chromium = mod.chromium ?? mod.default?.chromium;
  if (!chromium) throw new Error(`${found.name} at ${found.entry} exports no chromium`);
  if (!existsSync(chromium.executablePath())) {
    throw new Error(`the Chromium of ${found.name}@${found.version} is not downloaded: run \`node <skill>/scripts/doctor.mjs --install\``);
  }
  return chromium;
}
