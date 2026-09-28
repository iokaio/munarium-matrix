# Munarium Matrix — documentation index

Start with the repo-level [README](../README.md) for what Matrix is and how to
run it. This index covers everything else.

## Using it

| Document | What it answers |
|---|---|
| [user-guide.md](user-guide.md) | Author a DataSource, a QueryContract and a ClaimMapping; apply them; read a refusal. |
| [adapters/build-matrix.md](adapters/build-matrix.md) | **What each adapter can actually do, and what it refuses** — mode A/B support, replay level, and the cycle behind each row. |
| [architecture.md](architecture.md) | The shape in one sitting: three modes, seven guarantees, the runtime roles, the two ground rules, and how a query actually flows. |
| [errors.md](errors.md) | **The refusal registry** — the six closed classes, every code, and which refusals spend budget. Kept honest by a test. |
| [api/rest.md](api/rest.md) | The REST surface, beside the generated [openapi.json](api/openapi.json). |
| [guides/mode-a-materialize.md](guides/mode-a-materialize.md) | Mode A: render source rows into a governed collection, and why a watermark cannot see a delete. |
| [guides/mode-b-query.md](guides/mode-b-query.md) | Mode B: contracts, metric views and native data views — one execution path, and what makes a result sealable. |
| [guides/mode-c-reconcile.md](guides/mode-c-reconcile.md) | Mode C: shadow first, the two promotion gates, and why rollback is supersession. |
| [ops/runbooks.md](ops/runbooks.md) | Resnapshot, retention and legal holds, the circuit breaker — each with the reasoning that decides whether to act. |
| [guides/admin-ui.md](guides/admin-ui.md) | **The operator console** (`/admin`): every page, the configure loop, and why exporting a bundle is the default path. |
| [security/admin-ui.md](security/admin-ui.md) | The console's threat model, its header set, and — stated plainly — what it does **not** defend against. |
| [api/grpc.md](api/grpc.md) | The gRPC data plane: one server-streaming `Execute`, and why a refusal rides the stream as a message. |
| [api/mcp.md](api/mcp.md) | The MCP toolset: pre-declared tools from the assets, no free SQL, an evidence id on every answer. |
| [api/planner.md](api/planner.md) | Conversational planners (Genie): it proposes, Matrix decides — and why `genie_plan_unpinned` is a label rather than a failure. |
| [../deploy/helm/munarium-matrix/README.md](../deploy/helm/munarium-matrix/README.md) | The Helm chart (SI-6.4): one Deployment per role, installed beside the server's chart — **installed and probed on a real cluster (kind) 2026-08-30**: five pods Ready, role isolation structurally intact, and it found the missing health descriptor in gRPC reflection that rendering never could. |
| [../scripts/doclint.py](../scripts/doclint.py) | The §18.3 lint: every cycle a document names has a results file, or a reason in `conformance/results/UNRECORDED`. Runs in `test.ps1` and CI. |
| [../ui-smoke/smoke.mjs](../ui-smoke/smoke.mjs) | The console through a real browser (`test.ps1 -BlackBox -Browser`); the source of the guide's screenshots. |
| [../contract/README.md](../contract/README.md) | The cross-tree wire contract, its versioning rule, and how it is vendored. |
| [../conformance/SCENARIOS.md](../conformance/SCENARIOS.md) | Every conformance scenario, its tier, and the guarantee it proves. Generated — a test fails if it drifts. |
| [../fixtures/t0/README.md](../fixtures/t0/README.md) | The adversarial fixture and every trap planted in it. |

`matrix/fixtures/assets/` is worth reading as documentation in its own right:
`valid/` is four annotated, complete assets, and `invalid/` holds one file per
fail-closed rule, **named for the finding code it produces**.

## Designing it

The design set was written before the code and is kept as the record of what
was decided and why. Where the code has since taught us something, the plan
documents carry ✎ correction markers rather than being silently rewritten.

| Document | Contents |
|---|---|

## Building it

The plan is phased, and each phase document states its own exit criteria.

| Phase | Document | Status |
|---|---|---|


## The one rule that shapes everything

`matrix/` never depends on a `server/` crate, and `server/` never depends on a
`matrix/` crate. `contract/` is the only thing they share, and CI fails the
build if the dependency graph says otherwise. Everything Matrix needs from the
server it gets over REST, against schemas that are versioned and vendored into
both trees.
