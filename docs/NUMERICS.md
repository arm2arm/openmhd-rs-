# Numerical-method specification (draft)

> This is a **planning specification**, not a complete transcription of Springel, Mayer & Pakmor (2026). M0 must verify every paper-specific equation, term, sign, numerical operator, timestep stage and parameter using the **full text**, not only the abstract.

## Governing equations

Use ideal MHD in units with magnetic permeability `μ0=1`. For density `ρ`, velocity `v`, pressure `p`, magnetic field `B` and adiabatic index `γ`, the conserved fluid state is:

```text
U = (ρ, ρ v_x, ρ v_y, ρ v_z, E)
E = p/(γ−1) + 0.5 ρ |v|² + 0.5 |B|²
∂t U + ∇·F(U,B) = 0
B = B_mean + ∇×A
∇·B = 0    (continuum constraint)
```

A discrete implementation of `div(curl(A))` does not necessarily vanish for arbitrary irregular-cell operators. We must identify the exact discrete identity and report independent divergence diagnostics.

## Coupled algorithms

1. **Gas finite volume:** conservative mass/momentum/energy cell integrals; face-area fluxes in each moving face's rest frame; HLLD-style Riemann solver with positivity/fallback handling.
2. **Magnetic field:** cell-centred vector potential `A`, evolved via the paper's *specific* gauge, advection, smooth auxiliary velocity and cleaning discretization (do **not** substitute a generic induction equation).
3. **Field reconstruction:** compute `B` from a documented, conditioned discrete curl of `A`, adding any periodic mean/background field consistently.
4. **Geometry:** compute oriented faces, areas, volumes, centroids, mesh/face velocity and reconstruction stencils; update Voronoi topology when generating points move.
5. **Integration:** first implement globally synchronized second-order stages with correct mesh/field ordering; later introduce power-of-two local timesteps.
6. **Adaptive changes:** conservative transfers for gas variables and carefully defined A/mean-flux handling when cells are inserted/removed.

## M0 equation-to-code traceability

Before numerical coding, record source equation/page and exact pseudocode for:

| Topic | Must specify |
|---|---|
| Vector-potential gauge | Complete `D_w A/Dt` evolution, gauge scalar `φ`, signs, any non-conservative terms |
| Smooth auxiliary velocity | Differentiability, interpolation/smoothing, periodic handling, spatial gradients |
| Discrete curl and divergence | Stencils, least-squares conditioning, discrete identities, cell/face reconstruction |
| Periodic mean magnetic flux | `B_mean`, background correction and gauge compatibility |
| Fluid solver | Moving-face flux transform, normal field, positivity and robust fallbacks |
| Energy coupling | Consistency of conservative total energy with reconstructed magnetic energy |
| Cleaning | Cleaning equations, wave speed/damping, CFL restrictions, boundary conditions |
| RK stage sequencing | Exact tessellation/field/flux/curl order per stage |
| Refinement & local steps | Transfer operators, deferred fluxes, stage synchronization |

## Unit/integration tests

- Uniform states and constant/linear vector potentials produce expected derivatives and zero-update limits.
- Analytic `A` fields have convergence-tested curls under mesh refinement.
- Equal-and-opposite shared-face fluxes give correct total mass/momentum/energy budgets.
- Galilean boosts preserve solution in appropriately shifted/comoving coordinates.
- Cleaning controls gauge noise without unexpected changes to physical magnetic observables.
- Changing topology and mesh degeneracies are monitored, not silently ignored.

## Known risks

A cell-centred least-squares curl is **not** automatically the same as machine-precision constrained transport. Correctly reproducing the published stable gauge and coupled integrator is the central scientific challenge. The initial 2D baseline does not establish correctness in the target 3D moving Voronoi method.
