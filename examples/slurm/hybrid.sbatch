#!/bin/bash
#SBATCH --job-name=openmhd-rs
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=6
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --output=openmhd-%j.out

# EXAMPLE ONLY: no OpenMHD-RS solver exists yet.
# Adjust resource limits and compiler/MPI runtime to the target HPC cluster.
set -euo pipefail
export RAYON_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

srun --cpu-bind=cores ./target/release/openmhd --config examples/config.toml
