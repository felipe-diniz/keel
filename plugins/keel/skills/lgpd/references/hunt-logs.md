# Hunt: personal data in logs, alerts, APM and analytics

Read when auditing code for personal data that leaves through a log line, an error alert (chat webhook, error e-mail,
pager), APM or tracing, product analytics, session replay or the browser console, or when reviewing a diff that adds a
log line.

## Why logs come first

A log sits outside the data's own access control: no tenant scoping, retention set by the log platform, read by
operators, often shipped to a third party. Personal data in it is a copy with no legal basis on record, no purge and no
owner (LGPD arts. 6 III, 15, 16 and 46). Health data in it is a copy of sensitive data (art. 11). An alert sent to a chat
or e-mail tool is a transfer to another operator, frequently abroad (art. 33).

## The fix, once

Every finding below closes with the same rules; the patterns only say where they break.

- Log by reference: tenant id, user id, record id, route template, status, error class, count, duration. Never the
  value of a name, document (CPF, CNPJ, RG), e-mail, phone, address, birth date, free text, clinical text, body, token.
- The message is fixed text. Variables are ids and enums, never user input.
- Redaction matches key FRAGMENTS, case-insensitive, after normalizing camelCase, snake_case and kebab-case:
  `email, mail, phone, fone, whatsapp, mobile, cpf, cnpj, rg, document, doc, name, nome, address, street, rua, zip,
  cep, birth, nasc, password, senha, token, secret, authorization, cookie, card, pix, iban, note, comment, message,
  text, body, encrypted, cipher, signature`. It runs recursively (objects and arrays), on request AND response, and
  has a test with variant keys (`billingEmail`, `requester_name`, `workplace-phone`, `zipCode`).
- A body that is not JSON is logged as length and content type only.
- An error is logged as name, code, status and a fixed message. Its `message` goes in only through a mask
  (documents, e-mails, phones) when it can echo input.
- One helper owns serialization (`safeError(err)`, `redact(obj)`); call sites never stringify.

## Patterns

Severity: P0 personal or health data reachable by another tenant or the public; P1 personal data sent to a third
party (alert, APM, analytics, provider) or health data in any log; P2 personal data in own server logs; P3 hygiene
(dev output, fixtures, client console). The `rg` lines are starting points: open each hit and follow the variable.

### 1. Value interpolated in a log line
- Signal: `rg -n "(console|logger|log)\.(log|info|warn|error|debug)\(.*(email|phone|cpf|cnpj|name|document|address|birth)" -i`
  and template literals `rg -n '\$\{[^}]*(email|phone|cpf|name|document)[^}]*\}' -i` near a logger.
- Severity: P2; P1 with health data.
- Fix: replace with the id; keep a fixed message.

### 2. Error alert to an external channel
- Signal: `rg -n "hooks\.slack\.com|discord(app)?\.com/api/webhooks|webhook\.office\.com|sendAlert|notify(Error|Admin)|alertService" -i`,
  error e-mail senders, pager integrations. Trace what the payload carries.
- Severity: P1. The channel is a third party, readable by everyone in it, kept forever.
- Fix: the alert carries route, error class, tenant id, record id, count and a link to the internal log entry.
  Recipient, message text, payment link and provider response stay out.

### 3. Messaging and e-mail provider calls
- Signal: logs or alerts around SMS, WhatsApp, e-mail sends that include `to`, `from`, `text`, `body`, `subject`,
  a reply's sender, or a link with a token (checkout, reset, magic link).
- Severity: P1 when it reaches an alert or APM; P2 otherwise. A link with a token is also a credential.
- Fix: log message id, template id and the provider status code; mask the recipient to the last two digits if support
  needs a handle.

### 4. Upstream error echoed
- Signal: `rg -n "JSON\.stringify\((err|error|e)?\.?response\.data|response\.data\)|errors\[[0-9]*\]\.(description|message)"`.
  Partner APIs (payment, invoicing, identity) echo the document and name they rejected.
- Severity: P2; P1 when forwarded to an alert.
- Fix: map the upstream to a code; run the document/e-mail/phone mask before any log; one helper for every partner,
  not only the caller that remembered.

