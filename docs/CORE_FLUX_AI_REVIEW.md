# AI review — issue #4

Date: 2026-11-04. Separate review agent: `/root/issue4_ai_review`, requested by the user. The reviewer did not edit the implementation. This record preserves the review's findings, evidence and acceptance boundary.

Reviewed implementation commit `f569019d8036834f9942df79e73d558acad7d7f7` and follow-up `c18664d3b8accb1048db9d456c3a68d58141973a`, against the preregistered gates in `a3446d1`.

**Verdict:** no remaining blocking findings for the scoped conservative-state and moving-face flux work.

## Finding and resolution

One validation defect was found and fixed: the periodic-coordinate comparison could report zero error for malformed coordinates outside `[0,2)`. The follow-up rejects invalid coordinates in either profile and adds a regression test. The reviewer reproduced the original false positive and verified its rejection after the fix. Existing archived coordinates and numerical results were unaffected. Documentation now also distinguishes characteristic signal travel from a strict numerical-domain-of-dependence guarantee.

## Independent checks

- All 11 `mhd-core` flux tests, two Brio driver tests, and four Python comparison tests passed.
- Recomputed every archived Brio–Wu L1/L2 error using coordinate-based reference-cell matching; results agreed exactly with the study tables.
- Verified the final archive records clean revision `c18664d`, all source/artifact hashes match, and all 13 study gates pass.
- Ran an additional deterministic 10,000-state flux probe: 658 upwind, 7,637 HLLD, and 1,705 HLL fallback cases. Normal-reversal and boost checks had maximum relative-plus-absolute error `3.3519e-13`. This was an ad hoc review diagnostic, not a committed acceptance test.

The scaled wave-speed calculation, conservative face exchanges, common-normal-field energy treatment, immutable retry states, and independent-reference averaging are consistent with the documented scope. The pressure-floor proposal is explicitly superseded by the reviewed rejection/retry policy.

## Acceptance boundary

This is a separate **AI review**, not human peer review or author confirmation. It supports issue #4 completion after normal CI/publishing checks; it does not establish arbitrary-state positivity, full floating-point-range robustness, or validation of the general vector-potential integrator, deforming meshes, or M1 as a whole.

See [setup, gates and measured results](CORE_FLUX_VALIDATION.md) and the [archived evidence](../tests/reference/core_flux/).
