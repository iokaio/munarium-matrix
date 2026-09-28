# SPDX-License-Identifier: Apache-2.0
<#
.SYNOPSIS
  The BigQuery conformance fixture, reproducibly: dataset, table, principal.

.DESCRIPTION
  First run 2026-08-31 against project `munarium-snowflake-dev`; committed so
  the setup is a script rather than a paragraph. Everything here is idempotent
  and the whole footprint has NO idle-billing component: BigQuery is
  serverless, the fixture is three rows inside the free storage tier, the
  service account and IAM bindings are free, and the tier's queries scan
  kilobytes against a 1 TB/month free query tier. Leaving it in place costs
  $0; deleting and recreating it is this script either way.

  The tier then runs from `matrix/`:

    $tok = gcloud auth print-access-token `
        --impersonate-service-account=matrix-tier@<project>.iam.gserviceaccount.com
    $env:MUNARIUM_MATRIX_TEST_BIGQUERY = '<project>'
    $env:MUNARIUM_MATRIX_TEST_BIGQUERY_TOKEN = $tok
    $env:MUNARIUM_MATRIX_TEST_BIGQUERY_DATASET = 'crm'
    cargo test -p munarium-matrix-conformance --lib bigquery_ -- --include-ignored

  The adapter takes the MINTED token and never exchanges a key — the
  impersonation grant (`roles/iam.serviceAccountTokenCreator` for the
  operator, below) is what keeps a long-lived credential out of every file.

.NOTES
  The fixture's amounts are the tier's oracle: `900000.50` in a NUMERIC(28,2)
  is the value whose trailing zero the wire DROPS (BigQuery renders NUMERIC
  minimally; captured in the adapter's tests/captured-query.json), which is
  the property the exact-decimal scenario exists to measure.
#>
[CmdletBinding()]
param(
    [string]$Project = 'munarium-snowflake-dev',
    [string]$Operator = 'tyler@tsjensen.com'
)

$ErrorActionPreference = 'Stop'
$sa = "matrix-tier@$Project.iam.gserviceaccount.com"

gcloud services enable bigquery.googleapis.com iamcredentials.googleapis.com --project $Project

# Least privilege at project scope: run jobs, read data, nothing else. The
# project exists for this fixture, so project scope IS the dataset's.
if (-not (gcloud iam service-accounts list --project $Project --filter="email:$sa" --format="value(email)")) {
    gcloud iam service-accounts create matrix-tier `
        --display-name 'Munarium Matrix conformance tier (least privilege)' --project $Project
}
gcloud projects add-iam-policy-binding $Project --member "serviceAccount:$sa" --role roles/bigquery.jobUser --condition=None | Out-Null
gcloud projects add-iam-policy-binding $Project --member "serviceAccount:$sa" --role roles/bigquery.dataViewer --condition=None | Out-Null
gcloud iam service-accounts add-iam-policy-binding $sa --member "user:$Operator" --role roles/iam.serviceAccountTokenCreator --project $Project | Out-Null

# The dataset and the fixture, seeded through the same API the adapter reads.
bq --project_id=$Project mk --dataset --force=true "${Project}:crm" 2>$null
@'
CREATE OR REPLACE TABLE crm.opportunities (
  id INT64,
  name STRING,
  stage STRING,
  amount NUMERIC(28,2),
  region STRING,
  updated_at TIMESTAMP
);
INSERT INTO crm.opportunities VALUES
  (1, 'Acme renewal',   'Negotiation',  900000.50, 'EMEA', TIMESTAMP '2026-06-01 10:00:00'),
  (2, 'Beta expansion', 'Proposal',    1020000.50, 'EMEA', TIMESTAMP '2026-06-15 11:30:00'),
  (3, 'Gamma pilot',    'Closed Won',   430000.25, 'AMER', TIMESTAMP '2026-06-20 09:15:00');
'@ | bq --project_id=$Project query --use_legacy_sql=false

Write-Host "fixture ready: $Project.crm.opportunities; tier principal $sa" -ForegroundColor Green
