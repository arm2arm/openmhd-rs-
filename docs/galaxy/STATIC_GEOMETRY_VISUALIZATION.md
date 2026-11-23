# Static 3D geometry visualization

Three actual Rust-output figures are available as of 2026-11-23. Each input
ran once in its own REANA workflow using the compiled `geometry3-case`
executable; all eight registered static geometry comparisons passed. The
figures were then rendered on REANA and visually inspected. They show
static geometry, with no mesh motion, fluid evolution or MHD acceptance.

| Recorded case | PNG | SVG |
| --- | --- | --- |
| Nonuniform periodic mesh, 64 cells | [Three views](../images/geometry3_actual_20261123/case0156/mesh3d.png) | [Vector figure](../images/geometry3_actual_20261123/case0156/mesh3d.svg) |
| Bounded oblique partition, two cells | [Three views](../images/geometry3_actual_20261123/case0228/mesh3d.png) | [Vector figure](../images/geometry3_actual_20261123/case0228/mesh3d.svg) |
| Periodic Cartesian mesh, eight cells | [Three views](../images/geometry3_actual_20261123/case0048/mesh3d.png) | [Vector figure](../images/geometry3_actual_20261123/case0048/mesh3d.svg) |

The [published provenance](../images/geometry3_actual_20261123/provenance.json),
[candidate origins](../images/geometry3_actual_20261123/actual_candidate_origins.json)
and [body inventory](../images/geometry3_actual_20261123/publication.sha256.json)
bind the actual workflows, inputs, transcripts and captured rendering sources.
Each case directory includes those source and data bytes. The candidate source
is `58fe532f642e17f4961ce1ce7497882a88cbf069`; the final rendering workflow is
`openmhd-geometry-actual-plot-a02.1`, UUID
`346b7530-04e8-4589-8d5b-ec85477dd235`. The earlier render is retained in the
operational evidence: the second render corrected overlapping labels only,
without rerunning any candidate or changing its input or transcript.

The full registered static comparison family contains 252 cases. These three
figures do not replace the remaining 249 comparisons or their output review.
Periodic figures retain the recorded owner/image charts and seam incidences;
they do not reconstruct a tessellation or fold the polygons into one box.

The original `scripts/plot_geometry3.py` draws polygon edges exported by the
driver, using its exact literal input and complete stdout. The captured
`renderer.py` in each published case extends that diagnostic to the displayed
owner charts. Both produce three static camera views in PNG and SVG. A separate
[kinematic 3D preview](../MESH_MOTION_3D_PREVIEW.md) illustrates prescribed
generator motion without executing the candidate. Existing `docs/images/mesh_motion/` images show
2D geometry from the 2.5D reference and retain that scope.

After the actual driver build, input/provenance and immutable Python import
prerequisites, run the renderer on REANA with real successful driver output:

```text
python3 -B scripts/plot_geometry3.py --input literal_input.json --transcript driver_stdout.txt --output new-render-directory
```

A periodic input requires `--cell` followed by an exact persistent cell ID.
That view retains the complete recorded owner chart, including both
self-image incidences. It does not fold polygons into the primary box.
For a bounded input, omitting `--cell` shows each shared face once. Colors
follow persistent IDs; coordinates use the candidate's code units.

The renderer uses the source-pinned bridge and actual exported vertices;
it does not reconstruct geometry, interpolate positions or infer time.
Its report, captured input/transcript/source and image inventory are
diagnostic records, with scientific acceptance flags false. A drawable
transcript does not replace independent geometry validation. First visual
QA must include bounded and periodic selected-cell cases with actual
zero process outcomes, coherent reports and retained image hashes.

The independent narrow source review is
`results/galaxy_geometry3_plot_source_review_20261122/REVIEW.md`, SHA256
`751395d650dfc675bbcd88b9f5f3f3f1297f92bbac4f3d3b5c2829ce61ead453`.
It supports the persistent-ID/chart mapping and requests two small recording
corrections. This revision holds renderer bytes once for capture and report,
adds them to the final source check, protects post-mkdir capture writes, and
closes the figure before publishing completion. Handled failures preserve
partials and attempt a failed report; storage or interpreter loss may leave
an unclosed result. Actual successful process evidence remains mandatory.

No new test suite is needed for this reversible diagnostic. No renderer,
floating-point coordinate conversion, test, reference or plot ran locally.
Actual REANA rendering and visual inspection of the three figures above are
complete. Static 3D
geometry, deforming nonzero-MHD, live gas/DM/old/new-star ISM/SF/feedback and
full-duration merger acceptance remain separate open gates.
