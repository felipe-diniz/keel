# Release notes

Read when the owner asks for a release note, a changelog for customers, the "what's new" message or the release video. Covers scope, draft structure, the WhatsApp broadcast message, the release video and the approval gate.

The skill drafts. It never uploads or publishes. Where notes live and how they go live come from the project (its own publish script or process). The owner approves before anything ships.

Config used here (see [config](config.md)): `copy.releaseNotes` (folder where notes live), `copy.rules`, `copy.notDo`, `product`, `site`, `locale`, `output`.

## 1. Flow

1. Find the starting point (section 2).
2. Collect what changed and apply the scope rule (sections 2 and 3).
3. Draft the note (section 4) and save it in `copy.releaseNotes`.
4. Show the draft to the owner and wait for approval (section 8).
5. After approval, write the WhatsApp message (section 5).
6. Produce the video if the owner wants one (section 6).
7. Hand over. The owner publishes with the project's process (section 7).

## 2. Commits since the last note

- The last published note is the newest file in `copy.releaseNotes`. If the project has a publish tool that lists notes, use it to confirm what is live.
- Read its version and date. If the folder is empty, ask the owner for the date of the last deploy.
- List the changes: `git log --oneline --no-merges <since>..HEAD`, where `<since>` is the commit or tag of the last note, or `--since=<date>` when there is no ref. Run it on the branch that goes to production.
- Alternative: the summary of the release PR (development branch into production branch).
- Keep `feat` and `fix` with a visible effect. Drop `chore`, `refactor`, `test`, `ci`, `docs` and fixes for things never released.
- Read the diff when a commit message is unclear. Do not write a bullet from a title alone.

## 3. Scope: user-facing only

A release note is news for the end user. Include only what the end user sees or does.

Exclude, even as a generic bullet:

- Security work, hardening, vulnerability fixes. Reason: it tells attackers where to look and means nothing to the user.
- Infrastructure, deploy, DevOps, database, migrations. Reason: invisible to the user.
- Admin-only or back-office features. Reason: the audience of the note cannot use them.
- Internal performance work. Reason: the user cannot verify it and the claim ages badly. A speed-up the user clearly feels may be a plain bullet.
- Refactors, tests, CI. Reason: no behavior change.

If the release has only excluded items, there is no note. Tell the owner and stop.

Also:

- Write for the end user in `locale`, in the audience's words. Never cite internal technology: caches, queues, DTOs, migrations, library names.
- Apply the project's hard copy rules from the config (`copy.rules`) to every field.
- Check each bullet against code or docs. Do not announce what `copy.notDo` says the product does not do, and do not announce roadmap items.
- If a feature is plan-gated or metered, say so, or leave it out.

## 4. Draft structure

Fields:

| Field | Rule |
|---|---|
| `version` | The idempotency key. Re-publishing the same version updates the same note instead of creating a new one. The project decides the format. A date-based version such as `YYYY.MM.DD` is an example. Follow the existing files in `copy.releaseNotes` |
| `title` | Short. Example: "What's new in July" |
| `description` | Optional. One or two sentences of context |
| `highlights` | 3 to 6 bullets. Each opens with the benefit ("Schedule recurring appointments...", "Get the PDF of each session...") |

- Highlights are one idea each, benefit first, plain words.
- Use the existing note format of the project. Match its file type and fields. Do not invent fields the publish step does not read.
- Example, neutral:

```json
{
  "title": "What's new in July",
  "version": "2026.07.24",
  "description": "See what arrived in Acme in the last weeks.",
  "highlights": [
    "Book recurring appointments in one step",
    "Download the PDF of each report"
  ]
}
```

- Save as `<copy.releaseNotes>/<version>.<ext>` following the folder's convention. The file is versioned in git as history.
- Optional attachments (links to a guide, video URL, poster, captions) only if the project's note format has such fields. Links point to the project's own paths or `https://`.
- A feature the customer configures through a click path that does not fit a note may deserve a separate illustrated guide. That is a project decision; use the project's own guide process and do not invent one.

## 5. WhatsApp broadcast message

Write it after the note is approved, without waiting to be asked. Broadcast lists are highlights, not the whole note.

