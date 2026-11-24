# O01 manufactured 3D operator inputs

The O01 source defines 84 polynomial cases and three overdetermined stencils
with deficient rank. It prepares the analytic side of the first M2b gate.
The Rust operator comparisons depend on G02–G04. No O01 numerical result or
M2b acceptance is recorded here. [Registered operator gate](MESH_3D_SPEC.md#9-prospective-reana-fixtures-gates-and-dependencies).

Each full-rank case places a scalar polynomial in one vector-potential
component, with zero mean field. The linear fit uses 1, x, y and z. The
quadratic fit adds x²/2, y²/2, z²/2, xy, xz and yz. The polynomial is
evaluated at the actual lifted sample positions. Exact rational
differentiation supplies the intercept, gradient, curl and divergence at
the evaluation point. Quadratic cases also retain the full Hessian, the
Jacobian of the curl, and its trace. All input and expected values are
encoded as binary64 words. [Fixture generator](../../scripts/geometry3_operator_fixtures.py).

| Layout | Samples and expected behaviour |
| --- | --- |
| Synthetic local chart | 26 sheared offsets near a periodic seam. Wrapped coordinates and integer images identify each lifted sample. Polynomial values belong to this chart. |
| Bounded Cartesian interior | The centre of a 5³ cube lattice with spacing 1/4. The six adjacent cells have face area 1/16. The quadratic stencil includes those cells and the 18 cells in the second face-adjacency ring. |
| Plane | 24 coplanar samples. Expected design ranks are 3 for the linear basis and 6 for the quadratic basis. |
| Shell | 12 samples with squared displacement 1/32. The quadratic design has rank 9 because its squared-radius column combination is constant. |

The packet includes positive objective weights for the linear samples and
squared distances for the quadratic inverse-distance weights. Exact
elimination checks the design rank. A Rust evaluation still needs its own
rank and condition decisions, physical derivative rows and measured errors.
The registered reproduction limit uses `max(1e-10, 64 ε κ)` times the
analytic derivative scale.

To prepare the REANA specifications in a fresh folder, run the following
command. It writes one import preflight, two independent reference controls
and one fixture-generation specification per selection.

```sh
python3 -B scripts/prepare_geometry3_operator_fixtures.py results/o01-fixtures
```

The controls check curl signs for all component placements, reconstruction
of lifted points across a seam, the bounded neighbour rings and independently
known ranks. [Control source](../../scripts/test_geometry3_operator_fixtures.py).
