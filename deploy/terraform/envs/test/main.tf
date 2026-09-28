# The EPHEMERAL Matrix test estate.
#
# Unlike the demo and the server's dev estate, nothing here is always on. A
# cycle creates this, seeds it, runs the live scenarios, and DESTROYS it — and
# a cycle that leaves resources behind is a failed cycle even when every
# scenario passed (§18.1). The reason is specific: a *stopped* Flexible Server
# still bills storage and auto-restarts after seven days, so "stop it" is not
# a cost floor. Destroy is.
#
#   terraform init -backend-config=<your backend.hcl> \
#                  -backend-config=key=envs/matrix-test.tfstate
#   terraform apply -var run_id=<id> -var matrix_image_tag=local-<sha>
#
# Everything is run-scoped by `run_id` so two cycles cannot collide, and the
# resource group is a DATA source: it is created once by bootstrap (an empty
# group costs nothing) so the CI identity can hold Contributor on it before
# any run exists.

terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
    random  = { source = "hashicorp/random", version = "~> 3.6" }
  }
  backend "azurerm" {}
}

provider "azurerm" {
  features {
    resource_group {
      # A cycle must never leave a half-destroyed group behind.
      prevent_deletion_if_contains_resources = false
    }
  }
  subscription_id     = var.subscription_id
  storage_use_azuread = true
}

variable "run_id" {
  description = "Short id making every resource name unique to this cycle."
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9]{4,12}$", var.run_id))
    error_message = "run_id must be 4-12 lowercase alphanumerics."
  }
}

variable "location" {
  type    = string
  default = "centralus"
}

variable "matrix_image_tag" {
  description = "Matrix image tag in the shared ACR; a branch build is local-<sha>."
  type        = string
  default     = "0.1.0"
}

variable "lockstep_version" {
  description = <<-EOT
    The server SEMVER Matrix expects, independent of which IMAGE runs it.
    Passed as MUNARIUM_MATRIX_TARGET_SERVER_VERSION. Kept separate from
    server_image_tag so a branch image (`local-<sha>`, no parseable version)
    does not turn the lockstep check into `unknown`.
  EOT
  type        = string
  default     = "0.5.0"
}

variable "server_image_tag" {
  description = "munarium-server image tag. TARGET_SERVER_VERSION, or a branch image so an S-package is tested BEFORE it merges."
  type        = string
  default     = "0.3.0"
}

variable "roles" {
  description = "Split Matrix into one container app per role (the isolation scenario). Off by default: one app is cheaper and enough for most cycles."
  type        = bool
  default     = false
}

locals {
  rg        = var.resource_group_name
  shared_rg = var.shared_resource_group_name
  acr       = var.registry_name
  tenant    = "mxtest"

  # Run-scoped names. Postgres names are globally unique, so the run id is not
  # optional decoration.
  pg_name    = "psql-mxtest-${var.run_id}"
  env_name   = "cae-mxtest-${var.run_id}"
  matrix_app = "ca-mxtest-matrix-${var.run_id}"
  server_app = "ca-mxtest-server-${var.run_id}"
  storage    = "stmxtest${var.run_id}"
}

data "azurerm_resource_group" "test" {
  name = local.rg
}

data "azurerm_container_registry" "acr" {
  name                = local.acr
  resource_group_name = local.shared_rg
}

data "azurerm_log_analytics_workspace" "logs" {
  name                = "log-munarium-shared"
  resource_group_name = local.shared_rg
}

# --- identity ----------------------------------------------------------------

resource "azurerm_user_assigned_identity" "mxtest" {
  name                = "id-mxtest-${var.run_id}"
  location            = var.location
  resource_group_name = data.azurerm_resource_group.test.name
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = data.azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.mxtest.principal_id
}

# --- landing-export storage --------------------------------------------------
#
# The mode-A fixture lands here. Managed identity only: Container Apps have no
# IMDS, so the object-store client must be built `from_env()` — the server's
# live-found gotcha, kept as a live test rather than a comment.

resource "azurerm_storage_account" "landing" {
  name                            = local.storage
  resource_group_name             = data.azurerm_resource_group.test.name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  account_kind                    = "StorageV2"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = false
  # The seeding script writes with the operator's own AAD identity, so no
  # account key needs to exist at all.
  shared_access_key_enabled = false
}

