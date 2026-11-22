# Independent AI review of the portable M1 archive revision

2026-11-22. **Recommendation: revise the remaining gate-consistency checks before relying on portable verification.** Original archive findings 2 and 5 and the portable command/runtime portions of 7–8 have concrete source repairs. Findings 3–4 are substantially repaired, with the three remaining issues below. These are source-derived metadata consistency gaps, not observed physical failures or executed failing tests. This review does not accept M1.

The subject is commit `ba6fa8009cf1c909b11c7400ccddf7d59666ab41`. **P**, **V** and **T** below mean its `tools/m1_evidence/pack_final_review_evidence.py`, `verify_final_review_evidence.py` and `tests/test_archive_metadata.py`, respectively. All three complete files and all 28 ordinary direct test methods were read. **None was imported or executed.** Comparisons use the collector/preparer at `03988252591b0d91f1cb7269f7e719c793b71e0b`, the [original review](M1_FINAL_ARCHIVE_DESIGN_REVIEW.md) at `b402753`, and the [collector review](M1_COLLECTION_REVISION_REVIEW.md) at `8790fb1`. Unfinished collector/lifecycle and runner working files were excluded.

| Subject | Bytes | SHA256 |
| --- | ---: | --- |
| P | 9,295 | `3b22c0d2f4e4ffbba653fc47f29ad2ec13cad54865ea552c887bfd0651dc1ba9` |
| V | 77,562 | `0e129ec8fbec29b29af21948fd7bf2111d485ffb5324e47327f2ee1e35de48c6` |
| T | 30,845 | `0ff7ab71c581a236f3d314750c361c3d5a857026cd2e578180adac515ca1669d` |

Scientific identity remains `2bdcea0d28340e7429e10053a641f92d51fcc696`, snapshot SHA256 `b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f`, binary SHA256 `18afcf0308338e2ea0ea7ef5e03dba46af9d7025f3ccf4a6a48ebbfe800d0725`. The selected iterative, screening-1, pressure-blended HLLD, smooth-extrema configuration and trial fraction 1 are unchanged. No numerical threshold or registered case is changed here.

## Numbered findings

1. **High — the final verdict does not have to contain the registered checks, and some omitted checks have no other full-path validation.** V:1106–1112 checks the exact seven phase names and candidate identities, then accepts any nonempty all-true `checks` object. T:306–325 deliberately uses `{'metadata_control': True}` as its positive case. That case is clearly labelled synthetic and is not fabricated physical evidence; nevertheless it tests a weaker contract than the function name suggests.

   This is reachable from the actual entrypoint: P:144 invokes `verify_evidence`, whose V:1176–1181 calls phase/raw checks, then `check_verdict`, report checks and adapter checks. Those connected checks already enforce much of the case/state/configuration/boost/reference contract. The finding is **not** that removing a verdict key bypasses every physical check. Two existing requirements remain unclosed elsewhere:

   - `mean_refinement_measured`: frozen `scripts/run_m1_campaign.py:76–90` requires four candidate rows, the two jitter values, exact n/dt coordinates, finite nonnegative measurements and the corresponding order-array lengths. V never inspects `checkpoint.summaries.wave.mean_refinement`. Its mean report path at V:772–795 checks the twelve boost pairs and their identities, not those four observations. The unchanged `reduce_mean.py:24–27,71–78` also does not require them. Collector `0398825`'s preparer:52–59 accepts the seven passed phase flags without checking the constituent keys. Thus a stable captured checkpoint missing the refinement observations plus a stale/all-true verdict is not closed by the other validations.
   - `calibration_wave.amplitude_error`: frozen `scripts/fanout_campaign_verdict.py:156–166` selects both N128, jitter .15, parallel 0, fixed, unconstrained-dt calibration runs and requires each final B L1 divided by .1 to be at most .02. V:737–739 checks analytic field names and a reported production-agreement scalar, while V:752–758 gates the N256 finest error and finest-three slope. Neither enforces this N128 bound. The middle N128 point can exceed the calibration bound while the N256 accuracy and endpoint fitted slope still pass. Boost agreement is also a different requirement.

   **Repair:** freeze the exact registered check sets, reject missing/renamed/extra checks and any failed/error phase, and connect the registered checks to the appropriate captured observations. At minimum add the existing mean-refinement observation rules and exact two-run calibration selection/error test. Do not infer those rules from a nonempty dictionary or introduce an order threshold for mean residuals or temporal observations. Use the frozen scripts as definitions; no raw numerical operator needs to be rerun by these metadata checks.

   Derived check inventory, confirmed against the actual closed A verdict schema:

   | Phase | Exact check set |
   | --- | --- |
   | `bounded_short` | `workflow_completed`, `same_snapshot`, `gate_file_unchanged`, `four_short_stages_passed`, `blockers_closed`, `configuration` |
   | `bounded_medium` | B plus `all_runs_completed`, `positive_and_conservative`, `boost_pairs_passed` |
   | `mean` | B plus `all_completed`, `positive_and_conservative`, `boost_pairs`, `execution_configuration`, `mean_refinement_measured` |
   | `calibration_wave` | `all_completed`, `positive_and_conservative`, `boost_pairs`, `execution_configuration`, `amplitude_error` |
   | `calibration_vortex` | `complete`, `diagnostics`, `execution_configuration` |
   | `physics` | B plus `physics_gates`, `complete_ladder` |
   | `waves` | B plus `all_completed`, `positive_and_conservative`, `boost_pairs`, `execution_configuration`, `spatial_gates`, `temporal_measured` |

   Here B is the seven plan checks `same_snapshot`, `registered_cases`, `registered_options`, `terminal_without_errors`, `every_planned_case_completed`, `same_binary`, `candidate_and_limiter_metadata`. Definitions are `fanout_campaign_verdict.py:52–75,78–111,147–192`, `run_m1_campaign.py:59–90` and `run_m1_bounded.py`'s registered medium verdict. Key-set enforcement alone does not establish that a supplied true value agrees with its captured inputs. Conversely, the short bounded/preflight bytes are already pinned by the immutable 69-file parent closure and checked at V:1015–1082; their isolated all-true checks are not an independent full-path bypass of those fixed bytes.

   **Smallest future REANA controls:** reject the current `metadata_control` substitute and one missing, additional or renamed check per phase using a copied real verdict; independently reject a missing/malformed mean-refinement row and an above-limit selected N128 calibration error while phase flags remain true. Keep these labelled metadata mutations, without fabricating a passing complete campaign.

