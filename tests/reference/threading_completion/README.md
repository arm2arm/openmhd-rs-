# Threading experiment completion evidence

Workflow `openmhd-threading-20261108.1` finished at 2026-11-08 16:15:05 UTC.
All eight scaling cases and the N256 t=1 demonstration completed. See
[the report](../../../docs/THREADING_RESULTS.md). The earlier
[partial archive](../threading_scaling/README.md) remains unchanged and includes
the verified initial N256 CSV and serial-reference record.

* `runs.json.gz`, `summary.json.gz`, `provenance.json.gz`: final remote records,
  per-file hashes, timings, physical diagnostics and source provenance.
* `source.tar.gz`, `source_snapshot.json`: same 45-file numerical source and
  complete submission provenance as the earlier partial archive.
* `n256_final.csv.gz`, `n256_history.json`, `n256_summary.json`: downloaded
  N256 outputs, checked against the completed run manifest. Initial CSV and
  initial bit parity are retained in the preceding partial archive.
* `n256_measurement.json`: post-run analytic errors and positivity/budget
  checks from those verified outputs. This is not a new acceptance gate.
* `remote_execution.json`, `remote_runtime.json`, `checks.tar.gz`: final
  command outcomes, runtime record and all eight hash-verified command logs.
* `remote_artifacts.sha256.json`: server export manifest. The large full raw
  tarball listed there was not downloaded; this is a compact completion archive.
* `archive.json`: SHA-256 of every archived file except itself.

N64/N128 raw CSVs and N256 intermediate checkpoints remain on REANA; all
their per-file hashes are retained. The full-study source and script are in
the source archive; reproduce with `python3 scripts/run_threading_validation.py
--output-dir results/threading_reproduction` in a checkout with existing
reference fixtures. The run uses the original paper profile, not the later
auxiliary-projection comparator. Different output clocks prevent a bitwise
comparison of its final state to the old serial study.
