# Exact force reference: source integration

2026-11-22. The independently reviewed force-reference source is integrated
byte-for-byte as `scripts/galaxy_gravity_reference.py` and
`scripts/test_galaxy_gravity_reference.py`. Its 16 arithmetic controls remain
unexecuted. This is source integration, with no G1 or merger acceptance.

The [independent source review](G1_REFERENCE_SOURCE_REVIEW.md) found no
demonstrated blocker for the bounded 32-source arithmetic slice. The source
SHA256 is `91e11a87248f51f00dfa477708dd33f1f49b2cfd1e883a574991ec506fdeffbe`;
the test SHA256 is
`cd3885ebf4b2f1d65823c8e6a0195593b865d5ae7142831dfeb5d56b3d2c0aa6`.
Root inspected the complete review, checked its closed 33-file reading
boundary and exact source/helper identities with 106 inert checks and no
errors. Copying and AST parsing executed no target module or arithmetic.

The reference takes actual finite binary64 words and persistent ParticleIds
for an isolated common fixed positive Plummer model. It computes directed
force and specific potential, independently sums unordered pair energy, and
retains unrepaired force/torque residuals and independent interaction scales.
Exact rational/radical expressions, signed enclosures and unique finite
nearest-word certification remain available to a later comparison consumer.
Resource or rounding failure produces a typed nonpassing result.

The binary64 codec is an explicitly shared dependency:
`scripts/galaxy_geometry3_reference.py`, SHA256
`2b9f55d5ed72a08a90c3445fcd62b7702598174e04603e7ecd0d672c387df2df`.
It is loaded from one checked source buffer only on arithmetic use. Sharing
that codec is not an independent second rounding implementation. An ordinary
import performs no reference evaluation; actual import capability remains a
REANA prerequisite.

After the original frozen 56-method Python campaign closes, register the new
suite in a coherent runner generation, run its immutable import-only REANA
preflight, and execute each source-derived method in its own declared
workflow. No existing runner, snapshot, staged case or original submission was
changed by this integration. The historical `SOURCE PROPOSAL` label in the
exact reviewed module is retained; this note records its canonical location.

The one-input CLI is intended for a later independent workflow:

```text
python3 scripts/galaxy_gravity_reference.py --input <actual-words.json> --output <fresh-directory>
```

Before comparing Rust output, retain actual source/model/unit/backend/time
and stage identities, original and canonical input bytes, successful process
receipts, exact allowlisted output closure, and independent error reductions.
A reference packet alone cannot attest those Rust identities. There are no
actual input references, Rust comparisons, N128 controls, gradients, physical
unit/orbit, 100-period, boost or restart results from this source integration.
The protected timestep ceiling and amended orbit ladder remain unchanged.
Gas gravity/work, sources, moving nonzero-MHD and the full galaxy merger keep
their separate gates.
