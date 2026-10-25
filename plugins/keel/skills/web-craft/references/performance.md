# Performance for marketing sites

Read when you add or change a hero, image, font, script, animation or 3D scene on a public page, or when LCP, INP or CLS regress.

## Budgets and thresholds (checked 2026-10)

| Metric | Good | Notes |
|---|---|---|
| LCP | 2.5 s or less | Needs improvement 2.5 to 4.0 s; poor over 4.0 s |
| INP | 200 ms or less | Replaced FID in March 2024 |
| CLS | 0.1 or less | |

- A page passes only if all three are good at the 75th percentile of page loads, split by mobile and desktop.
- The sources did not confirm INP and CLS "poor" cutoffs in text.
- Google recommends good Core Web Vitals and states no ranking weight.
- Googlebot fetches only the first 2 MB of an HTML file (uncompressed) and has the same limit per subresource. Content past it is ignored.
- A new section must not worsen median LCP against baseline, push CLS above 0.1, or put new JS on the critical path.
- Do not read cookies, headers or nonces in a page that must stay edge-cacheable.

## Static-first hero

- Compose the hero on the server: real images as CSS backgrounds or `<img>`, layered cards, gradient, text. It is complete without JS.
- The LCP element is static (an image or the h1). It never waits for JS or WebGL.
- Every motion or 3D piece is a layer loaded after load. It mounts invisibly and flips a `data-*` flag only after its first frame is drawn. CSS reacts to the flag.
- Any failure leaves the static composition. Wrap renderer creation in try/catch and `.catch(() => undefined)` the async chain.
- Reserve space: aspect ratio on the frame, canvases absolutely positioned in boxes that already have size. CLS stays 0.
- Secondary images start downloading only after load: give them no `background-image` until a ready flag is set.
- Animate only what is below the fold. Animating what the visitor already sees reads as a flash.
- Cycling images: pure CSS timing, enabled after `load`, never with reduced motion (so overlay images are never fetched).

## Fonts

- Check on the rendered page that the declared font arrived, not the fallback.
- Re-split or re-measure text effects when the font arrives (a split-text `autoSplit` style option, or a layout refresh).
- Source reports did not cover a font loading strategy. Pick one and measure LCP and CLS before and after.

## Images

- The hero screenshot is usually the LCP element.
- Formats: AVIF with WebP fallback. Google Images indexes AVIF, WebP, JPEG, PNG, GIF, BMP and SVG.
- Serve a variant per width with the box's aspect ratio.
- LCP image: `fetchpriority="high"`, never lazy.
- Below the fold: `loading="lazy"`. An image under `display:none` is not downloaded.
- Responsive backgrounds: `image-set()` with `type('image/avif')` and `type('image/webp')` entries at 1x and 2x, in a CSS custom property per theme. Add `role="img"` and a label.
- Google indexes `<img>` (also inside `<picture>`), not CSS images. If the image must be indexed, use `<img>` or `<picture>`.
- Preload per theme and breakpoint with literal tags: `<link rel="preload" as="image" type="image/avif" imagesrcset="... 1x, ... 2x" media="(min-width:768px) and (prefers-color-scheme:dark)" fetchpriority="high">`.
- One link per breakpoint x theme; the `media` attribute makes the browser fetch only the match. A single unconditioned preload cost 3.8 s of LCP in a lab test, because the other theme downloaded too.
- Do not preload a below-the-fold phone image. An 86 KB high-priority preload stole bandwidth from CSS and fonts on 4G.
- Emit preload as a literal `<link>` in served HTML; verify it appears in the page source, not only in a framework hint.
- A visitor whose stored theme differs from the device theme loads the correct variant through CSS without preload.
- CSS-only theme switching fetches only the matching variant and runs no JS. A client component that swaps the image on mount causes a flash on the LCP element and a second download.
- Version the filename when a screenshot changes.

## Loading JS

