# Independent AI review: original metadata baseline outputs

2026-11-22. **The original acquisition and independent output-review fence is satisfied: the baseline is completely and honestly observed, with no unexplained missing or incoherent row found. The original suite does not pass.** Its actual result is **169 passed, four failed, zero pending/incomplete**, with `whole_suite_passed=false`. Recommend closing the original acquisition fence before later coherent source integration, while preserving this failed baseline permanently. This does not release final scientific collection or grant metadata-suite, M1 or merger acceptance.

I am separate from the coordinator who acquired the packet and executed its offline check. I authored portable `46378c2` and the separately proposed archive-fixture correction. This review does **not** independently approve those algorithms, adopt my proposal or replace their separate independent source reviews. It checks actual acquired data against the frozen identities and documented interfaces. No target validator, test, proposal or service was executed here.

## Exact observed subject and reading boundary

The subject is the closed actual packet `results/m1_archive_metadata_results_20261122_attempt01/`, its original launch receipt, and the actual offline verification under `results/m1_metadata_original_catalog_offline_verification_20261122/`. Source revision is **`b8496c98c85ad7339ec461deabc012f9f08c1d90`**, metadata snapshot **`4ff43e5940c51380282f6a1a0a0f0de30c45c0520dbee657e1c35c703bfbab6f`**, archive **`7681adc54fa7c53cc0bb3ab6a45274a7c5fe9c20fcc8f307555117e8cbc4fa9c`**. This is the original 173-case catalog, not any proposed repaired catalog or a scientific campaign snapshot.

| Actual control | Bytes | SHA256 |
| --- | ---: | --- |
| `collection_status.json` | 280 | `24758873f92b991037528caa74bd84815c2e3e1d9acf08593b726d5bafa0560f` |
| `summary.json` | 737410 | `3833eba813457d283ddaf3872864c0175765af940adcab4e515133f389fa93d4` |
| `files.sha256.json` | 840426 | `956a1b57d390fbfe93f34615324f41b8dea9e6c9c4c9d73a37d518fd96da2181` |
| Original case `plan.json` | 270277 | `9fb6b955f62683a442baecce8d9f6db0064a2d0b1ef5845f7b8d59075094e7c8` |
| Original `submission.json` | 14975 | `16963a1a5875452cca00408d5e04347de3e08b393954d2706b2e6c2076e1d171` |
| Original import-preflight certificate | 559642 | `a95fd026c598b97145aa2fa940abc8842774aeb0b78d08848e103ec4d955d805` |

For source locators below, **P** is `tools/m1_evidence/prepare_metadata_reana.py`, **J** is `reana_metadata_job.py`, and **C** is `collect_metadata_reana_results.py`, all exact original `29a38f9` bytes retained in the snapshot. Their SHA256 values are respectively `ce54b54204df409758874b6dc4f48456c4d5d7b5bea6513fa99dc959e17b3e12`, `5b1bf259f638135ccbee32eab3c3e81bb1090f35e97fc420eba69db9f57fbbee`, and `ffd7f3510f2c0f28b2bfde36c89d361cf276007299cd4e948685f57f825025b3`. The unchanged adapter hash is `09a7f0cbaaa657eb6d84668dced7693c57c9784e78135adc86e72737ded79c4a`. All four working host files still equal the snapshot's source bytes. No proposed replacement entered this acquisition or review.

The prior [exact-source results review](M1_METADATA_RESULTS_DESIGN_REVIEW.md), [actual preflight review](M1_METADATA_PREFLIGHT_REVIEW.md), [independent archive-fixture proposal review](M1_ARCHIVE_FIXTURE_PROPOSAL_REVIEW.md), and [collector-runtime proposal review](M1_COLLECTION_RUNTIME_PROPOSAL_REVIEW.md) remain unchanged context. Their source recommendations are not substituted for actual outputs here, and this report does not reopen their unchanged algorithms.

