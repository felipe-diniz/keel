# Interface copy

Read when you write or review text inside a product screen: labels, buttons, errors, empty states, confirmations, toasts, e-mails, consent text or translation keys.

Marketing text (headlines, CTAs, proof) is in [web-craft copy.md](../../web-craft/references/copy.md). The hard rules there apply here too: no em or en dash in UI text, never invent a fact.

## Words

- Plain, active voice, the name the user recognizes ("reminders", not "webhook").
- The same concept has the same name through the whole flow.
- Button: action plus object ("Save note"). The confirmation repeats the verb ("Note saved").
- Page subtitle only if it informs something the title does not. "Follow your data" informs nothing.
- Never claim something the system did not do. Copy that states a result ("Reminder sent") is shown only on a real marker of it (a delivery status, a timestamp), not on the intent.

## Errors

- The backend returns an error CODE; the client translates it. Raw backend text never reaches the screen.
- Three parts: what failed, why (only if the system knows and it helps), how to proceed.
  "Could not create the invoice: the customer has no tax ID. Complete the record and try again."
- No internal code as the main sentence, no apology, no promise of a cause the system does not know.
- The error sits beside the field and says how to fix it, without blame.

## Empty states

Say which kind it is. One line, not a block.

| Kind | Says |
|---|---|
| First use | What to do to start |
| Search with no result | What to change |
| Filter | How to clear it |
| No permission | Who to ask |
| Failure | Try again |

## Destructive actions

- Name the object and the consequence. The button repeats the action.
  "Cancel the 4 bookings in this group? Customers are notified." with "Cancel bookings". Never "Yes" or "OK".
- Where undo is safe, prefer undo over asking.
- The confirmation component and widths: [components.md](components.md).

## Forms

- Fixed label. The placeholder is an example, not a label.
- Say the required format before submit.
- A request for sensitive data says what it is for, when not obvious.
- Toggle helper and dependent toggles: [components.md](components.md) Toggles.

## Loading

- Name the operation ("Generating the invoice PDF"). A progress bar only if progress exists.

## Sensitive data and consent

- No sensitive data in a toast, push, e-mail subject or message preview: a locked screen shows it.
- Access denied does not confirm a record exists. "Not found or no access" for both.
- Consent or terms text states the effect in plain words, with no legalese and no hidden purpose.
- Personal data (LGPD, GDPR): the legal rules are in the lgpd skill when the project has it.

## Translation

- One whole sentence per key. Never concatenate fragments.
- Variables as `{name}`. Plurals and word order through the i18n library's plural keys, not by hand.
- Leave room for the longest language to grow and test it at every width ([verification.md](../../web-craft/references/verification.md)).

## Checklist

- [ ] No em or en dash.
- [ ] Every error is a code translated to the three-part form.
- [ ] Each empty state names its kind.
- [ ] Each destructive prompt names the object and the consequence.
- [ ] Nothing sensitive in toast, push, subject or preview.
- [ ] No sentence states a result the system did not produce.
- [ ] Every sentence is a whole key, with plural keys where a count appears.

## Sources

The interface part adapts clarify.md of impeccable (Apache-2.0). Keep this attribution and license.
