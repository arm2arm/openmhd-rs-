# Independent AI review: case0057 collector-runtime proposal

2026-11-22. **Conditional source support; no new blocking source defect found in this exact proposal within the existing cooperative POSIX contract.** The change removes the process-launching runtime-discovery path that caused the acquired case0057 error. Its strengthened existing test distinguishes that path from the intended guardian-launch failure and retains an honest kernel-identity failure. This is an independent source/manual review, not a passing test, canonical-source integration, baseline replacement or M1 acceptance.

## Exact subject and review boundary

The subject is the source-only proposal in `results/m1_metadata_collection_runtime_repair_20261122/`. **C** and **T** below denote its proposed collector and collection tests; **C0/T0** denote the originals at `b8496c98c85ad7339ec461deabc012f9f08c1d90`. Proposed files are intended for their canonical tool paths; running from the ignored proposal directory is outside this review.

| Identity | Bytes | SHA256 |
| --- | ---: | --- |
| C `proposal/collect_fresh_physics_reference_inputs.py` | 52820 | `a781e4ea910038a4c1be045c2e88a06e460d6492dd7d47ac1cfc24f76b44d355` |
| T `proposal/test_collection_metadata.py` | 45549 | `4059589b6c2077f99387af729a20f944b1d42da0140f19397d084a15507b132a` |
| Author `CAUSAL_DIAGNOSIS.md` | 10490 | `133e8d2b6a1d8159822c946742cebd6de36c4918d6be9202647d348670892357` |
| Author ten-file closure `sha256.json` | 1634 | `9b9802648bd7444f2f4d4e2fbec11efcdb49e31a6938c3f5b322fce8c87dddfa` |
| C0 | 52143 | `10b604537daeec56510ec1b884569aee73fe559a00a351ce907123cb02740f0d` |
| T0 | 40249 | `ed7d3a7ad70ae116a613c5ecf76fe655730d584f103d59d5fc97e0369bf11bd5` |
| Unchanged preparer **P** | 23608 | `5fb1a4214aa9309bc8e68d06cbe2396927105213809710c108dcadd5c2889eac` |

I read all C1–1036 and T1–762, both complete diffs, the complete diagnosis and schema/mock audit, and the source/selector/nonzero receipts. Independently regenerated diffs match exactly. C's only changed definition is `runtime_info`; its only other AST change removes `import platform`. T's only changed method is `test_command_start_failure_has_durable_attempt_and_logs`; its other 28 method ASTs, all imports/helpers and all 29 selectors are unchanged. All 186 original snapshot source entries still match working bytes. No author source or working tool was changed here.

For unchanged consumer locators, **V** is `verify_final_review_evidence.py` at portable `46378c2c227b721dcdc8d97a3fdeb28a655c7b35`, SHA256 `258e644694cee02b1398e0a09c13926497ef3dd762b3940a9c6bf0208a7dcdfc`; **A** is its packager, SHA256 `7df47d18533a8ed686cca5a8ac2634987354f426dc0f0d41bb72ea34110116fe`. **J** is the metadata job at `29a38f9`, SHA256 `5b1bf259f638135ccbee32eab3c3e81bb1090f35e97fc420eba69db9f57fbbee`. This review reads their relevant interface predicates; it does not independently rereview my own portable algorithms. The [independent portable review](M1_PORTABLE_GATE_REVIEW.md) and [collector signal review](M1_COLLECTION_SIGNAL_REVIEW.md) remain context with their original limits.

The new [104-file closed reading boundary](../results/m1_collection_runtime_proposal_review_20261122/sha256.json) has SHA256 **`7efaacbdda3512b11c5ffefea17d914574e40b0df8f725d3fdf3f0b59a097ab3`**, 20395 bytes. It includes 91 captured input identities, all subject files, both original failed-case closures, exact original Git/tool bytes, consulted retained primary bytes, independent static scripts/results, manual read/selector receipts and the unsuccessful inspection attempts. Only its own top-level manifest is excluded. This report pins that boundary; the companion inventory pins this report, avoiding circular hashes.

## Numbered findings and dispositions

### 1. Observed causal chain — repaired by source inspection, not yet rerun

**Severity/disposition: original observed unittest error; conditional source support for the repair.** The actual workflow is `openmhd-m1-archive-metadata-4ff43e5940c5-0057.1`, UUID `22ea181f-2f0c-483b-8225-67353b604ed6`, selecting `tools.m1_evidence.tests.test_collection_metadata.CollectionMetadataTests.test_command_start_failure_has_durable_attempt_and_logs`. Its original child reports actual CPython 3.11.6, optimize zero, exactly one test, one error, zero failures/skips and `passed=false`. This is a real metadata-test error, not a scientific evolution failure or an infrastructure-only success.

