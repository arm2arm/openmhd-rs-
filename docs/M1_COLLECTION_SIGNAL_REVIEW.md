# Independent AI review: collector signal and partial-output correction

2026-11-22. **Conditional source support: both findings in the prior lifecycle review are repaired within the declared cooperative POSIX contract.** I found no additional blocking source defect in this correction or the narrow frozen portable interface. This is source and written-test review, not an executed cleanup result, import approval, numerical-output review or M1 acceptance.

## Exact scope and identities

The subject is Git `0bab08c9164dece7eb0bd913547ba11ee5c8ee9b`; later peer working changes are excluded. **C** denotes `tools/m1_evidence/collect_fresh_physics_reference_inputs.py`, **P** `tools/m1_evidence/prepare_final_evidence.py`, and **T** `tools/m1_evidence/tests/test_collection_metadata.py` at that commit. I read all C1–1025, P1–373 and T1–685, the complete collector diff from `3b2c6f70a19e3268ddf7963a967704cb64ab17e7`, and every direct written test.

| Subject | Bytes | SHA256 |
| --- | ---: | --- |
| C | 52143 | `10b604537daeec56510ec1b884569aee73fe559a00a351ce907123cb02740f0d` |
| P | 23608 | `5fb1a4214aa9309bc8e68d06cbe2396927105213809710c108dcadd5c2889eac` |
| T | 40249 | `ed7d3a7ad70ae116a613c5ecf76fe655730d584f103d59d5fc97e0369bf11bd5` |

P is byte-identical to the baseline; all 24 old direct test ASTs are unchanged and five methods are added, making 29. AST parsing did not import or call the modules. The scientific `main` AST, capture/copy helpers and failure-envelope definition are unchanged.

The historical comparison is [the lifecycle review](M1_COLLECTION_LIFECYCLE_REVIEW.md) at `79739019aafecc86619b53bf5cd5e7810f10980f`, report SHA256 `cdb8893cb7e48c575ef32a7a749607911b7a635df430daa7917091305bbcd169`, inventory `63d8f4fac5afcb8d4098d78eab9e2926f7b0326afed93c9c3d8808af5b49ac56`. The narrow portable comparison is `46378c2c227b721dcdc8d97a3fdeb28a655c7b35`, following [the portable gate review](M1_PORTABLE_GATE_REVIEW.md) at `45328bd`, report `248d483846ef20f7aa1c6a0bc80698258fbe2d8dee9b04d8e8b829e2d20ccc8c`, inventory `aa682a415f0460713cbfd257079d53e221b47f4faf9285cfa355cfcc6ce147cb`. All four historical files remain unchanged.

For portable locators, **A** denotes the packager, **V** the verifier and **AT** the archive test file at `46378c2`. Their SHA256 values are respectively `7df47d18533a8ed686cca5a8ac2634987354f426dc0f0d41bb72ea34110116fe`, `258e644694cee02b1398e0a09c13926497ef3dd762b3940a9c6bf0208a7dcdfc`, and `8d37f9c63cd1c57bd2f8388cd91a29e159f5fd7a59fd1746a3e4d8d5018bf227`. This follow-up reread lifecycle/export/entrypoint paths and ownership controls, rather than repeating the earlier complete 48-method semantic review.

Exact source/context/primary/AST/manual receipts form the [31-file closed retained boundary](../results/m1_collection_signal_review_20261122/sha256.json), SHA256 **`8b29f4742e94e6446fd3be51b19a71f6cc70e262a463e29952eeb362057e5074`**. The manifest excludes itself; this report pins it and the companion source inventory pins this report. The [manual receipt](../results/m1_collection_signal_review_20261122/manual_read_receipt.json) records read ranges and all selectors. Read-only historical 69/9/94 inventory checks found no missing, changed or extra non-cache files; no old packet was rewritten.

## Numbered dispositions

### 1. Prior high finding: ancestry fencing and consumed signal authority — supported repair

