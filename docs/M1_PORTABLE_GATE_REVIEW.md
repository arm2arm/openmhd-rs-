# Independent AI review of portable M1 gate and lifecycle integration

2026-11-22. **Conditional source recommendation: the three findings in the `ae57045` portable review have supported repairs at `46378c2`. No additional blocking portable mismatch was identified against its declared collector baseline `3b2c6f7`.** This does not clear the two known collector failure-path findings, the runner/integration prerequisites, or any execution or scientific acceptance gate.

This is an independent **AI source/interface/test-design review**, not human peer review. All three subject files and all 48 direct ordinary test methods were read completely. AST parsing, Git-blob capture, hashes, existing closed JSON/schema inspection and manual algebra/control-flow checks were performed. **No target module was imported or called; no test, help/guard, collector, packager, verifier, runner, numerical reducer/probe/build/evolution, REANA client/workflow or service control ran.** No complete successful physical packet was fabricated. Running scientific outputs were not reviewed as final evidence.

## Exact subject and context

The reviewed commit is `46378c2c227b721dcdc8d97a3fdeb28a655c7b35`, also the entry checkout. Later peer working changes were excluded. In the locators below, **P**, **V** and **T** mean that commit's three files:

| Subject | Bytes | SHA256 |
| --- | ---: | --- |
| P: `tools/m1_evidence/pack_final_review_evidence.py` | 9,693 | `7df47d18533a8ed686cca5a8ac2634987354f426dc0f0d41bb72ea34110116fe` |
| V: `tools/m1_evidence/verify_final_review_evidence.py` | 105,313 | `258e644694cee02b1398e0a09c13926497ef3dd762b3940a9c6bf0208a7dcdfc` |
| T: `tools/m1_evidence/tests/test_archive_metadata.py` | 58,636 | `8d37f9c63cd1c57bd2f8388cd91a29e159f5fd7a59fd1746a3e4d8d5018bf227` |

The comparison review is [M1_PORTABLE_REVISION_REVIEW.md](M1_PORTABLE_REVISION_REVIEW.md), frozen at `ae57045b65a04ad6753f8561d388bca03d9dda06`, report SHA256 `ca2cce6d1e1127b4d35f282e1b94ab69df0dcd15e6f56d1b274c053b223d67bd`. The separate [collector lifecycle review](M1_COLLECTION_LIFECYCLE_REVIEW.md) is frozen at `79739019aafecc86619b53bf5cd5e7810f10980f`, report SHA256 `cdb8893cb7e48c575ef32a7a749607911b7a635df430daa7917091305bbcd169`. Both historical reports and their inventories remain unchanged.

Collector integration was compared with the exact delivered `3b2c6f70a19e3268ddf7963a967704cb64ab17e7` bytes: preparer SHA256 `5fb1a4214aa9309bc8e68d06cbe2396927105213809710c108dcadd5c2889eac`, collector `b5dce4a68a20a3cf27f1155925b01e7198f84eee65596ab3ad5a13a90d3e3c30`, collection tests `d8ce10e13e3371cb992ff3d247b67f85ca4095a6050272cbf487ae43c2c42dfa`. Undelivered repairs to that lifecycle, and mutable runner/adapter files, are not subjects of this review.

Scientific identity remains revision `2bdcea0d28340e7429e10053a641f92d51fcc696`, snapshot SHA256 `b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f`, candidate binary SHA256 `18afcf0308338e2ea0ea7ef5e03dba46af9d7025f3ccf4a6a48ebbfe800d0725`. The iterative, screening-1, `hlld-pressure`, `smooth-extrema` candidate and historical trial fraction 1 are unchanged. This review changes no threshold, default or registered case.

Required project context was retained at the reviewed commit: AGENTS, README, handoff, roadmap, numerics, validation, archive plan and host-tool README. The relevant source/acceptance/archive/execution sections were consulted alongside the prior reviews. Exact context hashes, frozen gate/reducer identities and all method locators are in [the source inventory](m1_portable_gate_review_sources.json).

## Numbered dispositions

