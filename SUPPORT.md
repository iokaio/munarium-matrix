# Support

Munarium Matrix is open source under the Apache License 2.0 ([LICENSE](LICENSE)). **The license
includes no support from Ioka LLC**, and nothing in this repository is a support commitment.

## What is available to everyone

- **Questions** — GitHub Discussions on this repository.
- **Defects** — GitHub Issues, with the Matrix version, the Server version it is talking to, the
  adapter and mode involved, the asset that reproduces it, and the refusal code you got. The
  conformance scenarios are the fastest way to show a behavior that differs from the documented
  one, and the refusal registry says what each code means.
- **Vulnerabilities** — the private channel in [SECURITY.md](SECURITY.md), never an issue.
- **Compatibility** — this repository declares the range of Munarium Server versions it supports,
  and Munarium Matrix Enterprise declares the range of this repository it builds on.

Issues are read and triaged by a small team. There is no response-time commitment on this
repository, and a defect may be closed as "recorded, not scheduled" — which is a truthful answer
rather than a dismissal.

## What is not

A production support relationship. If you need one — a response target, a supported-version
window, long-term support branches, certified deployment architectures, upgrade tooling, or the
adapters for Databricks, BigQuery, Snowflake, Cube and dbt — that is **Munarium Matrix
Enterprise**, a separate proprietary product that builds on this one and is sold by subscription.
It is not open source and this license grants no right to it.

Commercial enquiries, including Munarium Enterprise and Munarium Matrix Enterprise, go to
**info@ioka.io**.

## Running it yourself

Everything needed to operate Matrix without Ioka is in the repository: the user guide, the mode
guides, the operations runbooks, the refusal registry, the adapter support matrix, and the
conformance suite that tells you whether your deployment behaves. That is deliberate. The open
edition is a complete product against the databases most applications already run, not a trial.