The [new 132-file closed reading boundary](../results/m1_metadata_baseline_output_review_20261122/sha256.json), **24474 bytes**, SHA256 **`514f36efb1f474184d98d57e675a0b10523eac4b995df00ddbbfa2a6e2f5798b`**, retains exact small readings, the independent inspection source/results, selected actual logs, and compact identity maps. All 5,897 original packet files remain in their original closed packet; the large tree/source archive was not recopied. `external_packet_identity_map.json` explicitly records hashes/lengths/generations as witnesses, not claimed retained copies. `reading_receipts.json` lists the 77 actual copied readings. The companion source inventory pins this report and manifest without a circular hash.

## Numbered findings

### 1. Supported complete coverage and immutable input identity

**Disposition: no acquisition/coverage blocker found.** Independent byte inspection found exactly **5,896 body files plus the manifest itself**, using its actual `openmhd.metadata-case-results-files.v1` envelope and `files` map. Every listed length/hash matches; the recursive file set, directory set, ordinary-file types and initial/final generations agree. There are no extra partials, caches, links, unregistered files or unexplained empty directories. The top-level manifest excludes only itself; the summary is included in its body.

All **186** canonical regular tar members match the snapshot source catalog and byte hashes. Independent AST enumeration of the three actual archived suite texts reconstructs every selector/source hash/class/method/aliased runtime identity: **29 collection, 48 archive, 96 runner**. This full map equals the snapshot, original plan, summary catalog and all actual executed identities. A count of 173 alone was not treated as coverage. The preflight certificate's captured bytes/hash map still matches its exact pinned original, with 31 parsed/compiled paths and all 173 resolved identities. Its preflight branch ran no test methods; actual methods belong to these later case outputs.

Every original plan entry occupies its exact `0000`–`0172` index and unique version-1 workflow, with the correct selector, case, five payload input pins, certificate, workflow bytes and declared resources/output paths. The copied context has **1,222 unique original-path/role witnesses** materialized into **530 stored shared/input files**. All role-to-stored mappings and actual copied hash/length values agree. I additionally compared each available original context path with its stored bytes and checked final generations. That is an extra identity inspection; C's offline verifier does not require reopening original paths.

Original submission bytes remain **172 acknowledged plus one `submission uncertain`**, exactly covering the plan workflows. No receipt was rewritten to claim an acknowledgement. The shared archive/snapshot/job/certificate are stored once. Compact per-case and source-member maps retain every join rather than copying the 3.6 MB archive 173 times.

### 2. Supported actual terminal observations, transport and artifact closure

**Disposition: no hidden transport loss or unavailable output found.** All **173** cases have exactly 31 files: two observations, transport journal, eight artifacts, and twenty numbered transport logs. Each has observe-before, eight exact allowlisted downloads, observe-after: **1,730 successful return-zero attempts**, with the precise frozen adapter argv, registered workflow, requested/output paths, ordered UTC intervals, output hashes and actual stdout/stderr log hashes. Every diagnostic is completed/success with no partial, and its received/retained length equals the actual requested bytes. All transport stderr logs are empty.

Before/after observations each contain exactly one requested full workflow/version-1 match with unchanged terminal state: **169 finished, four failed**. Every diagnostic names the corresponding actual UUID, consistent across all ten calls and with `runtime.job_path`, `runtime.child_raw_path` and command `cwd`. The 173 UUIDs are unique. Version-1 observations themselves carry names/status/times, **not UUIDs or server completion timestamps**; the UUID join uses diagnostics and remote paths. This review makes no server-signature or cryptographic attestation claim.

Each original `artifacts.sha256.json` has exactly seven `outputs/*` entries, and all seven original file hashes match. Its own hash is connected through the successful download, summary artifact witness and outer manifest. All eight files, including both original child log streams, are retained. Summary observation/artifact/transport witnesses agree with the same actual buffers. No self-reported pass fills a missing file or bypasses a failed observation.

