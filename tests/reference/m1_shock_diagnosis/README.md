# Jittered-shock energy-closure investigation

See [the contract, findings and plot](../../../docs/M1_SHOCK_INVESTIGATION.md).
The baseline and both experimental reconstructions fail the jittered shock.
The two rejected experimental profiles were removed from the working solver.
Only passive energy tracing, an accepted-state observer and clearer errors
are retained. No thresholds, floors, energy resets or resistivity changed.

`raw.tar.gz` contains initial/final cells, per-step energy traces, histories,
failed-state outputs and exact experiment commands/return codes. All raw
file hashes are in `raw_sha256.json`. `parity.json` records ten bit-identical
historical wave/loop comparisons with tracing enabled.

`baseline_source.tar.gz` is the frozen pre-diagnostic source;
`centered_source.tar.gz` and `facefit_source.tar.gz` retain the two rejected
experiments and their tests. `diagnostic_source.tar.gz` is the retained
instrumented source and plot script. Each archive uses repository-relative
paths; extract into its own fresh directory to reproduce a particular version.
Use the exact commands in the experiment JSON with the rebuilt binary path.
The compiler, binary hashes and base revision are in `provenance.json`.

Regenerate the plot after extracting raw data:

```sh
python3 scripts/plot_shock_diagnosis.py extracted/shock_diagnosis --output shock.png
```

The finite-volume induction energy rate is diagnostic only; that field is
not evolved or used to overwrite the curl field. This archive does not
establish a stable shock treatment or permission to merge M1.
