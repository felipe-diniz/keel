# Hunt: storage, lifecycle and exposed surface

Read when auditing how personal data is stored, kept, exported, shared and deleted: fields without encryption,
exports, retention without purge, consent, debug endpoints, secrets in the repository, third-party SDKs and AI
providers, non-production copies, browser storage and the access trail.

Severity as in [hunt-logs.md](hunt-logs.md): P0 reachable by another tenant or the public; P1 sent to a third party
or sensitive data unprotected; P2 own exposure; P3 hygiene.

## Patterns

### 1. Sensitive field stored in plain text
- Signal: schema and migration files with health, document or free-text clinical columns:
  `rg -n "(cpf|cnpj|rg|document|diagnos|prescri|anamnes|clinical|health|medical|allerg|symptom|note|birth)" -i`
  over the schema, entities and migrations. Then: is the column encrypted at the application level, or only by the
  disk?
- Severity: P1 for health data and documents (art. 11; art. 46 asks for measures proportional to the risk).
- Fix: field-level encryption with envelope keys from a KMS, the key outside the database, rotation planned; search on
  an encrypted field through a keyed hash (blind index), never by decrypting the table. Disk encryption does not cover
  a dump, a replica or a stolen credential.

### 2. Exports and reports
- Signal: CSV, spreadsheet or PDF exports: which columns, who may call it, where the file lands (temporary bucket,
  public link, e-mail attachment), how long it lives, whether the export is recorded. CSV cells that start with
  `= + - @` are formula injection when opened in a spreadsheet.
- Severity: P1 (bulk copy that leaves the system); P0 when the link is public or unscoped.
- Fix: only the columns the purpose needs; role check; private storage with a short signed link; expiry and purge;
  an audit entry (who, when, which filter, how many rows); prefix risky cells with `'`.

### 3. Retention without purge
- Signal: soft delete (`deletedAt`, `active=false`) with no job that eliminates after the period; account deletion
  that leaves rows in related tables, files in storage, entries in search indexes, analytics profiles; logs and
  backups with no retention set; "keep forever" by default.
- Severity: P2; P1 for health data with no defined period.
- Fix: a retention table per data category (purpose, legal basis, period, what happens at the end: eliminate or
  anonymize), a purge job per category with a test, and the delete path tested across every store
  ([lifecycle.md](lifecycle.md) §Retention). Periods set by law or professional councils are "to validate" with the
  data protection officer.

### 4. Consent handled as a flag
- Signal: consent stored as a boolean without version of the text, timestamp, purpose and channel; pre-checked boxes;
  marketing sent without opt-in; withdrawal that does not stop the processing; tracking and marketing scripts loaded
  before the choice; one consent bundled for several purposes.
- Severity: P2.
- Fix: a consent record per purpose (who, what text version, when, how), withdrawal as easy as giving it, and the
  processing gated by it. Consent is one basis among ten (art. 7); do not force it where another basis fits, and do
  not fall back to it silently when it is refused ([law.md](law.md) §Legal bases).

### 5. Debug and administrative surface
- Signal: `rg -n "/debug|/_debug|/dump|/env|/actuator|/metrics|swagger|graphiql|playground|introspection" -i`;
  health endpoints that return configuration; admin routes without a role guard; seed or impersonation routes
  enabled by an environment check that can be wrong.
- Severity: P0 when it returns personal data or secrets without authentication; P1 behind login without a role.
- Fix: remove from production builds; behind staff role and network restriction when needed; impersonation logged and
  visible to the tenant.

### 6. Secrets in the repository
- Signal: environment files tracked by git, checked by name only: `git ls-files | rg -i "(^|/)\.env"` (do not open
  them); key shapes in code and docs: `rg -n "-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|sk_live_|xox[abp]-|ghp_[0-9A-Za-z]{36}|eyJhbGciOi"`.
- Severity: P0 for a production credential that reaches personal data.
- Fix: report the file, line and kind of secret, NEVER the value; the owner revokes and rotates (removing it from
  history does not un-leak it); a secret manager; a pre-commit scanner the team chooses.

### 7. Third-party SDKs and AI providers
- Signal: personal or health data sent to maps, chat widgets, e-mail marketing, CRM, translation, OCR, or a language
  model API (prompts with the patient's or customer's record, uploads for transcription). `rg -n "openai|anthropic|generativelanguage|vertex|bedrock|azure.*openai|chat\.completions|messages\.create" -i`.
- Severity: P1; transfer abroad and a new operator in the chain.
- Fix: send the minimum (pseudonymize identifiers before the call), a contract that names the provider as operator
  with no training on the data and a retention limit, the international transfer covered
  ([lifecycle.md](lifecycle.md) §International transfer), the processing listed in the records.

### 8. Production data outside production
- Signal: dumps restored to staging or a developer machine, seeds built from real records, support exporting a table to
  reproduce a bug, fixtures with real names.
- Severity: P1.
- Fix: synthetic or anonymized datasets; when a real record is needed to reproduce, access in production with an
  audit entry.

### 9. Browser storage and offline caches
- Signal: `rg -n "localStorage|sessionStorage|indexedDB|caches\.open|navigator\.serviceWorker" ` where the value is a
  token, a form with personal data or an API response with records; a service worker that caches authenticated
  responses.
- Severity: P2 (shared devices, XSS reach).
- Fix: tokens in `HttpOnly; Secure; SameSite` cookies; no personal data persisted client side; caches cleared on
  logout; authenticated routes excluded from the service worker cache.

### 10. Personal data in URLs and messages
- Signal: links with names, documents or e-mails in the path or query; reset and magic links without expiry or
  single use; documents shared by public token without expiry; analytics running on token pages.
- Severity: P2; P1 with health data.
- Fix: opaque ids; short-lived single-use tokens; analytics off on token pages.

### 11. No trail of access to sensitive data
- Signal: reads of health records or documents leave no record of who saw what; audit tables that the app can update
  or delete.
- Severity: P2.
- Fix: an append-only access trail (actor, tenant, record id, action, time, never the content), its own retention,
  readable by the controller.

### 12. Data subject requests that cannot be answered
- Signal: no way to list everything held about one person across stores (art. 18 II), to export it in a usable format
  (art. 18 V), to correct it, or to eliminate it where the basis was consent (art. 18 VI).
- Severity: P2.
- Fix: a per-person map (tables, files, indexes, third parties) and one routine per right, run by the controller; in a
  SaaS, the tenant runs it and the vendor provides the tool ([law.md](law.md) §Data subject rights).
