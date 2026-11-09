# Auxiliary projection investigation evidence

Workflow `openmhd-auxiliary-20261108.1` completed 2026-11-08 at 16:12:39 UTC.
See [the report](../../../docs/M1_AUXILIARY_RESULTS.md) and
[prospective contract](../../../docs/M1_AUXILIARY_INVESTIGATION.md). This is a
bounded engineering comparison, not full M1 acceptance or independent review.

* `raw.tar.gz`: all 80 run directories, snapshots, summaries, histories, exact
  commands, per-file hashes, numerical provenance and original inspected plot.
* `source.tar.gz`: all 47 files recorded by the numerical runner, extracted
  from the frozen submission and hash-verified; `source_snapshot.json` records
  the complete submission, including its base revision and uncommitted files.
* `manifest.json.gz`, `runs.json.gz`, `summary.json.gz`, `provenance.json.gz`:
  convenient exact copies of the remote configuration and measurement records.
* `remote_execution.json`, `remote_runtime.json`, `checks.tar.gz`: command
  outcomes, environment and all nine remote logs. Preparation runtime cgroup
  records describe the preparation pod; the test-job 64G limit is in YAML.
* `remote_artifacts.sha256.json`: original 17-file export manifest, verified
  before archiving; `temporal.png` is the original REANA plot.
* `local_legacy_parity.json`, `remote_legacy_parity.json`: exact physical-output
  parity for four local historical profiles and 20 cases from the frozen
  previous REANA Heun study. These compare hashes, not timing files.
* `archive.json`: SHA-256 of every archived file except itself.

To reproduce, extract the source archive in a checkout providing the existing
reference fixtures and run `python3 scripts/run_heun_temporal.py --auxiliary-study
--jobs 24 --output-dir results/auxiliary_reproduction`. Then run
`python3 scripts/plot_heun_temporal.py results/auxiliary_reproduction`.
Rust 1.85.1 is pinned; the study uses the Python standard library. The archived
plot used REANA Matplotlib 3.8.0. Use a fresh output directory for every run.