Save next to the note as `<version>.whatsapp.md` (or the project's convention) and show the text in the reply, ready to copy and paste.

- Length: 4 to 6 lines of news, one sentence each. A highlight that does not fit in one sentence stays out. Pick what the customer notices first. No "additionally", no step-by-step configuration.
- Structure: bold title on the first line, a blank line between items, each line opening with one emoji and the topic in bold, and a final line pointing to the place in the product where the note lives (e.g. the "What's new" button), or the link.
- A link goes at the end, as a plain URL (`site`), on its own line.
- Same rules as the note: `locale`, no jargon, scope rule, project hard copy rules (`copy.rules`).

WhatsApp markdown:

| Effect | Syntax |
|---|---|
| Bold | `*text*` (not `**text**`) |
| Italic | `_text_` |
| Strikethrough | `~text~` |
| Monospace | three backticks around the text |
| Line break | a real newline; a blank line separates items |

- Headings (`#`), `-` lists and `[label](url)` links do not render. Do not use them.
- Why blank lines: pasted into WhatsApp Web, a dense paragraph becomes an unreadable block.
- Example, neutral:

```
*What's new in Acme*

📅 *Recurring appointments* in one step.

📄 *PDF of each report*, ready to share.

See everything in the "What's new" button.
https://example.com
```

## 6. Release video

One video per release, desktop landscape, with real screens from seed or demo data, narration and captions.

- Plan: a storyboard JSON with `"format": "landscape"`. See [storyboard](storyboard.md).
- Scenes: captured by `capture.mjs` from a JSON plan. See [capture](capture.md). Run against a local or demo environment, never production. Seed or demo data only, with personal data masked or invented.
- Composition: `compose.mjs` with `"format": "landscape"` produces the 1920x1080 mp4, a poster image, one still per scene and the WebVTT track (captions). Landscape is the only format that emits the WebVTT.
- Order: stills first, narration after.
  1. Build the silent stills and review framing, text and screens. Stills cost nothing.
  2. Get the owner's approval of the stills.
  3. Only then generate the narration with `audio.mjs`. See [audio](audio.md). Each call spends credits; do not regenerate it to fix framing.
  4. Check the spoken text against the transcript before delivery.
- The video promises only what the note and the code confirm.
- Work files (mp4, audio, stills) stay out of git. The storyboard and capture plan stay versioned.
- The skill does not upload the video. Hosting and where the URL goes come from the project's process.
- Do not make two videos for the same release.

## 7. Where notes live and how they publish

- Drafts live in `copy.releaseNotes`.
- Publishing is the project's own mechanism: a publish script, a deploy step that syncs the folder, a CMS. Read the project's docs and `CLAUDE.md` for it.
- Typical mechanics to check, not to assume: committing the draft may publish it on the next deploy; re-running with the same `version` updates the same note; there may be a dry-run and an unpublish command. Confirm each in the project before telling the owner.
- Say to the owner exactly which action ships the note, and wait for their go.
- The skill never runs a command that publishes or unpublishes.

## 8. Approval

- Show the draft and wait for explicit approval. Do not commit it without review: in many projects a commit plus a deploy is the publication.
- Validate with the project's dry-run or validation command if one exists, and report the result.
- The WhatsApp message and the video start only after the note is approved (the video also needs the stills approved).
- Corrections after approval: edit the same `version` and re-validate. A message already sent to customers cannot be recalled.

## 9. Cadence

- One note per release that matters to the user, or grouped weekly.
- A release with only internal fixes gets no note.

## 10. Checklist

- [ ] Starting point found from the newest file in `copy.releaseNotes`; `git log <since>..HEAD` read.
- [ ] Only user-facing changes. No security, infra, database, admin-only, internal performance, refactor, tests or CI.
- [ ] Every bullet checked against code or docs; nothing from `copy.notDo` or the roadmap.
- [ ] `version` follows the project's format and matches the file name.
- [ ] Title short, 3 to 6 highlights, each opening with the benefit.
- [ ] No internal jargon. Project hard copy rules (`copy.rules`) met in every field.
- [ ] Draft saved in `copy.releaseNotes`; owner approved before anything shipped.
- [ ] WhatsApp message: 4 to 6 lines, WhatsApp markdown only, blank lines between items, link at the end.
- [ ] Video, if any: landscape 1920x1080, stills approved before narration, WebVTT present, seed data only.
- [ ] Nothing uploaded or published by the agent; the owner was told which action ships it.
