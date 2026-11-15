# Security incident with personal data

Read when personal data may have leaked, been exposed to the wrong tenant or person, lost, altered or made
unavailable, when deciding whether an event must be communicated to the ANPD and data subjects, or when building the
incident runbook and its record.

Rules from LGPD art. 48 and Resolução CD/ANPD 15/2024 (published in the DOU on 2024-04-26, in force on publication),
read on 2026-11-15. The decision to communicate is the controller's, with the encarregado; engineering supplies facts
fast.

## What counts

- Incident: a confirmed adverse event that violates the confidentiality, integrity, availability or authenticity of
  personal data (Res. 15/2024 art. 3 XII). Examples in software: data of one tenant shown to another, a public bucket,
  personal data in an external alert channel, a leaked credential with access to personal data, ransomware, a deletion
  without backup.
- Communication is required when it may cause relevant risk or damage to data subjects (LGPD art. 48). Res. 15/2024
  art. 5: it may significantly affect their interests and fundamental rights AND involves at least one of: sensitive
  data; data of children, adolescents or the elderly; financial data; authentication data; data protected by secrecy;
  large scale (number of subjects, volume, duration, frequency, geographic reach).
- Data made unintelligible by adequate technical measures (encryption with the key not exposed) lowers the risk
  (art. 48 §3).

## Deadlines (Res. 15/2024)

| Step | Deadline | Article |
|---|---|---|
| Communication to the ANPD | 3 business days from the controller's knowledge that personal data was affected | art. 6 |
| Complement to the ANPD | 20 business days from the communication | art. 6 §3 |
| Communication to data subjects | 3 business days | art. 9 |
| Small processing agent | the deadlines above in double (6 and 40 business days) | art. 6 §8, art. 9 §6 |
| Record of the incident, communicated or not | kept at least 5 years | art. 10 |

- Knowledge starts the clock: the processor (the SaaS vendor) tells the controller (each affected tenant) at once so
  the controller's 3 days are not spent inside the vendor. The vendor's contract sets that duty; the vendor does not
  communicate to the ANPD in the tenant's place unless the contract says so.
- Data subjects: plain language, direct and individual when possible; when not, public notice for at least 3 months,
  and a statement to the ANPD within 3 business days after the deadline saying how they were informed (art. 9).
- Whether a company is a small processing agent (double deadlines): to validate with counsel.

## Content of the communication (LGPD art. 48 §1)

Nature of the affected data; the data subjects involved; technical and security measures used to protect the data;
the risks; the reasons for any delay; the measures taken or to be taken to reverse or mitigate the effects. The
ANPD form asks more; fill it from the record below.

## Runbook for engineering

1. Contain: revoke the exposed credential, close the bucket or route, disable the feature flag, stop the job. Do not
   delete evidence.
2. Preserve: snapshot access logs, audit trails, the deployed version, the configuration; record the time of
   knowledge.
3. Scope with queries that return counts and ids, never personal data in the incident channel: which tenants,
   how many data subjects, which data categories, from when to when, who accessed (logs).
4. Tell each affected controller (tenant) with the facts so far; name the time of knowledge.
5. Fix the cause with a regression test (for tenant leaks, a two-tenant test).
6. Write the record (below) whether or not it is communicated.
7. Review: what detection would have caught it earlier; add it.

## The record (Res. 15/2024 art. 10)

Date of knowledge; general description of the circumstances; nature and category of the data; number of data subjects
affected; risk assessment and its reasoning; measures to correct and mitigate; how and when communicated (or why
not); kept for at least 5 years. Store it outside the system that failed, access-restricted, without copying the leaked
personal data into it.

## Sources

- https://www.in.gov.br/en/web/dou/-/resolucao-cd/anpd-n-15-de-24-de-abril-de-2024-556243024
- https://bibliotecadigital.mj.gov.br/bitstream/1/12879/2/RES_ANPD_2024_15.html
- https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm (art. 48)
