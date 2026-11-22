# First isolated direct-gravity/KDK implementation

2026-11-22. **Code and written controls; not built, formatted, linted, tested or
numerically accepted in this author task.** M1's acceptance at `309ae41` is
restricted to the named periodic fixed/rigid, single-process 2.5D reference.
It permits this next implementation slice; it does not validate gravity.
The full goal remains deforming full-3D moving-Voronoi nonzero-MHD gas with
isolated gravity, live DM/old/new stars, published multiphase ISM/SF/feedback
and a validated full-duration merger.

The new [gravity crate](../../crates/gravity/src/lib.rs) implements only
checked collisionless point sources with one fixed common Plummer epsilon,
a serial direct force evaluation, synchronized fixed-mass KDK, and raw
diagnostics. No gas geometry is manufactured. No tree, population evolution,
birth, mesh, MHD, MPI, cooling or source coupling is wired into it. The
[source inspection inventory](../../crates/gravity/SOURCE_INSPECTION.json)
lists exact source hashes, byte counts, context/proposal identities, all
direct test selectors, actual inert checks and unexecuted prerequisites.
It is a delivery receipt, not a numerical result or an independent review.

## Authority and equation map

The [integration contract](INTEGRATION_CONTRACT.md),
[gravity contract](GRAVITY_PARTICLES_SPEC.md) §§2–4,6.1,9,11–12, and
[G1 literal review](G1_LITERAL_PROPOSAL_REVIEW.md) remain authoritative.
The original two ignored proposals stay unchanged and unadopted as complete
runtime/reference packets. This implementation maps their small manual
controls into checked Rust input construction; it does not freeze the full
G1 campaign or fill absent high-precision outputs with candidate results.

The [source review](G1_SOURCE_REVIEW.md) of frozen `8fe7342`, committed at
`3e525cc`, identified a long-orbit ladder/ceiling conflict and an implicit
empty-step policy. The [campaign amendment](G1_ORBIT_CAMPAIGN_AMENDMENT.md)
implements the coordinator's decisions: retain the old ladder as rejection
controls, preregister an additional feasible ideal-step ladder with unchanged
physical gates, and explicitly reject empty KDK steps. Only two existing
test bodies and the related documents/inventories change; production Rust,
the unconditional ceiling, APIs and all 39 selector names remain unchanged.
This author follow-up is unexecuted and needs independent revision review.

| Source/equation | Implemented path and scope |
| --- | --- |
| GP-1, gravity §2 | `src/units.rs`: SI base scales, derived code G, specific/total quantities and named cgs boundary. Constants/provenance are explicit inputs. |
| Shared IDs; gravity §3 | `src/state.rs`: shared `ParticleId`, private particle fields, checked momentum or velocity input, immutable sorted catalog and versioned state/source bytes. |
| GP-2, gravity §4 | `src/kernel.rs`: `d=x_right-x_left`, `s=sqrt(d·d+epsilon²)`, `F_left=G*m_left*m_right*d/s³`, `Phi_left=-G*m_right/s`, `Phi_right=-G*m_left/s`, `U_pair=-G*m_left*m_right/s`. |
| GP-2 serial oracle | `src/direct.rs`: sorted real IDs, `i<j`, one force and its negation per evaluation/pair, deterministic Neumaier component/scalar reductions, ID-keyed immutable output. |
| GP-4, gravity §6.1 | `src/kdk.rs`: half kick, drift, endpoint force, final half kick; accepted full-step catalog/cache commit together. Conservative registered step ceiling is enforced. |
| GP-6 and internal virial, gravity §9 | `src/diagnostics.rs`: laboratory mass/P/L/K/U/H, raw net force/torque, COM, direct internal velocity-deviation kinetic energy, virial work and typed undefined scales. |
| Engineering representation | `src/identity.rs`, `src/checked.rs`: versioned big-endian exact input-bit encodings, SHA-256 plus full-byte equality, checked finite arithmetic and compensated sums. |

