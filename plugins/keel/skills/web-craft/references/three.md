# Three.js

Read when you add a WebGL scene (hero depth layers, background particles) to a marketing page, or when you review one for cost, fallback and teardown.

## When a WebGL scene is justified
- The static page already paints the full composition. The scene is an enhancement on top.
- Never the LCP. The h1 or hero image paints first as HTML/CSS.
- Desktop, fine pointer, no reduced motion, real GPU. Everything else keeps the static page.
- The canvas lives inside a box that already has size, so CLS stays 0.
- It carries no text that search engines or screen readers need.
- Put background effects only where nothing must be read. Fade the effect over text zones.
- Gate and load it as in `motion.md`: pure gate, then `load`, then idle, then dynamic `import()`.
- Import named classes, never `import * as THREE`. Measure the chunk.
- Write down the measured cost and who accepted it.

## Capability probe
- Request WebGL2 only. WebGL1 is gone since r163 (checked 2026-10).
- Probe on a throwaway canvas, lose the context at once.

```ts
export function probeWebGL(doc: Document): 'gpu' | 'software' | 'none' {
  const ask = (opts?: WebGLContextAttributes) => {
    const gl = doc.createElement('canvas').getContext('webgl2', opts) as WebGL2RenderingContext | null;
    gl?.getExtension('WEBGL_lose_context')?.loseContext();
    return !!gl;
  };
  try {
    if (ask({ failIfMajorPerformanceCaveat: true })) return 'gpu';
    return ask() ? 'software' : 'none';
  } catch { return 'none'; }
}
```
- `failIfMajorPerformanceCaveat: true` fails on a software renderer. `'software'` means WebGL exists but is slow.
- Without it, GPU-blocked and headless Chrome render in software (SwiftShader). One measured project saw 70-90 ms long tasks per frame at 4x CPU slowdown, and TBT 130-256 ms versus 4-28 ms with the option.
- Create the renderer with the same option. Heavy scenes need `'gpu'`.
- `'software'` may get a reduced scene: 30 fps, no antialias, DPR 1. Or nothing.
- Probe contexts count against the browser's context limit. Lose them immediately.

## Renderer setup
- Defaults (checked 2026-10): `antialias` false, `powerPreference` 'default', `alpha` false, `failIfMajorPerformanceCaveat` false.
- Typical overlay: `new WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'low-power', failIfMajorPerformanceCaveat: true })`.
- Wrap the constructor in try/catch. On failure return a no-op teardown and leave the static page.
- `setClearColor(0x000000, 0)` for a transparent canvas.
- Pixel ratio: the manual calls `renderer.setPixelRatio(devicePixelRatio)` "strongly NOT RECOMMENDED" (checked 2026-10). It suggests sizing from `clientWidth * dpr` with `setSize(w, h, false)`, rendering at 1x for heavy apps, and a max pixel count cap.
- A cap of about 1.5 is a measured practical choice. `Math.min(dpr, 2)` is a community habit, not official (unverified).
- Cap the pixel count, not only the ratio, on fractional OS scaling.
- `setSize(w, h, false)` leaves the canvas CSS size to the stylesheet.
- Resize with `ResizeObserver` on the host.
- Prefer `renderer.setAnimationLoop()` over manual `requestAnimationFrame` (manual, checked 2026-10). A hand-rolled rAF also works if you cancel it, not just skip frames.
- Color: `outputColorSpace` is `SRGBColorSpace` and `ColorManagement.enabled` is true by default since r152. Set `texture.colorSpace = SRGBColorSpace` on color textures.
- Physically based light units are default since r155 (`useLegacyLights` false).
- `PCFSoftShadowMap` is removed in r186. Use `PCFShadowMap`.
- `Clock` is deprecated since r183. Use `Timer`. Or use `performance.now()`.
- Post-processing needs `OutputPass` for tone mapping.

