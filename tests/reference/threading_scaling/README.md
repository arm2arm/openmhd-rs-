# Partial threading experiment evidence

Workflow `openmhd-threading-20261108.1`, observed 2026-11-08. All eight N64/N128
scaling runs completed; the N256 full-wave demonstration was still running
when this archive was made. See [the results](../../../docs/THREADING_RESULTS.md)
and [prospective contract](../../../docs/THREADING_PLAN.md).

* `runs.json.gz`, `summary.json.gz`, `provenance.json.gz`: remote measurements,
  commands, per-file hashes, exact thread-count parity results, compiler,
  CPU affinity and test-pod cgroup limits. N256 has no completed run record yet.
* `source.tar.gz`: all 45 source/configuration/contract files listed by the
  numerical runner, extracted from the frozen submission and hash-verified.
  `source_snapshot.json` records the original complete submission.
* `remote_execution.json`, `remote_runtime.json`, `checks.tar.gz`: all seven
  completed remote check commands and their hash-verified logs. Preparation
  runtime records are distinct from the numerical runner's test-pod limits.
* `initial_parity.json`, `n256_initial.csv.gz`, `serial_reference.json`,
  `serial_run_record.json.gz`: byte-identical N256 initial conditions against
  the frozen old serial executable. Later output landing times differ, so this
  is not a full N256 trajectory comparison. `n256_run.log` records mesh timing.
* `threading_scaling.png`, `plot_threading.py`: inspected scaling plot and its
  generator. The plot was generated locally from the downloaded measurements.
* `launch.json`: workflow and latest observed progress; `archive.json` records
  SHA-256 for every archived file except itself.

The full N64/N128 CSVs remain in the REANA workspace under
`source/results/reana_threading/`. The runner checked every initial/final CSV,
summary and history against its one-thread counterpart; their hashes can also
be compared directly in `runs.json.gz`. This compact archive is not a complete
download of all remote outputs. No full M1 acceptance is implied.

To reproduce, extract `source.tar.gz` in a checkout providing the existing
reference fixtures, then run `python3 scripts/run_threading_validation.py
--output-dir results/threading_reproduction`. Rust 1.85.1 is pinned. The runner
uses the Python standard library and executes cases sequentially with at most
24 threads per case. Use `--quick` only for a small execution check. Plotting
requires Matplotlib; the archived plot used local Matplotlib 3.9.4.