The published Plummer potential is in the complete retained Dehnen
[astro-ph/0011568v1](https://arxiv.org/pdf/astro-ph/0011568v1), PDF p3 §1.3
Eq3; PDF SHA-256
`6d1b778745aa433fe5021549ed4cd4def0b9dc28810aca0a2681d5ec53d53dbc`.
The attractive force here is the independent derivative of that potential,
as recorded in the G1 review, rather than an unqualified transcription of
the apparent printed Eq4b sign discrepancy. That is not an official erratum.
Hairer's complete [2010 lecture 2](https://www.unige.ch/~hairer/poly_geoint/week2.pdf),
PDF p2 Theorem2/Eq2, SHA-256
`f4f15ff5124fb685870e13b36e54cbc4edc96744199b518ec12e1c5cf006f0fb`,
supplies the separable Verlet/KDK construction. Neither primary supplies
these toy ICs, a measured floating-point result, or the engineering cache
encoding. Complete retained sources/pages and prior manual derivations are
identified by the original proposal/review inventories; no new external
implementation was copied or dependency code adopted from these papers.

This worker previously authored the G1 literal review and adjacent narrow
gravity/spherical interface and virial-frame corrections, as well as ISM
and metadata work. This implementation does not independently approve
those interfaces or itself. Root source/integration review and independent
numerical references/output review remain required.

## Checked state, units and identities

`Particle::from_momentum(id,mass,x,p,metadata)` accepts only positive finite
mass, finite Cartesian x/p and representable finite `p/m`. Primary momentum
is stored. `from_velocity` checks and forms `p=m*v` once; subsequent velocity
is derived from the actual stored p/m. The caller retains original conversion
inputs if needed for its external receipt. Cartesian coordinates are isolated,
nonexpanding coordinates, with no periodic wrapping/minimum-image operation.

`ParticleMetadata` contains DM/Star kind, softening class, component and galaxy
tags. These are collisionless gravitational labels, never species-dependent
force physics. `Star` here does not construct or validate a stellar population,
formation epoch, birth packet or return history. Initial populations and later
new-star records must satisfy their separate metadata/source contracts before
galaxy use. A cell/event wrapper cannot be supplied where a ParticleId is
required. There is no gas variant or placeholder geometry epoch.

`Catalog::new` validates finite time, sorts by the shared persistent-ID order,
and rejects duplicate payloads across all particles regardless of kind or tag.
Zero namespace/counter payloads are valid. Particles/catalogs expose read-only
fields/slices; they do not allocate identities. The shared run-wide registry
must separately retain issued IDs/tombstones and check particles against
cells/events and namespace roles when those exist. This crate neither forks
that registry nor infers identity from array position. Its collisionless
checkpoint is not a complete future gas/source/RNG/allocator checkpoint.

`UnitSystem::si(L0,M0,V0,G_si,mu0_si,provenance)` is the single owner of the
physical map. All five numeric inputs and derived positive scales must be
finite and representable; provenance must be nonempty. `si_inputs()` exposes
the immutable actual supplied constants/scales/provenance for reporting.
The code scales are

```text
T0=L0/V0; rho0=M0/L0³; p0=rho0*V0²; E0=M0*V0²
momentum0=M0*V0; angular_momentum0=L0*M0*V0
acceleration0=V0²/L0; specific_potential0=V0²; force0=E0/L0
G_code=G_si*M0/(L0*V0²)
B0=V0*sqrt(mu0_si*rho0); A0=B0*L0; mu0_code=1
power0=E0/T0; volumetric_power0=p0/T0.
```

There is no independent G-code setter and no physical default/CODATA/IAU
constant inferred by the crate. Thus three arbitrary physical scales cannot
also impose G=1. `dimensionless_g1()` is a separate non-SI tag; its SI/cgs
conversions fail with `PhysicalUnitsRequired`, even if a physical map happens
to derive G-code=1. Catalog numbers/step arguments are in the selected code
length/mass/time convention; physical timestamps/rates must cross the same
T0-to-SI-seconds adapter once at a future shared boundary. No cosmological
h/a or hidden Gaussian magnetic factor is introduced. The cgs API multiplies
SI density/specific energy/pressure/volumetric power by `1e-3/1e4/10/10`
respectively and provides the reverse path through the same SI owner.
It does not infer temperature, composition, cooling or a thermal closure.

The version-1 encodings are binary, not a JSON-float or eval grammar:

| Identity | Exact ordered body after its literal version/tag prefix |
| --- | --- |
| Units, physical | Five supplied f64 bit patterns L/M/V/G/mu0; length-prefixed UTF-8 provenance; 16 derived scale bits in `Quantity` declaration order; derived G-code bits. |
| Units, fixture | Literal `gravity-units-v1\0dimensionless-G1-mu01`; no fictitious SI inputs. |
| Source catalog | Count u64; sorted fixed 32-byte lower-case EntityId hex, kind u8 (`DM=0,Star=1`), class u16, mass bits and three position bits for each real source. The enclosing prefix specifies collisionless ParticleId sources. |
| Full state | Time bits, revision u64, length-prefixed full source bytes, then each source's three momentum bits, component u16 and galaxy u32 in the same order. |
| Model | Isolated/common-Plummer/no-self version tag, G-code bits, epsilon bits, common class u16. Full units have a separate compulsory pin. |
| Backend | Serial sorted `i<j` Neumaier version tag and explicit configuration revision u64. |
| Evaluation/checkpoint | Versioned length-prefixed exact pin bodies plus input G/epsilon bits, pair count, output diagnostic bits and ID-keyed samples; checkpoint also includes full state/model/unit/backend bodies. See the small literal encoders for field order. |

All integer/IEEE bit words are big endian. Byte lengths/counts are u64 on the
supported 64-bit target. Supplied signed zeros are preserved, so physically
equivalent input encodings may deliberately differ in cache identity. NaNs
and infinities never enter a valid encoding. SHA-256 is computed over these
exact bytes; equality compares the complete bytes as well as the digest.
This is a fixed implementation encoding for review, not an adopted portable
file format or a substitute for source/compiler/runtime provenance. A future
encoding/algorithm change needs a version change and new immutable evidence.

`Evaluation::validate_for` independently checks exact time bits, state
revision, source identity, full state identity, G, epsilon, model, units and
backend, then sample count/order/IDs. It reports the first typed mismatch
in that order. The nine internal written guard controls deliberately poison
one private pin at a time so another stale field cannot hide a missing check.
The public-context control separately constructs real changed states/models.
Raw read-only samples can be inspected for a receipt; applying a cached force
requires validation against the current catalog/model/config. `acceleration`
does that validation and divides the force by the current particle's mass.
KDK/diagnostics validate before consumption. No mutable cache builder/rebinder
is exposed.

## Pair arithmetic, diagnostics and atomic KDK

The direct backend processes exactly the unordered pairs of the sorted real
catalog. Distinct co-located IDs are retained, with zero force and finite
negative U/Phi. A repeated ID is rejected, and the public pair helper rejects
a self pair. Every particle must have the selected common class even in a
one-source catalog. Common epsilon is positive and immutable; epsilon=0,
adaptive/mixed-class softening and periodic gravity are unsupported.

Checked operations reject nonfinite intermediate values and nonzero products
or quotients rounded to zero. They are deliberately conservative rather than
a scale-free/extended-range kernel: intermediate overflow or tiny square
underflow can fail even when a differently scaled expression could yield a
representable final answer. Diagnostic norm/scale overflow also fails the
evaluation. Failures are typed errors, never clipped displacements, a force
floor or a zero result. This does not certify accuracy for arbitrary extreme
finite inputs; the independently frozen fixture domain remains essential.
Memory exhaustion, panic and process loss are not covered by Result atomicity.

Pair forces are computed once and accumulated with opposite signs. Per-axis
forces, potentials, pair U and reported raw diagnostics use checked Neumaier
sums in fixed order. No mean-force, torque, momentum or energy correction is
applied. Force and acceleration are separate APIs. The potential sample is
specific energy; U is counted once per pair. `Evaluation` also reports actual
candidate summed magnitudes (per-ID force/Phi, |U|, `2 sum |Fpair|` and
`sum (|xi|+|xj|)|Fpair|`). They are useful diagnostic ledgers, **not independently
certified reference denominators**. Acceptance must use independently bounded
analytic/reference scales, especially at cancellation points. Zero scales
remain zero, with absolute residuals and no tuned denominator floor.

`measure` reports raw M/P, COM and COM velocity, origin/internal angular
momentum, K_lab, U, H_lab, net force/torque, I_cm, W and K_int. K_lab is
computed as `sum (p dot (p/m))/2`, algebraically `sum p²/(2m)`;
K_int uses `sum m*|v-P/M|²/2` directly. It is not the difference of two
large energies. W uses `(x-Xcm) dot F`; virial residual is
`abs(2*K_int+W)/(2*K_int+abs(W))`. Empty COM/internal quantities are None.
A nonpositive virial scale is `VirialResidual::Undefined` with a typed reason,
not an equilibrium pass. Other nonfinite diagnostic intermediates are errors.
Free/one-source states can still be integrated while their virial diagnostic
is explicitly undefined. The result is a collisionless global ledger only;
per-tag exchange reports and bounded gas pressure/magnetic/surface terms are
not supplied or silently treated as a closed collisionless system.

`KdkSystem::new` checks forces and diagnostics before accepting an initial
state. For each `try_step(dt)` it:

1. Checks positive finite dt, validates the old cache, and enforces
   `dt <= .05*sqrt(epsilon³/(G*Mtotal))`. Empty catalogs can be constructed,
   but a positive finite empty KDK step returns `EmptyTimestep` without
   changing its checkpoint, time or revision; it is not a free empty drift.
   Half dt must be positive/representable, the rounded endpoint time must
   strictly advance, and the revision must not wrap.
2. Privately constructs the checked half-kicked/drifted catalog, with actual
   rounded binary64 coordinates/momenta and new endpoint time/revision.
3. Evaluates that actual endpoint, applies the final half kick privately, then
   constructs the full-step catalog. No force from an old epoch supplies the
   final kick.
4. Evaluates at the same endpoint positions again to pin the *full* final
   momentum state, and checks all final diagnostics. This intentional extra
   direct pass avoids an unchecked relabel of the half-momentum cache. Each
   evaluation still computes every unordered pair exactly once.
5. Commits catalog/cache only after all preceding Result operations succeed.
   Returns dt, start pins, before/after raw diagnostics, the actual drift
   catalog/forces and final cache in `StepReport`.

An error preserves the entire accepted catalog/cache. It allocates no real
ID or RNG counter. The caller must retain each report, supplied dt, rejection
reason and any trial-input receipt; this library is not an output service
and does not suppress failed attempts. dt is the integration argument while
endpoint time is its separately retained rounded sum; it is never represented
as an ideal rational time. The in-memory checkpoint includes the immutable
catalog/model/units/config and exact cache; restore validates them. Durable
file I/O/decoder, cross-binary restart and future allocator/source-event/RNG
restore are deferred. No automatic timestep adaptation or retry is hidden
in this module.

## Written controls and remaining reference closure

There are **39 direct written test functions**: nine private isolated cache
guards and thirty integration controls. Names/targets in the inspection
inventory are the authoritative per-method selectors. No ignored tests,
stochastic draws, callable factories or numerical placeholder passes exist.
The controls are grouped below without claiming full G1 coverage:

| Written family | Source of its expected meaning; limits |
| --- | --- |
| Empty/one/self/coincident; axis/oblique/triplet; equal masses | Reviewed exact eps=4 manual GP-2 fractions, including retained co-located pair energy, Phi/U signs and distinct acceleration; empty public KDK step additionally requires typed `EmptyTimestep` and unchanged checkpoint/time/revision. |
| Registered small ratio input | Exactly `q=f64::from_bits(0x3eb0c6f7a0b5ed8d)`, i.e. `4722366482869645*2^-72`. Written decimal-literal bit comparison runs only in the future test. Force/U/Phi expectations use this exact q, not rational `1/1000000`. |
| Permutation, tag/ID relabel, translation, 90-degree rotation | Deterministic small controls. ID rename preserves relative ordering; it is not proof that arbitrary ID reordering gives bitwise equality. Seeded N=4/32/128/general rotations remain absent. |
| Bad particles/model/units/common class/intermediate arithmetic | Explicit semantic constructor/evaluation errors, including one-source class validation and ordinary isolated displacement overflow. Wrong wrapper/gas view cannot be expressed as a valid input type. |
| Units/cgs | Synthetic SI constants and exact dyadic base scales only. One owner, rejected invalid scales, round trips and a second SI map with derived G=1/4; physical force/Phi/U compare to the same manual axis fractions. Astronomical profile/orbit conversion validation remains pending. |
| Cache | One guard at a time plus real time/revision/position/momentum/model/unit/backend changes; no fake gas epoch. |
| KDK/manual drift/actual endpoint | Exact free-body drift/K=14. The pair test compares ideal symbolic positions only at the algebra tolerance and separately retains actual rounded endpoint inputs/cache. It does not claim independently evaluated endpoint forces or energy order. |
| Atomicity | Invalid dt/ceiling, revision overflow, nonadvancing rounded time and a failure after private drift/evaluation begins leave checkpoint bytes unchanged. The latter uses explicit dyadic large co-located sources: x=3*2^510, v=2^511, eps=8, h=1/2. Initial x²=9*2^1020 and v²=2^1022 are finite; trial x=2^512 makes a diagnostic squared norm unrepresentable. This is a deliberately rejected numerical-scale input, not a physical instability. |
| Raw ledgers/short boost/reversal/in-memory restart | Nonzero lab P/L preserved; internal versus lab energy distinction, short fixed dt sequences, byte-identical same-binary checkpoint continuation and raw short reversal residuals. These do not replace the registered long boost/restart/orbit gates. |

The existing dt/revision-rejection selector additionally checks the original
T/{128,256,512,1024} requests for d=1,m=(1,2),epsilon=.1. A std-f64 period
expression supplies guard-branch inputs only; each request must produce
`StepAboveCeiling` and preserve accepted checkpoint/time/revision. Its resting
momenta do not furnish a circular IC or independent period/endpoint oracle.
The four checks remain within that existing written method; each actual
long-integration level below remains a separate future REANA case.

Small scalar/component comparisons use the unchanged `5e-13` algebra budget
and explicit manual nonzero scales; structural zero-scale cases use absolute
zero checks. The oblique raw-torque control uses twice the largest exact
individual torque component, a stronger fixed small-case component scale,
not a numerical norm oracle. The reported candidate scale never substitutes
for the independent acceptance scale. These are ordinary f64 evaluations of
reviewed rational expressions when run; no high-precision reference table,
successful rounding test, reference uncertainty or output bit history has
been invented here.

Before G1 acceptance, independently close and freeze the remaining exact
input/reference packet: high-precision GP-2 values and gradients with another
loop/layout, actual-rounded-endpoint forces separately from ideal KDK,
reference uncertainty and cancellation/operation-count bounds; seeded
N=4/32/128/general orthogonal transforms; physical SI profile and rescaling;
the softened circular binary d=1,m=(1,2),epsilon=.1, with the original
T/{128,256,512,1024} retained as infeasible requests requiring rejection
observations, and additional actual integration steps
T/{8192,16384,32768,65536} for 100 periods under the unchanged ceiling;
eccentric/plunge references and fixed-list boost/restart histories. The
added ladder's finest-three order fit uses T/{16384,32768,65536}. The linked
manual ideal bound puts its coarsest step/ceiling ratio below 15/16; it does
not certify the actual rounded period, step, guard or endpoint. Initial
orbital momenta/period rounding and all random input bits remain absent,
rather than generated by this kernel as its own oracle. No long evolution
starts before those independent references and prerequisites pass.

Retain the existing full gates: algebra `<=5e-13`; independent-U gradient
plateau `<1e-7` and derivative `<5e-13`; covariance `<=5e-12`, raw net
force/torque `<5e-13` reference scales; at least four timesteps with
finest-three order `>=1.8`; finest energy excursion `<1e-4 E_scale`,
COM/P/L `<1e-11`, no secular trend larger than excursion, fixed-list reversal
`<1e-10`; physical rescaling `<1e-11` kernel/`<1e-8` orbit and the other
parent G1/G2/G4/G5 gates. A passing short control cannot certify those gates.

## Integration and prospective REANA execution

Root has registered `crates/galaxy-types` and `crates/gravity`; their coherent
workspace/lock source freeze and execution review remain root-owned. This
task changes neither root file. The
dependency graph is `gravity -> galaxy-types` and `gravity -> sha2=0.10.9`,
with only the latter's already locked cfg-if/cpufeatures/digest graph. The
exact existing sha2 package is MIT OR Apache-2.0; its local primary manifest
and MIT license were inspected. No new numerical dependency or copied kernel
is introduced. The shared-ID source now inspected provides the required
new/entity/namespace/counter/Display/Ord APIs. Its separate author/root
review owns registry/allocator acceptance.

After independent source/integration review and coherent committed source
freeze, run immutable REANA format/Clippy/build preflight, including the
registered workspace checks and both gravity test targets. Proposed build
resources are 1 CPU/4 GiB/900 seconds, with one Cargo job and one thread.
These are unmeasured requests, not image/toolchain/memory/timing observations.
Formatter/compiler/lint findings must be repaired and the changed source
refrozen before numerical evidence is credited; none has run here.

Each ready written method then gets its own workflow, 1 CPU/1 GiB, one Rust
test thread, 180-second declared runtime. Use the committed per-target binary
from that preflight or the exact equivalent Cargo selector, for example:

```text
cargo test -p gravity --test reference eps4_axis_force_potential_energy_and_acceleration -- --exact --test-threads=1
cargo test -p gravity --lib direct::tests::cache_g_guard_isolated -- --exact --test-threads=1
```

These commands are intended future invocations, not an execution record.
Resolve/discover the actual compiled Rust selectors before release, compare
them with the lexical inventory, and reject missing/extra/ambiguous selectors.
Retain source/dependency/toolchain/image/resources, exact command and selector,
input/model/unit/cache identities, UTC/runtime/exit/status, stdout/stderr,
actual test count and outputs. Do not infer a pass from a workflow label or
submission. Each independent high-precision/gradient/orbit/refinement case
also has its own workflow with explicit resources and required dependencies.
Submit ready independent cases concurrently without an aggregate cap;
do not start a dependent long campaign while a prerequisite gate fails.

No local cargo/rustc/rustfmt, build, test, reference arithmetic, numerical
probe or evolution was invoked, and no workflow was submitted by this author.
Only document/source reads, manual mathematical reasoning, lexical test
enumeration, JSON/hash/path/whitespace inspections and manual TOML/dependency
inspection were performed. A source-receipt attempt importing `tomllib`
failed because the host's default Python lacks it, before any receipt or
checks ran; direct manifest reading and literal dependency-line checks were
used instead. This was a source-inspection failure, not a numerical test.
One earlier patch tool response and a later batched context read were
truncated; no hidden output was credited. The affected written files and
the relevant context were subsequently read directly; NUMERICS was reread
in full. All recorded nonzero inspections/corrections, if any, belong in the
delivery receipt rather than being described as test results. A documentation
patch with a nonexistent context line was rejected without changing any file;
the corrected patch targeted this actual inspection paragraph.

Gravity numerical acceptance, gas centroid/work/birth-representation ledgers,
tree comparisons, equilibrium ICs and live stability, bounded and deforming
3D nonzero-MHD coupling, ISM/feedback and the full merger remain open. This
code is a reviewable first implementation, not a substitute deliverable for
that goal or a claim of AREPO/paper-level equivalence.
