# Independent AI source review: runner-runtime proposal

2026-11-22. **Conditional source support: no blocking defect or mandatory external consumer change found in these exact J/T replacements.** They remove the identified broad-platform exposure and retain a truthful handled runtime-failure packet without relaxing successful-test or certificate predicates. This is source inspection, not integration approval, executed test success, M1 acceptance or scientific implementation authorization.

I authored the adjacent collector-runtime proposal, **not** this runner proposal. Its separate [independent review](M1_COLLECTION_RUNTIME_PROPOSAL_REVIEW.md) remains the disposition of that work; I do not self-approve it here. The [archive fixture review](M1_ARCHIVE_FIXTURE_PROPOSAL_REVIEW.md), [results-interface review](M1_METADATA_RESULTS_DESIGN_REVIEW.md) and [transport review](M1_METADATA_TRANSPORT_REVIEW.md) retain their separate scopes.

## Reviewed bytes

**J/T** mean the proposed replacements in `results/m1_metadata_runner_runtime_repair_20261122/proposal/`; **J0/T0** mean the unchanged working originals at baseline `b8496c98c85ad7339ec461deabc012f9f08c1d90`. Proposed files are intended for their canonical tool/test paths after coherent integration; the ignored proposal directory is not an installed package.

| File | Bytes | SHA256 |
| --- | ---: | --- |
| J `reana_metadata_job.py` | 58713 | `8d8a39844b631eb17d46f897bea71ae2464be1e400c75a54dd6c091a1fd2dbc3` |
| T `test_runner_metadata.py` | 106892 | `5d120dcfa32ea14aeebd48efdc5190d36933896e044f3e032f8756e69be3a70d` |
| J0 | 57129 | `5b1bf259f638135ccbee32eab3c3e81bb1090f35e97fc420eba69db9f57fbbee` |
| T0 | 97956 | `fd95d063f0aba01c91594c2059191e7b4b3bc4e9ec9e9929630788d8e44bb71c` |

I independently checked the author’s exact 48-file closure, plus its own manifest: 7740 bytes, SHA256 `0987feb21ea2578937d198767f4cc271e3cc03d2842a3225d71d0da5e0bc8bac`. No missing, extra or mismatched entry was found. Both full diffs regenerate exactly. I read all J1–1036 and T1–1731, including all 97 direct methods, complete causal/schema audits, relevant retained primary paths and strict consumer joins.

Task-entry context is `ca8fc77922bc19fe2ce7b8b04b70f1b802a3ef94`; the author’s retained `642ac1b1de549d0d0bfcf3e6c3ddb4cefe803eb6` context stays historical. All 186 original snapshot-listed working source members still match snapshot `4ff43e5940c51380282f6a1a0a0f0de30c45c0520dbee657e1c35c703bfbab6f`; the 3684823-byte original archive hashes to `7681adc54fa7c53cc0bb3ab6a45274a7c5fe9c20fcc8f307555117e8cbc4fa9c`. These checks do not put proposed bytes into that snapshot.

The new [81-file reading/check boundary](../results/m1_runner_runtime_proposal_review_20261122/sha256.json), excluding its own manifest, is 13959 bytes, SHA256 **`2100c05e99eeaa8a0c6915a0c0370d0c0dd74b23528bd0f774254eac9115a187`**. It retains complete subject bytes, current context, independent AST/diff/selector checks and manual receipts. This report pins that boundary; the companion inventory pins this report, avoiding a hash cycle.

## Numbered dispositions

### 1. Causal ordering — supported repair of a source exposure

**No new blocking finding.** J0:621 calls `platform.platform()`; J0:655 calls the runtime helper before initial structured-record publication and before the handled try at J0:674. Thus ordinary runtime-discovery exceptions can bypass that finalizer, and broad platform discovery can launch an external processor probe outside the intended supervised child. This is a demonstrated source exposure, **not a newly observed failing runner workflow**.

The separate actual collector0057 traceback is retained unchanged: workflow `openmhd-m1-archive-metadata-4ff43e5940c5-0057.1`, UUID `22ea181f-2f0c-483b-8225-67353b604ed6`. Its real CPython 3.11.6 child reports one test, one error, zero failures/skips and passed=false. Collector `runtime_info` calls broad platform discovery before its row is durable; the shared `Popen` callback then indexes an empty journal and raises `IndexError`. The actual raw child, envelope and parent agree; the 1232 raw bytes hash to `6aea19f654ea47188725ac0a3c3524bfc774267cc63c873328aea616aa0c4b1a`.

