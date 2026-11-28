# Hybrid parallel validation

The November 28 extension measures the same 21 families through eight MPI ranks and 16 Rayon threads, including larger meshes, waves and gravity inputs. [Single-node measurements](M3_SINGLE_NODE_EXTENSION.md).

The parallel solver reproduced the serial scientific output byte for byte in 21 problem families on REANA. The comparisons covered one, two and four MPI ranks, with one to four Rayon threads per rank. Both a vector-potential Alfvén wave and a collisionless gravity evolution also reproduced their uninterrupted endpoints after restarting a two-rank checkpoint on four ranks. [Registered inputs and layouts](../reana/m3/mpi_matrix.py) · [MPI and Rayon implementation](PARALLEL_HPC.md).

![Measured Rayon speedups and equal-CPU MPI configurations on REANA](images/m3_parallel/scaling.png)

Both panels show elapsed time for a complete executable invocation, including output and, for hybrid runs, MPI launch. Each point or bar represents a separate workflow. The left panel uses three repetitions per layout. In the right panel gravity and the regular mesh use three repetitions, while the wave and jittered mesh use one. Timings describe the shared Linux worker available to REANA. [Original REANA figure workflow and input hashes](images/m3_parallel/provenance.json) · [Rendering source](../reana/m3/plot_scaling.py) · [Original measurements](../tests/reference/m3_parallel/hybrid-measurements.json).

## Coverage and reproducibility

| Numerical path | Compared output |
| --- | --- |
| Rigid and jittered 3D Voronoi meshes, a face flip, periodic self-neighbours and Lloyd motion | Every exported vertex, volume, face orientation and incident owner at each epoch |
| Euler and Heun swept volumes on both jittered and flipping meshes | Signed face volumes and per-cell uniform transport against the measured volume change |
| 3D finite-volume operators | Shared-face curl and transpose, Gram diagonal, moving curl and transpose, and conservative ALE HLLD face flux |
| Point-sampled 3D magnetic operators | Linear, quadratic and curvature-corrected fields, four divergence diagnostics per field, and the forward, adjoint and Gram operators for the static point curl and its smooth-motion derivative |
| 2.5D ideal MHD | Full state and checkpoints for an Alfvén wave, boosted field loop, Brio–Wu and Orszag–Tang, plus an Alfvén wave on a prescribed deforming mesh |
| Planar evolution | Gas finite volume, constrained transport with and without admissibility limiting, passive-potential evolution and prescribed scalar advection |
| Collisionless KDK gravity | Particle endpoint, conserved quantities, full checkpoint and restart across a rank-layout change |

The largest absolute sum of the periodic 3D mass, momentum and energy rates was 5.82e-17 in code units. The normalized moving-curl adjoint residual was 4.34e-19. The largest relative error in transporting a uniform state through swept faces was 3.58e-16, and the largest constrained-transport divergence in the two planar runs was 1.05e-14. [Per-case diagnostics](../tests/reference/m3_parallel/hybrid-measurements.json).

The separately built point-sampled extension `e4034c9f2d51` passed seven layouts, including reversed input order. All twenty earlier problem families also ran on two ranks with that executable. Fifteen reproduced every scientific file byte for byte. In five 2.5D MHD families, the complete saved state and all CSV files matched. The original whole-file comparison stopped on the Alfvén checkpoint because each checkpoint embeds its executable SHA-256 and seals that identity together with the state. Ten separate REANA comparisons verified both executables and the saved state, and tested rejection of changed state, source, executable, checksum and length. The largest normalized periodic divergence budget across the nine point-field face diagnostics was 7.91e-17. The static and moving point-curl adjoint residuals were 1.73e-18 and 0.00e+00. [Checkpoint comparison](../reana/m3/checkpoint_identity.py) · [Original workflow pairs](../tests/reference/m3_parallel/summary.json).

The workspace build discovered **510 ordinary Rust tests**. Each passed in its own REANA workflow. An additional example-only build discovered 9 tests in scientific example executables. Those also passed individually. The default catalog also marked 10 release-scale mesh tests as ignored. We selected each explicitly on the same compiled executable. All ten passed, including the 512-cell periodic mesh through multiple box crossings. Separate kernel controls exercised stable ownership, input order, geometry and gravity across 1, 2, 4, 8 and 16 threads. The MPI and workspace builds passed formatting, strict Clippy and release compilation. [Workspace inventory and build identities](../tests/reference/m3_parallel/summary.json) · [Earlier preflight diagnostics](../tests/reference/m3_parallel/build-history.json).

## Rayon strong scaling

Elapsed seconds below are medians of three runs. The direct-gravity cases used two equal-mass populations and the same ordered pair accumulation at every thread count. [Timings, exact arguments, CPU time and resident memory](../tests/reference/m3_parallel/rayon-measurements.json).

| Threads | 64-cell Voronoi mesh | 256 particles, 16 KDK steps | 2,048 particles, 4 KDK steps |
| ---: | ---: | ---: | ---: |
| 1 | 1.072 | 0.240 | 3.216 |
| 2 | 0.683 | 0.255 | 3.670 |
| 4 | 0.382 | 0.267 | 3.666 |
| 8 | 0.205 | 0.290 | 3.903 |
| 16 | 0.174 | 0.299 | 3.914 |

The 64-cell mesh ran 6.16 times faster at 16 threads. Direct gravity was fastest at 0.240 s on 1 thread for 256 particles and 3.216 s on 1 thread for 2,048 particles. Each pair is evaluated once, and the compensated force accumulation retains its original order.

## MPI strong scaling

