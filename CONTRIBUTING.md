# Contributing to OpenMHD-RS

**Current state:** public research repository with a Cartesian kinematic pilot and an experimental coupled planar MHD reference. The full paper method and M1 scientific release are not validated; see [COUPLED_2D.md](docs/COUPLED_2D.md). An [MIT License](LICENSE) is present. New dependencies and imported code must be checked for compatibility.

Before opening an implementation pull request:

1. Trace each paper-derived mathematical operation to [arXiv:2609.35989](https://arxiv.org/abs/2609.35989) including version, page/equation number and discretization assumptions.
2. Include minimal unit tests and reproducible reference configurations for new numerical functionality.
3. Run `cargo fmt --check`, `cargo clippy --all-targets --all-features` and `cargo test --workspace` in the existing reference workspace.
4. For physics changes, report conservation, Galilean invariance, convergence and magnetic-divergence diagnostics.
5. Describe Rust FFI or `unsafe` use, toolchain dependencies and any relevant source licenses.
6. Never claim AREPO-equivalent results until independent benchmarks support that claim.

The repository is public and **MIT-licensed**. The contribution and scientific review policy remains under development; coordinate substantive code contributions with the maintainer.
