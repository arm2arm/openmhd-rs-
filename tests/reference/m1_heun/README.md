# Bounded Heun investigation evidence

Workflow `openmhd-heun-20261108.1`, completed 2026-11-08 at 14:03:54 UTC.
See [the report](../../../docs/M1_HEUN_RESULTS.md) and
[prospective contract](../../../docs/M1_HEUN_INVESTIGATION.md). This is a new
engineering comparator, not full M1 acceptance or an independent review.

* `raw.tar.gz`: all 40 run directories, initial/final CSVs, histories, logs,
  summaries, exact commands, source/execution provenance and the plot.
* `source.tar.gz`: the 43 source/configuration/contract files recorded by the
  numerical runner, extracted from the frozen submission and hash-verified.
* `source_snapshot.json`: original REANA submission provenance, including
  uncommitted-source hashes and base Git revision. The complete submission
  archive is larger than the numerical source archive above.
* `*.json.gz`: convenient copies of manifest, measurements, run map and
  numerical provenance. `temporal.png` is the original inspected REANA plot.
* `remote_execution.json`, `remote_runtime.json`, `checks.tar.gz`: command
  outcomes, runtime and all nine remote command logs. Runtime cgroup values
  were observed in the preparation pod; the test job's 64G limit is in YAML.
* `remote_artifacts.sha256.json`: original 17-file REANA output manifest,
  verified against the complete local download before archiving.
* `archive.json`: SHA-256 of every archived file except itself.

For reproduction, extract `source.tar.gz` in a checkout providing the existing
reference fixtures, then run `python3 scripts/run_heun_temporal.py --jobs 24
--output-dir results/heun_reproduction` and `python3 scripts/plot_heun_temporal.py
results/heun_reproduction`. Rust 1.85.1 is pinned. The run itself uses the Python
standard library; plotting used Matplotlib 3.8.0 on REANA.

For measurement inspection, extract `raw.tar.gz` into a new directory; its
top-level `heun/runs.json` contains per-file hashes for every run. Do not reuse
an existing result directory for new numerical executions.
