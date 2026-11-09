# Running the validation studies on REANA

## Resumed acceptance campaign, 2026-11-09

The owner now requests continuing until M0/M1 gates pass, using REANA for
tests and long runs. This supersedes the execution hold below for **new**
validation jobs; old stopped workflows and their partial results stay intact.
The `m1-bounded` study runs format, strict Clippy, Rust/Python tests and M0
checks, then the combined screened-candidate gate with its medium wave/loop
stage. Short stages use three serial workers and 30-second case limits;
the medium stage uses `jobs` workers (at most 24), with a 600-second case
limit. The 64G workflow memory limit remains. It exports the gate and all
raw evidence, including failures, and never claims full M1 acceptance.
Full-matrix escalation requires the medium gate and calibration in
[the registered plan](M1_FULL_VALIDATION_PLAN.md).

The `m1-campaign` study reruns checks and preflight on its own frozen source,
measures the candidate's nonuniform mean-field ladder and N128 resource
calibration, and conditionally executes the full 30-case physics and 112-case
wave/loop/temporal matrices. It caps concurrent serial cases at 24 and reduces
that count using the measured memory budget. Its report remains distinct
from milestone acceptance; failures stop escalation and are exported with
compact measurements. Full snapshots remain in the workflow workspace.
After the first REANA preflight hit the laptop's 30-second case limit,
the campaign uses explicit 120-second short and 1800-second medium limits.
Failed short stages block medium execution immediately. The original
30/600-second defaults remain for local use; no physical threshold changes.

## Current execution hold, 2026-11-08

The user requested stopping long studies and developing fixes with short tests.
The original and candidate replays are stopped at 28/112 and 100/184 completed
cases. Spline-full stopped at 64/112; physics stopped with 14 completed,
6 failed and 4 unfinished cases. Completed-run records, provenance, source
snapshots and logs were saved locally with checksums; raw remote workspaces
remain available. No incomplete case is a pass, and stopping does not create
a restart checkpoint. Use the [short shock development loop](M1_SHOCK_INVESTIGATION.md)
for now; do not submit another long matrix during this phase.

