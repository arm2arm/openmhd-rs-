#!/bin/bash
#SBATCH --job-name=openmhd-rs
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=6
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --output=openmhd-%j.out

# Submit from the repository root after building the MPI binary using the cluster MPI.
# sbatch examples/slurm/hybrid.sbatch mesh docs/galaxy/fixtures/m2c_tessellation_flip.txt mesh-output 0.5 0.5
set -euo pipefail
: "${SLURM_CPUS_PER_TASK:?reserve CPUs per rank with --cpus-per-task}"
if (( $# == 0 )); then
    echo "usage: sbatch examples/slurm/hybrid.sbatch MODE [DRIVER_ARGUMENTS ...]" >&2
    exit 2
fi
export RAYON_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
binary="${OPENMHD_MPI_BINARY:-./apps/openmhd-mpi/target/release/openmhd-mpi}"
srun --cpu-bind=cores "$binary" "$RAYON_NUM_THREADS" "$@"
