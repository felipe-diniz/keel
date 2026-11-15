# Hunt: data crossing tenants

Read when auditing a multi-tenant system (SaaS where each customer company is a tenant) for personal data that one
tenant can reach from another: queries, row-level security, caches, realtime channels, jobs, search and vector indexes,
file storage, exports.

## Why this is the worst finding

In a multi-tenant SaaS each customer is usually the controller of its own users' data and the vendor is the operator
(see [law.md](law.md) §Roles). Data of tenant A shown to tenant B is a security incident in the sense of LGPD art. 46
and Res. CD/ANPD 15/2024 for every controller affected, and with health data it is almost always relevant risk
([incident.md](incident.md)). Every pattern here is P0 unless stated.

## The fix, once

- The tenant comes from the authenticated session or token on the server, never from the body, query, header or path
  the client controls. A path parameter with a tenant id is checked against the session.
- Every read and write of tenant data is scoped by the tenant: a compound `WHERE id = ? AND tenant_id = ?`, a
  repository or ORM extension that injects the scope and refuses an unscoped call, or row-level security in the
  database. Defense in depth: application scope AND database policy where the database supports it.
- Every key that can hold tenant data carries the tenant: cache keys, realtime rooms, queue payloads, index
  partitions, storage prefixes, export file names.
- A test with two tenants proves each path: tenant B asks for tenant A's id and gets 404 (not 403, which confirms the
  id exists), and list endpoints return none of A's rows.

## Patterns

### 1. Lookup by id alone (IDOR across tenants)
- Signal: `rg -n "find(Unique|First|One|ById)\(\s*\{?\s*(where:\s*)?\{\s*id\b|findById\(|WHERE id = \?" -i`, and
  `update`/`delete` by id alone. Then check the caller: does the scope come from the session?
- Fix: compound key with the tenant; a 404 for a foreign id.

### 2. List, count and aggregate without the tenant
- Signal: `findMany`/`find`/`SELECT`/`aggregate` whose `where` or `$match` lacks the tenant field; `$lookup` or `JOIN`
  that reaches a table without filtering it by tenant; `count` used for plan limits across all tenants.
- Fix: the scope helper on every query; for joins, filter both sides.

### 3. Tenant taken from the client
- Signal: `req.body.tenantId`, `req.query.companyId`, `headers['x-tenant-id']` used to scope without a check against
  the session; a tenant switcher that trusts the stored choice.
- Fix: derive from the session; a switch validates membership on every request.

### 4. Row-level security with holes
- Signal: tables with tenant data and no policy; the application connecting as a role that bypasses RLS (table owner,
  superuser, `BYPASSRLS`); the tenant setting (`SET app.tenant_id`) done per connection in a pool and not per
  transaction (a pooled connection keeps the previous tenant); `SECURITY DEFINER` functions; migrations that create a
  table without enabling RLS.
- Fix: `SET LOCAL` inside the transaction; a non-owner role for the app; a test that lists the tables without a
  policy and fails the build.

### 5. Cache key without the tenant
- Signal: `rg -n "cache\.(get|set)\(|redis\.(get|set)|memoize|unstable_cache|'use cache'|cacheTag|new Map\(\)" -i`
  and read each key: `user:${id}`, `report:${month}`, a module-level `Map` in a server process. A CDN or reverse
  proxy caching an authenticated response (`Cache-Control: public`, `s-maxage` on a route that reads cookies). A
  client cache key without the tenant survives a tenant switch in the same tab.
- Fix: the tenant in every key; `private, no-store` on authenticated responses; clear the client cache on tenant
  switch and logout.

### 6. Realtime to the wrong room
- Signal: `rg -n "\.to\(|\.in\(|join\(|broadcast|publish\(|channel\(" ` in socket, pub/sub or SSE code. A room name
  taken from the client, a join with no membership check, an emit to every connection, a payload that carries more
  than the event needs (a token or credential sent to a whole company room).
- Fix: rooms named from the session's tenant; the server authorizes each join; the event carries ids and the client
  refetches through the scoped API.

### 7. Background jobs and queues
- Signal: job payloads without the tenant; a worker that re-reads by id alone; a cron that iterates all tenants and
  shares state between iterations; a retry that runs under another tenant's context.
- Fix: the tenant in the payload, re-validated in the worker; per-tenant context reset every iteration.

### 8. Search and vector indexes
- Signal: one index or collection for all tenants queried without a tenant filter; full-text search engines and
  vector stores used for retrieval-augmented generation where the retrieval step has no tenant filter, so the model
  answers tenant B with tenant A's documents.
- Fix: a mandatory filter added server side (not by the prompt or the client), or one index per tenant; a two-tenant
  test that asks for the other tenant's content.

### 9. File storage
- Signal: object paths without a tenant prefix, predictable names (`/uploads/123.pdf`), public buckets, signed URLs
  valid for days, a download route that checks login but not ownership.
- Fix: tenant prefix plus a random id; private bucket; signed URLs in minutes, issued after the ownership check.

### 10. Exports, reports and admin views
- Signal: export or report endpoints that build the query from filters without the scope; internal admin screens
  that list across tenants without a role check and an audit trail.
- Fix: the scope helper in the export path; cross-tenant views only for a staff role, logged per access.

### 11. Existence leaked across tenants (P2)
- Signal: global unique constraints on e-mail or document that answer "already registered" for another tenant's
  person; error messages naming a foreign record.
- Fix: unique per tenant where the business allows; a neutral message.

## Review a diff

For each new query, cache key, room, job and storage path in the diff, name where the tenant comes from. "From the
session" passes; "from the request" or "not present" is a finding.