C298–327 treats both `<node>.cancel` and `<node>.cancel.tmp` as conservative ancestry launch tombstones. Only a valid canonical cancellation record authorizes cancellation; a partial marker only prevents launch. C389–427 registers/launches under the cancellation registry lock. Both the caller's inherited-parent check and the guardian's check (C557–612) inspect ancestors and markers. A failed node-copy publication therefore cannot reopen the subtree after its ancestor fence exists; a failed atomic fence replacement leaving a temporary entry also prevents a newly registering nested child.

The source ordering is:

1. Under the lock, select the root and registered descendants; publish the root's canonical fence (C459–471).
2. Complete cancellation/unattempted publications for **all** selected nodes before dispatch (C473–486).
3. For an active node with unattempted authority, publish `state=signal_intent` and delivery phase `intent`, including SIGKILL/pgid/by_node_id, before the sole registered-group `os.killpg` (C487–512).
4. Publish `attempted` with `syscall_returned` or `group_absent`; another syscall exception records typed `uncertain`. If acknowledgement publication fails after a possible signal, canonical intent remains consumed (C513–529).

An owner or ancestor seeing intent/uncertainty cannot turn it into fresh numeric PGID authority. The old sequence of nested signal, caller reaping, failed acknowledgement and stale ancestor retry consequently has no dispatch path. UUID ordering can choose either ancestor or descendant first, but the full fence pass precedes either dispatch and the shared lock serializes owners. A normal held guardian cannot complete its closure publication while another holder dispatches under that lock. Later process-table ambiguity may leave conservative unfinished evidence; it never authorizes another signal.

C422–427 removes the unrecorded emergency kill after Popen/PID-publication failure. Only the caller's still-held direct `Popen` can recover that registered child's identity through the same fence/intent protocol (C477–483). The source-failure bootstrap stays held; lost caller/identity instead remains unfinished. An already reaped direct guardian becomes `leader_lost` and is not signalled (C494–501). The direct `/bin/ps` probe's `kill()` is separate from registered-group dispatch.

**Limits:** this is observable publication ordering, not power-loss durability. C90–96 closes a temporary write and replaces its canonical name without fsync. If storage prevents even a temporary entry, no fence or writer closure can be claimed; whatever partial evidence exists needs external recovery. Corrupt/inaccessible registry state raises `CleanupIncomplete`, not authority to signal a historical PID. The declared C353–375 contract requires trusted functioning Python, cooperative same-UID descendants preserving environment/groups, flock semantics and a visible same-namespace process table. Deliberate session/daemon escapes, interpreter/container loss, uncatchable termination, blocked storage and reaping non-child orphans remain outside local guarantees. No old-protocol registry recovery is certified.

**Disposition:** close the prior high source defect conditionally. Execute the five new controls and existing harmless real-child controls after immutable preflight. No additional blocking correction is justified by this inspection; a focused post-Popen/pre-PID-publication write-failure control would strengthen coverage of the documented recovery branch.

### 2. Prior medium finding: late cumulative timeout output — supported repair

`timeout_output_snapshot` (C259–263) replaces each channel with the latest non-`None` `TimeoutExpired` observation. It does not append an already cumulative prefix. `None` retains the previous channel; `b''` is an actual newer empty observation. C731–740 handles initial/outer timeout snapshots; C757–758 handles timeout while draining interrupted cleanup. This closes the former loss of later markers after initial `KeyboardInterrupt`.

After cleanup uncertainty, even a later successful drain cannot make closure true merely because the direct child is reapable. C747–778 preserves `closed=False`; final rows retain `outcome=running`, null finished time/log hashes, `logs_closed=False` and `external_evidence_required=True`. Final stored bytes are redacted and counted. Typed errors avoid copying transport exception arguments. Communicate calls are bounded; normal initial timeout cancels its registered subtree before drain.

T608–662 checks late redacted markers, absence of duplicated cumulative prefixes, channel-None preservation and unfinished fields. Mock observations accord with the inspected CPython POSIX accumulation implementation; this is not proof of the target runtime. An explicit empty-byte versus None control could cover the remaining simple branch directly.

