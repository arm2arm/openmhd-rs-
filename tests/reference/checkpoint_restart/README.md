# Serial checkpoint/restart review evidence

This compact archive accompanies the separate [AI review](../../../docs/CHECKPOINT_AI_REVIEW.md), dated 2026-11-05. It documents serial continuation and I/O behavior, not M1 physical acceptance or cross-platform portability.

## Reviewer experiments

- `reviewer_provenance.json`: compiler/platform, base revision, exact reviewed working-tree source hashes, executable hash and independently run test counts. The working tree was reviewed before its implementation commit; the hashes identify the reviewed source precisely.
- `run_probe.py`: independent subprocess continuation comparison.
- `reviewer_probe_report.json`: exact commands, exit statuses, stdout/stderr and all seven matching artifact hashes for four cases. Each stopped at step 7, changed cadence from 2 to 3, and finished at step 15.

The four cases are fixed paper, fixed projected unlimited, fluid projected and prescribed projected, using a 6×6 jittered mesh and identical physical/output targets for uninterrupted and resumed runs. Reproduce the probe with a freshly built executable from the reviewed source:

```sh
cargo build --locked -p openmhd --bin vector-potential
python3 tests/reference/checkpoint_restart/run_probe.py \
  target/debug/vector-potential results/checkpoint_review_reproduction
```

The probe compares each build against itself. Its outputs may differ on a different build/platform; its checkpoint format deliberately rejects a different executable. The original review executable hash is recorded, not required as a cross-build reference result.

## Implementation-agent release smoke check

`implementation_release_verification.json` and `implementation_release_run_*.log` came from the implementation agent's saved release executable. It ran the N32 projected Alfvén case to time 1, stopping at step 200 and resuming into a new directory. Six artifacts matched the frozen pre-checkpoint `fb8bb14` baseline at `results/m1_projected_probe/n32`.

The separate reviewer did not rerun that experiment. It independently checked all six existing byte comparisons and recorded that check in `reviewer_release_artifact_check.json`.

## Deliberate omissions

`omitted_artifacts.json` gives the original local path, byte size and SHA-256 for omitted executables, restart files and raw numerical outputs from both experiments. The archive retains commands and output hashes rather than committing those binary/CSV files. Local originals are under `results/checkpoint_ai_review/` and `results/checkpoint_release_smoke_20261105/`. These paths are provenance records, not an assertion that the raw files are distributed in this archive.