This is actual configured-service access to **four failed workspaces** as well as finished ones; their eight forensic outputs were available. It does not show stopped/deleted workspace retention or every service error behavior. Diagnostic page counts are **346 observe calls at two pages** and **1,384 downloads at four pages**, consistent with repeated one-page scans; this does not establish a nontrivial multi-page/changing-list workload. Actual transport durations range from about 0.411 to 13.776 seconds. They do not establish an absolute 120+15-second deadline: the reviewed cooperative checkpoints/socket-idle/mandatory 300-second direct-process contract remains the source contract at P128–176/C462–483. Passing mocked deadline/framing controls are not observations of a real stalled service.

### 3. Supported one-leaf execution, raw child and parent supervision joins

**Disposition: actual coherent metadata results, not just server-finished labels.** All 173 original raw child buffers parse with duplicate/nonfinite-JSON checks. Their exact original length/hash equals the valid child envelope, and typed parsed values equal both envelope and parent copies. Each requested mode is `unittest`; each reports the exact source-pinned selector/class/method/runtime ID and **exactly one test**. There are four actual errors and **zero failures, skips, expected failures or unexpected successes**. Parent/result/command outcome, Boolean pass, return code, source revision/catalog, snapshot, payload, runtime hash, command hash, argv, cwd and remote UUID agree throughout.

J236–289 checks imported explicit source/hash, plain leaf identity and compiled function-code equality before running J320–332's single suite. Actual outputs record its resulting source/leaf identity. These are meaningful source/runtime links under the trusted wrapper contract; serialized outputs are not independent memory or bytecode attestation. I did not import or compile target code to recreate execution. All tar-member and AST comparisons here were inert reading.

Every actual parent command retains positive original PID/private PGID/SID/starttime, direct child reaped, writers settled, no live PIDs, `leader_held_until_group_close=true` and `group_authority_lost=false`. The child interval lies inside its parent interval. Four commands correctly return nonzero 1 because their child tests error; the other 169 return zero. No row is a launch, cleanup, timeout or missing-child envelope being relabelled as a unittest failure. Source predicates are J788–891 and C304–356.

All nominal parent cleanup records set `term_sent` and `kill_sent` true, consistent with J523–568's unconditional cleanup path. These flags alone do not prove a parent timeout, actual signal delivery to a live process or an injected interruption. They are separate from the inner timeout controls discussed below.

| Actual suite | Cases | Passed | Failed/errors |
| --- | ---: | ---: | ---: |
| ArchiveMetadataTests | 48 | 45 | 3 |
| CollectionMetadataTests | 29 | 28 | 1 |
| RunnerMetadataTests | 96 | 96 | 0 |

### 4. Supported closed acquisition and actual offline verification; both exit 1 honestly

**Disposition: original acquisition/offline requirement met, suite-success requirement unmet.** The status is `complete`, `problem=null`, spanning **10:08:58.417260–10:43:21.748231 UTC**. `complete` describes the acquisition loop and fences, not successful tests. The launch receipt records terminal PID **77681**, exit **1**, finished **10:43:24.341048 UTC**, 197-byte stdout and empty stderr. This review did not poll, stop, restart or reuse that process handle.

The coordinator's actual original P `verify-results` command ran **10:44:25.852285–10:44:27.116515 UTC**, resolved interpreter `/Library/Developer/CommandLineTools/usr/bin/python3`, exit **1**. Its exact command, recording source, streams and four-file receipt inventory match. Both recorded `original_controls_unchanged` and `host_tools_unchanged` are true; all actual current pinned controls/quartet still match those hashes. No host interpreter version or executable-byte attestation is invented from that path.

