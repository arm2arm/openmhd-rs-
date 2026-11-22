# Reproducible galaxy sampling: proposed address and endpoint contract

2026-11-22. **Coordinator proposal for independent review; unimplemented and
unexecuted.** This selects a concrete candidate for the still-open IC RNG
choice in [the gravity contract](GRAVITY_PARTICLES_SPEC.md). It preserves
the existing proposed star-formation stream and supplies a distinct stream
for collisionless initial-condition sampling. M1 acceptance precedes new
implementation/tests. This does not accept a DF, a disk or a merger.

The hash primitive is SHA-256 from the complete August 2015
[FIPS 180-4](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf),
section 6.2; section 3.1 defines its word convention. The project already
locks `sha2 =0.10.9` and exposes `mhd_io::digest`, which concatenates supplied
byte slices in order. No new dependency or hash implementation is proposed
here. The complete standard and official
[NIST byte-oriented vectors](https://csrc.nist.gov/Projects/Cryptographic-Algorithm-Validation-Program/Secure-Hashing)
are retained and hashed in [the inventory](random_sampling_sources.json).
Relevant PDF pages were rendered and inspected. These sources specify the
hash and its informal test inputs; they do not endorse this simulation RNG,
prove independent uniform outputs, or certify NIST validation.

## IC address: `ic-sha256-open52-v1`

Each draw is a pure function of the following **90-byte** message. Offsets
are half-open byte intervals. Serialize every integer explicitly; never
hash native Rust struct memory, a JSON number, display text or a native
`u128` interpretation of the identity struct.

| Bytes | Field | Encoding |
| --- | --- | --- |
| 0..22 | Domain | ASCII `openmhd-ic-uniform-v1` followed by one NUL byte |
| 22..54 | Seed | Exactly 32 configured bytes, retained as 64 hexadecimal digits |
| 54..62 | Component stream | `u64`, little endian; stable configured component identifier |
| 62..70 | Sampling entity namespace | `u64`, little endian |
| 70..78 | Sampling entity counter | `u64`, little endian |
| 78..82 | Purpose | `u32`, little endian; fixed values below |
| 82..90 | Draw index | `u64`, little endian; zero for each first quantile below |

Sampling entities use the checked `ParticleId(EntityId)` convention. They
are real candidate particle identities, never array positions, MPI ranks,
thread IDs, face/image IDs or hash-allocated canonical IDs. A component is
an actual configured halo/bulge/disk stream, not a species-dependent force
law. Its mapping must be unique within the IC manifest. Use disjoint galaxy
namespaces from the outset. An explicitly remapped imported catalog retains
its original sampling-address map; it must not be regenerated using new IDs
and presented as the old realization. Restart reads the accepted catalog.

The proposed decimal seed labels 1101, 1102 and 1103 mean the corresponding
`u64` encoded into seed bytes 0..8 little endian with bytes 8..32 zero. A
full configured 32-byte seed instead uses those exact bytes. These inputs
are reproducibility labels, not an entropy or security claim. Different
seeds/domains are intended distinct streams, not a proof of independence.

| Purpose | Value | Meaning |
| --- | --- | --- |
| `radius_quantile` | `0x1001` | Radial enclosed-mass quantile |
| `position_mu` | `0x1002` | Position direction cosine |
| `position_phi` | `0x1003` | Position azimuth |
| `speed_quantile` | `0x1011` | Conditional speed quantile |
| `velocity_mu` | `0x1012` | Velocity direction cosine |
| `velocity_phi` | `0x1013` | Velocity azimuth |

Compute `digest=SHA256(message)`. Keep the standard's output byte order;
then explicitly interpret `digest[0..8]` as a **little-endian** `u64 r`.
This latter conversion is a sampling convention and does not change SHA's
internal word convention. Candidate open-interval mapping:

```text
k = r >> 12                         # 0 <= k < 2^52
U = (f64(k) + 0.5) * 2^-52           # 2^-53 <= U <= 1-2^-53
```

In binary64, the integer conversion, half addition and power-of-two scaling
are exact in this range. Each of the `2^52` midpoint values has `2^12`
preimages among all `u64` inputs. Uniform digest words would therefore give
uniform midpoint values. Do not claim that mathematical conditional result
proves the hash outputs are IID random variables. No period, collision-free
output or cryptographic RNG certification is asserted.

The tempting 53-bit formula `(f64(r >> 11)+0.5)*2^-53` can round its largest
value to **1**. It is not the proposed open mapping. No clamp or retry is
permitted to conceal such an endpoint error. The existing SF convention is
instead the separate half-open map `(r >> 11)*2^-53`, with domain
`openmhd-sf-uniform-v1` and its own parent/source-counter/draw fields; it
remains unchanged. Do not change a Bernoulli law by substituting the IC map.

## Spherical quantile transform and catalog transaction

Only after a nonnegative, normalized DF and its numerical representation
pass [the softened equilibrium gates](SPHERICAL_EQUILIBRIUM_SOURCE_NOTE.md),
define

```text
F_r(r) = (4*pi/M) integral_0^r s^2 rho(s) ds,
F_v(v|r) = (4*pi/rho(r)) integral_0^v s^2 f(Psi(r)-s^2/2) ds,
r = inf{x in [0,R] : F_r(x) >= U_radius},
v = inf{s in [0,sqrt(2*Psi(r))] : F_v(s|r) >= U_speed}.
```

The generalized-inverse convention fixes plateau/tie semantics. An invalid
normalization, unresolved DF sign, nonmonotone table, failed finite bracket
or inverse with unresolved uncertainty rejects IC construction; drawing a
different sample does not repair the input model. Exact endpoint limits and
table/root uncertainty remain part of the independent DF/CDF gate. This note
does not invent an accepted interpolation grid or inverse tolerance.

For each direction use its separate draws:
`mu=2*U_mu-1`, `phi=TAU*U_phi`,
`n=(sqrt((1-mu)*(1+mu))*cos(phi), sqrt((1-mu)*(1+mu))*sin(phi), mu)`.
Position and velocity are `r*n_position` and `v*n_velocity`. For ideal
independent continuous uniforms, `dOmega=dmu*dphi` gives the isotropic law;
the finite midpoint lattice, rounded angle/transcendental functions and
numerical inverse require their own diagnostics. Do not draw three uniform
Cartesian components and normalize them as a substitute spherical law.

The first equal-mass reference uses mass `M/N`. Stage a checked contiguous
ID allocation and the entire catalog on scratch state, then commit once
all DF/CDF/state checks pass. Failed construction consumes no IDs or mutable
random state. Draw-index/allocator overflow is an error, never wrapping.
Use one address per named quantity, without rejection draws in this first
inverse-CDF path. A later rejection, stratified, antithetic or quasi-random
sampler needs a separately named stream and reviewed law.

Record the seed, stream-definition hash, purpose/component maps, sampling
IDs, DF/table/reference/units hashes, compiler/binary and transformation
history with the catalog. Storage permutation and thread scheduling do not
change addresses. Relabelling sampling IDs or changing N/table/physics can
change the realization; deterministic access does not promise timestep or
resolution-invariant star histories. Centering/symmetrization is not part of
this sampler. Any explicitly chosen IC COM transform must retain raw and
transformed diagnostics and be applied once; never recenter live evolution.

Hash/message and mapped-uniform bits must agree across supported builds.
Same-build/thread/restart catalog parity also requires identical accepted
tables and deterministic inverse/arithmetic order. No cross-platform bit
identity is promised for `sin`, `cos`, square roots or numerical CDF tables
without actual evidence; record tolerance and binary/architecture separately.
This spherical component path does not specify a disk DF or gas equilibrium.

## Prospective independent REANA cases

All cases are unexecuted. Each parameter/thread member gets its own workflow
with explicit resources after the immutable build and M1 prerequisites.
No local hash-vector/RNG/sampling probe was run to prepare this source note.

| Case | Frozen challenge / expected property | Resources per member |
| --- | --- | --- |
| `rng-hash-source` | All SHA256ShortMsg and SHA256LongMsg records from the pinned official byte-vector archive, Rust digest versus published MD; honor Len in bits, including Len=0 despite its Msg=00 placeholder. A separate Python hashlib oracle checks message concatenation. No CAVP certification claim. | 1 thread / 1 GiB |
| `rng-address` | Literal asymmetric seed bytes `00..1f`, component 7, namespace `0x0102030405060708`, counter `0x0a0b0c0d0e0f1011`, each six purposes and draw indices 0 and `u64::MAX`; compare a separately assembled Python byte message and Rust message, then hashes. Also zero/max IDs, seed labels and explicit wrong-endian/domain negative controls. Every addressed message is exactly 90 bytes. | 1 thread / 1 GiB |
| `rng-float-edges` | Synthetic word high-52 values 0,1,`2^51-1`,`2^51`,`2^52-2`,`2^52-1`, varied discarded low bits; exact midpoint bits/range/multiplicity argument, no zero/one. Check the unchanged half-open SF map separately. | 1 thread / 1 GiB |
| `rng-schedule` | Namespace `0x0102030405060708`, counters 0..4095, component 7, all six purposes at draw 0, seeds 1101/1102/1103; natural/reversed/left-rotated-by-17 storage, R=1/2/4 and checkpoint restart. Canonical address/word/uniform tables must be bit-identical; include overflow and failed-catalog rollback. No random state shared between workers. | R threads / 1 GiB |
| `equilibrium-quantiles` | Only after accepted finite-epsilon DF/CDF references: inspect inverse enclosures, radial/conditional-speed probabilities, angular moments and raw COM/P/L for the full registered N/seed cases. Retain independent reference/finite-table/sample uncertainties and the existing source/live gates. No resampling failed seeds or trimming negative-DF energies. | 1 thread / 2 GiB |

Acceptance order is hash/address/endpoint correctness, independent DF/CDF
closure, sampling/restart evidence and then the existing live-equilibrium
gates. The three seed labels and an engineering hash choice alone do not
establish equilibrium, statistical adequacy or the requested merger physics.
