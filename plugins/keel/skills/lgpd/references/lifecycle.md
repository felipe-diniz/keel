# Data lifecycle: minimization, retention, anonymization, transfer, records and RIPD

Read when designing a feature that collects, keeps, shares or deletes personal data: which fields to collect, how long
to keep them and how to end them, anonymize vs pseudonymize, sending data to a provider abroad (cloud, e-mail, AI),
the record of processing operations, the data protection impact report (RIPD), security by design.

Articles from the official LGPD text and ANPD resolutions, read on 2026-11-15. "To validate" marks what counsel or
the encarregado decides.

## Minimization by design (arts. 6 III, 46 §2)

- Security and privacy from the design of the product to its operation (art. 46 §2). A new feature names, per field:
  purpose, legal basis ([law.md](law.md)), who reads it, where it is stored, retention, and how it is deleted.
- Collect the least: birth year instead of birth date when age is the need; the last digits of a document for
  matching; no free-text field where a closed list does the job (free text collects health and third-party data
  nobody planned).
- Keep identifiers out of URLs, logs, analytics and error reports by default ([hunt-logs.md](hunt-logs.md)).
- Separate identity from content: health or financial content keyed by an internal id, identity in its own protected
  table, so most code never touches both.

## Retention and elimination (arts. 15 and 16)

- Processing ends when the purpose is achieved or the data is no longer necessary, at the end of the period, on the
  data subject's request (including consent revocation), or by ANPD order (art. 15).
- After the end, data is eliminated. It may be kept only for: legal or regulatory obligation; research by a research
  body (anonymized when possible); transfer to a third party within the law; the controller's exclusive use,
  anonymized and without third-party access (art. 16).
- The security duty survives the end of processing (art. 47): backups, exports and archives stay protected until
  deleted.
- In code: a retention table per data category (category, purpose, basis, period, end action: delete or anonymize,
  legal source of the period), a purge job per category with a test, and a deletion path that reaches every store
  (database, files, search and vector indexes, caches, analytics, third parties, backups by expiry).
- Health records: Lei 13.787/2018 art. 6 sets a minimum of 20 years from the last entry for paper and digitized
  records; a council resolution has been read as permanent keeping for electronic records. The period that applies to
  a given product and record type: to validate with counsel. The software makes the period configurable per tenant
  and category, never hard-coded.
- Accounting, tax and labor records have their own legal periods: to validate.

## Anonymization vs pseudonymization

- Anonymized data leaves the LGPD only if re-identification is not reasonably possible, considering cost, time and
  available technology (art. 12). Removing names is rarely enough: quasi-identifiers (zip, birth date, sex, rare
  diagnosis) re-identify.
- Techniques that move toward anonymous: aggregation with minimum group sizes, generalization (age bands, region
  instead of zip), suppression of rare values, noise. Test re-identification against the data you hold.
- Pseudonymization (hash, token, encryption) keeps it personal data; it reduces impact and is a security measure
  (art. 13 §4; art. 48 §3 lowers incident severity when data is unintelligible).
- A keyed hash (HMAC with a secret key) for joins and lookups; a plain hash of a CPF or e-mail is reversible by
  dictionary.
- The ANPD anonymization guide was still a draft (public consultation in 2024) on 2026-11-15.

## International transfer (arts. 33 to 36, Res. CD/ANPD 19/2024)

- Sending personal data to a provider abroad (cloud region abroad, e-mail, monitoring, analytics, AI model API) is an
  international transfer and needs one mechanism of art. 33.
- Mechanisms: adequacy decision for the destination country (the EU got one by Res. CD/ANPD 32/2026); the ANPD
  standard contractual clauses adopted in full and unaltered (Res. 19/2024, Annex II; the deadline to put them into
  existing contracts ended on 2025-08-23); specific clauses approved by the ANPD; global corporate rules; and the other
  cases of art. 33 (including specific highlighted consent, and the cases of art. 7 II, V and VI).
- Prefer keeping personal data in a region inside Brazil where the provider offers one; when not, the contract with
  the provider carries the clauses. The processor helps the controller verify the mechanism (Res. 19/2024 art. 4).
- Data collected directly by a foreign site from the data subject is outside the procedure.
- Which mechanism covers a given provider contract: to validate.

## Records of processing (art. 37)

- Controller and processor keep a record of their processing operations, especially those based on legitimate
  interest. Small agents may keep a simplified record (Res. 2/2022 art. 9).
- Minimum useful fields: operation, purpose, legal basis, data categories, data subject categories, sources,
  recipients and sub-processors, international transfers with mechanism, retention, security measures, system where
  it lives.
- Keep it next to the code: a feature that adds a field or a provider updates the record in the same change.

## RIPD, the data protection impact report (art. 38)

- The ANPD may require it, including for sensitive data and legitimate interest. Minimum content: the types of data
  collected, the collection method, security methodology, and the controller's analysis of measures and safeguards to
  mitigate risk.
- Write one before launch for high-risk processing: sensitive or health data at scale, children, systematic
  monitoring, automated decisions with significant effects, new technology (AI) on personal data. Res. 2/2022 art. 4
  uses these criteria to define high risk.
- No official ANPD template as of 2026-11-15 (the RIPD regulation is on the 2025-2026 regulatory agenda): use a
  structure with description, necessity and proportionality, risks per data subject, measures, residual risk, sign-off
  by the encarregado.

## Security measures (arts. 46 to 49)

- Technical and administrative measures proportional to the risk: access control by role and tenant, encryption in
  transit and at rest (field-level for sensitive data), logs without personal data and access trails for sensitive
  reads, backup and restore tested, vulnerability management, least privilege for staff and services, incident
  response ([incident.md](incident.md)).
- The ANPD security guide for small agents (2021) is a usable baseline checklist.

## Sources

- https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm
- https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/L13787.htm
- https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd/resolucao-cd-anpd-no-19-de-23-de-agosto-de-2024
- https://www.gov.br/anpd/pt-br/assuntos/regulacao/agenda-regulatoria-1