2. **High — per-case physics diagnostic semantics are still accepted as nonempty all-true flags.** V:621–623 requires `state_and_diagnostic_gates` and a nonempty all-true `diagnostic_checks`, but not its required keys, `diagnostic_gates`, diagnostic values or agreement with recorded histories. The unchanged strict verifier has the same limitation at `verify_fresh_phase.py:124–125`; its execution/record/hash checks establish the identity of the recorded object, not this omitted semantic relationship.

   The source definition is exact: `scripts/run_m1_physics.py:233–248` requires shock `signal_tracking` and `seam_isolated`, adds `bx_preserved` on regular/column meshes, and requires the two named normalized mean-B-drift and limited-face dimensionless divB RMS checks for every vortex case. `run_m1_physics.py:37–47` and `benchmarks/m1/shock-bx-amendment.json` gate final Bx at 1e-8 only for regular/columns; planar-jitter Bx remains diagnostic with `passed=None`. The packet's seam bound is .45, vortex drift bound .001 and vortex limited-face RMS bound .1 (`benchmarks/m0/packet.json:49–59`). These are existing gates, not proposed replacements.

   Other connected checks do not close this gap. V:843–871 validates primary shock/vortex reference norms; shock fields are rho/p/vx/By, and its independently reported `final_Bx_max_error` is never checked there. Fifteen boost pairs constrain differences between paired solutions, not their common Bx preservation or recorded divergence/drift. Primary vortex norms cover only the six regular reference cases; the diagnostic gates also cover the jittered cases. A removed required diagnostic key can leave a nonempty true map, and contradictory recorded diagnostic values can remain unchecked.

   **Repair:** require the case-specific exact key sets and existing diagnostic flags; connect shock travel/tracking/Bx applicability and recorded values to their existing source/packet/amendment definitions, and vortex values to the existing history-derived maxima and normalization. Check internal duplicated Bx values and the independent primary shock Bx receipt where available. Preserve the planar-jitter exemption and the exact limited-face divergence operator; do not substitute a different divergence diagnostic or recompute raw operators in this utility. These consistency checks do not certify the recorded history as an independently evolved solution.

   **Smallest future REANA controls:** copy one actual regular/column shock, planar-jitter shock and jittered vortex record. Remove a required key while another true key remains; contradict a recorded value/history with unchanged true flags; exercise both sides of the existing Bx applicability rule. Require rejection of the contradictory metadata and continued support for the correctly labelled planar diagnostic-only case. No new evolution is needed.