1. **Prior high finding 1 — source repair supported: exact registered checks and connected mean/calibration observations.**

   V:28–44 derives the seven phase/check inventories from frozen `scripts/fanout_campaign_verdict.py:52–111,147–192`, `run_m1_campaign.py:59–90` and `run_m1_bounded.py`'s medium verdict. V:1545–1553 requires those exact seven phases, exact `{checks, passed}` phase objects, exact check-key sets and literal true values. Missing, renamed, additional, arbitrary all-true, failed and error-bearing phase rows no longer satisfy this path.

   The exact sets are preserved. Let B be `same_snapshot`, `registered_cases`, `registered_options`, `terminal_without_errors`, `every_planned_case_completed`, `same_binary`, `candidate_and_limiter_metadata`:

   | Phase | Exact check inventory |
   | --- | --- |
   | bounded_short | workflow_completed, same_snapshot, gate_file_unchanged, four_short_stages_passed, blockers_closed, configuration |
   | bounded_medium | B plus all_runs_completed, positive_and_conservative, boost_pairs_passed |
   | mean | B plus all_completed, positive_and_conservative, boost_pairs, execution_configuration, mean_refinement_measured |
   | calibration_wave | all_completed, positive_and_conservative, boost_pairs, execution_configuration, amplitude_error |
   | calibration_vortex | complete, diagnostics, execution_configuration |
   | physics | B plus physics_gates, complete_ladder |
   | waves | B plus all_completed, positive_and_conservative, boost_pairs, execution_configuration, spatial_gates, temporal_measured |

   This is more than a key-set repair. V:897–936 requires exactly four candidate mean-refinement rows, jitter 0/.15, n coordinates [8,16,32,64], dt coordinates [.001,.0005,.00025], finite nonnegative measurements and order-array lengths one shorter than the values. It connects each selected value to the captured production pair's B L1 residual, validates pair coordinates against the captured run configuration and preserves historical empty-profile rows. V:939–950 selects **exactly** the two named N128, jitter .15, parallel-0, fixed, unconstrained-dt base/boost runs and requires each B L1/.1 <= .02. V:953–983 connects their captured pair, production pair statuses, temporal observations and complete physics summary.

   Actual reachability is V:1615–1616 after hash-bound capture/phase/raw checks. P:149 calls the same complete portable entrypoint. Thus plausible true flags alone no longer replace the missing observations identified in the earlier review. Pair/report validation at V:1157–1239 separately closes case partitions and independent report identities; these helpers do not claim to reconstruct omitted raw bytes.

   **No new mean or temporal order gate is introduced.** Mean successive-order contents remain observations; the frozen rule requires their array length, not a lower bound. The temporal rule remains twelve completed finite B L1 observations, with dt/cap/reference/step metadata linked separately. T:388–488 supplies copied-real positive and adversarial controls, all unexecuted.