**Disposition:** close the prior medium source defect conditionally. No executed output-preservation result is claimed. A repeated interruption or storage loss can prevent final publication, so failed/unfinished/external-evidence handling remains necessary.

### 3. Immediate envelope and unchanged success/scientific gates — supported, unexecuted

The immediate post-mkdir envelopes remain in both entrypoints (C859; P213–214 onward). C616–663 records typed stage/cleanup evidence, invalidates a published successful manifest into an unfinished manifest and preserves partial bytes on capture/copy/journal/view/reducer/publication/message failure. Unreadable/running records or uncertain cleanup are not closure. If storage cannot publish even failed status, the missing final observation requires external evidence.

P bytes, scientific collector-main AST, existing require calls/candidate/raw identities and 13 successful command labels are unchanged. Successful status remains exactly `status=complete`, `full_m1_accepted=false`, `final_ai_output_review_passed=false`. Capture-v1 and normal ownership-v1 fields remain unchanged. The preparer still gates the existing 214/99/238 case/pair/consumed-input claims. Source preservation is not an observation that missing real outputs exist; neither entrypoint nor any numerical reducer was exercised.

### 4. Narrow frozen portable compatibility — supported in source

The failure-only additions do **not** require broadening successful evidence.v2 or ownership-v1:

- A41–42 checks the original closed manifest; unlisted cancellation/temporary files cannot be silently dropped.
- For listed files, V320–335 allows only the lock and UUID `.json` ownership nodes. `.cancel`, `.cancel.tmp` and node temporary entries are rejected in export selection (A52/V478–510), before A87 creates output.
- A56–57 invokes lifecycle validation before mkdir. V424–435 requires exact outer/nested complete/false/false statuses. Failed, collecting or extended unexpected statuses fail.
- V236–274 requires exact seven-field ownership receipts and closed/finished attempts; an optional failure `signal_delivery` receipt cannot pass by being mislabelled success.
- V353–421 requires exact normal nodes, settled/uncancelled/stopped state, successful return and actual row/registry/parent/argv/cwd/captured-helper/bootstrap links. Extra delivery fields, intents and uncertainty are rejected.
- The copied entrypoint repeats lifecycle checks at V1603 after connecting original manifest/export origins. Final original closure and copied verification remain linked by the packager.

Normal successful C.start/receipt paths still produce exactly these fields and no cancellation marker. I found no present success-path mismatch or justified portable-author repair. Failure markers/partial logs belong in the original partial evidence or a separately specified failure-results collector, not a success archive. Deleting them to manufacture success violates closure. AT842–1004 covers strict ownership classification generically; final joint metadata controls should explicitly check listed/unlisted cancellation markers, delivery fields and intent/uncertain states. These are small schema controls, not fake complete physical packets. No portable entrypoint or test ran.

## All 29 written controls

Every row is source assessment only. The direct class is `CollectionMetadataTests`; selectors below retain their exact names. No current mutable runner, adapter or metadata-results collector was inspected/approved.