Acquisition and offline stdout are identical, **197 bytes**, SHA256 `ae2ac61a5171ba3d9dcbb9afd9001953c2c9844a7056994753dffce1588cbb30`, reporting 169/4/0/0 and false whole-suite/acceptance. P279–282 returns 1 for a nonpassing derived whole verdict. Thus exit 1 is an actual valid nonpassing baseline result, **not exit-zero success and not evidence of an incomplete packet**. No verifier was rerun here.

The coordinator's separate supporting `review.json` hashes to `83de1a081b2f13fba12af89ebd2a40a34040b1530d2c75bf68ba42628f097259`; its analysis source and closure are pinned. Its 173 UUID/count checks agree with this independently written buffer inspection. That supporting result was not accepted in place of independent joins, and its target-importing analysis source was read but never executed by me.

### 5. Three archive errors and masked case0010 remain blocking metadata coverage defects

**Severity: high for claiming the original metadata suite passes; not an unexplained acquisition failure.** The actual error records are:

| Directory / original method suffix | UUID | Traceback entry |
| --- | --- | --- |
| `0011` `test_exact_calibration_wave_selection_and_amplitude_bound` | `ae4ce1f4-d6a0-4a9b-be96-a52334e8cff0` | archive test479 → verifier1546 |
| `0014` `test_exact_registered_verdict_names_configuration_and_checks` | `eff18a9d-24fb-49a3-801a-01ad263a2d5a` | archive test391 → verifier1546 |
| `0037` `test_real_mean_refinement_missing_row_coordinates_and_order_lengths` | `069aa6db-2e0a-4e74-b0a4-168f4369fade` | archive test454 → verifier1546 |

Each actual child has one error and the exact `EvidenceError: Exact registered phases/candidate verdict`. The genuine archived historical verdict, SHA256 `bcb442c207029dc98cf14d6250ac7b3f333b08f6428bedd01daf9e7556465f97`, has scientific snapshot `f1fee18166bdfc20575f793c17b6cedfca8c5d1999a68239642bd17e603c092e` and binary `492b56e0b8f70519ac950f9f49c889dbaf462e97732eaf12e9be86f593ea8471`. The untouched fresh-only verifier guard requires `b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f` and `18afcf0308338e2ea0ea7ef5e03dba46af9d7025f3ccf4a6a48ebbfe800d0725`. I joined these actual retained data and literal source fields without calling `check_verdict`. These scientific identities are distinct from the metadata snapshot.

Case **0010**, UUID `9e6030e6-2f07-44f4-a2d7-d4529168fbc1`, genuinely ran and reports passed. Its original test407–427 starts from that already-invalid historical verdict and accepts any `EvidenceError` within negative mutations. The top-level guard at verifier1546 can satisfy those assertions before the intended phase checks. Its passing envelope therefore **does not prove intended negative-branch coverage**. It remains part of the 169 observed passes; it must not be silently recounted as an additional observed error or treated as coverage success.

The separately [independently reviewed archive fixture proposal](M1_ARCHIVE_FIXTURE_PROPOSAL_REVIEW.md) addresses those four methods with a labelled nonphysical positive schema control. It is unintegrated and unexecuted. I authored it and do not reapprove or adopt it here. Neither changing historical identities nor weakening production guards is an acceptable reinterpretation of these original outputs. All three new catalog error artifacts are byte-identical to their earlier forensic originals, whose closed manifests were rechecked.

### 6. Collector0057 is the same actual early metadata-probe error

**Severity: high for the original metadata gate; attribution complete.** Directory `0057`, UUID `22ea181f-2f0c-483b-8225-67353b604ed6`, selects `CollectionMetadataTests.test_command_start_failure_has_durable_attempt_and_logs`. Its actual traceback is test263 → collector705/68 `runtime_info` → `platform.platform` → lazy `uname.processor` → `subprocess.check_output/run` → globally patched `Popen` → test256's empty `commands[0]`, raising `IndexError`. This occurs before the intended durable guardian-launch row, not at the failure branch the test meant to exercise. Parent nominal writer closure and the correct one-test/one-error result agree; it is not infrastructure-only or passing evidence.

