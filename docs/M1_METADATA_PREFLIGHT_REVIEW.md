# Independent AI review: actual metadata preflight and staged release

2026-11-22. **Recommendation: the actual retained source/import preflight and the staged links support executing the exact 173 registered independent metadata cases on REANA. No blocking output or identity defect was found.** This recommends the next metadata execution step; it neither executes those cases nor accepts their results, the physical M1 campaign or the galaxy goal.

This is an independent existing-output/identity review. I read and parsed retained data, decoded certificate buffers, inspected source where needed to interpret observations, and checked hashes, inventories and links. I did not import or call a target module/validator, run a test/mock/entrypoint, make an adapter/network/service request, submit a workflow or access private configuration. The source algorithms were already reviewed separately; this is not a repeat source audit. I authored portable `46378c2`, so its algorithms are not independently rereviewed here. The independent portable and collector reviews remain the context for those components.

## Exact inputs and retained boundary

The actual source snapshot is `results/m1_archive_metadata_source_20261122/`, source revision **`b8496c98c85ad7339ec461deabc012f9f08c1d90`**. The actual observation is `results/m1_archive_metadata_preflight_observation_20261122/`; the staged, unsubmitted cases are `results/m1_archive_metadata_cases_20261122/`. These are the actual metadata records, not the older scientific preflight or synthetic test fixtures.

| Input | Bytes | SHA256 |
| --- | ---: | --- |
| source `snapshot.json` | 167118 | `4ff43e5940c51380282f6a1a0a0f0de30c45c0520dbee657e1c35c703bfbab6f` |
| source `source.tar.gz` | 3684823 | `7681adc54fa7c53cc0bb3ab6a45274a7c5fe9c20fcc8f307555117e8cbc4fa9c` |
| source `job.py` | 57129 | `5b1bf259f638135ccbee32eab3c3e81bb1090f35e97fc420eba69db9f57fbbee` |
| original `preflight/plan.json` | 679 | `6696cf7e43e8b86e556e5ed14d6d1f7dd7cc7e883b69be574ce48a48a2ca1ca2` |
| original `preflight/submission.json` | 94 | `609c6cbb86c7a6b247ffe948efbbc507a327d03bcc9920eeadc508f979f52c9d` |
| observation `certificate.json` | 559642 | `a95fd026c598b97145aa2fa940abc8842774aeb0b78d08848e103ec4d955d805` |
| observation `transport.json` | 12224 | `c80de42db7e473d1210a341c935afec542a2b8227b026577eea7aaa8de51c575` |
| staged `plan.json` | 270277 | `9fb6b955f62683a442baecce8d9f6db0064a2d0b1ef5845f7b8d59075094e7c8` |

The prior exact-`29a38f9` [source/results review](M1_METADATA_RESULTS_DESIGN_REVIEW.md), committed at `b8496c98`, remains unchanged: report `60a2fc9a2476a6259e3da5ece289c71e7436b0742bc0d98584835b99f3df11b8`, inventory `57484fc7a335c879a784c4203209be1cba5b0eb49e8753a668b27f72662fe14a`. All six reviewed subject identities match the actual archived source. Collector `0bab08c` and portable `46378c2` remain covered by the independent [collector signal review](M1_COLLECTION_SIGNAL_REVIEW.md) at `09f782b` and [portable gate review](M1_PORTABLE_GATE_REVIEW.md) at `45328bd`; this output review adds no independent approval of my own portable algorithms.

The [closed independent reading boundary](../results/m1_metadata_preflight_review_20261122/sha256.json), SHA256 **`a665b5d9a00dd23eae4cb75d1c8aeb0abcdced23b83e3c46431a6d7b70e4024d`**, retains the actual source archive once, snapshot/job, original preflight metadata, all 37 observation files, staged plan, deduplicated small case metadata, compact original-path/hash/length/materialization maps and inspection receipts. The repeated 3.6 MB archive, snapshot, job and certificate were stream-compared across every original staged input, not copied 173 times. The [source inventory](m1_metadata_preflight_review_sources.json) pins this report and the boundary; the boundary excludes itself and both new tracked review documents, avoiding a circular digest.

## Numbered findings and dispositions

1. **Supported release prerequisite — actual immutable source and complete source-derived coverage.**

   `snapshot.json.source_revision`, `archive_sha256`, `job_sha256`, `source_sha256`, `test_files`, `tests` and `test_identities` connect to the actual source bytes. All **186** regular canonical archive members match both the snapshot catalog and the exact committed Git blobs in the three selected roots. No member, duplicate, link, cache or unexpected selected path was found. This checks the newly prepared archive's identity, not the unchanged algorithms again.

   Independent AST inspection of the three actual archived suite texts derives **29 collection, 48 archive and 96 runner** direct methods and their full source-hash-based identities. The resulting sorted 173 selectors and aliased runtime IDs equal the snapshot map and every preflight child identity. The count is derived from those sources; 173 alone is not a coverage criterion. All 31 `.py` catalog paths equal the child's `parsed_files` list. The compact member map and full staged leaf map are retained in `source_member_identity_map.json` and `staged_case_identity_map.json`.