## Pixel-parity camera (scene locked to the layout)
- Goal: 3D layers start exactly over their HTML twins and diverge only as motion advances.
- Narrow FOV (about 28) keeps perspective distortion low.
- Place the camera at `distance = (height / 2) / tan(FOV * PI / 360)` on the z axis. One world unit equals one CSS pixel at z=0.
- Size each plane with `scale.set(w, h, 1)` from the DOM element's pixel size.
- Measure DOM with `offsetLeft`, `offsetTop`, `offsetWidth`. They ignore CSS transforms, so GSAP and entrance animations do not corrupt them.
- Flip y: three's y points up.
- A layer lifted by `lift` toward the camera looks bigger. Compensate: `perspective = (distance - lift) / distance`, `position.xy = home.xy * perspective`, `scale = perspective`.
- Read scroll progress from `getBoundingClientRect` of the section, not from Lenis. It works with or without Lenis.
- Drive pointer rotation of a root group with a lerp. Time-based easing `1 - exp(-dt * k)` feels equal at 30 and 60 fps.
- Cap `dt` (for example 100 ms) after tab switches.
- Drive data from markup: `data-depth`, `data-aspect`, `data-texture-light`, `data-texture-dark`.

## Shaders and SDF
- Use `ShaderMaterial` for rounded cards: no mask texture needed.
- Signed-distance rounded box gives corner radius and a 1 px border. Anti-alias with `fwidth(d)` and `smoothstep`.
- Fake soft shadow with the same SDF enlarged by a blur radius, `depthWrite: false`, offset behind the card. It conveys distance between layers.
- End the fragment shader with `#include <colorspace_fragment>` for correct sRGB output.
- For particles, compute motion in the vertex shader. After frame 1, update only uniforms (`uTime`, `uPointer`). Zero CPU buffer writes.
- Fake depth of field in the shader: scale `gl_PointSize` and fade alpha by distance from the focal plane.
- Seed any random geometry with a deterministic PRNG so every visit looks the same.
- To keep text legible, pass `vec4` boxes of text zones as uniforms and fade alpha to a floor near them.
- Read theme colors from CSS variables at runtime, with a hard-coded fallback in try/catch.
- Change blending per theme (additive in dark, normal in light), set `material.needsUpdate = true`.
- Re-theme only when the theme actually changed. Compare before acting, since `<html>` mutates often.

## Reveal handshake
- The static composition stays visible until the scene is ready.
- Order: lay out, load textures, `await renderer.compileAsync(scene, camera)`, draw one frame, then set `data-scene="on"` on the stage.
- CSS reacts to the flag: hide the HTML layers, fade the canvas in (about 400 ms).
- Any failure (`catch`) leaves the HTML as it was.
- `compileAsync` uses parallel shader compile where the browser supports it (KHR_parallel_shader_compile). It avoids a first-frame jank.
- Check `disposed` after `compileAsync` and after each texture load.

## Pause and budget
- Pause with an `IntersectionObserver` on the host or section.
- Pause on `document.visibilityState !== 'visible'` via `visibilitychange`.
- Combine both in one `sync()`: run only if visible and the tab is visible. Cancel the frame, do not just skip.
- Throttle software mode to about 30 fps and cap each frame's elapsed time.
- Make the canvas host `pointer-events: none` so it never captures clicks or scroll.
- Window `pointermove` with `{ passive: true }`. Ignore `pointerType === 'touch'`.
- Reduced motion: render one still frame, no loop, redraw only on resize or theme change.
- One context per scene is a cost. Share a context where layering allows.