Each column gives ranks × threads per rank and elapsed seconds. The input stays fixed along each row. MPI 1 × 1 uses the same communication path as the other columns. A separately executed serial numerical path supplied the scientific reference. All ranks reported their own work and exchange counts. [Rank work, halo bytes, timings and workflow IDs](../tests/reference/m3_parallel/hybrid-measurements.json).

| Case | 1 × 1 | 1 × 4 | 2 × 1 | 2 × 2 | 4 × 1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Rigid 3D mesh | 3.041 | 1.476 | 1.989 | 1.588 | 1.689 |
| Jittered 3D mesh | 7.861 | 3.300 | 5.051 | 3.564 | 3.301 |
| 3D face flip | 0.349 | 0.353 | 0.333 | 0.326 | 0.381 |
| Periodic self-neighbours | 0.306 | 0.384 | 0.331 | 0.345 | 0.323 |
| Lloyd mesh regularisation | 27.913 | 10.474 | 16.564 | 11.012 | 10.325 |
| Swept volumes at a face flip | 0.389 | 0.382 | 0.524 | 0.415 | 0.363 |
| Jittered 3D swept volumes | 7.944 | 3.243 | 5.354 | 3.418 | 3.274 |
| Moving 3D curl and adjoint | 5.038 | 2.543 | 3.386 | 2.551 | 2.754 |
| 3D curl and HLLD flux | 18.145 | 6.896 | 12.597 | 7.735 | 7.545 |
| Direct gravity, 256 particles | 0.557 | 0.486 | 0.535 | 0.466 | 0.517 |
| 2.5D Alfvén wave | 0.410 | 0.441 | 0.413 | 0.416 | 0.439 |
| Boosted field loop | 0.466 | 0.560 | 0.589 | 0.482 | 0.477 |
| Brio–Wu shock tube | 0.381 | 0.408 | 0.451 | 0.402 | 0.458 |
| Orszag–Tang vortex | 0.449 | 0.503 | 0.469 | 0.536 | 0.512 |
| Deforming 2.5D Alfvén wave | 0.401 | 0.498 | 0.515 | 0.735 | 0.461 |
| Planar finite-volume gas | 0.350 | 0.304 | 0.355 | 0.325 | 0.349 |
| Planar constrained transport | 0.407 | 0.336 | 0.467 | 0.360 | 0.336 |
| Admissibility-limited constrained transport | 0.353 | 0.352 | 0.404 | 0.388 | 0.372 |
| Passive-potential evolution | 0.331 | 0.309 | 0.348 | 0.327 | 0.352 |
| Prescribed scalar advection | 0.361 | 0.327 | 0.427 | 0.310 | 0.323 |
| Point and shared-face 3D operators (extended build) | 4.998 | 2.663 | 3.449 | 2.711 | 2.576 |

## MPI weak scaling

![Elapsed time for growing mesh, Alfvén-wave and gravity problems on one, two and four MPI ranks](images/m3_parallel/weak-scaling.png)

The dashed line in each panel shows its single-rank time. Labels below the ranks give the total problem size.

The mesh and wave problems retain the same cell count per rank. For direct gravity, the particle count was chosen to keep unordered force pairs per rank within 1.5% of the single-rank value. These medians use three repetitions and one thread per rank. [Weak-scaling definitions](../reana/m3/mpi_matrix.py) · [REANA reductions](../tests/reference/m3_parallel/hybrid-measurements.json).

| Case | Ranks | Global problem size | Elapsed seconds | Halo bytes received, summed over ranks |
| --- | ---: | ---: | ---: | ---: |
| 3D mesh | 1 | 27 cells | 1.182 | 0 |
| 3D mesh | 2 | 54 cells | 1.963 | 130,600 |
| 3D mesh | 4 | 108 cells | 4.434 | 783,546 |
| Alfvén wave | 1 | 64 cells | 0.251 | 0 |
| Alfvén wave | 2 | 128 cells | 0.253 | 1,163,472 |
| Alfvén wave | 4 | 256 cells | 0.275 | 9,254,496 |
| Direct gravity | 1 | 128 particles | 0.234 | 0 |
| Direct gravity | 2 | 181 particles | 0.274 | 9,542,286 |
| Direct gravity | 4 | 255 particles | 0.382 | 56,891,352 |

## Evidence and scope

The published packet contains 956 successful workflow receipts including 297 MPI runs and 44 independent comparisons across the retained source revisions. The 20 integrated MPI families used source `26750efba146`. All workspace crates and regression definitions have identical Git object IDs in that build and the workspace build `229e10da522d`. The replay also matched 162 source, manifest and fixture hashes between both test builds and both MPI builds. The intervening Rust change corrected an import in the standalone MPI executable. An earlier two-rank run exposed an unbounded input-weight iterator during planar initialization. The repaired constructor supplies one weight per generator and has a dedicated public-entry-point regression. [Original pilot outcomes](../tests/reference/m3_parallel/superseded-pilots.json). The offline replay joined each original workflow, catalog, compiled binary digest and scientific output, and rechecked the comparisons. [Manifest](../tests/reference/m3_parallel/manifest.json) · [Independent REANA replay](../tests/reference/m3_parallel_replay.json) · [Verifier](../reana/m3/verify_evidence.py).

To replay the published comparisons from a checkout, run the verifier against the evidence directory. It reads the recorded scientific output and the original REANA receipts.

```bash
python3 reana/m3/verify_evidence.py tests/reference/m3_parallel
```

The REANA jobs requested one CPU per rank thread. The worker exposed 24 CPUs through affinity and reported `max 100000` for the cgroup quota. The measurements cover real MPICH processes on one node. Each rank holds a full geometry and halo, and the small swept-volume correction solve retains its serial Cholesky order. Sparse halo exchange, cross-node scaling, parallel HDF5 and coupled deforming 3D MHD evolution remain separate milestones. [Roadmap](ROADMAP.md).
