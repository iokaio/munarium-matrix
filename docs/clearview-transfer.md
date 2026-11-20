# ClearView Matrix transfer inventory

The [ClearView transfer plan](https://github.com/iokaio/munarium/blob/0791d06f3020a8a0d06d646ca407c210b84721b8/server/docs/design/repository-handoffs.md#m1)
puts Matrix publication and interoperability ahead of the Server switch.
Comparison sources are Server v1.4.0 at `25012c22087fbaa8ce29ddd68d2880d6e9499b1c`,
Munarium main at `bb18085f3d407e9b77d551fbf7ac68a6572fce27`, and Matrix main at
`643863fcb4433c8236f3ab22ca812f17c354f34c`, fetched on 19 November 2026. The
released Server container is pinned by [its OCI index digest](https://github.com/iokaio/munarium/blob/25012c22087fbaa8ce29ddd68d2880d6e9499b1c/server/CONTAINER.md#last-published-image-140).

| Released Server source or section | Blob or tree | Comparison and disposition |
|---|---|---|
| `server/contract/matrix/` (all 18 paths) | `ad2e73bbd913b4f8373aa1130f953dda3c7a0e1c` (tree) | Same tree on Server main. Matrix's `contract/` reproduces all 17 files covered by the lock and its digest. Preserve the full 0.1.0 bundle at the publisher and export the version, exact digest and verified source separately. The tree ID plus its paths identify every released blob. |
| `server/src/munarium-core/src/evidence.rs` | `8be2254082984049e68d1c7931ed066c120f3321` | Same on main. Retain Server evidence behavior and replace the compile-time `VERSION` include with the generated pin at cutover. |
| `server/src/munarium-api-types/tests/matrix_contract.rs` | `0234cb612d96ffe67554fb9f7af30bb9b7ccb225` | Same on main. Run the DTO test alongside the Matrix publisher's file lock and schema checks. Keep Server-specific assertions and switch external vectors to a pinned input when Server changes layout. |
| `server/src/munarium-server/src/evidence_providers.rs` | `d36a25654658d8099320814bc09528961d7c05e8` | Same on main. Keep Server authorization, sealed evidence, result mapping and breaker handling. Matrix owns the peer request/response fixtures. |
| `server/src/munarium-server/src/evidence_hierarchy.rs` | `12e67afce165b3133ab639769aa2da9ca486227c` | Main uses `serde-saphyr` for metric-view YAML. Preserve the current parser and qualify typed selections and historical runbooks on the Server candidate. |
| `server/src/munarium-cli/src/matrix.rs` | `e2966849fc3fd024606d9febecebd04a2917c099` | Same on main. `server/src/munarium-cli/src/main.rs` changed its independent YAML parser. Matrix exports all ten legacy commands and tests forwarding from the bundled CLI. Keep the shim through the standalone consumer and package comparison. |
| `server/docs/ops/mmctl.md`, Matrix commands and environment | `a1ee9bf3001ccbf677a5a6c96e34323760ef0502` | Same on main. The [Matrix operator guide](user-guide.md#mxctl-and-mmctl-matrix) holds the crosswalk. Retain the Server entry point and link to the crosswalk at cutover. |
| `server/docs/guides/evidence-hierarchy.md`, integration and field report | `11c52077747ffb018eddd4110e58a819162512de` | Same on main. Matrix owns the [query guide](guides/mode-b-query.md#structured-evidence-from-a-server-runbook) and [peer diagnosis](ops/runbooks.md#3-the-circuit-breaker). Server retains its evidence rules, report reference and configuration links. |
| `server/tools/check_matrix_contract.py` | `d45b60c7091b658de644b88220df146191c2bf2b` | Same on main. Matrix publishes the source and tests the frozen lock and profile. Retain this checker until the replacement gate validates the standalone Server inputs. |
| `.github/workflows/server-ci.yml` and `server/tools/gate-catalog.json` | `1d848471dab218372c16930356a240aea481e9b7`, `36190d539cb33289b01c6528cbc73c04aa2f18fa` | Same on main. The Matrix workflow covers the original bundle and both Server source refs. The Server cutover must update the workflow, catalog, equivalence baseline and negative controls together. |
| `README.md`, `server/deploy/helm/munarium/README.md`, `server/docs/guides/validation.md`, Matrix links and instructions | `e802c2522ecfa9854c1778f0245ae17635c9b0dc`, `2728e7206f5b89e6e33e69a853381891339980f2`, `d326d0f2c8298ea6f2dafabc52e076c485206ccd` | Main has newer release text in the root and Helm guides. Matrix owns its operating procedures. Preserve Server chart values, environment names and Server checks when replacing Matrix instructions with links. |
| `server/src/munarium-server/src/main.rs`, `config.rs`, and `server/docs/api/openapi.json`, Server report and peer configuration | `7546f3021ee0cd4ec569b1081904c89b321dd08c`, `d184e6493832285f4409d160417b683fd0b9bdc7`, `d35d3c104b22ed7a4806e0e48c6f36659fedab39` | Retain `/v1/reports/matrix`, `/admin/matrix`, `matrix:` sources, `matrix.` findings and the provider metric in Server. Compare configured, unconfigured and unavailable peers. |
| `server/docs/api/grpc-reference.md` and `clients/server-api.json`, Matrix report and evidence surfaces | `c7ba085880a989116c9d6db860eecd9ac9a49864`, `48c4900319730016ee22c273362e75678728f915` | Retain Server's typed gRPC `MatrixReport` and four SDK surfaces. Qualify them with the released clients. Matrix's own clients stay here. |
| `server/Dockerfile`, bundled `/mmctl` | `447a8cbf0d151511cc84c39f0a12aaa80adc932f` | Retain the Server image entry point. The same CLI fixture can exercise the release and later candidate images with no extra CLI in the container. |

## Per-path evidence

Blob identities were rechecked on 19 November 2026 with `git rev-parse` against
Server v1.4.0 (`25012c2`) and Munarium main (`bb18085`, unchanged since the
inventory was pinned). "Same" means the blob or tree ID is identical at both.
Reviewer confirmation is recorded by the owning maintainer and is not implied by
this table.

| Released path | v1.4.0 → main | Evidence already collected | Receipt still required before removal | Reviewer confirmation |
|---|---|---|---|---|
| `server/contract/matrix/` | Same tree `ad2e73b` | Lock and digest reproduce 17 files; eight examples validate | M1-T1 export pin consumed by a standalone Server build | Pending |
| `munarium-core/src/evidence.rs` | Same `8be2254` | 5 Server contract tests | M1-T1 build with the generated pin replacing `VERSION` | Pending |
| `munarium-api-types/tests/matrix_contract.rs` | Same `0234cb6` | 5 Server contract tests | M1-T1 run against the pinned external vectors | Pending |
| `munarium-server/src/evidence_providers.rs` | Same `d36a256` | 16 evidence-provider tests; 11 live worker tests against the v1.4.0 image | M1-T2 Server calling an installed Matrix peer | Pending |
| `munarium-server/src/evidence_hierarchy.rs` | `12e67af` → `2b4e249` (YAML backend change, Server #83) | None specific to the new parser | Typed-selection and historical-runbook replay on the Server candidate | Pending |
| `munarium-cli/src/matrix.rs` | Same `e296684` | Ten verbs match source build and v1.4.0 image binary | M1-T2 standalone package comparison and v1.4 rollback | Pending |
| `munarium-cli/src/main.rs` | `7e3408a` → `d3abb5e` (YAML parser) | CLI fixture forwarding | Same as above; parser change stays Server-owned | Pending |
| `server/docs/ops/mmctl.md` | Same `a1ee9bf` | Crosswalk in the Matrix user guide | Link check after cutover | Pending |
| `server/docs/guides/evidence-hierarchy.md` | Same `11c5207` | Matrix query and runbook guides exist | Link check after cutover | Pending |
| `server/tools/check_matrix_contract.py` | Same `d45b60c` | Frozen lock and profile tested here | Replacement gate validates standalone Server inputs | Pending |
| `server-ci.yml`, `gate-catalog.json` | Same `1d84847`, `36190d5` | Matrix workflow covers bundle and both Server refs | Server workflow, catalog, baseline and negative controls changed together | Pending |
| Root and Helm READMEs, `validation.md` | Root `e802c25` → `287ad12`; Helm `2728e72` → `6ea2a64`; validation same `d326d0f` | None | Newer release text preserved when links replace instructions | Pending |
| Server `main.rs`, `config.rs`, `openapi.json` | Same `7546f30`, `d184e64`, `d35d3c1` | Live worker suite (Matrix calling Server) | Configured, unconfigured and unavailable peer comparison | Pending |
| `grpc-reference.md`, `clients/server-api.json` | Same `c7ba085`, `48c4900` | None | COMPAT-T2 replay with the four released SDKs | Pending |
| `server/Dockerfile` | Same `447a8cb` | v1.4.0 image binary extracted and compared | Candidate image comparison with the same CLI fixture | Pending |

## Validation record

The lock and all eight wire examples were verified locally. The exported command
profile matched `mmctl` built from the Server design checkout at `0791d06` and
the exact Linux binary extracted from the published v1.4.0 image.
The Matrix live worker suite passed all 11 tests against that Server image with
disposable PostgreSQL, including sealing, replay and reconciliation.
The workflow records results for the released and current Server sources. The
CLI fixture establishes forwarding, and the live worker suite covers Matrix
calling Server. Server calling a real installed Matrix, v1.4-to-v1.5 upgrade and
rollback across the same data, the four SDKs, candidate package isolation and
per-row reviewer confirmation remain required before source removal. Retain the
original configuration and vendored bundle until the relevant receipts pass.

The [Lens repository](https://github.com/iokaio/munarium-lens/tree/8cf7f040c06bd215cb536b9e06ec3e8f3415bdfb)
has the CPU-only scaffold described in the plan. Its locked offline suite passed
the loopback, typed HTTP 503 and shutdown checks on 19 November 2026. Model serving
and Lens qualification remain open.
