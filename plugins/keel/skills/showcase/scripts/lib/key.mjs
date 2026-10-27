/**
 * The ElevenLabs key: `ELEVENLABS_API_KEY` from the process wins; else the single `ELEVENLABS_API_KEY=` line of
 * `~/.config/keel/elevenlabs.env`, a file the owner creates (chmod 600) outside any repo. No other line of that file
 * enters the process. The value only goes into the request header; every message passes through `redactor`.
 */
import { existsSync, readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

export const keyFile = () => join(homedir(), '.config', 'keel', 'elevenlabs.env');

export function readKey() {
  if (process.env.ELEVENLABS_API_KEY) return process.env.ELEVENLABS_API_KEY;
  const file = keyFile();
  const text = existsSync(file) ? readFileSync(file, 'utf8') : '';
  const line = text.split('\n').find((l) => /^\s*ELEVENLABS_API_KEY\s*=/.test(l));
  const value = line ? line.slice(line.indexOf('=') + 1).trim().replace(/^(['"])(.*)\1$/, '$2') : '';
  return value || null;
}

export const redactor = (key) => (text) => (key ? String(text).split(key).join('***') : String(text));
