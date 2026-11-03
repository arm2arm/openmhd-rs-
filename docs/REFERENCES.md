# References and technical resources

## Primary method

Springel, V., Mayer, A. C. & Pakmor, R. (2026), *Divergence-free magnetohydrodynamics on a moving mesh*, [arXiv:2609.35989](https://arxiv.org/abs/2609.35989). The implementation must be traced to the **full text**, its version, equation numbers and appendices. This project is independent and does not claim an official AREPO affiliation.

## Earlier moving-mesh MHD literature

- Pakmor, R., Bauer, A. & Springel, V. (2011), *Magnetohydrodynamics on an unstructured moving grid*, [arXiv:1108.1792](https://arxiv.org/abs/1108.1792).
- Mocz, P. et al. (2016), *A moving mesh unstaggered constrained transport scheme for magnetohydrodynamics*, [arXiv:1606.02310](https://arxiv.org/abs/1606.02310). **Do not assume it is numerically equivalent to the 2026 gauge.**

## Engineering candidates

- Rust MPI / rsmpi: <https://crates.io/crates/mpi>.
- Rayon: <https://crates.io/crates/rayon>.
- Meshless Voronoi candidate: <https://crates.io/crates/meshless_voronoi>.
- HDF5: <https://www.hdfgroup.org/solutions/hdf5/>.
- Slurm: <https://slurm.schedmd.com/>.

Every imported algorithm must have recorded assumptions, version and any relevant upstream license restrictions.
