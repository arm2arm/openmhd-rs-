# M1 completion and merge contract — 2026-11-08

The user requested passing M1 gates and merging to main. Merge authorization
is conditional on measured success; it does not authorize relaxed thresholds,
discarding failures, substituting pilot results for the general solver, or
claiming paper/AREPO equivalence. The existing historical defaults and evidence
remain available. Engineering comparators must be identified by name.

## Required evidence

1. A frozen candidate passes the full wave/loop packet: N32/64/128/256,
   regular/jittered, fixed/comoving, base/boost, through t=1; all eight wave
   spatial gates use finest-three order >=1.8 and finest B L1/.1 <=.02.
   Preserve both boost normalizations and the stricter wave-amplitude bound.
   Run the registered N64 temporal ladder and report actual dt and rejections.
2. Include the nonzero-mean-field refinement/boost ladder for that candidate,
   prescribed-flow transport evidence, and all coupled-loop boost checks.
3. General A/gauge solver Brio-Wu and Orszag-Tang comparisons against the
   checksum-pinned M0 Athena reference archive, using the unchanged packet
   domains, EOS, resolutions, projection rules and acceptance limits.
   Implement the Brio signal-travel isolation diagnostic before certification.
   Do not reuse separate planar/1D solver results as general-method passes.
4. Every execution must complete with positive accepted states, conservative
   budgets <=1e-10, and the specified independent divergence/mean-field checks.
   Raw failures, missing cases, geometry/step/fallback counters and source
   hashes remain in the record. New changes require relevant regression,
   convergence and boost checks; no passing gate is inferred from submission.
5. Format, Clippy, workspace/Python/M0 checks and a final review pass on the
   exact merge candidate. Check the current main branch and merge conflicts,
   preserve user changes, commit reviewable changes, and merge only after the
   complete required evidence passes. Never force-push.

## First execution

Run `bulk-frame-heun-spline-v1` through the existing 112-run physical/temporal
wave/loop matrix on REANA with 24 independent serial cases and 64G test memory.
This maximizes case throughput; the previous single-case threading experiment
showed that a 24-thread pool does not keep 24 cores busy. The existing full
baseline workflows continue untouched. Develop the missing general shock/
vortex drivers and diagnostics while this frozen candidate runs. Investigate
remaining spatial/reconstruction failures from their measured error sequences.

The packet's regular meshes are its primary shock/vortex profile gates;
jittered runs retain their separately specified state/budget/diagnostic checks.
The existing wave evaluator's stricter eight-family spatial gates are retained.
The earlier N32 short time-order result alone is insufficient to merge M1.