resource "azurerm_storage_container" "landing" {
  name                  = "landing"
  storage_account_id    = azurerm_storage_account.landing.id
  container_access_type = "private"
}

resource "azurerm_role_assignment" "blob_reader" {
  scope                = azurerm_storage_account.landing.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.mxtest.principal_id
}

# The OPERATOR writes the landing fixture (test-up.ps1, `az storage blob
# upload-batch --auth-mode login`). Shared keys are off on the account, and an
# Owner on the subscription holds no data-plane right, so the identity that
# runs the cycle is granted the writer role explicitly — scoped to this one
# account, which is destroyed with the cycle.
data "azurerm_client_config" "operator" {}

resource "azurerm_role_assignment" "blob_writer_operator" {
  scope                = azurerm_storage_account.landing.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.operator.object_id
}

# --- PostgreSQL --------------------------------------------------------------
#
# The SMALLEST burstable SKU with the smallest disk and NO geo-redundant
# backup. This estate lives for one cycle: paying for durability it will never
# need is the difference between cents and dollars per run.

resource "random_password" "pg" {
  length  = 32
  special = false
}

resource "azurerm_postgresql_flexible_server" "pg" {
  name                          = local.pg_name
  resource_group_name           = data.azurerm_resource_group.test.name
  location                      = var.location
  version                       = "16"
  sku_name                      = "B_Standard_B1ms"
  storage_mb                    = 32768
  backup_retention_days         = 7
  geo_redundant_backup_enabled  = false
  public_network_access_enabled = true
  administrator_login           = "mxtestadmin"
  administrator_password        = random_password.pg.result
  zone                          = "1"

  lifecycle {
    # The zone Azure picks is not stable across plans and is not something a
    # one-hour estate should be re-created over.
    ignore_changes = [zone, high_availability]
  }
}

# Container Apps have no stable egress IP on the consumption profile, so the
# estate is reachable from Azure services and from the operator running the
# cycle. It holds only synthetic fixture data and lives for an hour.
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure" {
  name             = "allow-azure"
  server_id        = azurerm_postgresql_flexible_server.pg.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