## Dispose and context loss
- Removing a mesh from the scene does not dispose it.
- Dispose geometries, materials, textures and render targets separately. Disposing a material does not dispose its textures.
- Call `ImageBitmap.close()` yourself.
- Renderers and controls cannot be reused after `dispose()`.
- Teardown order: set `disposed`, cancel the frame, disconnect observers, remove listeners, delete the `data-*` flag, dispose geometry/material/textures, then `renderer.dispose()`, `renderer.forceContextLoss()`, `canvas.remove()`.
- `forceContextLoss()` needs `WEBGL_lose_context`. Official guidance on calling it after `dispose()` was not found (unverified); it is a defensive practice.
- `renderer.dispose()` may have become async in r186 (unverified). Do not rely on either behavior.
- A late async result (texture, compile) after teardown must dispose itself immediately.
- Use `renderer.info` to find leaks.
- `webglcontextlost` / `webglcontextrestored`: no official docs found (unverified). Forum answers from maintainers say listen for `restored` and rebuild your own state. A static fallback makes this optional.

## Static fallback, server side
- Compose the page fully on the server: real images as CSS backgrounds, layered cards, gradient, text.
- Hero image: `image-set()` with AVIF then WebP, a CSS variable per theme, `role="img"`, one `<link rel="preload" as="image">` per breakpoint and theme with `media`.
- Secondary layer images start fetching only after the ready flag, not at first paint.
- The page never waits for WebGL. No loader, no blank box.
- Give the box an aspect ratio so the canvas swap causes no shift.
- Decorative canvas and layers are `aria-hidden`.
- Phones, reduced motion and no-WebGL2 get exactly this.

## r186 facts (checked 2026-10)
- npm `three` 0.186.1. ES modules only: `build/three.js` removed in r161. CommonJS deprecated and minified builds removed in r186 (single source).
- WebGL1 unsupported since r163.
- `Clock` deprecated for `Timer` since r183.
- `renderAsync`/`computeAsync` deprecated in r181. Use `await renderer.init()` with WebGPU.
- `WebGPURenderer` is experimental per the manual. Import from `three/webgpu`, TSL from `three/tsl`. It falls back to a WebGL2 backend.
- `ShaderMaterial`, `RawShaderMaterial`, `onBeforeCompile` and `EffectComposer` are NOT supported by `WebGPURenderer`.
- `WebGLRenderer` stays maintained and recommended for pure WebGL2 apps. Use it for shader-based marketing scenes.
- Addons: `import { X } from 'three/addons/...'`.
- Dates for r186 conflict between sources (unverified). Do not cite one.

## Anti-patterns
- Canvas as the LCP element or the only carrier of text.
- `setPixelRatio(devicePixelRatio)` uncapped.
- No `failIfMajorPerformanceCaveat`, so software GL burns the main thread.
- `import * as THREE` in a hero chunk.
- Hiding the HTML before the first frame is drawn.
- Render loop that runs off-screen or in a hidden tab.
- `new Clock()` in new code.
- Skipping dispose on unmount, or leaking per-theme textures.
- Adding a second probe or renderer per component.
- A decorative object instead of real product UI.
- Reading scroll from Lenis when the DOM rect works without it.

## Tests
- Mock the scene module in component tests. Assert the chunk is not requested on phone, reduced motion, and no-WebGL2, and that teardown runs once.
- Spy `HTMLCanvasElement.prototype.getContext`, keyed on `failIfMajorPerformanceCaveat`, to simulate gpu, software, none.
- Probe unit test: fake document. Assert exact args and one `loseContext`.
- First render has the static composition and no canvas.
- Real scene code is hard to unit test in jsdom. Cover it with a lab run in a real browser: frames, long tasks, LCP, CLS.
- Pure helpers (camera distance, perspective compensation, easing) are plain unit tests.

## Sources
- https://threejs.org/manual/pages/responsive.html
- https://threejs.org/manual/pages/how-to-dispose-of-objects.html
- https://threejs.org/manual/pages/webgpurenderer.html
- https://threejs.org/manual/pages/color-management.html
- https://threejs.org/manual/pages/installation.html
- https://threejs.org/docs/pages/WebGLRenderer.html
- https://github.com/mrdoob/three.js/wiki/Migration-Guide
- Attribution: rule lists adapted from scroll-craft (MIT) and gsap-skills (MIT).