2. **Prior high finding 2 — source repair supported: per-case physics semantics, all-case history checks and primary Bx connection.**

   V:986–1061 now checks every one of the 30 physics records through V:1617–1620, using hash-verified frozen packet/amendment bytes. Source definitions are `run_m1_physics.py:29–47,75–77,233–248`, `benchmarks/m0/packet.json` and `benchmarks/m1/shock-bx-amendment.json`. It does not rely solely on the earlier nonempty all-true check in V:797–799 or on matched boosts.

   Shock values have exactly `bx_max_error`, `bx`, `signal_travel_x`; Bx has exact initial/final max/L1 and applicability/pass fields. Tracking, nx/ny/domain dimensions, nonnegative finite travel and duplicate travel/final-Bx scalars are checked. The exact required flags are tracking and seam isolation, with Bx preservation added only for regular/columns. Travel must remain **strictly below .45**. The final Bx maximum must be <= **1e-8** where the amendment applies. Planar-jitter Bx remains diagnostic with `gate_applies=false`, `passed=None` and no `bx_preserved` success flag. Initial Bx is recorded, not made a new acceptance gate.

   V:1064–1076 additionally connects each of the twelve primary shock reports' `final_Bx_max_error` to both production duplicates and the unchanged bound; V:1285 calls it. The independent scalar is defined at frozen `reduce_shock.py:146` by the same f64 abs(Bx-.75) maximum. Exact scalar equality is appropriate for this retained subtraction/max receipt, with the limitation that the portable verifier does not re-read the omitted CSV.

   Vortex values/flags have exactly `mean_B_drift_over_Bscale_max` and `limited_face_dimensionless_divB_RMS_max`. V:1040–1056 connects them to the recorded history maxima, with drift norm divided by **1/sqrt(4pi)**, and the specific **div_B_limited.dimensionless.rms** operator. Every vortex, including jittered cases outside the regular primary reference ladder, retains drift <= **.001** and RMS <= **.1**. Both the recorded value and its history-derived value must satisfy the actual bound; the roundoff comparison does not relax it. Positive-state/budget and diagnostic flags are required to agree with those results.

   Signal travel is an accepted-stage accumulated diagnostic. Its tracking/configuration/duplicates and seam bound are checked; the retained diagnostic history does not contain every reconstructed-stage speed needed for an independent reintegration. No such reintegration or raw divergence evaluation is claimed. T:489–578 covers the applicable shock families, diagnostic-only planar case, exact seam boundary, independent Bx and jittered vortex normalization/history/operator contradictions, all unexecuted.

3. **Prior medium finding 3 — source repair supported: separate production/independent fits and residual standard errors.**

   V:1079–1090 validates exact analytic norm fields/shapes, finite nonnegative values and the reported maximum production/independent difference against those retained scalars, preserving the original strict **<2e-13** agreement rule from `reduce_waves.py:164–168`. V:1127–1154 connects the four independent named errors and four production rows to their respective captured inputs, then validates each fit on its **own** finest-three errors. V:1187–1196 selects all eight exact spatial ladder identities and reaches this helper.

   Manual derivation from frozen `run_m1_wave_loop.py:213–223,293–305` and `reduce_waves.py:203–221`: let a=ln(2), y=(ln e64, ln e128, ln e256). Centered x=ln(1/N) is (a,0,-a), so Sxx=2a² and the least-squares slope is

   ```text
   p = (y64-y256)/(2a) = ln(e64/e256)/ln(4).
   delta = y64 - 2*y128 + y256.
   residuals = (delta/6, -delta/3, delta/6).
   RSS = delta²/6.
   SE(p) = sqrt(RSS/Sxx) = |delta|/(sqrt(12)*a).
   ```

   There is one residual degree of freedom. The middle error changes residual uncertainty while leaving the exact endpoint slope fixed. The production source uses the centered least-squares expression; the independent source uses the endpoint expression and numpy log/centering for residuals. V:1093–1124 preserves these distinct expressions rather than requiring identical fits when their own error inputs differ within the original agreement bound. Positive finite errors and finite arithmetic are required; zero/negative errors cannot enter log fits. This was algebraic inspection, **not an evaluated fit or numerical experiment**.

   V:82–98 documents the fixed comparison rule: |actual-expected| <= 256*binary64-epsilon*max(|actual|,|expected|,explicit scale). With no supplied scale, zero requires exact zero. Fits supply a finite log-input/centering scale, max(1,|x|,|y|)*(1+|p|)/sqrt(Sxx), to allow absolute roundoff near vanishing residuals. This reflects subtraction/cancellation scales in short finite log sums. It is a defensible declared engineering allowance for these metadata comparisons, **not a certified universal libm bound**; actual supported-runtime behavior remains an immutable-preflight/REANA prerequisite. It is not added to any physical inequality.

   Both independently calculated and recorded slopes must remain >= **1.8**, and each finest relative error remains <= **.02**. The production residual-only uncertainty scope is required verbatim. No uncertainty threshold or temporal order threshold is added. T:579–635 targets changed independent/production order, missing/negative uncertainty, stale middle-point residual, altered production inputs, false under-limit analytic-agreement scalar and invalid fit inputs/scope, all unexecuted.