| T lines | Selector | What the written control can establish if run |
| --- | --- | --- |
| 88–101 | `test_wave_links_materialize_verified_fresh_bytes` | Fresh symlink materialization checks actual bytes, original identity and local regular-file closure. |
| 103–113 | `test_wave_identical_bytes_wrong_origin_rejected` | Equal bytes with wrong original-run identity must be rejected; content equality alone is insufficient. |
| 115–124 | `test_wave_changed_raw_hash_preserves_failed_partial` | Changed raw hash must retain a failed partial acquisition rather than promote it. |
| 126–135 | `test_closed_collection_rejects_linked_directory` | Linked directories are rejected from a closed collection. |
| 137–153 | `test_capture_parse_hash_copy_use_same_bytes` | Parsing, hashing and copying use the same captured bytes despite later original-file changes. |
| 155–169 | `test_capture_retries_unstable_generation` | An unstable generation must be retried before capture publication. |
| 171–180 | `test_capture_bounded_failure_never_exports` | Exhausted capture retries must leave no exported capture. |
| 182–193 | `test_capture_retries_semantically_incoherent_observation` | Semantically incoherent observations must be retried. |
| 195–205 | `test_capture_late_optional_metadata_is_not_hidden` | A late optional metadata file is a generation change rather than an invisible omission. |
| 207–219 | `test_capture_copy_corruption_rejected` | Copy corruption must be rejected by captured identity. |
| 221–249 | `test_private_view_uses_captured_metadata_and_actual_staged_bytes` | The private view uses captured metadata and actual staged bytes; receipt workflow is fixture-workflow, not a physical campaign. |
| 251–270 | `test_command_start_failure_has_durable_attempt_and_logs` | A mocked launch failure must retain the prelaunch attempt and closed failure logs; it does not cover post-Popen PID-publication failure. |
| 272–288 | `test_command_timeout_retains_partial_logs_and_outcome` | Mocked timeout followed by successful drain must retain partial markers and a timeout outcome. |
| 290–305 | `test_real_host_timeout_is_finalized` | A harmless real child prints a marker then sleeps; timeout must finalize its group, logs and receipt. |
| 307–326 | `test_transport_receipt_redacts_secrets_preserves_requested_paths` | Synthetic secret redaction preserves requested workflow/remote-path receipts; no real credential is used. |
| 328–338 | `test_command_nonzero_retained_without_success` | A nonzero command must retain code/logs without success. |
| 340–382 | `test_exited_leader_pipe_descendant_interruption_is_closed` | A harmless real exited primary with an ordinary pipe-holding descendant is interrupted and must close group writers; KeyboardInterrupt is injected, not an actual SIGTERM delivery. |
| 384–417 | `test_outer_timeout_stops_separately_grouped_nested_writer` | A harmless real outer timeout must cancel a separately grouped nested writer; the killed nested journal stays unfinished rather than becoming invented success. |
| 419–444 | `test_failure_envelope_preserves_first_metadata_copy` | A helper-level second metadata-copy failure preserves the first copied bytes and typed failure envelope. |
| 446–455 | `test_failed_publication_invalidates_successful_manifest` | A tiny nonphysical publication fixture invalidates a nominal successful manifest into an unfinished manifest. |
| 457–480 | `test_uncertain_cleanup_retains_unfinished_attempt` | Mocked uncertain cleanup preserves a running attempt, null hashes/time and external evidence requirement. |
| 482–500 | `test_failure_envelope_covers_journal_initialization` | A helper-level journal-initialization failure remains within the failure envelope and retains partial metadata. |
| 502–548 | `test_post_signal_publication_failure_never_resignals_reaped_nested_group` | A synthetic ancestor/nested registry, post-dispatch acknowledgement failure and reaping barrier must consume nested intent and prevent a later ancestor numeric retry; killpg is mocked. |
| 550–579 | `test_failed_fence_publication_blocks_new_nested_launch` | A real temporary fence entry with mocked canonical replace failure must prevent an inherited nested launch before Popen. |
| 581–606 | `test_failed_signal_intent_is_unattempted_and_retry_dispatches_once` | A mocked prepublication intent failure must cause no dispatch; later cleanup dispatches once per held node and never retries consumed intent. |
| 608–637 | `test_interrupted_cleanup_timeout_retains_late_redacted_markers` | An initial interruption and a later cumulative cleanup timeout must retain late redacted markers exactly once and honest unfinished fields. |
| 639–662 | `test_cleanup_timeout_replaces_cumulative_output_preserves_absent_channel` | Later cumulative stdout replaces earlier stdout while stderr=None preserves the prior channel; no concatenation duplication. |
| 664–671 | `test_optimized_flag_rejected_before_argument_or_output_processing` | A separate -O interpreter invocation must reject before argument/help/output processing. |
| 673–681 | `test_pythonoptimize_environment_rejected_before_output` | A separate PYTHONOPTIMIZE=1 interpreter invocation must reject before output creation. |