Every current original artifact equals the earlier forensic bytes. The old initial manifest transport remains failed with its **655-byte partial**; the separate retry remains a distinct three-successful-transport packet. Their manifest hashes remain `223ca38164db0ce83d51476a396ad2688eebfa87d964177776dd3e8973af4c2b` (32 files) and `dcfae87e8ce24c84774bafa5f67f93c1cde5f75e291a05ea09618496d08904b8` (11 files). The partial and retry manifest bytes equal the currently complete original seven-file manifest. Byte equality does not retroactively change a failed transport or supply its formerly absent UUID certificate. The new whole-catalog acquisition itself has all ten transports successful for this failed test.

The [collector runtime proposal review](M1_COLLECTION_RUNTIME_PROPOSAL_REVIEW.md) conditionally supports its separate source correction. That proposal is still unintegrated/unexecuted and receives no new execution claim here. The analogous runner runtime exposure is also a **separate source issue**, with no additional actual failed runner case in this baseline. Its new proposal/reviewer work is outside this output subject; no passing old runner case proves that hidden probing was absent or that an unseen repair works.

### 7. Same-UUID0156 recovery is complete without rewriting uncertainty

**Disposition: supported terminal attribution; no replacement workflow inferred.** The closed 45-file recovery manifest remains SHA256 `2e0550da1c7278c0598bd4d4b1f62df74fd80c08974e9abf215356f61b418f7a`. All six prior downloaded inputs match their originals, and all seven post-restoration inputs match the current closed plan/payload/source/certificate bytes. The restored file is only the exact original `preflight_certificate.json`. Receipts identify the same planned workflow `...-0156.1`, UUID **`456f3101-cf1a-4b25-b391-94e7762a8de8`**, and one start of that existing version.

Its old recovery summary/observation ends **queued**, following created. Those are historical observations, not edited to finished. The newer complete case has finished before/after observations, ten successful same-UUID transports, exact one-test/zero-error child, and nominal parent/writer closure. The child executes **10:14:18.146582–10:14:18.532247 UTC**, within parent **10:14:14.362995–10:14:18.620320 UTC**. These newer outputs supply finish evidence without inventing a completion timestamp in the old v1 record. The original submission still says `submission uncertain` and retains its original digest.

Initial legacy retrieval and later forced-verification SDK recovery have distinct receipts/scopes. I did not reclassify the earlier retrieval as verified TLS. The later recorded upload/retrieval/start receipts state CA/host verification with redirects/proxies disabled; their source/receipt bytes are retained. This was an earlier authorized recovery, not a write performed by the GET-only whole-catalog collector or by this review. No new private configuration, SDK or network request was used here.

### 8. Actual runtime/capability evidence is stronger than import-only evidence, with limits

**Disposition: supported tested paths; no universal process/platform guarantee.** All actual wrapper/child interpreters agree on **CPython3.11.6, conda-forge, `/opt/conda/bin/python3`, optimize zero**, with the same reported Linux x86_64 platform. Earlier consulted CPython v3.11.14 source is not this observed runtime. Each case/spec/runtime declares **1 CPU / 2Gi / 180-second direct-child-wait**, one metadata method and the pinned image label. Every runtime records `memory.max=2147483648`, `cpu.max="max 100000"`; **35 see eight CPUs and 138 see 24 CPUs**. This does not establish hard one-CPU enforcement or runtime image attestation. Thread/environment settings are source declarations; optimization zero is actually recorded. No complete environment dump or library-thread measurement is inferred.

Actual parent durations span about **2.821–11.533 seconds**, direct children **0.101–8.230 seconds**. Scheduling, extraction, validation and cleanup are outside the declared 180-second direct-child-wait. The short observed runs do not prove every future workflow fits that bound.

The old preflight explicitly did not exercise collector process/lock/mask operations or timeout/detached paths. Actual passing cases now add relevant evidence:

