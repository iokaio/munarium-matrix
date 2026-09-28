# The ephemeral Matrix test estate

`envs/test/` stands up everything Matrix's live tier needs — a PostgreSQL Flexible Server
with the fixture, a Container App running Matrix (optionally one per role), a Container App
running the Server it seals evidence into, and, with `-var databricks=true`, a Databricks
workspace with a serverless SQL warehouse — runs the scenarios against it over real ingress,
and **destroys all of it**. Nothing here is always on. A *stopped* Flexible Server still
bills storage and restarts itself after seven days, so "stop it" is not a cost floor; destroy
is. A cycle that leaves resources behind is a failed cycle even when every scenario passed.

Everything is scoped by `run_id`, so two cycles cannot collide, and the resource group is a
**data source**: created once, out of band, so the identity that runs a cycle can hold
Contributor on it before any run exists (an empty group costs nothing).

## The procedure

The scripts that automate this end to end (`test-up` → `test-run` → `test-down`, with
teardown in a `finally`) are Ioka's own operations and are not part of this repository;
this is what they do, so it can be done by hand or scripted for another estate.

1. **Create the resource group once**, and grant the identity that will run cycles
   Contributor on it and `AcrPull` on the registry that holds the two images. Give the group
   a budget alert: the estate is cheap (cents per cycle with PostgreSQL), but a Databricks
   workspace's managed group holds a NAT gateway that bills hourly whether or not a query
   runs — never park one.
2. **Publish the images** the cycle will run: the Matrix image for the version under test
   and the Server image Matrix's `MUNARIUM_MATRIX_TARGET_SERVER_VERSION` expects
   (`server_image_tag` and `lockstep_version` are separate variables so a branch image with
   no parseable version does not turn the lockstep check into `unknown`).
3. **Apply**, with a fresh `run_id` (4–12 lowercase alphanumerics) and your own state
   backend:

   ```bash
   cd deploy/terraform/envs/test
   terraform init -backend-config=<your backend.hcl> -backend-config=key=envs/matrix-test-<run_id>.tfstate
   terraform apply -var run_id=<run_id> -var matrix_image_tag=<tag> -var server_image_tag=<tag> \
                   -var lockstep_version=<server semver> [-var roles=true] [-var databricks=true]
   ```

   The outputs name the Matrix and Server ingress FQDNs, the PostgreSQL host, and (with
   Databricks) the workspace URL.
4. **Wait for health** on both apps' `/healthz`, then **seed**: load the T0 fixture
   (`fixtures/t0/sql/`, in order) into the PostgreSQL server as its owner, and create the
   least-privileged reader the fixture's assets name; mint the Matrix tokens and the Server
   token Matrix seals with, and set them where the apps read them (`MUNARIUM_MATRIX_SECRET_*`
   and `MUNARIUM_MATRIX_SERVER_TOKEN_REF` — see `docs/user-guide.md`). With Databricks: wait
   for the workspace API (an ARM `Succeeded` is minutes short of an API that answers), create
   a 2X-Small serverless warehouse with `auto_stop_mins: 5`, and load the Delta fixture through
   the Statement Execution API — the same API the adapter uses, so a fixture loaded another
   way cannot differ in the ways the tier exists to catch.
5. **Run** the conformance tiers against the FQDNs (`conformance/SCENARIOS.md` lists every
   scenario and its tier; `MUNARIUM_MATRIX_TEST_*` variables select them), and keep the
   results file the harness writes: a number quoted in a document must trace to one.
6. **Destroy**, and **verify** the group is empty — and, for a Databricks cycle, that the
   workspace's *managed* resource group is gone too. It sits outside the estate's group,
   where a sweep of the group cannot see it, and an empty estate beside a surviving managed
   group is a failed teardown that looks like a clean one.

## What the variables mean

| Variable | Meaning |
|---|---|
| `run_id` | The cycle's id; every resource name carries it |
| `location` | Region (default `centralus`) |
| `matrix_image_tag`, `server_image_tag` | The two images, by tag, in the registry the apps pull from |
| `lockstep_version` | The Server semver Matrix expects, independent of which image runs it |
| `roles` | One Container App per Matrix role (the isolation scenario) instead of one app; off by default because one app is cheaper and enough for every other scenario |
| `databricks` | Add the workspace and the Databricks tier (`databricks.tf`); the one flag that changes the bill from cents to dollars |

The subscription, resource-group and registry names in `envs/test/main.tf` are the values
this estate was proven on and are the ones to change first for another estate.