3. **Medium — a spatial gate's recorded order need not agree with its own errors, and its uncertainty can be absent.** V:755–758 connects four `B_L1` entries to their named independent case errors and checks the reported order against 1.8, but never connects that order to those errors. It never reads `residual_based_order_standard_error`. The production checkpoint's convergence fit is not separately validated by this full path; a true verdict flag is not that validation.

   The frozen independent reducer defines both quantities at `reduce_waves.py:203–221`. Manual algebra for the equally log-spaced N64/128/256 fit gives `p = ln(e64/e256)/ln(4)`. The N128 value contributes to the residual-based standard error, not this slope. With `x=ln(1/N)` and `y=ln(error)`, its reported standard error is `sqrt(sum((y-y_mean-p*(x-x_mean))^2)/sum((x-x_mean)^2))`, with one residual degree of freedom. No new numerical fit was run here. The production fit/uncertainty is recorded separately at `run_m1_wave_loop.py:293–305`.

   **Repair:** require positive fit errors and the complete uncertainty field; validate the recorded slope and residual-based uncertainty against the retained scalar errors with a documented floating-roundoff consistency rule. Connect production/independent fit inputs and recorded agreement as appropriate. Keep 1.8 and .02 unchanged, add no uncertainty acceptance threshold, and retain uncertainty's residual-only interpretation. Temporal dt/cap/order observations remain observations; no temporal order gate is proposed.

   **Smallest future REANA controls:** a copied real spatial row with only its order changed, a missing/negative uncertainty, and a changed middle error with unchanged uncertainty. The latter must leave the endpoint slope definition intact while making the uncertainty inconsistency detectable. These are scalar metadata controls, not a raw-snapshot reduction or a new physical accuracy experiment.

## Supported dispositions of the original review

| Original finding | Disposition at the reviewed source |
| --- | --- |
| 2, original manifest and exported origins | **Source repair supported.** V:336–375 binds the exact copied original manifest digest to the index, manifest artifact and every fresh origin/path/decoded digest. V:303–333 and 1164–1166 require the exact export/omission partition. V:378–429 connects observation copies, summary hashes, original paths, capture generation receipts and tools. P:41–59,95–103,139–144 verifies actual original input bytes, omitted decoded duplicate identities/lengths and final unchanged closure before portable verification. |
| 3, cases/execution/configuration/preflight | **Substantially repaired; findings 1–2 remain.** V:161–181,449–635 compares fresh plan order to its own specifications, matches historical A by name, and links exact case/run/receipt membership, workflow/payload/source parts, execution/record/artifact/preflight identities, resources and candidate commands/defaults. It checks state histories and budget maxima. V:1015–1082 connects pinned preflight/bounded command/log/runtime receipts. These are archived consistency checks, not proof of a new build or independent execution. |
| 4, independent reports/adapters/coverage | **Substantially repaired; findings 1–3 remain.** V:644–676,679–872,875–1012 connects actual consumed input sets, pair partitions, analytic case identities, 8 spatial and 12 temporal identities, 12 primary shocks, 6 primary vortices, source/reference hashes, geometry receipts, 6×4×4096 projected bins and adapter/capture/transport provenance. Physics adapter run maps correctly use semantic JSON equality while reports bind their reserialized byte hash (V:902). No incorrect byte-equality requirement was added. |
| 5, historical closures/A identity | **Source repair supported.** V:102–137,1132–1136 recursively closes and pins 69/9/94 boundaries; V:638–676 derives A flags/count from the copied closed A maps. A/B are separately labelled. Historical cache exclusion is explicit; the new boundary rejects unlisted caches and links. A equality never authorizes selecting A instead of fresh inputs. |
| 7, portable command/transport receipts | **Normal-path portable repair supported against 0398825.** V:194–269,875–1012,1168–1172 requires the exact 13 successful labels, captured script/context/argv links, timing/timeout/runtime/environment/log identities, and the physics workflow/path/transport/acquisition identities. Failed attempts are distinguishable and cannot supply a complete successful command inventory. Lifecycle ownership and failure-envelope repairs remain the separate integration prerequisite below. |
| 8, optimized execution | **Portable source repair supported.** Unconditional P:6–7 and V:6–7 reject optimization before argument processing; journal/runtime checks require assertions enabled. T:542–560 supplies unexecuted `-O` and environment controls. No optimized invocation or import was performed here. |

