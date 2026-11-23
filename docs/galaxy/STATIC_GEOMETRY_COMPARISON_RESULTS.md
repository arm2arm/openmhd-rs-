# Actual static 3D geometry comparisons

2026-11-23. All **252** registered analytic comparisons passed on REANA, using
one actual Rust execution and the separately executed independent reference
for each exact input. The [complete case summary](results/geometry3_analytic_20261123.json)
records every selection, original candidate/reference UUID and transcript hash.
The [actual PNG/SVG figures](STATIC_GEOMETRY_VISUALIZATION.md) are available on
this branch, with original input, transcript and rendering provenance.

| Analytic family | Cases | Eight gate groups per case |
| --- | ---: | --- |
| Periodic one cell, including self-image incidences | 36 | Passed |
| Periodic Cartesian 2×2×2 | 36 | Passed |
| Periodic Cartesian 4×4×4 | 36 | Passed |
| Periodic nonuniform 3×2×2 | 36 | Passed |
| Periodic nonuniform 4×4×4 | 36 | Passed |
| Bounded one-cell cuboid with sides 2, 3, 4 | 36 | Passed |
| Bounded two-cell oblique bisector | 36 | Passed |

Each family includes all three scales (`1e-6`, `1`, `1e6`), all six coordinate
permutations and both registered translations. The comparisons retain the
registered normalized `1e-10` limits for volume, cell centroid, positive face
area, face centroid, unit normal, central moment, normal closure and volume
closure. Squared Euclidean comparisons retain the equivalent squared limit.
Exact positive-face/cell counts and signed reference incidence inventories
are required by the unchanged reducer; self-image incidences are retained.
No error threshold, denominator floor or topology repair was added.

The compiled candidate source is `58fe532f642e17f4961ce1ce7497882a88cbf069`.
The actual standalone `geometry3-case` export is 727,792 bytes with SHA256
`6eb185eb1a423fcdc7f23c5b865b5f09e5acc20ac81f89141b527932fe67f4a2`.
Every job requested one CPU, 2 GiB and a 300-second child wait, with Rust,
Rayon and FFI thread counts set to one. Resource requests and image labels
remain distinct from observed runtime/cgroup visibility.

Three priority cases completed first; the remaining 249 were submitted once.
Four uncertain submit receipts were preserved and resolved through missing-only
uploads and first starts under their original unstarted version1 UUIDs. No
candidate or reference was rerun. Failed GET transports remain failed; bounded
fresh whole-case captures supplied the missing complete evidence without
combining fragments. All 252 accepted captures bind an original finished
version1 observation before and after eight complete artifacts.

The root's final reading review checked 299,667 metadata and identity relations,
all 2,016 registered gate groups and 182,700 recorded per-item observations.
It retained 17,890 original bodies in a separate closed reading boundary.
The original reference input/output bytes equal the bytes supplied to each
candidate comparison. Source, binary, argv, runtime, held-leader cleanup,
closed log writers, original transcript, artifact manifest and successful GET
receipts were checked. Scientific arithmetic was performed on REANA; this
host review read recorded certificates and did not run a geometry evaluator,
floating codec or reducer.

The root coordinated the execution adapter and this output review. This is
not a new independent-agent approval claim. The existing independent
[candidate source review](M2A_SOURCE_REVIEW.md),
[reference review](GEOMETRY_REFERENCE_SOURCE_REVIEW.md) and
[driver/reducer review](GEOMETRY_DRIVER_REDUCER_SOURCE_REVIEW.md) retain their
separate source/manual-mathematics scope.

Original local evidence boundaries are:

- `results/geometry_candidate252_output_review_20261123_attempt01/`, with
  manifest SHA256 `997d385f258d489ad10fed439196974840f381f5a7be9086c7effeb1b3a84d81`.
- The published summary is a byte-identical copy of its actual output review,
  SHA256 `36c3c04b9ffe0166e872166d6e5938e548db9455c9e71c0100d7528247dcce1c`.
- The complete independent-reference packet manifest is
  `757edf3a9296c85a321e1836d1e1caf1fe94ac63eec31a25b7cbadfdb26fd06c`.

## Remaining requirements

These results support the registered **static analytic comparison slice**.
They do not grant full M2/G01 prerequisite acceptance or moving-mesh MHD
acceptance. The [mesh specification](MESH_3D_SPEC.md#9-prospective-reana-fixtures-gates-and-dependencies)
keeps G00 and G02–G04, operators, motion, GCL, fluid/MHD coupling and physical
campaigns as separate requirements.

The current G00 coverage audit finds 676 listed debug/release leaves, with
passing actual output proof for the selected 186 identity, gravity and static
geometry leaves. Full current execution proof for the other 490 leaves is
still required. Eight of those are restart leaves whose source embeds
`CARGO_BIN_EXE_vector-potential`; copying a test binary alone does not establish
its executable dependency. Successful compilation/listing is not a substitute
for those method results. The earlier named fixed/rigid periodic 2.5D M1
acceptance remains unchanged.

Jitter/sliver and invalid-input families, determinism across threads and
windings, genuinely deforming geometry, nonzero-MHD evolution, gravity/ISM
coupling, stable galaxy components and the full-duration merger remain open.
