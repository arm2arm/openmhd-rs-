# Issue #4: conservative states and moving-face flux validation

This packet covers the ideal-gas/finite-volume kernels in `mhd-core`, independently of the future general A/gauge integrator. The published flux and wave-speed equations are attributed in [COUPLED_2D.md](COUPLED_2D.md), including [CANS+ equations (18), (45)-(74)](https://www.astro.phys.s.chiba-u.ac.jp/cans/doc/riemann.html). No external solver source is imported into Rust.

## Pressure and energy policy

The original issue mentioned pressure floors. The reviewed [M0 engineering profile](M0_ENGINEERING_DECISIONS.md) supersedes that proposal: require finite positive density/pressure, return errors for inadmissible states, and reject/retry invalid timesteps. Do not add pressure floors or reset conserved cell total energy. Face primitives receive a common arithmetic normal B while retaining their reconstructed gas pressure; their face energies are recomputed for the Riemann problem. Cell closure uses its conserved energy and reconstructed B, so increased magnetic energy reduces available thermal energy and may reject the state.

HLLD's guarded degeneracies/nonpositive intermediate states use a counted two-wave HLL fallback. The fallback must also be finite and admissible or return an error. This is a tested policy, not a proof of positivity for arbitrary data or discretizations.

## Predeclared extension checks

Declared before evaluating the new regression tests or comparing the updated kernels with the independent profiles:

1. Preserve analytic identical-state ALE fluxes, contact and rotational waves. Extend checks to both upwind branches, coordinate rotations, magnetic reversal, induction/EMF boost transforms, and normal reversal. Use relative-plus-absolute tolerance 1e-11 for ordinary states.
2. Check common-normal-B pressure preservation and fixed-cell-energy magnetic/thermal coupling. Reject nonfinite/invalid primitive, conservative and face inputs. Exercise valid low-pressure and zero-field/degenerate cases without floors.
3. Check the fast magnetosonic speed against exact parallel/perpendicular/unmagnetized limits, including pressure scales 1e-200 and 1e200 at rho=1. Require relative error <=1e-12 for the speed when the expected result is representable. Avoid avoidable squaring overflow/underflow; unrecoverable states still return errors.
4. In the separate 1D conservative-induction driver, evolve Brio-Wu on periodic [0,2], interface x=1, gamma=2, Bx=.75, at total N=512/1024/2048 through t=.1 with first-order spatial states and synchronized Heun time integration. Use CFL .3 with endpoint rechecking and counted half-step retries; no A/curl or Voronoi geometry enters this fixture. Compare x in [.5,1.5] with the pinned independent Athena++ 8192-cell unit-domain profile from the M0 archive, averaging fine reference cells over each candidate cell interval. The reference coordinates are already shifted to [.5,1.5].
5. For each rho/p/vx/By profile report L1 and L2 normalized by the fixed unit scales in the M0 packet. Require finest L1 < .03/.04/.03/.04 respectively and lower than coarsest. These limits are reused from M0; the driver and resolution ladder are this explicitly separate kernel-validation case, not a run of `paper-global-v1`.
6. Require finite positive density/pressure in accepted stages, periodic conservative budgets <=1e-10, unchanged Bx, and integrated maximum face-relative signal travel <.45 so the second periodic interface cannot reach the analysis region. Record fallback and rejection counts. A joint fluid/grid x-boost of +2 at N512 must reproduce comoving rho/p/B to 1e-10 after transforming velocity and energy appropriately.

In this one-dimensional fixture both the cell-centred and arithmetic-face divergence of the constant Bx are identically zero; By is evolved conservatively. This says nothing about unstructured multidimensional div(curl(A)). The independent reference uses Athena's HLLD implementation and PLM reconstruction, while this driver uses our implementation and piecewise-constant spatial states. Finite-resolution errors and the reference's own refinement uncertainty must be reported separately.

## Reproduction and evidence

The extension tests, study script and measured table will accompany the completed issue. The M0 reference archive is immutable and checksummed; it is not regenerated or adjusted to match the Rust results.