| Original case | Actual control and precise scope |
| --- | --- |
| `0059` | Real exited primary and pipe-holding descendant; handled `KeyboardInterrupt` is injected after readiness, then closed logs/ownership and absent group/writer are asserted. Not an actual external signal-delivery test. |
| `0067` | Real outer timeout with a separately grouped nested writer; asserts two linked stopped nodes and absent writer, while the killed nested attempt deliberately remains running/unfinished. It does not invent a completed inner journal. |
| `0071` | Real harmless child times out after printing a marker; typed timeout, closed logs, stopped ownership and actual retained log hash are asserted. |
| `0166` | Runner two-second timeout with an ordinary descendant writer; marker, reaped child, no live writers and stable later log bytes are asserted. |
| `0167` | Runner two-second timeout with a new-session same-UID log writer; marker, stopped writers and stable later log bytes are asserted. |

With their exact source identities and no skips, these are actual REANA executions of the supported ordinary Linux `/proc`/writable-FD/WNOWAIT and collector `/bin/ps`/flock/mask/session paths used by those controls, not merely definitions imported by preflight. Their temporary internal receipts are asserted inside the test; they are not retained production command registries in this output packet. Other cancellation/publication/redaction/ambiguous/framing controls use labelled synthetic metadata/mocks. Passing those tests checks their assertions, not actual service failures, power-loss durability, arbitrary daemon/UID/container escapes, invisible processes or a complete scientific collector run. No new speculative control is demanded without a concrete gap.

### 9. Original fence can close; the next catalog and physical acceptance remain separate

There is **no unexplained failed, pending, incomplete, missing-output or invalid-envelope row** in the original closed packet. All four actual errors are attributable, and the extra masked0010 coverage limitation is explicit. Original acquisition, real offline verification and this independent output review therefore satisfy the requirement to finish observing the original catalog before later source integration. This conclusion does not convert its result to suite success or waive any failed metadata prerequisite.

The next work is to finish all independent source-proposal reviews, integrate only coherent reviewed archive/collector/runner bytes, commit/freeze a **new source-derived catalog**, obtain its actual REANA source/import preflight, and execute every final selected method independently with the declared resources and no aggregate cap. Proposed selector totals and successful old methods cannot substitute for the final exact source/runtime identities. The new catalog requires its own whole-catalog acquisition, offline verification and independent output review. Original failed bytes, 172+1 submission history and recovery/transport limitations remain immutable.

The dispatch reports fresh scientific 214-case/seven-phase results, all238 raw identities and six independent reports passing; a distinct scientific-output review is active. Those are not certified by this metadata review. Final complete scientific collection/lifecycle, immutable packaging, copied portable execution, separate numerical-output review and scoped M1 acceptance remain pending. **All acceptance flags remain false.** No M1, full3D, isolated gravity, ISM/SF/feedback or merger acceptance follows. The subsequent goal remains the genuinely deforming moving-Voronoi magnetized gas/DM/old-and-new-star galaxy merger after its prerequisites.

## Performed checks and explicit nonexecution

The independent inert inspection records **88,577 existing-data relations** over **7,340 original paths**, with exact packet/source/case/raw/transport/witness/receipt joins and final observable-generation fences. These are data checks, not unit tests. All performed inspection commands returned zero; no nonzero inspection result was suppressed. Some large displayed context/root-JSON reads were truncated, so relevant source/report ranges and structured rows were subsequently inspected in bounded form. The exact inspection source and limitations are retained.

Only the two new review documents and the new ignored reading boundary were written. No original packet, source/test/proposal, previous review, scientific evidence, Git index/commit, workflow, service or supervisor was changed. No target module import/call/guard/help, validator invocation, test/mock, runtime/process probe, build/reducer/evolution, network/platform/private-configuration action, commit, push or delegation occurred. The coordinator's already-recorded offline execution remains distinct evidence; it was not rerun here.