4. **Portable lifecycle integration — successful-schema repair supported against exactly 3b2c6f7; final joint review remains a prerequisite.**

   P:41–57 validates the original closure, then calls V:431–444's shared lifecycle check **before P:87 creates the export**. An outer or nested collecting/failed status fails first at V:424–435. Complete status remains the exact three-field complete/false/false object. Journals require finalized timestamps, closed exact log bytes/hashes, stopped ownership writers, no external-evidence requirement, thirteen successful root labels and successful transport rows. An unfinished nested record cannot be promoted to complete merely because its outer process exited.

   V:320–335,478–510 explicitly classifies UUID-named regular node JSON files and the empty registry lock for selection. They enter the original-manifest/export-origin/decoded-byte closure rather than being silently dropped. V:353–421 requires exactly the root rows' nodes plus the transport rows' nodes: no missing, unreferenced, extra or cyclic ancestor graph. The full preparer has **one outer shared registry**, not a nonexistent nested registry. Nested transports must be children of the physics_inputs command and lie within its recorded interval.

   Exact successful node fields, node/filename/row/registry/parent identities, actual argv/cwd, guardian/primary identities and zero primary result, settled/not-cancelled/writers-stopped state, source digest/path, literal captured bootstrap and complete isolated launcher argv are linked. V:338–350 parses the captured source literal using AST without importing it. It correctly distinguishes original helper paths for outer nodes from the captured helper path for nested transports, while requiring the actual same source bytes at V:442–444. These match delivered collector `OwnedCommand.start` at C:356–400 and the normal journal/guardian path described in the frozen lifecycle review.

   The portable entrypoint repeats the same lifecycle checks at V:1603 on decoded exported bytes. V:1390–1451 also closes acquisition/workflow/transport requests and the exact nested metadata/log inventory, including nested status. The original manifest, artifact origins and selected-path equality prevent receipt exclusion through an unrelated self-report. T:842–1003 supplies eight new lifecycle controls; the synthetic graph is explicitly process metadata, never a physical campaign.

   **Known external blocker, not a newly discovered portable defect:** the `7973901` lifecycle review still requires (1) a durable pre-signal cancellation/signal-intent fence to prevent stale numeric group authority after failed publication, and (2) retention of later-only partial output from a timeout during interrupted cleanup. This archive's receipt checks cannot establish that those process operations actually occurred safely. Source-derived closure flags are not independent liveness attestation. Do not count this review as resolving either finding. Review the final delivered lifecycle/schema changes jointly with selection/ownership validation and the runner; do not guess new fields or approve mutable working edits.

   Deliberate unregistered daemon escapes, container/interpreter loss, inaccessible process/storage observations and non-child orphan reaping remain outside the cooperative POSIX guarantee. Requiring honest unfinished/external-evidence receipts is appropriate. No present portable mismatch with the declared successful `3b2c6f7` schema was found.

