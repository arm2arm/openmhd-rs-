# Separate REANA workflows: execution validation, 2026-11-11

The new runner submits each independent simulation as its own workflow. A
common preflight verifies the frozen source and exports one binary; case
workflows reuse it without reinstalling Rust or rebuilding. No Rust numerical
source or physical acceptance threshold changed. All 66 workspace Rust/Cargo/
toolchain files match the preceding pressure-candidate snapshot.

## Verified preflight

`openmhd-fanout-preflight-20261111-v3.1`, UUID
`9ae446de-adf0-4618-960a-50965cad3db1`, finished at **12:41:19 UTC** after
690 seconds. All eight commands passed:

- Format and strict Clippy, including all targets/features.
- 154 debug Rust tests and a locked release workspace build.
- 94 Python tests, including concurrent submission, failed/changed prerequisite
  rejection, the unchanged 112-case manifest, early detection of a failed
  complete ladder with an unfinished sibling, scoped cancellation, retention
  of the first failure, and separation of observation errors from gate failures.
- M0 algebra/normalisation and independent reference checks.
- 163 release/all-target Rust tests.

The binary SHA256 is
`7720e737c3275d76cb7e1141c72d8d8a2969501082b5e728c74b57e9e414288f`.
Snapshot SHA256:
`fd3bf8185f140e13efb286d2a9530590f5ffcee17a5aec66cef75aebb347967c`.
The actual source parent is `deb245e`; source hashes preserve the uncommitted
execution changes. The separate Git revision `e1d6e4b` is a private one-commit
export fixture, not a development commit. Compact export reduced the history
bundle from **538,856,118 to 20,619,057 bytes**, retaining exact file hashes and
the original source revision. The source tarball remains separate.

The initial full-history upload was abandoned while still `created`; it never
ran tests. The v2 preflight was stopped after validation guards were tightened.
Neither is claimed as successful; v3 is the complete, matching preflight.

## Six real case workflows

The `openmhd-fanout-smoke-7f12f6c2627e-0000` through `-0005` workflows were
created concurrently at **12:43:40–41 UTC**, each as run `.1`. The packet is
`benchmarks/m1/reana-fanout-smoke.json`: four N32 fixed standing Alfvén cases
(regular/jitter .15, base/boost, t=1) and one regular Brio N256 base/boost pair
(t=.1). Every case completed and all **three boost comparisons passed**.

All six downloaded final CSVs are **byte-for-byte identical** to their matching
cases in the previous stopped pressure-reuse campaign. The same verified
binary is recorded by every workflow. Individual case execution/measurement
times were **12.4–27.9 seconds**, with explicit 180-second caps.

The backend staggered starts by approximately 15 seconds; up to **three
workflow executions overlapped**. This verifies independent concurrent
execution, not simultaneous startup of all six or unlimited physical capacity.
The client imposes no aggregate CPU/memory allocation cap. Each packet requests
two application threads and 4 GiB. The observed memory cgroup limit is exactly
4 GiB; `cpu.max` remains `max 100000`, so the generated CPU hints are **not
evidence of an enforced CPU quota or dedicated CPU reservation** on this server.

## Real cancellation control

Two additional independent workflows tested the backend stop path, using the
same verified binary. `openmhd-fanout-cancel-ccb1f1fe464b-0000.1` deliberately
used a .001-second case timeout. The monitor verified its timeout record,
saved `first_failure.json`, then requested a stop for its still-running sibling
`...-0001.1`. REANA confirms that sibling **stopped after 54 seconds**, before
its own 90-second cap. This is an intentional execution-failure control, not
a failed physical M1 benchmark. The force-stopped sibling's missing final
artifacts remain explicit observation errors; no success is inferred for it.
Inputs, first-failure evidence and terminal states are retained in
`cancellation/`. No manual stop was issued for either control workflow.

## Scope and retained evidence

`snapshot.json`, the nine frozen execution-source files in
`execution_sources.tar.gz`, preflight logs/receipts, per-case YAML, execution
records, raw final snapshots, original baseline records and terminal monitor
reports are retained here. `verification.json` records software checks;
`smoke_verification.json` records parity, timing and overlap. Full raw inputs,
the executable and other per-case artifacts remain in their REANA workspaces
and local `results/` downloads. Only the final CSVs are duplicated here.

The monitor's checkpoint reports the registered subset honestly: full spatial
ladders and the full physics matrix are unexecuted in this six-case packet.
**M1 is not accepted.** The original fixed standing-wave convergence failures
and default-profile shock failure remain open. See the
[separate error localisation](../standing_diagnosis/README.md).

Automatic sibling cancellation requires `watch` to remain running on an
available client host; it is not an always-on REANA service. A sleeping/stopped
host suspends monitoring. The first failure is retained even if later polls
have download errors. All deliberately launched tests and evolutions ran on
REANA; local work was packaging, checksum verification and postprocessing.

Run `python3 tests/reference/m1_pressure_campaign/fanout_execution/verify.py`
for the archive-integrity and parity checks; this does not run numerical tests.
The per-case runner is an execution layer, not an automatic M1 acceptance
controller. Required bounded, mean-field and calibration gates must still be
verified before a full numerical phase is submitted.