2. **Supported actual observation — correct workflow, status, UUID and original transport bytes.**

   The preflight is **`openmhd-m1-archive-metadata-4ff43e5940c5-preflight.1`**, UUID **`adeedb1f-f934-4619-85d2-def4c9242c5b`**. The original plan/case/payload/spec/submission consistently select that workflow and snapshot. The original submission has exactly that workflow with `status="submitted"`; this review made no submission or platform query.

   `server-before.json` and `server-after.json` each contain one exact `origin="server"`, version-1, full-name match with `status="finished"`, observed at **06:08:30.386849** and **06:08:46.315513 UTC**. Their SHA256 values are respectively `fe388a49e06913d19b662b5c319cee31087ec0a93e881c615cf38c0ccc0ac0dc` and `211055a3dfcbfad9eb298c941c8e02260f638c0977951d86e1293247a3d1e146`. These establish the retained finished observations; v1 does not itself contain a server completion timestamp or UUID. The coordinator-reported server finish at 06:06:39 is not mislabelled as a field in those v1 records.

   All **ten** numbered transport attempts are successful return 0: observe, eight exact `outputs/*` downloads, observe. Every actual argv, requested/output path, downloaded hash, stdout/stderr path/hash and ordered UTC interval agrees. Each observation time lies inside its own attempt interval. Every diagnostic names the same UUID above, which also appears in the actual remote runtime/command workspace paths. Diagnostics are completed/success, have no partial, and their retained/received integer lengths equal the original file lengths. All ten transport stderr logs are empty. The observation inventory is exactly **37 files**: certificate, five original preflight metadata files, two observations, transport journal, eight artifacts and twenty transport logs. There are no partials or extra directories/files in this observation.

   The credential-free actual host argv uses `/usr/bin/python3` and the absolute source-pinned adapter; the adapter source matches the snapshot. The remote child instead records `/opt/conda/bin/python3`. Successful diagnostics are source-pinned consistency evidence, not cryptographic server attestation or an independent statement of the host adapter interpreter version. No private settings or raw REST page was accessed during this review.

3. **Supported artifact/certificate closure — all eight actual outputs and same-buffer links.**

   The original seven-file `artifacts.sha256.json` hashes match every actual artifact except itself; its own bytes are captured by the transport and certificate. Both child-only log artifacts are empty. The actual artifact identities are:

   | Artifact under observation `artifacts/` | Bytes | SHA256 |
   | --- | ---: | --- |
   | result.json | 149545 | `0084a0b4d3bf9e16394ac914dfd04cf323a75bf589f836298ef5876d3e04d8b0` |
   | runtime.json | 909 | `104d8514e73382e08c39cee36e34b906ab8d67636bc05408c4161e863af102bd` |
   | command.json | 1124 | `86e1ba4b9b34d630b2199d1d04b2b141d7dc962cc4ffcbf92bea5a0bddab8538` |
   | stdout.txt | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
   | stderr.txt | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
   | child_result.json | 122809 | `d323f78705c0e23531e8e14f32c75ec7a7f583de857cd506e2e10398173ef355` |
   | child_raw.bin | 120996 | `0eb836eaf970847a641b44371bfa9475b3940a416af64beba2f14d3ac33026cd` |
   | artifacts.sha256.json | 655 | `d6c73cbd87468e7337b8d3d754f81efad244bf341aecb1b850128e4bb4637f5b` |

   Every one of the certificate's **36** strict base64 buffers decodes to the exact corresponding original observation bytes; every `capture_sha256` matches those same buffers. The capture inventory is exactly the observation minus the certificate itself. Original source `preflight/plan.json`, `submission.json`, and `0000/{case.json,payload.json,reana.yaml}` are byte-identical to their observed and embedded copies. Original uploaded archive/snapshot/job/case input hashes, the plan's payload/spec hashes and the declared specification all agree. The result binds the same case, source revision, 186-entry source catalog, snapshot, payload, runtime and command hashes.

   `child_raw.bin` parses as the original preflight child, with its hash/length recorded in a valid `metadata-child-envelope.v1`. That parsed object equals both `child_result.json.value` and `result.json.child_result`, including strict boolean/integer distinctions. Duplicate/nonfinite JSON, canonical path, exact field/inventory and original-versus-copied checks found no contradiction. No target validator was called to obtain this conclusion.