variable "operator_ip" {
  description = "The address running the cycle, so seeding and assertions can reach Postgres directly."
  type        = string
  default     = ""
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "operator" {
  count            = var.operator_ip == "" ? 0 : 1
  name             = "operator"
  server_id        = azurerm_postgresql_flexible_server.pg.id
  start_ip_address = var.operator_ip
  end_ip_address   = var.operator_ip
}

# Three databases: the server's ledger, Matrix's own schema, and the fixture
# `crm` that stands in for a customer system of record.
resource "azurerm_postgresql_flexible_server_database" "munarium" {
  name      = "munarium"
  server_id = azurerm_postgresql_flexible_server.pg.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_postgresql_flexible_server_database" "matrix" {
  name      = "matrix"
  server_id = azurerm_postgresql_flexible_server.pg.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_postgresql_flexible_server_database" "crm" {
  name      = "crm"
  server_id = azurerm_postgresql_flexible_server.pg.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# pgvector, which the server's retrieval plane needs.
resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.pg.id
  value     = "VECTOR,UUID-OSSP"
}

# --- Container Apps ----------------------------------------------------------

resource "azurerm_container_app_environment" "env" {
  name                       = local.env_name
  location                   = var.location
  resource_group_name        = data.azurerm_resource_group.test.name
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.logs.id
}

locals {
  server_tokens = "mxtest-rw:${local.tenant}:rw,mxtest-ro:${local.tenant}:ro,mxtest-mgmt:${local.tenant}:mgmt"
  matrix_tokens = "mxtest-rw:${local.tenant}:rw,mxtest-mgmt:${local.tenant}:mgmt"

  pg_host  = azurerm_postgresql_flexible_server.pg.fqdn
  pg_admin = "mxtestadmin"
  pg_pass  = random_password.pg.result
}

resource "azurerm_container_app" "server" {
  name                         = local.server_app
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = data.azurerm_resource_group.test.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.mxtest.id]
  }

  registry {
    server   = data.azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.mxtest.id
  }

  ingress {
    external_enabled = true
    target_port      = 8080
    transport        = "auto"
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1
    container {
      name   = "munarium-server"
      image  = "${data.azurerm_container_registry.acr.login_server}/munarium-server:${var.server_image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "MUNARIUM_STORE"
        value = "postgres"
      }
      env {
        name  = "MUNARIUM_DATABASE_URL"
        value = "postgres://${local.pg_admin}:${local.pg_pass}@${local.pg_host}:5432/munarium?sslmode=require"
      }
      env {
        name  = "MUNARIUM_AUTH_MODE"
        value = "static"
      }
      env {
        name  = "MUNARIUM_STATIC_TOKENS"
        value = local.server_tokens
      }
      env {
        name  = "MUNARIUM_SOURCE_STORE"
        value = "pg"
      }
      env {
        name  = "MUNARIUM_TOKEN_SECRET"
        value = random_password.pg.result
      }
      env {
        name  = "MUNARIUM_LOG"
        value = "info"
      }
      # The evidence retention janitor, ON here and only here (the product
      # default is 0 = off: a janitor nobody configured deleting regulated
      # data on a schedule nobody chose is worse than one that never runs).
      # Phase 2's seventh live scenario — an artifact with retentionDays 0 is
      # purged and resolves `evidence-expired`, a held one survives — needs a
      # sweep inside the cycle. 60 is the honest value: the server clamps the
      # interval to a 60-second floor and jitters the first sweep by up to
      # another 60 s (cycle lnhm42r0 set 15 here and measured 60–120).
      env {
        name  = "MUNARIUM_EVIDENCE_PURGE_INTERVAL_SECS"
        value = "60"
      }
      # The structured-evidence plane, so a runbook with data views can run
      # its verifyDataViews step and a turn can execute through a research
      # profile on THIS estate (the §18.3 harness; until cycle qvi99cuf the
      # test server had no Matrix and the step refused). Computed from the
      # environment's default domain rather than from the Matrix app's
      # resource, or terraform sees a cycle: Matrix's env names the server's
      # FQDN. Container App FQDNs are `<app>.<default_domain>` by construction.
      env {
        name  = "MUNARIUM_MATRIX_BASE_URL"
        value = "https://${local.matrix_app}.${azurerm_container_app_environment.env.default_domain}"
      }
      env {
        name  = "MUNARIUM_MATRIX_ADMIN_URL"
        value = "https://${local.matrix_app}.${azurerm_container_app_environment.env.default_domain}/admin"
      }
      env {
        name  = "MUNARIUM_MATRIX_TOKEN"
        value = "mxtest-rw"
      }
    }
  }
}

# The Matrix container's environment, ONCE. Two apps run this image — the
# REST/ops app and the gRPC sibling below — and an env list copied into each
# is the kind of thing that drifts by one variable and costs a cycle to find.
# The comments that used to sit beside each entry are in the git history of
# this file; the load-bearing ones are repeated here.
locals {
  matrix_env = [
    { name = "MUNARIUM_MATRIX_ROLE", value = "all" },
    { name = "MUNARIUM_MATRIX_DATABASE_URL", value = "postgres://${local.pg_admin}:${local.pg_pass}@${local.pg_host}:5432/matrix?sslmode=require" },
    { name = "MUNARIUM_MATRIX_AUTH_MODE", value = "static" },
    { name = "MUNARIUM_MATRIX_STATIC_TOKENS", value = local.matrix_tokens },
    { name = "MUNARIUM_MATRIX_SERVER_URL", value = "https://${azurerm_container_app.server.ingress[0].fqdn}" },
    { name = "MUNARIUM_MATRIX_SERVER_TOKEN_REF", value = "env:MUNARIUM_MATRIX_SERVER_TOKEN" },
    { name = "MUNARIUM_MATRIX_SERVER_TOKEN", value = "mxtest-rw" },
    { name = "MUNARIUM_MATRIX_SECRET_MXTEST_CRM", value = "postgres://matrix_reader:matrix-reader-dev@${local.pg_host}:5432/crm?sslmode=require" },
    { name = "MUNARIUM_MATRIX_TARGET_SERVER_VERSION", value = var.lockstep_version },
    { name = "AZURE_CLIENT_ID", value = azurerm_user_assigned_identity.mxtest.client_id },
    { name = "MUNARIUM_MATRIX_LOG", value = "info" },
  ]
}

