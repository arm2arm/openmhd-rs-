# Static direct-force exporter integration

The independently reviewed example is now at
`crates/gravity/examples/gravity-force-case.rs`. It was copied byte-for-byte
from the closed proposal: 12,673 bytes, SHA256
`3192814364e24a4ca1b0ab8e6216abaedff1e00e0de4c675c54996bd645a53d6`.
The source's historical “unadopted” comment records its proposal origin; this
integration adopts only the source adapter for validation. It has not been
formatted, compiled or executed, and no force agreement is established.

[Independent source review](GRAVITY_DRIVER_SOURCE_REVIEW.md) found no demonstrated
blocking API or adapter defect. Root read that review and checked the exact
four-body proposal and 32-body reviewer reading closure. The source uses current
public gravity/shared-ID APIs, standard library and the already locked SHA256
dependency. It introduces no force law, timestep, tolerance or dependency.

One bounded ASCII input supplies an isolated fixed-common-Plummer collisionless
snapshot of at most 32 particles. Inputs distinguish explicit SI base scales
from the nonphysical G=1 fixture; particle state and clock remain code values.
The example evaluates the checked production direct kernel once and exports
actual binary64 words, original and sorted IDs, full source/state/model/unit/
backend identities and their cache copies, private-pin evaluation bytes and
unrepaired diagnostics. These records retain observables; they do not attest
source code, compiler, binary, command, runtime or a numerical reference.

The complete String is assembled before the one stdout write, with a 4MiB
postconstruction limit. This is neither a peak-memory bound nor transactional
stdout. Require a genuinely successful process and complete strict decoding;
partial output, rejection or diagnostic failure cannot pass a required case.

Next gates are actual REANA format/strict-Clippy/example compilation, a
bit-preserving decoder and reference-input projection with causal malformed/
identity/failed-process controls, actual same-input exact-reference comparisons
and independent numerical-output/provenance review. The exact reference cap
does not cover N128, gradients, physical-unit evolutions, 100-period orbits,
boost/restart or gas/work/source coupling. All those G1 gates and the live
deforming nonzero-MHD merger remain required. M1's accepted scope is unchanged.