- Heavy libraries (animation, smooth scroll, 3D) are out of the initial bundle. Load with dynamic `import()` after `window.load` and an idle callback.
- Idle: `requestIdleCallback(task, { timeout: 2000 })`, or `setTimeout(200)` where unsupported. Run at once if `readyState` is already `complete`. Return a cancel function.
- Gate before download. A pure function decides from media queries and a WebGL probe who gets what; the chunk of a blocked device is never requested.
- Probe WebGL lazily; it costs a GPU context. Lose the probe context at once.
- Import only named classes (never `import * as THREE`). The build must show a separate chunk per library.
- Render-less client components decide and import; the module returns a teardown.
- Handle async teardown races: a `disposed` flag checked after each await; run cleanup at once if already disposed.

## Main-thread work

- Split work per task. Create below-the-fold effects one per `setTimeout(..., 0)` task and refresh layout once at the end. Mounted together they summed to one long task.
- Animate only `transform` and `opacity`.
- Prefer CSS scroll-driven animation (inside `@supports`, visible state outside it) for the base layer.
- Compile shaders with `compileAsync()` before the first frame.
- After the last frame of a tilt, clear the transform so text rasterizes sharp.
- Remove an effect if it makes LCP, CLS or TBT worse beyond run-to-run variance.

## WebGL budget

- Require a real GPU: request `getContext('webgl2', { failIfMajorPerformanceCaveat: true })` and create the renderer with the same option. Without it, software rendering (SwiftShader) turned each frame into a 70 to 90 ms long task. Lab TBT was 130 to 256 ms without the option and 4 to 28 ms with it (measured 2026-10 in one project, relative evidence).
- Three.js r163 and later does not render on WebGL1.
- Desktop with mouse and motion only.
- Cap DPR at `Math.min(devicePixelRatio, 1.5)`.
- Use `powerPreference: 'low-power'`.
- Pause off-viewport with `IntersectionObserver` and when hidden with `visibilitychange`. Cancel the requestAnimationFrame, do not only skip.
- Software fallback (if you accept it): 30 fps, no antialias, DPR 1. Smooth the pointer by elapsed time, not per frame, so 30 and 60 fps feel equal.
- Do all particle motion in the vertex shader; write no CPU buffers after frame 1.
- Dispose geometry, material, textures and renderer; call `forceContextLoss()` and remove the canvas.
- A theme observer on `<html>` must act only when the theme really changed; smooth-scroll libraries can toggle classes on `<html>` every frame.
- Write the measured cost and who accepted it. One project accepted +126 to +199 ms TBT at 1440 knowingly.

## Measuring

- Lab (Lighthouse, scripted runs) and field differ. Lab data does not replace field data.
- Field sources: CrUX, PageSpeed Insights, Search Console report.
- Lighthouse cannot measure INP; it uses TBT as a proxy.
- Lab protocol: 3 or more runs, at 390 and 1440 wide, same machine, CPU 4x throttle, before and after; compare medians. Interleave A/B runs.
- In the page, use `PerformanceObserver` for `largest-contentful-paint`, `layout-shift` and `longtask`.
- Measure the production build.
- Measure at the first gesture too: a long task there is an INP risk.

## Anti-patterns

- Hiding content with `opacity-0` until a script runs: loses content when JS fails, delays LCP.
- A client component choosing the LCP image after mount.
- A single preload for both themes or all breakpoints.
- Lazy-loading the LCP image.
- Importing a 3D or animation library in the initial bundle.
- Letting a canvas change layout size after load.
- Running render loops off-screen or in hidden tabs.
- No DPR cap; no dispose.
- Requesting WebGL for phones.
- Judging by the dev server or by lab alone.
- Shipping `markers` or debug flags.

## Sources

Core Web Vitals and image facts come from web.dev and Google Search documentation (checked 2026-10). Budget, hero and WebGL rules come from observed practice on a production marketing site, generalized.
