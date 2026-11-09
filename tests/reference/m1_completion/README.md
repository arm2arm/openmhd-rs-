# Issue #7 continuation evidence

See [results](../../../docs/M1_COMPLETION_RESULTS.md), the
[prospective plan](../../../docs/M1_COMPLETION_PLAN.md) and the separately
labelled [AI review](../../../docs/M1_COMPLETION_AI_REVIEW.md).

- `original/`: completed 112-run original-profile physical spatial/temporal
  study; 3/8 wave spatial gates and 13/32 wave boost pairs pass; all 16
  coupled-loop boost pairs pass. Failed gates remain explicit.
- `candidate/`: completed 184-run study: 72 mean-field evolutions across three
  profiles and 112 full spatial/temporal evolutions for `bulk-frame-signal-v1`.
  The new profile passes 3/8 wave spatial gates and 31/32 wave boost pairs;
  the N256 standing fixed-grid pair still fails. All 16 coupled-loop boost
  pairs pass. Its six N256 standing-pair snapshots preserve the counterexample.
- `signal_quick/`: completed 48-run N32/64 coupled physical packet for
  `bulk-frame-signal-v1`; full spatial/temporal gates are not evaluated here.
- `prescribed/`: completed 32-run constant-flow regular/jittered Voronoi loop
  packet, N32/64/128/256, fixed/comoving and base/boosted; all registered gates pass.
- `rejected_hll/`: rejected `bulk-frame-hll-v1` experiment, with 81 completed
  records out of its 184-run manifest before stopping. These are partial
  execution records, not an accepted benchmark packet. `stopped_experiment`
  records the boundary-discontinuity finding and unfinished work.
- `ai_review/`: independent probes, logs, exact rejected core source,
  reviewed-source hashes and reproduction commands.

Each completed archive contains compressed numeric summaries, immutable
execution provenance, exact execution sources, selected raw snapshots and an
archive SHA256 manifest. Reanalyzed packets also preserve the original
execution summary and separate measurement provenance. Git HEAD alone does
not identify uncommitted execution sources; use the archived source bytes and
hashes. Raw full result directories remain separate from these compact files.

For exact source reproduction, use a fresh checkout at the execution revision
and overlay `execution_sources.tar.gz`; this preserves tracked dependencies
outside the recorded execution-source set. Invoke the archived commands with
a fresh output location. Reanalysis has its own `measurement_sources.tar.gz`
and provenance; preserve original execution metadata and summaries when using
it. Restoring exact source bytes is distinct from promising identical floating
point trajectories on other platforms/toolchains.

Full local raw copies are in `results/issue7_completion_20261106/` (ignored by
Git); the immutable provenance retains the actual original execution paths.
The compact numeric reports and selected snapshots can be inspected without
rerunning the expensive N256 evolutions.

The historical evidence under `../m1_wave_loop/` is unchanged. Failed gates
are not relabelled and no full M1, 3D or AREPO-equivalence claim is made.
