# Single-threaded 3D Voronoi backend comparison

Keep `HalfSpaceOracle3::build_motion_epoch` as the qualified moving-mesh rebuild. The upstream `meshless_voronoi` 0.7.2 backend was much faster on the ten measured inputs. With two generators separated by (2^{-32}) box widths it exceeded the registered face, volume and closure tolerances. Both implementations found the same positive-area face keys on that input. The benchmark crate and its locked dependencies are isolated from the application. [Benchmark protocol and executable](../../benchmarks/m2/backend/README.md)

## Measured construction times

Each entry is the elapsed time in seconds inside a release executable running in its own one-CPU REANA workflow. The original and pruned project implementations compute validated shared faces and moments. The upstream time includes building convex cells, finding their faces and integrating native volumes and centroids. Each selection ran once. The comparison includes the cost of each implementation’s actual responsibilities, and gives no estimate of run-to-run variance.

| Unit-box fixture | Unpruned oracle | Motion-epoch oracle | meshless_voronoi |
| --- | ---: | ---: | ---: |
| Periodic cube, 8 sites | 0.0862 | 0.0389 | 0.00218 |
| Periodic cube, 64 sites | 6.083 | 0.510 | 0.00737 |
| Periodic cube, 512 sites | — | 15.150 | 0.0505 |
| Jittered periodic, 27 sites | 3.341 | 3.342 | 0.00245 |
| Deformed second epoch, 27 sites | 3.311 | 3.268 | 0.00225 |
| Jittered bounded, 27 sites | 0.261 | 0.261 | 0.00196 |
| Nearly coincident pair, 27 sites | 3.425 | 3.371 | 0.00240 |

All 29 geometry processes returned zero. The independent comparison accepted 28 geometry outputs. It checked the original position bits, positive-area directed face keys, periodic images, opposite incidences, outward normals, polygon boundaries, face and cell centroids, domain volume and area closure. The single-site torus and both epochs across a periodic seam passed for every backend. The project builder passed each of its selected fixtures. At 512 sites the previously qualified exact-pruning motion builder provided the reference. [Individual numerical results](../../tests/reference/m2_backend_benchmark/comparison.json)

On the near-pair input, the maximum upstream polygon discrepancy divided by the reference cell length was 9.13e-7 against a limit of 1e-9. The maximum relative cell-volume difference was 1.05e-8, and area closure divided by surface area reached 1.15e-8 against 1e-10. The measured speedup on a regular mesh therefore does not qualify this external backend across the full benchmark domain. The project’s all-pairs loop has a quadratic candidate count before clipping. Its exact motion pruning benefits the aligned grids in this sample and has little timing effect on the irregular cloud. The external implementation uses a spatial neighbour search. [Pinned upstream source](https://docs.rs/crate/meshless_voronoi/0.7.2/source/) · [License and notice review](MESH_NOTICE_REVISION_REVIEW.md)

## Moving-MHD prerequisite

A separate thirtieth workflow requested the original shared-polygon derivative at the first stage of the registered 4³ periodic sine-shear problem. The executable returned 1 with `non-simple moving periodic vertex`. It counted 768 multiply supported face–vertex incidences. This is a measured failure of the time-zero stage. Running the other 29 geometry benchmarks to completion does not qualify field advection, blast or vortex evolution.

The workflow inputs, build commands, source identities, raw polygon words, original error, comparison output and their digests are retained together. [Evidence index](../../tests/reference/m2_backend_benchmark/index.json) · [Complete recorded outputs](../../tests/reference/m2_backend_benchmark/evidence.tar.gz)

## Transient three-dimensional face reference

All 108 independent S20 reference workflows completed on REANA from commit
`132620df41d7a87449ff875e2b5a9adee982ad87`. The 69-site inputs cover
three perturbation magnitudes, three centre offsets, six axis permutations,
and both bounded and periodic domains. Each certificate verifies the two
contact times, the interior triangular face, and exclusion by competing sites
using the actual binary64 input words. The [workflow index](../../tests/reference/m2_transient_face/index.json)
and [raw certificates and inputs](../../tests/reference/m2_transient_face/evidence.tar.gz)
record the original UUIDs and hashes. This establishes the independent
geometry reference for those paths. Coupled fluid exchange and magnetic
evolution through the event still require their own measurements.

## Geometric conservation through a flip

All twelve REANA selections passed for the shared signed swept-volume correction at `70e51d6`. Each internal face transfers one volume with opposite signs to its two owners. On the five-site flip, the largest relative volume defect across the two Euler stages fell from 0.02235 to 1.70e-17 after correction. The corresponding maximum for Heun fell from 0.001424 to 8.83e-18. The executable also recovered the new triangular face area of 1/192. The tests cover fixed walls, periodic self-images, disconnected components, smooth refinement, unequal cell states and invalid or stale stage data. [Workflow and executable identities](../../tests/reference/m2_swept_volume_and_vertex/index.json) · [Original logs, measures and input specifications](../../tests/reference/m2_swept_volume_and_vertex/evidence.tar.gz)

Four additional REANA selections at `a801244` checked persistence of multiply supported vertices along linear paths. Rigid self-faces and a separable nonrigid tensor deformation passed their respective motion checks. The registered cubic shear has incompatible axial and diagonal support planes at its initial vertex. The negative control reproduced this obstruction to the shared-face curl derivative. Moving magnetic evolution through that geometry remains open. [Execution records](../../tests/reference/m2_swept_volume_and_vertex/index.json)
