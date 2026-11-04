# M0 completion and review checklist

**M0 is not finished.** Both [issue #1, numerical specification](https://github.com/arm2arm/openmhd-rs-/issues/1) and [issue #2, benchmark definitions](https://github.com/arm2arm/openmhd-rs-/issues/2) remain open as of 2026-11-04. The serial planar implementation is useful evidence for a restricted method; it does not close either issue.

## Completed evidence

- The full v1 paper was read, with PDF provenance, page/equation references, stencil definitions, gauge/mean-field signs and endpoint-stage pseudocode in the [source specification](PAPER_IMPLEMENTATION_SPEC.md).
- Nine dependency-free algebra checks cover the covector identity, mean-field correction, least-squares moments, donor direction, centroid correction, cleaning signs/dimensions and initial-condition audits.
- The [planar reference](COUPLED_2D.md) implements and tests EOS/energy closure, HLLD/HLL moving-face fluxes, periodic Voronoi geometry, two distinct derivative stencils and the single-Az evolution. It records its engineering policies and measured limitations.
- The [isolated Rust operator audit](M0_OPERATOR_CHECKS.md) adds general point-source, shear/rotation, mean-field/boost and cleaning-stage checks. It measures first-order temporal convergence of a longitudinal gauge mode under the frozen-source prescription of Eq. (90). A separately labelled reevaluated-Heun comparator is second order.

## Decision register

The U/R identifiers refer to the source specification. A policy implemented for the planar reference is not automatically a reviewed choice for the general method.

| Topic | Recorded choice and evidence | Remaining work for M0 |
| --- | --- | --- |
| Units, EOS and precision | f64, nondimensional mu0=1, ideal gas with benchmark-specific gamma; tested conservative/primitive conversion. | Independent review of the convention map. |
| Geometry and boundary scope | Serial periodic 2D first; paired oriented faces, geometric centroids, explicit neighbour images. Planar solver permits fixed or rigid translation. General nonperiodic A/phi boundaries, adaptation and initial Poisson solve are explicitly deferred (U6). | Review the general centroid correction and deforming-geometry stage contract. Implementation belongs to M1/M2. |
| Curl and LS conditioning | Free-intercept face-area-weighted neighbour fit, target excluded, unlimited curl; scaled covariance rejects det <= 1e-10 trace² in 2D. | Review conditioning thresholds and the 2D/all-component embedding; no blanket div(curl)=0 claim. |
| Face flux and energy (U1) | Arithmetic common normal B at preserved gas pressure; HLLD with documented wave bounds and counted HLL fallback. Cell total energy is never reset. Analytic ALE/contact/rotational fixtures pass. | Specify the general endpoint primitive PDE predictor, including discrete B derivatives; the planar method-of-lines closure is a declared deviation. |
| A face derivatives/limiting (U2) | Separate face-centroid LS with face-area weights, donor direction fixed; cell-anchored neighbour-extrema limiting for planar face extrapolation. HLL fallback uses its numerical induction EMF. | Fix when endpoint A-face gradients are refreshed in the paper-stage implementation, and review these policies as general-method choices. |
| Auxiliary velocity (U3) | Paper's C1 adaptive tricubic construction and published averaging rules are extracted. Single-Az planar runs instead use the allowed special u=v reduction. | Specify root grid, exact corner-difference stencil, empty-bin and membership rules, within-step refresh and dimensional adaptation. These choices need constant/affine, seam, continuity and boost fixtures. |
| Cleaning coefficients/timesteps (U4) | Isolated kernels use alpha=1, beta=.15 and preserve the two printed bounds. They accept explicit positive cs and radius; they do not select a mesh radius or gas timestep. Planar pilot uses phi=0, no cleaning, CFL .3 and documented rejection policy. | Specify general cs=sqrt(gamma p/rho), radius convention, initial phi, combined timestep/rejection policy and tolerances before coupling cleaning. Do not silently inherit the planar controller. |
| Cleaning endpoint (U5) | Old div(A)/cs, predicted phi and new radius reproduce Eq. (90). Manufactured-mode error/order are archived separately. | Review the measured first-order gauge-mode result and decide whether to retain this reference prescription or introduce a separately named, documented alternative. Do not silently substitute Heun. |
| Optional physics | Entropy closure, explicit resistivity, Hessian reconstruction, local steps, refinement, gravity and cosmology are outside the initial coupled reference. The isolated source kernel accepts continuum -eta J only. | Review these deferrals; require separate specifications/tests before enabling them. |
| Published discrepancies (R1-R4) | Printed Alfvén A does not curl to stated B; cleaning explanatory equations have dimensional/notation findings; stage notation needs repairs; Brio-Wu resolution differs between caption/prose. All are attributed findings, not confirmed errata. | Independently check each against the rendered PDF and approve any derived benchmark correction. Orszag-Tang normalization is consistent and is not an outstanding discrepancy. |

## Acceptance and remaining sequence

1. Finish the general predictor, auxiliary-grid, endpoint-reconstruction and cleaning/timestep decisions above. Update the equation-to-code map with each adopted policy, fixture and explicit deferral.
2. Obtain independent scientific review of signs, stencils, R1-R4 and the engineering choices. Record reviewer identity, reviewed revision and conclusions. The existing tests and this checklist are self-checks, not that review. No independent review has occurred.
3. Complete issue #2's benchmark packet: versioned configurations, resolution ladders, analytic or independently produced reference data with checksums, norms, boosts and tolerances chosen before evaluating the new configurations. Current proposals and small pilot gates are a start. The shared-kernel 1D Brio-Wu comparison and early vortex images do not supply independent high-resolution shock/vortex references.

Issue #1 can close when its traceability, operator-fixture, explicit-deviation and independent-review criteria are met. Issue #2 has its own reference/configuration gate. Full 3D implementation, successful large benchmarks and MPI scaling are later milestones, not additional M0 completion requirements. General paper-faithful vector-potential implementation should follow the reviewed specification; the current pilots must retain their scope labels.
