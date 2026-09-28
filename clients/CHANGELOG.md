# Munarium Matrix clients — release notes

The Python, .NET and Java clients for Munarium Matrix. Releases before 1.2.0
were cut from `iokaio/munarium`, where these clients lived beside the Server
clients as `clients/matrix-{python,dotnet,java}`; their notes are carried here.

## 1.2.0 — unreleased, the standalone repository

- The three clients move to `iokaio/munarium-matrix` and version with Matrix:
  one number, 1.2.0, names the service, its container image and its clients.
- No API change. The clients target Matrix 1.2.0, whose wire surface is
  unchanged from 1.0.0, and support Matrix 1.2 and 1.0
  ([compatibility.json](compatibility.json)).
- Package metadata (project, repository, SCM and changelog URLs) names this
  repository. Package ids are unchanged: `munarium-matrix` on PyPI,
  `Ioka.Munarium.Matrix.Client` on NuGet and
  `io.ioka.munarium:munarium-matrix-client` on Maven Central.
- The Python package's `__version__` reports the package version; it had read
  `1.0.0` since the first release.
- Published from `iokaio/munarium-clients-publish`, which publishes every
  Munarium client family; `clients/release.json` describes these three to it.

## 1.1.1 — first registry releases

- First public releases on 2026-09-15: Matrix clients 1.0.0 to PyPI, NuGet and
  Maven Central, cut from `iokaio/munarium`.
- All seven Munarium client packages, these three included, moved to 1.1.1
  together so one number named one release across the registries; no API
  change. Matrix compatibility remained 1.0. 1.1.1 reached PyPI and NuGet;
  Maven Central lists 1.0.0 for the Java client.

## 1.0.0

The first public source release of the Python, .NET and Java clients for
Munarium Matrix, alongside the Server clients in `iokaio/munarium`.

### Accepted limitations

- **The Matrix clients expose no gRPC transport.** Matrix's gRPC plane serves
  `MatrixQuery/Execute` alone, and that call is service-to-service: the Server
  makes it while answering a turn, carrying an authorization snapshot an
  application does not hold. Generating stubs for it would put a large
  transitive dependency on every consumer's classpath to expose a call none of
  them may make.
- **No dependency-vulnerability gate yet** for the Python, .NET and Java
  dependency graphs; the Rust workspace has `cargo deny`.
