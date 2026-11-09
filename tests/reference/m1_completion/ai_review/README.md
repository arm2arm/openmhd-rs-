# Independent AI review probes


**Final status:** the bounded numerical/archive/figure/document AI review is
complete. All current full-study executions are finished; scientific wave gates
still fail and full M1 is not accepted. The final record is
`final_review_provenance.json`; `candidate_archive_report.json` and
`final_figure_report.json` complete the archived checks. Earlier sections and
provenance files retain their historical checkpoint scope: their pending
execution/archive/figure remarks are superseded by this final status.

These small probes were developed independently of the implementation tests.
They are an **AI review**, not human peer review or full physical validation.
The review's source hashes, compiler and exact executed commands are in
`provenance.json`; `archive_sha256.json` hashes this packet.

`hll_boundary.rs` and `hll_boost.rs` expose the rejected HLL-average
completion's outer-wave discontinuity. `rejected_hll_core.rs` is an exact copy
of the core from the frozen rejected checkout, included so the counterexample
remains reproducible after that experimental profile was removed. Its source
belongs to this MIT-licensed repository; no third-party code was imported.
The source's original historical `riemann` entry point is also preserved there.

`signal_boundary.rs` and `signal_boost.rs` repeat the same counterexamples
against the supported signal-weighted convention. `signal_random.rs` uses
a deterministic xorshift seed and 10,000 varied admissible faces, checking
unchanged conservative/induction fluxes, reversal and joint boosts of the
complete A source. The maximum source reversal and boost errors were
`3.927414e-15` and `5.884182e-15`, respectively. This is a bounded numerical
test, not a proof of general coupled Galilean invariance.

From the repository root, using the pinned Rust toolchain:

```sh
mkdir -p /tmp/openmhd-ai-review
cargo build --release --locked -p mhd-core
rustc --edition=2024 --crate-name mhd_core --crate-type rlib -O \
  tests/reference/m1_completion/ai_review/rejected_hll_core.rs \
  -o /tmp/openmhd-ai-review/libmhd_core_hll.rlib
for probe in hll_boundary hll_boost; do
  rustc --edition=2024 tests/reference/m1_completion/ai_review/$probe.rs \
    --extern mhd_core=/tmp/openmhd-ai-review/libmhd_core_hll.rlib \
    -o /tmp/openmhd-ai-review/$probe
  /tmp/openmhd-ai-review/$probe
done
for probe in signal_boundary signal_boost signal_random; do
  rustc --edition=2024 tests/reference/m1_completion/ai_review/$probe.rs \
    --extern mhd_core=target/release/libmhd_core.rlib -L dependency=target/release/deps \
    -o /tmp/openmhd-ai-review/$probe
  /tmp/openmhd-ai-review/$probe
done
cargo test --locked -p mhd-core --test completion \
  -p mhd-vector-pot --test completion --test transport
python3 scripts/test_m1_wave_loop.py
python3 scripts/test_m1_archive.py
python3 tests/reference/m1_completion/ai_review/integrity_probe.py
```

The corresponding `.log` files retain actual output. The large spatial,
temporal and prescribed-flow studies are separate evidence packets; their
completion or scientific acceptance is not implied by these probes.

## Actual standing-wave face diagnosis

`standing_faces.rs` reconstructs the limited primitive face states and auxiliary
velocity of the actual N64 regular standing-wave benchmark using the public
solver APIs. Fixed/rigid preparation uses the initial cached derivative stencil,
matching production. Sources are `electromotive - u cross B_face`, at the left
incident cell's auxiliary velocity. Wave locations are separately recomputed
from the input states as a diagnostic; the production function chooses the flux.

The ordinary CFL base evolution to t=.25 matches all 4096 archived cell primitive
states exactly. The reference CSV is already archived in the historical packet.
The source scan shows an initial stationary rotational-wave boundary (`SAL=0`,
`Bn=1`): perturbing one actual face's left normal velocity by one floating-point
bit changes the historical completion source by `2.360845816e-5`, while the gas
flux changes by `2.220446049e-16`. Signal completion changes by `2.428613e-17`.

