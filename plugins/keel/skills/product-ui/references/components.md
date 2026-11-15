# Components: buttons, fields, modals, dropdowns

Read when you build or review a button, a field, a form layout, a toggle and its helper text, a modal, a confirmation, a side panel or a dropdown.

Values are defaults. A project's own components and tokens win where they are more specific.

## Buttons

- Rectangular, 6px radius, 600 weight, no shadow, no displacement on hover.
- Height equals field height: 44px on phone, 36px on desktop. Button and field share one line in every toolbar; different heights misalign it.
- Hover is a color change only (a `translateY` shakes the action bar).
- Every button is filled. Hierarchy comes in two steps of one hue: the light saturated step (primary) and the tonal step (dark container hue with light on-color text, opaque). Outline-only reads as a label over a panel ([design.md](../../web-craft/references/design.md)).

| Variant | Form |
|---|---|
| primary | Saturated brand fill, no border. The main action |
| secondary | Tonal brand: container fill, on-container text, 1px border of the same hue. Every action that is not the main one |
| danger | Tonal red. Destroys or cancels something |
| caution | Tonal orange. Does not destroy but changes a rule or state (mark as missed, pause) |
| cancel | Neutral gray (neutral container, outline border). The exit of a modal or panel (Cancel, Close, Back), and only that |
| icon | Square (36px desktop, 44px phone), 6px radius, 1px border |

- Semantics come from the variant, never from text color on a neutral button. A secondary with orange text reads as green with orange writing.
- Next to a confirm (brand or red), gray cancel yields weight to the one that decides.
- Tonal pairs are their own opaque tokens, defined in both themes, with the text contrast measured (AA at least). A translucent error container is for hover veils and notice backgrounds, never a button surface.

## Fields

- Height 44px on phone, 36px from the small breakpoint up, in px: touch targets are physical and must not shrink with the type base.
- A compact variant (40/32px) only in dense toolbars.
- Never stamp height, padding or font size over the field class. Utilities beat the component layer and undo the standard and the anti-zoom floor.
- Label fixed above the field. Placeholder is an example ([copy.md](copy.md)).

## Form layout

- A work form fills horizontally. A tall narrow modal forces scrolling inside a box that already covers the screen.
- Split into zones with a purpose side by side (who, when, billing), not two columns that cut a list in half.
- Each zone absorbs its own warnings, beside the field that caused it. This keeps the form from growing and shifting on each choice. A summary on top may exist, never as the only indicator.
- A rule that was not violated takes no space. A permanent "rules for this item" block is noise: a short summary that expands only on a real violation.
- One consent ("proceed anyway") appears once, never duplicated between client pre-validation and the server error.

## Toggles and switches

- Helper text opens with the current state, then its effect, then what the other position does: "On: sends X. Off: sends nothing. Turn on to ...". The off sentence ends with the invitation.
- Never open with a loose behavior ("Does not create a charge"). Under an off switch the reader takes it as what happens if they turn it on.
- A trigger that looks at the past states its cutoff ("applies to those booked after you turn it on"). An automation silent because of old data becomes a support ticket, not a bug.
- A toggle that depends on another control: one sentence, derived from both states by a pure function, with the combination now in effect and no conditional ("The survey goes by WhatsApp. Anyone without WhatsApp gets nothing; e-mail is used only if you turn WhatsApp off."). It changes the instant a switch changes, before save, and is the same on every screen that shows the pair.
- Check in the code that each combination is true before fixing the sentence.

## Modals

| Role | Width | For |
|---|---|---|
| Confirmation | 448px | Yes/no, short notice, one question |
| Form | 784px | Most cases |
| Wide form | 1120px | Scheduling, payment split, import |

- Three widths as defaults. A touched screen adopts the scale; do not sweep all at once.
- The footer is a prop of the modal, never a `div` drawn at the end of the body. Pass only the buttons. The component owns the frame: 1px divider edge to edge, a background one step below the body, its own padding, stacking on phone.
- The divider reaches the edges because the footer lives outside the container that carries side padding.
- The footer stays fixed and only the body scrolls: confirm is found without scrolling a tall modal.
- Default aligns right. Destructive left and confirm right is one child: a full-width flex row with space between.
- Trap: a `type="submit"` button moved to the footer stops submitting, as it is no longer inside the form. Give the `<form>` an `id` and the button `form="id"`.
- Destructive confirmation is a modal, never in the row. A question and two buttons squeezed beside the opener break the row and read as a patch. The modal isolates the decision, shows the effect and keeps its error inside. Doubly so when the action reaches people not on screen.
- Inside a modal that already is the flow (a refund in a payment modal), an in-place confirmation panel with title, effect and its own button row is acceptable.
- A modal is not the first solution. If it fits on the screen or in a side panel, put it there ([screens.md](screens.md)).

## Dropdowns

- A custom select only when it solves a real problem. The native list is drawn by the OS: opens white in a dark theme, in the OS font and spacing, and on phones becomes the system wheel.
- A custom select inherits the field height, opens through a portal (a parent `overflow:hidden` clips it) and becomes a bottom sheet on phone.
- Label the trigger, not the hidden native select ([accessibility.md](../../web-platform/references/accessibility.md) §Names and roles). A custom trigger is not a native control; do not rely on `required`.
- The platform path is the native customizable select (`appearance: base-select`). Support status: [ui-primitives.md](../../web-platform/references/ui-primitives.md).

## Icons

- An icon font is text in the accessible name: naming rules in [accessibility.md](../../web-platform/references/accessibility.md) §Names and roles.
- Icon without a name is guesswork. Icon-only controls carry a tooltip, label or `aria-label` ([screens.md](screens.md)).
