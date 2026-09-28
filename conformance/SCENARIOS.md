# Conformance scenarios

Generated from `SCENARIOS` in `conformance/src/lib.rs` — edit the code, not this file.
Every guarantee in the plan maps to at least one row here; a guarantee with no scenario
is a claim with no test.

| Scenario | Guarantee | Phase | Tier |
|---|---|---|---|
| `canon.identity_is_stable_under_permutation` | G1 | 0 | offline |
| `canon.truncated_never_equals_complete` | G4 | 0 | offline |
| `canon.unidentifiable_result_refuses_sealing` | G1 | 0 | offline |
| `evidence.seal_is_idempotent_by_logical_hash` | G1 | 2 | offline |
| `evidence.under_cleared_session_cannot_resolve` | G6 | 2 | offline |
| `evidence.replays_after_the_source_changes` | G1 | 2 | offline |
| `sync.replayed_checkpoint_creates_no_duplicates` | G4 | 2 | offline |
| `sync.coverage_reports_excluded_rows` | G4 | 2 | offline |
| `sync.drift_refuses_then_compat_accepts` | G7 | 2 | offline |
| `postgres.watermark_advances_and_an_unchanged_source_reads_nothing` | G4 | 2 | postgres |
| `postgres.watermark_reads_the_columns_the_source_declared` | G4 | 2 | postgres |
| `policy.denied_column_never_appears_anywhere` | G6 | 2 | offline |
| `queue.a_stale_running_job_is_reclaimed_after_its_lease` | - | 6 | postgres |
| `registry.apply_is_idempotent_and_refuses_mutation` | - | 1 | postgres |
| `registry.concurrent_appliers_of_one_new_version_insert_once_and_never_fail` | - | 6 | postgres |
| `registry.matrix_owner_cannot_write_public` | - | 1 | postgres |
| `budget.concurrent_reservations_cannot_exceed_the_ceiling` | G7 | 1 | postgres |
| `queue.two_workers_claim_disjoint_jobs` | - | 1 | postgres |
| `contract.committed_contract_compiles` | G7 | 3 | offline |
| `contract.undeclared_source_column_refuses` | G7 | 3 | offline |
| `contract.denied_column_beats_a_reads_declaration` | G6 | 3 | offline |
| `freshness.stale_result_refuses_under_a_bound` | G3 | 3 | offline |
| `freshness.manifest_states_a_snapshot_marker_per_source` | G3 | 2 | offline |
| `verification.derivation_recomputes_from_the_sealed_cells` | G5 | 3 | offline |
| `verification.derivation_over_a_truncated_result_is_not_a_total` | G5 | 3 | offline |
| `budget.an_execution_spends_a_unit_and_a_refusal_refunds_it` | G7 | 3 | postgres |
| `roles.a_claimed_job_always_reaches_a_terminal_state` | - | 2 | postgres |
| `databricks.probe_reaches_a_real_warehouse` | - | 3 | databricks |
| `databricks.decimal_scale_survives_the_wire` | G1 | 3 | databricks |
| `databricks.source_time_travel_returns_the_prior_state` | G2 | 3 | databricks |
| `databricks.change_feed_returns_inserts_updates_and_deletes_with_their_versions` | G3 | 4 | databricks |
| `databricks.metric_view_is_fingerprinted_and_answers_measure_sql_by_grain` | G1 | 6 | databricks |
| `databricks.execute_reports_no_snapshot_marker` | G7 | 3 | databricks |
| `databricks.materializing_by_watermark_is_refused_naming_the_feed` | G7 | 3 | databricks |
| `databricks.introspect_reports_the_fixture_schema` | G3 | 3 | databricks |
| `databricks.statement_tags_reach_the_query_history` | G5 | 6 | databricks |
| `databricks.a_named_parameter_binds_rather_than_interpolates` | G6 | 3 | databricks |
| `databricks.a_row_filter_and_column_mask_survive_the_statement_api` | G6 | 3 | databricks |
| `databricks.policy_protected_time_travel_is_refused` | G6 | 3 | databricks |
| `databricks.the_engine_truncates_at_the_row_limit_and_says_so` | G4 | 3 | databricks |
| `databricks.a_statement_past_its_deadline_is_cancelled_not_awaited` | G4 | 3 | databricks |
| `databricks.change_feed_survives_an_add_column_without_misalignment` | G3 | 4 | databricks |
| `databricks.metric_view_groups_in_the_declared_zone_and_sum_skips_nulls` | G1 | 6 | databricks |
| `databricks.the_principal_cannot_reach_beyond_its_grants` | G6 | 3 | databricks |
| `planner.assist_admits_only_a_permitted_trusted_asset` | G6 | 6 | offline |
| `planner.evaluation_records_and_admits_nothing` | G6 | 6 | offline |
| `planner.an_unpinned_plan_is_a_label_not_a_failure` | G2 | 6 | offline |
| `genie.a_real_space_answers_and_the_unpinned_label_is_true_of_the_wire` | G2 | 6 | genie |
| `genie.under_an_unpermitting_spec_admits_nothing` | G6 | 6 | genie |
| `dbt.probe_reaches_a_real_deployment` | - | 6 | dbt |
| `dbt.answers_a_bounded_ask_keyed_by_its_dimension` | G1 | 6 | dbt |
| `dbt.definition_is_fingerprint_stable_and_an_unknown_metric_is_not_covered` | G7 | 6 | dbt |
| `dbt.statements_are_refused_by_name` | G6 | 6 | dbt |
| `grpc.reflection_lists_the_query_service` | - | 6 | grpc |
| `grpc.an_unauthenticated_call_is_a_status` | G6 | 6 | grpc |
| `grpc.a_refusal_is_a_message_not_a_status` | G7 | 6 | grpc |
| `grpc.execute_streams_the_block_rest_returns` | G1 | 6 | grpc |
| `grpc.a_past_deadline_is_refused_on_the_stream` | G7 | 6 | grpc |
| `grpc.tier_mcp_lists_declared_tools_and_a_call_seals_evidence` | G1 | 6 | grpc |
| `grpc.tier_native_data_view_verifies_and_executes_over_rest` | G1 | 6 | grpc |
| `grpc.tier_an_empty_result_is_a_complete_answer` | G4 | 3 | grpc |
| `mysql.probe_reaches_a_real_server` | - | 6 | mysql |
| `mysql.an_exact_decimal_survives_the_driver` | G1 | 6 | mysql |
| `mysql.a_positional_parameter_binds_rather_than_interpolates` | G6 | 6 | mysql |
| `mysql.an_unmodelled_type_is_refused_and_names_the_column` | G7 | 6 | mysql |
| `mysql.a_snapshot_read_reports_no_marker_when_the_server_has_none` | G2 | 6 | mysql |
| `mysql.introspect_reports_row_security_as_absent_rather_than_omitting_it` | G6 | 6 | mysql |
| `mysql.watermark_advances_by_the_declared_columns` | G4 | 6 | mysql |
| `cdc.a_missing_slot_is_refused_with_the_statement_that_creates_it` | G7 | 6 | postgres |
| `cdc.a_slot_that_decodes_with_test_decoding_is_refused` | G6 | 6 | postgres |
| `cdc.a_publication_without_a_row_filter_on_a_secured_table_is_refused` | G6 | 6 | postgres |
| `cdc.a_publication_that_does_not_match_the_projection_is_refused` | G6 | 6 | postgres |
| `cdc.inserts_updates_and_deletes_arrive_distinguishable_with_their_lsn` | G4 | 6 | postgres |
| `cdc.a_checkpoint_behind_the_slot_is_reported_as_a_gap` | G4 | 6 | postgres |
| `cdc.the_slots_retained_wal_is_observable` | G3 | 6 | postgres |
| `sqlserver.probe_reaches_a_real_server` | - | 6 | sqlserver |
| `sqlserver.an_exact_decimal_survives_the_driver` | G1 | 6 | sqlserver |
| `sqlserver.a_positional_parameter_binds_rather_than_interpolates` | G6 | 6 | sqlserver |
| `sqlserver.an_unmodelled_type_is_refused_and_names_the_column` | G7 | 6 | sqlserver |
| `sqlserver.a_snapshot_read_reports_a_marker_only_from_a_consistent_view` | G2 | 6 | sqlserver |
| `sqlserver.introspect_reports_row_security_as_present` | G6 | 6 | sqlserver |
| `sqlserver.watermark_advances_by_the_declared_columns` | G4 | 6 | sqlserver |
| `snowflake.probe_reaches_a_real_account` | - | 6 | snowflake |
| `snowflake.an_exact_decimal_survives_the_wire` | G1 | 6 | snowflake |
| `snowflake.a_positional_parameter_binds_rather_than_interpolates` | G6 | 6 | snowflake |
| `snowflake.an_unmodelled_type_is_refused_and_names_the_column` | G7 | 6 | snowflake |
| `snowflake.execute_reports_a_statement_id_and_no_snapshot_marker` | G2 | 6 | snowflake |
| `snowflake.introspect_reports_row_security_rather_than_omitting_it` | G6 | 6 | snowflake |
| `bigquery.probe_reaches_a_real_project` | - | 6 | bigquery |
| `bigquery.an_exact_decimal_survives_a_minimal_rendering` | G1 | 6 | bigquery |
| `bigquery.a_named_parameter_binds_rather_than_interpolates` | G6 | 6 | bigquery |
| `bigquery.an_unmodelled_type_is_refused_and_names_the_column` | G7 | 6 | bigquery |
| `bigquery.execute_reports_a_job_id_and_no_snapshot_marker` | G2 | 6 | bigquery |
| `bigquery.a_query_over_the_byte_ceiling_is_refused_before_it_scans` | G7 | 6 | bigquery |
| `bigquery.introspect_reports_row_security_rather_than_omitting_it` | G6 | 6 | bigquery |
| `cube.probe_reaches_a_real_deployment` | - | 6 | cube |
| `cube.answers_a_bounded_ask_keyed_by_its_dimension` | G1 | 6 | cube |
| `cube.narrows_to_one_group_under_a_filter` | G1 | 6 | cube |
| `cube.definition_is_the_deployments_schema_and_is_stable` | G7 | 6 | cube |
| `semantic.an_adapter_without_the_capability_is_metric_not_covered` | G7 | 6 | offline |
| `semantic.a_view_with_no_verification_on_record_is_not_covered` | G7 | 6 | offline |
| `semantic.a_changed_definition_is_refused_before_the_statement` | G7 | 6 | offline |
| `reconcile.a_pass_over_its_declared_ceiling_is_refused_before_it_writes` | G7 | 6 | offline |
| `reconcile.shadow_leaves_canon_byte_identical` | G7 | 4 | offline |
| `reconcile.ambiguous_identity_never_merges` | G7 | 4 | offline |
| `reconcile.replayed_batch_creates_no_duplicates` | G4 | 4 | offline |
| `reconcile.backdated_change_requires_review` | G7 | 4 | offline |
| `reconcile.discrepancy_carries_both_evidence_sides` | G1 | 4 | offline |
| `reconcile.absent_declared_holder_is_missing_in_source` | G4 | 4 | offline |
| `reconcile.precision_and_recall_on_the_t0_answer_key` | G7 | 4 | offline |
| `authority.unpromoted_mapping_proposes_nothing` | G7 | 5 | offline |
| `authority.promoted_mapping_proposes_only_in_scope` | G6 | 5 | offline |
| `authority.document_outranks_source_by_default` | G7 | 5 | offline |
| `authority.replayed_run_proposes_nothing_twice` | G4 | 5 | offline |
| `authority.backdated_never_proposes` | G7 | 5 | offline |
| `authority.disputed_proposal_is_counted_not_dropped` | G7 | 5 | offline |
| `authority.rollback_supersedes_with_origin` | G1 | 5 | offline |
| `authority.rollback_of_a_chain_restores_the_original` | G1 | 5 | offline |
| `authority.a_rollback_claim_holds_under_document_precedence` | G7 | 5 | offline |
| `admin.every_read_page_renders_without_script` | - | 7 | http |
| `admin.is_mgmt_only_over_the_wire` | G6 | 7 | http |
| `admin.a_write_without_a_csrf_token_is_refused` | G6 | 7 | http |
| `admin.an_action_needs_the_rw_credential_not_the_admins_own` | G6 | 7 | http |
| `admin.an_exported_draft_applies_identically_to_applying_in_place` | - | 7 | http |
| `admin.a_console_write_is_journaled_as_admin_ui` | G3 | 7 | http |
| `admin.the_drift_flag_sets_on_apply_in_place_and_clears_when_the_bundle_lands` | - | 7 | http |

