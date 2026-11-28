# Sparse MPI exchange for 3D mesh and field stages

The shared-face curl, conservative ALE flux and swept-volume update assign each canonical face to one MPI rank. The cell with the smaller persistent ID supplies the interior face owner. Each face owner publishes a single oriented exchange to the ranks that own the incident cells. Each cell owner accumulates its incidences in canonical face order. Moving-mesh sweeps use the union of the old and rebuilt face keys for the current substep.

| Stage | Producer | Consumers | Values per row |
| --- | --- | --- | ---: |
| Potential samples | Cell owner | Owners of cells whose quadratic fits use the sample | 3 |
| Quadratic jets | Cell owner | Incident face owners | 30 |
| Magnetic curl exchange | Face owner | Incident cell owners | 3 |
| Fluid, magnetic and generator state | Cell owner | Incident face owners | 11 |
| Extensive ALE flux | Face owner | Incident cell owners | 5 |
| Euler and Heun conserved states | Cell owner | Swept-face owners | Conserved field width |
| Corrected swept-face exchange | Face owner | Incident cell owners | Conserved field width |
| Completed sweep ledger | Face and cell owners | Rank zero | Conserved field width |

Receivers are sorted and deduplicated per global row. Periodic images reuse the transferred real-cell value and retain their distinct offsets and moments in the fit. Shared interior faces supply opposite signs, self-image exchanges give zero net cell increment and bounded faces have one incidence. Ranks with empty partitions participate in the collectives.

## Run and measure

The MPI driver selects sparse transport by default for the stages above. Select a mode explicitly to compare both transports with the same source, inputs, rank count and thread team.

```sh
mpiexec -n 4 openmhd-mpi 2 --halo sparse field3 mesh.txt fields.txt 1.6666666666666667 0.5 -0.25 0.125 out-sparse
mpiexec -n 4 openmhd-mpi 2 --halo full   field3 mesh.txt fields.txt 1.6666666666666667 0.5 -0.25 0.125 out-full
```

For each row of width $w$ doubles, the sparse payload across all ranks is $8w$ times the number of distinct requesting ranks other than its producer. The full comparison sends $8w(R-1)$ bytes per row for $R$ ranks. The sparse path uses `MPI_Alltoallv` with zero counts for unrelated peers. The full path uses `MPI_Allgatherv` and retains the same required rows for the numerical stage. Both preserve binary64 values and producer order.

Each rank's `openmhd-halo` record reports its stage, call count, remote payload received, corresponding full payload and time inside the payload collective. These byte counts exclude collective implementation overhead, plan hashes and count metadata. Wall time includes planning, packing, MPI, geometry, numerical work and output.

The validated tessellation, fit topology, grounded sweep graph solve and public global field outputs still use replicated data. The transpose, Gram, point operators and other solver families retain their existing transport. These are single-node MPI measurements. Cross-node tests and fully distributed geometry remain separate roadmap items.
