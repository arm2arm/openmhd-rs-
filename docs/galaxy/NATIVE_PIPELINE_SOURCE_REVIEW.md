# Independent AI source review: native one-leaf execution pipeline

2026-11-22. Reviewed subject: **`8e3fd8ec4f18745c763623dbc12e168ef3b91b7a`**.
The compile/list-only prerequisite is **source-eligible now, independently of
the downstream findings below**. The new native caller/transfer/catalog/output
logic has conditional source support within its declared cooperative Linux
scope. Two written metadata controls need the narrow causal repairs in findings
3–4 before their advertised coverage can be relied on. No production-path
change is required by those two findings. This is neither an executed preflight
nor a passing test, component acceptance or scientific-output review.

I did not author this pipeline. I authored the separate identity crate and
previously reviewed static geometry/direct gravity; I do not independently
approve my identity implementation here. The prior independent root restoration/
submission review is context, not this author's approval of this pipeline.
M1 acceptance at `309ae41` remains its named periodic, single-process fixed/rigid
2.5D decision. Gravity, deforming 3D MHD, gas/DM/old/new stars, published ISM/SF/
feedback and the full domain-controlled magnetized merger remain separately gated.

All locators refer to captured Git blobs, not concurrently changing working
files. The required project documents match the prior complete G1-review reading
byte for byte; their current acceptance/mission and execution-policy sections
were reread. No private configuration was inspected.

## Numbered findings and disposition

### 1. Supported — the compile/list-only workflow need not wait for unrelated downstream fixes

The early recommendation was delivered to the coordinator as Orca message
`msg_46d92bbee88b`, before completing the downstream review. It is a source
recommendation, not a submission or instruction to execute anything.

`scripts/prepare_reana.py:14–141` selects and hashes the original source, exports
regular source members, retains the actual development revision separately from
the compact export commit, and rechecks captured bytes. The wrapper
`scripts/prepare_galaxy_reana.py:25–88` derives the actual submission specification
without changing those source/archive pins: two serial steps, pinned image,
four requested/limited CPUs, **8Gi memory limit**, and fixed study/jobs arguments.
It does not claim an 8Gi request/reservation. The wrapper, freezer and
`reana/remote.py` are byte-identical to the `01c0534` context independently
reviewed in `IDENTITY_RESTORE_AND_SUBMISSION_REVIEW.md`; no identity delta is
re-reviewed here.

`remote.py:106–171` checks uploaded parts, reconstructed archives, source revision
and source hashes, and installs checksum-pinned Rust 1.85.1. Its new branch at
`174–186`, reached by `run` at `280–312`, requests exactly:

1. format check;
2. workspace/all-target/all-feature strict Clippy with the locked graph;
3. locked release workspace/all-feature build;
4. `galaxy_preflight.py` with four build jobs.

The exporter (`galaxy_preflight.py:86–137,140–250`) compiles both profiles with
`cargo test --no-run`, parses unique successful Cargo test artifacts, and runs
only discovery/ignored-discovery commands. It rejects source/path/link/target
collisions and ignored leaves, copies and hashes the actual executables, fences
source/snapshot bytes, and retains the original gzip archive plus ordered
one-MiB parts and exact regular-member map. Its finite transfer bounds are not a
claim that an oversized valid target can be silently omitted. No test method
command is selected by this workflow. Cargo compilation/build scripts and
libtest discovery are still executable work, authorized only on REANA.

