# Execution of the first post-M1 implementation slices

M1 scoped acceptance is complete at `309ae41`. Identity, static 3D geometry
and collisionless direct gravity are separate new components. Written source,
tests, successful compilation and test inventories do not accept those components.

The `galaxy-source-preflight` study in `reana/remote.py` uses the existing
checksum-pinned Rust 1.85.1 bootstrap and environment image. It requires format,
strict all-target/all-feature Clippy and a release workspace build. Its final
command runs `reana/galaxy_preflight.py` **on REANA**. That command compiles debug
and release all-target/all-feature tests with `--no-run`, records Cargo's JSON
artifact messages, and calls each compiled libtest executable with `--list`.
No test method runs in this preflight. No numerical source/kernel/reference
evaluation is authorized locally by this harness.

The exporter binds each exact leaf to its build profile, package manifest,
target/source, executable SHA256 and frozen snapshot/source inventory. It retains
compile/list stdout, stderr and command records, rejects ignored tests pending
explicit disposition, checks source identities before and after, and exports
the actual executables plus catalog. A failed/interrupted preflight retains a
failed report and cannot release dependent cases. External infrastructure loss
still needs authoritative workflow/status/log receipts; command timeout metadata
does not certify descendant cleanup or a successfully finished workflow.

Prospective preflight resources are four CPU threads, 8 GiB and 30 minutes per
compile command, with `RUST_TEST_THREADS=1`, `RAYON_NUM_THREADS=1` and FFI threads
one. The submission YAML must explicitly declare these resources, and actual
visible CPUs/cgroup limits must also be retained. The ordinary legacy YAML's
resource declarations must not be mistaken for this new study's final declaration.

`scripts/prepare_galaxy_reana.py --output <fresh-directory>` is the written
source/submission wrapper. It uses the existing minimal compact-history freezer,
then derives a JSON-as-YAML workflow with four requested/limited CPUs and 8 GiB
for both preparation and compilation, and fixed `galaxy-source-preflight --jobs
4` arguments. The final submitted specification hash and its derivation are
recorded in the original `snapshot.json`; source and archive digests retain
their freezer values. This command prepares files and submits nothing. Its
three synthetic packaging controls in `scripts/test_galaxy_submission.py` are
also unexecuted and require individual REANA workflows. Actual CPU/cgroup
enforcement must still be observed: declarations alone are insufficient.

After coherent source review and a real passing preflight, every selected test
leaf gets its own workflow using the exact exported executable and `--exact
--test-threads 1`. Release requires exact catalog coverage, actual one-leaf
execution with no ignored/failed test, snapshot/binary/case identities, terminal
server observation, complete logs and independent output review. Physical
geometry/gravity gates additionally require their independently frozen literal
oracles, norms and convergence evidence; passing a unit leaf is insufficient.
The ten written `GalaxyPreflightMetadataTests.test_*` controls in
`scripts/test_galaxy_preflight.py` cover exact/duplicate selectors, rejection of
benchmark/execution output, frozen-byte replacement and path/link escapes,
Cargo target identity, successful build completion, duplicate targets, binary
escapes and empty-catalog rejection. Their fixtures are inert, labelled synthetic
metadata; they contain no numerical results and never execute Rust. These new
controls also require separate REANA execution. No workflow, test or preflight
has been run by writing these files.

## Native one-leaf execution

`reana/galaxy_test_case.py` is the written native case job. It verifies the
original snapshot, preflight source inventory, four prerequisite commands,
compile/list journals, parent artifact hashes, finished server observation,
target identity, selector and exported binary. The case document pins every
dependency input and the payload pins all uploaded bytes. Binary transfer uses
at most 512 nonempty one-MiB parts. Case eligibility covers reviewed standalone
galaxy-types/gravity targets, the two `geometry3_analytic`/`geometry3_controls`
integration targets, and only the four explicitly listed
`three_d::exact::tests::*` library selectors. Reviewed case preparation must
also confirm their filesystem/runtime dependencies and complete source catalog.
Older restart tests embedding `CARGO_BIN_EXE` absolute paths need a separate
source-layout execution route and are not silently declared portable.

