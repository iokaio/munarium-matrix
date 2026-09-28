# Munarium Matrix — release notes

## 1.2.0 — unreleased, the standalone repository

Matrix and its three clients move from `iokaio/munarium` (`matrix/` and
`clients/matrix-*`) to their own repository, `iokaio/munarium-matrix`, and the
service, its container image and its clients take one version number, 1.2.0.
Matrix 1.1 was never released; the number follows the clients' 1.1.1.

- **No wire change.** The REST, gRPC and MCP surfaces, the contract under
  `contract/` (VERSION unchanged), the asset grammar and the refusal registry
  are the 1.0.0 ones. The clients' API is unchanged.
- Update rustls to 0.23.45 and refresh third-party notices.
- The workspace, the Helm chart (`0.2.0`, app `1.2.0`) and the client
  packages name this repository. The Server's vendored copy of the contract,
  `server/contract/matrix/` in `iokaio/munarium`, is unchanged; a future
  contract version is re-vendored there from a published cut.
- Local validation receipts use this repository's own copy of the shared
  receipt runner (`tools/validation.ps1`) and are written under
  `scratch/validation/`. The contract drift check against the Server's
  vendored copy runs when a Server checkout is at hand and is otherwise
  recorded as not requested.
- The compose `server-source` profile builds the Server from a sibling
  `iokaio/munarium` checkout (`../munarium/server`, or `MUNARIUM_SERVER_SOURCE`).

### Accepted limitations

- `contract/README.md` still describes the single-repository layout. It is part
  of the published contract bundle, so it changes with the next contract cut,
  never by a hand edit.

## 1.0.0

The first public release.

**What 1.0 commits to.** The wire contract, the asset grammar, the refusal
registry and the adapter interface, all under semantic versioning. It does not
claim every planned capability is finished. The list below is that gap, stated
rather than implied.

### Accepted limitations

- **Core ships four adapters**: `postgres`, `mysql`, `sqlserver` and
  `landing`. The analytics-platform adapters — Databricks, Snowflake,
  BigQuery, Cube and dbt — are **Munarium Matrix Enterprise**, a separate
  proprietary distribution, and their crates are not in this repository.
- **The asset grammar does not change between editions.** A core build still
  *accepts* a DataSource naming one of those adapters, and refuses it at
  execution by name with `adapter_not_available`, rather than failing to parse
  it. That is deliberate: the grammar is one contract, and a refusal that says
  which product serves the asset is more useful than a parse error.
- **Out-of-tree adapters register through `adapters::AdapterRegistry`.** The
  `AdapterFactory` trait is the public seam; there is no patch point inside
  `runtime::open_adapter`.
- **The conformance registry describes this repository.** 86 scenarios across
  six tiers — offline, postgres, grpc, http, mysql and sqlserver — every one of
  which this tree can build and run, on compose or on every push. Scenario
  names for adapters that are not here are not listed: a registry that
  advertises coverage the tree cannot execute is the failure mode the suite
  exists to prevent.
- **The Helm chart's image repository is required and empty by default.**
  Rendering fails until you supply an image repository. Build the image from
  this repository and make it available to your cluster.

### Verification

`cargo clippy --workspace --all-features --all-targets -- -D warnings` and
`cargo test --workspace --all-features` are both green, and both run in CI.
`scripts/boundaries.py` enforces the adapter inventory, the no-server-crate
rule, the rustls-only rule and the additive-migration rule.