4. **Observed successful import preflight — 31 files compiled and 173 identities resolved; zero test methods run.**

   The actual v2 parent result is `status="completed"`, `outcome="success"`, `passed=true`, integer `returncode=0`, `problem=null`. It spans **06:06:25.965614–06:06:32.980105 UTC**, duration **7.014499807963148 s**. Its child command spans **06:06:29.094723–06:06:32.877501 UTC**, duration **3.7827770530129783 s**, inside the parent interval.

   Actual child fields are `kind="preflight"`, `status="completed"`, `passed=true`, `resolved_tests=173`, the exact sorted selectors/identities and the exact 31 Python file paths. In actual source `job.py:299–319`, this branch parses/compiles source and imports/resolves/constructs the leaves, then returns. The `unittest.TextTestRunner(...).run(...)` branch begins only at `job.py:320–332` for `kind="unittest"`. The unfortunately named `executed_identities` list here contains **resolved** identities; it is not a record that 173 methods executed. No `tests_run` result is asserted by this preflight schema.

   This imports the explicit three test modules and their import-time dependencies, not every packaged Python module. For example, archive tests' lazy verifier load in `setUp` is not exercised by leaf construction; its source is compiled, while its actual setup/import and algorithms await the registered cases. Collector process/locking/signal functions are defined on import and not thereby executed. The literal scientific/evolution/full-M1 flags remain false and agree with this reviewed code path. Empty child logs alone are not used as proof of execution scope.

5. **Observed nominal supervision — useful actual capability evidence with a precise limit.**

   The parent and child agree on **CPython 3.11.6, conda-forge, `/opt/conda/bin/python3`, optimize=0**, with Linux x86_64 recorded in `runtime.json`. The earlier source review's consulted CPython **v3.11.14** tag is not this actual interpreter version. The actual command is the exact remote `job.py --child preflight --result .../outputs/child_raw.bin`, with matching UUID workspace and `cwd=.../source`.

   `command.json.cleanup` reports original PID/PGID/SID **8**, starttime **`28763918`**, direct child reaped, writers settled, no remaining live PIDs, `leader_held_until_group_close=true` and `group_authority_lost=false`. With the exact observed job source, this is evidence of the **nominal** WNOWAIT/held-leader, `/proc` and writer-inspection path in this runtime. It is more than an import assumption and less than a timeout/detached-writer/interruption result.

   `term_sent=true` and `kill_sent=true` are consistent with the unconditional nominal cleanup loop at `job.py:523–568`, not evidence of a timeout or injected signal test. `signal_owned_group` can return true with held authority even when no live group member needs signalling; these flags must not be interpreted as proof of delivery to a live process. The actual command outcome remains success/0. Unregistered escapes, inaccessible processes, competing reaping, timeout escalation, detached writers and collector process-tree/lock/mask operations are not established by this one normal run.

