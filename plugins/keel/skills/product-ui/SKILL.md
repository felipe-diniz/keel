---
name: product-ui
description: Screens of a product or app, the logged-in work tools: dashboard, table, list, form, modal, settings, work screen, empty and loading states, interface text, and auditing a screen's UI. Dense, scannable, coherent between screens. Use when building, changing or auditing such a screen. Not for public marketing pages (web-craft). A project's own design skill or design system wins where it is more specific.
---

# Product UI

A product screen is a work tool: people spend a shift in it. Every visual decision serves reading more data per screen,
comparing without scrolling and spotting the exception at a glance. The numbers below are defaults for a project with no
design system of its own. The detail lives in `references/`: open only the one the step needs.

## The rules that always hold

1. **Hierarchy by weight and position, not size.** Page title 20px at most. Type comes from the scale; no arbitrary size.
2. **Color is signal.** The brand accent sits on the main action and the active state, 1 or 2 points per screen. Status
   colors are separate from the brand and never color alone.
3. **Elevation is a 1px border plus a luminosity step.** Shadow only for what floats. Never dilute the border token.
4. **Every operational list is a table.** Cards only to choose or confirm. Status is a labeled badge.
5. **Absence takes one line.** An empty state is one line, never a block. Loading is a skeleton with the real geometry
   of the screen, over the results only.
6. **Air between blocks, density inside.** 24/32/48 between, 4/8/12/16 inside. One page container for every screen.
7. **Buttons are filled, as tall as the fields.** Hierarchy by tonal step; meaning comes from the variant, never from
   text color. A custom dropdown only when it solves a real problem.
8. **A modal is not the first solution.** Three widths (448, 784, 1120), the footer owned by the component, only the
   body scrolls. Consulting while writing goes in a side panel.
9. **A touched screen moves to the standard.** Drift between screens is a defect; a spec guards the scales and its
   ceilings only go down.

## The flow

1. **Read the surface.** Work tool, casual user or marketing; the project's own design skill or system; the neighboring
   screens ([foundations](references/foundations.md)). Build and audit with that surface's ruler.
2. **Compose with the tokens.** Scales, container, theme ([foundations](references/foundations.md)); buttons, fields,
   modals ([components](references/components.md)); lists ([tables](references/tables.md)).
3. **Shape the screen.** Where the work happens, what pushes it down, panel or modal ([screens](references/screens.md)).
4. **Build the states.** Loading, empty, error, denied, in the same geometry as the real content.
5. **Write the text.** Errors as codes translated into three parts, empty by kind, destructive by object and
   consequence ([copy](references/copy.md)).
6. **Verify on the rendered screen** at 390 and 1280, both themes, every state
   ([verification](../web-craft/references/verification.md)). A guard test holds what a document cannot.
7. **Audit** a screen you did not build with the rubric ([audit](references/audit.md)).

## References (read when...)

| File | Read when |
|---|---|
| [references/foundations.md](references/foundations.md) | setting type, spacing, radius, color, dark mode, transitions, the page container, loading or empty states |
| [references/components.md](references/components.md) | building a button, field, form layout, toggle and its helper text, modal, confirmation or dropdown |
| [references/tables.md](references/tables.md) | building a list or table, a status badge, a summary strip, pagination, an expandable or receded row |
| [references/screens.md](references/screens.md) | designing a work screen, a casual-user screen, a side panel, or checking drift and the guard spec |
| [references/copy.md](references/copy.md) | writing labels, errors, empty states, confirmations, toasts, consent text or translation keys |
| [references/audit.md](references/audit.md) | auditing or scoring the UI of any surface, or writing the audit report |

## What fails a review

- A font size, spacing or radius off the scale; a title above 20px; a shadow on something that does not float.
- A diluted border token, or height and font stamped over the field class.
- A list built as cards, a hand-written table, a color dot as row status with no label, numbers not right-aligned.
- Accent color on backgrounds, decoration or more than two places on a screen.
- Opacity to recede a row or an inactive item; `transition-all`.
- Outline-only buttons; text color on a neutral button to signal danger.
- A modal with its own width or a hand-drawn footer; a submit button outside its form with no `form="id"`.
- A skeleton with another geometry; a gate that shows "you do not have it" while loading; a spinner in the content.
- Raw backend text as an error; sensitive data in a toast, push or subject.
- Two screens with the same action in different variants.
- "Done" without the rendered screen in both themes and at phone width.
