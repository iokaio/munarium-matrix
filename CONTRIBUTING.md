# Contributing to Munarium Matrix

Contributions are welcome from anyone. What follows is the whole process; there is no contributor
license agreement to sign.

## Rights and license

- **Every commit carries a Developer Certificate of Origin sign-off**: `git commit -s`, which adds
  `Signed-off-by: Your Name <you@example.com>`. By signing off you certify the
  [DCO](https://developercertificate.org/) — that the work is yours to submit under this
  repository's license, or that you have the right to submit it. A pull request with an unsigned
  commit fails its check.
- **Accepted code is Apache-2.0**, the license of the whole repository ([LICENSE](LICENSE)), by
  section 5 of the license itself: a contribution intentionally submitted for inclusion is licensed
  under the same terms, copyright and patent alike. That is why no CLA exists; a CLA would add the
  right to relicense your contribution later, and that right is not wanted.
- A contribution grants no right to Munarium Enterprise and changes nothing about Ioka's trademarks
  ([TRADEMARK.md](TRADEMARK.md)) or the support boundary ([SUPPORT.md](SUPPORT.md)).

## Disclosure

The pull request template asks four questions; answer each, and "none" is an answer:

1. **third-party code** — any file or fragment you did not write, with its license;
2. **generated code** — what generated it, from what;
3. **AI-tool provenance** — which tools helped, and that you reviewed every line;
4. **employer or contractual restrictions** on what you may contribute.

You must have the right to submit every file in the pull request.

## Process

1. Fork the repository (maintainers: a topic branch) and make the change.
2. Run the gates below. Every new source file carries `SPDX-License-Identifier: Apache-2.0` on its
   first line — the second, after a shebang or an XML declaration — and `check_license.py` names
   any file that does not.
3. Open a pull request against `main`. Public CI runs the offline suites with no private
   credential. Anything needing a deployed environment runs on `main` after merge, never on a pull
   request from a fork.
4. A code owner reviews ([.github/CODEOWNERS](.github/CODEOWNERS)); Ioka squash-merges. External
   pull requests never gain deployment or release authority.

## Gates

| Gate | Command |
|---|---|
| The tiered test ladder | `.\test.ps1` (offline: unit tests, boundaries, contract checks, doclint), `-Gates` for fmt and clippy, `-Postgres`, `-BlackBox`, `-MySql`, `-Browser`, `-All` |
| Formatter and lints | `cargo fmt --all --check`; `cargo clippy --workspace --all-targets -- -D warnings` |
| Dependency policy | `cargo deny check` |
| License | `py check_license.py` — manifests, SPDX headers, license texts |
| Repository hygiene | `py scripts/private_material_scan.py`; `gitleaks dir . --config .gitleaks.toml` |
| Client records | `py clients/check_compatibility.py` and `py clients/check_license.py` |
| `clients/python` | `ruff check`, `ruff format --check`, `mypy`, `pytest` |
| `clients/dotnet` | `dotnet build` (warnings are errors), `dotnet test` |
| `clients/java` | `./gradlew build` |

Rules the gates enforce that are easy to trip:

- **Every cited conformance cycle has a results file.** `scripts/doclint.py` fails when a document
  names a cycle the repository cannot show, and it fails on a dead link in the documents it scans.
- **The boundary rules hold.** `scripts/boundaries.py` rules on the shipping dependency graph at the
  musl target: no Munarium Server crate in it, a pure kernel, rustls only, additive migrations, and
  no Matrix Enterprise adapter crate.
- **The conformance registry is generated.** `SCENARIOS.md` drifts and a test fails; add a scenario
  by registering it, not by editing the table.
- **`contract/` is normative and versioned.** A change to it is a version bump and a re-publish that
  the Server repository then vendors, never a hand edit on either side.
- **The adapter interface is public API.** `munarium-matrix-adapter` is depended on by Munarium
  Matrix Enterprise and by third-party adapters; a breaking change to it is a major version.

## Conduct and venues

[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) applies everywhere in this project. Questions go to GitHub
Discussions, defects to Issues, and suspected vulnerabilities to the private channel
[SECURITY.md](SECURITY.md) names — never to a public issue or a proof-of-concept pull request.

## Protected files

Only Ioka changes `LICENSE`, `NOTICE`, `TRADEMARK.md`, this file, `CODE_OF_CONDUCT.md`,
`SECURITY.md`, `SUPPORT.md`, anything under `.github/`, the contract directories, and any signing
or release configuration. A pull request that touches them is declined unless a maintainer opened
it.
