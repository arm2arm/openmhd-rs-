# Issue #6: measured 2.5D operator/coupling results

The [registered paper-global-v2 contract](VECTOR_POTENTIAL_REFERENCE.md) was evaluated from clean revision `d67e5c052ff4d877e82941e536af9681adc99520`. All 27 registered runs pass their unchanged gates. Two additional review-triggered runs expose a **nonuniform mean-field boost discrepancy**, reported below. This is bounded acceptance of the serial 2.5D operators and coupling, not full M1 or general Galilean-invariance validation.

The [archive](../tests/reference/vector_potential/) contains machine-readable results, source/compiler/command provenance and selected compressed snapshots. Run `python3 scripts/run_vector_potential.py` to regenerate all outputs. Units are dimensionless, mu0=1, gamma=5/3, periodic unit square, f64, one serial rank/thread. The toolchain is pinned Rust 1.85.1; the archived host is macOS arm64. Generator jitter is deterministic trigonometric displacement, not an RNG seed. See the contract for all initial states, amplitudes, operators, boundary conditions and timestep limits.

## Curl convergence

For A=.001(sin(2pi*y),cos(2pi*x),sin(2pi*x)sin(2pi*y)), errors compare the **initial discrete** three-component B against its analytic curl. These are volume-weighted vector norms, not evolved physical errors.

| Jitter | N | L1 | L2 | L1 order from previous N | L2 order |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 8 | 7.20282e-4 | 7.67096e-4 | — | — |
| 0 | 16 | 1.84395e-4 | 1.96266e-4 | 1.966 | 1.967 |
| 0 | 32 | 4.63661e-5 | 4.93511e-5 | 1.992 | 1.992 |
| .15 | 8 | 8.83008e-4 | 9.17010e-4 | — | — |
| .15 | 16 | 2.52780e-4 | 2.65723e-4 | 1.805 | 1.787 |
| .15 | 32 | 8.51185e-5 | 9.20091e-5 | 1.570 | 1.530 |

Every regular order exceeds 1.8 and every jittered order exceeds .7. No universal second-order irregular-mesh claim follows. Supplied analytic Hermite jets reproduce tensor cubics/physical derivatives to the 1e-11 algebra tolerance; periodic C1, root 4/2/1 fallback and weighted membership tests pass. The separate centred-difference-jet unit study has RMS derivative errors .13109, .040708, .010720 for 8/16/32 intervals (orders about 1.69, 1.93); finite-difference jets are not arbitrary-cubic-exact.

## Uniform mean field and registered boosts

All four uniform regular/jittered fixed/rigid cases through t=.05 preserve physical states to 5.56e-17 maximum absolute difference. A follows the required `v cross mean_B` drift to 6.60e-17. The nonuniform **mean-zero** boost pair through t=.02 has maximum transformed physical/energy error 4.67e-15 (regular) and 3.56e-15 (jittered), against the 1e-9 gate. Repeated auxiliary roots agree and translated origins agree within 4.45e-16.

## Longitudinal gauge mode

N16, t=.05, cs=1; errors use the exact same-grid damped mode with k_eff=16*sin(2pi/16). Limiting enabled/disabled give the same listed A/phi errors because this fixture isolates raw cleaning derivatives.

| dt cap | A L2 | phi L2 | A order | phi order |
| ---: | ---: | ---: | ---: | ---: |
| .001 | 9.79614e-9 | 8.56914e-8 | — | — |
| .0005 | 4.75640e-9 | 4.31128e-8 | 1.042 | .991 |
| .00025 | 2.34299e-9 | 2.16231e-8 | 1.022 | .996 |

The finest orders lie in the declared [.8,1.2] interval. Maximum physical |B| is below 2.95e-20 on the regular mesh. This confirms the documented first-order property of frozen C1; it does not claim a fully second-order gauge integrator.

The separate jittered run starts with discrete |B|max=1.61323e-4 despite analytically longitudinal A. Its subsequent maximum vector B change is 1.99845e-5; the maximum of |A| and |phi|/cs stays below 9.477e-4 (<.002). This is a coupled cleaning run, so the total magnetic change is not attributed exclusively to one term. Gas remains finite/positive. Discrete curl(grad phi) is not assumed to vanish on this mesh.

