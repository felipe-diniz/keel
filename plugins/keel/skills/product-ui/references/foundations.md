# Foundations: scales and tokens

Read when you set or check type, spacing, radius, color, theme, transitions, page container, loading or empty states of a product screen.

All numbers are defaults. A project's own design system or tokens win where they are more specific. Keep one brand across surfaces (palette, fonts, tokens in both themes).

## Rulers per surface

| Surface | Ruler |
|---|---|
| Work tool (used all shift) | Dense: read more data per screen, compare without scrolling, spot the exception at a glance. Page title 20px max, color only for decision, tables, 6px radius |
| Casual user (opens a few times a month to check, pay, sign) | Air, sectioned cards, fewer and clearer actions: [screens.md](screens.md) |
| Marketing page | Display type, authored motion: [design.md](../../web-craft/references/design.md) |

- Audit and build with the surface's ruler. Density is a virtue in a work tool and a defect on a home page ([audit.md](audit.md)).
- If the document and the taste of the moment disagree, the document wins.

## Hierarchy by weight and position

- Emphasis comes from weight (500 to 600) or position, never from a 32px title.
- Page title never exceeds 20px.

## Type scale (px)

| Role | Size | Weight |
|---|---|---|
| Page title | 20px | 600 |
| Section / card title | 16px | 600 |
| Body, table data | 14px | 400 (500 on the anchor column) |
| Field label, column header, caption | 12px | 600, uppercase, tracking 0.06em |
| Badge, counter | 11px | 600 |

- No arbitrary size (`17px`, `0.72rem`). If it does not fit the table, the layout is the problem.
- Icon glyphs are exempt: px is the right unit for a glyph.
- Root not 16px: `rem` scales with it (14px root: `0.875rem` gives 12.25px, not 14px). Lock the scale in px in the theme so each class delivers the table value. Touch targets are in px too.
- The phone font floor for editable fields ([forms.md](../../web-platform/references/forms.md) §Structure) is set in px when the root is not 16px: `1rem` on a 14px root gives 14px and iOS zooms on focus. Rich editors follow the same floor.
- Never stamp a smaller size over the field class.
- Numbers in columns: [design.md](../../web-craft/references/design.md) (`tabular-nums`).

## Spacing

- Inside a block: 4, 8, 12, 16.
- Between blocks: 24, 32, 48.
- Nothing else.

## Radius

| Element | Radius |
|---|---|
| Row, cell, badge, chip | 4px |
| Card, container, field, button | 6px |
| Modal, dropdown, sheet (really float) | 10px |
| Avatar, counter bubble | full |

- Large radius everywhere is a generic tell. No `2xl` or `3xl` on screen furniture.
- Casual-user surfaces go one named step up (12px section card). Nothing else leaves the scale.

## Color

- Color only for decision or exception. Neutral interface, color is signal.
- Accent (primary button, active item, focus): 1 or 2 points per screen. Not on backgrounds, card borders, decorative icons or body text.
- Tonal button pairs are furniture and do not count as accent points.
- Status colors (success, warning, error) mean real data state, never decoration, and are separate from the brand accent: "paid" green is not the brand green.
- If everything is colored, nothing is flagged. The confirmed item need not shout; the pending and the late do.
- Surfaces are opaque. Translucency only on temporary overlays (dropdown, sheet, modal backdrop).
- Hover is a surface too: the next luminosity step, not a translucent veil.
- Elevation is a 1px border plus one luminosity step. Shadow only for floating layers.
- Use the border token whole. Never dilute it (`/30`): it is already subtle (about 11% light, 12% dark) and a diluted one erases the edge.
- Other color rules (status never by color alone, gray on a colored surface, opacity on inactive items): [design.md](../../web-craft/references/design.md).

## Dark mode

- Base about `#10151c`, text about `#e4e8ee`. Not pure black, not pure white: both extremes together tire a long shift.
- Elevation climbs by luminosity: surface, elevated, container-high, container-highest, each a short step.
- Saturated color on a large area tires: accent as a point, neutral as an area.
- AA in both themes, measured on the rendered background ([verification.md](../../web-craft/references/verification.md)).

## Transitions

- `transition-colors`, never `transition-all` (why: web-craft [design.md](../../web-craft/references/design.md)).
- A panel hidden by `visibility` also gets `pointer-events:none`: during the transition it is still visible, so still clickable.
- Exception: an overlay that animates its own entry or exit (modal, dropdown) may transition `opacity` and `transform`. Use `transition-opacity`, not `all`.
- Hover is a color change, never `translateY` or shadow.
- Durations, easing and reduced motion: [motion.md](../../web-craft/references/motion.md).

## One page container

- Every page opens with the same container: centered, same max width (default 1600px), same vertical gap, bottom padding, content in a page card.
- Two max widths make the list ruler jump when navigating between screens.
- A touched screen adopts it. Exceptions are named and few (a wall display).

## Loading

Four phases, four owners. Each one needs its fallback, or the screen paints a wrong state.

| Phase | Owner |
|---|---|
| Server, before the page streams | Route loader. Gone once the client island mounts |
| Streamed part | Suspense fallback |
| After hydration, data refetch | The table's or list's own loading state |
| Client island deciding from fetched data (a feature gate, a permission) | Its own skeleton |

- The skeleton uses the container and the real geometry of the screen. Typical miss: a list becomes a 32px-row table but the loader still paints 85px cards with avatars.
- Skeleton only over the results area. Filters, title and toolbar stay put.
- A gate decided on client data shows the skeleton until the answer arrives. Never paint "you do not have it" or the sales pitch while loading. The gate is display only; the server enforces.
- No spinner in the middle of content.

## Empty states

- One line, never a block or a card for "no records".
- Say which kind of empty it is: [copy.md](copy.md).
