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

This is **not accepted license/distribution closure**. The initial filename
scan found no standalone LICENSE/COPYING/COPYRIGHT files in four archives.
The supplemental primary-source audit resolves where their grants are stated:

- `meshless_voronoi`'s published README explicitly offers Apache-2.0 or MIT
  for `ibig`, `dashu` and `num_bigint`. Its pinned upstream tree has no
  separate license file. The selected graphs enable `ibig` only; optional
  LGPL backends are absent. Preserve that conditional grant and complete
  applicable license/notice materials when packaging this candidate.
- rstar's [pinned workspace root](https://github.com/georust/rstar/tree/c8c5bf9e41468281d030869d409e3f67f1aaf5b7)
  has full MIT and Apache texts omitted from its subdirectory crate archive.
- r-efi includes a full grant and copyright notices in
  [AUTHORS](https://github.com/r-efi/r-efi/blob/97b55bed1c2c91dcbf787674849f05337ff80b33/AUTHORS),
  which the initial filename filter did not include.
- wasip2's [pinned workspace root](https://github.com/bytecodealliance/wasi-rs/tree/3da562c06214feafc14d37bf290671636caa6718)
  supplies the three alternative license texts. This package and r-efi are
  absent from the audited Linux/macOS reachable graphs.

`license_materials.json.gz` retains 84 distinct source texts across all 33
packages: actual license/notice/AUTHORS files, the four relevant published
README/manifest grants, pinned upstream supplements and copyright/permission
comments from 213 source files. Crate hashes are rechecked against the lock;
upstream commits match each published `.cargo_vcs_info.json`, and fetched
license bytes match the complete tree's Git blob identities. The original
`audit.json.gz` is preserved as the earlier observation, not rewritten.

Proposed options are Apache-2.0 where offered, MIT for byteorder/libm/r-efi,
and Apache-2.0 **AND Unicode-3.0** for unicode-ident. These are reviewable
choices, not a claim the graph is uniformly MIT or that every optional LGPL
branch was selected. libm's complete license text and retained per-file
third-party notices are included. The comment scan is an overinclusive aid,
not a complete source-language parser or a legal completeness certificate.
Independent distribution/notice review and actual integrated-graph review
remain prerequisites to adoption. No numerical implementation is vendored.

The [independent review](../MESH_DEPENDENCY_REVIEW.md) of `ca29264` supports
the proposed elections but identifies a concrete omission: `glam 0.27.0`'s
`ATTRIBUTION.md` contains three additive MIT notices. The original 84-text
observation and collectors above are unchanged. The new
[readable notice candidate](release_notice_candidate/THIRD_PARTY.md) retains
the exact 3,718-byte attribution file (SHA-256
`9f0738ead3dcc72bac87afc652c2466e1bc130d235db7798f98da4d4ef013639`),
all 33 packages' existing materials, pinned upstream-root supplements,
a complete Apache copy for the mesh README grant, and all 213 selected
source-notice records, including libm's 69 records. OpenMHD's own MIT license
is retained separately. Original filenames and per-package elections are
readable without decompressing a developer database.

`prepare_notice_candidate.py` rechecks all 33 archive identities, original
text hashes and source-comment membership, and prepares a new directory;
it refuses to overwrite an existing observation. Its `materials.json` and
closed `sha256.json` pin the builder, original observations and actual notice
paths. Reproduce into a **new** ignored destination with:

```sh
python3 docs/galaxy/dependency_audit/prepare_notice_candidate.py --destination results/new-notice-candidate
```

This fixes the identified material omission for review, not final
distribution closure. The candidate's index describes source and binary
layout obligations, including complete original source/header preservation;
selected comment records are not an exhaustive census. No dependency has
been integrated and no binary, installer, container or vendored-source
release has been produced. Independent revision review, actual integrated
graph review and inspection of the final artifact remain open.

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

The supplemental retrieval and collection sources are
`read_upstream_licenses.py` and `collect_license_materials.py`. To repeat that
observation, use a fresh ignored directory containing the collector scripts,
the decompressed original `audit.json` and registry archives populated by the
locked metadata preparation. Run the retrieval script, then the license
collector; both preserve existing observations rather than overwriting them.
The retained gzip's `texts_by_sha256` can also be checked directly without
any network or numerical execution. License texts retain their upstream
terms; the repository's MIT license does not relicense them.

Actual builds, target support, native/build-script effects, deterministic
geometry behavior and the periodic/normal-sign fixtures remain unperformed.
Any future integrated Cargo resolution must be re-audited: this standalone
lock is evidence about this precise candidate graph, not the project graph.
