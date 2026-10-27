/** Child processes: ffmpeg answers on stderr (the `loudnorm` measure comes back there), so `run` resolves with it. */
import { spawn } from 'node:child_process';

export function run(command, args, { cwd } = {}) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd, stdio: ['ignore', 'ignore', 'pipe'] });
    let stderr = '';
    child.stderr.on('data', (chunk) => (stderr += chunk));
    child.on('error', reject);
    child.on('close', (code) => (code === 0 ? resolvePromise(stderr) : reject(new Error(`${command} exited with ${code}: ${stderr.slice(-800)}`))));
  });
}

/** Integrated loudness, true peak and range of a file, from the first `loudnorm` pass. */
export async function measure(file) {
  const stderr = await run('ffmpeg', ['-hide_banner', '-nostats', '-i', file, '-af', 'loudnorm=print_format=json', '-f', 'null', '-']);
  return JSON.parse(stderr.slice(stderr.lastIndexOf('{'), stderr.lastIndexOf('}') + 1));
}