A separate **common-dt diagnostic**, `dt=1e-4`, finds an actual evolved base/boost
pair at t=.0001: face 461 has `SAL=0` versus `-2.220446049e-16`; its historical
source differs by `1.824959594e-5`, while its transformed gas flux differs by
`2.220446049e-15`. Signal completion on those exact face inputs differs by
`5.828670879e-16`. `standing_face_fixture.rs` preserves this compact example.
After the second common-dt step, the old pair's maximum B-component difference
is `7.325292262e-9`, versus `2.775557562e-17` for the signal-profile control.

Negative controls are retained in the log: direct initial face reversal and
joint boosts produce only roundoff changes; the separately initialized boosted
pair has roundoff source differences; both profiles have exactly zero B
pair difference after one `dt=1e-6` step; the t=.25 face scan has roundoff
perturbation sensitivity. Thus the benchmark contains a roundoff-sensitive
rotational-wave completion and the controlled change removes the demonstrated
sensitivity. This does **not** trace the first branch of the original adaptive
CFL trajectory or prove exclusive causation of its full nonlinear t=1 error.

```sh
cargo build --release --locked -p moving-mesh -p mhd-vector-pot
rustc --edition=2024 -O tests/reference/m1_completion/ai_review/standing_faces.rs \
  --extern mhd_core=target/release/libmhd_core.rlib \
  --extern mhd_vector_pot=target/release/libmhd_vector_pot.rlib \
  --extern moving_mesh=target/release/libmoving_mesh.rlib \
  -L dependency=target/release/deps -o /tmp/openmhd-ai-review/standing_faces
gzip -dc tests/reference/m1_wave_loop/bulk/snapshots/alfven_bulk-frame-v1_v1.0_j0.0_fixed_n64_base/checkpoint_0.25000000.csv.gz \
  > /tmp/openmhd-ai-review/quarter.csv
/tmp/openmhd-ai-review/standing_faces /tmp/openmhd-ai-review/quarter.csv
rustc --edition=2024 -O tests/reference/m1_completion/ai_review/standing_face_fixture.rs \
  --extern mhd_core=target/release/libmhd_core.rlib -L dependency=target/release/deps \
  -o /tmp/openmhd-ai-review/standing_face_fixture
/tmp/openmhd-ai-review/standing_face_fixture
```

## Completed prescribed-flow evidence

`prescribed_check.py` independently checks archive and source provenance, all
32 original raw run hashes, complete snapshots, analytical A/B norms and
magnetic energy/A integral/extrema without importing the production measurement
code. It also checks all 16 comoving A/B drifts and all 16 boosted pairs directly.
All passed. Fixed-grid nonsmooth-loop A error decreases with adjacent orders
about 1.40–1.46; this is not a second-order claim. The prescribed-loop figure was
visually reviewed against the independently verified packet.

```sh
python3 tests/reference/m1_completion/ai_review/prescribed_check.py \
  tests/reference/m1_completion/prescribed \
  /tmp/openmhd-issue7-candidate-v1/results/prescribed
python3 scripts/test_m1_wave_loop.py
```

The last measurement test repetition passes 13 fixtures; its separate log is
`measurement_tests_current.log`. `followup_provenance.json` records this later
review snapshot and exact commands without rewriting the initial review record.
The compact archive retains selected CSVs; reproducing the all-raw check requires
the full original packet (or an exact rerun with matching hashes).

## Bounded N64 snapshot figures

`snapshot_check.py` independently verifies the input and figure provenance,
periodic grid mapping, loop magnitude normalization/ranges, standing-wave
analytic phase, y-mean residuals and complete cellwise vector boost maximum.
The original plot ceiling clipped real loop overshoots; the corrected ceiling
1.2 covers the independently measured maxima 1.174804415 and 1.165278478 and
rejects future out-of-range inputs. The final rendered figures were inspected.
A fresh rendering reproduced both PNGs and their provenance byte for byte.

```sh
python3 tests/reference/m1_completion/ai_review/snapshot_check.py
python3 scripts/plot_m1_snapshots.py --output /tmp/openmhd-ai-review/snapshot_reproduction
```

The rendering command requires NumPy and Matplotlib. The executed interpreter,
versions, exact hashes and scope are recorded in `snapshot_review_provenance.json`.
This review covers the N64 snapshot figures only; the full coupled spatial and
temporal packets remain pending.

