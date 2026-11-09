# General shock/vortex execution probe

Sixteen small local runs at the full M0 final times; all eight boost pairs pass.
Jittered Brio Bx and coarse-vortex divergence diagnostics fail. This is not the
registered resolution ladder or M1 acceptance. See
[results and limitations](../../../docs/M1_PHYSICS_RESULTS.md).

`raw.tar.gz` retains complete cells, geometry/explicit polygon vertices, bins,
diagnostics and logs. `source.tar.gz` contains every source named in the run
provenance, extracted and verified against the frozen REANA submission.
`submission_snapshot.json` identifies that larger source snapshot. All raw
file hashes are in `runs.json`; top-level hashes are in `archive.json`.

The rerun verifies the final diagnostic-reporting script; all physical CSVs,
histories and summaries match the first probe byte for byte.
`legacy_parity.json` separately records ten wave/loop comparisons against the
pre-diagnostic frozen spline source, with exact commands and output hashes.
Historical study evidence and thresholds are unchanged.
