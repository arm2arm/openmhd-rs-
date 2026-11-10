# M1 candidate implementation audit (2026-11-10, issue #19)

This is an implementation/source audit by the coding assistant, not an
independent review, author confirmation or physical acceptance. It covers
`9ce5304` and the factor-shift reporting correction `9e99b74`. The cached
diagonal passes four serial baseline comparisons on REANA with byte-identical
scientific files. Full M1 gates remain open.

The candidate is `bulk-frame-heun-quadratic-v1` with accelerated projection
and screening 1. The default remains `paper-global-v2`; the literal-state
comparison is `paper-state-emf-v1`. A candidate passing physical gates would
validate this named implementation within the tested 2.5D scope, not reproduce
the published endpoint algorithm or establish general Galilean invariance.

## Source map and implementation decisions

Publication anchors refer to [Springel, Mayer & Pakmor, v1](https://arxiv.org/html/2609.35989v1).
The detailed transcription, derivations and unresolved publication details
remain in [the M0 specification](PAPER_IMPLEMENTATION_SPEC.md), with explicit
engineering resolutions in [U1–U5](M0_ENGINEERING_DECISIONS.md). P denotes a
publication anchor; D a derivation; E an implementation choice. The table
describes this code, including deliberate departures.

| Component | Code and classification | Evidence / remaining limit |
| --- | --- | --- |
| Cell field, P (51)–(61) | `MagneticFit::with_stencil`, `moving-mesh::Derivatives`: unlimited neighbour LS curl plus fixed mean field. Candidate E: double-neighbour quadratic derivatives for A/phi and cell B. | Affine/quadratic reproduction and curl refinement tests; not a discrete de Rham complex. Independent B-divergence operators need separate measurement. |
| Face reconstruction, U1/U2 | `operators::{gradients,predict}` and mesh limiter: free-intercept LS derivatives, reconstructed around the stored value, componentwise neighbour bounds. E: common arithmetic normal B preserves reconstructed gas pressure. | Polynomial/limiter fixtures and `common_normal_field_preserves_face_pressure_but_cell_energy_is_fixed`. Cell total energy is never reset by this face operation. |
| Riemann solution, P §5.1 / U1 | `mhd-core::{hlld,riemann_with_completion}`: face-rest-frame HLLD, upwind outer branches, counted HLL fallback, explicit lab transformation. E: candidate signal-weighted returned A-face state; conservative fluid flux unchanged. | `flux.rs` rotation, normal reversal, joint boost, contact/rotational and degenerate fixtures; `completion.rs` actual standing-face, wave-boundary continuity and fallback controls. A valid face state alone does not guarantee positive later cell closure. |
| Induction source, P (69) | `PotentialStage::rate_from_states` implements the literal returned-state product in `paper-state-emf-v1`. E: historical/default and candidate profiles use numerical EMF minus auxiliary-velocity cross face B. | A manufactured test supplies different state and numerical EMFs to distinguish them. Literal replacement does not cure the planar pressure failure. |
| Gauge/mean field, P (70)–(72), (76) | `gauge.rs`, `PotentialStage`, `auxiliary.rs`. D/E candidate: evolve periodic a with a separate constant gauge offset; bulk-frame gauge deliberately omits the original offset-distortion contribution. E: cubic auxiliary deposition and persistent translated origin. | Transpose/sign, shear/rotation, analytic mean-field, C1, deposition and bounded boost tests. Original and candidate gauges remain separately named. |
| Time update, P (80)–(92) | `general::trial` retains old-data endpoint primitive prediction, endpoint A/phi derivatives and frozen-source cleaning. E candidate: `trial_heun` reevaluates every rate from the provisional conservative/curl state on fixed/rigid geometry. | Endpoint sweep audit reproduces original Q/A bits at dt=1e-6; `general.rs` predictor/bisector and topology tests; `heun.rs` semidiscrete order, boosts and permutation. Full physical temporal measurements still required. |
| Conservative exchange | `general::fluid_rate` computes each face once and applies opposite mass/momentum/energy increments in deterministic face order. | Per-face/kernel tests plus periodic-budget measurements. Numerical B is recovered from A, not independently advanced as the accepted conserved field. |
| Pressure closure | `general::recover`, `IdealGas`: total energy minus kinetic and curl-derived magnetic energy. Invalid states reject and retry from immutable data. | Positive accepted-state and budget diagnostics; failed controls retained. No pressure floor, entropy switch, energy reset, Powell source or explicit resistivity in this candidate. |
| Projected induction, E | `projected_rate.rs` solves a weighted curl-rate correction. Screening 1 changes the objective; it is not a numerical preconditioner parameter or a paper coefficient. | Matrix/operator, normal-equation residual, screening and CG tests. κ=0 and κ>0 are distinct configurations; neither supplies a positivity theorem. |
| Cached diagonal, E optimization | Cache the geometry-dependent Jacobi metric with the existing Cholesky factor. Borrow identical coefficients during each stage. | Fixed/rigid endpoints retain volumes/weights; projected profiles reject deformation. Equality assertions cover both screening branches. Four serial wave/shock/vortex pairs match bitwise; observed evolution speedups 1.068–1.106. |

## Projection distinction

For the actual 2.5D derivative matrices define

```text
C a = (Dy az, -Dx az, Dx ay - Dy ax)
H = Cᵀ V C,  D = diag(H),  rhs = Cᵀ V (target - C r)
(H + κ D) δ = rhs,  corrected_rate = r + δ.
```

V repeats the positive cell volumes for the three magnetic components.
For κ=0 the existing shifted factor `H + 1e-8 D` only preconditions the
unshifted system. For κ>0 the factor is the screened operator itself.
Recursive relative residual tolerance is 1e-11, followed by the original
true-residual check at 1e-9. Caching D alters none of these equations,
summation orders, stopping criteria or the final state-recovery operation.

The finite-volume induction target is an independent diagnostic/rate target,
not a second evolved magnetic state. Screening damps the correction toward
that target; it is not a proof that magnetic energy and conservative gas
energy are discretely compatible. Full shock/vortex tests are therefore
necessary even after smooth operators and short waves pass.

### Reporting defect found during the remote campaign

The CLI in the frozen cache campaign emits `projection_preconditioner_shift=1e-8` whenever
acceleration is enabled, including screened runs. For positive κ this label
is wrong: `Preconditioner::build` factors `H + κ D`, and the separate
`projection_screening` field correctly records κ. The frozen κ=1 campaign
therefore uses shift **1**, despite that legacy metadata label. This is a
serialization defect, not a different executed matrix or a measured physics
failure. Preserve original outputs, annotate this discrepancy, and report the
actual stored factor shift in the corrected CLI. The verified correction stores
the coefficient used to build the matrix, exposes it through `Simulation`, and
uses it for serialization. It preserves the unscreened bytes. New solver/CLI
tests and a 20-evolution baseline comparison cover cached/uncached linear and
quadratic profiles, κ=0/.5/1. Only the documented metadata field may change;
all remaining scientific files must match. REANA completed all 20 evolutions
and all ten comparisons pass. Format, strict Clippy, 135 debug / 143 release
Rust tests, 66 Python tests and M0 checks pass on the same snapshot.
[Exact source, raw data and logs](../tests/reference/m1_projection_metadata/README.md)
retain that verification separately from the ongoing M1 physical campaign.

## Established failure mechanism and scope

The [frozen reconstruction audit](M1_SHOCK_INVESTIGATION.md#measured-reconstruction-input-result)
locates the original stationary planar shock's initial pressure loss in the
incompatibility between its conservative energy flux and the LS-curl magnetic
rate. At cell 253, dE=-42.281594 and dM=-6.926447, so dp=-35.355148 for gamma=2
and zero initial kinetic-energy rate. Neighbour By fits crossing the potential
kink dominate this frozen diagnostic. Independent reconstruction and endpoint
assembly agree with production arithmetic; no missing sign or factor was
identified by those checks. This is not a theorem about the later evolution.

The candidate completes the bounded cases, while the literal planar controls
still fail. The [owner-approved Bx amendment](../benchmarks/m1/shock-bx-amendment.json)
retains the 1e-8 gate on regular and y-invariant column-jitter meshes and records
planar-jitter Bx as a diagnostic. It does not turn planar Bx into a successful
gate or alter the wave, vortex, boost or reference-profile thresholds.

The [full campaign plan](M1_FULL_VALIDATION_PLAN.md) is the remaining physical
acceptance requirement. No result in this audit closes #7, #19–#22 or M1.

## Applicability of the historical prescribed-flow loop packet

The separate serial `constant-flow-voronoi-v1` packet remains applicable to
its original kinematic scope. This is a source-dependency review, **not a
fresh full-ladder execution or proof of current-binary bitwise reproduction**.
The [hash and comparison record](../tests/reference/m1_completion/prescribed/applicability_20261110.json)
verifies all 12 archived files and records 32 completed evolutions, 16 passing
boost pairs, 16 passing comoving checks and two passing refinement ladders.

The driver, `Transport` and divergence diagnostics are byte-unchanged from
the execution archive. The initial loop/reference code and the operator
prefix containing `gradients` and `TransportStencil` also match byte for byte.
Changed `PotentialStage`, Riemann-completion, gauge and projection paths are
not called by this transport driver.

Shared mesh construction now uses independent cell maps, but the driver
never enters a Rayon pool: `parallel::map` takes its ordered serial branch.
Generators, plane order, clipping arithmetic, cell-volume/centroid sums and
final face ordering are unchanged. Per-cell edge maps merge in cell order;
the owner-cell index is part of every key, so different maps cannot collide.
Gradient/limiter expressions and their inner reduction orders are unchanged.
New column, quadratic and positive-Laplacian paths are unused here. Current
mesh thread-equality and transport covariance/refinement unit tests passed
in the cache campaign's workspace checks.

This supports retaining the archived full prescribed-flow results without
rerunning that large independent matrix. It does not substitute for any
coupled MHD wave/loop gate in the new campaign.