## Deforming geometry

N6, t=.04, prescribed nonuniform generator velocities and initially uniform physical state. The physical error below is the maximum absolute error over rho,p,v3,B3; density dominates. The geometric error is the maximum **single accepted step** volume residual defined in the contract, normalized by old cell area. These are different quantities.

| dt cap | Physical error, limited | Unlimited | Step geometric error | Physical orders, limited/unlimited | Geometric order |
| ---: | ---: | ---: | ---: | ---: | ---: |
| .004 | 2.42240e-8 | 2.44044e-8 | 2.63731e-9 | — | — |
| .002 | 6.04785e-9 | 6.09515e-9 | 3.30802e-10 | 2.002 / 2.001 | 2.995 |
| .001 | 1.51095e-9 | 1.52304e-9 | 4.14221e-11 | 2.001 / 2.001 | 2.997 |

Both reconstruction variants meet finest-error < coarsest-error. No machine-zero geometric-conservation claim is made. Separate tests exercise a topology-changing endpoint, motion exceeding a periodic box, new A/phi endpoint fits, frozen C1, equal/opposite exchanges and rejected-trial immutability including the auxiliary origin.

## Diagnostics and execution checks

Across all 29 runs, the maximum normalized mass/momentum/energy budget residual is 1.237e-15; minimum density is .9998407 and minimum pressure .0099999986. No floor or magnetic-energy repair exists. There were 76 endpoint-CFL rejections, zero invalid-state/geometry rejections and zero successful HLL fallbacks in this smooth packet. Rejected-state and HLL fallback paths are exercised by separate deterministic tests. All evolved packet runs select root 4; roots 2/1 are tested by empty-bin fixtures. Worst final neighbour/face covariance conditioning indicators are 4.093/4.319.

The three B-divergence operators remain measurably different. For the jittered N8 mean-zero smooth run at t=.02:

| Operator | Dimensional RMS | Dimensionless RMS | Dimensionless max |
| --- | ---: | ---: | ---: |
| Raw neighbour LS | .00164572 | .0230451 | .0971999 |
| Arithmetic face flux | .00232784 | .0320683 | .127854 |
| Separately limited face flux | .00490428 | .0653164 | .156887 |

The archive includes signed means, maxima, div(A)/phi, magnetic energy and mean-B drift for every run. These diagnostics do not imply machine-zero divergence.

Validation passed: `cargo fmt --check`; `cargo clippy --all-targets --all-features -- -D warnings`; locked workspace build; **70 Rust tests**; 13 M0 algebra checks; the independent-reference archive checker; four Python comparison tests; and the clean 29-run study. The [separate AI review](VECTOR_POTENTIAL_AI_REVIEW.md) records its scope and additional probes. Human peer review and author confirmation have not occurred.

## Observed limitation and next gate

The additional unit-square N8 jittered mean-field pair uses the smooth gate6 initial state but mean_B=(.3,.2,.1), t=.02 and boost (2,-1,0) with matching rigid mesh translation. Both take 18 accepted steps. Maximum differences are rho 6.01e-8, p 2.61e-6, vz 5.29e-7 and **Bz 3.93966e-5**. This is an observed failure of broad invariance expectations, outside the original mean-zero boost gate. It has not been relabelled a passing physical test.

The independent reviewer also found B-component differences near 1.99e-5 at t=.01 on rectangular deforming geometry with nonzero mean B, nonzero phi and a three-component boost. The otherwise matched zero-mean probes agree to roundoff. A noncommuting discrete curl/gradient response to mean-field-induced gauge drift is a possible explanation, not a verified diagnosis.

Issue #7 must investigate this discrepancy and measure refinement before claiming general invariance, alongside the Alfvén/field-loop benchmark matrix. Shock/vortex comparisons for this general integrator also remain open. 3D, adaptive auxiliary trees, MPI/Rayon, local steps, remapping and checkpointing remain later work.
