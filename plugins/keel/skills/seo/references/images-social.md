# Images, Open Graph and Twitter cards

Read when you touch image `alt`, file names, formats, `srcset`, hero or content images, Open Graph or Twitter cards, or share previews.

Time-sensitive facts carry "(checked 2026-10)". Re-verify before hardcoding.

## Image SEO

- `alt` is the most important image attribute. Describe what the image shows; no keyword stuffing.
- Decorative images use `alt=""`, only when the image tells nothing.
- A product screenshot informs: describe the screen ("weekly agenda with six confirmed appointments"), never "system screenshot".
- File names: short, descriptive, translated when the page is translated.
- Indexable formats: BMP, GIF, JPEG, PNG, WebP, SVG, AVIF (AVIF since 2024-08), with the extension matching the real type.
- Google indexes `<img>` (also inside `<picture>`), not CSS images. A hero or product image that must be indexed is an `<img>`, never a CSS `background-image`. A theme-dependent CSS image does not enter Google Images; accept it only when indexing the image is not a goal.
- Responsive: `srcset` with `sizes`, or `<picture>`, always with a fallback `<img src>`.
- `sizes` discounts the container padding: an image inside a `px-6` section is `calc(100vw - 48px)` on a phone. With `100vw` a 412 px device downloads the next, larger variant.
- Serve variants at the box's aspect ratio, not only its width. A landscape image in a portrait box with `object-cover` makes the browser scale by height and rasterize about 3x the area; `sizes="100vw"` lies in that case.
- Lazy-load only below the fold, and never depend on scroll or click to load.
- LCP image priority, preload and format rules live in [performance](../../web-craft/references/performance.md).

## Weight (working numbers, not Google rules)

- Hero up to about 200 KB; content image up to about 100 KB; thumbnail up to about 50 KB.
- AVIF before WebP before JPEG where the tooling allows; a phone hero is often a fraction of the desktop one.

## Safety of product images

- Product screenshots use synthetic seed data only: invented patient or customer names, no real national ID, no real clinical text, no real customer data (privacy law).
- A file in a `public/` folder ships to production whether referenced or not. Audit captures and drafts live outside it.

## Open Graph and Twitter/X

- OG required: `og:title`, `og:type`, `og:image`, `og:url`. Optional: `og:description`, `og:site_name`, `og:locale`, `og:image:width`, `og:image:height`, `og:image:alt`. Set `og:image:alt` whenever `og:image` is set.
- `og:url` equals the canonical.
- Every public page declares its own OG. In Next.js a page's `openGraph` replaces the layout's wholesale: OG without an image ships no preview ([crawl-index](crawl-index.md)).
- Share image: 1200x630, JPEG, `alt` in the page language, about 300 KB or less (house heuristic: messengers drop large previews). Google gives no official `og:image` pixel size.
- Version the file name (`card.v3.jpg`): messengers cache previews by image URL, and the same name keeps the old art for whoever shared before.
- After deploy, force a re-scrape: Facebook Sharing Debugger, LinkedIn Post Inspector. Check the card as the crawler sees it, not the browser.
- Static art over a generated OG image (`opengraph-image`-style routes) when the card has a canvas or a real screenshot: the generator renderer does not paint canvas, and generating on request spends CPU on every preview bot for a card that changes only when the hero changes. Changed the hero: re-capture the art and bump the version.
- A profile page shares the profile photo or logo, with a small-card fallback.
- Twitter/X (secondary, unverified; official pages were inaccessible): `twitter:card` required (`summary_large_image` or `summary`), no OG fallback for that tag; `twitter:title` up to 70 chars, `twitter:description` 200, `twitter:image:alt` 420; large card 2:1, min 300x157, max 4096x4096, under 5 MB; other tags fall back to OG.

## Anti-patterns

- An indexable hero as CSS background; a lazy LCP image.
- `sizes="100vw"` inside a padded container.
- A landscape image forced into a portrait box.
- A page with `openGraph` and no image; the same file name for a new card.
- Screenshots with real customer data; drafts in a public folder.

## Sources

- Google Search Central: `https://developers.google.com/search/docs/appearance/google-images`, `…/crawling-indexing/javascript/lazy-loading`; blog 2024-08-30 (AVIF)
- https://ogp.me/
- https://web.dev/articles/optimize-lcp
