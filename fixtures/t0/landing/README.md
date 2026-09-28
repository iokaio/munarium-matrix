# The landing-export fixture

An immutable CSV export of an `opportunities` table beside the manifest the
`landing` adapter reads — eight rows, three regions, two closed stages. It is
the **mode-A blob scenario's** input on the ephemeral estate: `test-up.ps1`
uploads this directory to the cycle's storage account under `landing/crm/`
with the operator's own identity, and `test-run.ps1` registers a `store: az`
DataSource that Matrix reads through its **managed identity** (`Storage Blob
Data Reader`, granted in `envs/test/main.tf`). Until 2026-08-30 the account
and the role assignment existed and nothing could read them.

`manifest.json` carries the file's sha256 and row count. The bytes are LF and
generated (`scripts` in the session that added it); edit the CSV and the
adapter refuses it as changed under its manifest, which is the point.
