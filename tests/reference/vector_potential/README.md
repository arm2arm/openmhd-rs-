# Issue #6 vector-potential operator/coupling packet

Measured on clean revision `d67e5c052ff4d877e82941e536af9681adc99520`. `summary.json` contains 27 predeclared acceptance runs and two **observational** nonuniform mean-field boost runs added after the AI review. The latter show a discrepancy; they are not successful invariance tests. See [results and limitations](../../../docs/VECTOR_POTENTIAL_RESULTS.md).

Reproduce with `python3 scripts/run_vector_potential.py`. It builds the locked release CLI, checks the original gates, and writes all cell CSVs plus summary/provenance under `results/vector_potential/`. The provenance records the exact revision, clean-tree status, source/result SHA256 hashes, commands, compiler, hardware and physical conventions. The optional `scripts/plot_vector_potential.py` reads this archive directly, verifies the recorded input hashes and generates the four [documented figures](../../../docs/VECTOR_POTENTIAL_RESULTS.md); it does not rerun simulations. The original preregistration is commit `67715a8`; the auxiliary implementation is `557fea3` and coupled code is `67b24ef`.

The archive retains initial/final snapshots for the irregular gauge and both nonuniform mean-field boost runs in `snapshots/`. Decompress a `.csv.gz` and compare its SHA256 against the matching `run/initial.csv` or `run/final.csv` entry in `provenance.json`. Other full cell snapshots are reproducible outputs; all 29 runs' diagnostics/configuration and their snapshot hashes are archived.

`ai_probe.rs` and `ai_mean_components.rs` preserve the independent reviewer's additional rectangular deforming/fluid-following fixtures. The first checks a zero-mean-field three-component boost. The second reports the observed nonzero-mean-field difference without asserting a success tolerance. They are supplemental review evidence, not the original acceptance ladder. Reproduce either with:

```sh
cargo build --release --locked -p mhd-vector-pot
rustc --edition=2024 tests/reference/vector_potential/ai_probe.rs \
  -L dependency=target/release/deps \
  --extern mhd_vector_pot=target/release/libmhd_vector_pot.rlib \
  --extern moving_mesh="$(rg --files target/release/deps | rg '/libmoving_mesh-.*\.rlib$' | head -1)" \
  -o /tmp/openmhd-ai-probe
/tmp/openmhd-ai-probe
```

Use a clean target directory if multiple dependency builds exist. The regular unit suite already covers all predeclared algebra/stage fixtures, including rejected-state immutability, full distortion, both A donors, numerical HLL EMF and partially failed HLL sweep accounting. This packet does not validate the full M1 physical benchmark matrix or 3D/MPI/local timesteps.
