# Serial checkpoint and restart

The general 2.5D `vector-potential` driver can save full accepted-step state and resume it. This covers all eight named profiles and fixed, rigid, fluid and prescribed mesh motion. The earlier planar/kinematic drivers do not use this format. MPI-aware/HDF5 restart remains future work. This I/O feature does not establish M1 numerical acceptance.

## On a Mac

Build once and keep a copy of the executable beside the run. Version 1 intentionally requires the **same executable bytes**, source/build fingerprint and compatible platform. Rebuilding, changing code or switching debug/release builds may make a checkpoint incompatible; keep the original executable for long runs.

From the repository root:

```sh
source "$HOME/.cargo/env"
cargo build --release --locked -p openmhd --bin vector-potential
mkdir -p results/restart_demo
cp target/release/vector-potential results/restart_demo/vector-potential

./results/restart_demo/vector-potential \
  --case alfven --profile bulk-frame-hll-projected-v1 \
  --n 32 --jitter 0.15 --time 1 --checkpoint 0.25 \
  --checkpoint-steps 200 --output results/restart_demo
```

This writes `results/restart_demo/restart.chk` initially, every 200 accepted steps, after each requested analysis output and at completion. The projected profile is still experimental; see its [validation limits](M1_PROJECTED_CONTROLS.md).

After interruption or a laptop shutdown, run the saved executable:

```sh
./results/restart_demo/vector-potential \
  --resume results/restart_demo/restart.chk
```

Resume uses the checkpoint's directory by default. To keep resumed outputs elsewhere or change save cadence:

```sh
./results/restart_demo/vector-potential \
  --resume results/restart_demo/restart.chk \
  --output results/restart_resumed --checkpoint-steps 100
```

The file includes the original initial CSV, diagnostics/history, completed requested analysis CSVs and pending output schedule. A new output directory therefore retains the original t=0 and prior analysis history. Original mesh-cache files are not needed. Existing completion/failure markers in the selected output directory are removed when the run resumes, then regenerated on completion.

To stop cleanly after a chosen **total accepted-step count**, add `--stop-after-steps 1000` to a fresh run or resume command. That count must exceed the restored count. The driver saves immediately after that accepted step and exits successfully without claiming completion. If the simulation reaches its final time first, it completes normally. A normal Ctrl-C or abrupt process termination recovers from the last completely written checkpoint; steps since that file was saved must be recomputed. Checkpointing cannot be added retroactively to a binary already running without this feature.

## Options and guarantees

| Option | Meaning |
|---|---|
| `--checkpoint-steps N` | Save every N accepted steps; positive integer; no extra physical timestep targets. |
| `--restart-out FILE` | Choose the restart destination; alone, saves initial and analysis/final boundaries. Default is `OUTPUT/restart.chk`. |
| `--resume FILE` | Restore the saved run and pending targets. Only output path, restart path, cadence and stop-count overrides are accepted. |
| `--stop-after-steps N` | Save and exit after accepted step N; requires checkpointing. |
| `--checkpoint T` | Existing analysis CSV at time T. This is distinct from a restart file. |

Changing physics, resolution, motion, final time or analysis times on resume is rejected. Version 1 does not support extending a saved run. Distinct analysis times that collide at the existing eight-decimal CSV filename precision are rejected before simulation/output creation. A restart file cannot share a generated analysis filename in the output directory.

The observer runs after all accepted state, time, auxiliary-grid history and counters are committed. Periodic saves do not truncate a timestep or alter retry logic. State contains cell-integrated fluid variables, reduced vector potential, gauge offset, phi, mean field, mesh/connectivity, auxiliary origin, configuration, reference velocity, conservation baselines and every counter. Linear/quadratic/compact stencil coefficients are stored bit for bit, including repeated periodic-image sample IDs; they are not refitted on load.

The envelope has a magic identifier, format version, exact byte length and SHA-256 checksum. Checked decoding rejects corruption/truncation, incompatible builds, invalid tags/counts/topology, nonfinite state and invalid recovered primitives. An infinite configured timestep cap is valid. SHA-256 detects accidental corruption; it does not authenticate a third party's scientific results.

Writes use a newly created temporary file in the destination directory, file sync, atomic rename and directory sync on Unix. Before a successful rename, a failed write leaves the previous checkpoint intact. A directory-sync failure after rename is reported explicitly; the replacement has already occurred, so durable storage cannot be promised in that case. File size includes exact cached stencils and grows with explicitly requested analysis CSVs; periodic restart saves do not accumulate additional CSV snapshots. No compression or cross-build migration is implemented.

## Validation and AI review

The regression suite compares complete final serialized states after an accepted-step stop/save/load/resume against uninterrupted integration toward identical targets. It covers all eight profiles, projected caches, nonzero phi/gauge/origin, periodic rigid wrapping, deforming topology, unlimited reconstruction and actual discarded CFL trials. Separate tests cover observer failure, invalid state/fingerprints, truncation, corruption, checked lengths and atomic replacement.

CLI subprocess tests compare `initial.csv`, both analysis CSVs, `final.csv`, `summary.json`, `history.json` and `polygons.csv` byte for byte. They cover stops between outputs and exactly at boundaries, deletion of the original output directory, altered checkpoint cadence, completed-file replay, a relative resume filename, rejected overrides, output-name collisions and recovery after an actual process kill. These are determinism tests on the same build/platform, not a cross-architecture guarantee.

Run the checks with:

```sh
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --workspace --locked
```

On the implementation Mac, all **133 workspace tests**, formatting, strict Clippy, the release build, 13 M0 algebra checks and the reference-packet integrity check passed. A saved release executable also stopped the N32 jittered projected Alfvén run at accepted step 200, resumed into a fresh directory to t=1, and reproduced all six analysis artifacts byte for byte against the frozen pre-checkpoint `fb8bb14` run. That is a bounded numerical-regression check; the completed N256 convergence failure remains unchanged.

See the separately authored [AI checkpoint review](CHECKPOINT_AI_REVIEW.md). The new `mhd-io` crate uses RustCrypto SHA-256; [dependency versions and licenses](DEPENDENCIES.md) are recorded separately.