The first REANA integration targets the AIP Kubernetes service at
`https://reana-p4n.aip.de` (observed server version 0.9.4). It follows the
[AIP serial-workflow example](https://gitlab-p4n.aip.de/esacchi/reana-test/-/tree/drp-ori)
at revision `b3a9945f078d7a909676ba716f3ae8618686bb22`. Its approved Python
environment is pinned by image digest in [reana.yaml](../reana.yaml).

This moves execution off the development machine. Each study is a separate
Kubernetes workflow, with up to 24 independent serial simulations running
inside its study job by default. Simultaneously submitted studies can run
concurrently, subject to cluster scheduling. This is study-level scheduling;
it does not introduce MPI or one pod per case. Increasing this worker count
does not accelerate an individual serial case. The separate `threading` study
below explicitly runs one simulation with a local pool of up to 24 threads.

## First deployment evidence (2026-11-08)

`openmhd-smoke-20261108-v3.1.1` completed on Linux/x86-64 at
`2026-11-08T12:33:26Z`: format, Clippy, all 88 Rust tests, a locked release
build, 22 Python tests, both M0 checks and two N8 simulations to t=.02 passed.
All 11 output-manifest entries were downloaded and checksum-verified. The
source-snapshot SHA-256 is
`58a8f30e9f4a0ce349319d90fa62daf812d79d5acdeb1008257d6ede9f714e1e`.
The runtime used Rust 1.85.1, Python 3.11.6, NumPy 1.26.4 and Matplotlib 3.8.0.
Local evidence is retained in `results/reana_remote_20261108/smoke/`.

A separate preparation attempt encountered a TLS handshake timeout before
running numerical tests. Bounded retries and atomic downloads were then added;
the expanded 24-test Python suite passed locally and is included in the new
remote regression submission. A subsequent preparation-recovery guard adds
one further test; all 25 current Python tests pass locally.
This smoke evidence establishes remote execution, not full M1 acceptance or
completion of the long remote benchmark matrix.

`openmhd-regression-20261108-v2.1` subsequently completed at
`2026-11-08T12:54:32Z`: all 24 Python tests in its snapshot and the existing
core-flux, geometry, kinematic, coupled-planar and general vector-potential
regression scripts passed. All eight output-manifest entries verify locally.
Its source-snapshot SHA-256 is
`14c9f78bc321ab3cd87febe3aabb2104b247a835bdfa1ab219ced73178b463cf`;
evidence is under `results/reana_remote_20261108/regression/`.

`openmhd-heun-20261108.1` completed at `2026-11-08T14:03:54Z` with 24 workers
and a 64G test-job memory limit. All 92 Rust/27 Python tests and 40 bounded wave
evolutions completed; the numerical runner took 33.35 seconds after setup and
checks. All 17 exported artifacts verify locally. See the [measured time slopes,
remaining limitations and archived plot](M1_HEUN_RESULTS.md). This is a bounded
time-integrator study, not completion of the full physical matrix.

`openmhd-auxiliary-20261108.1` completed at `2026-11-08T16:12:39Z`: all
102 Rust/29 Python checks and 80 auxiliary-projection/limiter comparisons
completed, using 24 workers and a 64G memory limit. The numerical study took
53.13 seconds. All 17 exported artifact hashes and all run-file hashes verify
locally; see [results, limitations and the archive](M1_AUXILIARY_RESULTS.md).

`openmhd-threading-20261108.1` finished at `2026-11-08T16:15:05Z`, including
the full N256 t=1 demonstration in 49.1 minutes at 24 threads. Its older frozen
source passed 95 Rust/28 Python checks. See the [measured scaling, physical
checks, CFL retries and comparison limits](THREADING_RESULTS.md).

The full studies are submitted as `openmhd-original-20261108`,
`openmhd-candidate-20261108` and `openmhd-prescribed-20261108`. Consult REANA
for their current status; submission is not a claim that their scientific
gates pass. The comparator's setup used the recorded recovery helper after
a download timeout; its numerical source snapshot was preserved.

## Freeze and submit the current source

Use `reana-client` with `REANA_SERVER_URL` and `REANA_ACCESS_TOKEN` configured
locally. Keep credentials outside the repository and workflow inputs. The
client needs the token; the computation jobs do not.

```sh
python3 scripts/prepare_reana.py --minimal --output results/reana_submission
cd results/reana_submission
reana-client validate
reana-client run -w openmhd-smoke -p study=smoke -p jobs=24
reana-client status -w openmhd-smoke
reana-client logs -w openmhd-smoke
```

The packer includes the exact working source, including uncommitted changes,
a Git bundle identifying its base revision, and a SHA-256 manifest. It excludes
local `results/`, `target/`, credential-shaped files and symlinks. The bundle
retains reachable Git history; credentials must never be committed to Git.
The compressed source and Git bundle are uploaded in 1 MiB parts to avoid long
HTTP request; every part and the reassembled archive are checksum-verified.
Use a fresh output directory for every source snapshot. Submission does not
commit or push the development worktree.

`--minimal` omits the existing `m1_completion`, `m1_heun`, `m1_auxiliary`, `m1_physics_probe`, `m1_shock_diagnosis`,
`threading_scaling` and `threading_completion` result directories under
`tests/reference/`; these are not inputs to the simulations or unit tests.
All numerical source and required independent references, including the M0
Athena shock/vortex data, are retained. The exact omission list is recorded
in `snapshot.json`. Omit this option when old study archives are needed
remotely. The original local archives are never modified.

Preparation verifies the uploaded bytes, reconstructs the Git checkout and
installs Rust 1.85.1 in the workflow workspace without root privileges.
The official release manifest and each downloaded compiler component are
SHA-256 checked. The image provides Python, NumPy and Matplotlib; their actual
versions, architecture, compiler details and cgroup limits are recorded.
Network access to `static.rust-lang.org` is needed during preparation.
Transient download failures are retried up to three times. Incomplete files
are never promoted to verified component archives.

## Execution groups

| `study` | Work performed |
| --- | --- |
| `smoke` | Format, Clippy, workspace tests, release build, all Python unit tests, M0 algebra/reference checks, two small wave/loop simulations |
| `regression` | Python unit tests and existing core-flux, geometry, kinematic, coupled-planar and general vector-potential regression studies |
| `original` | 112 original-profile physical and temporal evolutions |
| `candidate` | 184 mean-field/comparator physical/temporal evolutions |
| `prescribed` | 32 prescribed-flow loop evolutions |
| `heun` | Workspace/M0 checks, 40 bounded time/boost wave evolutions comparing signal endpoint with reevaluated Heun, plus a plot |
| `auxiliary` | Workspace/M0 checks, 80 bounded Heun evolutions comparing bin/cubic auxiliary projection with limiting on/off, plus a plot |
| `threading` | Workspace/M0 checks, sequential 1/4/12/24-thread N64/N128 comparisons, then a full N256 case at 24 threads; requires `jobs=1` |
| `spline-full` | Workspace/M0 checks, full 112-run physical/temporal wave/loop matrix for `bulk-frame-heun-spline-v1` |
| `physics` | Workspace/M0 checks, 24 general-solver shock/vortex evolutions against the unchanged M0 Athena packet; [contract](M1_PHYSICS_PLAN.md) |

After the smoke workflow succeeds, submit the remaining groups from the same
frozen submission directory:

```sh
reana-client run -w openmhd-regression -p study=regression -p jobs=24
reana-client run -w openmhd-original -p study=original -p jobs=24
reana-client run -w openmhd-candidate -p study=candidate -p jobs=24
reana-client run -w openmhd-prescribed -p study=prescribed -p jobs=24
```

To prepare a runtime ahead of execution, use `start -o TARGET=prepare-source-and-rust`
after uploading the workflow inputs. Once that preparation finishes, run the
study with `restart -o FROM=run-tests -o TARGET=run-tests`, retaining the same
`study` and `jobs` parameters. This skips the fresh-workspace preparation guard
and is only appropriate before that workspace has an `outputs/execution.json`.

For new submissions, the YAML requests 64 GB (`64G`) for the test job and 8 GiB
for preparation, with 24 independent simulations by default, as authorized by
the user on 2026-11-08. Existing frozen jobs retain their four-worker/8 GiB settings.
The deployed REANA 0.9.4 serial engine does not forward CPU request/limit options;
24 is an application-level worker cap, not a Kubernetes CPU reservation. `jobs` limits the existing
runner's concurrent simulations (1–24 accepted); it is not a Kubernetes CPU
reservation. Compilation uses at most four jobs, and library thread controls
are set to one. The environment probe on 2026-11-08 observed an uncapped CPU
cgroup; resource defaults and available concurrency are deployment-specific.
Measure representative cases before predicting full-suite duration. The
longest individual laptop runs took about 2.28 hours under their recorded
concurrent workload; this is not a prediction for the cluster.

## Outputs and interpretation

The `physics` study exports its summary, runs, manifest and provenance in
`outputs/physics/`, plus compact diagnostics and 64² projected vortex values
in `outputs/physics-measurements.tar.gz`. Full cell snapshots and explicit
polygon vertices stay under `source/results/reana_physics/`, with per-file
checksums in `runs.json`. A completed workflow can still have failed scientific
gates; consult `all_registered_physics_gates` and the individual diagnostics.

`outputs/execution.json` records every command, return code, duration and log
checksum. `outputs/runtime.json` records the runtime and source-snapshot hash.
`outputs/artifacts.sha256.json` covers the output artifacts. Per-command logs
are retained under `outputs/logs/` and are available while a command runs.

The REANA progress counter counts workflow steps, not individual simulations;
it can remain at `0/2` during a long benchmark command started with `FROM`.
For live case progress, download that study's
`source/results/reana_<study>/runs.json` or its `outputs/logs/00.log` from the
workspace. The run map grows as cases finish and includes their status and
wall-clock durations.

Complete original/comparator/prescribed studies also produce compact verified
archives in `outputs/{original,candidate,prescribed}/`, including numeric
summaries, source provenance and selected snapshots. Full raw results remain
in `source/results/reana_<study>/` in that workflow workspace. The regression
scripts retain their usual output directories under `source/results/`.

```sh
reana-client download -w openmhd-candidate outputs
reana-client ls -w openmhd-candidate source/results/reana_candidate
```

Preparation requires a fresh workspace by default; an existing run is never
silently overwritten. A crashed individual simulation is not automatically
resumed from a CSV snapshot. Raw files and command logs remain available for
diagnosis. Preserve or export results before any service retention policy
expires.

For a network failure during preparation, `--resume-prepare` verifies the
original upload hashes, Git revision and recorded source hashes before reusing
checksum-valid compiler archives. It rejects any workspace with an execution
record, including a failed numerical execution. Runtime provenance records the
actual bootstrap script hash separately from the original source bootstrap
hash. This allows an updated setup helper to recover an older frozen source
packet without relabelling its source.

To use this recovery on a failed preparation, copy the current `reana/remote.py`
as `recovery_driver.py` into a temporary submission folder alongside
[reana/recover.yaml](../reana/recover.yaml), named `reana.yaml`. Upload only
`recovery_driver.py` to that workflow, then use `restart -f reana.yaml
-o FROM=recover-verified-runtime -o TARGET=recover-verified-runtime` from that
folder. After recovery succeeds, restore the **original submitted** workflow
definition with `restart -f <original-submission>/reana.yaml -o FROM=run-tests
-o TARGET=run-tests`, passing its original study and worker count.

Workflow execution success is separate from scientific acceptance. The
adapter fails for unsuccessful commands, incomplete evolution counts or
source-integrity errors. It retains scientific gate failures in the original
summary structure. Current wave spatial/boost failures and temporal limitations
remain documented in [M1_COMPLETION_RESULTS.md](M1_COMPLETION_RESULTS.md).
Linux/x86-64 results must be measured and compared with the Mac reference;
cross-platform byte-identical trajectories are not assumed.

The `heun` study exports compact measurements and a plot in `outputs/heun/`,
and all raw snapshots in `outputs/heun-raw.tar.gz`. Its contract is in
[M1_HEUN_INVESTIGATION.md](M1_HEUN_INVESTIGATION.md); it does not replace the full
M1 acceptance matrix. Submit it with `-p study=heun -p jobs=24`.

The existing plot scripts accept compact archive paths. After collecting all
three new packets, generate the combined plots with:

```sh
python3 scripts/plot_m1_completion.py \
  --original collected/original --candidate collected/candidate \
  --prescribed collected/prescribed --output results/reana_plots
```

The paths above should contain the corresponding `summary.json.gz` and
`archive_sha256.json`. Historical checked-in packets are not overwritten by
remote measurements. Case-level Kubernetes scheduling and restartable solver
checkpoints are possible later improvements; neither is part of this first
migration.

### Projection-cache verification campaign (2026-11-10)

`m1-cache-campaign` runs all workspace checks, compares the cached-diagonal
binary with a pinned baseline, measures 1/4/12/24-thread performance, then
starts the unchanged `m1-campaign` phases only after bit-identical physical
outputs pass. Supply the baseline binary as a chunked archive named
`baseline-vector-potential` and its original `baseline-provenance.json` as
checksum-covered workflow inputs. The baseline comes from the stopped
`openmhd-m1-bounded-20261109.1` workspace; only `projected_rate.rs` may differ
among its recorded Rust/Cargo sources. Timings are observations on a shared
cluster. All runs are sequential during the comparison, at most 24 threads.

Peak memory calibration uses Linux `wait4` through `measure_process.py`; it
does not require `/usr/bin/time`, which is absent from the pinned image.
The wrapper records the largest process RSS, not simultaneous-worker total.
