# Issue #21 — reviewed representation and gate disposition

The implementing assistant reviewed the retained operator/source evidence and
the already owner-approved Bx amendment on 2026-11-10. This completes the
scoped representation investigation in #21. It is **not independent peer
review, a repair of the literal profile's pressure failure, or M1 acceptance**.
The original failed planar Bx measurements remain failures under the original
rule. Under the explicit amendment they are recorded diagnostics, never
reported as passed Bx gates.

| Issue criterion | Reviewed evidence and disposition |
| --- | --- |
| Exported operator | The exporter adds every sample coefficient to its cell index and subtracts it from the first sample index, matching `sum(weight * (value − baseline))`. Accumulating repeated periodic indices is necessary and implemented. The exporter, effective-gradient expression and affine fit are unchanged from the retained audit source. The quadratic sample enumeration, weighted QR and first-derivative coefficients also match; later Hessian output does not alter these coefficients. |
| Gauge removal | The Helmert columns are orthonormal and span the Euclidean complement of the constant potential. Any potential differs from one in that complement by a constant, which the effective derivatives annihilate. Cell-volume weights belong on the derivative rows; a volume-weighted gauge basis is unnecessary for this quotient. |
| SVD tolerances and bound | All 24 original and explicit-contraction records agree in configuration, input hashes and rank. For nx256 planar jitter, the smallest singular values exceed the numerical rank tolerances by 59,800.6 (affine) and 4,117.6 (quadratic). Constant-annihilation, gauge-orthogonality and SVD backward residuals remain recorded. The two gain estimates agree to 1.12e-16 relative or better. This is numerical evidence, not an interval proof. |
| Paper and project geometry | Section 6.2 describes a stationary mesh and a problem invariant in y, using a narrower transverse box; it does not establish machine-small Bx for this project's planar-jittered stencil. The prose's 100 x-points and Figure 6's 512 cells remain the recorded source discrepancy. The project-specific symmetry-preserving regular/column controls therefore test a different property from generic planar jitter. |
| Explicit reviewed revision | The owner-approved `shock-bx-amendment.json` applies the unchanged 1e-8 Bx limit to regular and nonuniform column meshes. No field overwrite, initial-state change or M0 packet modification is introduced by this review. The latest complete primary shock ladders contain 12 base/boost cases with max Bx error at most 1.03251e-14 and passing independent reference checks. |
| Separate failures | The literal/default planar pressure failure remains #20. Full vortex/wave/loop/temporal gates and the final #7/#19/#22/#24 disposition remain required. Closing #21 does not certify those results or imply paper/AREPO equivalence. |

The paper was rechecked in the [v1 full text, Section 6.2 and Figure 6](https://arxiv.org/html/2609.35989v1#S6.SS2).
The amendment and prior approval remain [versioned separately](../../../../benchmarks/m1/shock-bx-amendment.json).

For clarity, write `Q` for the Helmert basis and define

```text
N = sqrt(V) Dy Q,   T = sqrt(V) Dx Q,   N = U S Wᵀ.
```

On the recorded full-column-rank cases, a gauge-fixed potential has coordinates
`q` with `N q` representing the weighted normal-field error. Since
`q = W S⁻¹ Uᵀ N q`, the bound is
`||T q||₂ <= ||T W S⁻¹||₂ ||N q||₂`.
Right multiplication by `Uᵀ` preserves the nonzero singular values because
U has orthonormal columns. The common total-volume normalization cancels in
the RMS ratio. Thus the recorded gains 30497.7109 and 757526.7818 imply
transverse RMS below .000304978 and .007575268 if max normal error is below
1e-8, inconsistent with this shock's order-one transverse field. This
conclusion is restricted to the measured operators/meshes and floating-point
audit; it is not a claim about every unstructured curl or unpublished AREPO.

The archive verification rechecks all **189 raw and 104 source members**,
the original warning-bearing report and clean rerun, derivative source
applicability, the unchanged M0 packet, and the completed independent primary
shock reference report. It does not recompute singular values or rerun a
simulation. Earlier measured regressions remain in their original archives;
the current frozen REANA candidate has already passed its workspace checks.

From the repository root:

```sh
python3 tests/reference/m1_mesh_symmetry/disposition_review/verify_archive.py \
  /tmp/fresh_bx_disposition_review.json
```

`verification.json` records the inputs and observed comparisons;
`archive_sha256.json` covers this review directory except itself. The parent
historical archives are not rewritten. The scientific closure is a completed,
explicitly reviewed representation/gate disposition, **not a claim that the
planar mesh now preserves Bx to roundoff**.
