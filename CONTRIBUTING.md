# Contributing to OpenMHD-RS

**Current state:** public planning repository; solver implementation is not yet available. An [MIT License](LICENSE) is present. New dependencies and imported code must be checked for compatibility.

Before opening an implementation pull request:

1. Trace each paper-derived mathematical operation to [arXiv:2609.35989](https://arxiv.org/abs/2609.35989) including version, page/equation number and discretization assumptions.
2. Include minimal unit tests and reproducible reference configurations for new numerical functionality.
3. Once a Cargo workspace exists, run `cargo fmt --check`, `cargo clippy --all-targets` and `cargo test`.
4. For physics changes, report conservation, Galilean invariance, convergence and magnetic-divergence diagnostics.
5. Describe Rust FFI or `unsafe` use, toolchain dependencies and any relevant source licenses.
6. Never claim AREPO-equivalent results until independent benchmarks support that claim.

The repository is public and **MIT-licensed**. The contribution and scientific review policy remains under development; coordinate substantive code contributions with the maintainer.
