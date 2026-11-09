# Rejected shared-vertex face-normal experiment

The prospective contract and measured disposition are in
[the shock investigation](../../../docs/M1_SHOCK_INVESTIGATION.md).
The candidate removes the initial Riemann face-flux divergence to roundoff,
but both jittered shocks still fail positivity near t=.00333. It is removed
from the working solver. No physical M1 gate passes as a result of this probe.

`source.tar.gz` contains the exact four-case execution source, including the
short runner and seven passing operator/Heun tests. `raw.tar.gz` contains
all four runs, commands, per-step energy traces, failure outputs, budgets,
boost checks, timings and provenance. Source/binary hashes are recorded in
its `provenance.json`; `raw_sha256.json` lists every raw file. Extract source
and raw data into separate fresh directories. Reproduce with:

```sh
python3 scripts/run_shock_repro.py --profile bulk-frame-heun-vertex-v1 \
  --output-dir results/fresh_vertex_probe --trace-energy
```

An exit status of 1 is expected: two regular cases complete, two jittered
cases fail. The complete short screen took .85 seconds after a cached build.

`diagnostic_source.tar.gz` adds only the initial-state comparison report;
`initial_face_flux.log` records its command output. Reproduce that report with
`cargo test --release --locked -p mhd-vector-pot report_shock_face_normal_experiment -- --nocapture`.
It measures the oriented sum of the actual Riemann magnetic normal field,
divided by cell volume. It does not replace the cell-curl divergence operator.

`comparison.json` retains the failing-cell energy rates and both face-divergence
measurements; baseline raw data/source are in `../m1_shock_diagnosis`.
`verification.json` records the seven candidate tests and failed short screen.
All archives and their contained file hashes were verified before removing
the candidate from the working source. `archive.json` hashes the evidence
files except this explanatory README.
