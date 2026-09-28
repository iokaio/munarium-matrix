# Security

Do not file a vulnerability as an issue or a pull request.

Report a suspected vulnerability in Munarium Matrix, in the contract under `contract/`, or in
anything you reached through them, privately, by either route:

- GitHub's private vulnerability reporting on this repository ("Report a vulnerability" under the
  Security tab), or
- email to **info@ioka.io** with "security" in the subject.

Say what you found, where, and how to reproduce it. Do not include live credentials, customer data,
or a proof of concept run against a system you do not operate. You will get an acknowledgement
within two business days, and a fix — or a recorded decision — on the affected path before any
related release. Credit is given if you ask for it.

## Supported versions

Security fixes go to the current minor release and to the previous one for six months after its
successor ships.

## What Matrix defends, and what it assumes

Matrix reads customer data sources under credentials the operator gives it, and seals evidence into
Munarium Server. Two classes of finding matter most, and a report naming one of them will be taken
seriously and quickly:

- **A read that escapes its declared scope.** A query contract executing a statement its allowlist
  should have refused, a row filter or column mask not surviving to the source, an adapter reading
  a column the source never declared, or a watermark advancing past rows it did not read.
- **Evidence that does not describe what happened.** A sealed result whose logical hash does not
  bind the rows it claims, a truncated result presented as complete, a replay that returns
  something other than the state it pinned, or a promotion writing outside its declared authority
  scope.

Matrix assumes the operator controls the credentials in `credentialRef` and the network path to the
source, and it fails closed by design: an unsupported combination is a refusal rather than a
best-effort answer. A refusal where you expected an answer is usually correct behavior, and the
refusal registry says which class it belongs to.

## Munarium Matrix Enterprise

The adapters for Databricks, BigQuery, Snowflake, Cube and dbt are part of Munarium Matrix
Enterprise, a separate proprietary product. A vulnerability in one of them goes through the same
private channel; subscribers are notified under their agreement.

## Secrets

If you have committed a token or key, treat it as compromised: rotate it first, then report it.
