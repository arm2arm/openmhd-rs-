# Candidate 3D backend: resolved metadata and source-byte inventory

This packet records a **metadata-only audit**, prepared on 2026-11-22, of
`meshless_voronoi = "=0.7.2"`, with default features disabled and only `ibig`
enabled. It does not adopt the dependency or modify the project Cargo files.
No compilation, build script, geometry probe, numerical test or evolution
was executed. New numerical execution remains REANA work after M1 acceptance.
The independently written all-pairs geometry oracle remains the first path.

`Cargo.toml` and `Cargo.lock` belong to a separate scratch workspace.
`metadata-only.rs` is an inert package target needed by Cargo metadata.
`audit.json.gz` retains the resolved graphs, enabled features, registry crate
checksums, declared licenses, hashes of available license/notice files,
manifest hashes and build-script source hashes. Registry archives for all
33 external packages were checked against the lock checksums. Linux
`x86_64-unknown-linux-gnu` and macOS `aarch64-apple-darwin` each reach 29
external packages; the all-target graph reaches 33. The selected mesh crate
has only the `ibig` feature in these graphs. No Rayon backend was enabled.

This is **not accepted license/distribution closure**. The inspected
`meshless_voronoi`, `rstar`, `r-efi` and `wasip2` archives lack standalone
LICENSE/COPYING/COPYRIGHT files under those names. The first two are reachable
on the audited Linux/macOS paths; the latter two occur only in the all-target
graph. A declared SPDX expression alone does not establish complete grant
and notice packaging. Preserve each package's actual expression, including
Unicode licensing and alternative-license choices; do not label the graph
uniformly MIT. Resolve and independently review distribution obligations
before adoption. No upstream code or dataset is vendored by this packet.

The audit ran with Cargo/rustc 1.85.1 on an Apple Silicon host. To reproduce,
copy this packet into a new ignored results directory, leaving the project
workspace unchanged, then run in that directory:

```sh
cargo metadata --locked --format-version 1 > metadata_all_targets.json
cargo metadata --locked --offline --format-version 1 --filter-platform x86_64-unknown-linux-gnu > metadata_linux.json
cargo metadata --locked --offline --format-version 1 --filter-platform aarch64-apple-darwin > metadata_macos.json
python3.11 collect_metadata.py
```

The first original resolution generated the retained lock before these
locked replays. `collect_metadata.py` uses Python 3.11's `tomllib`; it reads
Cargo's retained registry/cache files and writes `audit.json`. The packet's
gzip encoding has timestamp zero. Original raw metadata hashes are recorded,
but raw metadata contains host paths and is not promised byte-identical
across hosts. `sha256.json` closes this packet's file inventory.

Actual builds, target support, native/build-script effects, deterministic
geometry behavior and the periodic/normal-sign fixtures remain unperformed.
Any future integrated Cargo resolution must be re-audited: this standalone
lock is evidence about this precise candidate graph, not the project graph.
