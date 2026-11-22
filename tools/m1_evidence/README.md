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
  --client '/usr/bin/python3 /Users/arm2arm/orca/workspaces/openmhd-rs-/m1-run-alfv-n-wave-and-field-loop-benchmarks/tools/m1_evidence/reana_metadata_readonly_adapter.py' \
  --output results/m1_archive_metadata_preflight_observation_20261122
```

The delivered `reana_metadata_readonly_adapter.py` implements this protocol
with single-process standard-library HTTPS, without CLI/uv/wrapper children.
The absolute invocation above is for this workspace; a relocated checkout
requires its actual absolute adapter path. This is source-only delivery,
**not verified configured-service readiness or an actual observation**.
Credentials come from the existing private `~/.config/openmhd/reana-p4n.json`
(`server_url`/`access_token`), a private filename selected by
`OPENMHD_REANA_CONFIG`, or the complete `REANA_SERVER_URL`/`REANA_ACCESS_TOKEN`
environment pair. Partial environment overrides fail. No settings are read
at import or source/import preflight. Values never belong in argv, committed
source, snapshots or receipts. The entrypoint calls only:

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

The audited primary interface is the installed REANA-client 0.9.6 with
REANA-commons 0.9.11's packaged REANA-server 0.9.4 OpenAPI, checked against
[server 0.9.4 GET routes](https://github.com/reanahub/reana-server/blob/0.9.4/reana_server/rest/workflows.py),
[its authentication decorator](https://github.com/reanahub/reana-server/blob/0.9.4/reana_server/decorators.py),
[controller list mapping](https://github.com/reanahub/reana-workflow-controller/blob/0.9.4/reana_workflow_controller/rest/workflows.py)
and [pagination/file helpers](https://github.com/reanahub/reana-workflow-controller/blob/0.9.4/reana_workflow_controller/rest/utils.py).
Exact consulted bytes, hashes and locators are retained locally under ignored
`results/metadata_readonly_adapter_design_20261122/source_receipts.json`.
These are source identities, not a probe of the configured server's version.
The existing formatted CLI receipt's decimal-string `run_number` is a CLI
transformation; it does not establish the REST schema. The adapter accepts
REST `items`/integer `total` pages with an explicit versioned `name` and UUID,
never invents a missing UUID/version, and never treats an unversioned CLI
row plus `run_number` as that REST response.

Observation uses only `GET /api/workflows` with `type=batch`, exact base-name
filter, numeric `page`/`size`, and no status filter. Every matching requested
full-name/version row is retained, including duplicate, pending or stopped
rows; other explicit integer versions cannot stand in for the requested one.
All base-name pages are enumerated twice and their identity/status projections
must agree. Inconsistent totals/lengths/optional pagination flags, unexpected
base names, unsupported name/version formats or changing generations fail.
This is a finite quiescence check, not a server transaction guarantee.
Pagination has engineering bounds of 100 rows/page and 100 pages/scan; it
does not follow server-provided links. Exhausting a bound fails closed.

The source-supported authentication is `access_token` in each HTTPS query,
held in memory only. Unlike the legacy client's `verify=False` path, the
adapter requires normal CA/hostname verification, refuses every redirect
(including same-origin redirects), disables automatic proxies and has no
insecure fallback. Normal `SSL_CERT_FILE`/`SSL_CERT_DIR` CA configuration may
apply; actual host certificate trust/access remains unobserved. Diagnostics
never include request URLs, settings, headers, error bodies or exception
arguments. This supplies no claim about server/proxy logging, platform
retention or redistribution authorization.

Download first resolves one exact full-name/version row with a real UUID and
finished status, requests only `GET /api/workflows/<UUID>/workspace/<path>`,
then checks the same identity/status after the stream. Only the eight named
metadata output paths are allowed; globbing, directories, encoded/traversal
paths and zip/other content types are rejected. The audited non-preview
single-file response is octet-stream; an attachment filename, if present,
must equal the requested path or its basename. Compressed/duplicate headers
and inconsistent Content-Length fail. A proxy stream without Content-Length
is accepted only through its ordinary HTTP framing/EOF; exact expected-byte
hashes remain checked by the outer artifact manifest/certificate validator.

Output directories are traversed with no-follow descriptors; final and
`.partial` names must be absent. Artifact stream bytes are retained in an exclusive regular
`.partial` file and published without replacement only after all checks.
Handled failures leave the requested name absent and emit a typed JSON
diagnostic on stderr, retaining the received prefix under `.partial` (up to
16 MiB, with received/retained lengths distinguished on overflow). A rejected
observation can leave an empty partial: raw REST pages/error bodies are not
published as server receipts. No error body is downloaded. A late local
close failure is recorded as failure even if validated bytes were already
published; it cannot authorize a certificate. Severe storage/process loss may prevent cleanup or a
diagnostic; external transport/status receipts remain required. Successful
stdout is a credential-free diagnostic with actual selected UUIDs and page/
byte counts, never artifact contents. The total adapter deadline is 120 s
with at most 15 s per blocking socket operation (a final operation can cross
the deadline by that bound), within the observer's existing 300 s child
timeout; no subprocess writer is created. Repeated observations use fresh
directories and never resubmit a workflow.

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

Linux supervision creates a distinct session/process group and observes the
primary's exit with `waitid(WNOWAIT)`, retaining the original unreaped leader
through every group signal and group/writable-FD scan. Its waitable-child,
PID/starttime and private PGID/SID identity must remain held before TERM/KILL
or numerical group matching. Only after group and writable-log-FD closure
does it reap the direct child; there is no later group signal or group scan.
A reaped/lost leader cannot lend authority to a reused PGID. Lost authority
fails cleanup and disables numeric group matching, while independent writable
log-FD checks remain. The supported parent has no competing reaper or SIGCHLD
auto-reaping handler; this is not a recovery guarantee after that ownership
is lost. `command.json` retains the original argv/child PID/runtime links and
adds cleanup `leader_identity` (PID, PGID, SID, starttime),
`leader_held_until_group_close` and `group_authority_lost`; the strict validator
requires that identity, held closure and no lost authority for success.

Same-UID detached-session log writers are included; their observed
PID/starttime is rechecked before signalling. Supported jobs must expose
their own UID's Linux `/proc` process/FD metadata and `waitid(WNOWAIT)`.
The pinned image digest is the existing REANA environment image, not an
inferred Python image. These capabilities, and the collector's `/bin/ps`,
`flock` and POSIX signal-mask dependencies, have not been observed by the
new source/import preflight or controls. Zombies cannot write;
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
