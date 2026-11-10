# Handoff from ChatGPT conversation to Codex

*Prepared November 3, 2026. This is a curated, faithful project-context summary of the ChatGPT discussion, **not** a verbatim export of the ChatGPT conversation or a transferable Codex chat session.*

## Active binary-reuse campaign (2026-11-10)

`openmhd-m1-pressure-reuse-20261110.1`, UUID
`7a615758-c141-4903-a2ea-8da3094ddd58`, starts **05:35:42 UTC** after all
26 inputs upload. Packet/export:
`results/reana_{submission,export}_m1_pressure_reuse_20261110`.
Snapshot SHA256
`00d823cc61e3ebfca3c79645625e528bf45f59e0a94967f532d74cd52b56390b`,
323 sources, actual parent **4f491de**, clean at freezing; private export
revision is only a fixture. All 70 Rust/Cargo input hashes match the previous
passing pressure candidate. The only implementation change is the execution
correction below; previous numerical failures and thresholds remain intact.

The same `m1-pressure-campaign` study runs full preflight, all five bounded
stages, mean, calibration and full matrices in a fresh workspace. The five
new Python regressions must pass before any evolution. At this checkpoint
all eight preflight commands pass: formatting, strict Clippy, 154 debug Rust
tests, release build, 85 Python tests, 13 M0 algebra checks, independent
reference verification and 163 release/all-target Rust tests. The scientific
campaign starts **05:47:05 UTC**. All five bounded stages pass in 1308.14 s,
including the 48-run medium stage in 1096.51 s. The 24-run mean ladder also
passes in 14.87 s. [Verified preflight archive](../tests/reference/m1_pressure_campaign/reuse_preflight/README.md).
All 471 short-stage raw artifacts were downloaded and verified; all 365
scientific files reproduce the preceding campaign exactly. The 106 changed
runtime/log files and new provenance are retained in the
[short-stage parity archive](../tests/reference/m1_pressure_campaign/reuse_short/README.md).
All 384 medium and 168 mean raw artifacts are also downloaded and verified;
their 288/120 scientific files exactly reproduce the preceding campaign.
Independent reductions pass all 24 medium and 12 mean pairs. The complete
bounded/mean total is 1023 verified raw artifacts and 773 identical scientific
files. [Verified bounded/mean archive](../tests/reference/m1_pressure_campaign/reuse_validation/README.md).

Both N128 calibration drivers start **06:09:08 UTC** and record
`prebuilt_binary_sha256=90d40a752e357ed6a459e828d8a48cba51eed13549229271583f89fb7384a426`,
matching the campaign binary. Neither calibration log contains a Cargo build.
The wave pair now completes and passes in 1896.65 s: relative B L1 .00316421,
independently reduced maximum normalized boost L1 2.74699e-14, peak process
RSS 667,435,008 bytes. All 16 raw files verify; the N64→N128 order is 1.841711,
an observation rather than the required finest-three fit.
[Verified wave-calibration archive](../tests/reference/m1_pressure_campaign/reuse_calibration/README.md).
The vortex remains running; its completed memory/physics result, resource
allocation and full physical gates are pending. The previous HLLD vortex
calibration took about 43 minutes; this is a historical cost, not a completion
promise.
The old `openmhd-m1-pressure-campaign-20261110.1` remains stopped. Only this
new compute workflow is active, within 24 aggregate worker cores / 64 GB.

Download root `results/reana_remote_m1_pressure_reuse_20261110`. Monitor
`outputs/execution.json`, `outputs/logs/00.log`–`08.log` and
`source/results/reana_m1-campaign/campaign.json`. In Python test logs, the new
mocked calibration-failure test intentionally emits failed/cancelled phase
messages; distinguish that regression from the actual scientific campaign.
No gate or issue is closed until the required evidence passes. Keep the
active M0/M1 goal intact.

## Calibration execution correction (2026-11-10, issue #25)

