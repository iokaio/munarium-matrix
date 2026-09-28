# The Databricks half of the ephemeral estate. OFF unless a cycle asks.
#
# WHY IT IS ITS OWN FILE AND ITS OWN SWITCH
#
# A Databricks workspace is the most expensive thing this estate can create,
# and the cost is not the cluster. Creating a workspace provisions a MANAGED
# resource group containing a **NAT gateway**, which bills hourly whether or
# not anything runs. A workspace was parked on 2026-08-28 on the assumption
# that an idle one is free, and deleted on 2026-08-29 when it turned out to be
# a standing charge for a workspace that had never served a query. So:
# per-cycle, never parked, and `count = 0` by default.
#
# Measured 2026-08-29: workspace create -> Succeeded in **3 m 29 s** (the plan
# estimated ~15), a 2X-Small serverless warehouse had no perceptible cold
# start, and the whole create-to-destroy session was ~7 minutes. Premium
# Serverless SQL lists at **$0.70/DBU-hour** in centralus, so the smallest
# warehouse is ~$2.80/hour RUNNING — against $0.034 for a whole Postgres
# estate cycle. That ratio is why this is opt-in and why the warehouse carries
# `auto_stop_mins`.
#
# The SKU is `premium` and not negotiable: serverless SQL warehouses and Unity
# Catalog both require it, and `standard` fails late — after the workspace
# exists and has begun billing.

variable "databricks" {
  description = <<-EOT
    Create a Databricks workspace for this cycle. OFF by default.

    This is the only variable in the estate that materially changes the bill.
    A cycle without it costs cents; a cycle with it costs dollars per hour for
    as long as the workspace exists, because the workspace's managed group
    holds a NAT gateway that bills whether or not a query runs.
  EOT
  type        = bool
  default     = false
}

resource "azurerm_databricks_workspace" "dbx" {
  count               = var.databricks ? 1 : 0
  name                = "dbx-mxtest-${var.run_id}"
  resource_group_name = data.azurerm_resource_group.test.name
  location            = var.location

  # Premium, because serverless SQL and Unity Catalog need it. `standard`
  # fails AFTER the workspace exists, which is the expensive kind of wrong.
  sku = "premium"

  # Named explicitly so teardown can assert it is gone. Azure would generate
  # one, and a generated name is one more thing a verification step has to
  # discover before it can check anything.
  managed_resource_group_name = "rg-mxtest-dbx-${var.run_id}-managed"

  tags = {
    purpose = "munarium-matrix-ephemeral-test"
    run_id  = var.run_id
    # The hourly sweep reads this. A workspace that outlives its cycle is the
    # single most expensive way to forget.
    sweep = "true"
  }
}

output "databricks_host" {
  description = "Bare hostname — what DatabricksConfig.host wants, and it refuses a scheme."
  value       = var.databricks ? azurerm_databricks_workspace.dbx[0].workspace_url : ""
}

output "databricks_workspace_id" {
  value = var.databricks ? azurerm_databricks_workspace.dbx[0].id : ""
}

output "databricks_managed_rg" {
  description = "The group teardown must verify is GONE — it is where the NAT gateway lives."
  value       = var.databricks ? "rg-mxtest-dbx-${var.run_id}-managed" : ""
}
