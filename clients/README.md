# Munarium Matrix client libraries

REST clients for [Munarium Matrix](../README.md), the structured-evidence
plane, in Python, .NET and Java. Each is deliberately small: Matrix's surface
is registering assets, running the three modes, and reading what happened.
The clients for Munarium Server live in
[iokaio/munarium](https://github.com/iokaio/munarium/tree/main/clients).

**License: Apache-2.0** ([LICENSE](LICENSE), [NOTICE](NOTICE)). Contributing is
a signed-off pull request with no CLA ([CONTRIBUTING.md](../CONTRIBUTING.md));
suspected vulnerabilities go to the private channel in
[SECURITY.md](../SECURITY.md); what is and is not supported is in
[SUPPORT.md](../SUPPORT.md).

| | Python | .NET | Java |
|---|---|---|---|
| Package | [`munarium-matrix`](python/) (import `munarium_matrix`) | [`Ioka.Munarium.Matrix.Client`](dotnet/) (net10.0) | [`io.ioka.munarium:munarium-matrix-client`](java/) (Java 21) |
| Transport | REST | REST | REST |
| Runtime dependencies | `httpx` | none beyond the shared framework | Jackson databind |

None of them has a gRPC transport. Matrix's gRPC plane serves
`MatrixQuery/Execute` alone, a service-to-service call the Server makes while
answering a turn; see the [release notes](CHANGELOG.md#accepted-limitations).

## Installation and publication

| Language | Published package | Latest verified version | Installation guide |
|---|---|---|---|
| Python | [munarium-matrix on PyPI](https://pypi.org/project/munarium-matrix/) | 1.1.1 | [Python](python/README.md#install) |
| .NET | [Ioka.Munarium.Matrix.Client on NuGet](https://www.nuget.org/packages/Ioka.Munarium.Matrix.Client) | 1.1.1 | [.NET](dotnet/README.md#install) |
| Java | [io.ioka.munarium:munarium-matrix-client on Maven Central](https://central.sonatype.com/artifact/io.ioka.munarium/munarium-matrix-client) | 1.0.0 | [Java](java/README.md#install) |

Registry versions were verified on **2026-09-15**, when they were published
from `iokaio/munarium`. The source manifests here are **1.2.0 (unreleased)**,
the first release prepared in this repository, with no API change. Installing
from a registry is the normal path; each language README also shows how to
build from a checkout.

Official packages are published from
[iokaio/munarium-clients-publish](https://github.com/iokaio/munarium-clients-publish),
which publishes every Munarium client family and holds the registry
credentials; this repository holds none. [`release.json`](release.json) tells
it how these clients are gated, built and tagged. A release is cut by bumping
the manifests and [`compatibility.json`](compatibility.json) (which
`check_compatibility.py` keeps in step), merging, tagging the merged commit
`matrix-clients-v<version>`, and dispatching that repository's workflow. Its
preflight refuses a tag that is not on `main`, did not arrive through a green
pull request, or does not match the version in the tree. It then runs the
gates above and builds and tests every package, and it skips any version a
registry already has.

## Compatibility

**[`compatibility.json`](compatibility.json) is the authoritative record.** It
names the Matrix release the clients target (`target_matrix`, which must be
the version this checkout builds) and the Matrix minors each client supports:
**1.2 and 1.0** for the 1.2.0 clients, whose wire surfaces are identical.

## Development

Two stdlib checks run first in CI and take a second locally, from the
repository root:

```console
python clients/check_compatibility.py   # compatibility.json matches every manifest
python clients/check_license.py         # manifests, license texts, headers
```

`check_license.py --artifact <package>...` then scans a built wheel, sdist,
nupkg or jar for the license files, the Apache-2.0 metadata, and any path that
reaches outside the package. Each language's gates:

| Client | Checks |
|---|---|
| `python/` | `ruff check`, `ruff format --check`, `mypy`, `pytest` |
| `dotnet/` | `dotnet build` (warnings are errors), `dotnet test` |
| `java/` | `./gradlew build` |

The offline tests read the response shapes each client claims to parse. The
live tier runs against a Matrix built from the same commit when
`MUNARIUM_MATRIX_TEST_URL` and `MUNARIUM_MATRIX_TEST_TOKEN` are set, and skips
out loud without them; [matrix-ci.yml](../.github/workflows/matrix-ci.yml)
sets them, so a skip there is a failure.
