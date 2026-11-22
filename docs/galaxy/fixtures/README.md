# Analytic 3D geometry fixture design, v1

This packet freezes exact inputs and analytic expectations for the first
geometry implementation. **It contains no implemented geometry builder,
executed numerical test, REANA result or M2 acceptance.** M1 remains the
first prerequisite. The packet covers the base analytic G01 family from
[the mesh contract](../MESH_3D_SPEC.md), with an additional oblique two-cell
case. Jitter/degeneracy, operators, motion and coupled physics remain separate
registered work; this is not a substitute for the complete M2 matrix.

`geometry3_analytic_v1.json` specifies all generator coordinates exactly:
small Cartesian products use explicit rational axis arrays and an unambiguous
x-fast ID order. This defines a complete point set without a random generator.
The future runner must archive its expanded point arrays and actual f64 bits.
Every scale, translation, coordinate permutation and backend case runs in its
own REANA workflow after the new source preflight. The current packet is
design data, outside the frozen M1 source/benchmark directories.

The reference reduction must be independent of the candidate's clipping,
polygon integration and connectivity code. It may use exact rational and
high-precision algebraic arithmetic on these expectations. Syntax/hash checks
of this packet are not numerical validation of its formulas. Independent
mathematical review and REANA fixture/reference checks are still required
before the expectations are used to accept a new builder.

## Exact derivations

For a Cartesian product of generator axes, squared distance separates by
coordinate, so each Voronoi cell is the product of the one-dimensional
nearest-generator intervals. Boundaries are adjacent midpoints; periodic
end intervals use the neighbouring image. A width `h` has midpoint centroid
and central per-volume second moment `h^2/12`. Thus
`V=hx*hy*hz`, `J_aa=V*ha^2/12`, `J_ab=0` for a != b. The packet stores
volume-integrated J, not its per-volume value.

In the 3x2x2 case, the x intervals are `[-1/16,1/4]`, `[1/4,9/16]` and
`[9/16,15/16]`; widths are `5/16,5/16,3/8`. The first two centroids are
`3/32,13/32`, distinct from their generators `1/8,3/8`. In the 4x4x4
nonuniform case, the cyclic generator gaps are exactly `1,2,3,4` divided by
10. Its first centroid is `-1/40` in the owner's unwrapped chart, although
its generator is `1/20` inside the primary box. Wrapping that centroid and
discarding its image would change the reconstruction displacement.

A one-cell periodic cube has three canonical self-image faces and six cell
incidences. The two incidences of a face belong to the same real cell in
different image charts; the face's net conservative incidence is zero.
For 2x2x2 there are 24 canonical shared faces, not 12: each pair along an
axis has both an internal and a distinct periodic face. Collapsing images
by neighbour ID loses half the geometry. The two 4x4x4 products each have
192 shared faces and 384 oriented incidences. These are exact topology
expectations, not measured counts.

For the bounded one-cell box the generator has no effect on the shape:
the physical cuboid is the cell. Side lengths `(2,3,4)` give volume 24 and
central moments `(8,18,32)`. Its six physical boundary fragments carry
geometry only; no hydro/MHD wall condition is inferred from clipping a box.

For the oblique fixture, generators `(1/4,1/4,1/4)` and `(3/4,3/4,3/4)`
split the unit cube at `x+y+z=3/2`. Reflection through the cube centre swaps
the cells, giving volume 1/2 each. Write `S=x+y+z` and let D be the lower
cell. Inclusion/exclusion of the unit-cube corners gives

```text
V(D) = ((3/2)^3 - 3*(1/2)^3)/6 = 1/2
integral_D (3/2-S) dV = ((3/2)^4 - 3*(1/2)^4)/24 = 13/64
integral_D S dV = (3/2)*(1/2)-13/64 = 35/64
integral_D x dV = 35/192, hence c_x=c_y=c_z=35/96.
```

Using the reflection and the full-cube integrals `integral x^2=1/3` and
`integral xy=1/4` gives
`integral_D x^2=19/192` and `integral_D xy=11/192`.
Subtract `V*c_a*c_b`: central J has diagonal `599/18432` and off-diagonal
`-169/18432`. The upper cell has centroid `(61/96,61/96,61/96)` and the
same central moment tensor. Nonzero cross moments detect an implementation
that treats every shape as an axis-aligned box.

The common regular hexagon has side length `1/sqrt(2)`, area
`3*sqrt(3)/4`, centroid `(1/2,1/2,1/2)` and normal `(1,1,1)/sqrt(3)`
from the lower-ID cell. Its stored vertex order has outward winding.
On a lower-cell minimum-coordinate wall, the polygon is a unit square
minus an upper triangle of area 1/8, so its area is 7/8 and its two tangent
centroid coordinates are `19/42`. On a maximum-coordinate wall it is the
triangle of side 1/2, area 1/8 and tangent centroid `(1/6,1/6)`.
Reflection gives the other cell's face data. For example the x component
of lower-cell normal closure is `-7/8+1/8+3/4=0`.

The packet preserves the mesh contract's normalized `1e-10` analytic
geometry gates. Length rescaling changes areas, volumes and central J by
squared, cubed and fifth powers respectively. Coordinate permutations also
permute both tensor indices; an odd permutation requires reversing the
polygon loop to retain outward winding. Raw unit-dependent tolerances and
absolute determinant values must not conceal an orientation error.