The later successful manifest retry belongs to the **same original workflow**, not a test rerun or repaired runner. Its 655 bytes hash to `defbee5106ec2ea5b89c9447a17c192b3f197219b9f2935b314f070ec699082f`, equal the initial partial; the seven retained artifact digests match. The original manifest transport remains failed. Neither that equality nor this proposal changes the observed one-test error.

**Required next evidence:** execute the strengthened launch-failure selector in the new coherent frozen source; do not rewrite/reclassify original0057.

### 2. Direct runtime observations and label equality — supported under the stated trusted POSIX contract

J619–645 obtains one actual `os.uname()` result, direct `sys` interpreter fields, actual `os.cpu_count()` and the existing optional cgroup texts. The new platform value is:

`posix-uname-v1:` + compact, sorted, ASCII JSON of `sys_platform/system/release/version/machine`.

Only the latter four uname attributes are accessed/serialized; no additional hostname, lazy processor, libc or broad-platform lookup occurs. The uname result itself includes nodename as documented, but the proposal does not export that attribute. This string is a deliberate representation change, not the old pretty string, an image attestation or a CPU reservation. Historical observations must stay unchanged.

The retained `platform.python_implementation()` display label remains in both J parent and J child. In the inspected installed **3.11.15** source, `python_implementation:1106–1120 -> _sys_version:1002–1104` uses the cache or a cold regex/sys-only parser, with globals at 974–1000; neither path calls an OS/platform/subprocess helper. The inspected 3.9 path corroborates this only for that source. No cache was primed or target helper evaluated in this review. These retained versions are **not the actual conda 3.11.6 source**; they do not prove arbitrary vendor/replaced modules equivalent.

J297–298 still records the child’s four keys `executable/python/optimized/implementation`; J340–343 requires exact equality with the parent subset and real integer optimize zero. Replacing the label by raw lower-case `sys.implementation.name` would unnecessarily break that join. This proposal correctly preserves the observed display spelling.

Required text must be nonempty and `visible_cpus` a positive real integer before the helper returns. A documented CPU-count `None` becomes a handled observation failure, not a fake count or a later launched-but-invalid result. This is logical system CPU count, distinct from affinity and declared allocation. Optional cgroup `OSError -> null` behavior is unchanged; no new timeout for these metadata operations is claimed.

**Resolution:** accept this narrow representation conditionally for coherent integration; no external parser of the historical pretty string was found in the related consumers. Actual selected-runtime behavior remains unexecuted.

### 3. Runtime-failure envelope — supported, with explicit initialization/storage limits

J657–792 publishes the initial structured records from an exact 14-key failure template, then sets `runtime_observation_failed` and calls the helper inside the existing handled try (J697–702). Assignment replaces the template only after a complete return. An ordinary uname/parser/required-CPU error therefore retains null unavailable observations; partially obtained values are not presented as a completed observation.

For such a handled early failure with writable storage, the existing finalizer closes exactly these eight artifacts:

`result.json, runtime.json, command.json, stdout.txt, stderr.txt, child_result.json, child_raw.bin, artifacts.sha256.json`.

The enclosing result is failed/false, class-only `problem`, null returncode/case/source/snapshot/payload/child claims and empty argv. Runtime retains actual direct sys/path values; implementation/platform/CPU/cgroups and unvalidated image/resources remain null. Command is `not_started`, no PID/PGID, no signal/reap and `writers_settled=true` because none was launched. Raw/log files remain empty; child envelope is absent, not a successful fabricated child. Final timestamps, runtime/command digests and seven-body-file manifest are computed by the unchanged finalizer. Both science/acceptance flags remain false.

The optimization guard runs before fallible runtime capture and retains `optimized_rejected` with the actual optimize integer. A caught `KeyboardInterrupt` retains `interrupted` and its class, not success. This ordering precedes input capture/extraction in both preflight and unittest modes; no source or child can already exist from this fresh run at the runtime-failure branch.

**Limit:** path resolution, output-directory creation, eight initial empty writes, clock acquisition and initial dumps still precede the main try. Failure there, another failure during finalization, storage loss/full/permissions, interpreter loss, SIGKILL or pod loss cannot be promised a completed receipt. Handled interruption also presumes finalization can run without another fatal interruption. External status/job logs are required for those losses. No broader lifecycle guarantee is inferred from the new stage.

### 4. Strict consumers and successful schemas — unchanged; no required companion edit

The exact 14 runtime keys remain `schema/python/executable/implementation/platform/optimized/image/visible_cpus/declared_resources/image_and_resources_are_declared_labels/job_path/child_raw_path/cpu.max/memory.max`. The schemas and success shapes remain unchanged; only a failed-job outcome and its unavailable values are added.

