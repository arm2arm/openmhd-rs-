# Nine actual static gravity comparisons

On 2026-11-23, all nine registered small collisionless catalogs passed their
Rust-versus-independent-reference comparisons on REANA. All 63 per-particle
and global arithmetic gates passed. Each case ran in its own original workflow,
with one Rust evaluation and one independent reference execution. No case was
rerun, and no scientific source, tolerance or measured residual was changed.

This supports the bounded static common-Plummer force slice. It does not accept
G1, orbital evolution, gas gravity, moving-mesh MHD or the galaxy merger.

| Input | Particles | Passing gates |
| --- | ---: | ---: |
| Empty catalog | 0 | 3 |
| One particle | 1 | 5 |
| Axis-aligned pair | 2 | 7 |
| Oblique pair | 2 | 7 |
| Coincident pair | 2 | 7 |
| Three particles | 3 | 9 |
| Same three particles in a different input order | 3 | 9 |
| Three particles with different persistent IDs | 3 | 9 |
| Unequal-mass pair with the registered approximately 10^-6 ratio | 2 | 7 |

All inputs use the explicitly tagged dimensionless G1 unit system, isolated
boundaries, code gravitational constant 1 and common Plummer softening 4.
Self interaction is excluded. The unequal-mass input retains its original
binary64 word `3eb0c6f7a0b5ed8d`; it is not substituted by an exact decimal
rational. These are static catalogs with zero initial momentum and no timestep.

The registered force, specific-potential and pair-energy checks retain the
inclusive relative threshold 5e-13. Raw total force and torque about the input
origin retain their strict threshold, using independently derived interaction
scales. Vector checks use the corresponding squared norm. Structural-zero
scales require exact absolute zero, with no denominator floor. The Rust
diagnostics are retained without subtracting or repairing their residuals.

The independent reference consumes the actual exported binary64 source words.
It preserves both the original input order and the separately sorted canonical
input identity. Its exact-rational and radical-enclosure certificates are
checked by the unchanged reducer on REANA. The complete eight-body reference
packet and both original supervised process journals are carried inside each
`child_result.json` output capsule.

Before scientific release, the new execution wrapper's 13 metadata methods
passed as separate original REANA workflows. One GET loss left its initial
packet at 12 passing and one incomplete case. Whole-case recovery under the
same original UUID completed that evidence, and separate offline verification
returned zero. The failed packet and an interpreter-path guard failure remain
preserved in the operational history. No metadata method was rerun.

The nine scientific submissions were all acknowledged. Their actual finished
version1 UUIDs yielded 72 output artifacts through 90 successful transports,
with a before/download/after identity check for each case. Both candidate and
reference journals show successful exit, held original process-group authority,
reaped direct children and stopped log writers. The root output review records
10294 successful inert checks and a closed 987-body review boundary. It ran no
force, reference or reducer arithmetic on the laptop. The review discloses
that the root coordinator also authored the new wrapper; no separate delegated
reviewer approval is claimed.

The compact published evidence is available here:

- [Actual nine-case review](results/gravity_static9_20261123/actual_output_review.json)
- [Publication manifest and original byte identities](results/gravity_static9_20261123/publication.sha256.json)
- [First case's exact input](results/gravity_static9_20261123/case_0000/input.txt)
- [Three-particle actual output capsule](results/gravity_static9_20261123/case_0005/child_result.json)
- [Execution wrapper and prerequisites](GRAVITY_FORCE_CASE_EXECUTION.md)
- [Existing G1 source review](G1_SOURCE_REVIEW.md)
- [Actual 252-case static geometry results](STATIC_GEOMETRY_COMPARISON_RESULTS.md)

Every case directory contains the original ASCII input, payload, root release,
case specification and all eight actual output bytes. The publication is a
compact output copy; the complete source/upload/GET command archives remain in
the separately closed local evidence boundary. The actual exported Rust binary
is 590808 bytes with SHA256
`b7185b92b1c5052f5fc315e2fa8720eae54cb26742ed4b028127449d938f0196`.
Its build source is `58fe532f642e17f4961ce1ce7497882a88cbf069`; the scientific
execution wrapper is `424d125996f2e521ed0814ebb59c30491bbd0ee4`.

Remaining G1 work includes independent gradient and covariance campaigns,
physical-unit and larger-N checks, the amended long-orbit ladder, boost and
restart evidence, and coupled gas/gravity conservation. Full workspace G00,
the remaining static geometry controls, moving geometry/MHD, galaxy equilibrium,
ISM/star formation/feedback and the full-duration merger retain their own gates.
The named fixed/rigid 2.5D M1 acceptance is unchanged.

The subsequent [G-GRAD campaign](G1_FORCE_GRADIENT.md#measured-reana-results) measured the direct force against derivatives of the total energy at six separation ratios and in a three-particle catalog.