5. **Retained archive contracts — no regression identified by source/hash inspection; execution is still absent.**

   V:513–606 binds exact original manifest bytes/digest, per-artifact origins/decoded identities, capture copies/generation and expected captured source roles. P:100–108 checks selected original hashes; P:144–149 rechecks the original closure, closes the export and calls complete verification. V:1604–1606 enforces exact selected/omitted partition. Large raw inputs are explicitly omitted with decoded identity/length, source/workflow/path/artifact provenance; their bytes are not independently checked by a relocated verifier.

   The actual case/receipt/specification/plan membership checks and input schemas remain connected at V:626–854,1157–1451: 48+24+112+30=214 cases; 24+12+48+15=99 boost pairs; 8 spatial and 12 temporal comparisons; 12 primary shock and 6 primary vortex cases; 214 finals+18 geometry+6 projected-bin inputs=238 identities. The physics acquisition accounts for 54 files. Independent bins retain exactly six cases, four named fields and 4096 finite entries per field. Physics reserialized run maps correctly use semantic equality while independent reports bind their actual serialized byte hashes. A byte match with A is derived from closed A maps; it never licenses historical-A substitution or proves an independent new reduction.

   Historical 69/9/94 closures remain pinned and recursively checked at V:157–173,1572–1577. Historical cache exclusions remain explicit; new evidence/outer boundaries close every file and reject extra caches/links. The 237 selected historical Git blobs remain anchored to the snapshot, with 226 science/configuration files, one toolchain file and ten external-reference files. V:1581–1590 uses archived source bytes, so portable checks do not require later M2 working files to stay unchanged. Current context documents and A/B archives remain separately labelled.

   Source/runtime/timeout/log/command links and captured immutable reducers remain connected at V:236–317,609–623,1313–1451. The eight original strict/reference/adapter/reducer scripts are captured by exact hash. Unconditional optimized-mode guards precede imports/argument processing in P:6–7 and V:6–7. No guard invocation occurred here.

   V:1628–1642's optional sibling outer mode closes evidence/reviewer manifests and connects the outer record's source/configuration/manifest identities. Its scope remains **consistency only**, without an acceptance decision and with the evidence result's full_m1_accepted=false. The sequence is still immutable evidence, separate reviewer inventory pinning it, resolved gates/review, coordinator acceptance, then outer closure. It creates no circular evidence/reviewer hashes.

## All 48 written tests: inspection and limits

AST inspection confirms 48 ordinary direct `ArchiveMetadataTests.test_*` methods; all 28 prior method names remain and 20 are added. This is not a claim of identical old method bodies: notably the verdict positive control is now the actual closed historical schema. The complete subject source, helper fixtures and every method were read. **All remain unexecuted.**

Top-level imports are standard library facilities plus the suite's explicit future load of V. V's top level defines helpers/constants and rejects optimization; it launches no command. This is a static import-surface conclusion, not an import preflight. The two optimized controls would run early rejection subprocesses, each with a 30-second timeout. Other controls read/copy closed metadata or use small synthetic schema/process graphs; none evolves a state, runs a reducer or constructs a passing full physical packet. Exact direct selectors must still be pinned by the final runner.