The coverage arithmetic is connected to named memberships, not only totals: 48+24+112+30=214 cases; 24+12+48+15=99 boost pairs; 214 finals+12 shock geometry+6 vortex geometry+6 vortex bin inputs=238 consumed identities. The physics acquisition path accounts for 54 files: 30 finals, 18 geometry and 6 bin inputs. V:663–674 and the adapter checks connect the actual fresh workflow and `outputs/raw/<case>/<filename>` to source/copy paths and artifact hashes. Full boost reports require `all_passed`; a partial wrapper's `all_available_pairs_passed` is not silently promoted to that schema.

P:69–79,113–118 and V:1137–1149 retain the historical Git blobs instead of requiring later M2 working files to match M1. I independently rehashed the selected 237 blobs against the snapshot: 226 science/configuration files, one toolchain file and ten external-reference/provenance/license files; no mismatch. This is byte identity, not a build. Captured reducers/reference files are connected at V:432–446 and report/command sites; eight frozen reference scripts remain byte-identical to the original reviewed versions. Deterministic gzip headers and separate stored/original hashes/lengths are appropriate; they do not promise identical compression across every runtime. Large raw files are explicitly omitted from the portable archive, with actual identities/retrieval provenance retained. Portable verification cannot re-read omitted bytes, certify original staging/build/operator execution, or replace final numerical review.

The optional sibling mode at V:1187–1201 recursively closes evidence and reviewer manifests and connects the outer record's configuration and manifest identities. Its output is explicitly **consistency only**, with `full_m1_accepted=false` retained. It does not establish that a review recommends acceptance, write acceptance, or confer authority on an acceptance record. The archive-plan sequence—freeze evidence, pin it in a separate reviewer boundary, resolve review and actual gates, then coordinator acceptance/outer closure—avoids circular hashes and remains appropriate.

## Prospective peer integration boundary

Collector review findings 3–4 at `8790fb1` remain unresolved at the reviewed `0398825` baseline: nested/interrupted writer cleanup and early post-creation failure status. The coordinator's later relay `msg_86d9cd338a03` describes **proposed**, undelivered ownership fields and top-level `command_ownership` JSON/lock receipts. Those are not reviewed bytes or executed evidence. V:303–333 currently rejects those unclassified paths, so eventual integration must explicitly retain their roles, manifests, node/parent links and cleanup/writers-stopped semantics. Silently dropping them or merely tolerating additive row fields would not close the lifecycle requirement. This is a prospective interface prerequisite, not a current incompatibility with the exact three-field successful `collection_status` produced by 0398825; V:1162–1163 correctly matches that baseline.

After the actual lifecycle delivery, review its final committed schemas jointly with the archive selection/verifier and failure paths. Review the independently repaired runner separately; no mutable runner file, import preflight, selector or test execution is approved here. Retain unsuccessful collection/packaging attempts and externally recoverable unfinished receipts; never convert missing observation or transport data into a physical failure or duplicate numerical submission.

## Complete written-test inspection

Every T method below remains **unexecuted**. Positive helper controls establish only the specified local schema relationship when later run; they are not passing complete packets. Top-level imports are standard-library facilities plus explicit loading of V; neither P nor a numerical reducer is imported by the suite. The optimized controls launch only the two reviewed tools' early rejection paths. Import-surface conclusions are static inspection, not an import preflight.