The source snapshot now includes `tools/`, retaining the already reviewed and
REANA-tested `tools/m1_evidence/reana_metadata_job.py` supervisor. Its original
source remains unchanged. A case verifies that exact module against the frozen
snapshot, imports its inert definitions, and uses held-leader/writable-log-FD
supervision with declared per-leaf timeout and one test/Rayon/FFI thread.
The native job passes `--exact`, `--test-threads 1`, `--color never` and
`--show-output`. Its raw stdout must contain one named successful test and the
matching one-pass/zero-failure/zero-ignored libtest summary, including the exact
filtered count from that compiled target. Successful test diagnostics remain
visible in the retained output. Before calling supervision it durably publishes
actual argv/cwd and input/runtime/binary/source launch intent. An escaping
supervision exception retains unknown closure and external-terminal evidence;
it cannot become a `not_launched`/settled receipt. An unclosed writer is a
failed case requiring external terminal evidence; no successful closure is invented.

The eight result/runtime/command/stdout/stderr/child-witness/raw/artifact files
use the existing read-only adapter's allowed download names, with separate
native-result and libtest-witness schemas. Six additional written metadata
controls cover one-leaf shape, zero/ignored tests, wrong selectors/counts,
aggregate/duplicate results, failed/truncated summaries and expected panics.
These are parser fixtures, not execution evidence. Native job source review,
case preparation, immutable real preflight and all per-leaf executions/output
review are still required before this path can validate a component. Two new
inert written controls cover escaping supervision and actual prelaunch failure;
the file now has 18 unexecuted controls.

The authored practical interface is `scripts/prepare_galaxy_cases.py`, described
in [NATIVE_CASE_IMPLEMENTATION.md](NATIVE_CASE_IMPLEMENTATION.md). Its
`acquire-preflight`/`prepare`/`collect`/`verify-results` commands submit or recover
nothing. A new GET-only adapter reuses the unchanged tested transport's TLS and
partial-publication helpers with a narrow preflight export/log allowlist and
UUID-bearing observations. Ordered one-MiB archive parts preserve original
archive/member hashes rather than claiming an oversized archive passes the
old 16-MiB path/body protocol. Actual acquisition capability remains untested.

Preparation binds an immutable actual preflight and explicit reviewed
source/catalog contract: 26 identity, 28 geometry (including four library),
39 gravity methods **per profile**, yielding 186 native cases if those counts
remain unchanged after source repairs/review. Both profiles are mandatory;
missing methods are failures, never silently excluded. Initial independent
case requests are identity 1 CPU/2 GiB/180 s, geometry 1 CPU/2 GiB/300 s and
gravity 1 CPU/1 GiB/180 s, all one thread. Ready cases may run concurrently
without an aggregate CPU cap. Runtime/cgroup visibility is retained separately
from declarations. Do not interpret the native 186-case count as the older
M1 metadata snapshot's unrelated 186-source-member count.

Whole-catalog output checking requires original plan/submission/context pins,
actual observe/eight-download/observe UUID/version identities, every raw body
and transport hash, native-schema/source/runtime/command/held-leader cleanup,
and exactly one nonignored passing libtest leaf per workflow. Failed/stopped/
pending/uncertain rows retain forensic histories and cannot pass. The new
`scripts/test_galaxy_cases.py` contains 16 additional written inert metadata
controls; no new test/import/build/preflight/network action has occurred.
Independent source review of the caller/transfer/pipeline, final coherent
source/import preflight, each metadata and native REANA case and independent
actual output review are still required. No component acceptance is made by
any helper, catalog, leaf or whole-catalog flag.

Primary API references consulted for this harness are the
[Cargo JSON-message specification](https://doc.rust-lang.org/cargo/reference/external-tools.html#json-messages)
and [rustc libtest options](https://doc.rust-lang.org/rustc/tests/index.html).
The attempted Rust 1.85.1 documentation URLs were unavailable through the web
tool. The exact Rust 1.85.1
[console discovery source](https://github.com/rust-lang/rust/blob/1.85.1/library/test/src/console.rs)
and [terse formatter](https://github.com/rust-lang/rust/blob/1.85.1/library/test/src/formatters/terse.rs)
were then inspected: the terse discovery path prints one `name: test` line per
leaf and no summary footer. Actual compatibility with the pinned compiler
remains a required REANA observation.