[Issue #25](https://github.com/arm2arm/openmhd-rs-/issues/25) records the
shared-target calibration build failure below. The correction introduces
`--reuse-binary-sha256` in the wave/physics drivers. When explicitly supplied,
the existing preflight executable must exist and match that digest; Cargo
is not invoked. Standalone default builds keep the original command. The
campaign supplies the frozen binary digest to mean, both calibration drivers
and full physics/waves; provenance records the reuse choice.

Calibration futures are inspected as they finish. A failed return, missing
measurement or failed scientific check cancels the sibling process group,
including descendants. Both failed/cancelled outcomes remain in the campaign
record. The default bounded stage timeout behaviour is retained.

Five new Python regressions cover correct/missing/wrong/malformed reuse,
standalone build compatibility, campaign failure propagation/provenance and
real Linux descendant-process cancellation. At implementation time these
were unexecuted; all tests must run on REANA. Static inspection confirms unchanged Rust/Cargo
inputs and unchanged measurement/configuration/nested evolution-worker
functions. This is an orchestration correction, not a new numerical method.
The fresh campaign above subsequently passes all five new regressions as
part of its 85-test Python suite. Actual concurrent calibration remains pending.

The fresh `m1-pressure-campaign` packet above now runs the unchanged
acceptance sequence on REANA. Keep the old workflow stopped;
do not reuse an incomplete calibration as a pass or silently omit gates.

## Pressure-blend campaign checkpoint (2026-11-10)

`openmhd-m1-pressure-campaign-20261110.1`, UUID
`b04502aa-c906-4efa-9333-7f2649a28757`, started **04:39:05 UTC** after all
26 inputs uploaded. Packet/export:
`results/reana_{submission,export}_m1_pressure_campaign_20261110`.
Snapshot SHA256
`de65afe4f1920ec3a6db0535f904d48112227ce1fc57324fe604b3fbaf8b5c95`,
321 source files, actual parent `d1127f2`; private export revision is a fixture.
The only dirty file at freezing is `scripts/prepare_reana.py`, adding the new
campaign evidence directory to future minimal-export omissions. Relative to
the passing focused snapshot, only docs, the plotting script and that packaging
list differ. **Every Rust source and Cargo input is unchanged.**

The focused comparison below passes and its verified archive is committed.
This campaign runs full workspace/M0 checks, five bounded stages, the 24-run
mean ladder, N128 wave/vortex calibration, 30 full physics cases and the 112-run
wave/loop/temporal matrix. It uses explicit `hlld-pressure` throughout the
candidate; historical literal controls stay HLLD. Every phase must pass before
escalation. All thresholds, grids, times and caps remain as preregistered.
At most 24 aggregate worker cores / 64 GB; calibration determines the full
worker count from measured memory. Stop unnecessary long work at a verified
required-gate failure. No other compute workflow is active.

Monitor authoritative REANA status, `outputs/execution.json`,
`outputs/logs/00.log` through `08.log`, and
`source/results/reana_m1-campaign/campaign.json` with per-stage results.
Download root `results/reana_remote_m1_pressure_campaign_20261110`.
Final `outputs/artifacts.sha256.json` and the compact
`outputs/m1-pressure-campaign-measurements.tar.gz` appear on wrapper exit.
Do not restart or mutate the frozen packet. All eight preflight commands pass:
format, strict Clippy, 154 debug Rust tests, release build, 80 Python tests,
13 M0 algebra checks, independent reference verification and 163 release/all-target
Rust tests. [Verified preflight archive](../tests/reference/m1_pressure_campaign/preflight/README.md).
The scientific campaign starts at **04:51:22 UTC**. All four short stages
pass: 51 completed evolutions (49 candidate and two literal column controls),
with two literal planar pressure failures retained. All 471 raw artifacts
are hash verified; the [short-stage archive and plot](../tests/reference/m1_pressure_campaign/short/README.md)
include independent wave, vortex-norm, boost and final-budget reductions.
Short magnetic/velocity orders range 1.918–1.952 / 1.907–2.038. N32 vortex
diagnostics pass; N16 jittered mean-field drift .0016708 remains a failed
coarse diagnostic under the registered finest-quick-grid rule.
The 48-case N32/64 t=1 medium stage passes all 24 boost pairs, state and
budget checks in 1073.24 seconds. The complete five-stage bounded gate passes:
99 completed evolutions plus two expected literal planar failures. The
24-run mean-field ladder also passes all 12 pairs and four candidate refinement
rows, with maximum transformed component error 1.04361e-14.
[Verified medium/mean results and independent reductions](../tests/reference/m1_pressure_campaign/README.md).

**Stopped at 05:22:00 UTC:** the wave-calibration Cargo build exits 101 while
removing missing faer-traits/gemm rlibs during concurrent shared-target builds.
No calibration waves run. The vortex build succeeds with the same binary but
its evolution is interrupted by the stop. Its partial result is not accepted.
The campaign waits for both futures before checking failure, so it could not
advance and was stopped explicitly. No full physics or full wave matrix starts.
The [failure archive](../tests/reference/m1_pressure_campaign/calibration_build_failure/)
retains logs, failed memory record, partial vortex provenance and terminal status.
Running JSON checkpoints are historical, not authoritative workflow status.

Next fix hash-validated binary reuse in concurrent drivers and calibration
sibling cancellation, then test on REANA before a fresh complete campaign.
No Rust numerical change or threshold change is warranted by this build error.
M0 remains accepted; M1/#7/#19–#22/#24 remain open. No compute workflow remains
active after this stop.

## Passing focused pressure-blend comparison (2026-11-10)

`openmhd-m1-pressure-blend-20261110.2`, UUID
`976c4360-a91b-4a5c-842a-01c997ff82c5`, finished **04:31:45 UTC** after
741 seconds. Snapshot
`85cbaf2025f591ee989c59a33c4c5db5b3a212ef7fe6dd5c95feb5649760ad89`;
321 sources, actual parent `c0265ee`, private export revision is a fixture.
All 224 artifacts and 28 uploads verify. All 169 archived executable/config
files match published commit **144ac35** exactly. Format, strict Clippy,
163 release/all-target Rust tests, 80 Python tests and M0 checks pass.
All tests/evolutions ran on REANA, at most 16 worker cores / 16 GB.

All 24 evolutions finish; **all 96 historical HLLD/HLL files match**.
The eight `hlld-pressure-blend-v1` candidates and four boost pairs pass.
Column shock boost maximum L1 is **6.049405107e-14**, limit 1e-8;
regular shock is **5.619539122e-14**. Regular/jitter N32 vortex normalized
limited-face divergence maxima are **.06846058 / .07301384**, limit .1.
All positivity, budgets, mean-field, shock reference/Bx/seam checks pass.
Column base/boost vx row ranges are 1.87642e-12 / 8.42881e-13.
The original HLLD column failure and global-HLL vortex failure stay visible.
[Verified exact source/results, independent reductions and inspected plot](../tests/reference/m1_column_boost/pressure_blend/README.md).
The earlier strict-Clippy-only failure is preserved separately below.

Next run the unchanged complete sequence with `m1-pressure-campaign`:
workspace/M0 checks, five bounded stages, mean-field ladder, N128 calibration,
full 30-run physics ladder, then 112-run wave/loop/temporal matrix. Each phase
must pass before escalation. Use at most 24 aggregate cores / 64 GB, with
registered case caps and memory-based workers. Numerical source is unchanged
since the focused pass. At this checkpoint no workflow is active; the new
campaign is being prepared. Do not close M1 or claim general invariance yet.

## Pressure-blend implementation and failed preflight (2026-11-10)

The [registered pressure-weighted HLLD/HLL blend](M1_PRESSURE_BLEND_PLAN.md)
is implemented as `hlld-pressure-blend-v1`, with seven new Rust tests and two
Python tests. It blends the complete fluid/induction vector using the fixed
cubed neighbouring gas-pressure ratio; no shock-only theta correction is
combined with it. The earlier numerical paths remain separate. All numerical
tests/evolutions must run only on REANA.

First workflow `openmhd-m1-pressure-blend-20261110.1`, UUID
`e6315eaf-fc64-4a78-9d0f-2c7b84c3c33d`, ran **04:11:35–04:15:40 UTC**.
Snapshot `beda7bd90d04dfef8e004bf06030c173c18ffd75bdebb69a95a1569e35d64daa`,
321 sources, actual parent `c0265ee`. Formatting passed; strict Clippy failed
on `needless_range_loop` in the new covariance test. **No simulations ran.**
[Verified failed preflight](../tests/reference/m1_column_boost/pressure_blend_preflight/README.md).
The test-only loop is corrected using `enumerate`, without numerical changes.
A fresh v2 packet is being prepared; never restart the failed immutable packet.

The current source also prepares conditional `m1-pressure-campaign` routing
for the unchanged full sequence. It is not submitted unless all focused gates
pass. Require the 24-case shock/vortex comparison to preserve all 96 HLLD/HLL
control hashes and pass every candidate gate. Eight two-thread workers,
16 GB, 600 seconds per case. New observations use rest-frame shock windows
and `omega` metadata; the original shock-only archive remains untouched.
This failed-preflight record and the test-loop correction are retained together
with the implementation; the newer run .2 is described above.

## Completed failed shock-only HLLD trial (2026-11-10)

`openmhd-m1-shock-sensor-20261110.1`, UUID
`443effc9-4179-46ba-97d0-e27ca17e21c2`, finished **04:00:01 UTC**, 756 s.
Snapshot `2a8cadb08e98a2368ab48414a3e80ab780920f60b25bbaba0c63af33c374e969`,
315 source files, actual parent `8f48a08`; private export revision is a fixture.
All 28 inputs and 224 output artifacts verify. Format, strict Clippy,
156 release/all-target Rust tests, 78 Python tests and M0 checks pass.
All 24 focused evolutions finish; **all 96 historical HLLD/HLL files match**.
All tests/evolutions ran on REANA, at most 16 worker cores / 16 GB.

The new `hlld-shock-sensor-v1` passes both vortex diagnostics but fails the
column shock boost at **7.503948931e-6**, limit 1e-8. It is active but does not
remove the row instability. No long campaign was started. The workflow's
finished status is not scientific acceptance. [Exact source/results archive,
independent reductions and inspected plot](../tests/reference/m1_column_boost/shock_sensor/README.md).
The first remote face-window report used absolute x for boosted states;
archived independent reductions correct only that observation to rest-frame x.
No gate depends on this reporting error.

The next hypothesis is the [registered pressure-weighted HLLD/HLL blend](M1_PRESSURE_BLEND_PLAN.md).
This is an explicitly new MHD engineering extension, using the published
pressure ratio exponent three without tuning. Implement/test it separately;
require historical controls and both shock/vortex gates before escalation.
No workflow is active at this checkpoint. M0 remains accepted, M1/#24 open.

## HLL campaign failure checkpoint (2026-11-10)

`openmhd-m1-hll-campaign-20261110.1` started **03:06:16 UTC**, UUID
`f32fda39-1696-4fe2-8950-54e4ec10fd55`. Frozen packet
`results/reana_submission_m1_hll_campaign_20261110`, snapshot SHA256
`cf55c78de31a305bb06f0059e7a347cfe5c6563bcfcf64bba023b64932a067b4`;
307 source files, all 26 remote input names/sizes verified before start.
Preparation independently verifies input hashes. Actual source parent
`8d53b79`; the private export revision is a build/provenance fixture.
The Rust numerical source is unchanged from the passing HLL shock comparison.
Runner changes propagate and validate the explicit HLL choice, including four
new configuration/provenance tests. No new tests or evolutions run locally.

Preflight completes at approximately **03:19:16 UTC**: format, strict Clippy,
139 debug Rust tests, 148 release/all-target Rust tests, 76 Python tests,
13 M0 algebra tests and independent M0 reference checks pass.
[Verified preflight archive](../tests/reference/m1_hll_campaign/preflight/README.md)
retains all eight logs, the full snapshot manifest and 163 exact source/config
files; all 307 frozen source files and upload hashes verify. The first bounded
short-shock, symmetry and short-wave stages pass in 61.45 / 40.40 / 70.66
seconds. The coarse physics stage fails after 78.85 seconds: regular N32
vortex normalized limited-face divergence is .385293086709, limit .1.
All 20 physics evolutions finish with passing positivity, budgets and boost
pairs. The medium and every later phase never start. REANA ends **failed at
03:23:35 UTC** (1039 seconds). No workflow remained active at that checkpoint.
[Preserved failure, independent reduction and plot](../tests/reference/m1_hll_campaign/bounded_failure/README.md).
Two weak-field cells account for 98.35% of the squared normalized error;
dimensional divergence RMS is actually lower than HLLD. This is not permission
to change the diagnostic or claim a pass. Global HLL is not adopted.

Next implement and test the [prospective HLLD shock-sensor comparison](M1_SHOCK_SENSOR_PLAN.md).
It uses Minoshima–Miyoshi's published transverse-compression pressure-jump
correction with an explicitly documented Voronoi extension, not global HLL
or a relaxed divergence denominator. At this historical checkpoint the plan had not been implemented or executed;
see the newer failed-trial record above. Preserve existing numerical paths and require
exact historical HLLD/HLL controls plus both shock and vortex gates.

The `m1-hll-campaign` study executes workspace/M0 checks, all five bounded
stages, the 24-run mean-field ladder, N128 wave/vortex calibration, the 30-run
full physics ladder and the 112-run wave/loop/temporal matrix. Each phase must
pass before escalation. All numerical thresholds, grids, physical times and
resource/case limits remain as [registered](M1_FULL_VALIDATION_PLAN.md#explicit-hll-continuation-2026-11-10-before-campaign-execution).
At most 24 aggregate worker cores / 64 GB were permitted.

Monitor authoritative workflow status, `outputs/execution.json`,
`outputs/logs/00.log` through `08.log`, and
`source/results/reana_m1-campaign/campaign.json` with per-stage records.
Download root: `results/reana_remote_m1_hll_campaign_20261110`.
The wrapper exports compact results and an artifact hash manifest on exit;
all 13 final output artifacts now verify.
Do not mutate or restart the frozen packet. Stop unnecessary long work at a
verified required-gate failure. M0 remains accepted; M1 and #24 remain open.

## Completed HLL shock comparator (2026-11-10, #24)

`openmhd-m1-hll-shock-20261110.1` started **02:34:02 UTC**, UUID
`b689d692-63c5-40cb-9026-b338872346b2`. Frozen packet
`results/reana_submission_m1_hll_shock_20261110`, SHA256
`20c103fef9facca21884aed961dd7349997555492ebac9607f88e059daf4ff9c`;
305 source files, all 28 uploads successful. Actual parent `cac0088`.
At most eight two-thread simulations (16 worker cores), 16-GB job memory,
600-second case limits and 900-second per-command limits. The workflow finished **02:43:56 UTC** (594 s). No workflow remained active at that checkpoint.
All tests/evolutions ran on REANA.

Opt-in `--riemann hll` selects the existing two-wave formula explicitly with
separate `hll-comparator-v1` metadata and no fallback-count conflation. Default
HLLD and historical wrapper APIs retain their arithmetic. The comparison has
four original nx1024 regular/column base/boost HLLD controls requiring 24
byte-identical scientific files, plus four matching HLL trials. It measures
positivity, budgets, Bx/seam, original reference errors and 1e-8 boost gates,
with accepted-step row-mode observations. Success is not full M1 acceptance.
New algebra/covariance and derivative-symbol tests run in the full preflight.

Monitor `outputs/hll_execution.json`, `outputs/check_07.log`,
`source/results/hll_shock_probe/report.json` and authoritative workflow status.
The final `outputs/hll_artifacts.sha256.json` covers all artifacts. Download
root: `results/reana_remote_m1_hll_shock_20261110`. The wrapper's opening
"no-evolution" wording is a copied docstring typo in the immutable packet;
this study explicitly executes eight bounded shock evolutions. The working
wrapper corrects only that comment; its frozen bytes remain in the archive.

All eight complete in 131.92–172.59 s. Format, strict Clippy, 148 release/all-target
Rust tests, 72 Python tests and M0 checks pass. **All 24 HLLD control files are
byte-identical** to the original failure; the HLLD column boost still fails at
5.818394374e-6. The explicit HLL column pair passes at **9.589525564e-14**;
regular HLL passes at **6.836139727e-13**. All four HLL cases pass positivity,
conservation, Bx/seam and original finest-grid reference limits. Final column
row-to-row vx ranges are 1.27701e-12 / 7.46736e-13 (base/boost), compared with
.001680084 / .002194238 for HLLD. This is a strong bounded remedy, not full
M1 acceptance or proof that one HLLD term alone causes the instability.
Next promote the explicitly labelled HLL configuration into the unchanged
bounded wave/loop/shock/vortex suite, then calibration and full gates only
if it passes. HLL's accuracy cost must be measured. Keep the HLLD/default
profiles and failed evidence intact; do not close M1 or #24 yet.

## Uniform response checkpoint (2026-11-10, #24)

`openmhd-m1-transverse-symbol-20261110.1` finished at 02:24:18 UTC (425 s),
UUID `8e21b7ea-c053-41a6-9461-25286b170419`. Frozen packet
`results/reana_submission_m1_transverse_symbol_20261110`, snapshot SHA256
`6a70c0c542ae41773d9d49adc53460b9238119972a727df8a33cfe08335e373c`.
All 96 no-evolution uniform/unlimited probes complete; format, strict Clippy,
146 release Rust tests, 72 Python tests and M0 checks pass. All 204 artifacts
and 303 frozen source files verify. No resolved positive screened eigenmode
in the sampled states/wavelengths; this does not explain or repair the limited
nonlinear shock. The unprojected stationary short-mode control grows.
[Full data/source archive](../tests/reference/m1_column_boost/uniform_symbol/README.md).
The next bounded comparator is explicit two-wave HLL versus unchanged HLLD,
using the original four nx1024 shock cases and unchanged gates. It is not
adopted as a fix. M0 remains accepted; M1/#24 remain open.

## Acceptance campaign checkpoint (2026-11-10)

Current branch: `arm2arm/m1-require-bounded-shock-wave-and-boost-regressi`.
M0 #1/#2 are accepted and closed; #7 and #19–#22 remain open. The owner
requests continuing through genuine acceptance on REANA, within 24 total
cores / 64 GB. Old execution holds below are historical, not current.

**Stopped after a verified required-gate failure at 01:16:53 UTC:**
`openmhd-m1-reporting-campaign-20261110.1`, UUID
`01947a14-a507-4384-a4ca-9533395d08e8`, started **2026-11-09 23:52:22 UTC**.
Frozen submission: `results/reana_submission_m1_reporting_campaign_20261110_v2`,
snapshot SHA256 `b102b766bc5b8e116811924f977e923e097c7ec3cf351647fae3bd2c8c46de04`.
All 391 uploads succeeded before start. This is an exact source snapshot over
`9ce5304`, including the reporting correction and resource allocation below.
It reruns workspace/M0 checks, 20 metadata-parity evolutions, then bounded,
mean-field, calibration and full gates. Do not mutate or restart that snapshot.
Monitor `outputs/execution.json`, `source/results/reana_projection-metadata/report.json`,
and `source/results/reana_m1-campaign/campaign.json` with per-phase run records.
The reporting correction is committed as `9e99b74`; resource allocation is
`cb70b85` (only a clarified help string differs from the executed runner).
Format, strict Clippy, **135 debug Rust / 143 release Rust / 66 Python tests**,
M0 algebra/reference checks and **20/20 reporting evolutions** pass. All ten
comparisons preserve scientific files and every remaining summary field.
All five bounded stages pass, including the 48-case medium wave/loop suite
(1061.49 s). The 24-run nonuniform mean-field suite also completes with all
12 boost pairs passing (56.9 s). **All N128 calibration checks pass**:
both wave frames pass at t=1 (1745.37 / 1915.21 s), with relative B L1
.003164125 and maximum normalized boost residual 2.69922e-14. The vortex
completes at t=.5 in 2574.25 s: normalized mean-B drift .000137274 and
limited-face divergence RMS .0361845 both pass, with positive states and
conserved budgets. Each case used eight threads. Wave peak process RSS is
667,623,424 bytes, vortex 665,624,576. All 24 raw files and exact source hashes verify;
see the [calibration archive](../tests/reference/m1_reana_calibration/README.md).
The matching N64→N128 order is 1.841645, a two-grid diagnostic that does not
replace the full N64/128/256 gate. The full 30-case physics matrix ran
from about **01:10:36 UTC**, with ten workers and two threads per case. The
8× N128 memory forecast and 8-GB reserve determine this allocation within
24 cores / 64 GB. It was stopped with 20/30 runs complete after the N1024
column-jitter Brio boost pair failed: maximum normalized L1 5.81839e-6 versus
1e-8. All 18 Brio runs and two N64 regular vortices completed with passing
state/diagnostic checks. Eight other Brio boost pairs and the completed vortex
pair pass; the regular and column Brio reference/refinement gates pass.
The 112-case wave/temporal matrix never started. Preserve the partial records;
forced-stop campaign JSON can still say running. See the
[new failure evidence](../tests/reference/m1_column_boost/README.md).

**Completed bounded reproduction:** `openmhd-m1-column-repro-20261110.1`, UUID
`1f6ce890-5340-4842-989c-049b780aaddb`, started 01:25:37 and finished
01:28:23 UTC. Frozen packet:
`results/reana_submission_m1_column_repro_20261110`, snapshot SHA256
`65c556d30ed5f171ed608c6fe22c7c26eb2edf1097c84231360e9bf2185ce800`.
All ten uploads succeeded. Four N1024 regular/column base/boost cases use
the exact original Linux binary, SHA256
`ac3e8e895624f80e02e25fb0794c69b1f2a1e2162b697db812b4d46128b8648c`,
two threads each, 8-GB job memory and 600-second case limits. It requires
scientific-file parity with the original cases and reproduces the known
pass/failure pattern. All four cases complete in 124.87–155.06 s; all 24
scientific-file comparisons match byte for byte. The regular pair passes
at 5.70035e-11; columns reproduce 5.81839e-6. A successful reproduction is
not physical acceptance. No compute workflow remains active at this checkpoint.
No solver change has been made for this failure yet. Alternating-row errors
are measured; the responsible operator and mechanism remain to be isolated.
Next: add bounded observation of transverse-mode growth without changing
timesteps, then isolate reconstruction/fluid-flux/curl/projection contributions.
Run all new tests and evolutions on REANA. Do not restart the full matrix
while this required boost regression fails.

### Active bounded row-mode diagnosis (2026-11-10, #24)

The original failure/reproduction packet is committed and pushed as `411d917`.
New bug [#24](https://github.com/arm2arm/openmhd-rs-/issues/24) and a parent
[#7 update](https://github.com/arm2arm/openmhd-rs-/issues/7#issuecomment-6756435422)
record the failed gate. No numerical correction has been claimed.

Two immutable diagnostic workflows were submitted and both are now finished. Their
overlap used at most 16 worker threads / 32 GB. Each has four original nx1024 regular/column
base/boost cases, two threads per case, 600-second case limits, and requires
all 24 original scientific files to remain byte-identical. Their instrumented
sources are separately hash pinned; private source-export commits are only
build/provenance fixtures, not the repository's real revision (`411d917`).

- Snapshot-only: `openmhd-m1-column-trace-20261110.1`, UUID
  `c4ad247d-9fb4-438f-8387-92bcf7edd1bc`, started **01:41:19 UTC**.
  Packet `results/reana_submission_m1_column_trace_20261110`, SHA256
  `4ecb1c27d91d6ba285b208cd47de8bd8b4ff5fb3a353073402f38c1f4a0d1308`;
  all 35 uploads succeeded. Format, strict Clippy, release/all-target workspace
  Rust tests, Python tests, M0 algebra/reference and invalid stride parsing
  pass (143 Rust / 68 Python tests). Four evolutions started at approximately
  **01:48:49 UTC** and the workflow finished **01:51:42 UTC**. All four
  complete in 135.63–165.12 seconds, and all 24 scientific-file comparisons
  match exactly. All 152 snapshot mode records are retained; four intermediate
  raw snapshots are downloaded/hash checked and their 36 coefficients independently
  reproduced with a NumPy row DFT. See the
  [trace archive](../tests/reference/m1_column_boost/accepted_trace/README.md)
  and [inspected plot](images/m1_completion/column_mode_growth.png).
- Frozen-rate decomposition: `openmhd-m1-column-rates-20261110.1`, UUID
  `658b9f65-b318-474c-a81a-71e2ef2da244`, started **01:48:39 UTC**.
  Packet `results/reana_submission_m1_column_rates_20261110`, SHA256
  `488774a9fc2f50764cdce1826ceb881bc2cc0127e194443e4b5eee3897601b9d`;
  all 35 uploads succeeded. Finished **01:59:08 UTC**. Format, strict Clippy,
  145 release/all-target Rust tests, 70 Python tests, release build and M0
  checks pass. All four evolutions complete in 143.11–174.09 seconds; all 24
  original scientific files and all 152 earlier snapshot records match exactly.
  The six current instrumentation sources match the frozen input hashes.
  [Raw rate/source archive](../tests/reference/m1_column_boost/frozen_rates/README.md).

Instrumentation adds `--snapshot-stride 64`: step 1 and each 64th accepted
step, with no new landing times. `--trace-frozen-rates` additionally samples
the immutable production RHS. It groups fluid face exchanges by normal
orientation and measures curl(projected A-rate), curl(unprojected A-rate),
and the same comoving FV-induction target as production. No evolved operator
is changed. Files are under `outputs/column_trace`; `row_modes.json` is reduced
only after each evolution completes. Monitor `outputs/trace_execution.json`,
`outputs/column_trace/report.json`, and authoritative workflow status.
Local download directories use matching `results/reana_remote_m1_column_*` names.

`scripts/plot_column_modes.py` is subsequent local postprocessing, not in
either frozen input. It verifies report/snapshot provenance before plotting.
Both plots pass visual inspection and reproduce byte for byte.
Measured column-mode envelope slopes over t=.04–.09 are approximately 260
per simulation-time unit, versus 100–103 on the regular mesh. The column mode
reaches about 1e-3 by t=.1 and tracks the right-moving slow-shock region.
Investigate the signs of the x/y fluid
contributions before changing fluxes or curl/projection. Positive instantaneous
mode growth on a nonlinear shock is not itself a linear eigenvalue or a proof
of numerical instability. A uniform-state finite-amplitude/linearized mode
probe is a possible next discriminator if the frozen shock rates are ambiguous.
Primary-source hypotheses and links are in `M1_SHOCK_INVESTIGATION.md`.

The rate decomposition finds **negative y-normal-face contributions in all
77 observations** with max |vx mode| >= 1e-10 (range -100.330 to -83.335 per
time unit). The x-normal contribution varies between about -1341 and +1233.
This does not support direct transverse-face anti-diffusion as the source.
The magnetic projected/unprojected/FV rates differ substantially and change
phase as the shock moves; their differences alone do not prove a bad term.
Four raw rate snapshots are hash verified and their acceleration mode rates
independently reduced with NumPy DFTs. Maximum relative-growth discrepancy
is .000339 for the tiny regular modes and 1.80e-8 for columns; local fluid
face-group sums differ from production by at most 1.34e-13.

**No compute job is active after this checkpoint.** Next investigate the
shock-propagation-direction fluid/magnetic feedback with bounded REANA
operator probes. A regular uniform-state Fourier response at the same
aspect ratio (dy/dx=16) can test whether the coupling has an intrinsic growing
short-wave mode before changing any Riemann or projection term. Distinguish
unlimited linear-symbol analysis from the production limited nonlinear shock;
the limiter at a uniform state is not automatically differentiable. Test
perturbation amplitude dependence and retain the unchanged shock control.
Do not insert a transverse shock detector merely from the visual row pattern,
or hide the growth by enforcing symmetry or changing the boost threshold.

[Verified bounded/mean archive](../tests/reference/m1_reana_bounded/README.md).
All 480 medium/mean raw files and their execution source hashes verify.
The medium wave coarse N32→N64 orders are 1.565–1.769; they do not satisfy
or replace the registered finest-three N64/128/256 gate. See the
[medium plot](images/m1_completion/medium_screened_gate.png).
Read-only [wave-mode postprocessing](../tests/reference/m1_reana_bounded/wave_modes/README.md)
checks all 96 medium wave snapshots. Phase supplies 65–84% of N64 fixed-mesh
final squared B error; this identifies a leading component, not its numerical
cause. The new analysis/plot scripts change no solver or acceptance threshold.
See [the immutable verification packet](../tests/reference/m1_projection_metadata/README.md).

**Completed performance study:** the cache code in **`9ce5304`** exactly
matches the tested numerical sources. Format, strict Clippy, 133 debug and
141 release Rust tests, 64 Python tests and M0 checks pass. All 11 performance
evolutions complete and seven comparisons match scientific files byte for
byte. All 52 downloaded scientific-file hashes verify. Evolution speedups
are 1.068–1.106 for four serial baseline/cache pairs; N128 threading at
4/12/24 gives 1.367/1.479/1.382. These are single shared-node samples.
See [the archived evidence](../tests/reference/m1_projection_cache/README.md)
and [the performance plot](images/m1_completion/projection_cache.png).

The parent cache workflow `openmhd-m1-cache-campaign-20261110.1`, UUID
`9122c09e-93da-4bda-9f57-a534713cf4d3`, is **stopped** (23:51:52 UTC), before
the replacement started; there was no compute overlap. Its four short
numerical stages pass. 42/48 medium cases completed with positive states and
conserved budgets; six cases and final boost comparisons remain incomplete.
This is not a medium-stage pass. Raw remote and local partial records remain.
Its original snapshot SHA256 is
`c559771dac2006da0bc84f176b2146a80e890e2dfe03753f32c3bceacb2f9939`.
Force-stop can leave local execution/campaign JSON labelled running; use
REANA's authoritative workflow status when interpreting those partial files.

**Reporting defect:** screened summaries falsely label the factor shift as
1e-8, although the matrix uses κ=1 and `projection_screening` correctly
records it. The verified correction stores/reports the actual factor coefficient and
add solver/CLI tests plus `run_projection_metadata_check.py` (20 small matched
evolutions; only that field may change). Keep old outputs immutable and
annotated. The correction changes metadata, not the executed equations.

The measured cached N128 **standing** wave costs 91.60 evolution seconds to
t=.02, suggesting about 76 minutes to t=1 before setup. Calibration instead
uses a travelling wave, so this is a cost warning, not its measured runtime.
The replacement prospectively uses two-hour calibration/24-hour full-case
caps, with worker-count-aware stage caps. Calibration uses three cases with
eight threads each; full matrices use memory-bounded workers and remaining
threads within 24 cores total. Physical targets and thresholds stay unchanged.

The [candidate audit](M1_CANDIDATE_AUDIT.md) separates every engineering
departure from the source formalism; it is an assistant implementation audit,
not an independent review. The archived prescribed-flow packet's 12 file
hashes, 32 completed evolutions, 16 boosts, 16 comoving gates and two refinement
gates verify. A source-dependency review finds the serial transport arithmetic unchanged;
see the audit and `tests/reference/m1_completion/prescribed/applicability_20261110.json`.
This retains historical evidence, not a new full-ladder binary reproduction.

`openmhd-m1-campaign-20261109.1` **failed at numerical launch** at 22:57 UTC:
the pinned image lacks `/usr/bin/time`. Format, strict Clippy, 133 debug Rust
tests, 141 release Rust tests, 61 Python tests and M0 checks passed first.
See [its preserved preflight evidence](../tests/reference/m1_reana_preflight/README.md).
The Linux `wait4` resource wrapper replaces that dependency and passes
success/failure/memory tests in the cache campaign. Its RSS is the maximum
individual process, not the concurrent-worker sum. Memory scheduling reserves
8 GB and forecasts eight times the largest N128 peak per N256 worker.

## Verified follow-up reporting correction (2026-11-10)

A source audit found that `evaluate()` only emits mean-field refinement rows
for the three historical `PROFILES`, even when `--candidate-mean` evolves the
new quadratic profile. Per-run and pair errors are still computed; this is
an omitted-summary-row defect, not a numerical evolution change. Commit `c6cda9d`
derives additional smooth profiles from measured pairs, preserve
historical rows, and require the candidate's four registered spatial/time
observation series in the campaign reducer. No new physical-order target is
introduced for roundoff-sensitive boost residuals.

Both added regressions pass within **68 Python tests on REANA**.
The original completed mean summary confirms zero candidate refinement rows.
Its 24 runs and 12 pair measurements are preserved in `m1_reana_bounded/mean`.
The original report remains unchanged. A verified copy restores only its
`mean_refinement` field; all other fields are identical and the four candidate
spatial/time observations are present. No MHD evolution was repeated.

The supplemental workflow **finished successfully at 01:17:44 UTC**:
`openmhd-m1-mean-report-audit-20261110.1`, UUID
`9fb39416-290c-4028-b199-8aa0e0248d18`. Frozen input directory:
`results/reana_submission_m1_mean_report_audit_20261110`; snapshot SHA256
`becbff01b4671d52de3e597093ded7d7f3bcc5d862d241318961ce5e61874dc5`.
All six uploads succeeded. It ran Python regressions and restored only the
missing refinement observations from the original hash-verified summary.
No MHD evolutions; 2 GiB limit. Its private export Git commit exists only
for unit-test provenance fixtures; the actual source revision `c6cda9d` and
all 80 source/config hashes are pinned separately. It started after the main
compute job was authoritatively stopped; no resource overlap occurred.
[Verified supplemental archive](../tests/reference/m1_reana_bounded/mean_reporting_audit/README.md).

## Earlier campaign submission (2026-11-09, 22:45 UTC)

Current branch: `arm2arm/m1-require-bounded-shock-wave-and-boost-regressi`.
The owner explicitly requests continuing until M0/M1 gates pass, using
REANA for tests and long runs. M0 #1/#2 remain accepted and closed; M1 and
#19–#22 remain open. No numerical solver changes accompanied this earlier snapshot.

The local four-stage gate passes in 71.1 seconds: 51 evolutions complete,
two literal planar controls reproduce the pressure failure. Exact source,
raw measurements and hashes are archived under `tests/reference/m1_bounded_gate`;
see the [plot](images/m1_completion/bounded_screened_gate.png).

`openmhd-m1-bounded-20261109.1` passed format, strict Clippy, 133 workspace
Rust tests, 57 Python tests, release build and M0 algebra/reference checks.
Its 30-second local-case budget was too small on REANA: nx512 × ny8 shock
and both N32 jittered vortices timed out. The workflow was stopped with raw
workspace retained; 16 N32 medium wave records also completed before stopping.
They took 20–49 seconds, around 2.5–3 times local costs. No timeout is a pass.

`openmhd-m1-campaign-20261109.1` started at **22:45:55 UTC** from the frozen
`results/reana_submission_m1_campaign_20261109_v5` packet, snapshot SHA256
`29e467e6a0af19cc2afd59701c7132e9f813d71bdaae704bef13bdccafcd828d`.
It reruns all checks (also release/all-target Rust tests), then short/medium
gates, candidate mean-field boosts, N128 memory/time calibration, the full
30-case physics matrix and 112-case physical/temporal wave/loop matrix.
New remote budgets: short cases 120 s, medium cases 1800 s; local defaults
stay 30/600 s. A failed short stage now prevents medium execution.
At most 24 serial simulations and 64G memory; calibration may reduce workers.

Monitor `outputs/execution.json` and, once present,
`source/results/reana_m1-campaign/campaign.json`, then each phase's `runs.json`.
The campaign must not be called accepted merely because its workflow finishes.
The plan, historical prescribed-loop evidence and paper/code audit remain
part of final M1 review. Preserve failed records and physical thresholds.
The snapshot contains the current uncommitted runner changes over `3cbd1d5`;
commit them after the new remote checks, then publish verified result links.

## Updated merge instruction (2026-11-09)

Latest instruction: continue until M0/M1 acceptance gates pass and close
their issues only with measured evidence. Use REANA for tests and long runs,
within 24 total cores and 64 GB. Work on
`arm2arm/m1-require-bounded-shock-wave-and-boost-regressi`. M0 issues #1/#2
are already closed under their documented AI review. The screened quadratic
candidate passes the combined **short-only** gate; the medium and full
matrices remain required. See [results](M1_SHOCK_INVESTIGATION.md#bounded-m1-gate-for-the-screened-candidate-2026-11-09-issue-22)
and [the plan](M1_FULL_VALIDATION_PLAN.md). New REANA validation is authorized;
the older execution hold below applies to the archived stopped workflows.

The user explicitly requests merging this development branch into main after
being informed of the remaining Bx failure. Merge the tested implementation
and evidence as a development checkpoint; full M1 acceptance remains pending.
This supersedes earlier "do not merge" instructions in this historical handoff,
not the physical gates. Keep #7/#19–#22 open and long REANA jobs stopped.
See the [updated merge contract](M1_MERGE_PLAN.md).

## Latest bounded candidate result (2026-11-09)

The new opt-in `--accelerated-projection` caches a sparse Cholesky
preconditioner for the existing projected-rate profiles. It changes neither
the projection objective nor its original residual tolerances. The quadratic
profile completes both nx512 jittered Brio base/boost cases to t=.02 in
7.64/7.92 seconds, minimum accepted pressure .0467862, budgets <3.74e-15,
zero state rejections, passing boost agreement. All 40 bounded controls now
complete. Its four N8/16/32 t=.02 wave families have B/velocity orders
1.909–1.953; the linear-curl comparator still fails two velocity screens.
Matched N32 jittered waves are about 10 times faster. Across 38 completed
old/new pairs, physical states agree within 2.8e-13, A within 2.33e-10.
Serial and 1/2/4/24-thread states/diagnostics/counters agree bitwise.

This is a working short-time **engineering candidate**, not the literal paper
algorithm or full M1 acceptance. The fine shock Bx error is .0457136 initially
and .0549856 finally, versus the unchanged 1e-8 gate. Do not merge main or close
#7/#19–#22. Next investigate the transverse curl representation (#21), using
this faster comparator for bounded controls, then the original full physical
gates. Long REANA jobs remain stopped. Preserve all failures and thresholds.

A positive, quadratic-consistent Laplacian was also implemented independently
and passed standalone moment/maximum-principle/Fourier checks, but its coupled
nx512 shock failed at .00113439. That evolution profile is removed; only its
measurement API/probe remains. No retained evolution uses this dissipation.
See [measured results](M1_SHOCK_INVESTIGATION.md#measured-projection-retry-2026-11-09)
and the [exact source/data archive](../tests/reference/m1_projection_retry/README.md).
Checks pass: 138 release Rust, 43 Python and 13 M0 tests, strict Clippy, format
and reference integrity. faer 0.22.6 is pinned, MIT, Rust 1.84 minimum;
its Rayon feature is disabled. Default solver behavior remains unchanged.

## Previous rejected dissipation result (2026-11-09)

The user requests a deeper solution and completion. Optional paper Eq. (77)
was implemented in two separately named trial profiles: successive raw-LS and
direct quadratic Hessian trace, alpha=.2 primary, .1/.3 short sensitivities.
37 local evolutions take <=3.52 seconds each; no long job is resumed. Both
variants stabilize nx256 to t=.02, but both fail nx512 before .000824, base
and boost. The unchanged Bx gate still fails. A new regular-mesh Fourier proof
shows that the quadratic trace amplifies high-frequency modes despite passing
polynomial/smooth tests. Both evolution profiles are rejected and removed.
Do not propose either archived profile as a validated repair.

Retained changes: tested second-derivative measurement API and Fourier-sign
regression, accepted-step diagnostic CSVs, reproducible analysis and plot,
complete failed source/data archive. 134 Rust/42 Python/13 M0 tests, format,
strict Clippy and reference integrity pass. Original jittered baseline CSVs
are byte-identical. See [full findings and next decision](M1_SHOCK_INVESTIGATION.md#measured-dissipation-result-both-candidates-rejected-2026-11-09)
and [archive reproduction](../tests/reference/m1_paper_dissipation/README.md).
Next work must establish the discrete magnetic-energy damping property before
another diffusion evolution. Pressure, initial Bx representation, and full
wave/mean-field boost gates remain distinct problems. #19–#22 remain open;
M1 is not ready to merge. No pressure floor, energy reset or relaxed gate.

## Resumed session (2026-11-09)

The user requested bug reports on 2026-11-08 and explicitly resumed development
with "continue" on 2026-11-09 (Europe/Berlin). The pause is lifted for local
development. Preserve the short-test constraint and paper formalism; all long
REANA workflows remain stopped.

The next-session order under [#7](https://github.com/arm2arm/openmhd-rs-/issues/7) is:

1. [#18: checkpoint current source and evidence](https://github.com/arm2arm/openmhd-rs-/issues/18).
2. [#19: audit the paper-to-code interfaces](https://github.com/arm2arm/openmhd-rs-/issues/19).
3. [#20: isolate cell 253's pressure failure](https://github.com/arm2arm/openmhd-rs-/issues/20).
4. [#21: resolve the jittered Bx representation/gate conflict](https://github.com/arm2arm/openmhd-rs-/issues/21), separately from pressure stability.
5. [#22: pass bounded regressions before longer validation](https://github.com/arm2arm/openmhd-rs-/issues/22).

The accumulated code is now checkpointed in `4c5341a` (Riemann completion),
`76470eb` (mesh derivatives/threading), `b5bea83` (M1 solver profiles/tests)
and `5175240` (measurement/REANA tooling). A fresh local check passes 127 Rust,
41 Python and 13 M0 tests plus format, strict Clippy and reference integrity.
The retained paper-audit source is byte-identical apart from this handoff.
All 126 files named by study archive manifests verify. The reports embed
measured failures, reproduction commands and archive hashes; their initial
uncommitted status is historical. The paper-source comparison
still fails both jittered short shocks at t=.00334288704. All long REANA jobs
remain stopped; full M1 acceptance and merge remain blocked by numerical gates.

Checkpoint issue #18 is closed: `e17cf9b` publishes the source/evidence with
the preceding four component commits. New face-assembly and geometry probes
retain the original solver. The stationary first-step reconstruction matches
the production Q/A update bit for bit. Faces 1050 and 1051 explain 99.4% of
cell 253's initial energy loss; both use HLLD and agree between state/flux EMFs.
The optional mixed-Hessian paper trial fails earlier (t=.00295085417) and is
removed; its exact source/data remain archived. Seven of eight short geometry
controls complete. At fixed nx256, increasing ny4 to ny8/16 permits t=.01
completion, but Bx errors remain .110146/.0821556. Original ny4 still fails.
See [the new measured interpretation and plot](M1_SHOCK_INVESTIGATION.md).
The subsequent exact-pattern controls separate local geometry from row count:
repeating the original stretched four-row pattern in taller boxes still fails
at t=.00334, while compressing the same perturbation pattern reaches t=.01.
Repeated effective derivative rows agree within 3.87e-14 relative L1.
Compression removes the 253/255 face and changes neighboring magnetic
reconstruction; cell 253's initial dp changes from -35.3551 to +3.34461.
This localizes sensitivity to shape/topology at the magnetic discontinuity;
it does not isolate aspect ratio alone or fix the original benchmark.
The original physical CSVs reproduce byte for byte; no library solver changes.
All six configurations plus face audits take 3.16–11.27 seconds each, no
timeouts. Final checks pass 129 Rust, 42 Python and 13 M0 tests, strict
Clippy/format/reference integrity. See the [pattern evidence](../tests/reference/m1_pattern_controls/README.md)
and [plot/interpretation](M1_SHOCK_INVESTIGATION.md#measured-repeated-pattern-result).
Next focus on discontinuity reconstruction and conservative energy/curl
coupling under the verified source formalism. Keep the original ny4 benchmark
and Bx gate; #19–#22 remain open, and no long workflow is restarted.

The next frozen audit tests the paper's optional primitive fit through the
central value. It passes operator tests but changes cell 253's initial dp from
-35.3551 to -35.4438; zero magnetic face slopes worsen it to -61.9306. No new
evolution profile is added. Counterfactual Riemann inputs isolate the neighboring
cell values: analytic Bx at cells 254/255 leaves dp=-30.6001, analytic By gives
-.0320103, both give +5.89480. These inputs are inconsistent with stored A and
never evolved; they diagnose, rather than repair, the coupling. Independent
kink-residual/normal-equation calculations reproduce the neighboring initial B
to about 1e-14. The broadened By jump dominates this initial energy drain;
Bx-only correction would be insufficient. Source-supported broadening itself
is not a coding error. Robust conservative energy/curl coupling on the original
geometry remains the problem. See [results and plot](M1_SHOCK_INVESTIGATION.md#measured-reconstruction-input-result)
and [reproducible archive](../tests/reference/m1_reconstruction_inputs/README.md).
The final 80 frozen evaluations take 5.43 seconds; 131 Rust/42 Python/13 M0
checks plus strict Clippy/format/reference integrity pass. Production solver,
all gates and stopped long workflows are unchanged.

**Historical handoff:** subsequent local work added the [M0 source audit](PAPER_IMPLEMENTATION_SPEC.md), [kinematic pilot](KINEMATIC_2D.md) and [experimental coupled planar reference](COUPLED_2D.md). Issue #6 adds a separate [general 2.5D endpoint implementation](VECTOR_POTENTIAL_REFERENCE.md). Issue #7 has [historical incremental results](M1_WAVE_LOOP_RESULTS.md) and a [continuation with full wave spatial/temporal measurements and prescribed-flow loops](M1_COMPLETION_RESULTS.md). The named signal-completion comparator improves boost agreement but still fails the N256 fixed-grid standing-wave pair; spatial and temporal limitations remain explicit. Consult README/AGENTS and the continuation's labelled AI review for current status; the planning-only descriptions below describe the original handoff.

Current continuation (2026-11-08): the separately named `bulk-frame-heun-v1`
adds fully reevaluated stages for fixed/rigid meshes. See [its contract](M1_HEUN_INVESTIGATION.md)
and [measured status](M1_HEUN_RESULTS.md). New REANA submissions use up to 24
serial cases concurrently and a 64 GB test-job memory limit. Existing frozen
full matrices retain their original resource settings.

At the user's request, a bounded within-simulation threading experiment now
adds `vector-potential --threads 1..24`, default 1. The REANA N64/N128 scaling
runs have byte-identical physical outputs across 1/4/12/24 threads; N128 wall
time is 72.7/25.3/15.2/16.7 seconds. Twelve threads are fastest overall in these
measurements. The N256 24-thread full-wave demonstration completed in 49.1
minutes (earlier serial: 148.0 minutes, different checkpoint clocks), with
positive sampled states and budget residual <=1.171e-12. Its initial CSV
matches the frozen serial reference. See
[threading results and evidence](THREADING_RESULTS.md). This user-authorized
experiment does not imply M1 acceptance or completion of the MPI/3D milestone.

The subsequent [auxiliary-projection study](M1_AUXILIARY_RESULTS.md) adds
`bulk-frame-heun-spline-v1`. All 80 REANA cases and 16 boost pairs complete;
limited jittered standing-wave time slopes improve from 1.729/1.598 to
2.000/2.011. Unlimited magnetic slopes remain 1.704/1.668, and the full
physical/spatial gates remain open. All 102 Rust/29 Python checks pass;
the original profiles are unchanged. Raw outputs and source are archived.

## What the user wants

Latest execution constraint (2026-11-08): the user requested short tests for
development and stopping unnecessary long studies. All four long REANA
workflows are stopped: original 28/112 completed, candidate 100/184,
spline-full 64/112, physics 14 completed + 6 failed of 24. Partial records/logs
are saved locally and raw remote workspaces retained. Use
`scripts/run_shock_repro.py` (four cases, measured .87 seconds) and targeted
unit tests while developing the coupling fix. Hold new long submissions;
passing this short screen does not satisfy M1 or authorize a merge. Report
the candidate's measured short-test results before considering long validation.

The current user request is to pass M1 gates and then merge to main; see
[the merge contract](M1_MERGE_PLAN.md). The 112-case spline wave/loop study
was stopped after 64 completed cases. A [general shock/vortex driver and measurement contract](M1_PHYSICS_PLAN.md)
now implement the M0 Athena comparison packet, including periodic polygon
overlap and a passive shock characteristic-travel diagnostic. Sixteen small
execution probes complete and all eight boost pairs pass, but jittered Brio
Bx diagnostics fail. These probes are not the registered resolution ladder,
and do not establish M1 acceptance. Preserve all failures and historical
profiles; merging is still conditional on the full gates.

The full remote physics study subsequently failed all six jittered Brio
cases before t=.004. See [the diagnostic investigation](M1_SHOCK_INVESTIGATION.md):
smaller dt converges to the same failure, and two tested reconstruction
comparators failed and were removed after archiving. The retained
`--trace-energy`/accepted-state observer and cell/stage error context do not
change physical outputs. The fluid/curl energy mismatch remains unresolved;
do not describe either rejected comparator as a fix or relax the M1 packet.

A subsequent shared-vertex face-normal comparator also fails the short shock
screen (t=.00333372, .85 seconds for four cases), despite eliminating the
initial Riemann face-sum divergence to roundoff and passing seven bounded
operator/Heun checks. It too is archived and removed. See
[the probe evidence](../tests/reference/m1_face_normal_probe/README.md).
The energy-transfer mismatch persists; no accepted M1 fix or merge is ready.

The next initial-state least-squares probe shows that the historical curl
cannot exactly represent the FV induction rate on these jittered meshes:
nx256 retains a .4718 relative rate residual after a converged normal solve.
A separate `bulk-frame-heun-projected-v1` candidate projects each stage's
comoving FV rate onto that curl range. It completes all four short shocks
to t=.01 in 2.62 seconds with positive pressure, conservative budgets and
both boost pairs passing. The jittered Bx error remains .112966 versus the
unchanged 1e-8 gate: the overall short screen still fails. Retain this as a
partial stability improvement only; long jobs stay stopped. See the
[contract and results](M1_SHOCK_INVESTIGATION.md) and
[exact experiment archive](../tests/reference/m1_projected_rate/README.md).

The subsequent initial-curl audit isolates the remaining Bx error. Independent
70-digit free-intercept fits reproduce the Rust gradients. Jittered Brio
initial max Bx errors at nx256/512/1024 are .160355/.149907/.284451; errors
outside stencils spanning an Az slope change are <=3.34e-16. A smooth 1D
control also has nonzero transverse error. This implicates the chosen spatial
reconstruction rather than roundoff; it does not prove the entire code correct.
All 12 probes take 2.29 seconds. No production algorithm or gates change;
see [the audit evidence](../tests/reference/m1_curl_audit/README.md).

The [deeper interpretation](M1_SHOCK_INVESTIGATION.md#root-cause-interpretation-two-separate-errors)
separates the worst initial-field cell 640 from the first pressure-failure
cell 253, which starts with the correct B. Cell 640's fit matrix has condition
number 1.46; inventing a transverse slope reduces the least-squares objective
by 49.25%. The exact neighbour contributions explain its Bx error. A new
figure and reproducible analysis script use only preserved measurements.
The paper cross-check supports the selected affine-fit formula but does not
establish machine-precision Bx for our jitter family. No numerical changes,
gate changes or new evolutions accompany this explanation.

The subsequent bounded development adds `bulk-frame-heun-quadratic-v1`: a
quadratic double-neighbour A/phi derivative coupled to the existing projected
rate. Eight short trials and six t=.02 extensions complete. At t=.02 on the
jittered nx256 shock, the retained candidate reduces max Bx error from .107515
to .0604426 and has minimum p=.0493331, with zero state rejections and passing
budgets/boosts. A concurrent-Hessian face-slope variant is rejected and removed
after giving Bx error .0701692. The 1e-8 gate still fails; this is partial
progress, not a fixed/accepted solver. The wider quadratic fit improves smooth
convergence order but has larger absolute 2D errors on the small ladder and
costs more per run. See [the measured tradeoffs](M1_SHOCK_INVESTIGATION.md) and
[all source/data versions](../tests/reference/m1_quadratic_curl/README.md).
126 Rust, 41 Python and 13 M0 algebra tests pass; strict Clippy/format/reference
checks pass, and ten historical cases retain byte-identical physical outputs.
All long jobs remain stopped. No commit or merge is made by this continuation.

The user's latest steering explicitly requests the Springel–Mayer–Pakmor
formalism. The independent face-integral prototype was removed and archived.
A matrix-rank audit finds a severe numerical representability constraint for
the current jittered Bx gate; it does not authorize changing that gate or
replacing the paper method. See the
[paper-source comparison](M1_SHOCK_INVESTIGATION.md#paper-source-comparison-measured-result).
`paper-state-emf-v1` isolates the literal Eq. (69) state product in both
historical endpoint stages, with linear cell curl and original gauge. Its
unit/uniform tests pass. Both regular short shocks complete, but both jittered
shocks fail at t=.00334288704 (matched default: .00336336379), still at cell
253. The pressure mismatch is unresolved. Do not continue independent
projection/face-integral method development under the paper's name.
127 Rust tests, strict Clippy and formatting pass; ten historical wave/loop
cases remain byte-identical. Exact source and raw observations are in
[m1_paper_audit](../tests/reference/m1_paper_audit/README.md). The latest work
is uncommitted; no full acceptance or merge is claimed.

Develop a new **Rust** scientific HPC code implementing the new **moving-mesh magnetic vector-potential ideal-MHD** method presented in **Springel, Mayer & Pakmor (2026), arXiv:2609.35989**. The target is an independently developed, scientifically validated, **hybrid MPI/Rayon** code runnable on the user's **Mac Pro** for local development and later on Slurm clusters for multi-node scaling. The initial discussion also considered C++ with MPI/OpenMP; the user explicitly preferred the additional **Rust implementation** and asked to preserve the plan in GitHub for future coding.

User repository: **https://github.com/arm2arm/openmhd-rs-**. The trailing hyphen in `openmhd-rs-` is intentional and part of the actual repository name. It is **public**, with an existing **MIT** license; the user explicitly wants public visibility.

## Conversation decisions in chronological order

1. Asked for the main findings of arXiv:2609.35989. Discussion centered on a new vector-potential, moving-Voronoi mesh approach to ideal MHD, aiming for stable magnetic-field evolution and Galilean invariance.
2. Asked whether we could implement the physical method using MPI/OpenMP. Initial engineering proposal used C++20, finite-volume ideal MHD (HLLD as candidate), moving Voronoi meshes, second-order integration, 3D, MPI/OpenMP, refinement and local timesteps, with quantitative validation and Slurm benchmarks.
3. Asked whether it could be written in Rust. Agreed target: Rust 2024 + `mpi`/rsmpi + Rayon, `f64` scientific precision, HDF5/Slurm, 2D serial validation first and MPI/3D later. Rayon replaces OpenMP for native Rust loops; MPI provides multi-node scaling.
4. Asked to create a GitHub project and save the plans. The repository `arm2arm/openmhd-rs-` was created by the user; the assistant published planning documentation and 17 GitHub issues to `main`.
5. Confirmed project should be **public**, not private. README and docs describe the planning-only state; existing MIT LICENSE was detected and preserved.
6. On Nov 3, 2026, asked to move this ChatGPT discussion to **Codex on the user's Mac Pro**. This file and root `AGENTS.md` enable an effective **project handoff** through Git; they do not migrate the actual conversation thread, Codex session history, or the Mac's local filesystem.

## Current GitHub state at handoff

- Repository: `arm2arm/openmhd-rs-`, default branch `main`, public.
- Planning docs: `README.md`, `docs/ROADMAP.md`, `docs/NUMERICS.md`, `docs/ARCHITECTURE.md`, `docs/VALIDATION.md`, `docs/PARALLEL_HPC.md`, `docs/REFERENCES.md`, `docs/DECISIONS.md`, `docs/ISSUE_BACKLOG.md`.
- Contribution policy in `CONTRIBUTING.md`; example Slurm script in `examples/slurm/hybrid.sbatch`; GitHub issue templates.
- Issues #1–#17 cover M0 numerical-method extraction, M1 serial solver, M2 3D moving mesh, M3 MPI/Rayon, M4 adaptivity/physics, M5 scientific release, and governance.
- **No validated or compilable MHD solver has been implemented.** The Slurm script is illustrative, not runnable at this stage.

## Scientific requirements that must not be simplified away

- The equation `B = B_mean + curl(A)` identifies the strategy, **not an entire implementation**.
- M0 must extract the **exact published discrete equations**, including gauge choice, smooth auxiliary velocity, terms/signs, cleaning, mesh/timestep coupling, treatment of periodic mean magnetic flux and any positivity/energy subtleties. Existing planning docs are not authoritative transcriptions.
- Verify and document the exact relation between vector potential, the solver's discrete curl, independent `div(B)` diagnostics, and conservation. Avoid an unjustified blanket assertion of machine-zero `div(B)`.
- The numerical scheme must pass **Alfvén wave, magnetic flux-loop advection, Brio–Wu shock tube, Orszag–Tang, 3D field advection/blast, MRI and magnetized-collapse** tests as the relevant physics modules become available.
- Numerical targets should be declared in advance, assessed via resolution studies and compared with the paper where possible. Reproducibility includes configs, code revision, hardware/compiler/MPI/runtime and plotted error data.
- MPI domain decomposition, cross-boundary face flux conservation, Rayon race-free face reductions, geometry rebuilds after mesh movement, per-cell timesteps and adaptive remapping are separate milestones, not trivial add-ons.
- Avoid reusing/copying AREPO source without checking licensing, provenance and whether the user's requested independent method warrants it.

## Proposed order of work

**M0 — scientific specification (#1 and #2):** Read the full primary paper; produce a detailed equation-by-equation, stencil-by-stencil, and stage-by-stage implementation plan. Resolve 2D embedding, boundary conditions and mean field. Predeclare benchmark reference curves/tolerances.

**M1 — serial Rust baseline (#3–#7):** Introduce a Cargo workspace, EOS/conservative states, robust HLLD-style moving-face fluxes, 2D Voronoi mesh, paper-specific A evolution and diagnostics, with analytic/small benchmarks.

**M2 — 3D moving mesh (#8–#9):** Real 3D dynamic Voronoi geometry, smooth velocity/gauge, full moving-face operations, 3D published cases.

**M3 — hybrid HPC (#10–#12):** rsmpi ranks, ghost halos and geometry, consistent face owners, Rayon kernels and Slurm strong/weak scaling with correctness checks.

**M4 — advanced physics (#13–#15):** Mesh refinement/derefinement, local timesteps and optional gravity/magnetic collapse.

**M5 — scientific release (#16):** Documented numerical tests, open reproducibility data, performance report and deviations from the paper.

## First Codex session

Open this repository locally on Mac Pro and give Codex the prompt in `codex/FIRST_TASK.md`. Start at M0, GitHub issue #1. Treat the full paper as authoritative for numerical claims. Do **not** invent code or claim the solver already exists.

## Open questions for a later design decision

- Which Rust Voronoi geometry implementation survives 3D periodic moving-topology robustness tests?
- Should M1 use 2D unstructured Voronoi from the start or a temporary, strictly labeled structured-mesh verification kernel?
- Exact face flux method and fallback, reconstruction and limiting choices compatible with the paper.
- Gravity and cosmological coordinate extensions: optional and out of initial M0/M1 scope.
- Mac Pro architecture (Intel or Apple Silicon), macOS version, local compiler/MPI availability; obtain from the machine rather than guessing.
