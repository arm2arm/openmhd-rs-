# Finest column-jitter Brio boost failure (2026-11-10)

The full REANA physics matrix exposes a **required boost-gate failure** for
`bulk-frame-heun-quadratic-v1 --accelerated-projection --projection-screening 1`.
At nx1024 × ny4, column jitter .15, t=.1, the largest normalized base/boost L1
difference is **5.818394374e-6**, above the unchanged **1e-8** bound. Both runs
complete with positive states, passing budgets, Bx and seam diagnostics.
The regular and column reference-profile/refinement gates also pass. Those
successes do not override the boost failure.

The main workflow `openmhd-m1-reporting-campaign-20261110.1`, UUID
`01947a14-a507-4384-a4ca-9533395d08e8`, was **force-stopped at 01:16:53 UTC**
after checking the completed pair's raw hashes and recomputing its comparison.
Its exact source snapshot is `b102b766bc5b8e116811924f977e923e097c7ec3cf351647fae3bd2c8c46de04`.
Twenty of thirty physics runs completed: all 18 Brio cases and two regular
N64 vortices. The remaining ten vortices are incomplete; the 112-run full
wave/temporal matrix never started. `workflow_status.json` is authoritative;
the preserved campaign checkpoint can still say running after a forced stop.

## Registered comparison

The periodic domain is [0,2] × [0,.125], gamma=2, mu0=1, f64; interface x=1,
mean B=(.75,0,0), original Brio states. The boosted fluid and rigid mesh add
(2,-1,0). Both cases use two Rayon threads, the original CFL and no floors,
energy reset or resistivity. All nine Brio boost pairs are remeasured from
hash-verified final snapshots. Eight pass, including N256/512 columns and
N1024 regular/planar-jitter meshes. The completed regular N64 vortex pair
also passes. No unfinished pair is counted as passed.

| Failed-pair component | Normalized L1 |
| --- | ---: |
| Density | 5.541334874e-7 |
| Pressure | 3.013007181e-6 |
| vx | 5.818394374e-6 |
| vy | 1.561528693e-6 |
| By | 1.137327531e-6 |
| Bx | 7.940685270e-13 |
| Energy | 2.605942573e-6 |

Paired translated-position error is 5.77316e-15; volumes match exactly. Both
runs take 2395 steps, with 1575 CFL retries, zero state rejections and 72
accepted HLL fallbacks. Final maximum |Bx-.75| is 6.92556e-11 / 4.65935e-11,
below the amended 1e-8 gate. This failure is distinct from historical negative
pressure and planar-jitter Bx failures, which remain preserved elsewhere.

## Measured transverse pattern and bounded reproduction

The final column states contain an alternating-row component. At a fixed
column, maximum row-to-row vx variation is .001680084 (base) / .002194238
(boost). The largest cellwise transformed vx discrepancy is .002230347 near
x=1.137683. Rows 0/2 and 1/3 form opposite pairs. This measures lost transverse
symmetry; it does **not yet identify the responsible operator or prove a
particular shock-instability mechanism**.

A fresh bounded REANA job reproduces the result using the exact original
Linux binary, SHA256
`ac3e8e895624f80e02e25fb0794c69b1f2a1e2162b697db812b4d46128b8648c`.
Workflow `openmhd-m1-column-repro-20261110.1`, UUID
`1f6ce890-5340-4842-989c-049b780aaddb`, completes at 01:28:23 UTC.
Snapshot SHA256 `65c556d30ed5f171ed608c6fe22c7c26eb2edf1097c84231360e9bf2185ce800`.
Four cases (N1024 regular/columns, base/boost), two threads each, 8-GB memory
limit and 600-second per-case caps take 124.87–155.06 s. All **24 scientific
file comparisons** match the original bytes: initial/final snapshots, summary,
history, geometry and physics metadata in each case. Regular boost passes at
5.70035e-11; columns reproduce 5.81839e-6. `scientific_acceptance` stays false.

The reproduction report gives initial/final transverse variation for each
physical component. The driver uses the original commands and source-verified
comparison/validation functions. It compiles or changes no solver. Binary
parts remain in the named REANA input workspace and the local frozen submission
`results/reana_submission_m1_column_repro_20261110`; the archived source and
provenance identify the binary's original build.

The subsequent [accepted-state trace](accepted_trace/README.md) also preserves
all 24 scientific files byte for byte. It observes growth from roundoff-sized
row differences near the right-moving slow shock, with much faster growth on
the column mesh. This narrows the location and timing; the responsible operator
is still under investigation. It does not change the failed acceptance verdict.

## Evidence and next gate

`failed_pair_raw.tar.gz` retains all 18 raw files of the failed pair, independently
hash verified. The complete partial manifest (30 cases), runs (20 cases), source,
stage log and original provenance are preserved. `partial_physics_summary.json`
is explicitly a later reduction of those records with the unchanged evaluator;
it reports incomplete/failed full physics. All 20 completed final snapshots
were independently hash checked before that reduction. Other full raw files
remain in the main REANA workspace and local remote-download directory.

The next work is to trace when the transverse mode grows, isolate fluid-flux,
reconstruction, curl/projection and floating-point frame effects, then test a
minimal correction. Reproduce the failure before changing a numerical term.
Keep the regular control and N256/512 column controls, conservation, Bx, wave
and boost gates. A known-failure reproduction is not a correction. Full
matrices must wait for the new bounded regression to pass; thresholds stay fixed.
