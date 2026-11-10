# Pressure-blend preflight stopped by strict Clippy

`openmhd-m1-pressure-blend-20261110.1`, UUID
`e6315eaf-fc64-4a78-9d0f-2c7b84c3c33d`, ran 04:11:35–04:15:40 UTC on
2026-11-10 and failed before any evolution. Snapshot SHA256
`beda7bd90d04dfef8e004bf06030c173c18ffd75bdebb69a95a1569e35d64daa`.

Formatting passed. Strict Clippy rejected an indexed loop over a local
momentum array in the new covariance test (`needless_range_loop`). No Rust
test execution or scientific result is claimed. The correction iterates
that same array with `enumerate`; it changes no numerical implementation.
A fresh snapshot is required; this failed workflow is preserved, not resumed.

All 321 frozen source files and four final output artifacts verify. The
source archive retains the executed Rust/Python/configuration files, with
the complete source manifest, wrapper, REANA configuration and logs.
