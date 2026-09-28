# Adapter support matrix

What each adapter can actually do, and what it refuses. A row here is only
worth reading if it cites a cycle, so each one does.

**Two editions, one interface.** Munarium Matrix core — this repository — carries the adapters for
the operational databases an application already writes to, and for file and blob sources. The
adapters for analytics platforms an enterprise buys and administers separately are **Munarium
Matrix Enterprise**, a separate proprietary product that links this repository as a library and
registers them through the public `SourceAdapter` interface. The **Edition** column says which is
which.

The asset grammar does not change between them. A `DataSource` naming `databricks` parses,
validates and applies against a core build exactly as it does against an Enterprise one, and is
refused only when something tries to execute it — `adapter_not_available`, naming what would serve
it. That is what lets one set of assets move between deployments. It also means a core build never
silently substitutes a different adapter: it refuses, by name.

| Adapter | Edition | Mode A (materialize) | Mode B (query) | Replay level | Live-verified |
|---|---|---|---|---|---|
| **postgres** | core | ✅ snapshot + watermark + **cdc** (logical replication) | ✅ | `sealed_result` | cycles 7–10, 2026-08-29 ; cdc: compose, 2026-08-30 — 7/7; **watermark: the checkpoint did not advance until 2026-08-30** (the 2026-08-30 estate run read four rows twice; `postgres.watermark_advances_and_an_unchanged_source_reads_nothing` pins the fix), and the columns are the source's own declaration since the same day (`postgres.watermark_reads_the_columns_the_source_declared`) |
| **landing** | core | ✅ manifest + snapshot, over `file` and **Azure Blob** (`store: az`, managed identity — 2026-08-30) | ⊘ `not_covered` — an export serves materialization, not query contracts | `sealed_result` | cycles 7–10 (`file`); the blob transport's live proof is the estate's mode-A check, recorded in `docs/ops/test-estate.md` |
| **databricks** | **Enterprise** | ✅ over the **Change Data Feed** (`sync_modes: [Cdf]`, 2026-08-30 — a delete is a tombstone, a retention gap resnapshots); a *watermark*-mode DataSource still refuses `sync_not_covered` by design | ✅ | `source_time_travel` *(of the source; see below)* | the 2026-08-31 estate run, 2026-08-31 — **17/17** in the `databricks` tier as a per-cycle least-privilege service principal over OAuth M2M (the three-cycle arc is in the twelve-gate section; mode B first proven on 2026-08-29, CDF on 2026-08-30) |
| **sqlserver** | core | ✅ snapshot + watermark | ✅ | `sealed_result` | compose, 2026-08-30 — **7/7** in the `sqlserver` tier (the watermark scenario arrived last, and the ✅ was unearned until it did — see [the declared watermark](#the-watermark-columns-are-the-sources-not-the-adapters)) |
| **snowflake** | **Enterprise** | ✅ snapshot + watermark *(unrun; the watermark fix below is compiled and never executed here)* | ✅ *(unrun)* | `sealed_result` | **never** — no account exists |
| **bigquery** | **Enterprise** | ✅ snapshot + watermark *(unrun — mode A has not yet read live)* | ✅ | `sealed_result` | **live 2026-08-31** — 7/7 in the `bigquery` tier against a real project, first contact finding two defects the constructed fixtures had invented their way past (no scale in the query schema; scientific-notation epochs), both pinned against committed captured bytes (`tests/captured-query.json`) |
| **mysql** | core | ✅ snapshot + watermark | ✅ | `sealed_result` | compose, 2026-08-30 — **7/7** in the `mysql` tier (same as sqlserver: the watermark had no scenario until the last one) |
| **cube** | **Enterprise** | ⊘ refused — a semantic layer is not a table store | ✅ semantic | `sealed_result` | compose, 2026-08-30 — 4/4 in the `cube` tier |
| **dbt** | **Enterprise** | ⊘ refused, as cube | ✅ semantic *(unrun)* | `sealed_result` | **never** — no MetricFlow deployment exists |

Two things live on the Databricks adapter rather than in this table because
they are surfaces, not modes: the **Change Data Feed** (mode A's transport, see
below) and **Genie**, the conversational planner — which executes nothing and
therefore has no mode. See [../api/planner.md](../api/planner.md).

## The watermark columns are the source's, not the adapter's

Closed 2026-08-30; it had been a `[gap]` on the postgres row and an unearned
✅ on four others.

`DataSource.spec.sync.watermark` declares the column an incremental read
compares by, whether the comparison is inclusive, and the tie-break that stops
two rows sharing a watermark value from straddling the boundary. It was
**validated and then read by nobody**: `validate_sync` checked the pairing at
apply time, and five adapters went on to read `(updated_at, id)` because the
`SourceAdapter` trait did not carry the declaration down. A source declaring
`modified_on` therefore validated and was then queried by a column it had never
named — on Postgres a `not_covered` refusal, on the others a statement the
engine rejected. An asset field nothing reads is a lie waiting to be believed.

Three things changed:

* **`ReadMode`** carries the mode and its declaration as one value, so
  `read_batch` cannot be handed "watermark" without the columns to read by;
  `Watermark::resolve` is the single place a declaration becomes columns, and
  a watermark read with no declaration is a **refusal**, never a fallback to
  the old pair. Reading the wrong column is worse than not reading.
* **`inclusive` is honoured.** Exclusive without a tie-break stays refused
  (that is the configuration that loses rows); inclusive *without* one is
  legitimate — it re-reads the boundary rows every run — and was unreachable
  while the pair was hard-coded.
* **The checkpoint advances on every engine.** Postgres was fixed on the
  estate's mode-A check; MySQL, SQL Server, Snowflake and BigQuery all still
  returned `next_checkpoint = the checkpoint they were given`, so an
  "incremental" run re-read the whole table forever and looked like
  convergence because nothing had changed. On MySQL and BigQuery the FIRST
  watermark read was not even ordered, so the row it would have resumed from
  was whatever the engine returned last.

**How four engines carried a ✅ for a mode with no scenario:** each tier's six
scenarios were probe, decimal, parameter binding, an unmodelled type, the
snapshot marker and row security. Not one of them read a watermark. The row
said "✅ snapshot + watermark" from the day the adapter landed. There is now a
`watermark_advances_by_the_declared_columns` scenario in the `mysql` and
`sqlserver` tiers (green in compose) and
`postgres.watermark_reads_the_columns_the_source_declared` in the `postgres`
tier; each declares `(id, name)` — deliberately not the old pair — and asserts
the checkpoint came back holding an **id**, which under the convention would
have been a timestamp. Snowflake and BigQuery carry the same code and no
account to run it on, which is what *(unrun)* in the table means.

## postgres

The only adapter whose role posture is *proven* rather than configured: it
reads `pg_roles` and `pg_tables` at connect time and refuses a superuser, an
owner, or a role holding DML. Cycle 10 runs the service itself under the
restricted `matrix_owner`, so the posture the design specifies is the posture
deployed.

### Mode A over logical replication (WP-6.8, built 2026-08-30)

**Live, and it very nearly could not be.** Modes A (snapshot, watermark, **cdc**)
and B are all live on this adapter; the CDC path is proven in the `postgres`
tier, which compose stands up for $0.

#### The measurement that shaped the whole design

Logical decoding reads WAL, and **WAL is written before any policy is
consulted**. Measured on a real PostgreSQL 16: a role restricted to EMEA by a
row policy and denied the `secret` column outright — a role whose `SELECT`
returns exactly one row and cannot name `secret` at all — saw this through a
`test_decoding` replication slot:

```
table crm.opportunities: UPDATE: id[bigint]:3 ... region[text]:'AMER' secret[text]:'hush2'
table crm.opportunities: INSERT: id[bigint]:9 ... region[text]:'APAC' secret[text]:'topsecret'
```

Both denied rows, and the denied column's contents. That is a complete bypass of
row-level security **and** of column privileges, which is to say a complete
bypass of G6, through a channel the posture checks cannot see.

So `test_decoding` is **refused by name** (`cdc_slot_wrong_plugin`), and the
adapter reads `pgoutput` only — the plugin the built-in replication uses, which
applies the **publication's** column list and row filter while decoding. The
same measurement through `pgoutput` with
`FOR TABLE ... (id, name, amount, region) WHERE (region = 'EMEA')` returned only
the EMEA rows, and `secret` did not appear even in the Relation message that
describes the shape.

#### What Postgres will not let you have all at once

Both of these are engine refusals, provoked rather than read about:

| Attempt | The engine's answer |
|---|---|
| `REPLICA IDENTITY FULL` + a column list that withholds a column | "Column list used by the publication does not cover the replica identity" |
| A row filter naming a non-key column + `REPLICA IDENTITY DEFAULT` | "Column used in the publication WHERE expression is not part of the replica identity" — updates and deletes on the table are refused outright |

A source that needs a row filter on a non-key column **and** a column list that
withholds one therefore needs `REPLICA IDENTITY USING INDEX` over a unique index
covering the key and the filter's columns. The fixture does exactly that
(`CREATE UNIQUE INDEX ... (id, region)`), and it works.

#### The role posture holds

`REPLICATION` is a role attribute, not superuser: it does not bypass row
security, grants no DML and confers no ownership. A role holding it still passes
every check `introspect` makes, so **CDC did not require widening the posture**
— which is the outcome that made building this legitimate rather than a
compromise. It is checked in the CDC path only (`cdc_role_lacks_replication`),
never added to the posture, because a non-CDC source has no use for it.

The service role deliberately does not hold it. The conformance tier stages its
slots as the bootstrap superuser, which is what an operator would do — the first
run of the tier said so itself: *"Only roles with the REPLICATION attribute may
use replication slots."*

#### The slot is durable state on someone else's database

**Matrix never creates one.** A replication slot makes the server RETAIN WAL
until something consumes it: a slot nobody reads fills the disk and stops the
database, and it goes on doing that after Matrix is uninstalled. Creating one
implicitly would make Matrix the author of an outage it never announced. So
`cdc_slot_missing` refuses with the exact statement to run, and says why.

The names are a **convention** derived from the source id
(`munarium_matrix_<source>` for both the slot and the publication) unless the
DataSource declares them — `spec.sync.cdc: {slot, publication}`, either or
both, since 2026-08-30 — for the same reason: a refusal has to be able to
print the statement an operator should run, and it can only do that when the
name is derived or declared, never guessed. A declared name must be a plain
Postgres identifier (`sync.cdc-name` at validation, with its fixture), because
it is interpolated into that statement.

Retention is reported, not acted on: `cdc_retained_bytes()` returns
`pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)`, so an operator can
watch retention grow before a disk fills. Matrix is in no position to decide
that a customer's slot should be dropped.

#### Peek, then advance on the next call

`pg_logical_slot_get_changes` **consumes**: what it returns is gone from the slot
whether or not the caller managed to persist a checkpoint, so a crash in between
loses changes silently. Every read here **peeks** — non-destructive — and the
slot is advanced to the checkpoint's LSN at the start of the *following* call,
where the checkpoint's existence is itself the proof that the previous batch was
durably recorded. The cost is a little extra retained WAL between runs, which is
exactly what `cdc_retained_bytes()` exposes.

The conformance scenario asserts this directly: reading twice from the same
checkpoint returns the same three changes.

#### The first read, and which way to be wrong

A slot has no history before it existed, so the first CDC read is a **snapshot**
pinned to an LSN — and the LSN is read as the FIRST statement of the same
`REPEATABLE READ` transaction. That ordering is the whole point: it fixes the
transaction's snapshot at the moment it reads the position, so a commit that
interleaves is delivered **twice** rather than never. Duplicates are free here
because the rendering is idempotent by row path; a miss would be permanent.

#### Gaps, truncations and absent values

* **`cdc_checkpoint_gap`** — the checkpoint is behind the slot's
  `confirmed_flush_lsn`, so the WAL that held those changes has been released.
  Reported, never silently resnapshotted: that is what lets the sync worker
  record `resnapshotted: true` instead of implying continuous coverage.
* **`cdc_truncate_not_covered`** — a `TRUNCATE` means every row went away at
  once, and there is no way to render that as records. Refused rather than
  skipped, because reporting nothing would leave the collection claiming rows
  the source no longer has.
* **`cdc_unchanged_toast`** — an out-of-line value that did not change is not in
  the stream. Sealing NULL in its place would put a value in evidence the source
  never held, so the record is refused and the column is named.
* **`cdc_unsupported_message`** — a protocol message this build does not model
  is refused, not stepped over. It may be a change the collection would
  otherwise miss.

#### A delete carries the identity, and the tombstone says so

With `REPLICA IDENTITY DEFAULT` or `USING INDEX`, a DELETE carries **only** the
identity columns; everything else arrives NULL because the engine did not send
it, which is a different fact from the row having held a null. The sync worker's
tombstone wording was changed to match: it now says the fields are *"the values
the source sent with the deletion — some engines send only the row's identity"*,
which is true of both this adapter and the Databricks change feed. It previously
said "the row's last known values", which was true only of Databricks.

#### Measured — compose, 2026-08-30

`docker compose down -v && docker compose up -d postgres` (the `-v` matters:
Postgres runs its init directory only on an empty data dir, and `test.ps1` now
fails with that instruction rather than letting the tier refuse
`cdc_publication_missing` and look like a code defect).

Seven `cdc.*` scenarios green in the `postgres` tier, twice in a row and verified
with `--nocapture` so a silent skip could not read as a pass:

| Scenario | What it proved |
|---|---|
| `a_missing_slot_is_refused_with_the_statement_that_creates_it` | Matrix creates no slot, and the refusal is actionable |
| `a_slot_that_decodes_with_test_decoding_is_refused` | the policy-bypassing plugin cannot be used by accident |
| `a_publication_without_a_row_filter_on_a_secured_table_is_refused` | a secured table cannot be streamed unfiltered |
| `a_publication_that_does_not_match_the_projection_is_refused` | the column list is the policy, so it must be exact |
| `inserts_updates_and_deletes_arrive_distinguishable_with_their_lsn` | three `ChangeKind`s in commit order, each with an LSN; `900000.75` exact; delete keyed `1\|EMEA`; the AMER row and `secret` absent; replay non-consuming; resume empty |
| `a_checkpoint_behind_the_slot_is_reported_as_a_gap` | `Incomplete`, so the worker resnapshots and says it did |
| `the_slots_retained_wal_is_observable` | retention is a number an operator can watch |

The decoder itself is tested against **captured bytes** from a real PostgreSQL 16
(`src/munarium-matrix-adapter-postgres/tests/captured-pgoutput.txt`), not against
a constructed shape — eight further unit tests, including that a truncated
message refuses rather than panics.

#### What is NOT built

* **The streaming replication protocol.** This adapter reads slots through the
  SQL interface (`pg_logical_slot_peek_binary_changes`), which is pull-based and
  bounded per call. `START_REPLICATION` would give lower latency and needs a
  replication connection sqlx does not speak.
* **Proto version 2+.** Streamed in-progress transactions are not decoded; the
  adapter asks for `proto_version 1`, where a transaction arrives only once it
  has committed. That is the conservative choice for a sealer.
* **Proof that the publication's filter matches the RLS policy.** Comparing two
  SQL expressions for equivalence is undecidable, so the filter is recorded
  verbatim in the sealed coverage (`filter=...` in the marker) and the
  equivalence is **an operator's assertion**. That is a weaker guarantee than
  RLS, and it is the honest limit of this path.

## landing

Immutable CSV/JSONL exports over `file://` or, since 2026-08-30, an **Azure
Blob container** read with the process's managed identity (`connection:
{store: az, account, container, prefix}`; the blob endpoint is the egress
host and must be in `allowHosts`). The estate had carried a landing storage
account and a `Storage Blob Data Reader` assignment for Matrix's identity
since Phase 0 while the adapter could read only a filesystem — so the Phase 2
live scenario "manifest sync from blob via managed identity" was unrunnable
for a phase and a half, and the docs index said "`file` only" as if that were
a choice. The client is `object_store`'s, built `from_env()` exactly as the
server's own blob store is, because Container Apps have no classic IMDS and a
client built any other way black-holes against a link-local address.

Refuses `execute` by design (`capabilities().query_contracts == false`), and
refuses any sync mode but manifest/snapshot, because an immutable export has no
watermark and no change feed and declaring either "would be a support claim we
cannot honour". No S3 or GCS transport: nothing needs one yet, and a transport
with no live proof is a support claim too.

## databricks

**Mode B is live.** Statement Execution API, OAuth M2M or a bearer token,
serverless SQL warehouse. Verified 2026-08-29 against a premium workspace in
`centralus`.

### The twelve gates of review §5.9, and which of them ran

The Phase 3 exit gate asks that "the Databricks gate list states which gates
ran". The review's §5.9 lists twelve; **seventeen** `databricks.*` scenarios
exist (the `databricks` tier, `test-cycle.ps1 -Databricks`, last green on
the 2026-08-31 estate run at 17/17, 2026-08-31 — the funded three-cycle arc
three runs that day that closed most of what was open below;
the two red cycles' findings are in `docs/ops/test-estate.md`). Stated per
gate rather than as a count, because a count would hide which residuals
remain and why:

| §5.9 gate | State | Scenario / where it is proven |
|---|---|---|
| 1. OAuth credentials rotate without asset changes and never appear in logs or evidence | **proven for M2M** (2026-08-31); no log-scrubbing scenario | `credentialRef` resolves at call time, so rotation is a secret change, not an asset change; the results file records `auth: pat \| oauth_m2m` and never the credential. **OAuth M2M ran on the 2026-08-31 estate runs** — the AAD-application premise dissolved (the workspace's `/oidc/v1/token` takes a Databricks-managed OAuth secret its admin can mint over the API), so the estate's DEFAULT credential is a per-cycle service principal whose secret never outlives the cycle |
| 2. The principal holds only the intended workspace/warehouse/catalog/schema/table permissions | **closed** (the 2026-08-31 estate run) | the tier RUNS as a per-cycle principal granted exactly warehouse CAN_USE + the fixture schema read-only, and `databricks.the_principal_cannot_reach_beyond_its_grants` asserts the boundary against an ungranted schema — least privilege by a principal that IS least-privileged, loud-skipping under a PAT where the assertion would be about an admin |
| 3. Unity Catalog row filters and column masks survive Statement API queries; a denied value cannot be reached through a sealed artifact | **closed** (the 2026-08-31 estate run) | `databricks.a_row_filter_and_column_mask_survive_the_statement_api` over `holdings_secured` — an UNCONDITIONAL filter (EMEA for everyone, so the expectation is credential-independent) admits two of three rows and the masked amount arrives NULL on the same wire path every sealed result takes |
| 4. Parameter types, row/byte limits, cancellation, async polling, external-link expiry, `truncated` | **closed for the paths this adapter takes** (the 2026-08-31 estate run) | types/polling as before; `databricks.the_engine_truncates_at_the_row_limit_and_says_so` (100k rows behind a 1000-row engine-side limit, `truncated: true`); `databricks.a_statement_past_its_deadline_is_cancelled_not_awaited` (~10⁸ hashed join pairs against a 6s deadline — the transport-races-the-wait defect this found is in cycle 31's entry). External links stay deliberately unexercised: the adapter requests `INLINE` with the engine-side row limit by design, so link expiry is a path it does not have |
| 5. A metric-view query matches a hand-verified result across joins, non-additive measures, nulls, decimal scale, timezones | **partly → nulls and timezones closed** (the 2026-08-31 estate run) | the original grouped-measure scenario, plus `databricks.metric_view_groups_in_the_declared_zone_and_sum_skips_nulls` over `pipeline_monthly` — a 23:30 UTC boundary row that is June in UTC and July in Europe/Paris, and a NULL that leaves the sum without leaving the count, both hand-verified. Joins and non-additive measures remain un-fixtured |
| 6. A metric-view definition change invalidates verification before cutover | **proven** | the same scenario: the fingerprint is re-read before every execute and a moved definition is `metric_view_changed`; offline, `semantic.*` provoke it before any statement |
| 7. CDF: insert, update pre/post-image, delete, duplicate delivery, checkpoint restart, schema drift, retention-gap resnapshot | **partly → the drift half closed** (the 2026-08-31 estate run) | insert/update/delete with `_commit_version` as before; `databricks.change_feed_survives_an_add_column_without_misalignment` walks the feed ACROSS an `ADD COLUMN` and asserts the post-boundary record's VALUES — the dangerous failure is positional, and rows after the boundary carry one more column. The retention gap stays the offline `cdf_checkpoint_gap` path; duplicate delivery stays unexercised live |
| 8. A sealed result remains replayable after the table changes and after time travel expires | **proven** for the first half | `databricks.source_time_travel_returns_the_prior_state` mutates the fixture and re-reads the prior version by hash; G1 replay after expiry is the server's evidence plane (`evidence.replays_after_the_source_changes`), engine-independent by construction |
| 9. Policy-protected time travel is refused rather than run through an over-privileged principal | **closed** (the 2026-08-31 estate run) | `databricks.policy_protected_time_travel_is_refused` — `VERSION AS OF` on the row-filtered, column-masked `holdings_secured` arrives as a typed refusal carrying the engine's reason, never as rows |
| 10. Genie records enough plan identity to explain which path ran, else `genie_plan_unpinned` | **built, NOT proven live** | `docs/api/planner.md`; no Genie space exists between cycles |
| 11. Volume and OpenSharing reads do not bypass the governance boundary | **closed as decided** (2026-08-31) | the adapter reads tables through the Statement API only; volumes and shares are refused by having no code path — decided the *permanent* answer, with the reopen condition recorded in decisions.md (a customer source whose governed rows are reachable only through one of them) |
| 12. `statement_id`, query tags and system-table correlation connect cost/lineage to the journal | **built; correlation is ENVIRONMENT-BOUND**, measured twice | `statement_id` retained; **query tags built 2026-08-31 and flowing on every recorded cycle since** (`munarium_product: matrix`, `munarium_source: <DataSource name>`; fixed underscore keys because the API refuses `,:-/=.` in a key, values truncated at its 128-char ceiling, absent tags serialize to no field). The correlation scenario reads `system.query.history` as the OPERATOR credential — cost/lineage is an operator activity — and two 2026-08-31 estate runs measured that NEITHER credential an ephemeral cycle holds can be granted the system schemas (they are a metastore admin's, on a shared regional metastore the cycle does not administer). It therefore gates on `MUNARIUM_MATRIX_LIVE_DATABRICKS_SYSTEM_TABLES`, an operator's assertion the grant exists on a standing workspace, and skips loudly under `test-run.ps1`'s one named exemption |

After the 2026-08-31 arc: **eight of the twelve are proven or closed**
(1's M2M half, 2, 3, 4, 6, 8's first half, 9, and 11-as-decided), gate 12 is
built with its correlation environment-bound, and the honest residuals are
NARROW and named in their rows — gate 1's log-scrub scenario, gate 5's joins
and non-additive measures, gate 7's live duplicate delivery, gate 8's
post-expiry half (the server's engine-independent evidence plane), and gate
10's Genie space. The never-executed parameterised bind also executed on the
arc (`databricks.a_named_parameter_binds_rather_than_interpolates`, a hostile
value staying data). `databricks.execute_reports_no_snapshot_marker`,
`databricks.introspect_reports_the_fixture_schema` and
`databricks.materializing_by_watermark_is_refused_naming_the_feed` prove
properties the twelve do not name (G7 refusals and G3 markers). Each open
row names a fixture that does not exist, which is what closing it takes.

**Mode A is live over the Change Data Feed** (WP-4.3, built 2026-08-30), and
only over it: the adapter declares `sync_modes: [Cdf]`, and a `watermark`
DataSource is refused naming the modes it does declare — a watermark query
re-reads unchanged rows, cannot see a delete, and leaves a checkpoint with no
engine position. The first read pins the table's Delta version with `DESCRIBE
HISTORY` and reads `VERSION AS OF` it, so the snapshot and the checkpoint name
one commit; every later read asks `table_changes()` for the commits after
the checkpoint and returns one record per post-image — inserts, updated
post-images, deletes — each stamped with its `_commit_version` as the event
position, pre-images dropped. **A delete is a record**: the sync worker
renders it as a tombstone document at the row's own path, saying the row is
gone and at which position, so a reader who cites it learns the fact. When
the feed no longer holds the commits after a checkpoint the engine's error
reaches the worker as `cdf_checkpoint_gap`, and the worker re-reads the whole
entity from a start checkpoint (`resnapshotted: true` on the outcome) rather
than report coverage of changes it never saw; a table without the feed is
`cdf_not_enabled_or_supported`. The fixture creates `opportunities` with
`delta.enableChangeDataFeed = true`; the live scenario is
`databricks.change_feed_returns_inserts_updates_and_deletes_with_their_versions`,
**green on the 2026-08-30 estate run** (Databricks tier 8/8): an insert, an update
post-image and a delete each came back as a record stamped with its
`_commit_version`, pre-images dropped, the checkpoint advanced to the last of
them, and a read from that checkpoint returned nothing. The two feed codes are
provoked offline from captured engine messages in the classifier's own test; a
real retention gap cannot be staged on a fresh table and is recorded as such.

One thing cycle 22 taught before that: the change-feed and time-travel
scenarios mutate the SAME fixture table and `cargo test` runs test functions
concurrently, so the feed correctly returned the other test's commits and the
assertion was what was wrong. They take turns over a `FIXTURE_LOCK` now — the
table is the shared resource, and giving each its own would have fixed the
test by testing something else.

**Native data views** (WP-6.3): this adapter also serves a `DataView` — one
fact table, the aggregates declared in the asset, dimensions as columns —
with the same fingerprint gate as a metric view (`definition_of` reads the
catalog definition). Postgres serves them too (`information_schema.columns`
as the definition); landing does not.

### `source_time_travel` — measured, and narrower than the word suggests

The capability declares `replay_level: source_time_travel`, which the crate
itself calls "the strongest claim any adapter makes". Measured:

| | |
|---|---|
| Delta time travel works | **yes** — after mutating the fixture, the same query at `VERSION AS OF 2` returned the pre-mutation rows byte-for-byte (`2950000.75`, and the identical grouped result) |
| The statement response carries a version | **no** — `manifest` holds only `chunks`, `format`, `schema`, `total_chunk_count`, `total_row_count`, `truncated` |

So the claim is true of the **source** and not yet substantiable from a
**read**. Pinning a version needs a second `DESCRIBE HISTORY`, which is not
atomic with the statement — a concurrent write between the two pins the wrong
version — so `execute` reports `snapshot_marker: None` rather than a marker
that rests on a race. `tests/captured.rs` asserts the absence against captured
bytes, so if a future API version adds one, the test fails and the gap closes.

**G2 now has a conformance scenario** (2026-08-29, the second half of that
day). `databricks.source_time_travel_returns_the_prior_state` mutates the
fixture, runs the same query at the version read *before* the mutation, and
asserts the `logical_result_hash` matches — the identity a seal uses, not the
rendered text. It runs in the `databricks` tier, which
`test-cycle.ps1 -Databricks` stands up and tears down.

What was demonstrable by hand for a day and a half was a paragraph, and a
paragraph cannot fail. G2 had been at **zero scenarios since Phase 0**, which is
the state ground rule 4 exists to forbid.

The narrower statement survives and has its own scenario:
`databricks.execute_reports_no_snapshot_marker` asserts that `execute` reports
`None`, because a statement response still carries no version and pinning one
needs a `DESCRIBE HISTORY` that is not atomic with the statement. If a future
API version adds one, that test fails — which is how the gap closes rather than
being forgotten.

### Metric views (WP-6.1, built 2026-08-29)

The semantic tier, and on this adapter only. The `metric_views` capability
says the engine has a semantic layer with `MEASURE()` semantics; Postgres and
landing keep it `false` and refuse `metric_not_covered` by name. Three pieces:

- **`definition_of`** reads `SHOW CREATE TABLE <view>` — for a metric view
  that is the whole `CREATE VIEW … WITH METRICS LANGUAGE YAML AS $$…$$`
  statement, measures and dimensions included, which is exactly what a
  fingerprint has to cover. `munarium_matrix_core::semantic::fingerprint`
  hashes it LF-normalised and trimmed.
- **The `MetricView` asset** (design-assets §4.3.1)
  references the view by catalog identity and declares the closed lists: which
  measures a caller may ask for (typed, with scale, unit and additivity),
  which dimensions may be grouped by, which of those may be filtered, and a
  ceiling on dimensions per question. Matrix never copies a measure formula.
- **The compiler** (`core::semantic::compile`) turns a bounded intent —
  measures, dimensions, `eq` filters — into the one SQL shape a metric view
  answers: `SELECT dims, MEASURE(m) … GROUP BY dims ORDER BY dims`, filters
  bound by name (`:fN`, which is how this adapter binds), dimensions as the
  ROW KEY so every row is citable by its grain, and a zero-dimension ask keyed
  by a constant `grain = 'total'` column because a one-row result with no key
  cannot be sealed. Anything outside the lists is `metric_not_covered`.

**The gate.** `verify` runs the asset's questions under the definition the
source reports now and records that definition's fingerprint
(`matrix.metric_view_verifications`, migration 0005). `execute` reads the
definition again, BEFORE the statement, and refuses `not_covered` with no
passing record on file or `metric_view_changed` when the fingerprint moved —
so a semantic change upstream becomes a governed drift event, never a
silently different number. `metric_view_changed` spends budget like
`schema_drift`: the definition was read, so the source was reached.

**Measured — the 2026-08-29 estate run.** The estate's Databricks fixture
creates `pipeline_metrics` over `opportunities`, and
`databricks_metric_view_is_fingerprinted_and_answers_measure_sql_by_grain`
(under `-Databricks`) passed against the real warehouse: `SHOW CREATE TABLE`
returned the metric-view definition, `MEASURE()` returned `AMER`/`EMEA` keyed
by region with EMEA's `2520000.50` keeping its trailing zero and AMER's only
(Closed Won) deal contributing zero, and a `CREATE OR REPLACE` of the view
moved the fingerprint — the fact `metric_view_changed` rests on. Databricks
tier **7/7**, conformance **56/56**, the estate's own verify check green with
its first evaluated invariant, estate and managed group verified destroyed.

**One thing this found while being built, unrelated to metric views.** The
compiler renders every contract placeholder positionally (`$1`, `$2`) while
this adapter sends parameters by NAME to the Statement Execution API, which
reads `:name`. A parameterised query contract on Databricks has therefore
never been executed with its parameter bound — the captured statement and
the live tier use unparameterised statements. The semantic path is unaffected
(it emits `:fN` and binds by name). Recorded here rather than assumed either
way; a `-Databricks` cycle with a parameterised contract settles it.

## Measured — the first automated Databricks run, 2026-08-29

The first automated Databricks cycle (`test-cycle.ps1 -Databricks`), recorded in
`conformance/results/7t8ueuqb.json`:

| | |
|---|---|
| Provision (estate + workspace) | **456 s** |
| Workspace `Succeeded` → API answering → warehouse `RUNNING` → fixture seeded | inside that |
| Catalog | `dbx_mxtest_7t8ueuqb` — auto-provisioned, named after the workspace with dashes folded; asked for, not assumed |
| Auth | `personal_access_token`, minted for the cycle with a 1 h lifetime (OAuth M2M needs an AAD application this estate's identity cannot create) |
| `databricks` tier | **6 passed, 0 failed, 14.88 s** — including `source_time_travel_returns_the_prior_state`, G2's first scenario |
| Whole cycle, create to verified-destroyed | **18.7 min**, exit 0; managed group `rg-mxtest-dbx-7t8ueuqb-managed` verified gone |

## Measured cost, 2026-08-29

| | |
|---|---|
| Workspace create → `Succeeded` | **3 m 29 s** (the plan estimated ~15 min) |
| Warehouse create → first statement | seconds; a 2X-Small serverless warehouse had no perceptible cold start |
| Whole live session, create to destroy | **~7 minutes** |
| Warehouse | 2X-Small serverless, `auto_stop_mins: 5` |
| List rate | $0.70/DBU-hour Premium Serverless SQL, `centralus` |

Teardown deletes the workspace, which takes its managed group — and with it the
NAT gateway that bills hourly whether or not a cluster runs. Verified: both
groups empty afterwards.

**A correction to the risk register.** It named "Unity Catalog metastore not
available to a Terraform-created workspace" as the thing that would block this.
It did not happen: Azure auto-provisions a metastore and a default catalog named
after the workspace (`dbx_mxtest`). The only adjustment needed was not assuming
the catalog is called `main`.

## Genie (Databricks planner surface, WP-6.6)

Not a mode and not an adapter row: Genie **executes nothing**. It proposes, and
`munarium-matrix-workers::genie` decides what may run.

| | |
|---|---|
| Where the policy lives | `munarium-matrix-core::planner` — vendor-neutral by construction, so the deciding code names no vendor and the next planner arrives without its own policy |
| Where the wire lives | `munarium-matrix-adapter-databricks::genie` — the Conversation API's paths and response shape, decoded into a neutral `PlannerMessage` |
| Seam | `SourceAdapter::planner_ask`, returning `Ok(None)` for "I have no planner", exactly as `semantic_execute` does |
| Declared in | `spec.connection.genie` — adapter-owned by design, so no other adapter carries a field it can never use and the cross-tree contract does not move for a vendor feature |
| Allowlist | **required and never empty**; `trustedAssets` matched exactly, never by prefix; `allowedTables` non-empty is what admits *generated* SQL at all |
| Modes | `assist` returns the admitted SQL for the caller to run through a contract; `evaluation` records and **admits nothing**, and is off by default |
| Pin | space / conversation / message / attachment / statement ids and a query hash — with `pinned: false`, because no vendor API returns a space's configuration |
| Live-verified | **never.** No workspace exists between cycles, and a Genie space is not something the cycle script creates. |

**What `genie_plan_unpinned` means, exactly:** the sealed bytes are replayable
and the *decision* that produced the query is not. It is a label riding a real
result, not a failure — and the envelope says so in words rather than leaving a
reader to infer it from a `false`.

**What will happen in practice:** a planner's SQL frequently will not survive
the contract path, because the allowlist walk refuses `SELECT *`, subqueries,
non-deterministic functions and undeclared tables, and a generative surface
writes all of those. That is the design working. A query Matrix cannot verify is
a query Matrix will not seal.

## cube

**A semantic provider, not a database** (WP-6.2, built 2026-08-30). Cube owns
the metric definitions; Matrix declares in a `DataView` which of them a caller
may ask for and what type each answer arrives as, checks an ask against those
closed lists, and passes the NAMES across to `/cubejs-api/v1/load`. There is no
statement to compile and no formula to copy — which is the whole argument of
the review's §4.2, that a customer who already encodes metrics in Cube should
not restate them in a second YAML dialect.

The trade is explicit. Matrix cannot walk a statement here, so the bound it
enforces is the asset's lists plus Cube's own policy, and the sealed manifest
says `cube:` in front of the asset ref so a reader of an answer knows whose
definitions produced the number. `definition_of` returns the cube's entry from
`/cubejs-api/v1/meta` — measures, dimensions, types — so a redefined measure is
`metric_view_changed` exactly as a redefined Databricks metric view is.

| Mode | State |
|---|---|
| A (materialize) | **Refused.** A semantic layer is not a table store; `sync_modes` is empty and a `sync` block on a cube source is a validation error (`datasource.semantic-provider-sync`), so the asset cannot promise it. |
| B (query contract) | **Refused by name.** Matrix does not write SQL against someone else's semantic layer. |
| B (semantic) | **Live.** `data_views: true`, `semantic_provider: Some("cube")`. |
| C (reconcile) | Not applicable: mode C reads rows through mode A. |

`snapshot_marker` is `None` and `replay_level` is `sealed_result`: Cube may
answer from its own pre-aggregation cache, so a marker naming the upstream
would be a claim this adapter cannot support. The honest guarantee is the
sealed bytes.

**Measured — compose, 2026-08-30.** `docker compose --profile cube up -d`
brings up Cube v1.1 over the same Postgres the rest of the suite uses, reading
the model in `fixtures/cube/model/` (Cube's, not Matrix's) over the table in
`fixtures/t0/sql/04-cube-fixture.sql` (one Postgres init directory, so a
fresh compose volume loads it -- it was mounted nowhere until 2026-08-30). Four `cube.*` scenarios green: the probe reaches the
deployment; a bounded ask comes back keyed by its dimension with three status
groups and the summed decimal `1150001.00` — its scale intact through Cube's
JSON, which is the property the whole evidence identity rests on; a filter
narrows to the two EMEA groups through Cube's own `equals` operator rather
than by string-building; and the definition fingerprints identically twice
while an unknown cube is `not_covered`.

**One defect this found, in Matrix and not in Cube.** The asset validator's
`credential.literal` heuristic treated any value containing `://` as a
connection string with secrets — so a Cube or dbt source, which is REACHED at
a base URL, could never have been registered at all. The same shape as the
40-character hostname rule that cycle 19 caught, and found the same way: by a
source that could not be applied. The rule now catches what actually matters,
userinfo in the authority (`scheme://user:pass@host`), and a plain URL is a
location.

## dbt (Semantic Layer / MetricFlow)

Built the same day, the same seam: `createQuery` with metrics, group-by and
`where` predicates over `Dimension('name')`, then poll `query` until
`SUCCESSFUL` **inside the caller's deadline** — a query still running when the
deadline passes is `deadline_exceeded`, not a promise nobody sealed. The one
place a caller-supplied VALUE reaches the provider is a filter predicate, and
its quotes are doubled (a unit test drives `O'Brien' OR 1=1 --` through it).
Column lookup tolerates the warehouse's casing, because a lookup that only
tried the exact name would silently produce all-NULL rows — worse than a
refusal.

**`[gap]` — unmeasured beyond its unit tests.** The dbt Semantic Layer is a
**cloud** service with no OSS container, so there is nothing to stand up in
compose. Its live tier is env-gated (`MUNARIUM_MATRIX_LIVE_DBT_*`) like the
provider smokes, and no such run has happened: everything above about the
GraphQL shapes is written from the documented API and is a claim until a
recorded run replaces this paragraph. **The tier is REGISTERED as of
2026-08-31** — four `dbt.*` conformance scenarios (probe; a bounded ask keyed
by its dimension with the async query id retained and no snapshot marker;
fingerprint stability + `not_covered` on an unknown metric; statements
refused by name), gated on `MUNARIUM_MATRIX_LIVE_DBT_URL` with `_TOKEN`,
`_ENVIRONMENT_ID`, `_METRIC` and `_DIMENSION`, skipping loudly — so the
eventual account has something it can FAIL, which until then no paragraph
could. The assertions are shape-and-identity properties of ANY MetricFlow
environment, because a cloud service has no seedable fixture.

## mysql

**The second SQL engine behind the same seam** (WP-6.8, built 2026-08-30), and
the reason to build it was to find out what the seam had assumed about
Postgres. Modes A (snapshot, watermark) and B (query contracts, native data
views) are live; there is no CDC, so the plan's binlog path stays unbuilt
rather than implied — a watermark read cannot see a delete, and this adapter
does not pretend otherwise.

**Four defects a real server found on first contact**, none of them reachable
offline:

1. **Transaction characteristics must come BEFORE the transaction.** Postgres
   accepts `SET TRANSACTION` as the first statement inside one; MySQL answers
   1568/25001 "Transaction characteristics can't be changed while a
   transaction is in progress". The session is now configured on one acquired
   connection and the transaction opened on that same connection — a pool
   hands out a different session each time, and settings applied to another
   would be a no-op nobody would notice.
2. **Transaction control cannot be prepared.** sqlx prepares by default;
   MySQL answers 1295 "not supported in the prepared statement protocol yet"
   for `START TRANSACTION`. Executing a bare `&str` runs it as a simple query.
3. **`SHOW GRANTS` returns VARBINARY**, not VARCHAR — a decode-time type
   mismatch, invisible at compile time.
4. **So does `information_schema`.** Both are cast in SQL rather than decoded
   as bytes in four places.

**Three things it made explicit about the seam.** Quoting is per engine
(`` `ident` `` here, `"ident"` there). A snapshot marker is not universal:
MySQL's analogue is a GTID set, which exists only with GTID mode on — off by
default and off in the fixture — so the adapter reports one when the server
has one and `None` when it does not, and its `replay_level` is
`sealed_result`, the honest floor. And row-level security is not a given:
MySQL has no policy engine, so `introspect` REPORTS `subject_to_row_security`
as failing rather than omitting the check — a reader comparing postures across
engines must see that this protection is absent here and is supplied by
per-class grants and views instead.

Two decoding decisions worth keeping. An UNSIGNED BIGINT that does not fit
`i64` is refused rather than wrapped, because a wrapped id cites the wrong
row. And `TIMESTAMP` (stored UTC) and `DATETIME` (no zone) map to different
canon@1 types, which is the distinction the whole value layer exists for.

**Measured — compose, 2026-08-30.** `docker compose --profile mysql up -d`
brings up MySQL 8.4 with the fixture in `fixtures/mysql/`. **Seven** `mysql.*`
scenarios green: the probe reaches it; `900000.50` survives the driver with
its trailing zero; a bound parameter binds (the compiler's `$1` renumbered to
`?` in the adapter, so one plan hash runs on both engines); a GEOMETRY column
is refused `schema_drift` naming the column rather than guessed at; a snapshot
read reports no marker because the server has none; `introspect` reports
row security as absent; and a watermark read advances its checkpoint by the
columns the source DECLARED — the seventh, added 2026-08-30, which is when
this row stopped claiming a mode nothing tested.

## sqlserver

**The third SQL engine behind the same seam** (WP-6.8, built 2026-08-30), and
the first one whose differences from Postgres are about *guarantees* rather
than syntax. Modes A (snapshot, watermark) and B (query contracts, native data
views) are live. Change tracking could serve a change feed; reading a version is
not reading one, so `sync_modes` says what is built.

**Measured — compose, 2026-08-30.** `docker compose --profile sqlserver up -d`
brings up SQL Server 2022 Developer with the fixture in `fixtures/sqlserver/`.
**Seven** `sqlserver.*` scenarios green against a real engine, run as the
fixture's row-level-secured `matrix_reader` login rather than as SA:

| Scenario | What it proved |
|---|---|
| `probe_reaches_a_real_server` | TDS connect, TLS, login |
| `an_exact_decimal_survives_the_driver` | `900000.50` keeps its trailing zero through TDS, which carries a decimal as an integer plus a scale — and the read ran under `snapshot` isolation, reported as such |
| `a_positional_parameter_binds_rather_than_interpolates` | the compiler's `$1` renumbered to `@P1`, bound, four EMEA rows |
| `an_unmodelled_type_is_refused_and_names_the_column` | `geography` AND `money` refused `schema_drift`, each naming its column and its type |
| `a_snapshot_read_reports_a_marker_only_from_a_consistent_view` | four rows (the policy is in force), `ct:<n>` marker, every record stamped with it |
| `introspect_reports_row_security_as_present` | the policy is OBSERVED on `opportunities` and absent on `shapes`; the schema-wide claim is correctly false |
| `watermark_advances_by_the_declared_columns` | a watermark read by `(id, name)` — the DECLARED pair, not `[updated_at]`/`[id]` — advances the checkpoint, and the resumed read returns nothing. Added 2026-08-30; before it, `next_checkpoint` handed back the checkpoint it was given |

### What a real server found that nothing offline could

**1. The driver PANICS on a spatial column, before any row exists.** (True of
`tiberius` 0.12.3, the driver at the time; `tiberius-ng` 0.13, adopted the same
day, fixes it — see the decision below. The finding stands because the
pre-flight it forced is still the design.) tiberius
`todo!()`s while parsing the column-metadata token for a `Udt` — which is how
`geography`, `geometry` and `hierarchyid` all arrive
(`tiberius-0.12.3/src/tds/codec/type_info.rs:317`). The first version of this
adapter refused an unmodelled type from the driver's own result metadata, which
is what the MySQL adapter does; against a real server that call brought the test
process down instead of returning a refusal, so the refusal was unreachable for
exactly the type that most needed it.

The fix is engine-native rather than defensive: `execute` and `read_batch` now
ask `sys.dm_exec_describe_first_result_set` what the statement WILL return,
before running it. It names every output column and its type as text, costs a
plan compilation and no execution, and lets the adapter refuse by name. A
statement the engine cannot describe is refused rather than attempted — fail
closed, because the alternative here is a panic. It buys two things beyond
survival: a bad contract costs a compile rather than a scan, and the check is
the engine's opinion of the statement rather than a parse of it in Rust.

**2. Proving the posture needs a metadata grant a data reader has no other
reason to hold.** SQL Server filters catalog metadata by permission, so a login
with `db_datareader` sees ZERO rows in `sys.security_predicates` — and
`introspect` would report "no row security" for a table that has it. Measured
by revoking it: with `GRANT VIEW DEFINITION` the fixture's reader sees one
enabled predicate; without it, none. An absence of evidence read as evidence of
absence, on the one check where that is most dangerous. Postgres has no
equivalent trap because `pg_catalog` is world-readable. The fixture grants it
and says why; a deployment that does not grant it gets a posture that
under-reports, which is the safe direction but must not be mistaken for a fact.

**3. `DATABASEPROPERTYEX(DB_NAME(), 'SnapshotIsolationState')` returns NULL to a
least-privileged reader**, and a NULL there would have read as "snapshot
isolation is off" and silently downgraded every read to read committed —
which would in turn have suppressed the snapshot marker. `sys.databases`
answers the same question for the same login and is used instead.

### Three things it made explicit about the seam

**T-SQL has no read-only transaction.** Postgres has `SET TRANSACTION READ
ONLY`; MySQL has `START TRANSACTION READ ONLY`; SQL Server has neither.
Read-only here is a property of the PRINCIPAL and of the TOPOLOGY, so the
adapter proves it in `introspect` (server role, database roles, and
INSERT/UPDATE/DELETE/ALTER permission on the schema) and sets
`ApplicationIntent=ReadOnly` on the connection, which is a no-op on a
standalone server and a real engine-enforced guarantee against an availability
group listener. Writing "the transaction is read only" in this adapter would
have been a comfortable sentence about a flag that does not exist.

**Characteristics come before the transaction, on the same session** — the same
rule MySQL taught, for a different reason: SQL Server refuses SNAPSHOT
specifically (3951), while accepting other isolation changes inside a
transaction. This adapter opens a FRESH session per operation rather than
pooling, because `SET LOCK_TIMEOUT`, `SET ROWCOUNT` and the isolation level are
all session state and a pooled session handed back carrying any of them is the
next caller's silent problem. One TDS handshake per operation buys the property
outright; the MySQL adapter had to pin a connection out of its pool to get the
same thing.

**Transaction control cannot go through the parameterised path.** tiberius's
`query()` is an `sp_executesql` RPC, and changing `@@TRANCOUNT` inside a
procedure is error 266 on return; `simple_query()` sends a plain batch. Same
shape as MySQL's 1295, arriving for a different reason.

### A marker, and the condition on it

`snapshot_marker` is `ct:<version>` from `CHANGE_TRACKING_CURRENT_VERSION()`,
and it is reported **only** when change tracking is on AND the transaction
actually started in snapshot isolation — which is the arrangement Microsoft's
own change-tracking guidance prescribes, because the version then names the
same consistent view the rows came from. Read outside a snapshot transaction it
would be a number that raced the read. The presence half is proven live; the
`None` half (change tracking off, or a read committed transaction) is asserted
by `snapshot_marker_for`'s unit tests, because one fixture cannot be in both
states at once. `replay_level` stays `sealed_result`: a change-tracking version
is a POSITION, not a retained history, so there is nothing to re-run against.

### `money` is refused, on purpose

`money` and `smallmoney` are EXACT four-decimal currency types on the server and
IEEE-754 doubles in this driver (`money.rs`: `read_i32_le() as f64 / 1e4`). A
currency silently becoming a float is the precise failure canon@1 exists to
prevent, so both are unmodelled types and a read of one is refused naming the
column and the type. A deployment that needs the column casts it in the
contract's statement. The fixture carries a `money` column so the refusal is
reached rather than merely written.

### `[decision, taken 2026-08-30]` — the driver moved to `tiberius-ng`

sqlx dropped its MSSQL driver in 0.7 and has not brought it back, so this is the
only adapter that cannot ride the workspace's driver. `tiberius` 0.12.3 — the
last release upstream published — pins `tokio-rustls` 0.24 → `rustls` 0.21 →
`rustls-webpki` 0.101, which carries **RUSTSEC-2026-0098**, **-0099**
(name-constraint validation accepted where it should not be) and **-0104** (a
reachable panic parsing CRLs). The first two are certificate-chain flaws in the
path this adapter walks on every connect, not something reachable only through
an unusual API call.

**There was no in-range fix.** The advisories are answered by `rustls-webpki`
≥ 0.103 and `rustls` 0.21 cannot take it, so `cargo update` had nothing to
offer. Three moves existed: the fork, suppress the gate, or drop SQL Server
support.

**The fork was taken.** `tiberius = { package = "tiberius-ng", version = "0.13" }`
is the entire change — no source edits — and after it:

| | |
|---|---|
| `cargo deny check advisories` | **-0098, -0099 and -0104 are gone**; `rustls` 0.21 leaves the graph entirely, leaving one `rustls` 0.23.43 |
| `boundary: no openssl` | still clean — `default-features = false` remains load-bearing, because the defaults include `native-tls`. What the check does NOT ban, since 2026-08-30: `openssl-probe`, which is in the graph BECAUSE of `rustls-native-certs` and links nothing. The old prefix match could not tell the two apart and failed CI on it (`scripts/boundaries.py`) |
| the `sqlserver` tier | **6/6** against the same compose fixture, `an_unmodelled_type_is_refused_and_names_the_column` included (7/7 since the watermark scenario landed) |
| one of the two `rustls-pemfile` paths | gone with it |

**What was accepted, stated rather than buried.** `tiberius-ng` is one
maintainer and, at the time of writing, one published version. An unaudited
crate running in-process with a database credential is a real supply-chain
risk, and it is not smaller than the CVEs merely because it is newer. It was
taken because the alternative was shipping a driver whose certificate
validation is known-broken while a gate stayed green by suppression.

**Re-evaluate when:** upstream `tiberius` publishes past 0.12.3 — switching
back is the same one-line `package =` rename — or `tiberius-ng` goes quiet, or
any advisory lands against it.

A side effect worth knowing: `tiberius-ng`'s `type_info.rs` handles the `Udt`
token that made the pinned crate panic. The `describe_first_result_set`
pre-flight **stays anyway**. Asking the engine is the fail-closed design
independent of any driver bug — it refuses an unmodelled type by NAME rather
than after a decode, it is the only thing that would catch the next such token,
and a refusal that depends on the driver being correct is a refusal that moves
when the driver does.

### `cargo deny` is green, with two reasoned ignores

`advisories ok, bans ok, licenses ok, sources ok`.

Two advisories are ignored, each with the condition that revokes it recorded in
`deny.toml`:

- **RUSTSEC-2023-0071**, the Marvin timing sidechannel in `rsa`, reached
  through `sqlx-mysql`. There is no fixed release, so it cannot be updated
  away. **Not reachable here, and that was checked by reading the dependency
  rather than inferred from the advisory title**: Marvin recovers a PRIVATE key
  from DECRYPTION timing, and `sqlx-mysql/src/connection/auth.rs` imports only
  `RsaPublicKey` and calls only `encrypt` — this process holds no RSA private
  key and performs no private-key operation. The path is skipped outright over
  TLS as well (`if stream.is_tls { return Ok(to_asciz(password)) }`).
- **RUSTSEC-2025-0134**, `rustls-pemfile` unmaintained, now one path (tonic).
  An *unmaintained* advisory, not a vulnerability; the server tree carries the
  same entry for the same reason, since both trees pin the same tonic.

`cargo deny check licenses` had also been failing on a first-party rule: four
crates added since WP-6.2 — `adapter-cube`, `adapter-dbt`, `adapter-mysql` and
`proto` — had no `[[licenses.exceptions]]` stanza, so the gate was red over
something with nothing to do with third-party licence drift. Those four joined
the three new adapters, and that half is green.

## snowflake

**Built 2026-08-30, and NEVER RUN.** No Snowflake account exists and one was not
created.

| | |
|---|---|
| Proven | request shaping, `$1`→`?` rewriting, ordinal-keyed bindings, the closed type map, decimal rescaling, epoch/offset timestamp parsing, hex `BINARY`, error classification by SQLSTATE then error code, the egress check, config validation — **13 unit tests**, all against the API's DOCUMENTED shape |
| NOT proven | every byte of it. No live call has been made. The response fixtures are constructed from documentation, not captured |
| Tier | six `snowflake.*` scenarios, `#[ignore]`d behind `MUNARIUM_MATRIX_TEST_SNOWFLAKE`, each printing **SKIPPED** when it is unset |

Every adapter in this workspace that reached a real engine found defects on
first contact that a document could not have shown — a driver that panics on a
spatial column, a grant a catalog read silently needs, a statement type the
prepared protocol refuses, `SHOW GRANTS` returning VARBINARY. There is no reason
to expect this one to be the exception, and the first job when an account exists
is to replace the constructed fixtures with captured bytes and see what breaks.

**Two decisions worth knowing before that happens.**

*The identifier-folding trap.* Snowflake folds an unquoted identifier to UPPER
CASE at creation, so a table made as `create table opportunities` is stored as
`OPPORTUNITIES` and a query for `"opportunities"` — quoted, and therefore
case-sensitive — finds nothing. `quote_ident` upper-cases an all-lowercase name,
reproducing what the engine would have done to it unquoted, and passes through
a name that already carries case because it was evidently created quoted.

*The one documented ambiguity, and how it is NOT guessed at.* The JSON result
format returns every value as text, which is what makes an exact decimal
survivable at all: `NUMBER(18,2)` holding 900000.50 arrives as `"900000.50"`.
What the documentation does not settle is whether a whole value arrives as
`"900000"` or `"900000.00"`. Both are handled the same way — parse as a decimal,
then rescale to the column's declared scale — so `"100000"` at scale 2 becomes
`100000.00`. The alternative reading, that a dot-less string is an UNSCALED
integer (which some drivers do return), is deliberately **not** implemented: the
two differ by a factor of 100, and choosing between them from documentation
would be exactly the confident guess this layer exists to refuse.
`snowflake.an_exact_decimal_survives_the_wire` is the scenario that settles it.

`snapshot_marker` is `None` and `replay_level` is `sealed_result`. The statement
handle IS a position — `AT (STATEMENT => handle)` reads the table as of that
statement, and the handle arrives in the SAME response as the rows, so unlike
Databricks there is no race — but no account exists to measure it, and a
capability is a promise rather than a plan. The handle is reported as
`statement_id`. A unit test asserts the absence, so upgrading the claim is a
deliberate act.

## bigquery

**Built 2026-08-30, and NEVER RUN.** No BigQuery project exists and one was not
created.

| | |
|---|---|
| Proven | request shaping (`parameterMode: NAMED`, `maximumBytesBilled`, `defaultDataset`), `$1`→`@p1` rewriting, the closed type map including the REPEATED refusal, scale recovery, base64 `BYTES`, epoch timestamps with microsecond padding, error classification by `reason`, the 200-carrying-errors case, the egress check — **14 unit tests**, all against the API's DOCUMENTED shape |
| NOT proven | every byte of it. No live call has been made |
| Tier | seven `bigquery.*` scenarios, `#[ignore]`d behind `MUNARIUM_MATRIX_TEST_BIGQUERY`, each printing **SKIPPED** when it is unset |

**The decimal problem is the sharpest of the three engines.** BigQuery renders a
`NUMERIC` MINIMALLY: `900000.50` goes out as `"900000.5"`. The trailing zero is
recovered from the column's DECLARED scale, which a parameterised
`NUMERIC(18,2)` reports in the response schema — an adapter that trusted the
text would seal `900000.5` and every hash downstream would differ from the same
row read on any other engine. An unparameterised `NUMERIC` reports no scale, and
the value's own is then the honest answer.

**A numeric JSON value is refused rather than decoded approximately.** Every
value in this API arrives as a JSON string, including 64-bit integers, which is
what keeps them exact. If that ever changed, a `to_string` would work for most
values and silently round a large one — so a non-string scalar is a
`schema_drift` refusal instead, which makes the change loud.

**BigQuery has no escape for a backtick in an identifier.** Postgres doubles
`"`, MySQL doubles `` ` ``, SQL Server doubles `]`; this engine offers nothing,
so `quote_ident` REFUSES such a name rather than producing a statement that
means something else. BigQuery's own identifiers cannot contain one, so this
costs nothing real and closes an injection shape by construction.

`source_side_limits` is **true** and means something specific here:
`maximumBytesBilled` makes the engine refuse an oversized query BEFORE it scans,
which on an engine billed by bytes read is the ceiling that matters — it is the
only source-side limit in this workspace that costs money when it fails open.
`bigquery.a_query_over_the_byte_ceiling_is_refused_before_it_scans` is the
scenario for it.

`snapshot_marker` is `None`, and that is a considered answer rather than a gap
in the engine. BigQuery has real time travel (`FOR SYSTEM_TIME AS OF`), but
`jobs.query`'s response carries no query-start timestamp, so the only timestamp
available is the CLIENT's clock — and a write landing between the client reading
its clock and the engine starting the query would make the marker name a state
the rows never had. Appending `CURRENT_TIMESTAMP()` to the caller's statement
would change the result shape, and therefore the plan hash and the sealed
identity. A unit test and a live scenario both assert the absence, so a future
API that carries a start time closes the gap by failing.

## Placeholders and quoting, across the five SQL adapters

The compiler renders ONE plan with Postgres-style `$1` placeholders, and the
plan hash is over the parsed AST — so the hash does not move when the engine
does. Each adapter rewrites on the way in:

| Adapter | Identifier quoting | Placeholder | Rewritten where |
|---|---|---|---|
| postgres | `"ident"` | `$1` | not rewritten |
| mysql | `` `ident` `` | `?` | `positional_to_question_marks` |
| sqlserver | `[ident]` | `@P1` | `positional_to_at_p` |
| snowflake | `"IDENT"` (folded) | `?` + ordinal bindings | `positional_to_question_marks` |
| bigquery | `` `ident` `` (no escape) | `@p1` + named parameters | `positional_to_named` |
| databricks | `` `ident` `` | `:name` | emitted named by the semantic compiler |

In every case a placeholder beyond the bound count is left alone: if the
compiler and the binder ever disagree, the engine must see the discrepancy and
refuse rather than receive a placeholder with nothing bound.

### The semantic compiler's dialect table — found here, FIXED 2026-08-30

`core::semantic::SemanticScope::with_dialect` mapped `"databricks"` to
backtick/named and **everything else** to double-quote/positional. Correct for
postgres and sqlserver (which accepts `"ident"` under QUOTED_IDENTIFIER, on by
default for TDS clients) and correct for snowflake apart from case folding —
but **wrong for mysql and bigquery**: MySQL reads `"opportunities"` as a string
literal unless `ANSI_QUOTES` is set, and the compose fixture's
`--sql-mode=STRICT_ALL_TABLES` does not set it. A native `DataView` on a MySQL
source emitted a statement that runs and means something else.

**The catch-all was the defect, not the missing rows.** A default that produces
a plausible statement for an engine nobody taught it about fails as a wrong
ANSWER rather than as a refusal, and a wrong answer from a system built for
verifiable evidence is the worst failure it has.

`try_with_dialect` is now exhaustive over the six dialects an adapter reports —
databricks (`` ` ``/`:name`), postgres (`"`/`$1`), mysql (`` ` ``/`?`),
snowflake (`"`/`?`), bigquery (`` ` ``/`@name`), sqlserver (`[`/`@name`) — and
**refuses an unknown one by name**. Two tests pin it: one walks all six, one
asserts the refusal. `Quoting::Bracket` and the two new placeholder styles came
with it.
