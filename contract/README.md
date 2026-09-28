# The Munarium Matrix cross-tree contract

This directory is **the** boundary between `matrix/` and `server/`. It is the
only thing the two trees share: `matrix/` never depends on a `server/` crate and
`server/` never depends on a `matrix/` crate (ground rule
1).

## What is here

| File | Normative content |
|---|---|
| `VERSION` | The contract version. One line, semver, no `v` prefix. |
| `canonicalization.schema.json` | `canon@1` — the evidence-identity rules. Not a message: a machine-readable specification the two hashes are computed under. |
| `query-intent.schema.json` | Server → Matrix. The typed intent a turn's layer executes. |
| `evidence-manifest.schema.json` | Matrix → server. What sealing registers; also what `GET /v1/evidence/{id}` returns. |
| `evidence-block.schema.json` | Matrix → server. The closed set of things a layer can contribute to an answer. |
| `observation-batch.schema.json` | Matrix → server. Mode C typed observations and their origin. |
| `refusal.schema.json` | Either direction. A typed refusal, never a generic error. |
| `examples/` | One valid document per schema plus the edge cases the tests care about. Every example is deserialized by both trees' test suites. |

## Compatibility rule

The version in `VERSION` is semver over the **wire meaning**, not over the file
bytes:

- **patch** — examples, descriptions, or comments change. No consumer action.
- **minor** — a new optional field, a new enum value in an *open* enum, a new
  example. Old producers and old consumers keep working. A consumer MUST
  ignore fields it does not know and MUST NOT fail on an unknown value in an
  open enum.
- **major** — a required field is added or removed, a field changes type or
  meaning, or a **closed** enum gains a value. Both trees change together.

Closed enums (a new member is a major bump): `EvidenceBlock.kind`,
`Refusal.code`'s *class* set, `QueryIntent.kind`, `Observation.change_kind`,
`ColumnType`. Open enums (a new member is a minor bump): `Refusal.code` itself,
`replay_level`, `adapter`.

The rule that makes this safe in practice: **producers are strict, consumers
are tolerant.** Matrix validates every document it emits against these schemas
in debug builds and in conformance; both trees' deserializers ignore unknown
fields on the wire even though the asset parsers use `deny_unknown_fields`.

## How the two trees stay in sync

`matrix/contract/` is the source. `server/contract/matrix/` is a cut of it made by
[`publish.py`](publish.py) — every file here verbatim (UTF-8, LF, no BOM) plus a
`contract.lock` with the contract version, the source commit, a sha256 per file and a
digest over the list. A change lands in one commit that edits this directory, moves
`VERSION`, and re-cuts the copy:

```bash
python contract/validate_examples.py                              # the contract is self-consistent
rm -rf ../server/contract/matrix && python contract/publish.py --out ../server/contract/matrix
python contract/publish.py --check ../server/contract/matrix      # identical to what this tree cuts
python contract/publish.py --self-test                            # two cuts are byte-identical
```

Two checks keep it true, and they differ by whether the other tree is present. Where it
is (this repository), both CIs run `--check`: the copy must equal a fresh cut, source
commit ignored. Where it is not (a standalone Server repository, phase 2 of the
commercial repository plan), the server's `matrix_contract` test verifies its copy
against the lock — the same rule as `--verify`. Until 2026-09-03 this was a `diff -r`
that only worked with both trees in one checkout.

Read the files as bytes when you compare them. A console redirect on Windows adds a
BOM and produces false drift — the server's own OpenAPI drift check carries that scar
(`utf-8-sig` in `server-ci.yml`); the publisher normalizes so a cut is the same bytes
on every platform.

## Publication, once the trees are separate repositories

`matrix-release.yml` cuts the bundle on every `matrix-v*` tag (`publish.py --out`) and
attaches it to the run as the `munarium-matrix-contract` artifact, lock included, beside
the image's SBOM — so a contract version is published exactly when the Matrix that speaks
it is. The Server side of the sync (a workflow that fetches the bundle for the contract
version its `contract.lock` names and opens, but cannot merge, the pull request that
re-vendors it — repo-planning.md §10.2) needs the two repositories to exist and is phase 6
work; until then the same commit rule above is the whole mechanism.

## Notes for implementers

- **Hashes** are lowercase hex with an algorithm prefix: `sha256:<64 hex>`.
- **Timestamps** are RFC 3339 with an explicit offset, normally `Z`.
- **Decimals** are JSON **strings**, never JSON numbers — a decimal(38,2) does
  not survive an IEEE-754 double. `canon@1` fixes the text form.
- **Bytes** are base64 (standard alphabet, padded).
- A field that is absent and a field that is `null` mean the same thing:
  *not supplied*. Neither is "empty".