The retained `artifacts/stderr.txt` shows T0:263 calling `journal.run`, C0:705 constructing the row through `runtime_info`, and C0:68 calling `platform.platform()`. Actual runtime `platform.py:1217` iterates uname, `804/799/744/767` resolves processor information, and `subprocess.py:466/548` reaches the shared `Popen` mock. Its T0:256 callback indexes an empty command journal and raises `IndexError`. The attempted launch is runtime discovery before durable row insertion, not the intended guardian launch. Parent, envelope and decoded original child agree; the 1232 original child bytes hash to `6aea19f654ea47188725ac0a3c3524bfc774267cc63c873328aea616aa0c4b1a`.

C62–79 now obtains actual `os.uname()` fields and `sys` attributes, then formats JSON. The helper's complete call set is `os.uname`, `dict`, `os.environ.get` and `json.dumps`. It contains no `platform` helper, subprocess, shell command, processor/libc lookup, cache priming or invented fallback. Under the declared trusted CPython/POSIX API contract, this removes the observed route before row/ownership insertion. It does not claim that arbitrary replaced/vendor APIs cannot execute code.

The [Python 3.11 os.uname documentation](https://docs.python.org/3.11/library/os.html#os.uname), retained complete bytes SHA256 `5121e6404a2320178b883874a1b9a087ea70ec445f4ad338be09dd410a0f78b6`, lines 952–975, documents the Unix identity attributes. The retained [CPython v3.11.14 subprocess source](https://github.com/python/cpython/blob/v3.11.14/Lib/subprocess.py), SHA256 `baa9f9138d8d20df6284f67e7d2e790f847f65e2c5370de322d54cccd737f2d9`, lines 430–475/530–560 supports the `check_output` → `run` → `Popen` relation. That tag is an inspected source identity, **not** the actual 3.11.6 runtime; the actual traceback establishes the observed path. No new source download or runtime probe occurred.

### 2. Seven-key runtime schema and unchanged consumers — compatible by predicates

**Severity/disposition: no blocking interface defect found; actual integrated validation remains pending.** C62–79 preserves the seven keys and obtains actual values:

| Key | Proposed source/type and intentional change |
| --- | --- |
| `executable` | `sys.executable`, string, unchanged |
| `version` | `sys.version`, string, unchanged |
| `implementation` | `sys.implementation.name`, string; raw identifier such as `cpython` replaces the old display value `CPython` |
| `optimization` | `sys.flags.optimize`, integer, unchanged |
| `assertions_enabled` | `__debug__`, Boolean, unchanged |
| `pythonoptimize` | environment string or null, unchanged |
| `platform` | nonempty `posix-uname-v1:` plus sorted compact ASCII JSON of `sys_platform`, `system`, `release`, `version`, `machine` |

The platform representation explicitly omits the uname `nodename` attribute and processor/libc probes. It is an OS/runtime observation, not image, resource or server attestation. Kernel version text is retained as returned; this review makes no universal confidentiality promise about incidental text inside a system-provided version string. Historical platform strings remain historical and must not be rewritten into the new representation.

All existing producer paths use this helper: C176–189 capture runtime, C713–719 command interpreter, C903–911 physics provenance, and P21/P355 outer summary. P is unchanged. V224–227 requires zero optimization, true assertions and nonempty strings for executable/version/implementation/platform; it does not parse platform or require uppercase `CPython`. V255, V559, V1352 and V1421 apply that same predicate to journals, outer capture/summary, physics provenance and nested capture. V's separate exact child-environment requirements remain. The producer preserves the nullable `pythonoptimize` field; I do not claim V checks more about that field than it does.

Unchanged executable identity continues to bind real argv and guardian launch at V311/V414. Guardian bootstrap/collector-source byte links are unchanged in form; future integration must capture the **new** collector bytes, including its isolated `-I -S -B -c` launcher. V1350–1351 still binds the retained physics `collector.py` to captured tool source. A's lifecycle/export checks and copied verifier do not impose a separate implementation/platform literal. No schema exemption or verifier/packager edit is needed for this proposal.

J's wrapper/child interpreter object is a **different four-key object** (`executable/python/optimized/implementation`, J340–343,807,856). Its actual `CPython` display value is compared to its own wrapper runtime, not C's seven-key object. Thus differing casing between these objects does not justify fabricated runtime values or a relaxed check.

### 3. Intended start-failure test branch and assertion visibility — supported, unexecuted

**Severity/disposition: strengthened existing selector is causally specific; no masking defect found.** T254–271 first calls the real helper while `platform.platform` and the shared `collector.subprocess.Popen` are forbidden with assertion sentinels. It verifies all seven actual fields and the tagged uname contents, without stubbing runtime data or priming a cache. A second `os.uname()` comparison assumes stable kernel identity within the method, appropriate to the intended ordinary POSIX runtime; no sampled kernel values are invented here.

T273–323 then creates the real journal with only secret discovery stubbed to an empty list. At the intended guardian `Popen`, its callback checks that the durable journal already contains exactly one running attempt; original argv/runtime, empty precreated logs and hashes are present. It checks the actual guardian bootstrap/pinned canonical source path, registered node with no published guardian PID, private-session request, optimize-zero and no-bytecode environment. It deliberately raises `FileNotFoundError` at **guardian spawn**, not the guardian's later primary-command spawn or PID-publication branch. C400–438 then records `state=start_failure`, stopped writers and no PID; C747–788 finalizes typed logs/receipt before C791–792 raises `CommandFailed`.

The final assertions require exact `(outcome,error_type)=('start_failure','FileNotFoundError')`, null returncode, completed time, nonnegative duration, closed logs, no external-evidence requirement, matching log hash/length and no success manifest. They also reject the injected exception argument from stderr. A callback assertion is not hidden merely because `CommandJournal` catches `BaseException`: it would record `error_type=AssertionError`, failing the later exact type check. The positive precheck and exactly-one-launch assertion further distinguish an early metadata subprocess. This addresses the actual masked branch; no additional selector or redundant implementation-copy test is required by this source finding.

### 4. Unavailable uname and failure-envelope semantics — fail closed

**Severity/disposition: supported source path; no successful runtime fallback.** `runtime_info` does not catch `os.uname` errors. T327–347 injects `OSError` after journal initialization, forbids Popen, and enters the real failure envelope with a named stage. C709–712 creates empty logs; C716 raises before the row is appended/durably published at C720–721 and before `OwnedCommand` is constructed. The expected result is the original exception, an empty journal, zero launches, empty log files, typed failed stage/status, false acceptance flags and no successful manifest. Exception arguments must not enter the status.

No child was attempted in this subcontrol, so `external_evidence_required=false` is consistent; it is not an invented completed command attempt. A missing API (`AttributeError`) also propagates by the same source structure, though this written control exercises `OSError`, not every Unix failure. Earlier capture/provenance runtime calls are likewise within the unchanged C/P failure envelopes (C870 onward; P214 onward), rather than an unhandled successful-publication path. Storage/interpreter failure can still prevent even a failed status from being written; the existing unfinished/external recovery contract is not expanded.

The successful status stays exactly `complete/false/false`; V424–435 rejects failed or unfinished collections before successful export. This helper-level failed envelope is not a synthetic completed physical packet and supplies no physical campaign evidence.

### 5. Lifecycle, shared mocks and scientific scope — unchanged, conditional limits retained

**Severity/disposition: no new lifecycle or gate revision required by this diff.** Independent full-module AST restoration proves that ownership ancestry, registry lock, cancellation fences, one-shot signal authority, held guardian/bootstrap, cumulative timeout output, redaction, cleanup and source guards are untouched. C341–361's explicit `/bin/ps` child is a later owned-group observation; C423 and C588 remain intended guardian/primary starts. Removing high-level runtime discovery does not remove or certify these declared facilities. Private/session/registry/source bytes and failure classifications remain subject to the prior [signal review](M1_COLLECTION_SIGNAL_REVIEW.md).

I read every collection method, not only 0057. T627–656's shared-Popen failure-fence control enters `OwnedCommand.start` directly and has no runtime-helper call. Owner-mocked timeout/redaction/nonzero/uncertain/interrupted controls still construct real journal runtime before owner handling; the proposed production change removes their former hidden-probe possibility without rewriting their assertions. Shared standard-library `os`/`subprocess` attributes patched by the changed method are restored by bounded `with` contexts. Other controls retain their existing synthetic publication/signal boundaries or actual future harmless-child expectations. None was run here.

P's 13 successful command labels, capture-v1/ownership-v1 schemas, complete-status flags, 214/99/238 identities and frozen reducers/physical thresholds are unchanged. The main AST is unchanged. Hash comparison of all 186 baseline source members found no working-source modification, including the live host acquisition quartet. It is not permission to integrate while the original collection is live, nor a revalidation of numerical equations.

**Separate unresolved coupling:** J619–631 still calls `platform.platform()` in `runtime_record`, invoked at J655 before initial output record/try. This is a source-level analogous exposure, not a newly observed failing runner case and not fixed by this collector proposal. Root has assigned its separate proposal. A future coherent source freeze must include independently reviewed runner treatment; this review neither duplicates that fix nor approves it unseen. Passing server status of another method cannot prove no hidden runtime probe occurred.

### 6. Retained evidence and inspection limits — explicit nonblocking provenance note

Both actual case0057 packets remain separate and unchanged. Initial `case_0057_attempt01/sha256.json` closes 32 files, SHA256 `223ca38164db0ce83d51476a396ad2688eebfa87d964177776dd3e8973af4c2b`; retry `case_0057_manifest_retry01/sha256.json` closes 11, SHA256 `dcfae87e8ce24c84774bafa5f67f93c1cde5f75e291a05ea09618496d08904b8`. All entries and exact recursive closures were checked. The retry's seven-file artifact manifest is 655 bytes, SHA256 `defbee5106ec2ea5b89c9447a17c192b3f197219b9f2935b314f070ec699082f`, equal to the initial retained partial; all seven actual artifact hashes match it. This equality does not turn the initial failed transport into success.

The initial journal retains ten attempts: nine successful and one nonzero manifest transport. Its stderr diagnostic is `network_error`, with a 655-byte partial and **empty** `workflow_ids`; that failed attempt alone does not certify the UUID. The retry retains three successful attempts. All twelve successful diagnostics pin the requested UUID, all thirteen log hashes and successful output digests match, and both packets' before/after observations remain failed version 1. No observation is a preflight release certificate. Original child/envelope/parent equality and nominal held-leader/writer closure support attribution of the unittest error; they do not exercise proposed behavior or arbitrary cleanup failures.

The author retained two corrected inspection failures: an `rg` query for nonexistent `test_metadata_runner.py` (exit 2), and a static helper-call allow-list omitting unchanged `os.environ.get` (exit 1). Their corrected source checks require no altered target bytes. My own retained static failures are `nonzero_inspection01/02.json` (incorrect assumptions that the author's handoff-context hash would match current/Git bytes), and `nonzero_inspection03.json` (incorrectly expecting a failed transport's diagnostic on stdout). The third was resolved by inspecting stderr and preserving its empty UUID list; it did not justify filling in an absent certificate. These are inspection limitations, not executed test failures. A batched source display also exceeded output budget; bounded follow-up reads supplied the relevant complete ranges.

**Informational provenance limit:** the author records a 139961-byte working `docs/CODEX_HANDOFF.md`, SHA256 `4fc21f8d48786c9babef36b5c3555e44233c7708cc24ce2fa036456e8b63617a`. Those bytes were not retained in its proposal and match neither the independently captured current handoff nor its cited Git context `8d521b7572498b19466c327f73a2411216968d70`. The latter is 139135 bytes, SHA256 `57244adf270f0d16b23fa8e2379a1f56a7062626dc3a8aaa8d677b1025aed15f`; our current reading is separately pinned. I preserve the unmatched hash as an **unreconstructed historical working-copy observation**, not a reproducible verified input. This does not disconnect the exact proposal, baseline tool bytes, actual failure closures or consulted primary bytes. No source revision is requested on that basis. Final generation checks found all 91 independently retained working/Git readings consistent with their captures.

### 7. Recommendation and remaining prerequisites

Proceed conditionally to a **later coherent canonical integration review**, after original baseline acquisition is closed and reviewed. No additional blocking collector correction is established by this source inspection. The smallest direct causal regression is already the strengthened existing 0057 selector, including its positive no-probe capture and two distinct failure paths; retain all 29 methods and the full source-derived catalog. Do not replace original failed outputs, resubmit under their old identity, skip masked negative tests or infer passing suite coverage from 169 server-finished workflows.

The dispatch reports all 173 original workflows terminal (169 finished/four failed) and physical 214/seven-phase plus independent wave/physics reductions passing with 238 fresh raw identities. Those are coordinator-provided current status, not new server requests or a complete numerical-output review performed here. The live original result-acquisition packet was not inspected as closed or modified. The archive-fixture proposal remains separately reviewed and unintegrated; this review does not self-approve it.

Required sequence remains:

1. Close original whole-catalog acquisition, offline verification and independent output review using unchanged original pinned sources; retain all failures and transport limitations.
2. Independently review and integrate coherent archive-fixture, collector and separately assigned runner repairs; freeze new exact source bytes/selector catalog and actual immutable REANA source/import preflight.
3. Execute every final source-derived method in its own declared-resource REANA workflow (1 CPU/2 Gi/180 seconds, no aggregate scheduling cap), then acquire the exact catalog, verify offline and independently review outputs. Imports alone cannot establish `/bin/ps`, flock, masks, held-process/writer closure, timeout, detached-writer or transport controls; their relevant actual cases/complete collector still matter.
4. Run and review immutable final scientific collection, packaging and copied portable verification against actual fresh evidence, followed by the separate final numerical-output review and scoped M1 acceptance decision. Fresh passing counters alone do not close these provenance/acceptance gates.

Only source/AST/JSON/hash/link/whitespace and manual existing-data inspection occurred. No target import/call/guard/help, test/mock execution, runtime/process probe, network/private-configuration access, numerical reducer/build/evolution, workflow/service action, commit or delegation occurred. This review grants no M1, 3D, gravity, ISM or merger acceptance. The full genuinely deforming magnetized 3D galaxy merger remains the subsequent goal after its prerequisites.
