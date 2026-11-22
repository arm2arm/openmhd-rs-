# Final M1 acceptance sequence (2026-11-21)

This records the continuation authorized by the owner on 2026-11-21:
finish M1, make the necessary implementation decisions, and proceed without
asking for routine decisions. It changes no registered case or threshold.
Acceptance remains conditional on the evidence and separate AI review below.

## Configuration decision

Retain campaign A as the M1 configuration:

```text
bulk-frame-heun-quadratic-v1 --projection-screening 1 --riemann hlld-pressure --potential-limiter smooth-extrema
```

Use the iterative projection, the historical trial fraction 1, periodic
fixed/rigid 2.5D meshes, f64, synchronized timesteps and CFL .3. The owner
already selected the iterative solve on 2026-11-19; the current delegation
also authorizes selecting its tested smooth-extrema limiter for this named
configuration. This choice accepts the recorded 3–10% increase in fixed-mesh
passive-loop errors and the admission of curvature-confirmed potential
extrema. It does not change the binary default, primitive limiter, benchmark
definitions or any tolerance. No TVD, general positivity, entropy-stability,
paper-equivalence or AREPO-equivalence claim follows.

Campaign B also passed, but its .95 trial fraction remains optional. A
already has the required complete matrix, and retaining it avoids changing
the accepted timestep sequence solely for a shared-cluster timing advantage.

## Source and execution

The previous A campaign predates the later branch integration. Although
the merge has passing REANA identity comparisons, final acceptance will
also use a fresh registered campaign from the current integrated source.

- Development revision: `2bdcea0d28340e7429e10053a641f92d51fcc696`.
- Frozen submission: `results/reana_submission_m1_final_20261121`.
  Its `snapshot.json` pins every included source and upload.
- Preflight: `openmhd-m1-final-preflight-20261121`, study
  `m1-fanout-preflight`, one job. It must pass format, strict all-feature
  Clippy, debug/release workspace tests, Python tests, build and M0 checks.
- Then run the four short bounded stages, the 48-case medium matrix and
  24-case mean-field ladder. All three precondition phases must pass.
- Then run the registered 112-case wave/loop/temporal matrix and 30-case
  shock/vortex matrix from that preflight's immutable binary. Every
  independent benchmark case has its own REANA workflow and explicit
  resources; ready cases run concurrently. No aggregate resource cap.
- Use the existing `iter-*` specifications and frozen submission's runners.
  No new physical method is introduced by this continuation.
- Preserve incomplete uploads and recover only the same workflow. Missing
  downloads are observation errors. A verified required physical or
  execution failure stops escalation and unnecessary sibling workflows.

The full registered gates are those of
[M1_FULL_VALIDATION_PLAN.md](M1_FULL_VALIDATION_PLAN.md#gates-all-unchanged-except-the-owner-approved-bx-amendment)
and the frozen benchmark packets, including the existing owner-approved
column/planar Brio Bx distinction. Temporal orders remain reported
observations, with no retrospective threshold.

## Independent evidence and review

Before this fresh run, independently reduce A's existing 112 wave snapshots,
all 12 primary regular/column Brio cases and all six primary regular vortex
cases. Reuse the existing independent analytic-wave, decimal shock-reference
and raw-face rectangular vortex reducers; import no production measurement
functions. Preserve input hashes, scripts, all ladders, both boost
normalizations, actual timesteps, counters and uncertainties. Repeat these
reductions on the final campaign's outputs or establish exact snapshot
identity for every input being reused.

Review the named configuration's equation/source map, including the bulk-frame
gauge, reevaluated Heun stages, quadratic curl, screened projected rate,
pressure-weighted flux, and smooth-extrema limiter as engineering choices.
Check the prescribed-flow packet and its applicability to the current
implementation separately from coupled-MHD loop tests.

A separate AI reviewer must assess the exact candidate, the registered
gates, reference and provenance integrity, and the implementation departures.
The implementing assistant's audit and independent arithmetic reductions
alone do not constitute this separate review. Record blocking findings and
resolve them before an acceptance statement. This is AI review, not human
peer review or author confirmation.

## Completion boundary

M1 can be accepted only after the current-source checks, all registered
physical gates, prescribed-flow applicability and separate review pass.
Publish a clearly scoped acceptance record and update current status and
roadmap without erasing failed historical profiles.

The resulting milestone is the validated single-process 2.5D fixed/rigid-mesh
engineering reference, with deterministic per-case Rayon pools. The historical paper endpoint profile's mean-field
boost and planar pressure failures remain limitations of that profile.
Deforming-mesh physical acceptance, full 3D geometry, MPI, local timesteps
and adaptation remain later work. Passing this packet does not authorize
claiming general Galilean invariance or full reproduction of the paper.
