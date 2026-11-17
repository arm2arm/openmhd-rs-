# Read-only accepted-state trace for #24

Workflow `openmhd-m1-column-trace-20261110.1` (`c4ad247d-9fb4-438f-8387-92bcf7edd1bc`)
finished at 2026-11-10 01:51:42 UTC. Four original finest regular/column
base/boost cases complete in 135.63–165.12 seconds. All **24 scientific-file
comparisons match byte for byte**, including the unchanged boost failure.
The diagnostic adds no landing times or numerical evolution terms.

Format, strict Clippy, **143 release/all-target Rust tests**, **68 Python tests**,
M0 algebra/reference checks and rejection of invalid snapshot strides pass.
The new frozen-rate decomposition is a separate later workflow, absent here.

The alternating-row coefficient is `(q0-q1+q2-q3)/4`, evaluated at each
column. The trace records initial/final and step 1/every 64th accepted state:
144 accepted snapshots, 152 records total. The final maximum vx coefficients
are 3.16899e-9 / 6.77845e-9 on regular meshes and .000840033 / .001097114 on
column-jitter meshes (base/boost). These coefficients are **not** the boost
acceptance norm. The original failed norm remains 5.818394374e-6 against 1e-8.

The observed maximum-coefficient logarithmic slopes over t=.04–.09 are
99.610 / 102.962 on regular meshes and 259.720 / 259.594 on columns, per unit
simulation time. These are fits to a moving nonlinear shock, **not linear
stability eigenvalues**. Growth follows the right-moving slow-shock region.
The responsible operator is not identified by this trace alone.

The [inspected plot](../../../../docs/images/m1_completion/column_mode_growth.png)
regenerates byte for byte with `scripts/plot_column_modes.py`. Four intermediate
raw snapshots near t=.07 are retained compressed; hashes agree with both
remote manifests. An independent NumPy row DFT reproduces 36 reported
coefficients within 1e-14 absolute scaled by the raw field size. This is a
postprocessing check, not an independent scientific review.

All 16 initially downloaded reports/logs and four later raw snapshots verify
against the final remote artifact manifest. The full 152 snapshot files stay
in the named REANA workspace. Complete input archives also remain in the
local immutable submission `results/reana_submission_m1_column_trace_20261110`.
`instrumentation_sources.tar.gz` retains all 144 Python/Rust/Cargo/runtime
source files selected from that snapshot, each verified against its original
296-file manifest. Large benchmark references and documentation are omitted
from this duplicate source archive and remain individually pinned in
`snapshot.json`. Its `revision` is the private export fixture; the real
repository parent is `source_revision` (`411d917`).

Scientific acceptance remains false. Continue with the frozen face-group /
magnetic-rate diagnosis; keep the full matrix stopped until a correction
passes the unchanged regression and other bounded controls.
