# Static geometry export and exact comparison source

2026-11-22. The independently reviewed exporter, decoder and error reducer are
integrated from the exact proposal. No exporter, new method or full comparison
has run. The [source review](GEOMETRY_DRIVER_REDUCER_SOURCE_REVIEW.md) found no
demonstrated blocker in the bounded slice and supported the eight prospective
[comparison norms](G01_COMPARISON_NORMS.md) before execution. This is source
integration, not G01/M2a or moving-MHD acceptance.

`crates/moving-mesh/examples/geometry3-case.rs` invokes the actual checked
`HalfSpaceOracle3` once and exports finite scalar words, complete canonical
owner/image face keys, both self-face incidences, chart translations and raw
quality observations. `scripts/galaxy_geometry3_bridge.py` preserves input
words and original ordering, then checks complete output grammar and topology.
`scripts/galaxy_geometry3_compare.py` retains exact reference values and
certified enclosures through normalization and inclusive threshold decisions.
Unresolved bounds cannot pass. No candidate normalization floor or substituted
nearest reference word is used.

The source identities are unchanged from the review:

| Source | SHA256 |
| --- | --- |
| Rust example | `fc30eb85615bbaee863e802cb01acca80f82ca6a1f774b16a475f2394c81f37f` |
| Python bridge | `bbb5f5d0603d665ac1f0904741bc868953a047418711e6c98280636c08a03c16` |
| Exact reducer | `c4c57e5216a59d4578365fad88c636f04d13e41ef3465edb6f26cdba4293c530` |
| Bridge controls | `f13361db7aa9d2160ecfae24ce81194576a432c8e5f949c35a25fde2a4922475` |
| Reducer controls | `61badb74751c9043ab7567833c044d2e85644b4c2b299279cb1795379ead965f` |

Their 16 structural and 12 arithmetic methods are registered as mandatory
suites in the next frozen Python generation, which now contains 100 methods:
18 preflight, 16 native-case, 3 submission, 15 geometry-reference, 16
gravity-reference, 16 bridge, 12 reducer and 4 runner-isolation methods.
This generation requires its own actual immutable import-only prerequisite.
The earlier closed 56-method campaign remains a separate source generation;
none of its old results or certificate releases the added methods.

All eight design thresholds remain `1/10000000000`. The explicit norms use
independent reference V, Lref and area/surface enclosures. Euclidean centroid
and closure errors are compared as squared quantities with squared thresholds;
every owner's absolute face chart participates, including both self uses.
The retained covariance, polygon, radius, distance and other quality values
have no invented acceptance tolerance. Arithmetic agreement alone cannot
attest execution or complete geometry validation.

Next are actual REANA formatting, strict all-target Clippy, example build and
Python import/resolve prerequisites, each independent method, then all 252
registered exact-input/reference/candidate cases with complete source, binary,
compiler, command, runtime and original-input provenance. Sensitivity controls
must reach full reductions for wrong right charts/self incidences, key/row
inventory errors, independent denominators, cross moments, squared threshold
boundaries and unresolved enclosures. Require successful complete reference
and candidate outputs; rejection cannot satisfy a required case. Full geometry
conditioning/polygon, operator/moving/Cdot/GCL/nonzero-MHD and live-component
gravity/ISM/merger gates remain open.