6. **Resource and environment evidence — declarations and observations remain distinct.**

   The actual snapshot/case/spec declare the pinned image label, **1 CPU**, **2Gi**, one serial metadata case and **180-second direct-child-wait** timeout. `runtime.json.image_and_resources_are_declared_labels=true` correctly distinguishes these from attestation. `memory.max="2147483648"` is consistent with 2Gi, while **`visible_cpus=16` and `cpu.max="max 100000"` do not establish hard one-CPU enforcement**. The current REANA policy explicitly requires per-job declarations and actual resource recording; the legacy serial-engine CPU-forwarding limitation is documented in `docs/REANA.md`. No invented universal quota guarantee is made an acceptance requirement here.

   Exact source `job.py:716–719` constructs the child environment with `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `RAYON_NUM_THREADS=1`, `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`, and removes `PYTHONOPTIMIZE`. These are checked source declarations passed on the nominal launch path. The child actually reports optimize=0; no environment dump or measurement of library threads was retained, so no stronger environment/oversubscription observation is claimed. Image digest labels do not identify all running container bytes. Validation, extraction, scheduling and bounded cleanup remain outside the 180-second direct-child-wait scope.

7. **Supported staged release — all 173 original cases, every input and every leaf link agree.**

   The staged plan's source revision/snapshot/certificate pins and full coverage map match the actual source and certificate. There are exactly **173 directories `0000`–`0172`**, each containing exactly the seven specified regular inputs, and `plan.json`: **1212 files total**, with no extra empty/nested directory, output or `submission.json`. Case execution is not inferred from a preflight submission or a prepared plan.

   Every `case.json` equals its plan specification, has `kind="unittest"`, the correct exact selector, versioned unique workflow, resource dictionary and certificate hash. Each actual payload hash and five-input map, actual workflow-spec hash, input-file set, image/resource/command declaration and eight declared outputs agree. All 173 copies of the shared source archive, snapshot, job and certificate are byte-identical to the original shared bytes, checked by streaming comparison as well as SHA256/length. Each small case/payload/spec retains its actual bytes through content-addressed objects; the compact map records all seven original paths/hash/lengths and deduplicated retained destinations.

   The first registered workflow is `openmhd-m1-archive-metadata-4ff43e5940c5-0000.1`, for `tools.m1_evidence.tests.test_archive_metadata.ArchiveMetadataTests.test_a_identity_flags_derived_from_closed_run_maps`. The last is `...-0172.1`, for `tools.m1_evidence.tests.test_runner_metadata.RunnerMetadataTests.test_wrong_shape_child_keeps_raw_and_invalid_record`. Every intervening index, selector/source hash, class/method and expected aliased runtime identity is connected, not just counted. Actual future per-case identities and interpreter links must still be checked in their own outputs.

8. **No blocking release defect; outstanding capabilities are purposes of the registered tests and later full-path gates.**

   No missing prior output/identity prerequisite was found that requires inventing another local probe or an unbounded OS guarantee before these metadata cases. Recommend executing these **exact 173** independent REANA methods, one workflow per method, with the declared 1CPU/2Gi/180-second direct-child-wait envelope, ready cases concurrent and no aggregate cap. Preserve original names and uncertain/failure receipts; do not quietly resubmit, skip, realign or promote a failed case.

   Pure imports do not establish collector `/bin/ps`, flock and pthread signal-mask **operations**, or runner timeout/detached/interrupted closure. Existing registered real-child cases already target these missing observations: collection indices **0059** (exited-leader/pipe descendant interruption), **0067** (outer timeout/separately grouped nested writer), **0071** (`test_real_host_timeout_is_finalized`), and runner **0166/0167** (descendant/detached-session writers). These remain actual-case/full-collector prerequisites. They are not new pretests or evidence of success; full collection cannot rely on them until their real outputs and capability/failure results are reviewed. Required failures block escalation under the existing policy.

   Actual adapter acquisition now shows successful finished-workflow access, ordinary one-page scans and complete exact artifact delivery/publication for this case. Diagnostic page counts **2** for observe and **4** for download are consistent with one-page repeated scans before/after, not proof of a multi-page workload. Failed/stopped forensic availability, nonterminal/ambiguous/changing pagination, framing failures, late buffered data/EOF, outer timeout, partial preservation and storage/interruption paths remain unexecuted controls. Registered runner cases **0086**, **0091** and **0141** cover selected forensic/cooperative-late-read/outer-timeout relationships; mocks can check contracts but cannot establish actual service failures. Actual whole-catalog acquisition/offline verification and independent output review are still required. There is no need to manufacture unavailable failure artifacts or make fresh network requests in this review.

## Checks performed and remaining gates

The independently retained capture covers **1260 original paths**: 11 source/preflight files, 37 observation files and 1212 staged files. Same-buffer JSON/base64/hash comparisons and initial/final observable-generation fences were used. Exact file/directory inventories reject links/specials; no changed generation or repeated-byte mismatch was found. The retained inspection source documents **1450 existing-data identity relations**, all satisfied, plus explicit directory/resource checks. These are source/data inspections, not executions of the target validators, unit tests or numerical probes. No nonzero inspection result was suppressed; the performed identity/directory/fence/document checks returned zero. Earlier reviews' historical findings and failure receipts were not rewritten.

The actual preflight just reviewed was executed previously by the coordinator on REANA. **This review itself executed no target code or workflow.** Original source, observation, staged artifacts, scientific files, prior reviews, Git index/commits, services and supervisor PID33546 were untouched. The only authored tracked-area outputs are this report and its source inventory, plus the ignored independent reading boundary.

The next required outputs are the actual 173 independent metadata results and their strict whole-catalog acquisition/offline consistency verification, followed by separate output review. Preserve capability failures, timeouts, skipped/xfail counts, incomplete logs and external infrastructure evidence rather than converting them into success. Collector/portable full-path execution still awaits complete real scientific inputs and successful prerequisite evidence. The actual fresh **214-case/seven-phase physical campaign**, immutable final collection/archive/copied portable verification and separate final numerical-output review remain open; M1 is unaccepted. No metadata-suite success, 3D, isolated gravity, ISM/SF/feedback or merger acceptance is granted. The genuinely deforming full-3D moving-Voronoi gas/DM/old-and-new-star merger remains the goal after those prerequisites.