| T line | Method suffix after `test_` | Intended control / limit |
| ---: | --- | --- |
| 134 | `connected_manifest_bytes_control` | One clearly nonphysical observation with connected manifest/decoder. |
| 140 | `disconnected_original_manifest_hash` | Wrong original manifest identity. |
| 148 | `disconnected_origin_path_or_manifest` | Wrong origin path or manifest link. |
| 158 | `original_decoded_digest_and_manifest_artifact_origin` | Wrong decoded digest or manifest-artifact origin. |
| 171 | `stored_and_decoded_length_hash_mutations` | Each stored/decoded length and hash. |
| 184 | `unsafe_and_symlink_paths` | Traversal/noncanonical paths and symlinks. |
| 197 | `nested_missing_and_extra_rejected` | Nested reviewer deletion/addition. |
| 212 | `new_cache_not_exempt_historical_boundary_explicit` | Strict new boundary versus frozen historical cache exclusion. |
| 222 | `exact_copied_historical_closures` | Actual copied 69/9/94 inventories and missing reviewer child. |
| 239 | `semantic_historical_plan_order` | Reversed historical ordering still matches by name. |
| 248 | `a_identity_flags_derived_from_closed_run_maps` | True/false A identity derived from actual closed map digest. |
| 262 | `semantic_case_or_resource_mutation_rejected` | Wrong configuration or memory declaration. |
| 272 | `exact_phase_names_and_receipt_coverage` | Membership-only run/spec/receipt controls; no execution witness. |
| 288 | `candidate_command_defaults_and_flags` | Actual mean/wave/physics commands and rejected acceleration/fraction/screening flags. |
| 306 | `exact_registered_verdict_names_configuration_and_checks` | Phase names/configuration/false value; its positive arbitrary check map misses finding 1. |
| 327 | `actual_execution_receipt_metadata_links` | Actual prior fresh-medium receipt and workflow/payload/artifact/final mutations. |
| 337 | `execution_configuration_preflight_and_record_mutations` | Binary, preflight, record digest and config mutations. |
| 350 | `execution_download_partition_not_only_counts` | Checked/absent partition and unregistered artifact. |
| 362 | `submission_metadata_resources_parts_and_workflow` | Explicit schema-only source/binary parts, command and resource control; no part bytes claimed. |
| 397 | `preflight_and_bounded_retained_receipts` | Closed real preflight/bounded receipts and changed retained log. |
| 409 | `command_source_arguments_context_and_logs` | Thirteen invented transient command/context/log strings; helper only. |
| 454 | `boost_partition_and_mean_input_digest` | Copied real mean pairs, duplicate member and wrong input digest. |
| 469 | `primary_exact_names_and_input_key_digest_sets` | Real primary report names/input sets; full caller supplies independent expected names. |
| 487 | `independent_bin_entries_fields_and_shapes` | Real bins, missing case/field/value/shape; full caller supplies expected six names. |
| 506 | `command_journal_labels_logs_runtime_and_failures` | Small journal mutations; timeout interpretable but rejected for complete success. |
| 532 | `strict_json_duplicate_nonfinite_and_traversal_keys` | Duplicate/nonfinite JSON and escaping inventory key. |
| 542 | `optimized_cli_rejection_before_argument_processing` | Future `-O` negative for both tools. |
| 552 | `pythonoptimize_environment_rejection` | Future environment-optimization negative for both tools. |

The suite does not exercise the whole `verify_evidence`/packaging path, export/capture/adapters together, or the three semantic gaps above. Add the minimal targeted controls in findings 1–3 and focused export/capture/ownership-link mutations after the real integration. Do not invent a complete successful physical fixture to reach them. Each eventual test is an independent REANA workflow with its declared resources, after an actually successful immutable source/import preflight and resolved runner/lifecycle review. The first complete path must then use the actual finished physical data, and the copied standalone verifier must actually run without development-working-tree dependencies.

## Actual checks and remaining acceptance dependencies

Performed only committed-byte capture/hash checks, AST parsing, complete subject/manual test reading, control-flow/schema/algebra inspection, and read-only existing JSON/inventory checks. The existing 69-, 9- and 94-entry listed hashes and non-cache inventories have no mismatch, missing or extra file. Closed historical run/report schemas were inspected as schemas; none was substituted for fresh results. I did not inspect mutable peer repairs or treat running scientific outputs as final. No target import/entrypoint/help/guard/test, numerical reducer/probe/build/evolution, new metadata runner, REANA client/workflow or service control was run. All 28 archive tests and complete collection/packaging/portable execution remain unexecuted.

Entry HEAD was `f780a1440c9f6602a1479ee1b2a5228d6584c745`; the committed context and historical reviews are pinned independently of later working edits. The 43-file retained source/receipt boundary is `results/m1_portable_revision_review_20261122/sha256.json`, SHA256 `60967fdd15223dd8c8551e157db82092ba2b48ccd82ad5e3c766761751014ef0`. The accompanying `m1_portable_revision_review_sources.json` pins this report and that boundary; this report does not hash that inventory. Only these two new documents and the assigned ignored review directory were authored.

Before portable reliance: repair findings 1–3, deliver/review final collector ownership integration and runner bytes, freeze the integrated source, and obtain actual preflight plus every selected metadata-case REANA result. Before M1 acceptance: obtain the fresh 214-case/seven-phase final verdict, read and independently reduce/review the actual complete physical outputs with the unchanged gates and applicable prescribed-flow evidence, execute full collection and immutable packaging/portable verification, resolve the separate final AI output review, and only then allow the coordinator's scoped acceptance and outer closure. None of those pending results follows from this review. The full genuinely moving 3D magnetized live-component merger remains the goal; it is not physically accepted by this metadata review or by the fixed/rigid periodic single-process 2.5D M1 candidate.