| T line | Method suffix after test_ | Written control |
| ---: | --- | --- |
| 216 | connected_manifest_bytes_control | One nonphysical JSON observation; original/export connection only. |
| 222 | disconnected_original_manifest_hash | Reject disconnected original manifest digest. |
| 230 | disconnected_origin_path_or_manifest | Reject wrong origin path or manifest. |
| 240 | original_decoded_digest_and_manifest_artifact_origin | Reject wrong decoded digest or manifest-artifact origin. |
| 253 | stored_and_decoded_length_hash_mutations | Stored and original lengths/hashes, including a connected positive decoder. |
| 266 | unsafe_and_symlink_paths | Traversal/noncanonical names and links. |
| 279 | nested_missing_and_extra_rejected | Tiny nested reviewer closure: missing/extra. |
| 294 | new_cache_not_exempt_historical_boundary_explicit | New cache rejection; historical exception explicitly tested. |
| 304 | exact_copied_historical_closures | Real copied 69/9/94 closures and nested deletion. |
| 321 | semantic_historical_plan_order | Fresh order follows its specs, A compared by names. |
| 330 | a_identity_flags_derived_from_closed_run_maps | Exact equality and inequality flags derived, not asserted. |
| 344 | semantic_case_or_resource_mutation_rejected | Name/config or resource change against A registration. |
| 354 | exact_phase_names_and_receipt_coverage | Membership-only exact case/receipt sets. |
| 370 | candidate_command_defaults_and_flags | Real closed commands plus forbidden cached/fraction/screening mutations. |
| 388 | exact_registered_verdict_names_configuration_and_checks | Real closed verdict replaces arbitrary true-map positive control. |
| 407 | every_phase_exact_check_inventory_and_error_rejection | Every phase: missing/extra/renamed/substitute/error/failed. |
| 429 | real_mean_refinement_missing_row_coordinates_and_order_lengths | Real four-row observation; missing/duplicate/coordinate/value/order-length mutations. |
| 458 | mean_refinement_values_bound_to_captured_pairs | Plausible finite value and pair-coordinate contradictions. |
| 471 | exact_calibration_wave_selection_and_amplitude_bound | Both selected N128 errors fail above bound; unrelated N64 outside this helper. |
| 489 | regular_and_column_shock_exact_diagnostic_flags | Both applicable families; required flag/applicability/duplicate contradictions. |
| 510 | planar_jitter_shock_remains_diagnostic_only | Real above-gate planar error remains diagnostic; no false pass/gate/extra flag. |
| 529 | shock_tracking_travel_seam_and_independent_bx_receipt | Tracking, duplicate travel, exact .45 seam boundary and primary Bx. |
| 554 | jittered_vortex_named_history_maxima_and_normalization | Missing flag, wrong normalization/history/operator. |
| 579 | real_spatial_fit_order_uncertainty_and_production_links | Real copied fit; independent/production slope, uncertainty, input contradictions. |
| 597 | middle_spatial_error_changes_residual_not_endpoint_slope | N128-only consistent input mutation leaves stale uncertainties. |
| 610 | analytic_agreement_scalar_matches_retained_norms | Under-limit but wrong retained disagreement scalar. |
| 621 | spatial_positive_inputs_and_residual_scope | Zero/negative/nonfinite inputs; missing/negative uncertainty; wrong scope. |
| 637 | actual_execution_receipt_metadata_links | Real closed medium workflow/payload/artifact/final links. |
| 647 | execution_configuration_preflight_and_record_mutations | Binary/preflight/record identity contradictions. |
| 660 | execution_download_partition_not_only_counts | Actual downloaded/omitted artifact memberships. |
| 672 | submission_metadata_resources_parts_and_workflow | Explicit synthetic submission schema only, not staged bytes. |
| 707 | preflight_and_bounded_retained_receipts | Real copied receipt/log closure and log mutation. |
| 719 | command_source_arguments_context_and_logs | Synthetic directory strings and exact 13-label argv/cwd/log association. |
| 764 | boost_partition_and_mean_input_digest | Real mean pair partition and input hashes. |
| 779 | primary_exact_names_and_input_key_digest_sets | 12/6 real primary names, 24/18 inputs; missing/wrong names. |
| 797 | independent_bin_entries_fields_and_shapes | Six entries, four fields, 4096 finite cells; mutations. |
| 816 | command_journal_labels_logs_runtime_and_failures | Synthetic journal; finalized timeout interpretable but not success. |
| 842 | ownership_nodes_lock_and_nested_status_are_exported | Selection schema only; UUID/lock/nested status retained, malformed paths rejected. |
| 859 | ownership_real_source_launcher_and_exact_node_links | Synthetic graph using actual source/bootstrap; row/node identity changes. |
| 879 | ownership_missing_extra_cycle_and_unlisted_receipts | Missing/extra/cyclic/misnamed/unlisted nodes. |
| 903 | ownership_captured_guardian_hash_and_isolated_bootstrap | Hash/path/isolation/literal bootstrap/command-node links. |
| 925 | ownership_writer_cleanup_and_log_finalization_fail_closed | Unclosed journals and unsettled/cancelled/nonzero/error nodes rejected. |
| 959 | nested_transport_uses_parent_outer_registry_and_interval | Wrong registry/parent/interval and nonexistent nested registry rejected. |
| 974 | outer_and_nested_collection_status_are_exact_and_nonaccepting | Exact three-field statuses; numeric false and extra fields rejected. |
| 991 | nested_status_rejects_before_any_successful_lifecycle_claim | Invalid nested status rejected before any journal access; helper-only. |
| 1005 | strict_json_duplicate_nonfinite_and_traversal_keys | Duplicate/nonfinite JSON and manifest traversal. |
| 1015 | optimized_cli_rejection_before_argument_processing | Future -O subprocess early rejection, 30-second child timeout. |
| 1025 | pythonoptimize_environment_rejection | Future PYTHONOPTIMIZE=1 early rejection, 30-second child timeout. |