| Consumer | Exact source relation and disposition |
| --- | --- |
| J292–368 child/validation | Four-key interpreter equality, exact mode/source/leaf/runtime-ID/counts and false scope flags unchanged. |
| J813–916 `validate_case_outputs` | AST-identical. Positive CPU, nonempty runtime text, optimize0, exact image/resources, typed counts, actual held leader, argv/raw/envelope/hash links remain mandatory. |
| J919–922 / J932–1010 | AST-identical strict preflight wrapper and certificate validation, including finished before/after observations and complete transport/source/artifact joins. |
| P180–255 | Strict certificate validated before publication/release; original plan and exact source/job/certificate pins retained. |
| R66–172 / R304–355 | Full source/catalog/context checks; tries strict success then strictly executed failed-unittest validation. An early runtime failure satisfies neither. |
| R444–459 | Exact pinned preparer/job/adapter/result-collector bytes remain required; original host quartet cannot consume proposed source as if old. |
| T144–328 and existing negative controls | Complete synthetic runtimes remain explicitly synthetic opaque strings. Child mapping and runtime/command/source mutations stay unchanged. |

Here P is `prepare_metadata_reana.py` (16534 bytes, `ce54b54204df409758874b6dc4f48456c4d5d7b5bea6513fa99dc959e17b3e12`); R is `collect_metadata_reana_results.py` (31635 bytes, `ffd7f3510f2c0f28b2bfde36c89d361cf276007299cd4e948685f57f825025b3`). The adapter is 20866 bytes, `09a7f0cbaaa657eb6d84668dced7693c57c9784e78135adc86e72737ded79c4a`.

A failed runtime packet cannot satisfy success or the forensic failed-unittest option: among other contradictions it has null PID/CPU, a non-null problem, no held leader, `not_started` rather than `success/nonzero`, no executed child and no validated case/source link. R retains it as `invalid_or_job_failure_envelope`, failed or incomplete according to actual server/transport state, never as passed or a validated executed-test failure. Certificates ultimately invoke the same strict preflight predicate, so no release exemption exists.

**Resolution:** no directly necessary P/R/adapter/archive/portable edit is established by this representation change. This is interface inspection, not approval of those adjacent implementations.

### 5. Focused controls — causally specific, unexecuted

T462–531 strengthens the existing `test_launch_failure_has_finalized_attempt`. `source_fixture` prepares a small source-only fixture **before** patches; it neither stubs runtime capture nor primes a cache. The real helper then runs with broad platform/processor/libc/lazy-uname sentinels and a shared-`subprocess.Popen` callback. The sole permitted call must have the exact child argv, extracted-source cwd, private session, open exact logs and controlled environment, after a durable `pending_launch` command with no PID. It raises the intended `OSError`. Assertions require exactly one call, actual sys/uname/CPU/display-label fields, typed `start_failed/OSError`, null result problem, linked finalized packet and absent raw child.

Wrong-probe or callback `AssertionError` cannot turn green: an early one produces the wrong stage/problem; one at launch propagates to `launch_failed/supervision_failed` rather than the asserted `start_failed/OSError`. An extra call, forbidden probe, fake runtime or intended call before publication also fails explicit assertions. Shared standard-library patches are bounded by `with` and restored before after-checks. The second actual uname/CPU comparison assumes a stable ordinary kernel/CPU configuration during that method; no values are invented.

T533–593 adds one independent method, `test_runtime_observation_failure_keeps_unlaunched_failure_packet`, with three faults: uname `OSError`, implementation parser `ValueError`, CPU `None` rejected as `ValueError`. It calls the real run/finalizer, requires the selected observation exactly once, forbids supervision/Popen, and asserts the exact unavailable template, typed problem, all eight names/seven hashes, empty logs/raw, absent child, no source/extraction and strict preflight rejection. Exception argument text must not appear in any artifact. A wrong failure from the forbidding sentinels cannot satisfy both the expected type and selected-call assertions.

Existing actual preflight positive (T433–442), optimized rejection (T695–702), parent/child negatives and all other 95 old method ASTs remain. No skip/xfail, runtime stub, swallowed assertion or catch-to-success is introduced. These controls do not prove arbitrary cold vendor parser behavior or inspect every infrastructure loss; they are meaningful prospective controls of these exact branches. **No method or mock was executed here.**

### 6. Unchanged lifecycle and exact scope — supported source boundary

