# M2c prescribed centroid and volume rates

## Scope and prerequisites

This is the first M2c implementation, the S-CENTROID gate on a single validated geometry epoch. The generator velocities are prescribed instantaneous velocities keyed by persistent cell ID. A bounded cuboid can have stationary walls or a uniform translational wall velocity. The reference uses binary64, unit lengths and times in the manufactured cases, and the accepted serial half-space oracle. The outputs are a normal speed and its tangential gradient on every shared face, an oriented volume flux, and each cell's volume derivative and physical centroid velocity. [M2a decision](../../tests/reference/m2a_static_geometry/acceptance.json) · [M2b decision](../../tests/reference/m2b_static_operators/acceptance.json) · [S3 and S4 derivation](MOVING_MHD_STAGE_SPEC.md#3-actual-centroid-velocities-and-differentiated-curl) · [Independent equation review](MOVING_MHD_STAGE_DESIGN_REVIEW.md).

For a Voronoi bisector, use the generator separation in the actual periodic image, the canonical left-to-right normal, the area centroid and the area-averaged central covariance of the face. Integrate the affine normal speed over the face once. In the first-moment integral retain the product of face covariance and tangential speed gradient. Accumulate signed incidences in their own charts, including both lifts of each periodic self-face. A physical wall has constant normal speed and zero tangential gradient. These rates apply on smooth topology intervals. Curl-map differentiation, finite-step geometric conservation and event handling have their own gates.

## Independent oblique-box reference

In a stationary unit cube put left and right generators at $(1/4,7/16,3/8)$ and $(3/4,9/16,5/8)$. Prescribe velocities $(1/8,3/16,-1/16)$ and $(-1/16,-1/8,1/16)$. Write the bisector as the graph $x=F=a-P(y-1/2)-Q(z-1/2)$. The left cell is $0\le x\le F$. Integrating columns over the square gives

$$
V_L=a,\qquad I_L=\int_L \boldsymbol{x}\,dV=
\left(\tfrac12[a^2+(P^2+Q^2)/12],\ a/2-P/12,\ a/2-Q/12\right).
$$

The right cell has the complementary moments of the cube. At zero time $P=1/4$, $Q=1/2$, $a=1/2$ and $(\dot a,\dot P,\dot Q)=(5/128,-17/32,7/16)$. Thus $\dot I_L=(41/1536,49/768,-13/768)$ and $c_L=(53/192,11/24,5/12)$. These integrals give both analytic centroid velocities by the quotient rule without using the candidate face operator. The same graph gives the normal speed at each vertex by differentiating $F$ at fixed $y,z$. Throughout the registered small time interval the graph stays strictly between zero and one on every square corner.

Run all six xyz permutations. For each permutation and each spacing $h=2^{-5},2^{-6},\ldots,2^{-11}$ use a **separate REANA workflow**. Rebuild both endpoint meshes from the given positions and velocities. Require the same face-key inventory as at zero time. Measure both cell volumes and physical centroids at $-h,0,+h$. Compare the instantaneous candidate rates against the literal analytic rates to absolute $10^{-10}$ and retain all components. Compare central finite differences of the rebuilt values against the instantaneous rates. For each permutation, the maximum component error over both cells must decrease with observed order at least 1.8 on every adjacent pair and finish at or below $10^{-7}$, separately for the volume and centroid derivatives. The largest centroid–generator velocity difference and the largest change when the covariance term is deliberately omitted must each exceed $10^{-2}$ in this fixture. Run the reducer on the raw records, recomputing the exact column integrals at each endpoint from the original dyadic inputs.

## Additional controls

Run each control in its own workflow. Check the periodic one-cell self-image translation, the two-owner periodic slab across the seam with nonzero windings, a stationary single cell with moving generator and fixed walls, rigid translation of a complete bounded box, a joint boost of the deforming box, velocity catalog and finiteness errors, overflow rejection, and rejection of cell/face handles from a different epoch. Rigid and analytic controls use absolute error at most $10^{-10}$ on the stated scales. Check the shared interior volume fluxes cancel and distinguish generator and centroid motion. Every case requests 1 CPU, 4 GiB and a 15-minute envelope. Only the frozen, formatted, strict-Clippy-checked release test binary may supply the records.