## Interim travelling-wave ladders

`travelling_ladder_check.py` independently remeasures the twelve completed
travelling fixed-grid base runs at N64/128/256 (two profiles, regular/jittered),
including initial, quarter and final snapshots. It verifies every selected
run's raw-file hashes and the frozen source/binary hashes. No simulation or
production measurement code is called. `travelling_ladder_report.json` retains
only checked run inputs/metadata and measurements; it does not label either
still-growing full execution packet complete.

```sh
python3 tests/reference/m1_completion/ai_review/travelling_ladder_check.py \
  /tmp/openmhd-issue7-baseline-a8ff3f5/results/full \
  /tmp/openmhd-issue7-signal-v1/results/full \
  /tmp/openmhd-ai-review/travelling_ladder_report.json
```

NumPy is required. Exact executed commands and hashes are in
`travelling_ladder_review_provenance.json`. The report includes all initial and
final fitted/adjacent orders, residual slope SE, radial/quadrature/normal B
errors and separate divergence/conditioning diagnostics. Both irregular final
ladders fail the registered order gate; the low order is already present in
the initial reconstructed B. The deterministic jitter pattern changes with N,
and three-point residual SE is not ensemble or systematic uncertainty. The
full coupled packet review remains pending.

## Completed original-profile wave matrix

`wave_matrix_check.py` independently verifies all 64 completed spatial wave runs
and 32 boost pairs for one profile, importing no production measurement code.
It reads all 192 initial/quarter/final snapshots, verifies each inspected raw
hash plus frozen sources/binary, recomputes physical/component/vector norms,
boost velocity/energy transforms, geometry pairing, output positivity and
conservative budgets, and evaluates the registered spatial and both boost
normalization gates. `wave_metadata_check.py` separately cross-checks names,
manifest configuration, actual command arguments and run summaries.

```sh
python3 tests/reference/m1_completion/ai_review/wave_matrix_check.py \
  /tmp/openmhd-issue7-baseline-a8ff3f5/results/full \
  /tmp/openmhd-ai-review/original_wave_matrix_report.json
python3 tests/reference/m1_completion/ai_review/wave_metadata_check.py \
  /tmp/openmhd-issue7-baseline-a8ff3f5/results/full
```

NumPy is required by the matrix checker. The original-profile result is 64/64
sampled positivity/budget passes, 3/8 spatial gate passes, 13/32 boost pairs passing
both reported normalizations and 19/32 failing both. The negative regular fixed
standing-wave order and all inadequate irregular orders are retained. Exact
commands and review hashes are in `original_wave_review_provenance.json`.
The still-active root execution packet is not certified as a completed archive;
the completed signal wave review is recorded below; loop and temporal reviews
remain pending.

## Completed signal-profile wave matrix

The same independent matrix and metadata checkers were run on all 64 completed
signal-profile spatial wave runs. `signal_wave_matrix_report.json` records all
192 inspected snapshots and per-run raw/source hashes. The result is 64/64
sampled positivity/budget passes, 3/8 spatial gate passes and 31/32 boost pairs
passing both normalizations. The regular fixed standing-wave N256 pair fails
both, with B boost L1 `8.101939153e-6`; its valid geometry and small t=.25
residual are preserved alongside the late failure. No threshold or solver was
changed and no simulation was run.

```sh
python3 tests/reference/m1_completion/ai_review/wave_matrix_check.py \
  /tmp/openmhd-issue7-signal-v1/results/full \
  /tmp/openmhd-ai-review/signal_wave_matrix_report.json
python3 tests/reference/m1_completion/ai_review/wave_metadata_check.py \
  /tmp/openmhd-issue7-signal-v1/results/full
```

Exact review artifact hashes/commands are in `signal_wave_review_provenance.json`.
The unfinished global execution provenance is not certified. Full coupled
loops, temporal comparisons, final archives and full-study figures are pending.

## Completed mean-field comparison matrix

`mean_matrix_check.py` independently verifies all 72 completed `mean_*` runs
across the three named profiles, with 144 initial/final snapshots and 36 boost
pairs. It records exact inspected raw/source/binary hashes, command/configuration
matching, constructor/geometry checks, physical boost norms, recorded divergence
norms, sampled positivity/budgets and every refinement observation. It imports
no production measurement code and runs no simulation.

