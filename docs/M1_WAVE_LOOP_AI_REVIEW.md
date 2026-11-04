# Issue #7 incremental AI review

**Verdict: bounded approval to publish this increment; issue #7 and M1 remain open.** This is a separate **AI review**, performed by an independent review agent at the user's request. It is not human peer review, author confirmation or paper-equivalence validation.

The review covers numerical implementation `ee8fabc`, ordered clipping pruning `502959e`, corrected measurements through `0e710e18f9c807c2db274054ee7ad7f992a5799a`, the final measurement-test/CLI-guard changes, archived evidence, documentation and five plots. The Rust evolution packets record clean revisions `433ef7d` and `ebd590d`; reanalysis has distinct measurement provenance and does not relabel the evolution revision.

## Independent checks

- Format, Clippy with warnings denied and all **80 Rust tests** passed. All **seven measurement fixtures** passed, including repeated analysis and immutable-metadata corruption rejection.
- Verified **816 raw-output hashes**, **56 execution-source hashes**, **32 archived snapshot hashes**, both archive manifests and corrected measurement provenance. Verified the immutable original execution summary against its original hash.
- Reviewed the fixed mass-weighted reference velocity, reduced-potential source algebra, two-stage application, total-A output and accepted-only offset updates. Nonzero-offset rejected-trial rollback is tested; the default v2 profile remains unchanged.
- Reviewed conservative bounding-tree distance tests and surviving clipping order. Independent shuffled/jittered probes at length scales 1e-9, 1 and 1e9 yielded 18 bit-identical valid meshes and six matched duplicate rejections against exhaustive clipping.
- Reviewed immutable geometry ownership and fresh state-dependent gradients/extrema. Additional near-contact rigid-motion cache probes gave maximum A differences 1.70e-21 and integrated-Q differences 2.17e-19 against rebuilt stencils.
- Checked scalar/component/vector norms, physical frame transformations, coordinate/time pairing, actual refinement ratios, failure versus missing-run classification and RMS divergence plots. Independently recalculated the remaining failed pair directly from raw snapshots.
- Visually inspected all five plots and independently reproduced them **byte for byte** from archived inputs.

## Findings resolved during development

The exact Cartesian geometry shortcut failed its registered multi-step equivalence tolerance. A separate AI probe isolated nearly zero-normal-field HLLD returned-state/normal-EMF sensitivity despite stable conservative fluxes. The shortcut was withdrawn; the flux routine was not silently changed. The [observation and prospective follow-up](DEGENERATE_FACE_FOLLOWUP.md) remain explicit.

The initial runner incorrectly substituted absolute maxima for relative Alfvén boost norms, omitted some geometry pairing checks, could mislabel failed ladders as unexecuted, and assumed factor-two refinement even across missing entries. These reporting issues were corrected without rerunning or changing the evolved states. The Alfvén scale ambiguity is explicitly labelled a post-run clarification for the original packet; both conventions and raw norms are retained with the threshold unchanged.

Reanalysis initially read pair definitions from the mutable current report. It now preserves and verifies the immutable execution summary, validates raw files, constructs fresh pair definitions and records separate measurement provenance. A corruption/repeated-analysis fixture protects this behavior.

## Accepted evidence and limits

The mean-field bulk-frame ladder passes **12/12** pairs with maximum transformed component error **9.55e-15**. Original-v2 mean-field discrepancies remain observations, not retroactively passed gates. The original-profile physical subset has **7/16 passing and 9/16 failing Alfvén boost pairs** under both reported normalizations; coupled-loop pairs pass **8/8**.

The further bulk-frame physical subset has **15/16 passing Alfvén boost pairs** and **8/8 passing loop pairs**. The remaining regular N64 standing-wave, fixed-baseline-mesh pair fails under both normalization conventions. Independent raw recalculation gives:

| Quantity | Measured difference |
| --- | ---: |
| Magnetic vector L1 | 0.0003107687472172844 |
| Maximum transformed physical component | 0.002573486050191874 |
| Paired-position discrepancy | 3.55e-15 |

Its cause has not been isolated. The degenerate-face observation is a candidate to investigate, not an established explanation of this physical failure. The maximum conservative-budget residual across the measured packets is **6.91e-14**.

Full N128/256 spatial, N64 temporal and prescribed-flow loop validation remains unexecuted; broader shock/vortex and full M1 acceptance are also outstanding. The figures and text preserve these boundaries. A nonblocking future improvement is automatic archive-hash and CSV-completeness validation in the plotting loader; the inputs for this packet were independently verified. The signed-mean/RMS distinction and the normalization using `|B|+1e-12*Bscale` with fixed Bscale are stated explicitly.
