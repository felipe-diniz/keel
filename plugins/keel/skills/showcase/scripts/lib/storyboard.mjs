/**
 * The storyboard schema, checked before any frame is drawn: a typo in a shot or point name used to surface as an
 * exception inside the composition page, minutes into a render. With `cenas.json` at hand, the shot, burst and point
 * names are checked against what was captured. Returns the list of problems, each with its JSON path.
 */
const TRANSITIONS = ['push', 'rise', 'fade', 'cut'];
const EASES = ['inOut', 'out', 'back', 'linear'];
const AUDIO_KEYS = ['leadIn', 'sceneLead', 'tail', 'lufs', 'truePeak', 'voiceLufs', 'musicGapDb', 'duckThreshold', 'duckRatio', 'duckRelease', 'fadeIn', 'fadeOut'];

const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
const isStr = (v) => typeof v === 'string' && v.length > 0;
const isObj = (v) => v != null && typeof v === 'object' && !Array.isArray(v);

export function validateStoryboard(board, cenas = null) {
  const errors = [];
  const bad = (path, what) => errors.push(`${path} ${what}`);
  if (!isObj(board)) return ['storyboard must be a JSON object'];
  if (board.format != null && !['portrait', 'landscape'].includes(board.format)) bad('format', 'must be "portrait" or "landscape"');
  if (board.theme != null && !['dark', 'light'].includes(board.theme)) bad('theme', 'must be "dark" or "light"');
  if (board.fps != null && !(Number.isInteger(board.fps) && board.fps > 0 && board.fps <= 60)) bad('fps', 'must be an integer from 1 to 60');
  if (board.output != null && !(isStr(board.output) && board.output.endsWith('.mp4') && !board.output.includes('/'))) bad('output', 'must be a file name ending in .mp4');
  if (!Array.isArray(board.scenes) || !board.scenes.length) {
    bad('scenes', 'must be a non-empty array');
    return errors;
  }
  const captured = cenas?.scenes ?? null;
  const shotKnown = (path, name) => {
    if (captured && isStr(name) && !captured[name]) bad(path, `names "${name}", which is not in cenas.json`);
  };
  const pointKnown = (path, shots, point) => {
    if (!captured || !isStr(point)) return;
    const candidates = shots.filter((s) => captured[s]);
    if (candidates.length && !candidates.some((s) => captured[s].points?.[point])) bad(path, `names point "${point}", not captured in ${candidates.join(', ')}`);
  };
  const scrollValue = (path, v) => {
    if (v == null || isNum(v)) return [];
    if (isObj(v) && isStr(v.point) && (v.top == null || isNum(v.top))) return [v.point];
    bad(path, 'must be a number or {point, top}');
    return [];
  };
  const pair = (path, v) => {
    if (!(Array.isArray(v) && v.length === 2 && v.every(isNum) && v[0] <= v[1])) bad(path, 'must be [start, end] in seconds');
  };
  const checkShots = (path, shots) => {
    if (shots == null) return [];
    if (!Array.isArray(shots)) {
      bad(path, 'must be an array');
      return [];
    }
    shots.forEach((shot, j) => {
      const p = `${path}[${j}]`;
      if (!isObj(shot)) return bad(p, 'must be an object');
      if (!isStr(shot.shot)) bad(`${p}.shot`, 'must name a captured scene');
      shotKnown(`${p}.shot`, shot.shot);
      if (shot.at != null && !(isNum(shot.at) && shot.at >= 0)) bad(`${p}.at`, 'must be seconds >= 0');
      if (shot.in != null && !TRANSITIONS.includes(shot.in)) bad(`${p}.in`, `must be one of ${TRANSITIONS.join(', ')}`);
      if (shot.dur != null && !(isNum(shot.dur) && shot.dur > 0)) bad(`${p}.dur`, 'must be seconds > 0');
      const points = Array.isArray(shot.scroll)
        ? shot.scroll.length === 2
          ? shot.scroll.flatMap((v, k) => scrollValue(`${p}.scroll[${k}]`, v))
          : (bad(`${p}.scroll`, 'as an array must be [from, to]'), [])
        : scrollValue(`${p}.scroll`, shot.scroll);
      for (const point of points) pointKnown(`${p}.scroll`, [shot.shot], point);
      if (shot.scrollAt != null) pair(`${p}.scrollAt`, shot.scrollAt);
      if (shot.scrollEase != null && !EASES.includes(shot.scrollEase)) bad(`${p}.scrollEase`, `must be one of ${EASES.join(', ')}`);
      if (shot.burst != null) {
        if (!isObj(shot.burst) || !isStr(shot.burst.name)) bad(`${p}.burst.name`, 'must name the captured frame set');
        else {
          shotKnown(`${p}.burst.name`, shot.burst.name);
          pair(`${p}.burst.at`, shot.burst.at);
          if (shot.burst.ease != null && !EASES.includes(shot.burst.ease)) bad(`${p}.burst.ease`, `must be one of ${EASES.join(', ')}`);
        }
      }
      if (shot.url != null && typeof shot.url !== 'string') bad(`${p}.url`, 'must be a string');
    });
    return shots.map((s) => s?.shot).filter(isStr);
  };
  const checkCamera = (path, camera, shotNames) => {
    if (camera == null) return;
    if (!Array.isArray(camera) || !camera.length) return bad(path, 'must be a non-empty array of keys');
    camera.forEach((key, k) => {
      const p = `${path}[${k}]`;
      if (!isObj(key)) return bad(p, 'must be an object');
      if (!isNum(key.at)) bad(`${p}.at`, 'must be seconds');
      if (k && isNum(key.at) && isNum(camera[k - 1]?.at) && key.at < camera[k - 1].at) bad(`${p}.at`, 'must not go back in time');
      for (const n of ['s', 'fx', 'fy', 'ay', 'rot']) if (key[n] != null && !isNum(key[n])) bad(`${p}.${n}`, 'must be a number');
      if (key.ease != null && !EASES.includes(key.ease)) bad(`${p}.ease`, `must be one of ${EASES.join(', ')}`);
      if (key.focus != null) {
        if (!isObj(key.focus) || !isStr(key.focus.point)) bad(`${p}.focus.point`, 'must name a captured point');
        else {
          if (!shotNames.length && !key.focus.shot) bad(`${p}.focus`, 'needs a shot in the scene');
          if (key.focus.shot != null) shotKnown(`${p}.focus.shot`, key.focus.shot);
          pointKnown(`${p}.focus.point`, key.focus.shot ? [key.focus.shot] : shotNames, key.focus.point);
        }
      }
    });
  };

  const ids = new Set();
  board.scenes.forEach((scene, i) => {
    const p = `scenes[${i}]`;
    if (!isObj(scene)) return bad(p, 'must be an object');
    if (!isStr(scene.id)) bad(`${p}.id`, 'must be a non-empty string');
    else if (ids.has(scene.id)) bad(`${p}.id`, `repeats "${scene.id}"`);
    else ids.add(scene.id);
    if (!(isNum(scene.duration) && scene.duration > 0)) bad(`${p}.duration`, 'must be seconds > 0');
    if (scene.device != null && typeof scene.device !== 'boolean') bad(`${p}.device`, 'must be true or false');
    if (scene.frameAt != null && !(isNum(scene.frameAt) && scene.frameAt >= 0 && (!isNum(scene.duration) || scene.frameAt <= scene.duration))) bad(`${p}.frameAt`, 'must be inside the scene');
    if (scene.narration != null && !(isObj(scene.narration) && isStr(scene.narration.text))) bad(`${p}.narration.text`, 'must be the text the voice says');
    if (scene.caption != null) {
      const c = scene.caption;
      if (!isObj(c) || !isStr(c.text)) bad(`${p}.caption.text`, 'must be a string');
      else {
        if (c.accent != null && !(Array.isArray(c.accent) && c.accent.every(isStr))) bad(`${p}.caption.accent`, 'must be a list of words of the text');
        for (const n of ['delay', 'size']) if (c[n] != null && !isNum(c[n])) bad(`${p}.caption.${n}`, 'must be a number');
      }
    }
    if (scene.cta != null) {
      const c = scene.cta;
      if (!isObj(c) || !isStr(c.title)) bad(`${p}.cta.title`, 'must be a string (HTML, <em> is the accent)');
      else if (c.lines != null && !(Array.isArray(c.lines) && c.lines.every((l) => typeof l === 'string'))) bad(`${p}.cta.lines`, 'must be a list of strings');
    }
    const shotNames = checkShots(`${p}.shots`, scene.shots);
    if (scene.taps != null) {
      if (!Array.isArray(scene.taps)) bad(`${p}.taps`, 'must be an array');
      else {
        if (scene.taps.length && !shotNames.length) bad(`${p}.taps`, 'needs a shot in the scene');
        scene.taps.forEach((tap, k) => {
          const t = `${p}.taps[${k}]`;
          if (!isObj(tap)) return bad(t, 'must be an object');
          if (!isNum(tap.at)) bad(`${t}.at`, 'must be seconds');
          if (!isStr(tap.point)) bad(`${t}.point`, 'must name a captured point');
          if (tap.shot != null) shotKnown(`${t}.shot`, tap.shot);
          pointKnown(`${t}.point`, tap.shot ? [tap.shot] : shotNames, tap.point);
        });
      }
    }
    checkCamera(`${p}.camera`, scene.camera, shotNames);
  });

  for (const key of ['cover', 'poster']) {
    const still = board[key];
    if (still == null) continue;
    if (!isObj(still) || !isStr(still.scene) || !ids.has(still.scene)) bad(`${key}.scene`, 'must be the id of a scene');
    if (still && !isNum(still.at)) bad(`${key}.at`, 'must be seconds inside that scene');
  }
  if (board.carousel != null) {
    if (!Array.isArray(board.carousel)) bad('carousel', 'must be an array');
    else
      board.carousel.forEach((slide, i) => {
        const p = `carousel[${i}]`;
        if (!isObj(slide) || !isStr(slide.title)) return bad(`${p}.title`, 'must be a string');
        const names = checkShots(`${p}.shots`, slide.shots);
        if (!names.length) bad(`${p}.shots`, 'needs a shot');
        checkCamera(`${p}.camera`, slide.camera, names);
      });
  }
  if (board.voice != null) {
    const v = board.voice;
    if (!isObj(v)) bad('voice', 'must be an object');
    else {
      for (const n of ['voice_id', 'model_id']) if (v[n] != null && !isStr(v[n])) bad(`voice.${n}`, 'must be a string');
      if (v.pronounce != null && !(isObj(v.pronounce) && Object.values(v.pronounce).every(isStr))) bad('voice.pronounce', 'must map a word to how it is said');
      if (v.settings != null && !isObj(v.settings)) bad('voice.settings', 'must be an object');
    }
  }
  if (board.music != null && !(isObj(board.music) && (board.music.prompt == null || isStr(board.music.prompt)))) bad('music.prompt', 'must be a string');
  if (board.audio != null) {
    if (!isObj(board.audio)) bad('audio', 'must be an object');
    else
      for (const [k, v] of Object.entries(board.audio)) {
        if (!AUDIO_KEYS.includes(k)) bad(`audio.${k}`, `is not a known key (${AUDIO_KEYS.join(', ')})`);
        else if (!isNum(v)) bad(`audio.${k}`, 'must be a number');
      }
  }
  return errors;
}
