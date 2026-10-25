# Motion

Read when you add scroll, entrance or pointer motion (GSAP, Lenis, CSS scroll-driven) to a marketing page, or decide whether a device should get it.

## When motion is worth it
- Motion communicates what changed. If it communicates nothing, remove it.
- Marketing pages may carry authored motion across the scroll. App screens used all day get none.
- Content stays server HTML, readable without JS, and never hurts LCP, CLS or INP.
- Phone is first class. A desktop-only technique cannot carry the meaning of the page.
- Measure LCP, CLS and total blocking time before and after. If worse beyond run-to-run variance, remove it.

## Layers, in order of weight
1. CSS only: transitions and scroll-driven animations inside `@supports`. Zero JS. Serves phones, old browsers, JS failures.
2. GSAP + ScrollTrigger + SplitText for authored acts, desktop only.
3. Lenis smooth scroll, desktop with mouse only.
4. Three.js: see `three.md`.
- Every layer is an enhancement over a finished static page. Failure leaves the static page.

## Visible by default
- Never hide content with `opacity: 0` until a script runs. It loses content on JS failure, delays LCP, and leaves blocks empty for fast scrollers.
- Put the visible state outside `@supports`. Put only the animation inside it.
- Keyframes declare only the `from` state, so the natural state is the end state.
- Hide something from JS only if it is below the fold, then reveal with `once: true`. Do not animate what the visitor already reads.

## The motion gate
- One pure function decides who gets what. Inject the environment so it runs without a browser.
- Inputs: `(min-width: 1024px)`, `(hover: hover) and (pointer: fine)`, `(prefers-reduced-motion: reduce)`, a WebGL probe.
- Call the WebGL probe lazily. It costs a GPU context. Never call it on phones.
- Decide before the import. A device that gets nothing never requests the chunk.

```ts
export const Q = {
  desktop: '(min-width: 1024px)',
  fine: '(hover: hover) and (pointer: fine)',
  reduced: '(prefers-reduced-motion: reduce)',
};
type Env = { matchMedia: (q: string) => { matches: boolean }; webgl: () => 'gpu' | 'software' | 'none' };

export function planMotion(env: Env) {
  const reduced = env.matchMedia(Q.reduced).matches;
  const desktop = env.matchMedia(Q.desktop).matches;
  const fine = env.matchMedia(Q.fine).matches;
  const gsap = !reduced && desktop;
  const lenis = gsap && fine;
  const webgl = fine && desktop ? env.webgl() : 'none';
  return { gsap, lenis, scene: lenis && webgl === 'gpu', ambient: webgl === 'none' ? null : { still: reduced, software: webgl === 'software' } };
}
```
- Typical matrix: phone gets CSS only. Reduced motion gets CSS plus a still frame at most. Touch tablet gets GSAP without Lenis or pointer effects. Desktop with software GL gets GSAP + Lenis, no heavy scene. Desktop with GPU gets everything.
- Listen to the reduced-motion `change` event. If it turns on while the page is open, run every teardown at once.
- The reduced-motion signal comes from the OS, not the browser. Remote sessions often show it off.

## Loading
- Wait for `load`, then idle: run now if `document.readyState === 'complete'`, else wait for `load`.
- Then `requestIdleCallback(task, { timeout: 2000 })`, or `setTimeout(task, 200)` where unsupported (Safari).
- Return a cancel function that removes the listener, the idle handle and the timeout.
- Load heavy code with dynamic `import()` only. Never statically import gsap, lenis or three in the initial bundle.
- Check the build shows a separate chunk for each. Check the initial JS does not contain the libraries.
- Keep GSAP in a plain module, not in a hook. The `useGSAP` helper is a static import and pulls GSAP into the bundle.
- A render-less component decides, imports, and keeps the teardown. If it unmounts before the import resolves, run the cleanup immediately.
- Do not run GSAP in server render. Register plugins once with `gsap.registerPlugin(...)` at module scope.

## One act per task
- Create hero acts synchronously, then `ScrollTrigger.refresh()`.
- Create each below-the-fold act in its own `setTimeout(fn, 0)` task, wrapped in `context.add(fn)`, then a final refresh.
- Mounted together, acts add up to one long task.
- Use one `gsap.context(() => undefined)` for the whole page. `context.revert()` reverts tweens, ScrollTriggers and SplitText.

