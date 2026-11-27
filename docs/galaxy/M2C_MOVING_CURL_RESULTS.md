# M2c moving-curl results

The periodic point-curl derivative passes the registered smooth-motion tests. The same point-curl reconstruction fails the configured magnetic mean at initialization on all three jittered mesh families. These measurements address different questions. The derivative checks how the operator changes with geometry. The initialization check tests whether the operator can supply a physically admissible periodic field for a moving run.

## Point-curl derivative

For fixed real-owner potential samples, the implementation differentiates the free-intercept weighted quadratic fit using its original scaled pivoted QR factors. It includes centroid motion, volume scaling, inverse-distance weights and the least-squares residual. The transpose and volume-weighted diagonal operate on real-owner coefficients after combining repeated images and the baseline sample. Each operator belongs to a single validated geometry epoch and prescribed velocity field. [Implementation](../../crates/mhd-vector-pot/src/operators3/motion.rs) · [Protocol](M2C_VALIDATION_PROTOCOL.md).

All 10 selections passed in separate REANA workflows. On the 27-cell periodic deformation, the maximum scaled error against central differences of independently rebuilt endpoint curls decreased from 4.95724×10⁻⁶ at step 1/16 to 1.21001×10⁻⁹ at 1/1024. The six successive orders ranged from 1.99996 to 2.00036. The finest-error limit was 10⁻⁷. The largest local scaled QR condition estimate was 10.80. Separate tests covered the polynomial chain rule with moving samples, volume-weighted diagonal, transpose, constants, rigid motion and stale geometry/velocity rejection. The remote reduction and portable replay agree. [Numerical results and workflow IDs](results/m2c_moving/point-cdot.json) · [Raw cases, native executable and build receipts](results/m2c_moving/point-cdot.tar.gz) · [Reduction receipt](results/m2c_moving/point-cdot-reduction-workflow.json).

## Magnetic mean before the first moving timestep

Each of the 24 workflows used the original native M2b field and Voronoi volumes. The table gives the largest component of the volume-weighted mean error divided by 2π, taking the worse of the two imposed means. The registered limit is 10⁻⁹. Both imposed means passed on every regular mesh and failed on every jittered mesh. Exact rational summation of the stored binary64 words confirms the offset. [All measurements](results/m2c_moving/initial-mean.json) · [Original and new workflow receipts](results/m2c_moving/initial-mean.tar.gz).

| Mesh family | 8³ cells | 16³ cells | 32³ cells |
| --- | ---: | ---: | ---: |
| Regular | 1.688e-17 | 7.625e-18 | 1.155e-17 |
| Original jitter | 2.913e-04 | 5.649e-04 | 4.713e-05 |
| Fresh jitter A | 6.855e-04 | 1.800e-04 | 2.614e-05 |
| Fresh jitter B | 2.186e-03 | 7.880e-04 | 1.895e-05 |

## Shared-face candidate

`periodic-shared-face-quadratic-curl-v1` retains the potential as a centroid point sample. It integrates each owner's quadratic over the actual polygon using its surface covariance, averages the two face values, and applies one signed curl exchange to both adjoining cells. The magnetic result is a cell average. Its acceptance depends on its own reconstruction, moving derivative, field evolution and energy tests. [Rust interface](../../crates/mhd-vector-pot/src/operators3/shared_face.rs) · [Validation protocol](M2C_SHARED_FACE_VALIDATION.md).