Positive controls using closed A or prior fresh-medium metadata validate those schema relationships only when actually executed. They cannot become new physical evidence. Synthetic submission/ownership/selection helpers deliberately omit real physical inputs and do not call complete verification. The invalid nested-status control proves intended helper ordering; source reachability establishes its pre-mkdir placement, not an executed packager failure case. Likewise an ownership graph accepting consistent success fields cannot establish real stopped writers.

The written negative relationships are meaningful: copied data are mutated independently; mean and calibration mutations retain true verdict flags; planar-jitter's actual Bx above the applicable-family limit remains diagnostic; N128-only spatial mutation preserves endpoint slope while making uncertainty stale; ownership mutations retain other fields but break a concrete link. These cases can falsify the intended contracts without a fake complete campaign. They do not cover the two known collector failure paths, complete packaging/publication, or every runtime/libm boundary.

After final source review and immutable import preflight, run every selected method as its own resource-declared REANA workflow. A one-CPU/2-GiB/180-second envelope is a reasonable prospective starting declaration for these metadata/copy cases and the two sequential 30-second optimization subprocesses, but its actual sufficiency and runtime/filesystem behavior are unverified. The final runner must record failures/timeouts rather than skip them or treat them as passes; its own source/adapter review remains separate. Existing focused controls are the smallest gate checks required here. A small direct roundoff control at zero/near-zero residual and either side of the fixed 256-epsilon comparison would further document the declared rule; it must not retune it or create a new scientific threshold. No additional portable-code repair is identified solely because that direct helper control is absent.

## Read-only receipts and remaining gates

The retained closed **54-file** boundary is `results/m1_portable_gate_review_20261122/sha256.json`, SHA256 **`9a1856d612c707fb0459b4fa859b649c0c959e9a6660128386ee763e850ed41a`**. It contains the exact subject and context Git blobs, source/AST capture, closed historical schemas, identity checks and a manual inspection receipt with all 48 method locators. This report pins that boundary; the companion source inventory pins the boundary and report, without a self-hash cycle.

Independent read-only checks found no listed-hash mismatch, non-cache missing/extra file or link in the historical 69/9/94 boundaries. Their manifest hashes remain respectively `18e38519d43eac6c859c6bb2fd3788031c623cb4d7bb7eb2a2d357058531a7d4`, `ea0b252dda7ba1a850f629dfd28c9dc51f537de49c33a0a52bc30098059658fc`, `da6d8df237f2359ab69718bf73999b8e8ecb6dddd4eae3cde07087006602782b`. All 237 selected historical Git blobs match the snapshot's recorded hashes. These are integrity/source checks, not test/build/reducer results.

Before relying on this workflow, the remaining dependencies are:

1. Repair and independently review the two known collector lifecycle findings; jointly review the final committed receipt schema with these portable selection/ownership checks and the final runner/adapter. Undelivered peer code is excluded here.
2. Freeze a coherent three-suite source version and obtain the actual immutable source/import preflight certificate, then every independent resource-declared metadata-case REANA result. No subject import or test pass is supplied by this review.
3. Obtain the actual finished 214-case, seven-phase physical verdict and independent reductions over the actual 238 fresh inputs, retaining failures and observation retries without duplicate numerical submissions. No final verdict is inferred from partial reports or A equality.
4. Exercise complete collection, immutable packaging and the copied portable verifier on those real completed outputs; preserve unsuccessful attempts. Verify captured source/command/runtime/lifecycle, report/input/reference/geometry/bin identities and final closures using the actual artifacts.
5. Conduct the separate final numerical-output AI review of the immutable evidence, resolve findings, close the review inventory, and only then allow coordinator-scoped acceptance and final sibling outer closure.

Only the assigned new report/inventory and ignored receipt boundary were authored. Earlier review/evidence files, scientific bytes, thresholds, branches, workflows and supervisor were preserved. **M1 remains unaccepted.** This source review grants no 3D, gravity, ISM, source-physics or merger acceptance. The full genuinely moving 3D magnetized live gas/DM/old/new-star merger remains the goal after the actual prerequisites.