Independent whole-module AST comparison finds exactly J.`runtime_record` and J.`run` changed; all other **37 of 39** definitions and all imports/constants/top-level statements are identical. Source extraction, selector/code aliases, exact leaf loading, child/result/certificate predicates and the original held-leader PID/starttime/SID/PGID/`waitid(WNOWAIT)`/group/FD supervision remain identical. This preserves their previously reviewed Linux/cooperative limits; it is not a fresh runtime proof of them.

T retains all 96 original direct selector names, strengthens one and adds one: **97 runner leaves**. Test helpers/imports/top-level statements and 95 old method ASTs are identical. The current source composition is **29 collection + 48 archive + 97 runner = 174 prospective leaves**, independently derived from AST, not a hardcoded release requirement. Canonical future integration must derive its own final catalog. The new method’s three subcases belong to that one method/workflow.

Both diffs, AST/selector counts, JSON identities and source whitespace checks pass as **source checks** with no unresolved errors. No target/module/validator was imported or invoked. These are not executed unittest results.

### 7. Scoped adoption and remaining prerequisites

This exact proposal is suitable for a **later coherent canonical integration** after root closes and reviews the original acquisition boundary. No additional blocking correction is identified in J/T by this review. Preserve all original173 artifacts/certificates/source pins and observed failures; do not splice proposed bytes into old identities.

Root reports original173 terminal169finished/fourfailed and masked0010 coverage failure, with acquisition still active at assignment. I did not inspect or copy that active result packet as closed, contact a service or infer complete output review from server labels. Reported scientific214/seven-phase/238raw and independent reductions remain separate evidence under their active independent scientific review.

Remaining order:

1. Finish original whole-catalog acquisition, offline consistency and independent output review using unchanged original sources.
2. Integrate independently reviewed collector/archive/runner changes coherently, review final canonical interfaces, commit/freeze a new complete source snapshot and derive its exact selectors.
3. Perform actual immutable REANA source/import preflight, then every final method in a separate resource-declared workflow: 1 CPU/2 Gi and 180 seconds **direct-child wait**, not a whole-job deadline or measured reservation. Preserve required dependencies and no aggregate scheduling cap.
4. Acquire that complete actual catalog, verify offline and independently review outputs; import preflight/source inspection cannot establish test success or process/writer behavior.
5. Complete repaired scientific collection, archive/package and copied portable execution, the exact reviewer boundary and final joint output/archive review before any scoped M1 acceptance.

All genuinely deforming full-3D moving-Voronoi magnetized gas, isolated gravity, DM/live old/new stars, published ISM/SF/feedback and full-duration merger gates remain subsequent prerequisites. No M1, 3D or merger acceptance follows here.

## Primary identities and inspection limits

| Retained complete primary | Bytes / SHA256 | Inspected locator and limit |
| --- | --- | --- |
| Official [Python 3.11 os docs](https://docs.python.org/3.11/library/os.html) | 642880 / `5121e6404a2320178b883874a1b9a087ea70ec445f4ad338be09dd410a0f78b6` | HTML952–978,5397–5407: Unix fields, logical count/None/not affinity. |
| Installed CPython3.11.15 `platform.py` | 42273 / `4a3cc68ba7354f8d5cc28c55315a7d77b77dcdbbaa3a092572a636b5fb5b6938` | 974–1120; local installed source, not target3.11.6. |
| Installed Python3.9 `platform.py` | 40533 / `2d0f90d821fd998238e9b716b64fb2e73b8cad7375c4eff99d497305530cb7d9` | 1001–1119; version-limited corroboration. |
| Official [CPython v3.11.14 subprocess](https://github.com/python/cpython/blob/v3.11.14/Lib/subprocess.py) | 88725 / `baa9f9138d8d20df6284f67e7d2e790f847f65e2c5370de322d54cccd737f2d9` | 430–475,530–560: generic check_output/run/Popen relation, not actual3.11.6 source identity. |

No new retrieval occurred. The actual3.11.6 chain is established by its retained traceback, not by equating those source versions.

The author records an rg IO error for missing `/opt/homebrew/Cellar/python@3.11`; subsequent installed-source reads resolved the lookup without supplying actual3.11.6 source. My combined displays of J, historical reviews and the large input receipt were truncated; bounded J/review rereads and full JSON parsing/independent row checks resolved the reading gaps. Complete bytes are retained; I do not claim every identity-array row was visually printed. These inspection limitations are recorded in `manual_read_receipt.json`; final source checks have no unresolved nonzero status. They are neither physical failures nor passing executions.

No source/tool/test, historical review, original evidence or live acquisition file was edited. No runtime/platform/process probe, test/mock/entrypoint/validator, network/private configuration, build/reducer/evolution, workflow/service action, commit or delegation occurred.
