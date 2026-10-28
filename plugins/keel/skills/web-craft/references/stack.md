# Modern stack recipe

Read when you build, redesign or modernize a public page and lay down its motion and 3D layer: what the delivery contains by default, the files, the markup contract, the act for each section and the hero scene.

## Default delivery

A new site, a redesign or a request to "modernize" delivers all of this without being asked. Static first is how each layer is built, never a reason to leave one out. Dropping a layer is the owner's call: ask, with its cost.

| Layer | Who gets it | What |
|---|---|---|
| Brand | everyone | The existing palette, gradients, type and signature elements, refined (design.md "Keep the brand") |
| CSS | everyone | Scroll-driven reveal inside `@supports (animation-timeline: view())`, hover states, a slow decorative drift, all off or opacity-only under reduced motion |
| GSAP + ScrollTrigger + SplitText | desktop, no reduced motion | One act per section from the catalog below, at least 4 families on the page |
| Parallax | desktop, no reduced motion | Up to 3 layers on decorative shapes and image frames, about 200px total, never on reading text |
| Lenis | desktop with mouse | Smooth scroll on the GSAP ticker |
| Pointer tilt | desktop with mouse | `quickTo` on the hero composition, `clearProps` on leave |
| Three.js | desktop with mouse and GPU; still frame under reduced motion | One scene behind the hero, tied to the brand (see "Hero scene") |

Keep what already works for the business: the contact button, badges of credentials, the photo. A floating contact action stays floating.

## Files

One feature folder next to the page sections. Names are a suggestion; the split is the point.

| File | Does |
|---|---|
| `motion-gate.ts` | Pure: queries `Q`, `planMotion(env)`, `probeWebGL(doc)`, `afterLoadAndIdle(win, task)` returning a cancel. Unit tested |
| `motion-boot.tsx` | `'use client'`, renders `null`, mounted once after the last section. Plans, waits, imports, keeps every teardown, listens to reduced-motion `change` |
| `motion-engine.ts` | Registers plugins at module scope, one `gsap.context`, Lenis, the acts one per task. Returns one teardown |
| `hero-scene.ts` | `mountHeroScene(host, mode)` returning a teardown. Imports named three classes only |
| global stylesheet | The CSS contract: visible by default, flags, `@supports` block, reduced motion |

Boot, the shape that works in React 19 / Next App Router:

```tsx
'use client';
export function MotionBoot() {
  useEffect(() => {
    let disposed = false;
    const teardowns: Array<() => void> = [];
    const keep = (t: () => void) => (disposed ? t() : teardowns.push(t));
    const plan = planMotion({ matchMedia: (q) => window.matchMedia(q), webgl: () => probeWebGL(document) });
    const cancel = afterLoadAndIdle(window, () => {
      if (plan.gsap) void import('./motion-engine').then((m) => keep(m.startMotion({ lenis: plan.lenis })));
      const host = document.querySelector<HTMLElement>('[data-scene-host]');
      if (host && plan.ambient) void import('./hero-scene').then((m) => keep(m.mountHeroScene(host, plan.ambient!)));
    });
    const reduced = window.matchMedia(Q.reduced);
    const onChange = () => { if (reduced.matches) { teardowns.splice(0).forEach((t) => t()); } };
    reduced.addEventListener('change', onChange);
    return () => { disposed = true; cancel(); reduced.removeEventListener('change', onChange); teardowns.splice(0).forEach((t) => t()); };
  }, []);
  return null;
}
```

Engine skeleton:

