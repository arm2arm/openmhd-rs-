# Observed Rustfmt text application, generation 02

This source-only revision applies all **30 exact captured hunks in four files**
from Rust 1.85.1 `cargo fmt --check`. The original diagnostic workflow
`openmhd-galaxy-format-c4f3ef0b761e-a01.1`, UUID
`42e434a0-2f0e-4acd-a173-f950b6393f72`, exited **1** on that command only;
Clippy, build, discovery and test methods did not run. Both independent original
formatter downloads are 24,685 bytes, SHA256
`6e28811f0bedd423ec7443a8373ace3d7b0f205cf33aab1ccbf1512b6f1c1510`.
The closed diagnostic report/259-body manifest and all failed evidence remain
unchanged.

Every preimage matched its Git blob at
`30f0f4ef3938e6cc6da307fdee0b2650eeee893a` and the selected-source pins of
snapshot `c4f3ef0b761e0993224cd107318d44fa1ec207e4d2ce0c845565e13f88e9747e`.
Each hunk was decoded and matched once at its original declared line, with every
old context/removal line equal. There was no search, fuzzy matching, formatter,
Rust parser, compiler, linter, test, project-target import, reference calculation or workflow
action in this repair.

| Path under `crates/` | Hunks | Before SHA256 | Applied SHA256 |
| --- | ---: | --- | --- |
| `gravity/examples/gravity-force-case.rs` | 11 | `3192814364e24a4ca1b0ab8e6216abaedff1e00e0de4c675c54996bd645a53d6` | `dceacc9a0b3a140ddb933e9357cbe898fea9b483e57cb4af63195e27247d68b9` |
| `moving-mesh/examples/geometry3-case.rs` | 17 | `fc30eb85615bbaee863e802cb01acca80f82ca6a1f774b16a475f2394c81f37f` | `59be6c310d1678d626606168dfcf935982e66a5b37c0260c30e8501e1b05bbbf` |
| `moving-mesh/src/three_d/exact.rs` | 1 | `914b194779fc0b0ab32f62b66d077480aeceb562201cd3fd794f3595e9b73f31` | `4bf095f6c1ae70012b29634129d94d69f5bb3f10b5ce2d19d44260667e9ad492` |
| `moving-mesh/src/three_d/moments.rs` | 1 | `dd0725771005b3c693a1217fd8650d4b5a61a65b811b3a263e756e714ee216be` | `c58d1a0efacb7a356047f1e0c5fe8b2b0f9517cc7a5e90c31f0b3fb008759077` |

The two core hunks only reflow the same limb sum and affine-residual expression;
operand/grouping/traversal order is unchanged. The exporters reflow chains,
calls, arrays, structs and output writes. Seven trailing commas are explicit
punctuation changes: four in the gravity exporter (final `reject` argument,
`ParticleMetadata` field, `Star` match arm, `optional_vector` argument), three
in the geometry exporter (image array, `Domain3` field, result tuple). The
`EmptyCatalog` virial arm additionally wraps the same `writeln!(...)?` as a block
tail, replacing its arm comma; it adds no declaration or semicolon and preserves
unit result/error propagation. There is no import/module reordering. Protected
literal, numeric, comment, identifier and lifetime sequences agree exactly;
protocol strings, escaped newlines, limits, operands and output order are
unchanged. This is an explicit lexical/manual audit, not a claim of Rust AST or
byte identity.

The retained sorted text inventory has 559 test declarations across tracked Rust
files (including historical copies); the registered 98-name identity/gravity/3D
component scope is separately enumerated. Both inventories remain unchanged;
none ran. All other 4,904 tracked files, HEAD, the five active Python acquisition
helpers, and all 259 original diagnostic bodies are fenced unchanged. The
independent untracked geometry-review documents are outside this application.

Full preimages/candidates, exact hunk/context matches, old-to-new map, complete
diffs, lexical/manual audit, inspection corrections and final closure are in
[`results/galaxy_observed_format_repair02_20261122/`](../../results/galaxy_observed_format_repair02_20261122/).
Historical `FORMAT_REVISION.md`, `CLIPPY_REVISION.md`, source inventories and
reviews retain their original generation identities. Initial unavailable-name
lookups/truncated listing are recorded honestly; no failed check was treated as
a pass.

No repaired format pass is measured. Root review and a coherent committed source
generation must precede a new REANA format/strict-Clippy/build/no-run/list
preflight, then independently released component/reference cases. M1's accepted
periodic fixed/rigid 2.5D scope is unchanged. Deforming 3D nonzero-MHD gas, live
DM/old/new stars, isolated gravity, published ISM/SF/feedback and full-duration
merger validation remain open.
