# Verified projection-factor metadata correction (2026-11-10)

The reporting fix in `9e99b74` passes all ten matched comparisons on REANA:
20/20 evolutions complete; every scientific file and every remaining summary
field agrees with the pinned baseline. Only the known erroneous positive-
screening `projection_preconditioner_shift` field may change. All 80 downloaded
scientific-file hashes were independently verified. This is a reporting/parity
packet, not full M1 physical acceptance.

Workflow: `openmhd-m1-reporting-campaign-20261110.1`, UUID
`01947a14-a507-4384-a4ca-9533395d08e8`, started 2026-11-09 23:52:22 UTC.
Snapshot SHA256:
`b102b766bc5b8e116811924f977e923e097c7ec3cf351647fae3bd2c8c46de04`.
The source was frozen over `9ce5304` before the correction was committed;
all 59 recorded Rust/Cargo files match the committed correction. The only
subsequent runtime-runner difference in `cb70b85` is clarified timeout help
text; the archive retains the exact executed text.

| Check on the frozen snapshot | Actual outcome |
| --- | --- |
| `cargo fmt --check` | Pass |
| Strict Clippy, all targets/features | Pass |
| Debug workspace Rust tests | 135 pass |
| Release/all-target workspace Rust tests | 143 pass |
| Python measurement/orchestration tests | 66 pass |
| M0 algebra | 13 pass |
| M0 independent references | Pass |
| Reporting baseline/current evolutions | 20 complete, 10 pairs pass |

The configurations cover `bulk-frame-heun-projected-v1` and
`bulk-frame-heun-quadratic-v1`, each with uncached κ=0/1 and cached κ=0/.5/1.
All are N8 jitter .15 standing Alfvén waves to t=.002, fixed mesh, periodic,
dimensionless mu0=1, f64, gamma=5/3. No floor or energy reset is used.

For κ=0 the cached factor is `H + 1e-8 D`; for positive κ it is `H + κ D`.
Previously the CLI always labelled the shift 1e-8. The correction exposes the
coefficient actually used during factor construction. Uncached runs report
no cached-factor shift. The unscreened encoding is preserved byte for byte.
The comparison explicitly validates old/new expected shift values before
removing that one field for comparison; other summary changes fail it.

`raw.tar.gz` contains 101 files: all 20 runs' initial/final CSVs, histories,
summaries and logs, plus the complete report. `execution_sources.tar.gz`
contains 140 Rust/Cargo/Python/configuration files extracted and hash-checked
from the exact frozen upload. `execution_snapshot.json` records all original
source/upload hashes. The pinned baseline executable SHA256 is
`e956e598768adaf547e83e6b81e1a94f994565682fb53b12b2954348ffd25a93`;
its original provenance is embedded in `report.json`.

`checks/` preserves the runtime record and all nine successful command logs.
Every log, runtime and snapshot hash verifies against the execution record.
That record is a checkpoint with status `running`: the parent numerical
campaign continued afterward. It is not an assertion that the full campaign
has passed. `sha256.json` covers the archived files and raw members.

Reproduce in the pinned REANA image with the recorded baseline executable:

```sh
python3 scripts/run_projection_metadata_check.py --baseline /path/to/baseline-vector-potential --baseline-provenance /path/to/baseline-provenance.json --output-dir results/fresh_metadata_check
```

See the [candidate audit](../../../docs/M1_CANDIDATE_AUDIT.md) for equations,
engineering departures and the remaining physical gates.
