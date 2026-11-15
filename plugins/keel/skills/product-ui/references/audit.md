# UI audit rubric

Read when you audit, review or score the UI of any surface: a product screen, a dashboard, a casual-user area or a public page.

An audit documents; it does not fix. It points, with evidence, where the screen breaks its ruler, and the fix becomes work items.

## Choose the ruler

- Work tool, casual-user and marketing surfaces have their own rulers: [foundations.md](foundations.md) Rulers per surface.
- Auditing a surface by another's ruler gives false findings. Density is a virtue in a work tool and a defect on a home page.

## Five dimensions, 0 to 4

| Dimension | 0 | 2 | 4 |
|---|---|---|---|
| Accessibility (AA contrast, visible focus, tab order, semantics, `alt`, field labels, announced errors, reduced motion) | Fails WCAG A, no keyboard | Partial effort, gaps that block someone | Full AA; axe clean across measured widths and themes |
| Performance (what paints above the fold, animation that forces layout, images without ratio, JS on the critical path) | Freezes or shifts layout | Parts optimized, parts not | Fast and lean; on a public page, lab LCP and CLS in target |
| Theme (tokens instead of loose color, light and dark with contrast, nothing that does not switch) | Fixed color everywhere | Tokens with visible holes in one theme | Both themes right; any fixed-color section is a recorded exception |
| Responsive (390px, tablet, 1280+, 44px touch target, no horizontal scroll, text grows without breaking) | Desktop only | Works on phone with rough edges | Fluid; right targets and gestures; zero horizontal scroll |
| Ruler fidelity (the surface's ruler, the anti-patterns, coherence between screens) | Systemic deviation | Several confirmed deviations | Coherent and intentional |

- Scores 1 and 3 sit between anchors. Each score cites evidence (measurement, capture, `file:line`).
- Fixed-color section: allowed when the exception is recorded (which section, why, contrast measured on it). An unrecorded one scores as a hole in Theme.
- A brand gradient that the brand owns is not an AI tell. Generic-look findings ([design.md](../../web-craft/references/design.md) Anti-patterns) apply to patterns nobody chose, not to the brand's own.

## Total /20

| Band | Meaning |
|---|---|
| 18-20 | Polish only |
| 14-17 | Good; attack the weak dimensions |
| 10-13 | Significant work |
| 6-9 | Major overhaul |
| 0-5 | Foundation problem |

## Severity

| Level | When | Deadline |
|---|---|---|
| P0 | Blocks the task (a button that does not respond, invisible content, unreadable text) | Now |
| P1 | Greatly hinders or violates WCAG AA | Before publishing |
| P2 | Annoys but has a workaround | Next round |
| P3 | Polish | If time remains; keep few |

- On a public page, the generic-look severity (P0 layperson notices, P1 designer, P2 polish) also applies ([design.md](../../web-craft/references/design.md)).
- An accessibility failure rises one level whatever its looks.

## Report format

1. Surface, ruler applied, date, commit sha, environment (port, build), widths, themes and languages measured.
2. Table of the five scores with the key finding of each, and the total with its band.
3. Findings by severity: name and level, where (`file:line` or screen), user impact, rule broken, specific fix.
4. Repeating patterns (the same defect on several screens).
5. What is good, so the next person does not undo it.
6. Recommended order of attack.
7. What was NOT verified, and why (device gesture, a real screen reader, OS zoom).

- Save the report as a dated file (`audit-YYYY-MM-DD.md`) outside tracked and public folders, with the captures beside it. Never in a public directory.
- Run the checks on the rendered screen ([verification.md](../../web-craft/references/verification.md)).

## Do not

- A finding without impact.
- Generic advice ("improve contrast"). Give the token, the pair and the ratio.
- Everything P0.
- A finding not checked on the rendered screen.
- Fix while auditing.

## Sources

Dimensions, bands, severity and report format adapt impeccable (Apache-2.0). Keep this attribution and license.
