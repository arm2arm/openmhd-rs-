# Mesh-symmetry controls for the Brio shock (issue #22)

Bounded evidence that the two open shock blockers (#20 pressure, #21 Bx) are
tied to the registered planar jitter breaking the problem's y-invariance.
On a nonuniform y-invariant mesh the default `paper-global-v2` profile and the
quadratic projected candidate pass every unchanged gate at t=.1. The planar
failures are reproduced and remain failures. This is not M1 acceptance.

See the [measured results and disposition](../../../docs/M1_SHOCK_INVESTIGATION.md#measured-mesh-symmetry-disposition-2026-11-09-issue-22).

## Contents

- `symmetry_summary.json`: per-family gate results of the eight-case screen
  (`scripts/run_shock_symmetry.py`), nx256 x ny4, jitter .15, t=.1, base/boost.
- `scan.json`: twenty-run t=.02 planar-jitter scan (`scripts/scan_shock_meshes.py`)
  over aspect ratio, resolution and jitter amplitude, with commands, timings,
  failure messages and per-file hashes. Snapshots of the scan are not retained.
- `raw.tar.gz` (SHA256 `950c55529ff56c4dc0db9271e0f750a0dd80e817197ebe96e60ff8e128ce6fe0`):
  both result directories. The screen directory holds the manifest, provenance
  (source and binary hashes, rustc, 30-second cap), `source.tar.gz`, and for
  every case the command, log, summary, history, geometry and initial/final
  snapshots.

The runs were made on base revision `0988ae5` plus the uncommitted changes of
this work; the archived `source.tar.gz` and its hashes are the exact source.
Binary SHA256: `898f144dedc94937736351d4ffefe22a92a7db7d2948a80d1fca0501370ed8da`.
f64, periodic, mu0=1, gamma=2, mean B=(.75,0,0), box [0,2] x [0,1/8], rigid mesh
motion, CFL .3, one thread per case, no floors, resets or resistivity.

## Reproduce

```sh
python3 scripts/run_shock_symmetry.py --output-dir results/fresh_symmetry   # exits 1: planar gates fail
python3 scripts/scan_shock_meshes.py --output-dir results/fresh_mesh_scan
cd scripts && python3 -m unittest test_shock_symmetry
cargo test --release -p moving-mesh column_lattice
cargo test --release -p mhd-vector-pot literal_profile_shock
```
