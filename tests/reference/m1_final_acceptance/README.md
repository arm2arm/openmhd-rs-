# Accepted M1 fixed/rigid 2.5D reference

The coordinator's [acceptance record](acceptance.json) adopts the named iterative
`bulk-frame-heun-quadratic-v1 --projection-screening 1 --riemann hlld-pressure
--potential-limiter smooth-extrema` configuration for the registered periodic,
single-process fixed/rigid **2.5D** reference. Trial fraction is the historical
default 1, CFL is .3, states use f64 and timesteps are synchronized. The binary
default remains `paper-global-v2`.

The complete fresh campaign has 214 cases and 58 registered checks. Six actual
independent reductions cover 238 raw inputs, 99 boost pairs, eight spatial
ladders, twelve temporal observations, twelve primary shocks and six primary
vortices. The actual 13-stage collector, packager and copied portable verifier
passed. The [separate final AI review](review/FINAL_REVIEW.md) supports this
scope. This is AI review, not human peer review or author confirmation.

The `evidence/` and `review/` subtrees are separately closed and immutable.
Their manifests precede the acceptance record and outer inventory, so there
is no circular hash. The outer inventory pins their manifests and the two
outer payloads. The portable consistency command is:

```sh
python3 -B evidence/verify_final_review_evidence.py --outer .
```

It checks both recursive inventories and identity/report consistency. Its
`full_m1_accepted=false` result describes the immutable evidence and the
verifier's inability to make an acceptance decision. The coordinator's separate
record owns that decision. The actual command receipt is retained outside
this closed packet under `results/m1_final_acceptance_execution_20261122/`.

The archive includes selected provenance, complete compact reports, projected
bins and 237 frozen source/reference blobs. It identifies explicitly omitted
large raw duplicates by their actual consumed hashes and fresh workflow
retrieval receipts. The full 2,386-file original collection remains at
`results/m1_final_collection_20261122_attempt01/`; the portable export does not
claim to contain every raw byte or a standalone source-build layout.

The measured 3–10% fixed passive-loop error increase, 17–36% rim undershoot
increase, admitted curvature-confirmed extrema, fallback/retry counts and
historical default failures remain part of the record. This acceptance grants
no TVD/general positivity or entropy-stability theorem, general Galilean
invariance, paper/AREPO equivalence, deforming/full-3D physical validation,
MPI, local timesteps, adaptation, gravity, ISM/star formation or galaxy merger
acceptance. Those remain separately gated development.