```ts
gsap.registerPlugin(ScrollTrigger, SplitText);
const belowTheFold = (els: Element[]) => els.filter((el) => el.getBoundingClientRect().top > innerHeight);

export function startMotion({ lenis: smooth }: { lenis: boolean }) {
  const context = gsap.context(() => undefined);
  const undo: Array<() => void> = [];
  let lenis: Lenis | null = null;
  const tick = (t: number) => lenis?.raf(t * 1000);
  if (smooth) {
    lenis = new Lenis({ autoRaf: false, anchors: true, lerp: 0.2, allowNestedScroll: true,
      virtualScroll: ({ event }) => !event.defaultPrevented && getComputedStyle(document.documentElement).overflowY !== 'hidden' });
    lenis.on('scroll', ScrollTrigger.update);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);
  }
  context.add(heroAct);                       // synchronous, above the fold
  ScrollTrigger.refresh();
  const acts = [titlesAct, listAct, stepsAct, imageAct, ctaAct];
  let pending = 0;
  const next = (i: number) => { pending = window.setTimeout(() => {
    if (i < acts.length) { context.add(() => { const t = acts[i](); if (t) undo.push(t); }); next(i + 1); }
    else ScrollTrigger.refresh();
  }, 0); };
  next(0);
  document.documentElement.dataset.motion = 'on';
  return () => {
    clearTimeout(pending);
    undo.splice(0).forEach((t) => t());
    context.revert();
    gsap.ticker.remove(tick);
    gsap.ticker.lagSmoothing(500, 33);
    lenis?.destroy();
    delete document.documentElement.dataset.motion;
  };
}
```

## Markup contract

JS finds elements by `data-*`, never by styling classes. Server HTML carries them; CSS shows everything without them.

| Attribute | On | Used by |
|---|---|---|
| `data-hero-stage` | hero composition | tilt root, `data-ready` flag |
| `data-layer` + `data-depth="0.2"` | decorative shapes, image frame | parallax scrub, `y: -200 * depth` |
| `data-split-title` | section `h2` below the fold | SplitText line reveal |
| `data-batch` | each item of a list or grid | `ScrollTrigger.batch` |
| `data-steps` / `data-step` / `data-progress` | sticky method or flow section | scrubbed children, progress `scaleX` |
| `data-wipe` | a photo below the fold | `clip-path` inset wipe |
| `data-scene-host` | sized box behind the hero | the canvas, `data-scene="on"` when drawn |
| `data-motion="on"` on `<html>` | set by the engine | CSS drops its own fallback animation |

## Act catalog

Pick by section. Never the same family in neighbouring sections.

| Section | Act | Family |
|---|---|---|
| Hero | Layers parallax on scroll, pointer tilt, the scene behind | parallax, pointer, 3D |
| Pain points, services, list | `batch` from `y: 40`, short stagger, `once` | list entrance |
| Method, steps, how it works | CSS sticky frame, scrub its children, highlight the current step by color, progress rail | pinned scrub |
| Statement, quote, verse | SplitText lines from `yPercent: 105`, mask lines | line reveal |
| About, photo | `clip-path: inset(0 0 100% 0)` to `inset(0)`, frame decor in parallax | wipe |
| Booking, form, app UI | Frame entrance once; never animate fields, slots or prices | micro-UI assembly |
| Final CTA | `rotationX` entrance or background color change on enter | background change |
| FAQ, footer | CSS only | none |

## Hero scene

- One concept that the brand already suggests: its shapes, its colors, its subject. Examples: soft organic blobs or petals in the brand palette for care and wellbeing, a particle field that gathers into the brand mark, a helix or cells for health, light through glass for finance. A random torus is a decorative object and fails.
- Colors come from CSS tokens at runtime (`getComputedStyle`), with a fallback; re-theme only when the theme really changed.
- Behind text: fade alpha near the text box (pass it as a `vec4` uniform), `pointer-events: none`, `aria-hidden`.
- Motion in the vertex shader; after frame 1 only uniforms change (`uTime`, `uPointer`, `uScroll`).
- Mode from the gate: GPU gets the full scene; software gets 30 fps, DPR 1, no antialias, or a still; reduced motion gets one still frame; none keeps the static CSS glows.
- Renderer, loop, pause, dispose and the reveal handshake: [three](three.md).

## Delivery check

Run these on the rendered page before saying done ([verification](verification.md)):
- Desktop with GPU: `html.lenis` present, `ScrollTrigger.getAll().length > 0`, canvas drawn and `data-scene="on"`, no long task on the first wheel.
- Phone and reduced motion: no gsap, lenis or three chunk requested; content complete.
- JS disabled: every section visible, no blank block.
- Tests in the repo: gate table, probe, loader order, boot component (mocked engine and scene, teardown once, live reduced-motion toggle), e2e chunk markers per device ([motion](motion.md) "Tests").