## Guarantee coverage

- **G1**: 20 scenario(s)
- **G2**: 7 scenario(s)
- **G3**: 7 scenario(s)
- **G4**: 15 scenario(s)
- **G5**: 3 scenario(s)
- **G6**: 27 scenario(s)
- **G7**: 30 scenario(s)

## Tiers, and whether they have ever run

| Tier | Scenarios | Run against a real thing? |
|---|---|---|
| `bigquery` | 7 | yes — first live run 2026-08-31 against a real project, 7/7; two first-contact defects found and pinned (docs/adapters/build-matrix.md) |
| `cube` | 4 | yes — compose, $0, behind a profile and a variable |
| `databricks` | 17 | yes — the ephemeral estate, which costs money per cycle |
| `dbt` | 4 | **NEVER** — no dbt Cloud deployment exists, and no OSS container can stand one up (docs/adapters/build-matrix.md) |
| `genie` | 2 | **NEVER** — rides `-Databricks` plus a Genie space with a trusted asset, which no cycle has created (docs/api/planner.md) |
| `grpc` | 8 | yes — compose, $0 |
| `http` | 7 | yes — compose, $0 |
| `mysql` | 7 | yes — compose, $0, behind a profile and a variable |
| `offline` | 40 | yes — every push, $0 |
| `postgres` | 17 | yes — compose, $0 |
| `snowflake` | 6 | **NEVER** — no account exists (docs/adapters/build-matrix.md) |
| `sqlserver` | 7 | yes — compose, $0, behind a profile and a variable |
