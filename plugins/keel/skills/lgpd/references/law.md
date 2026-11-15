# LGPD: concepts, legal bases, rights and roles

Read when explaining or applying Lei 13.709/2018 (LGPD): what is personal or sensitive data, which legal basis fits a
processing, what health data allows, the data subject's rights and deadlines, controller vs processor (operador) in a
multi-tenant SaaS, the data protection officer (encarregado), sanctions.

Articles read on the official compiled text (planalto.gov.br) on 2026-11-15. Terms in Portuguese in parentheses are
the law's own. This is orientation for a software team, not legal advice: decisions go to the encarregado or counsel.

## Concepts (art. 5)

- Personal data (dado pessoal): information about an identified or identifiable natural person. An internal id that
  links back to a person is personal data.
- Sensitive data (dado sensível): racial or ethnic origin, religious conviction, political opinion, union or
  religious/philosophical/political organization membership, health or sex life, genetic or biometric data, when linked
  to a person.
- Anonymized data: the person cannot be identified by reasonable technical means at the time of processing. It is not
  personal data unless the anonymization can be reversed with reasonable effort (art. 12); data used to build a
  behavioral profile of an identified person may count as personal (art. 12 §2).
- Pseudonymization (art. 13 §4): re-identification only with extra information the controller keeps separately.
  Pseudonymized data IS personal data. Encryption is pseudonymization, not anonymization (ANPD draft guide; final
  guide not published as of 2026-11-15).
- Controller (controlador, art. 5 VI): decides on the processing. Processor (operador, art. 5 VII): processes on the
  controller's behalf. Encarregado (art. 5 VIII): channel between controller, data subjects and the ANPD.

## Principles (art. 6)

- Purpose, adequacy, necessity (minimum data needed: the minimization rule, art. 6 III), free access, quality,
  transparency, security, prevention, non-discrimination, accountability (show the measures work, art. 6 X).
- In code: every field has a purpose you can name; a field without one is not collected.

## Legal bases for personal data (art. 7)

I consent; II legal or regulatory obligation; III public administration for public policies; IV studies by a research
body; V performance of a contract or preliminary steps at the data subject's request; VI regular exercise of rights in
judicial, administrative or arbitration proceedings; VII protection of life or physical safety; VIII health protection,
exclusively in a procedure by health professionals, health services or health authority; IX legitimate interest, unless
the data subject's fundamental rights prevail; X credit protection.

- Each processing purpose has ONE basis on record. Consent is not the default: most product features run on contract
  (V) or legal obligation (II); marketing and optional analytics usually on consent or legitimate interest (with a
  balancing test on record).
- Consent must be free, informed, unambiguous, for a specific purpose, revocable as easily as given (art. 8); if
  refused, do not fall back silently to another basis.

## Sensitive and health data (art. 11)

- Processed only in the listed cases: with specific, highlighted consent for specific purposes (I), or without consent
  for legal obligation, public policy, research, regular exercise of rights, protection of life, health protection
  exclusively by health professionals/services/authority (II f), and fraud prevention and secure identification and
  authentication (II g).
- Sharing health data between controllers for economic advantage is forbidden, except in the cases tied to providing
  health services (art. 11 §4; the exceptions' wording: to validate with counsel).
- Biometrics for login falls under art. 11 (sensitive).
- Children's and adolescents' data in their best interest; for children, specific consent by a parent or guardian
  (art. 14). Products likely to be accessed by minors also fall under the ECA Digital (Lei 15.211/2025, in force since
  2026-03-17: privacy by default, no profiling for advertising).

## Data subject rights (arts. 18 and 19)

- Art. 18: I confirmation of processing; II access; III correction; IV anonymization, blocking or deletion of
  unnecessary, excessive or unlawful data; V portability; VI deletion of data processed on consent (except art. 16
  retention); VII information on sharing; VIII information on the option not to consent; IX revocation of consent.
- Art. 19: confirmation and access in simplified form immediately, or a complete declaration within 15 days of the
  request. Small processing agents get double deadlines (Res. CD/ANPD 2/2022 art. 14).
- In code: a per-person map of every store (tables, files, indexes, caches, third parties, backups) and one routine
  per right ([hunt-storage.md](hunt-storage.md) §12).

## Roles in a multi-tenant SaaS

- The role is decided per processing operation, not per company (ANPD agents guide v2.0, 2022, non-binding).
- Typical split: each customer (tenant) is the controller of its end users' data (its clients, patients, guests,
  employees); the SaaS vendor is the processor for that data, acting on the tenant's instructions (art. 39). The vendor
  is the controller of its own data: the tenant's admin accounts for billing, its marketing, its product analytics.
- The vendor becomes controller (and liable as such) when it decides purposes on tenant data: training a model on it,
  cross-tenant benchmarking, selling insights, using it for its own marketing. Each needs its own basis and usually
  the tenant's contract terms. Pinning the vendor as processor in a given case: to validate in the ANPD guide's text
  and the contract.
- A processor that breaks the law or the controller's lawful instructions is jointly liable (art. 42 §1 I); a
  sub-processor (cloud, e-mail, AI provider) is listed and bound by contract.
- Records of processing (art. 37) are kept by controller and processor.
- Tenant isolation is the processor's core security duty: data of tenant A reaching tenant B is an incident for both
  controllers ([hunt-isolation.md](hunt-isolation.md)).

## Encarregado (DPO) (art. 41, Res. CD/ANPD 18/2024)

- Appointed by the controller by formal written act; identity and contact public, prominent on the website; serves in
  Portuguese; can be a person or a company, internal or external; no certification required; avoid conflict of
  interest. Res. 18/2024 article numbers: to verify.
- Small processing agents are exempt but must keep a channel for data subjects (Res. 2/2022 art. 11). Whether a given
  company qualifies as small (revenue limit, high-risk exclusion of art. 3 and 4): to validate with counsel.

## Sanctions (art. 52)

- Warning; simple fine up to 2% of revenue of the last fiscal year, net of taxes, limited to R$ 50 million per
  infraction; daily fine; publicizing the infraction; blocking or deleting the data; partial suspension of the
  database or of the processing for up to 6 months; prohibition. Applied after administrative proceedings, graded by
  Res. CD/ANPD 4/2023.
- The ANPD is a special-nature autarchy with functional, technical and financial autonomy (art. 55-A, wording of Lei
  15.352/2026).

## Sources

- https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm
- https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2025/lei/L15211.htm
- https://www.gov.br/anpd/pt-br/assuntos/noticias/nova-versao-do-guia-dos-agentes-de-tratamento
- https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd
