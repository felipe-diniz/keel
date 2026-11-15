---
name: lgpd
description: LGPD (Brazil) for software with personal data. Teaches legal bases (arts. 7, 11), health data, data subject rights, controller vs processor in multi-tenant SaaS, retention, anonymization, international transfer, incidents, records, RIPD; hunts leaks in code (personal data in logs, alerts, APM, analytics; cross-tenant access; plain-text sensitive fields; exports; no purge; consent; debug routes; secrets). Use when designing or auditing personal data. A project's own privacy rules win where more specific.
---

# LGPD

Two modes. TEACH answers how the law applies to a feature, with the article. HUNT audits the code for the ways personal
data leaks or outlives its purpose, and reports each finding with severity and fix.

## The rules that always hold

1. **Security first.** In any doubt the order is: security, tenant isolation, data protection, then performance.
   Convenience comes after. A choice that trades one of these for speed goes to the owner with the case.
2. **No personal data in logs.** Logs, alerts, traces, analytics and error reports reference by id, never by value.
3. **Every query, cache key, room, job and file path carries the tenant** from the session, never from the client.
4. **Every field has a purpose and a legal basis on record**; a field without both is not collected.
5. **Every category has a retention period and a purge** that reaches every store.
6. **Cite the article.** A legal claim comes with its article or resolution, read in the official text. What was not
   verified says "to validate" and goes to the encarregado (DPO) or counsel.
7. **Never expose what you find.** A report names the file, line and kind of data or secret, never the value. A
   probe on real data returns counts and ids only. Never open environment files; check them by name.
8. **Not legal advice.** The skill does not replace the encarregado, counsel or the controller's decisions: whether
   to communicate an incident, which legal basis applies to a business purpose, a retention period set by law, whether
   a company is a small processing agent.

## Teach

1. Identify the data (personal, sensitive, health, children's), the data subjects and who decides the purpose
   (controller) vs who executes (processor) ([law.md](references/law.md)).
2. Name the purpose and the legal basis per processing ([law.md](references/law.md)).
3. Apply the lifecycle: minimize, retain, eliminate or anonymize, transfer, record, RIPD
   ([lifecycle.md](references/lifecycle.md)).
4. For an incident, the deadlines and the runbook ([incident.md](references/incident.md)).
5. Answer with the article, the design consequence in code, and what is "to validate".

## Hunt

1. **Scope.** Repositories, services and the data map: which entities hold personal or health data, which tenants,
   which third parties. Read the project's CLAUDE.md critical-risk section first.
2. **Sweep** each catalog in order, running its signals and opening every hit:
   logs and telemetry ([hunt-logs.md](references/hunt-logs.md)), tenant isolation
   ([hunt-isolation.md](references/hunt-isolation.md)), storage, lifecycle and surface
   ([hunt-storage.md](references/hunt-storage.md)).
3. **Confirm** each finding by reading the path end to end (where the value comes from, where it goes). A grep hit is a
   lead, not a finding.
4. **Report** one line per finding: severity, what, where (`file:line`), data category, impact, fix, and the test that
   proves the fix. Group by severity; count repeats once with the number of places.
5. **Fix** only when asked. A fix to tenant isolation, authorization or deletion is critical risk: it follows the
   project's gate.

Severity: **P0** personal or health data reachable by another tenant or the public, or a live credential exposed;
**P1** personal data sent to a third party (alert, APM, analytics, AI provider) or sensitive data unprotected;
**P2** personal data in own logs, missing purge, broken data subject right; **P3** hygiene.

## References (read when…)

| File | Read when |
|---|---|
| [references/law.md](references/law.md) | concepts, legal bases (arts. 7 and 11), health data, rights and deadlines, controller vs processor in SaaS, encarregado, sanctions |
| [references/lifecycle.md](references/lifecycle.md) | minimization, retention and purge, anonymization vs pseudonymization, international transfer, records, RIPD, security measures |
| [references/incident.md](references/incident.md) | a possible leak or exposure, deciding communication, deadlines of Res. CD/ANPD 15/2024, the runbook and the record |
| [references/hunt-logs.md](references/hunt-logs.md) | auditing logs, error alerts, APM, analytics, session replay, browser console, or a diff that adds a log line |
| [references/hunt-isolation.md](references/hunt-isolation.md) | auditing a multi-tenant system: queries, RLS, caches, realtime, jobs, search and vector indexes, storage, exports |
| [references/hunt-storage.md](references/hunt-storage.md) | auditing encryption at rest, exports, retention, consent, debug routes, secrets, third parties and AI providers, non-production copies, browser storage, access trails, data subject requests |

## What fails a review

- A log, alert or trace line with a name, document, e-mail, phone, address, body, token or clinical text.
- Redaction by exact key name; an error object or `message` logged whole.
- A query, cache key, room, job or path without the tenant, or with the tenant taken from the request.
- Health or document fields stored in plain text; a public or long-lived export link.
- Soft delete with no purge; a deletion that misses a store.
- Personal data sent to a provider abroad with no contract and no transfer mechanism.
- A legal claim without an article, or a "to validate" item presented as settled.
- A report that prints the leaked value or the secret.