## Lenis
- Package `lenis` 1.3.27 (checked 2026-10). Import `lenis/dist/lenis.css`.
- Enable only for fine pointer, desktop, no reduced motion. Keep `syncTouch` off.
- Official GSAP recipe (checked 2026-10):

```ts
const lenis = new Lenis({ autoRaf: false, anchors: true, allowNestedScroll: true });
lenis.on('scroll', ScrollTrigger.update);
const tick = (t: number) => lenis.raf(t * 1000);
gsap.ticker.add(tick);
gsap.ticker.lagSmoothing(0);
// teardown
gsap.ticker.remove(tick);
gsap.ticker.lagSmoothing(500, 33); // gsap defaults
lenis.destroy();
```
- Do not set `autoRaf: true` with this setup (inference, not stated by the README).
- No `scrollerProxy`. Lenis scrolls the native window, so plain `ScrollTrigger.update` is enough.
- `anchors: true` keeps menu, skip-link and hash links working. Anchors are blocked while scrolling otherwise.
- Nested scroll: `allowNestedScroll: true` is the simplest. It checks the DOM on every scroll event. If that costs too much, use `data-lenis-prevent` (variants `-wheel`, `-touch`, `-vertical`, `-horizontal`).
- Lenis ignores CSS `overflow`. When a modal locks the page, return false from the `virtualScroll` option if `getComputedStyle(html).overflowY === 'hidden'` or `event.defaultPrevented`.
- `lerp` default is 0.1. One measured project found 0.2 felt lighter (mean lag 64px down to about 35px). Treat as a starting point, then measure on your own page.
- `respectReducedMotion` defaults to true: smoothing off, anchors jump, Lenis keeps running. Read `lenis.prefersReducedMotion` for your own animations.
- Known limits: no CSS scroll-snap (use `lenis/snap`), 60 fps cap on Safari, `position: fixed` may lag on older Safari.
- Retire it if INP on first gesture or in-page search (Ctrl+F) gets worse.
- React: `lenis/react` `<ReactLenis root options={{ autoRaf: false }} ref>`. Add the ticker callback in `useEffect`, remove it on cleanup.

## ScrollTrigger
- Use `gsap.matchMedia()` for responsive branches. `ScrollTrigger.matchMedia` is deprecated (checked 2026-10). Everything built in the handler reverts when the query stops matching.
- A gate-plus-context design also works. Do not mix both styles for the same act.
- Call `ScrollTrigger.refresh()` after images, fonts or layout change. Create triggers top to bottom, or set `refreshPriority`.
- Never ship `markers`.
- Prefer CSS `position: sticky` over `pin: true`. No pin-spacer, no layout jump when a trigger is born after load.
- With sticky, animate the frame's children, never the sticky frame. Scrub those children from a ScrollTrigger on a timeline.
- If you must pin, do not animate the pinned element. `anticipatePin: 1` is typical.
- Do not combine `scrub` with `toggleActions`. Put the trigger on the timeline, not on child tweens.
- Entrance acts: `once: true`, `start: 'top 85%'`, `ease: 'expo.out'`.
- Batch lists with `ScrollTrigger.batch(tiles, { start: 'top 90%', once: true, onEnter })`.
- Skip `normalizeScroll`. It is marked experimental (checked 2026-10).
- Cheap option: CSS `animation-timeline: view()` or `scroll()` with `animation-range`, only inside `@supports (animation-timeline: view())`. Reported support at writing: Chrome/Edge 115+, Safari 26+, Firefox pending. Recheck caniuse.
- At most 2 `scrub` acts per page.
- Pointer tilt: `gsap.quickTo(el, 'rotationY', { duration: 0.8, ease: 'power3.out' })`. Only inside `(hover: hover) and (pointer: fine)`. On leave, `clearProps: 'transform'` so text rasterizes sharp at rest.

## SplitText
- GSAP 3.15.0 (checked 2026-10). All plugins are free on npm since 3.13. Read the license text yourself before claiming commercial terms (unverified).
- Use `SplitText.create(el, { type: 'lines', mask: 'lines', autoSplit: true, onSplit })`.
- Animate inside `onSplit` and return the tween. `autoSplit` re-splits on font load or width change and re-syncs the returned tween.
- `aria` defaults to `"auto"`: aria-label on the parent, children hidden. The title is read whole.
- Split by lines. One title per act. Never letter by letter in reading text.