```sh
python3 tests/reference/m1_completion/ai_review/mean_matrix_check.py \
  /tmp/openmhd-issue7-signal-v1/results/full \
  /tmp/openmhd-ai-review/mean_matrix_report.json
```

NumPy is required. The two bulk-frame comparators pass their 12/12 registered
boost gates; all 12 `paper-global-v2` pairs remain diagnostics with no retrospective
gate. Root matching and geometry pass all 36 pairs. The original-profile residual
persists under dt refinement; comparator residuals are at roundoff, so their
recorded refinement orders are not physical-accuracy claims. Exact execution
commands/hashes are in `mean_matrix_review_provenance.json`. This bounded
short-time result does not override the failed signal N256 standing-wave pair.
Full coupled loop/temporal/archive/figure review remains pending.

## Complete-wave figure review

`wave_figure_check.py` verifies the immutable input-report hashes, all 16 plotted
spatial curves, both 8-by-4 heat-map mappings, normalization, annotations, gate
labels and distinct magnetic-only/full-field verdicts. It checks plotted artist
objects directly against the reviewed numerical reports and reproduces both
PNGs and their provenance byte for byte. Shared colour limits encompass all
data, and final images were visually inspected.

```sh
python3 tests/reference/m1_completion/ai_review/wave_figure_check.py
```

NumPy and Matplotlib are required. The script writes only a fresh reproduction
under `/tmp/openmhd-ai-review/reviewed_wave_reproduction`; reviewed reports and
solver sources are unchanged. Exact hashes/versions and inspected scope are in
`wave_figure_review_provenance.json`. This figure review covers the completed
wave matrix; loop/temporal/final-archive review remains pending.

## Complete physical temporal packet

`temporal_matrix_check.py` independently checks the completed 16 temporal runs
from each frozen profile checkout: exact source/binary/config/raw hashes,
96 complete snapshots, fixed geometry and same-grid pairing, initial-state
identity, physical errors, EOS, sampled positivity/budgets and divergence RMS.
It records component/vector B, total/reduced A and phi L1/L2/max differences to
the same-grid `.000025` reference and every adjacent cap-ratio slope at `.25`
and 1. Aggregate dt statistics, all rejection/fallback/root counters and a
clock-only output-time truncation check are included.

```sh
python3 tests/reference/m1_completion/ai_review/temporal_matrix_check.py \
  /tmp/openmhd-issue7-baseline-a8ff3f5/results/full \
  /tmp/openmhd-issue7-signal-v1/results/full \
  /tmp/openmhd-ai-review/temporal_matrix_report.json
```

NumPy is required. No simulation or production measurement code is run.
`temporal_matrix_review_provenance.json` records the exact executed command,
versions and hashes for the archived report/log. The original regular standing
B difference is nonmonotone; no temporal success gate is invented. Finite
reference, frozen-C1, aggregate-only timestep information and roundoff-component
limits are explicit. The containing execution packets remain active, and their
observed metadata hashes are not certified as completed global provenance.
Full coupled-loop/final-archive/remaining-figure review remains pending.

## Partial coupled-loop matrix

`loop_matrix_check.py` independently validates only completed `loop_*` records
from both raw studies. `loop_partial_report.json` contains 60 reviewed runs,
180 snapshots and 30 passing boost pairs, with four unfinished N256 jittered
comoving runs and their two pairs explicitly unexecuted. It is not a complete
loop-matrix or global-packet certificate.

```sh
python3 tests/reference/m1_completion/ai_review/loop_matrix_check.py \
  /tmp/openmhd-issue7-baseline-a8ff3f5/results/full \
  /tmp/openmhd-issue7-signal-v1/results/full \
  /tmp/openmhd-ai-review/loop_partial_report.json
```