resource "azurerm_container_app" "matrix" {
  count                        = var.roles ? 0 : 1
  name                         = local.matrix_app
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = data.azurerm_resource_group.test.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.mxtest.id]
  }

  registry {
    server   = data.azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.mxtest.id
  }

  ingress {
    external_enabled = true
    target_port      = 8180
    transport        = "auto"
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1
    container {
      name   = "munarium-matrix"
      image  = "${data.azurerm_container_registry.acr.login_server}/munarium-matrix:${var.matrix_image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      dynamic "env" {
        for_each = local.matrix_env
        content {
          name  = env.value.name
          value = env.value.value
        }
      }

      # The two credentials this estate NEVER HAD until 2026-08-29.
      #
      # Without a server token every Matrix -> server call went out with an
      # empty bearer, and without a resolvable `mxtest-crm` the `crm` source
      # refused `credential_unresolved` before touching a row. So no mode A, B
      # or C operation had ever executed ON THE ESTATE against the real
      # fixture: the "live" tier was registry round-trips, psql from the
      # operator's laptop, and the conformance crate against the estate's own
      # store. Every cycle reported green. Found while auditing Phase 4's live
      # exit gate — "a mapping run over crm" — and discovering nothing could
      # have run it.
      #
      # Plain env vars, not Container App secrets, because every other
      # credential in this ESTATE is already a plaintext static token in env
      # (see MUNARIUM_STATIC_TOKENS above); a test estate that lives for
      # twenty minutes gets the same posture throughout rather than a secret
      # store for one value.
      # The object-store client must be built from_env(): Container Apps have
      # no IMDS, and this is the setting that makes the managed identity
      # reachable. Discovered live on the server estate; kept as a real test.
    }
  }
}


# --- the gRPC sibling app (Phase 6, WP-6.10) ---------------------------------
#
# The same constraint the server met on 2026-08-09: one Container Apps HTTP
# ingress targets ONE port, and an additional external TCP port needs a
# custom-VNET environment. So the gRPC plane gets its own app on the same
# image, with an `http2` ingress straight to the tonic listener on 50151 and
# Azure-managed TLS on its own FQDN. Same env, same identity, same store.
# Role `all`, so it also serves REST on 8180 — which the ingress does not
# expose, because this app's one port is 50151.
resource "azurerm_container_app" "matrix_grpc" {
  count                        = var.roles ? 0 : 1
  name                         = "${local.matrix_app}-grpc"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = data.azurerm_resource_group.test.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.mxtest.id]
  }

  registry {
    server   = data.azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.mxtest.id
  }

  ingress {
    external_enabled = true
    target_port      = 50151
    transport        = "http2" # gRPC needs h2 end-to-end; tonic serves h2c behind the TLS edge
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1
    container {
      name   = "munarium-matrix"
      image  = "${data.azurerm_container_registry.acr.login_server}/munarium-matrix:${var.matrix_image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      dynamic "env" {
        for_each = local.matrix_env
        content {
          name  = env.value.name
          value = env.value.value
        }
      }
    }
  }
}

# --- outputs: everything a cycle needs, written to .mxtest-current.json -------

output "run_id" { value = var.run_id }
output "resource_group" { value = data.azurerm_resource_group.test.name }
output "server_fqdn" { value = azurerm_container_app.server.ingress[0].fqdn }
output "matrix_fqdn" {
  value = var.roles ? "" : azurerm_container_app.matrix[0].ingress[0].fqdn
}
output "matrix_grpc_fqdn" {
  value = var.roles ? "" : azurerm_container_app.matrix_grpc[0].ingress[0].fqdn
}
output "pg_fqdn" { value = azurerm_postgresql_flexible_server.pg.fqdn }
output "pg_admin" { value = local.pg_admin }
output "pg_password" {
  value     = random_password.pg.result
  sensitive = true
}
output "storage_account" { value = azurerm_storage_account.landing.name }
output "tenant" { value = local.tenant }
output "server_mgmt_token" {
  value     = "mxtest-mgmt"
  sensitive = true
}
output "matrix_rw_token" {
  value     = "mxtest-rw"
  sensitive = true
}
