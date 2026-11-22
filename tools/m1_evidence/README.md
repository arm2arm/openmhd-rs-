# Read-only M1 evidence tools

These host utilities collect, reduce and freeze existing REANA outputs.
They submit no numerical workflow, evolve no state, build no code and
cannot accept M1. The scientific source, registered cases and numerical
reducers remain unchanged. See [the archive plan](../../docs/M1_FINAL_ARCHIVE_PLAN.md).

Use the repository root as the working directory and fresh output paths.
The [independent source review](../../docs/M1_FINAL_ARCHIVE_DESIGN_REVIEW.md)
at `b402753` requires repairs before complete capture/packaging or reliance
on portable verification. Its eight findings cover wave symlink containment,
connected provenance/coverage, nested inventories, coherent observations,
failure receipts and optimized-interpreter rejection. The following commands
describe the intended workflow; that repaired full path has not run.
After the existing supervisor produces the complete passing verdict:

```sh
python3 tools/m1_evidence/prepare_final_evidence.py --output results/m1_final_complete_collection
python3 tools/m1_evidence/pack_final_review_evidence.py --input results/m1_final_complete_collection --output results/m1_final_output_review/evidence
python3 results/m1_final_output_review/evidence/verify_final_review_evidence.py
```

The collector first requires all 214 cases and seven phase checks, then
executes unchanged strict provenance verifiers and six independent read-only
reducers. The physics collector obtains actual primary geometry/projected
bins from the fresh workflows; historical equal hashes do not substitute
for downloading their bytes. Partial failure preserves the new output.

The packager verifies the closed full collection, records deterministic
compression identities, copies historical packets and frozen source/reference
bytes, and closes its immutable evidence inventory. Its portable verifier
checks archive identities and report coverage without requiring future
development working files to remain frozen. Large raw inputs are identified
by their actual-byte hashes and retrieval provenance, not included here.

At preparation time, the sources have been syntax parsed and inspected.
The complete collector's readiness guard read the actual pending plans,
returned exit 2 and created no output. No downstream complete-input
collection, packaging or portable verification was executed. Source review
has identified the repairs above; final numerical-output review is pending.
The standalone physics collector and unchanged
numerical reducers have already been used on partial fresh observations;
those uses do not validate the new complete archive path.

## Metadata regression execution

The runner revision addresses findings 1–5 of the separate
[runner review](../../docs/M1_METADATA_RUNNER_DESIGN_REVIEW.md). This is a
source-only author correction: no new runner, import preflight or regression
case has executed. The real completed physical archive and independent
output review remain separate prerequisites; M1 is unaccepted.

`prepare_metadata_reana.py` freezes committed Git blobs under the host-tool
and two historical-packet roots, rejecting changed/missing/linked selected
files and tracked caches. It does not import tests while preparing a source
snapshot. The literal full coverage policy requires **all three** committed
files: `test_collection_metadata.py`, `test_archive_metadata.py` and
`test_runner_metadata.py`. Pending/uncommitted peer deliveries cannot be
silently omitted. Each direct synchronous, undecorated `test_*` method of a
plain `unittest.TestCase` subclass becomes one workflow. Factories, inherited,
async, decorated, duplicate and dynamic discovery/dispatch forms are rejected.
The preflight imports only these explicit test modules, resolves each exact
leaf and parses/compiles every packaged Python source; it does not execute
test suites. Imports still require source review for side effects.

Jobs declare one CPU, 2 GiB memory, a 180-second **direct child wait** timeout
and single-thread library settings. Validation, extraction, queueing and
the bounded cleanup grace periods are outside that child timeout. The pinned
image and resource fields are declared labels, not image attestation or proof
that reservations were enforced. Runtime records retain interpreter,
optimization, visible CPUs and cgroup values independently. Snapshot inputs,
fixtures and adapter argv must contain no credentials; raw child logs are
not automatically scrubbed or secret-certified.

After the repaired tools and their metadata tests are committed:

```sh
python3 tools/m1_evidence/prepare_metadata_reana.py snapshot \
  --output results/m1_archive_metadata_source_20261122
```

Submit its `preflight` plan with the unchanged generic
`scripts/reana_cases.py submit --directory ... --client ...` action. Its
client adapter path must be absolute because submission runs inside each
case directory. Reuse only that script's **submit** action; its physics
check/watch routines do not collect metadata jobs. Existing identities and
uncertain submissions must be observed, never implicitly resubmitted.

Once the actual preflight has finished, collect a fresh read-only observation:

```sh
python3 tools/m1_evidence/prepare_metadata_reana.py observe-preflight \
  --snapshot results/m1_archive_metadata_source_20261122 \
  --client /absolute/path/to/reviewed-read-only-adapter \
  --output results/m1_archive_metadata_preflight_observation_20261122
```

This is a concrete adapter protocol, **not a claim an adapter or server
observation is already verified**. The credential-free adapter argv may
identify an absolute executable (or an absolute interpreter and adapter).
Credentials belong in its existing private environment/configuration, never
argv or committed source. The entrypoint calls only:

```text
<argv> observe --workflow <planned-name.1> --output server-before.json
<argv> download --workflow <planned-name.1> --path outputs/<file> --output artifacts/<file>
<argv> observe --workflow <planned-name.1> --output server-after.json
```

Commands run inside the fresh observation directory. `observe` must query
the authoritative server and write exactly
`{"schema":"openmhd.metadata-server-observation.v1","origin":"server",`
`"observed_utc":"<UTC ISO8601>","matches":[{"workflow":"<name.1>",`
`"name":"<name>","version":1,"status":"finished"}]}`.
The adapter must preserve all matching workflow/version observations, never
choose one of an ambiguous set or translate running/stopped/uncertain into
finished. The normal host path always performs both observations and each
actual artifact download. An `origin=fixture-negative` receipt is rejected;
synthetic unit-fixture records are not real observation evidence. Trust in
the operator-selected adapter/server is explicit, not cryptographic server
attestation or proof derived from a planned workflow label.

The observation retains the original preflight plan, submission, payload,
workflow spec and case bytes, both server observations, exact artifact bytes
and durable transport attempts. Each attempt records argv, UTC times,
duration, outcome, return code, requested workflow/path, downloaded hash and
retained credential-redacted diagnostic hashes. Partial failures remain in
their fresh directory without a certificate. Known credential-pattern
redaction is not a general secret audit; inspect the actual adapter/log packet
before distribution. A fresh path permits a later observation, not another
workflow submission.

Before `certificate.json` is written, stable-generation fences capture each
required metadata file into one immutable buffer per attempt (maximum three
attempts, 16 MiB per file); parsing, hashes and embedding use those same
buffers. The final unchanged fence rejects replacement before release. All
downloaded outputs, including their manifest, are embedded with hashes in
the certificate, so remote case consumption needs no live host directory.
Then prepare the independent case plan:

```sh
python3 tools/m1_evidence/prepare_metadata_reana.py cases \
  --snapshot results/m1_archive_metadata_source_20261122 \
  --preflight results/m1_archive_metadata_preflight_observation_20261122 \
  --output results/m1_archive_metadata_cases_20261122
```

Host release and every remote dependent case use the same strict validator
for `openmhd.metadata-preflight-certificate.v2`. It checks the unique finished
workflow/version against the original plan/spec/payload/submission, all exact
download hashes, versioned result/child/runtime/command schemas, true bool/int
types, metadata-only scope, exact preflight command/mode, complete AST and
selector coverage, actual leaf/source identities and parent/child interpreter
links. No dependent directory is created from rejected/incoherent evidence. Source, payload and
plan schemas are v2; legacy loose v1 receipts cannot release these cases.

Submit all ready cases concurrently through the same generic submit action,
one independent method per workflow with declared resources and no aggregate
cap. The new runner controls cover failure envelopes, raw malformed/missing
child output, launch/timeout/optimization, actual metadata import success and
failure, descendant writers, preflight status/identity/schema contradictions,
selector factories/unsupported forms and coherent artifact replacement. They
are labelled synthetic metadata controls, never fake successful physical M1
evidence. Root will commit/review the exact three-suite revision before the
real source/import preflight and these per-case workflows.

Every normally started parent creates `outputs/` before validation. For
handled validation/extraction/launch/nonzero/timeout/missing-child/invalid-child
or optimized failures in a writable workspace, its declared closed output is:

| Artifact | Meaning |
| --- | --- |
| `result.json` | v2 result, typed outcome, timestamps, exact command and source/runtime links; both scientific acceptance flags false |
| `runtime.json` | v2 actual interpreter/host observations plus declared labels |
| `command.json` | v1 durable launch intent/final attempt, timeout scope and cleanup |
| `stdout.txt`, `stderr.txt` | Child-only logs, hashed after supervised writers settle |
| `child_raw.bin` | Original child bytes, including malformed bytes, or an explicitly absent empty file |
| `child_result.json` | v1 typed absent/invalid/valid envelope, raw hash/length and validated parsed child |
| `artifacts.sha256.json` | Exact seven-file map (manifest excludes itself) |

Linux supervision creates a distinct session/process group, sends TERM then
KILL for remaining descendants, reaps the direct child and checks `/proc` for
live group members and same-UID processes holding writable log descriptors
before closing/hashing logs. This includes detached-session log writers;
their observed PID/starttime is rechecked before signalling. Supported jobs
must expose their own UID's `/proc` process/FD metadata. Zombies cannot write;
arbitrary escaped nonwriters or UID changes are outside this containment
claim. Unsettled cleanup or process-inspection failure is failure, never
immutable success. `-O`/`PYTHONOPTIMIZE` rejection remains unconditional and retains a
handled failure envelope. Pod loss, SIGKILL, unwritable/full storage or process
loss can prevent local finalization: retain the external actual workflow,
status, download failure and job-log receipts; never relabel infrastructure
loss as a complete packet. Metadata success cannot accept M1 or replace the
real final scientific collection/output review.

Add the separate output review beside `evidence/`, pin its manifest, close a
separate reviewer inventory, then close the final outer archive only after
the coordinator resolves every required finding. Preserve each original
review byte. No utility success is a substitute for that review or an
explicitly scoped M1 acceptance record.