NumPy is required. No simulation or production measurement code runs.
Source/binary/raw/config hashes, all snapshots/geometry/positivity/budgets,
passive A/B comparisons, magnetic energy, reported divergence reductions and
boost transforms/gates are checked. Passive analytic references are not exact
coupled-MHD solutions; prescribed-flow drift/A gates are not applied.
`--require-complete` may be added for the later final matrix and refuses output
unless all 64 runs are complete. Preserve this partial archive separately.
`loop_partial_review_provenance.json` records the exact executed command and
scope; final coupled loops/global provenance/archives/remaining figures remain
pending.

## Final original loop and execution/archive review

`original_loop_check.py` completes only the original 32-run loop matrix. It
reuses 30 prior measurements after exact source/raw/config/command/record
hash checks and independently measures the final two N256 jittered comoving
runs. All 16 original loop pairs pass the registered magnetic boost gate.
The earlier partial report remains unchanged.

```sh
python3 tests/reference/m1_completion/ai_review/original_loop_check.py \
  /tmp/openmhd-issue7-baseline-a8ff3f5/results/full \
  /tmp/openmhd-ai-review/original_loop_report.json \
  --reuse-report tests/reference/m1_completion/ai_review/loop_partial_report.json
```

`original_archive_check.py` verifies original execution and later measurement
layers separately, both source maps and frozen binary, all 672 raw files in
two locations, all compact archive files and selected snapshots, and matches
the corrected numerical summary to the three independent numerical reports.
No norm/evolution rerun is needed for already hashed evidence.

```sh
python3 tests/reference/m1_completion/ai_review/original_archive_check.py \
  tests/reference/m1_completion/original \
  /tmp/openmhd-issue7-baseline-a8ff3f5/results/full \
  /tmp/openmhd-issue7-baseline-a8ff3f5 \
  results/issue7_completion_20261106/original \
  /tmp/openmhd-ai-review/original_archive_report.json
```

The loop checker requires NumPy; archive checking uses the standard library.
The `original_*_review_provenance.json` files retain exact executed commands,
versions and hashes. Every prior numeric result/gate label survives reanalysis,
including the original wave failures. Final signal loops/archive and combined
figures/overall assessment remain pending; this is an explicitly labelled AI
review, not full M1 acceptance.

## Complete coupled-loop matrix

`loop_matrix_check.py` was rerun with the completeness requirement after all
64 loop evolutions finished. `loop_matrix_report.json` and its log cover all
192 snapshots and 32 boost pairs, all passing the registered sampled
positivity/budget and loop magnetic boost gates. The earlier partial evidence
and final original-only report remain unchanged; their per-run measurements
match the full report exactly.

```sh
python3 tests/reference/m1_completion/ai_review/loop_matrix_check.py \
  /tmp/openmhd-issue7-baseline-a8ff3f5/results/full \
  /tmp/openmhd-issue7-signal-v1/results/full \
  /tmp/openmhd-ai-review/loop_matrix_report.json --require-complete
```

The full report preserves passive-reference scope, finite comoving drift,
magnetic overshoots and all three divergence diagnostics. It does not override
the failed signal Alfvén pair or certify the final signal archive/combined
figures. Exact hashes and command are in `loop_matrix_review_provenance.json`.

## Final candidate archive and four-figure audit

The final 184-run candidate archive has separate verified execution and
measurement layers, 1032 raw-file hashes checked at both locations and all
six N256 counterexample snapshots retained. Existing numerical values/gate
labels are unchanged by reanalysis. The independent checker reuses prior
numerical reviews only after exact input/source matching.

```sh
python3 tests/reference/m1_completion/ai_review/candidate_archive_check.py \
  tests/reference/m1_completion/candidate \
  /tmp/openmhd-issue7-signal-v1/results/full \
  /tmp/openmhd-issue7-signal-v1 \
  results/issue7_completion_20261106/candidate \
  /tmp/openmhd-ai-review/candidate_archive_report.json
python3 tests/reference/m1_completion/ai_review/final_figure_check.py
```

The figure checker needs NumPy/Matplotlib and renders only into fresh temporary
review directories. It checks all plotted artists against verified inputs,
then reproduces the four final PNGs from raw and compact summaries byte for
byte. `final_figure_report.json` retains input/source/figure hashes and pinned
environment versions; `final_review_provenance.json` records final document
hashes and the bounded outcome. No full M1, general-invariance or human-review
acceptance is claimed. Historical partial/rejected evidence remains unchanged.
