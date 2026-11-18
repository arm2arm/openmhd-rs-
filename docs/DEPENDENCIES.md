# Rust dependency licenses

The serial numerical algorithms remain independently implemented. Checkpoint integrity adds the RustCrypto `sha2` crate, pinned to **0.10.9** in `mhd-io`; no external MHD solver or numerical reconstruction code is imported.

The package manifests and bundled license texts in the Cargo registry were checked before integration. The locked packages below permit MIT use and are compatible with this repository's MIT license. Cargo downloads the packages with their original license files; binary distributions must retain the applicable notices. Versions are from `Cargo.lock`, built with Rust 1.85.1.

| Package | Locked version | Declared license |
|---|---|---|
| sha2 | 0.10.9 | MIT OR Apache-2.0 |
| digest | 0.10.7 | MIT OR Apache-2.0 |
| block-buffer | 0.10.4 | MIT OR Apache-2.0 |
| crypto-common | 0.1.7 | MIT OR Apache-2.0 |
| generic-array | 0.14.7 | MIT |
| typenum | 1.20.1 | MIT OR Apache-2.0 |
| cfg-if | 1.0.5 | MIT OR Apache-2.0 |
| cpufeatures | 0.2.17 | MIT OR Apache-2.0 |
| libc | 0.2.191 | MIT OR Apache-2.0 |
| version_check | 0.9.5 | MIT/Apache-2.0 |

`version_check` is a build dependency; platform-specific packages may not be linked on every target. Historical benchmark reports describing a dependency-free workspace refer to their recorded revisions, before checkpoint persistence was added. Use `cargo metadata --locked --format-version 1` to inspect the current resolved graph.
