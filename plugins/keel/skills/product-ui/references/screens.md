# Screens: work screens, casual-user screens, anti-patterns

Read when you design a screen whose job is to type, build a screen for an occasional user, review a screen for drift, or set up the guard that keeps the scales.

Values are defaults. A project's own design skill and components win where they are more specific.

## Work screens: the input dominates

A screen whose job is to WRITE (a note, a report, a long form) has one more rule: the text field starts near the top and takes most of the height. Header, metadata and support panels must not push it below the fold.

- The measure that matters: pixels before the first typeable character. Measure before opining.

What pushes the field down, worst first:
1. A closed accordion at the top. It takes the first scroll and informs nothing. Make it a badge with a count that opens the content on demand, showing the worst tone of what is filled.
2. A repeated metadata card. Four time blocks (scheduled, start, duration, timer) say one thing in four formats. One clock and one line beside the name suffice.
3. Card inside card. A bordered, filled form section inside the page card pays padding twice. Label and field suffice.
4. A selector in the header of the section it serves. A select with label and help is taller than the title beside it. Move it to the editor toolbar, in the flow of typing.

More rules:
- Absence of risk takes no space. A safety strip (alert, risk) is visible only when there is something to show. A permanent "none recorded" burns height to say nothing; when empty it goes to on-demand context.
- Steps in 2x2, not stacked, when the format has four steps: two per fold instead of one. Equal height on both columns of a pair, or the one with extra content grows alone and leaves a gap in its neighbor. Go two-column only when both steps exist: in a single-field template, half a width empty is worse than full width.
- A workflow of another moment goes in a modal opened from the toolbar, not a permanent section. A report with its own cycle (draft, final, printed) that most records never use charged everyone height for a few.
- Never wrap a toolbar in a `<label>`. A label points to the first control inside it, and with a formatting toolbar on top that is the Bold button: clicking the field label applied bold instead of focusing the text. A section label does not wrap controls that are not the field.

### Side panel or modal

- A side panel slides from the side over the page without covering what is being written. It is for CONSULTING while documenting (history, case topics, a reference).
- A modal centers and covers the work in progress.
- The line is consult versus type. What the user reads to decide goes in the panel. What the user fills in stays on the page, always. Hiding a field typed every time behind a click makes it worse.

## Casual-user ruler

For someone who opens the product a few times a month to check, pay or sign, sometimes elderly. Work-tool density becomes a dry screen with too many buttons, and the person phones the company. The ruler holds only inside that area and no global token changes; build it as shared pieces, and a screen of the work tool does not import them.

- Navigation: fixed bottom bar on phone and tablet; fixed side rail from the large breakpoint, with the brand on top and the account at the bottom. Page max width about 1360px. Two columns by container query, not window width: the rail eats width and a wide window does not mean wide content.
- Greeting: "Hello, <first name>". With no name the greeting goes without it.
- Each section is a card (border, 12px radius, title). In the work tool a section is only air; here two sections merged with no delimiter.
- The item type reads in brand color with an icon ("Form to answer", "Document to sign"). Exception to color-only-for-decision: here the type is the reader's decision.
- A secondary action is a small icon-only button, 44px. Pointer: tooltip on hover and focus. Touch: a short label under the icon. The full name in `aria-label`. An unnamed icon is guesswork, and a "..." menu hides the action behind one more tap. The main action (Pay, Book) stays a primary button with text.
- A rule that binds an item (cancellation window, reschedule limit) appears ONCE per section, never in each row.
- The next few items may be cards, not a table: the person does not operate the list, they check the next one. History, payments and documents stay tables, with long text wrapping instead of cutting.
- Empty welcomes: an icon and a human sentence inside the section card. Still one line, not an illustrated block.
- No sales banner. Warmth comes from the tone of the copy and the air.
- Measure on delivery: buttons on the first screen, smallest touch target on phone, clipped text, contrast of the type label, horizontal scroll at tablets.

## Product anti-patterns

The generic tells (gradients, equal card grids, glow, numbering, spinners, bounce) are in [design.md](../../web-craft/references/design.md) Anti-patterns. These are the ones specific to a product screen.

- Drift between screens: the same action with a different button variant on two screens, the same data with another name, the same empty state with another geometry. Visible only when comparing screens; an audit compares.
- Modal as the first solution for what fits the screen or a side panel.
- An icon in a colored square above the title of each block. That is the generic feature card. The icon goes beside the label at text size, or not at all.
- A subsetted icon font renders an unlisted icon as TEXT (the ligature name). A new icon: regenerate the subset and bump the font file version, because font files are immutable on the edge and overwriting one never reaches cached users.
- A text-color override on a neutral button to signal meaning ([components.md](components.md)).
- Opacity on a receded row or block ([tables.md](tables.md)).
- A select or menu clipped by `overflow:hidden` (use a portal).
- Text glued to the edge of a button, card or phone screen.
- A JavaScript error on load, even a silent one. A clean console is part of done.

## The guard by spec

A document does not stop regression; a test does. A spec fails when the pattern is broken:

1. Diluted border (`/30` on a border token): ceiling zero, no legitimate case.
2. Font size off the scale in text: a ratchet with a ceiling. Icons are out, as px is right for a glyph.
3. Height or font stamped over the field class: ceiling zero.
4. A guard for the icon subset: a spec that fails when a used icon is not in the subset.

- Ceilings only go down. When you migrate a residue, lower the number in the same change.

## A touched screen moves to the new standard

- No need to migrate the whole product to change one screen, but never write a new screen in the old pattern.
- Screens not yet touched keep the old values until they are.
- Verify on the rendered screen ([verification.md](../../web-craft/references/verification.md)): 390px and 1280px, both themes, and the loading, empty and error states.
