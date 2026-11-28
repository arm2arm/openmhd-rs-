# MPI and thread scaling on one REANA node

## Production solver

All 21 benchmark families reproduced their published scientific files and diagnostics at six additional layouts. The fixed-input comparisons covered 1×2, 1×8, 2×4, 4×2, 8×1 and 1×16, where the first number is MPI ranks and the second is Rayon threads per rank. Together with six larger-input runs, the study measured 396 complete executable launches across 132 independently submitted workflows. The eight-rank face-flip cases used five cells and also exercised ranks with no owned cell. [Registered inputs](../tests/reference/m3_single_node_extension/plan.json) · [All measured layouts](../tests/reference/m3_single_node_extension/measurements.csv).

![Eight-CPU performance for 21 solver families, compared with one MPI rank and eight Rayon threads](images/m3_parallel/eight-cpus.png)

Each larger input had a serial run and an eight-rank run. Both produced identical scientific files. Times are medians of three launches, including MPI startup and file output. The last column sums the halo bytes received across the eight ranks for one launch. [Raw REANA records](../tests/reference/m3_single_node_extension/workflows.tar.gz).

| Larger input | Serial | 8 MPI ranks × 1 thread | Halo bytes received |
|---|---:|---:|---:|
| 216-cell rigid 3D mesh | 22.024 s | 12.584 s | 3,656,674 |
| 512-cell Alfvén wave | 0.348 s | 0.446 s | 71,479,744 |
| 361-particle direct-gravity evolution | 0.306 s | 0.473 s | 266,297,598 |

The eight-rank mesh build was 1.75× as fast as the serial control. The wave and gravity evolutions took longer on eight ranks at these sizes. The current MPI implementation collects each rank's results on every rank. Sparse neighbour exchange for the mesh and field stages is the next parallel milestone. Direct gravity still needs every source particle. Tree gravity follows the separate long-orbit direct-solver validation. [MPI transport](../apps/openmhd-mpi/src/transport.rs) · [Roadmap](ROADMAP.md).

### Replay the production comparisons

From the repository root, the command below reads the original workflows, compares the numerical output with the published baseline, and writes the full timing table.

```sh
data=tests/reference/m3_single_node_extension
python3 reana/m3/verify_node_scaling.py "$data/plan.json" "$data/workflows.tar.gz" \
  tests/reference/m3_parallel/hybrid-e4034c9f2-e4034c9f2.tar.gz /tmp/m3-solver-replay
```

Separate REANA workflow `2db49c7b-f685-40a0-9949-2c8f613d0312` replayed all 126 fixed-input comparisons and the three larger serial/parallel pairs from the downloaded records. [Verification](../tests/reference/m3_single_node_extension/verification.json) · [REANA receipt](../tests/reference/m3_single_node_extension/replay.json).
