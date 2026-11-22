# Static 3D geometry visualization

`scripts/plot_geometry3.py` draws the polygon edges exported by the real
`geometry3-case` driver, using its exact literal input and complete stdout.
It produces three static camera views in PNG and SVG. It does not evolve
the mesh or produce a moving-mesh video. No 3D image has been rendered for
this source revision yet. Existing `docs/images/mesh_motion/` images show
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
Actual REANA rendering and visual inspection remain pending. Static 3D
geometry, deforming nonzero-MHD, live gas/DM/old/new-star ISM/SF/feedback and
full-duration merger acceptance remain separate open gates.