### 5. Redaction by exact key name
- Signal: `rg -n "includes\(key\)|\[('|\")(password|cpf|email)('|\"),|new Set\(\[('|\")password" -i` inside a
  sanitizer, a logging middleware, an exception filter.
- Severity: P1 when the redacted object is the whole request body; it leaks every key nobody listed.
- Fix: fragment matching as above, with the variant-key test. Adding a PII field to a DTO adds its fragment if new.

### 6. Database or validation error message echoes values
- Signal: logging `err.message` from the ORM or driver: validation errors that print the arguments, duplicate-key
  messages (`dup key: { email: ... }`, `Duplicate entry '...' for key`), failed-query errors that carry parameters.
- Severity: P2.
- Fix: log the error code and the constraint or field name; map duplicates to a domain code.

### 7. Whole error or object logged
- Signal: `rg -n "console\.error\([^,)]*(err|error|e)\)|logger\.error\((err|error|e)\)|\?\? (err|error)\)"`
  and `logger.error({ ...req })`, `{ error }` spread. An HTTP client error carries the request body and the
  `Authorization` header in its config.
- Severity: P2; P1 when headers are inside.
- Fix: `safeError(err)` with name, code, status, route template; stack only in non-production.

### 8. Raw body logged
- Signal: logging `req.body`, `request.body`, `await res.text()`, a body sliced to N characters, a GraphQL `variables`
  object.
- Severity: P2; P1 with health data.
- Fix: redacted JSON or length plus content type.

### 9. Query string, path and search terms
- Signal: access logs, slow-call logs, APM span names and analytics page views that record the full URL; search
  routes with `?q=`, `?search=`, `?email=`, `?cpf=`, `?name=`.
- Severity: P2; the same URL also lands in browser history, proxies and the `Referer` header.
- Fix: log the route template and an allowlist of non-personal query keys; personal filters go in a POST body.

### 10. A 4xx message forwarded to the log
- Signal: the client or a backend-for-frontend logs the API's error `message` ("document 123... already registered").
- Severity: P2.
- Fix: the user may see the message about their own data; the log keeps only the code.

### 11. Import and batch row errors
- Signal: per-row validation failures logged with the row content or with a message that quotes the cell.
- Severity: P2.
- Fix: row number, column, rule id.

### 12. APM, tracing and error monitoring
- Signal: `rg -n "setAttribute\(.*(email|user|name)|setUser\(|sendDefaultPii|captureRequestBody|beforeSend|setTag\(" -i`;
  database statement capture with bound parameters; HTTP body capture turned on.
- Severity: P1 (third party, usually abroad).
- Fix: internal user id only; body and parameter capture off; a `beforeSend` scrubber with the same fragment list;
  the provider under contract as operator and the transfer covered.

### 13. Product analytics and session replay
- Signal: `rg -n "identify\(|setUserProperties|people\.set|gtag\(|dataLayer\.push|posthog|mixpanel|amplitude|hotjar|clarity|logrocket|fullstory" -i`.
- Severity: P1; P0 when replay records health screens of every tenant.
- Fix: inputs masked by default, replay off on screens with personal or health data, the user keyed by an internal or
  hashed id, no e-mail as id, scripts loaded only after consent where consent is the basis (see
  [hunt-storage.md](hunt-storage.md) §4).

### 14. Browser console and client errors
- Signal: `console.log(` with a response or form state in client components; client error reporters with the store
  attached.
- Severity: P3; P2 when a reporter ships it.
- Fix: remove; report ids.

### 15. Scripts, seeds, jobs and tests
- Signal: seed or admin scripts that print e-mails, job logs with the payload, snapshots and fixtures with real data.
- Severity: P3; P1 when a fixture carries real production data.
- Fix: counts and ids in output; synthetic fixtures.

### 16. Error detail returned to the client
- Signal: an exception handler that returns `err.message` or the stack in the response.
- Severity: P2 (also a security finding).
- Fix: a code and a correlation id; detail stays in the redacted server log.

## Review a diff

`git diff -U0 <base> | rg '^\+.*(console\.|logger\.|log\.(info|warn|error|debug)|captureException|setUser|identify\()'`
lists every added log or telemetry line; each one passes the rules in "The fix, once".
