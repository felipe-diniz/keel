# Tables and lists

Read when you build or review a list of records, a table, a status badge, a summary strip, pagination or a row state.

Values are defaults. A project's shared table component and tokens win where they are more specific.

## Table, not cards

- Every operational list is a table. Cards are for choosing an item; tables are for operating on a list.
- Use the project's one shared table component. No hand-written `<table>` per screen.
- Exception by design: a list that is a selector (click picks the item and opens the panel beside it) is not operated on. Say so in the code.
- A casual-user surface may show the next few items as cards ([screens.md](screens.md)).

## Alignment

| Content | Alignment |
|---|---|
| Number, money, count, duration | Right, with `tabular-nums` (the pair that makes the column line up) |
| Icon, badge, glyph, action buttons | Centered: cell and header |
| Text | Left |

- Centered covers block content too (a row of buttons, a glyph with its sr-only text).
- A text column that only has an icon beside the text stays left: the data is the text.
- Action column: no header label, no label in the phone card.

## Values

| Rule | Value |
|---|---|
| Row height | 32px default, 24px compact (in px, not rem) |
| Cell padding | 12px horizontal, 4px vertical (dense: 8px, 2px) |
| Font | 14px data, 12px uppercase header |
| Row separator | The strong border token. The subtle one resolves to about 4% alpha and disappears |
| Hover | On-surface at about 6% alpha: lightens in dark, darkens in light. Never the muted surface, which is darker than the card in dark and sinks the row |
| Empty cell | Empty or `-`, never a decorative placeholder |
| Empty list | The empty-state component, never a bare empty table |
| Pagination | 20 rows, attached above the table |

## Columns

- Column headers have their own vocabulary. A form label ("Phone (optional)") is not a column title. Each list has its own block of column keys.
- Sortable column: the component only emits the request; the screen reorders or refetches. On a server-paginated list, sorting only the visible page lies to the user.
- Phone: secondary columns hide instead of squeezing the card.

## Phone

- The table becomes a card of labeled rows from the same markup: block / table-row at the large breakpoint / table-cell, the label in a span hidden at that breakpoint.
- Never two markups. The same data twice in the DOM is read twice by a screen reader.
- Long text wraps; a column with no width truncates with an ellipsis on desktop. Give it a width or let it wrap.

## Status badge

- A row's status is a badge, not a color dot: 1px frame, 4px radius, 11px semibold, low-alpha hue fill. One geometry across the product.
- No `rounded-full`, uppercase, wide tracking or 12px.
- Why: when states alternate line by line (confirmed, cancelled, missed), a dot carries too little painted area to separate blocks at a glance, and the column reads as one gray.
- The tone answers "what does this row ask of me?". The label says which state. A label is mandatory: color alone is no information.

| Tone | Meaning |
|---|---|
| success | Done, confirmed, paid, active |
| warning | Needs action |
| caution | Deviation that is not destructive (missed, at risk) |
| danger | Cancelled, refunded, failed |
| primary | In progress |
| review | Pending review (violet) |
| info | Category |
| neutral | Closed, inactive |

- Two states may share a tone (confirmed and paid are both success). The label separates them.
- One case remains for the 6px dot: where no label fits (a 20px-tall line inside a grid cell). It always carries sr-only text. If only color fits, the layout is usually the problem.
- A KPI legend stays a dot ("27 completed"): it is the key of a summary, not the state of a record.

## Signal column instead of a KPI strip

- A strip of summary cards on top (six counts of pending, confirmed, cancelled) rarely helps decide on any row and costs about 90px above the list.
- Use a narrow column of 18px glyphs per row (paid, owes, remote, walk-in, alert, note), text in `title` and in a `sr-only` span: a glyph alone informs no one.
- The aggregate, when needed, is one line of text above the table ("12 orders, 3 pending, 1 cancelled").
- A glyph for restricted data (money) follows the same permission as the data.
- A signal comes only from a field the payload already carries. The column rescues data the screen discards; it is no excuse to fatten the payload. Check the response type first.

## Pagination

- Pagination belongs to the table, attached at the top inside its frame, 20 rows by default.
- Why: whoever wants the next page already knows the list and does not want to reread it; at the bottom, advancing means scrolling 20 rows, advancing and going back up. With each screen mounting its own bar, bars end up above, below and at different distances.
- Set page size only when the backend paginates by another rule; total pages only when it already returns the number.
- A cursor list (previous / next, no total) passes its ready bar through the same slot. The frame stays the table's.
- A standalone pagination component is only for lists that are not tables.

## Expandable rows

- For what does not fit a column (breakdown of a payment, tax data, history).
- Return `null` for a row that does not expand: the arrow shows only where there is detail.
- The screen owns which row is open: expansion often comes from the URL, a realtime event or an action. Internal state in the component would compete.

## Row state

- Whole-row highlight only for data state: refunded, cancelled, overdue, in conflict. Never decoration. Painting cell by cell does not read like running the eye down the list.
- A receded row (cancelled, missed, inactive, outside the batch) recedes by token: muted surface background and the variant text token, including the cell that paints the main text color. The status badge keeps its hue.
- Never `opacity` on the row: it dilutes the text and badge together and fails AA in axe. Same outside tables: the block recedes by background and text token, a deactivated record by strikethrough ([design.md](../../web-craft/references/design.md)).
