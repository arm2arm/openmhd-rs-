# M2b static-operator qualification, revision 2

Frozen before executing the new comparisons. This protocol retains the original O01, O02 and O03 results at 89fccf1. The original O02 verdict is failed. The named production candidate remains the unlimited quadratic centroid point curl. All measurements here apply to static periodic meshes. M2c owns the moving-stage update.

## Fields and face sampling

Retain the original raw one-ring linear and two-ring quadratic point fields and their arithmetic-face, limited-face and separate cell-fit divergences. Also measure a curvature-corrected one-ring gradient. For each component of the point potential, form the quadratic fit on its existing support. Subtract $\tfrac12 d_j^T H d_j$ from each original one-ring point sample, then apply the original area-weighted linear fit to the corrected observations. Take its curl and add the imposed mean. The fitted Hessian $H$ uses only numerical potential samples. The correction removes the leading curvature term that an asymmetric stencil aliases into its linear gradient. This diagnostic uses two rings in total. The single-ring raw estimate remains in the output as a comparator.

For each recovered field retain the original arithmetic face mean. Also evaluate a shared value at the physical face centroid using
$$
 B_f^{s}=(B_L+B_R)/2 + (J_L+J_R)\,[x_f-(x_L+x_R)/2]/2 .
$$
Here $J$ is the independent linear fit to neighbouring recovered magnetic samples. The two cell centroids use one periodic image chart. The formula reproduces affine fields at the face centroid, equals the original mean on an orthogonal midpoint face, and uses one flux with opposite incidences. This extra operator has a separate output column. An independent NumPy fit and surface sum check the actual Rust fields.

## Selections and decision

Use the released unit cube, potential, two mean fields, 15% coordinate jitter and $8^3,16^3,32^3$ meshes. Run the regular family, the original SHA-256 jitter key 20261122 and two new fixed keys 2026112701 and 2026112702. Retain the existing key format and generator ordering. All four families use both means, for 24 workflows. Run three regular unequal-wave-number controls with $A_z=\sin(2\pi x)\sin(4\pi y)$ and zero mean. Each selection requests two CPUs and 8 GiB, after a frozen build and independently executed polynomial and face controls. The original 87 O01 and 74 O03 cases remain prerequisites. Compare matching original case inputs and raw output columns against their released arrays.

* The quadratic and curvature-corrected point curls each require volume-weighted relative $L_1$ order at least 1.8 on the three original-field mesh sizes and finest relative error at most 0.1. Use the analytic fluctuating field in the denominator. Require finite diagnostics, normalized signed shared-face sums at most $10^{-12}$ and unchanged results when independently re-reading the output.
* For both these fields and every jitter key, BOTH the original arithmetic-face and the skew-corrected dimensional divergence RMS must decrease at each refinement, for each mean. A global signed sum, a scaled norm or a same-Hessian identity cannot earn this pass. Report all results for the original raw linear fit, including any failed original criterion.
* The original-field cubic control has exact symmetry cancellation. Centered first differences commute, subtracting an even quadratic term from opposite samples leaves the linear slope unchanged, and the equal wave numbers cancel by axis exchange in the quadratic stencil. On this family alone, require all three levels below the explicit absolute numerical budget $128\epsilon[(2\pi+\lVert B_0\rVert)/h+1/h^2]$, with binary64 epsilon and $h=1/N$. The terms cover roundoff in a face difference of a magnetic sample and two differences of a unit potential. This is a restricted test tolerance. Record actual absolute residuals. The unequal-wave-number cubic control separately requires strict decreases for the quadratic arithmetic and skew fluxes and tests the equivalent commuting linear stencils against the same roundoff budget.
* On the original-field jittered finest meshes, require the skew correction applied to the sampled **analytic** magnetic field to reduce the RMS relative to the arithmetic face mean. This reference uses separate analytic magnetic *values* and independently fitted gradients. It diagnoses the effect of the sampling point independently of the point-curl recovery.

Publish per-case source/input/UUID/output identities, uncertainty/limitations and every failed comparison. A revised qualification is a separate decision from passing historical O02. Morphing cells, walls, conservation in time and full MHD benchmark acceptance require their own campaigns.