All 24 old methods are AST-identical to baseline; all five additions were read fully. Synthetic signal controls use mocked dispatch and a reaping barrier, not actual stale-PID signalling. Existing real-child cases cover ordinary cooperative descendants and a separately grouped nested writer, not daemon escapes. The real-host timeout includes an actual partial-marker assertion.

Module-level imports define the test environment and import guarded collector/preparer modules; source inspection found no test-body execution at import. This is not an import pass. Each final selected method needs an independent **1 CPU / 2 Gi / 180-second REANA workflow** after coherent source/import/capability preflight. Mock cases are small and real-child cases have bounded waits/readiness checks, but declared budget is not measured runtime. Actual ps/flock/session/signal-mask/held-leader capabilities still need verification.

The written methods do not establish all production paths or all interruption/storage states. Small useful additional controls are post-Popen PID-publication failure, node-copy failure after a canonical fence, and explicit empty-channel snapshots. These improve coverage; this inspection found no corresponding new blocker. Helper-level envelope fixtures cannot replace real complete collection execution.

## Primary contracts inspected

Complete retained identities are in the source inventory. The [Python 3.11 subprocess documentation](https://docs.python.org/3.11/library/subprocess.html#subprocess.Popen.communicate), at communicate/TimeoutExpired.output/stderr/start_new_session, establishes that timeout does not kill a child, communicate can be retried, captured channels can be bytes or None, and a private session is requested before execution. The retained [CPython v3.11.14 implementation](https://github.com/python/cpython/blob/v3.11.14/Lib/subprocess.py), lines 1165–1230, 1247–1256 and 2062–2157, reuses per-channel output buffers and joins them cumulatively on the inspected POSIX path, including interruption retry. It supports replacement rather than cumulative concatenation; it is not an invented target-runtime version.

The [os replace/killpg documentation](https://docs.python.org/3.11/library/os.html#os.replace), [pthread_sigmask contract](https://docs.python.org/3.11/library/signal.html#signal.pthread_sigmask), [flock contract](https://docs.python.org/3.11/library/fcntl.html#fcntl.flock), and [pathlib write_text/replace contract](https://docs.python.org/3.11/library/pathlib.html#pathlib.Path.write_text) support the publication/locking analysis. Atomic replacement is namespace atomicity, not fsync durability; a numeric group signal supplies no ownership authority itself; masking is per calling thread. Complete relevant API sections and the named implementation functions were inspected, not every unrelated line in these documentation files. subprocess/os/signal bytes were reused exactly from the old retained boundary; the other official sources were newly retained.

## Required next gates

Proceed to final source integration and prospective metadata execution preparation, conditionally:

1. Freeze and review coherent lifecycle/held-leader runner/adapter/results-collector sources, exact selectors and failure-artifact retention. Excluded peer working changes receive no approval here.
2. Execute immutable source/import/capability preflight on REANA; then each final declared-resource method independently. Collect real receipts and independently review all failure/closure outcomes without inventing completed nested rows.
3. Obtain the actual complete 214-case/seven-phase physical verdict, independent reductions and output/provenance evidence. Historical hashes cannot fill missing observations.
4. Execute immutable complete collection, packaging and copied portable verification with real command/log/source/raw-reference linkage. Preserve failures. Conduct separate final numerical-output review and the coordinator's scoped acceptance decision.

Science remains declared frozen at `2bdcea0d28340e7429e10053a641f92d51fcc696`, snapshot `b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f`, candidate binary `18afcf0308338e2ea0ea7ef5e03dba46af9d7025f3ccf4a6a48ebbfe800d0725`. These were not rebuilt or evolved here. No target import/call/guard, test/mock execution, numerical probe/reduction, workflow/service action or complete evidence execution occurred. No private configuration/credential values were read, printed, copied or hashed.

This AI review grants no M1, 3D, gravity, ISM or merger acceptance. The full live moving 3D magnetized merger remains the goal after actual prerequisites; no scope or scientific gate is retuned.