The retained official [Cargo message documentation](https://doc.rust-lang.org/cargo/reference/external-tools.html#json-messages) supports the used test-profile,
executable and build-finished fields. Exact Rust 1.85.1 `console.rs:172–218` and
`terse.rs:180–196` support discovery lines without a terse footer. These are API
source checks, not observed compiler compatibility.

**Disposition:** the stated compile/list-only slice is eligible for a coherent
immutable source freeze and actual prerequisite workflow independently of
findings 3–4. Actual fmt/Clippy/build/discovery, artifact/download capability,
resource visibility and output inspection are unexecuted. Later source changes
must retain their own exact source/preflight joins; this recommendation does not
permit substituting a binary built from different numerical source.

### 2. Supported — durable launch uncertainty fixes the prior caller defect

`galaxy_test_case.py:230–252,324–359` persists runtime/result metadata and a
pending launch intent before entering the unchanged supervisor. The intent binds
actual argv/cwd and snapshot/case/payload/runtime/binary/runner/supervisor hashes.
An escaping `BaseException` retains `unknown_closure`, null command finish and
unknown cleanup; `run` reloads that durable object and requires external terminal
evidence. It cannot replace a potentially launched process with the original
`not_launched` placeholder. Failure before intent remains explicitly unlaunched.
The caller never guesses a PID or dispatches an unowned signal.

The unchanged supervisor is pinned by the original source snapshot and is
byte-identical to accepted M1 context: SHA256
`8d8a39844b631eb17d46f897bea71ae2464be1e400c75a54dd6c091a1fd2dbc3`.
Its `supervise:486–581` requires Linux, a held unreaped private leader, process
identity/PGID/SID/starttime authority and writable-log-FD observation. Actual
returned success is accepted only with reaping and settled writers. That prior
implementation/evidence supports reuse, not a pass of this new caller.

**Limits:** the native output directory and two empty-log creations precede the
handled `try` (`271–283`); storage/initialization loss can leave an incomplete
packet. Final writes are fallible (`360–368`), not a transactional recovery
system. Interrupted/unknown-writer hashes are observations of retained bytes,
not closed logs. Interpreter/pod/storage loss requires external evidence, and
arbitrary daemon/nonwriter/UID escapes remain unsupported. The direct-child
wait timeout does not bound parsing, extraction or finalization. The exporter
similarly labels interrupted commands as requiring external evidence; its
subprocess timeout does not certify group cleanup. These limits do not produce
a passing native packet in the strict output path.

### 3. Medium — callback assertions can be swallowed by the failure path being tested

`GalaxyNativeWitnessMetadataTests.test_escaping_supervision_retains_intent_and_unknown_failure_packet`
at `scripts/test_galaxy_preflight.py:198–251` puts assertions about pending status,
unknown writers, argv/cwd, links and runtime publication **inside** `escape`
(`222–231`). `launch_native` catches any `BaseException` (`243–248`), and `run`
also catches it (`348–359`). Therefore an `AssertionError` at, for example, the
cwd assertion follows the same failed/unknown-closure path as the deliberately
raised `RuntimeError`. The existing outside assertions check the failed/unknown
packet but never require that expected exception type or that the callback
reached its intended terminal raise. They can all remain true after this
particular assertion fails. This is a manual call-flow counterexample; no
mutation or test was executed.

**Smallest repair:** keep the selector. Capture the callback's observed intent
and its reached marker, then assert those facts outside `native.run`; require
`result['error_type'] == 'RuntimeError'` and the intentional sentinel rather than
accepting `AssertionError` or an unrelated failure as coverage. Exact link values
can be checked against the fixture bytes outside the caught region. Retain the
failed command/child/acceptance assertions. Do not change the production broad
failure handler to make a test pass.

**Smallest REANA control:** the strengthened existing method in its own declared
metadata workflow. It must fail if a callback expectation raises instead of the
sentinel; no process or successful scientific packet is needed. This is a
written-control coverage blocker, not a demonstrated native runtime failure and
not a reason to hold finding 1's compile/list workflow.

### 4. Medium — the unittest-envelope negative never reaches the schema boundary

`GalaxyCaseMetadataTests.test_native_validator_rejects_unittest_and_incomplete_envelopes`
(`scripts/test_galaxy_cases.py:163–167`) supplies only `{}` and a one-file mapping.
Both fail `pipeline.validate_native:326`'s eight-artifact check. Neither reaches
artifact closure, case loading or the native-result discriminator at `333–339`.
The production discriminator is present by source inspection, but this method
does not exercise the advertised rejection of an old Python-unittest envelope.

**Smallest repair:** retain the incomplete-input checks and this selector. Add an
explicitly inert, eight-filename/hash-consistent negative fixture, with just the
case/payload fields required to reach that discriminator, and a distinctly old
unittest result schema. Assert the native-result error rather than `Eight` or an
unrelated `KeyError`. An otherwise identical native-schema/nonpassing control
can demonstrate that the inputs reach the same stage. No passing physical,
preflight or actual native execution need be fabricated. A small isolated
schema-check helper is also possible, provided the production validator uses it
and the exact unchanged artifact closure is checked separately.

Run this strengthened method independently on REANA after source/import
prerequisites. This is a focused coverage correction; it does not establish
that an old unittest packet currently passes the production validator.

### 5. Supported conditionally — original bytes, bounded transfer and UUID joins are concrete

`common.py:34–143` rejects noncanonical/escaping/linked evidence inputs, bounds
regular files, checks before/after generations, includes nested manifests,
reassembles the original source archives and requires the exact regular source
member/hash set. Source bytes are decoded into a map rather than extracted as
arbitrary filesystem paths. `extract_export:254–265` checks exact archive member
count/set, regular bounded members and hashes before exclusive publication;
links, duplicates and traversal do not become accepted export members.

`readonly_adapter.py:25–61` extends only allowed preflight/log/part paths and
UUID-bearing observation/download selection. It reuses the unchanged base
adapter (SHA256 in the companion inventory), whose normal CA/hostname TLS,
no-proxy/no-redirect GET, consistent pagination, 16-MiB body bounds, no-follow
exclusive partials and static credential-safe diagnostics remain unchanged.
Each download resolves the original versioned workflow/UUID and checks the row
again after the body. Private settings are reached only during an actual future
adapter call; none was made here.

`common.attempt:145–202` publishes a pending receipt before launch, retains typed
failure/partial diagnostics and checks actual successful UUID/action/path/body
linkage. `transport_body:205–238` and `transport_closure:241–251` bind source,
absolute credential-free argv, timestamps, retained stdout/stderr/body hashes
and exact receipt/download closure. Failed partials cannot be hidden inside a
successful selected closure. The helper launches no submit/recovery action.
The 300-second direct-call limit is distinct from the base adapter's cooperative
120-second checkpoints/15-second idle bound; no universal transfer or descendant
containment is claimed.

The original archive is checked from its actual parts, not regenerated to
match a manifest. `acquire_preflight/verify_preflight` (`pipeline.py:45–201`)
require actual finished observe/download/observe UUID identity, original source/
submission bytes, parent raw logs and original parent manifest links, exact
export/member inventory, helper-source fences and a complete compile-only
preflight. The local architecture bypass is explicit and used only for client
metadata checks; the actual native job keeps the default architecture match and
the supervisor enforces Linux before child launch.

**Remaining evidence:** real server path/part/log availability and bounded body
sizes, actual Linux architecture/Python/image observations and complete artifact
closure. YAML declarations do not prove reservations or network capability.
No accepted M1 transport result certifies this new subclass/composition.

### 6. Supported conditionally — selection is tied to the whole reviewed catalog and actual target counts

`common.catalog:268–329` requires explicit independent-review/source pins,
complete component Rust/manifest pins, exact target/source/selectors and resource
contracts, matching debug and release discovery, and global selected-leaf
uniqueness. It requires 26 identity, 28 geometry including the four exact library
selectors, and 39 gravity including nine library leaves **per profile**. The
moving-mesh library is filtered only for eligibility; its full discovered
selector count remains in the binary record and the native witness. Missing
new identity/gravity standalone targets cannot be silently dropped. These are
checks against actual future discovery and a manually approved exact contract,
not proof of a review document's semantic recommendation merely because it hashes.

`pipeline.prepare/validate_plan:236–322` retain the entire closed original parent
acquisition, coverage contract, original binary bytes, exact chunked inputs and
source-pinned case/supervisor; both profiles and all selected leaves are bound
to ordered immutable plans and JSON-as-YAML one-job specifications. Each native
job has one requested/limited CPU, one test/Rayon/FFI thread and the exact
component memory/timeout declaration (identity 2Gi/180s; geometry 2Gi/300s;
gravity 1Gi/180s). No aggregate running-case cap is introduced.

The actual unchanged `scripts/reana_cases.py:205–239` submit path consumes the
used directory/payload/workflow hashes and original input pins; it does not
interpret the new `specification` string as a scientific case. It writes pending
identities before its run calls, retains uncertain requests and refuses implicit
resubmission. Its eight upload clients limit local transport concurrency, not
remote ready-case execution. The old scientific check/watch branches are not
native result validators and must not be used for this catalog. Original submit
transport remains its historical SDK/CLI policy, not the new GET policy.

No actual reviewed coverage JSON, executable discovery or 186-case plan was
invented here. The 186 total is conditional arithmetic from the frozen source
policy, not a measured completed catalog. Future added/changed source names or
resources require the exact corresponding contract and source-derived count.
Runtime filesystem/dynamic dependencies still require the component portability
review; familiar crate names alone are insufficient.

### 7. Supported conditionally — native output is independently checked beyond summary flags

`galaxy_test_case.validate_inputs:98–217` binds payload/case/source/runner/
supervisor, exact parent prerequisite commands, runtime/artifact/log hashes,
original catalog and selected executable/selector. `run:271–368` reassembles the
actual pinned executable, records actual runtime and literal thread declarations,
launches one `--exact` leaf, requires settled supervised return0 and fences its
inputs afterward. Host preparation does not pretend to be Linux: it passes
`check_architecture=False`; the actual job does not.

`pipeline.validate_native:325–389` requires exactly eight bodies and their exact
artifact hash map, the native result schema, original case/payload/snapshot/
preflight/binary links, actual parent-compatible Python/machine, runtime/thread
observations, exact command/cwd/timeout, held-leader PID/PGID/SID/starttime and
closed-writer cleanup, command source/runtime/binary links and raw/stdout equality.
It reruns the native witness parser against the actual downloaded stdout. The
witness (`galaxy_test_case.py:255–268`) requires one named nonignored success and
one final one-pass/zero-failure/zero-ignored summary with the full target's exact
filtered count. Aggregate, wrong-name, ignored and truncated witnesses fail.
Rust 1.85.1 `pretty.rs:209–315`/`cli.rs:49–108,396–425` support the selected serial
pretty output/options; successful captured diagnostics precede the summary.
This is a source compatibility argument for ordinary ASCII libtest targets,
not a universal custom-harness/output theorem or actual witness.

`collect/verify_results:392–484` preserve the original whole-catalog submission
map, every original prepared input and original uncertainty/history bytes; they
perform observe/eight-download/observe per workflow with stable unique UUIDs.
Failed/stopped/pending/partial rows remain forensic/nonpassing. A failed row
can leave a complete acquisition summary with false whole-catalog verdict, but
the strict verifier then rejects it. It validates every row/body/transport/witness
again, requires all planned leaves exactly once and recomputes counts; summary
booleans alone cannot release the catalog. Source/input generation fences are
checked after collection. New acquisition attempts require fresh directories;
no recovery command here upgrades an uncertain original submission.

Acquisition exceptions retain typed failed metadata and partial bytes when the
destination is writable. Inaccessible storage or uncatchable loss cannot promise
a finalized receipt. Preparation itself is not an atomic transaction: interrupted
partial plans must fail `validate_plan`, not be relabelled complete. Actual
whole-catalog transfer, offline verification and independent output review
remain unperformed for these new sources.

### 8. Written coverage and implementation disposition

I read all 34 direct methods: ten Cargo/list/source controls, six original
libtest parser controls, two new caller-failure controls and sixteen transfer/
closure/generation/UUID/submission/resource/native-schema/catalog controls.
Static comparison confirms the original sixteen method ASTs are unchanged.
Positive baselines precede important source/catalog/transport mutations; inert
archive/binary/compiler placeholders are explicitly labelled nonphysical.
Findings 3–4 identify the two misleading coverage claims. The remaining methods
are useful local parser/source-contract controls, **all unexecuted**. They do not
exercise a real successful `validate_inputs -> launch -> validate_native` chain,
real TLS/server acquisition, Cargo/libtest discovery, unknown-writer settlement,
or whole-catalog failure/infrastructure behavior. Their absence of such evidence
is not converted into either a measured failure or a successful capability.

**Actionable disposition:** preserve finding 1's eligible compile/list slice;
repair the two existing metadata methods without changing their names or
weakening production checks; freeze coherent source/workspace/lock and exact
component/catalog review pins; then obtain actual REANA source/import/build/
discovery and parent-output evidence. Run every source-derived metadata method
in a separate declared-resource workflow, and every eligible native leaf/profile
in its own stated-resource workflow. No aggregate scheduling cap applies.
Acquire and independently review the actual raw outputs and strict offline
verdict. The prior accepted M1 metadata suite is not execution of these 34 new
controls. If final source/catalog counts change, derive the release from that
new source rather than reusing this count or old certificates.

No additional abstract review cycle is demanded absent a material change beyond
these narrow fixes. Exact geometry/gravity reference campaigns are separate
work; this report does not review the separately owned Python-arithmetic/literal
reference proposal, approve identity, reopen M1, or accept any new component.

## Exact source and inspection boundary

The companion `native_pipeline_review_sources.json` pins all subject/context/API
bytes, the report, source-check receipt and the closed reading inventory under
`results/galaxy_native_pipeline_review_20261122/`. It retains source-derived
selectors and manual traces without any passing runtime fixture. Representative
subject identities:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `reana/galaxy_preflight.py` | 13276 | `7698fc3fc18c1da16e2ac1eb85038cf0d1b259259a4a301cfda3d05ee5c42602` |
| `reana/galaxy_test_case.py` | 21689 | `b600008f8724920a4fb75b74aa23d0cb94ca6bba56cddeec8c433d8e645cbca5` |
| `tools/galaxy_evidence/common.py` | 17760 | `4cd01009348ba6af5d611e04446b4f72985d1af150c2f18b01b436cf264723ee` |
| `tools/galaxy_evidence/pipeline.py` | 33135 | `386bc5423d2fc05800bb3d0cbb367d83fb3ccbd378add9cdb6e3bc387c1354f1` |
| `tools/galaxy_evidence/readonly_adapter.py` | 5512 | `c8986e20c1cc08cd9689387ead5ee5fd9c05653c469e16bcceae0fae2afe4591` |
| `scripts/test_galaxy_preflight.py` | 15443 | `7b9338315883ff43beaa97fa8ebc77b6a1d5ae5e7288dc440b07423620652e4f` |
| `scripts/test_galaxy_cases.py` | 15013 | `339d8cc9aca05a2a9f266afcb43af28951fe7bc7c04e5fd0b4e4b62e236a0267` |

Actual read-only source check: **191 checks, errors=[]**, fifteen parsed Python
files and 34 unique written selectors. Root delivery identities and the author's
closed 40-body boundary were independently rechecked; this is not reliance on
their clean summary alone. The accepted supervisor/GET base and unchanged
wrapper contexts were compared byte for byte. Required documents retain their
historical entries; no concurrent gravity repair was changed or frozen here.

One tool response was wholly truncated by the output/context limit; none was
credited as read. The omitted remote run path, full implementation note and root
receipt were reread in bounded calls. No nonzero source-check command occurred.
The author's historical filename-discovery exits/truncated displays remain
historical inspection limits. No new target import/call, test/mock, compiler,
formatter/build, adapter/network/workflow or scientific/reference evaluation
occurred. Source checks are not tests. The only Orca write was the requested
early coordinator source disposition, followed by final task reporting.
