# Scientific validation and reproducibility

Successful execution is not equivalent to a correct physical solution. All results must be compared to analytical, converged, or published reference calculations and archived with configurations and code revision.

## Physics benchmark matrix

| Benchmark | Main quantitative check | Earliest milestone |
|---|---|---|
| Hydro smooth wave and shock tubes | `L1/L2` convergence; Rankine–Hugoniot; budgets | M1 |
| Circularly polarized Alfvén wave | Expected second-order error trend with resolution | M1 |
| Brio–Wu MHD shock tube | B, density, velocity and energy profiles vs references | M1 |
| Magnetic flux-loop advection | Field topology, energy, boosted vs unboosted error | M1/M2 |
| 2D Orszag–Tang vortex | Density/magnetic slices, energy history, stability | M1 |
| 3D vortex/field advection | Structure, spectrum, stability and 3D boost | M2 |
| MHD blast wave | Shock symmetry, no negative pressure, conservation | M2 |
| Magnetorotational instability | Linear growth vs theory once physical setup is ready | M4 |
| Magnetized gravitational collapse | B amplification and flow/outflows after gravity exists | M4 |
| Local timesteps/refinement | Reference to synchronized, fixed-resolution runs | M4 |
| MPI and Rayon invariance | Match physical diagnostics vs 1-rank reference | M3 |

## Diagnostics required in every physics case

- Integrated mass, momentum and total-energy budgets, including boundary/source terms.
- Volume-weighted magnetic energy and extrema; minimum density and thermal pressure.
- Magnetic divergence with **two explicitly labeled discrete operators** (solver-associated and independent flux-based).
- Gauge residual/cleaning behavior of A and correlation with physical field metrics.
- Galilean boost comparison after appropriate coordinate transformation.
- Mesh quality, ill-conditioned least-squares stencils, near-degenerate cell counters.
- Provenance: git revision, configuration, random seed, compiler flags, ranks/threads, hardware.

## Acceptance protocol

1. Declare resolution ladder, fitted convergence range and pass thresholds before using them to judge new code.
2. Fit smooth-wave error order and report uncertainties; second-order behavior is a proposed target.
3. For boosted runs, compare in equivalent physical coordinates at matched times.
4. For periodic conserved quantities, quantify any residual non-conservation and its change with refinement.
5. MPI/Rayon comparisons should allow numerical summation-order differences; byte-identical results are not required.
6. Do not test MRI and collapse as release gates until necessary physics and boundary conditions exist.

Large snapshots may be external, but scripts, small reference fixtures, checksums and quantitative tables belong in the repository.