```ts
SplitText.create(title, { type: 'lines', mask: 'lines', autoSplit: true,
  onSplit: (self) => gsap.from(self.lines, { yPercent: 105, duration: 0.9, stagger: 0.08, ease: 'expo.out',
    scrollTrigger: { trigger: title, start: 'top 88%', once: true } }) });
```

## Durations and easing
| Motion | Duration |
|---|---|
| Hover, press, check | 100-150 ms |
| Tab, toggle, expanded row | 150-300 ms |
| Modal, sheet, dropdown | 300-500 ms |
| Authored entrance of an act | 500-800 ms, marketing only |
- Exit is faster than entrance.
- Entrance easing: `cubic-bezier(0.16, 1, 0.3, 1)` (GSAP `expo.out`). Exit: short `ease-in`.
- No bounce or elastic by reflex.
- Animate only `transform` and `opacity` (plus `clip-path` for wipes). Never width, height, top, left, margin, padding.
- `filter`, blur and shadow only in small isolated areas.
- `will-change` only during the animation.
- Stagger only for list items, short total. Use a timeline, not chained delays.
- Parallax: up to 3 layers, about 200px total, never on reading text.
- Reduced motion: reduce, do not disable. Drop translate, parallax and zoom. Keep color, opacity and feedback. Do not zero all transitions globally.

## Composition
- At least 4 effect families per page, never the same in neighbouring sections: pinned scrub, line reveal, `clip-path` wipe, background change, marquee, micro-UI assembly, pointer, light parallax.
- Highlight the current step by color. Do not dim the others with `opacity` (fails contrast).
- Titles, steps, callouts and prices are real server text, not canvas or images.
- Counters only for real numbers, with `tabular-nums`, born at the final value under reduced motion.
- Handshake with CSS through `data-*` flags (`data-ready`, `data-motion`). Set the flag after the thing works. Remove it on teardown.

## Teardown checklist
- Cancel pending timers and idle handles.
- Run every act teardown, then `context.revert()`.
- Remove the ticker callback, restore `lagSmoothing(500, 33)`, `lenis.destroy()`.
- Remove listeners, observers, `data-*` flags and inline styles you set.
- Guard async work with a `disposed` flag checked after every await.
- Return a no-op teardown on any failed setup.

## Anti-patterns
- Same fade-up on every section.
- Opacity-zero start for content above the fold.
- `transition: all`. It animates `visibility` and leaves controls painted.
- Static import of gsap, lenis or three.
- Scroll-jacking, "scroll to explore", decorative "01/06" counters.
- Cursor-following glow, count-up on data, bounce.
- Animation that works only on desktop and carries the page meaning.
- Creating animations outside the context, so nothing reverts.
- Reading `<html>` class changes as theme changes without comparing the theme first. Lenis toggles classes there.

## Tests
- Gate: table test of the pure function with a fake env (answers map keyed by the exported `Q`). Assert `webgl` was not called on phones with `jest.fn()`.
- Probe: fake `document.createElement` returning `{ getContext }`. Assert exact args and one `loseContext`.
- Loader: fake window with a listener map and idle queue. Assert order load, idle, task, and cancellation.
- Component: mock the heavy modules, each returning a `jest.fn()` teardown. Assert nothing loads before `load`, each device row, a live reduced-motion toggle, and teardown called once on unmount.
- Fake timers: dispatch `load`, advance 300 ms for the idle fallback, await two microtasks for the dynamic import.
- First render has full content and no canvas.
- CSS contract: read the real stylesheet, extract the `@supports (animation-timeline: view())` block. Assert no animation rule outside it and that reduced motion zeroes the offset.
- E2E: initial JS lacks the libraries; phone, reduced motion and no-WebGL2 do not request chunks; no long task on first gesture.

## Sources
- https://gsap.com/docs/v3/Plugins/ScrollTrigger/
- https://gsap.com/docs/v3/Plugins/SplitText/
- https://gsap.com/docs/v3/GSAP/gsap.matchMedia()/
- https://gsap.com/docs/v3/GSAP/gsap.context()/
- https://gsap.com/docs/v3/GSAP/gsap.ticker/
- https://gsap.com/resources/React/
- https://github.com/darkroomengineering/lenis
- Attribution: rule lists adapted from scroll-craft (MIT) and gsap-skills (MIT).
