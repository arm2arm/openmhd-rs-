# Collisionless particles, isolated gravity and galaxy initial conditions

Design contract, 2026-11-22; **proposed, not implemented or numerically
validated**. This document owns the G1/G2/G4 gravity and initial-condition
interfaces in [the galaxy plan](../GALAXY_MERGER_PLAN.md). It changes no M1
source, default, benchmark, threshold or acceptance evidence. The frozen M1
source is `2bdcea0d28340e7429e10053a641f92d51fcc696`; historical campaigns and
the conditional source review pass, while fresh physical acceptance and its
final output review remain prerequisites. Full 3D moving gas/MHD, and then
coupled new physics, require their own preceding gates. Source/design work
can proceed now; no executable test or evolution was run for this contract.

## 1. Decisions and evidence boundary

The first force/integration reference is single-process, serial `f64`, in
three **physical, non-expanding Cartesian coordinates**, with Newtonian
isolated gravity, fixed Plummer softening, no external potential, synchronized
steps, and immutable particle masses between explicitly logged source events.
Dark matter, existing stars, new stars and gas use the same pair kernel and
gravitational/inertial mass. There is no cosmological scale factor, Hubble
flow, density subtraction, periodic image sum, minimum-image displacement,
TreePM mesh, or background gravitational field in this configuration.

The deliberately simple Plummer kernel makes differentiation and independent
checking easy; this is a reference choice, **not a claim of optimal force
resolution**. Finite-support kernels, adaptive softening, refinement,
individual timesteps, MPI, black holes and cosmology are separately gated.
The first collisionless merger needs no gas mesh. The first gas merger needs
the nonperiodic mesh/boundary path in section 7; existing periodic gas
geometry is not an authorized substitute.

Primary sources and the exact consulted identities are in
[gravity_particles_sources.json](gravity_particles_sources.json). Downloaded
reading material is ignored under `results/galaxy_gravity_design_20261122/`.
Page numbers below are one-based PDF pages, which coincide with the printed
numbers for the cited paper pages. Equations labeled `GP-*` below are this
project's derived/selected contract, not publication equation numbers.

| ID | Full-text source actually consulted | Use and limit |
| --- | --- | --- |
| D01 | [Dehnen, astro-ph/0011568v1](https://arxiv.org/pdf/astro-ph/0011568v1), p. 3 Eq. (3), p. 9 Eqs. (30)-(31), pp. 6-7, 14-16 | Plummer potential, smooth sphere targets, softening bias/noise. The force below is differentiated independently from Eq. (3). |
| S09 | [Springel, 0901.4107v2 PDF](https://arxiv.org/pdf/0901.4107v2), pp. 25-28 Eqs. (74)-(98), pp. 28-30 softening, p. 52 onward collapse | Continuum gravity sources, force/work coupling and actual face-mass transport; not an adoption of its adaptive cell softening or a claim of identical MHD integration. |
| D00 | [Dehnen, astro-ph/0003209v1](https://arxiv.org/pdf/astro-ph/0003209v1), pp. 2-3 Eqs. (2)-(8), section 2.3 | Symmetric opening and mutual tree interactions. Higher multipoles require a later derivation and validation. |
| Y14 | [Yurin & Springel, 1402.1623v2](https://arxiv.org/pdf/1402.1623v2), pp. 3-5 Eqs. (1)-(12), pp. 11-12 Eqs. (47),(50),(51) | Orbit-response equilibrium construction and halo/disk/bulge density families; no external implementation or example parameters are adopted. |
| C22 | [NIST complete 2022 CODATA table](https://physics.nist.gov/cuu/Constants/Table/allascii.txt), named G and permeability entries | Dimensional constants; retrieved through web full text. Direct local downloads returned HTTP 403, so no downloaded-byte hash is asserted. |
| I15/P16 | [IAU B3, 1510.07674v1](https://arxiv.org/pdf/1510.07674v1), p. 3; [Prsa et al., 1605.09788v1](https://arxiv.org/pdf/1605.09788v1), p. 5 Table 1 and p. 8 | Nominal solar GM and exact astronomical length conversions. Nominal GM is not an exact solar mass in kg. |

Two source-transcription cautions must survive implementation review:

* The retrieved S09 PDF is 66 pages and labels the potential-based work
  expression **Eq. (96), p. 28**. The arXiv HTML served for the same v2 URL
  labels it Eq. (113). Use the pinned PDF hash, not an unqualified equation
  number. Our outward-positive mass ledger and derivation below fix signs
  independently of that source's face/displacement convention.
* D01 v1 Eq. (4b) prints a leading minus multiplying the derivative of the
  positive kernel, although Eq. (3) and the stated `F=-grad(Phi)` give the
  attractive sign used here. This is an apparent sign inconsistency in the
  inspected text, not an author-confirmed erratum. Eq. (3), direct
  differentiation and the attractive two-body fixture are the authority for
  our implementation; do not transcribe Eq. (4b) blindly.

No third-party code was copied. Reading a paper/arXiv license does not grant
an MIT-compatible software license. GALIC/GADGET/AREPO source reuse is outside
this contract until a precise revision, file inventory and compatible license
are verified. All algorithms proposed here are to be independently written.

## 2. Units and configuration

`UnitSystem` contains positive finite SI base values `length_m=L0`,
`mass_kg=M0`, `velocity_m_per_s=V0`, the pinned `G_si`, and the magnetic
permeability convention. Derived scales are:

```text
T0 = L0/V0                  rho0 = M0/L0^3
p0 = rho0*V0^2              E0 = M0*V0^2
momentum0 = M0*V0           angular_momentum0 = M0*L0*V0
acceleration0 = V0^2/L0     potential0 = V0^2
G_code = G_si*M0/(L0*V0^2)                                  (GP-1)
B0_T = V0*sqrt(mu0_si*rho0)  A0 = B0_T*L0
```

Divide physical values by these scales on input; multiply on output.
`Phi` is specific potential, `U` pair energy; never interchange them.
The existing MHD convention `mu0_code=1` means magnetic energy density is
`B_code^2/2`, not Gaussian `B^2/(8*pi)` with the same numerical B. Store SI
permeability and any gauss-to-tesla conversion explicitly in a physical run.
The proposed physical profile uses `mu0_si=1.25663706127e-6 N A^-2`
(CODATA 2022, measured) and `1 gauss=1e-4 tesla` on explicit gauss input.
All density thresholds, cooling coefficients and stellar ages cross the ISM
interface through this one unit map. There are **no implicit factors of h,
a, or sqrt(4*pi)**. Do not infer temperature from specific energy without the
ISM worker's molecular-weight/EOS contract.

The one canonical `UnitSystem` remains SI-based. Cooling uses a named cgs
adapter, never a second independently configured base system: SI density
kg/m^3 to g/cm^3 multiplies by `1e-3`, specific energy J/kg to erg/g by
`1e4`, pressure J/m^3 to erg/cm^3 by `10`, and volumetric power W/m^3 to
erg/cm^3/s by `10`; time remains seconds. Round-trip these conversions in
the prospective unit fixtures and keep rate/total/specific quantities typed.

Proposed physical reporting profile: `L0=1 kpc`, `M0=10^10 nominal solar
masses`, `V0=1 km/s`, with
`kpc_m=1000*(648000/pi)*149597870700`,
`G_si=6.67430e-11 m^3 kg^-1 s^-2` (CODATA 2022), and
`M0=10^10*(1.3271244e20 m^3 s^-2)/G_si`. Store the actual f64 scales as well
as these expressions/version tags. The quoted G is measured, not exact; the
IAU nominal solar GM is an exact conversion constant. Fixtures instead use
`G_code=1`; a physical interpretation with `G_code=1` must derive
`V0=sqrt(G_si*M0/L0)`, not impose three inconsistent base scales. Use SI
seconds internally; a reporting year, if offered, is explicitly 365.25 days
of 86400 seconds (chosen Julian-year convention).

Keep three namespaces in every case manifest:

| Namespace | Examples |
| --- | --- |
| Physical model | Component masses/scales/tapers, velocity anisotropy/streaming, gas EOS, metallicities/ages, orbital energy/angular momentum/spins, external pressure and ambient density. |
| Dimensional map | L0/M0/V0, G and permeability provenance, physical/code conversion expressions. |
| Numerical choices | Counts/cell masses, epsilon, centroid monopole approximation, dt/CFL, tree opening, summation policy, seeds/RNG, finite domain and boundary discretization. |

Numerical softening is not disk thickness, a gas pressure floor, a Jeans
length, or a physical force modification calibrated by the source papers.

## 3. Persistent state, identity and API boundary

Proposed Rust declarations below are an API sketch, not a change to Cargo or
an implemented module. Private checked constructors enforce their invariants.
Positions/velocities/momenta and all scientific scalars are `f64`.

```rust
type Vec3 = [f64; 3];
struct EntityId(u128);       // serialized as 32 hex digits, never as JSON f64
struct CellId(EntityId);
struct ParticleId(EntityId);
struct EventId(EntityId);
enum GravityId { Cell(CellId), Particle(ParticleId) }
struct GalaxyTag(u32);       // analysis origin, never selects force physics
struct ComponentTag(u16);    // halo/disk/bulge/ambient/born-star analysis tag
struct SofteningClass(u16);
enum SourceKind { DarkMatter, Star, GasCell }
enum BirthOrigin { InitialPopulation, Gas { parent: CellId, event: EventId } }

struct PhasePoint {
    id: ParticleId,
    x: Vec3,                 // unwrapped physical Cartesian coordinates
    momentum: Vec3,          // primary integrated quantity; v = momentum/mass
    mass: f64,               // current gravitating and inertial mass, > 0
    softening: SofteningClass,
    galaxy: GalaxyTag,
    component: ComponentTag,
}
struct DarkMatterParticle { phase: PhasePoint }
struct StellarPopulation {
    origin: BirthOrigin,
    formation_time: f64,     // population clock; configured epoch or estimate
    activated_at: f64,       // accepted endpoint when force source materializes
    formation_interval: Option<[f64; 2]>, // both endpoints for in-situ births
    birth_mass: f64,         // immutable net locked long-lived mass L, > 0
    gross_formed_mass: Option<f64>,    // F; mandatory for in-situ births
    prompt_returned_mass: Option<f64>,// beta*F; mandatory for in-situ births
    birth_metal_fraction: f64,
    current_metal_mass: f64, // total metals; optional element vector separately
    model_tag: String,       // links to the ISM/return-table provenance
}
struct StarParticle { phase: PhasePoint, population: StellarPopulation }

struct GravitySource {
    id: GravityId, kind: SourceKind,
    mass: f64, x: Vec3, softening: SofteningClass,
}
struct GasGravityView {
    id: CellId, mass: f64, momentum: Vec3,
    volume: f64, volume_centroid: Vec3,
    // copied, immutable force-epoch view; not another owned gas state
}
struct GravityEpoch {
    time: f64, state_revision: u64, source_hash: [u8; 32],
    gas_geometry_epoch: Option<GeometryEpoch>, // Some for any real gas source
}
struct ForceSample { id: GravityId, force: Vec3, specific_potential: f64 }
struct GravityEvaluation {
    epoch: GravityEpoch, samples: Vec<ForceSample>, pair_energy: f64,
    // counters, residual sums, backend/config identity are mandatory metadata
}
trait GravityBackend {
    fn evaluate(&mut self, epoch: GravityEpoch, sources: &[GravitySource])
        -> Result<GravityEvaluation, GravityError>;
}
```

Force is the primary gravity output; acceleration is derived as `F/m`.
`gas_geometry_epoch` pins the immutable geometry used for every gas centroid
and volume; it is `None` only for a collisionless-only source catalog. Reject
a mismatched epoch even if the sorted source hash happens to agree. A gas
mass/source transaction still changes `state_revision` and the source hash
without necessarily changing geometry. This refines the sketch to match the
[shared integration contract](INTEGRATION_CONTRACT.md#identity-and-immutable-views).
`velocity` is computed, not a second mutable copy. Stars use current mass in
the force and kinetic energy, never gross formed mass. Initial populations
require an explicitly configured formation epoch and locked birth mass;
set `activated_at=t_start` and leave the in-situ formation interval/gross/
prompt-return metadata absent rather than inventing an observational age.
Age is `t-formation_time`, not a cosmological scale factor or activation age.
All returns are disabled in G1/G2, and delayed return remains disabled in
the first ISM-coupled profile. In future delayed-return extensions, current
mass can decrease only through an
atomic source event; require `0 < current_mass <= birth_mass` in this
no-accretion model. Require finite
`0 <= metal_mass <= current_mass`, `0 <= birth_metal_fraction <= 1`, and
`formation_time <= t` and `activated_at <= t` for active particles to
roundoff; element masses cannot sum above total mass.
Zero-mass tracers, negative masses, duplicate IDs and nonfinite values are
rejected, not silently skipped. A retired zero-mass object is removed only
by an explicit event retaining its tombstone/lineage.

ID rule: high 64 bits are an immutable dataset namespace assigned in the IC
manifest, low 64 bits a monotonically allocated entity counter. The serial
allocator is checkpointed, checked for overflow and never reuses a counter.
Gas cells and particles share it; IDs survive reordering, mesh rebuild and
restart. Source conversion creates/retires typed entities through explicit
events rather than reinterpreting a cell payload as a particle. Combining
galaxies must allocate disjoint
namespaces or remap IDs once with a saved bijection. Events have a separate
ID namespace. `CellId`, `ParticleId` and `EventId` are distinct wrappers over
this same payload; `u32` indices are storage/epoch-local only. Wrapper types
do not permit reusing a persistent payload or changing its meaning. A new
star receives a new ID and a parent/event link; a gas
cell does not change its ID because it loses mass. Future splitting/merging
requires an explicit lineage extension; future MPI ID allocation is gated.

Gas exports exactly one active source per real cell at the **geometric volume
centroid**, with its entire conserved gas mass, including every cold/hot
subphase and metals already contained in that mass. This is a piecewise
constant cell-monopole approximation; it is not an exact polyhedron field
or the first moment of an arbitrary reconstructed density. Mesh generators,
Riemann ghosts, periodic images, and phase fractions are never additional
mass sources. Force acts on that same cell's conserved momentum. Changing
the gravity position to a generator or reconstructed mass centroid is a
new discretization needing matched energy/torque tests.

Build a sorted immutable source array at each force epoch. Evaluation is
pure with respect to physics state; results carry IDs and are applied by
checked ID lookup, not storage index. Source counts, total masses by species,
softening table, epoch and source-array hash must match. Any mass, position,
softening or active-set change invalidates a cached evaluation. Diagnostics
on a selected component do not restrict its forces to that component.
Validate `GravityId::Cell` only with `SourceKind::GasCell` and particle IDs
only with their collisionless kinds. A particle with `activated_at>epoch.time`
is not an active source; do not backdate it for a cached previous force epoch.

## 4. Fixed symmetric gravity and the direct oracle

For source positions `x_i`, define `d_ij=x_j-x_i`, `r^2=d dot d`. The first
configuration gives **all species one common, positive, immutable epsilon**.
The table/API may later support fixed species classes with
`epsilon_ij^2=(epsilon_i^2+epsilon_j^2)/2`; this RMS rule is our engineering
choice, not the adaptive S09 scheme. Fixed unequal-class kernels must first
pass all mixed-species/energy tests. A table is never recomputed from gas
volume or changed at stellar birth without a recorded potential jump.

```text
s_ij = sqrt(r_ij^2 + epsilon_ij^2)
psi_ij = -G/s_ij
U_ij = m_i*m_j*psi_ij
F_i<-j = +G*m_i*m_j*d_ij/s_ij^3
F_j<-i = -F_i<-j
Phi_i = sum_(j != i) m_j*psi_ij
U = sum_(i<j) U_ij = (1/2) sum_i m_i*Phi_i                 (GP-2)
F_i = -partial U/partial x_i, holding masses/epsilon fixed.
```

There is no self force and **no diagonal self energy** in GP-2. Distinct IDs
at identical positions are valid: force zero, finite negative pair energy;
they must not be mistaken for a self interaction. Newtonian `epsilon=0`
is not a production mode. Reference comparisons to unsoftened dynamics are
resolution/softening comparisons, not a change to the active kernel.

Equal/opposite accumulation means compute a pair force once, add that vector
to `F[i]` and its negation to `F[j]`. It does **not** mean add equal/opposite
accelerations when masses differ. Central pair forces also give zero pair
torque about any origin in exact arithmetic. Summation roundoff remains.

The first serial oracle is deliberately independent of geometry and tree:

```text
validate and sort unique IDs; clear F, Phi, U
for i = 0 .. n:
    for j = i+1 .. n:
        d = x[j]-x[i]                       # ordinary isolated displacement
        s = sqrt(dot(d,d)+epsilon_pair^2)
        f = G*m[i]*m[j]*d/s^3
        F[i] += f; F[j] -= f
        Phi[i] -= G*m[j]/s; Phi[j] -= G*m[i]/s
        U -= G*m[i]*m[j]/s
return samples keyed by original ID, pair U and interaction counters
```

Use deterministic compensated component sums and one pair order. Do not
parallelize the reference reduction initially. Avoid mutable global scratch,
random perturbations and a tree built secretly inside the direct backend.
Scale/overflow checks reject nonrepresentable coordinates or intermediate
energies; a `Result` failure is not a zero force. An independent REANA
reference will evaluate GP-2 with high-precision arithmetic and a different
loop/layout, without importing the production kernel.

An exact first fixture is `G=1`, `m=(2,3)`, `x=((0,0,0),(3,0,0))`, common
`epsilon=4`. It gives `s=5`, `U=-6/5`,
`Phi=(-3/5,-2/5)`, `F_0=(18/125,0,0)`, `F_1=-F_0`, and
`a_0=(9/125,0,0)`. These fractions are derived from GP-2, not executed data.
The potential finite-difference gate must vary positions at fixed epsilon.

For a fixed-mass circular softened binary with separation `d`, total mass
`M`, and COM at rest:

```text
omega^2 = G*M/(d^2+epsilon^2)^(3/2)
v_rel = omega*d; period = 2*pi/omega                       (GP-3)
```

Place the two bodies at `(-m2*d/M,0,0)` and `(m1*d/M,0,0)`, and assign
opposite COM-weighted tangential velocities. Do not compare a softened
eccentric orbit to a closed Kepler ellipse: softening causes real precession.

## 5. Tree path and the limits of its conservation claims

Keep `DirectPairs` permanently available. The first accelerated candidate is
a **mutual monopole dual-tree** with a single softening class, deterministic
octree construction, bucket leaves (including coincident coordinates), and
rebuild at each force epoch. Store mass, COM, member count/IDs, bounding
radius and child IDs. Never accept a node containing the same source in
both sides of an interaction. Partition `(root,root)` recursively into
disjoint unordered node pairs; within a leaf use each exact pair once.

Proposed symmetric opening is D00 Eq. (2): accept disjoint A/B only when
`|R_B-R_A| > (radius_A+radius_B)/theta`; otherwise open a nonleaf (largest
radius, deterministic tie-break). Initial comparison ladder is
`theta=0.7,0.5,0.3,0.15`, leaf capacity 16, all declared numerical parameters.
Force full opening in the reference-limit mode. A finite root box encloses
all sources but imposes no physical boundary and never wraps particles.

For an accepted mutual monopole pair, compute GP-2 with `M_A,M_B,R_A,R_B`.
Distribute `delta F_i=(m_i/M_A)*F_AB` to members of A, and
`delta F_j=-(m_j/M_B)*F_AB` to B. For gas mass changes, the matching potential
must be the **mass derivative of this approximate pair energy**, including
the mass dependence of the node COMs. With `a_A=F_AB/M_A` and
`a_B=-F_AB/M_B`, the contributions are
`Phi_i=-G*M_B/s_AB-a_A dot (x_i-R_A)` and
`Phi_j=-G*M_A/s_AB-a_B dot (x_j-R_B)`. Their mass-weighted sum gives twice
the accepted pair energy; a constant potential per node would omit the COM
derivative and break the gas-work identity. Propagate uniform accelerations
and this linear potential down the tree;
do not loop over every member at every accepted pair. This defines the
derivative of `-G*M_A*M_B/s_AB` for a **fixed partition**, and yields opposite
aggregate forces and central COM torque. Exact arithmetic symmetry does not
promise floating-point roundoff identity or exact energy conservation when
tree membership/opening changes. Log partition changes and compare energies
to direct samples. Higher multipoles are not authorized merely by adding
quadrupole fields: derive matching forces, potentials and torque first.
Output `U_backend` at every diagnostic time and a full direct GP-2 energy
`U_direct_audit` at preregistered audit snapshots for the first accepted tree
cases. These are distinct diagnostics; an estimated/subsampled energy must
be labeled with its sampling error and cannot replace a promised full audit.

An ordinary one-sided Barnes-Hut walk may be built as a separately labeled
force-accuracy comparator. It does not share the mutual-pair momentum/torque
argument and is not an exact Hamiltonian gradient for arbitrary independent
opening decisions. No COM recentering, mean-force subtraction or energy
rescaling may conceal its residuals. It cannot pass as the conservative
backend solely because pointwise force error is small. Mixed softening
classes require homogeneous-class nodes or explicit class-pair moments;
using an averaged epsilon in a heterogeneous node is not GP-2.

## 6. Synchronized integration and gravitational work

### 6.1 Collisionless kick/drift/kick

With constant masses and fixed epsilon, use canonical `p=m*v`:

```text
evaluate F^n from all sources at t_n
p_half = p_n + (dt/2)*F^n
x_new  = x_n + dt*p_half/m
evaluate F^(n+1) at x_new
p_new  = p_half + (dt/2)*F^(n+1)                            (GP-4)
```

Synchronized snapshots store full-step momenta/time, not a mixture of drift
and half-step velocities. For fixed dt and exact forces this is the
Hamiltonian splitting of `H=sum(p^2/2m)+U`; it is time reversible, symplectic
and second order. It does not conserve H exactly. Variable step selection,
gas sources, changing tree partitions and mass events weaken these claims.
Time reversal tests use a fixed predetermined step list. No local clocks or
block-step prediction is included.

First use a fixed global `dt_max` chosen by the registered timestep ladder.
A conservative initial gravity ceiling is
`dt <= 0.05*sqrt(epsilon_min^3/(G*M_total))`, combined with hydro/MHD CFL,
output landing and source stability ceilings as applicable. This uses total
mass as an intentionally pessimistic frequency bound, not an optimal galaxy
production setting. Improving that criterion requires force/orbit evidence;
never quietly enlarge dt because a run is expensive. Every body/cell takes
the same accepted dt. Record all accepted dt values, rejection reasons and
force epochs; reject/retry from immutable old state, including RNG and IDs.

### 6.2 Gas coupling contract and a checkable work identity

The continuum added gas sources are `rho*a` in momentum and `rho*v dot a`
in total gas energy, with `a=-grad(Phi)` (S09 Eq. (74), p. 25). Conserved gas
energy continues to mean thermal + kinetic + magnetic energy, **excluding
potential energy**. Adding `rho*Phi/2` to the Riemann energy and then adding
the work below would count gravity twice. Vector potential and B receive no
direct Newtonian gravity source; indirect changes come through gas motion.

Define `q_ij=-q_ji` as the **mass rate leaving i for j**, one value for each
real shared face, including its actual area/moving-face Riemann solve, and
`Delta m_ij=integral q_ij dt`. With no births/returns or open boundary flux,
`dot m_i=-sum_j q_ij`. Let `c_i(t)` be the selected gravity centroid and
`w_c,i=dot c_i`, not mesh-generator velocity. Direct differentiation of
GP-2 gives, also in mixed gas/particle systems,

```text
dot U = -sum_all_sources F_i dot dot x_i + sum_gas Phi_i*dot m_i
      = -sum_all_sources F_i dot dot x_i
        -sum_unordered_gas_faces q_ij*(Phi_i-Phi_j).

dot E_grav,gas,i = F_i dot w_c,i
                + (1/2)*sum_j q_ij*(Phi_i-Phi_j).           (GP-5)
```

Particles receive the usual force work. Both cells receive the **same sign**
face work: reversing the face changes both q and the potential difference.
For gas moved from a shallower to a deeper potential, total face work is
positive. The sum of GP-5 and particle work cancels `dot U` for the defined
cell-monopole energy. This is the local, first-order consistency identity;
it is not exact finite-dt conservation. S09 section 5.4 motivates using
actual transported mass rather than only cell-centered `m*v`; the sign here
is fixed by our stated outward q and by differentiation of our U.

External-potential tests are explicitly source-only controls: add
`U_external=sum_i m_i*Phi_external(x_i)` without a factor of one half, and
record the external force/work/torque. They do not have the closed-system
COM/momentum invariance of isolated self gravity.

The first coupling slice uses synchronized gravity half kicks around the
already validated homogeneous **3D moving-mesh** gas step:

1. Save the full old state, masses/centroids/potentials/forces. Half-kick gas
   and particles. For each gas kick add the exact fixed-mass kinetic change
   `Delta K = (|p+Delta p|^2-|p|^2)/(2*m)` to gas E, preserving thermal and
   magnetic energy during that kick.
2. Drift particles; advance the homogeneous gas/MHD+geometry for the same dt
   using its time-centered velocities. Export every integrated signed face
   mass exchange and the actual old/new volume centroids. No star events,
   refinement or floor/reset is allowed inside this trial.
3. Rebuild sources from the new gas masses/centroids and particle positions;
   evaluate endpoint gravity and perform the second half kicks. Endpoint
   potentials must use all species, the same epsilon and the same U rule.
4. For each gas cell set its total gravitational energy increment to
   `W_path,i = 0.5*(F_i^n+F_i^end) dot (c_i^end-c_i^n)
   + 0.5*sum_j Delta m_ij*(Phi_bar_i-Phi_bar_j)`, where
   `Phi_bar=(Phi^n+Phi^end)/2`. The two half kicks have already added
   `W_kick,i`; therefore add **only** `W_path,i-W_kick,i` at this step.
   Record both, the signed correction and its effect on thermal energy.
5. Recover pressure/thermal state with the existing magnetic curl/energy
   convention; any invalid state rejects the whole trial. Do not impose a
   positive thermal floor or distribute the global energy residual to cells.

This trapezoidal mass/path work is a **proposed engineering coupling**, not
a demonstrated second-order scheme or the literal S09 integrator. It needs
the fixed/moving hydrostatic, face-transfer and collapse gates below. The
centroid path, cell-monopole spatial error and hydro splitting can dominate
its thermal accuracy even when total energy looks good. Compare an
independently implemented time-centered unsplit source treatment if it fails;
do not relax the physical gates. A cell generator following the fluid is not
proof that `w_c=v` or that face mass flux vanishes.

## 7. Gas mesh, ambient material and physical boundaries

Choose a finite **nonperiodic clipped Voronoi box**, stationary outer box
planes, with moving interior generators and a volume-filling positive-density
ambient gas. Start gas gravity with B=0 and ideal adiabatic gas; add the
validated ISM closure and nonzero magnetic field in separate comparisons.
Every ambient cell gravitates; uniform density is not subtracted. Ambient
mass/metals/thermal energy and accretion onto the galaxy are separately
tagged in diagnostics. Collisionless particles remain unbounded and continue
to gravitate after crossing the gas box; their positions are never wrapped
or deleted at a hydro boundary.

**Coordinator reconciliation, 2026-11-22:** the first coupled bounded profile
is [box-conducting-slip-relative-v1](BOUNDARY_MHD_SPEC.md), as recorded in the
[shared contract](INTEGRATION_CONTRACT.md#mesh-motion-and-physical-boundary-gate).
It has impermeable conducting slip walls, zero normal magnetic flux and no
independently imposed mean field. Gas/phase/metals do not escape; ambient gas
remains a live source. Collisionless particles remain unbounded. Accumulate
the wall's signed impulse, torque and lab-frame work, and show raw and
ledger-adjusted budgets. Zero mass loss or stationary-wall work is not
evidence of negligible boundary influence: retain the domain/ambient controls
below and their central-profile gate. Discrete boundary acceptance remains
M2d work, including independent review; this choice is not numerical evidence.

The original hydro proposal below is retained only for a **deferred separate
outflow profile**, not the first magnetized merger. It is transmissive,
no-inflow outflow: reconstruct
the interior thermodynamic state into an exterior ghost, allow outward
normal flux, and suppress inflow. Exact Riemann/ghost implementation and
magnetic/gauge boundary conditions require the geometry/MHD worker's own
nonperiodic contract before a magnetized run. Ghosts are not gravity sources.
This boundary is not guaranteed nonreflecting or hydrostatic; test it. Gas
that leaves is removed only through recorded mass/momentum/thermal/kinetic/
magnetic fluxes. Record the accompanying change in GP-2 from removed mass
as a **boundary potential-energy term** using before/after source states;
do not assert an isolated energy budget that ignores it or count it both as
face work and removal. Accepted comparisons of that deferred outflow profile
require boundary losses below `10^-6` of system mass and `10^-4` of binding
energy; larger losses demand a larger domain and a reviewed open-boundary
energy flux treatment.

Initial gas construction: sample the desired mass distribution plus a coarse
volume-filling ambient lattice; relax **generator geometry only** with a
fixed prescribed density, then integrate density/energy into final cells.
Do not call dissipative gas relaxation an equilibrium proof. Hold the
galaxy profiles fixed when comparing domains. Initial proposed merger box
side is `L=128 R_d`, centered on the pair COM, with `L=256,384 R_d` controls.
Those are numerical choices, not source-paper values. All collisionless
halo particles are included even outside this box. Set a common ambient
density low enough that its total mass in the **largest** comparison box is
at most `10^-4 M_pair`; reuse that density in all boxes. Set and record
ambient pressure/temperature from the gas EOS, match the tapered disk edge
smoothly, and compare density and pressure independently by factors 0.1/10.
There is no instantaneous vacuum or zero-pressure floor replacement.

If only periodic 3D gas geometry is available, continue collisionless work
and isolated small force fixtures; **gas merger coupling remains gated**.
A large periodic gas box with isolated forces would be a separately named
finite-time approximation needing seam/signal/domain evidence; it is not
this baseline and particles/gas cannot silently use different image choices.

## 8. Source transactions for star formation and recycling

The ISM worker chooses the physical source equations, IMF, yields, return
fractions and any stochastic spawning distribution. Gravity supplies this
boundary, without prescribing those equations:

```rust
struct StarBirthRequest {
    event: EventId, parent_gas: CellId, at_time: f64,
    formation_interval: [f64; 2], formation_time: f64, activated_at: f64,
    birth_mass: f64,         // net locked L after instantaneous recycling
    gross_formed_mass: f64, prompt_returned_mass: f64,
    birth_metal_fraction: f64,
    current_mass: f64, current_metal_mass: f64,
    position: Vec3, momentum: Vec3,
    // ISM model/version, random stream/counter and typed gas source deltas
}
struct SourceLedger {
    event: EventId,
    at_time: f64,
    affected: Vec<GravityId>,
    delta_mass_by_kind: [f64; 3],
    delta_metal_mass_by_kind: [f64; 3],
    delta_momentum_by_kind: [Vec3; 3],
    delta_angular_momentum_by_kind: [Vec3; 3], // same fixed origin per event
    delta_gas_energy: f64,
    delta_particle_kinetic: f64,
    delta_gravity: f64,                     // actual before/after GP-2
    delta_gravity_representation: f64,      // identified part of delta_gravity
    feedback_to_resolved: f64,
    radiation_to_resolved: f64,
    unresolved_reservoir_to_resolved: f64,
    boundary_to_resolved: f64,
    // All channel energies are signed, positive toward resolved H.
    // Also retain before/after state hashes, model identity and RNG counter.
}
```

Commit the source transaction and materialize a birth only at an accepted
full-step endpoint: `at_time=activated_at=t_end`, `current_mass=birth_mass=L`.
In the first source profile `L=F-prompt_returned_mass=(1-beta)*F` is the
net locked long-lived mass **after instantaneous recycling**; retain both
`gross_formed_mass=F` and `prompt_returned_mass=beta*F` in birth metadata.
Only L is a new collisionless gravity source. Prompt-returned mass remains
in the gas source transaction, so do not remove F from gas and leave only L
in the particle without crediting the return in that same atomic ledger.
The particle's initial metal mass is `L*birth_metal_fraction` to roundoff.

Retain each packet's actual source subinterval
`formation_interval=[source_begin,source_end]`. A configured first profile may
set `formation_time=(source_begin+source_end)/2` as an explicitly **first-order
population-age estimate**, separately from `activated_at=t_end`; record that
estimator in provenance. Validate finite ordered interval endpoints and
`source_begin <= formation_time <= source_end <= activated_at=t_end`.
The final inequality may be strict for source subcycling: each successful
subinterval retains its packet, and all packets commit at the accepted
global endpoint. This coordinator reconciliation preserves the ISM reference's
per-interval policy rather than silently aggregating packets. The joint
transaction includes interactions between all newly materialized packets
in its before/after GP-2 ledger; rejection consumes no IDs or ledger entries.
Such a packet has a
nonzero estimated population age at activation and must not be called
universally zero age. It participates only in the next force evaluation,
with **no previous fractional kick or drift**. Dynamical midstep activation/
subcycling needs a separate convergence contract. Delayed mass return is
disabled, so this metadata does not choose a delayed-return age algorithm.
Initial old populations may have a configured `formation_time<0`.

For the first interface fixture, create at parent centroid with parent
`v=p/m`; remove exactly net `delta m=L`, `L*v` and the declared locked metal mass
from the gas. This gives exact total linear momentum and centroid-based
angular momentum in exact arithmetic. Random launch velocities, displaced
birth sites, or kicks require explicit opposite impulses and angular-momentum
ledgers. Existing and newly formed stars then share GP-2/GP-4 unchanged.

The ISM event must provide the gas energy delta, identifying removed bulk
kinetic energy, carried/converted thermal energy, radiation and feedback.
A collisionless star does not automatically carry a gas thermal/magnetic
reservoir. Initially A and magnetic flux remain with the gas; copying a
fraction of `E_gas` blindly to a star removes magnetic energy without an
induction event. Effective-EOS feedback cannot be injected again as a second
resolved energy copy. Reject insufficient parent mass/metals/thermal energy,
duplicate events or unresolved reservoirs; commit all deltas or none.

**Important representation effect:** GP-2 excludes self energy. Splitting
one co-located source `m` into parent `m-dm` plus star `dm` with identical
epsilon leaves all external interactions unchanged, but creates the new
pair energy `-G*(m-dm)*dm/epsilon`. Thus births can change U even without
physical motion. Record the exact `Delta U_representation` separately from
physical cooling/heating; never subtract it from gas thermal energy merely
to force a conserved total. Different softening or birth position adds more
external-interaction changes. A merger with source events is not accepted
until the cumulative magnitude is below `10^-4` of initial binding energy
and converges with particle/cell mass; otherwise revise and review the
source/self-energy discretization (e.g. a consistent finite-cell/self-energy
model) before enabling it. This is an explicit G3 coupling issue, not
permission to hide a numerical energy jump in the radiation ledger.

The event check is `delta_gas_energy+delta_particle_kinetic+delta_gravity
-delta_gravity_representation = feedback_to_resolved+radiation_to_resolved
+unresolved_reservoir_to_resolved+boundary_to_resolved`, up to the stated
numeric residual. State deltas and carried thermal energy are not additional
external sources. The representation term is already part of delta_gravity,
so subtract it once for this explanatory residual while retaining raw H.

Prompt recycling is accounted within the same finite-interval ISM
transaction; it is not a newly materialized star receiving a retroactive
return. Future **delayed** returns use a separately gated reverse transaction
with stable stellar birth metadata,
current-mass reduction, declared recipient gas cells and conservative
momentum/metals/energy distribution. Specify transported angular momentum,
yield-created metals, nuclear/feedback energy sources and potential changes.
Gas-to-star and star-to-gas transfers must not create duplicate gravity
sources or leave retired zero-mass entries. Checkpoints save pending/committed
event IDs, allocator, RNG counters, all ledgers and source-model identity.

## 9. Diagnostics and accounting, before any merger claim

For all active sources, and separately per species/galaxy/ambient tag, write:

```text
M = sum m_i; P = sum p_i; X_cm = sum(m_i*x_i)/M
L_cm = sum (x_i-X_cm) cross (p_i-m_i*P/M)
K_particles = sum_particles |p_i|^2/(2*m_i)
K_gas = sum_cells |p_i|^2/(2*m_i)
E_B = sum_cells V_i*|B_i|^2/2
E_th = sum_cells E_gas,i - K_gas - E_B
H = K_particles + sum_cells E_gas,i + U                  (GP-6)
W_virial = sum_i (x_i-X_cm) dot F_i
```

Use `2K+W_virial` for the collisionless virial residual, **not `2K+U`**:
softened gravity is not a homogeneous inverse-distance potential. For gas,
report pressure/magnetic/ambient surface terms as well; do not apply the
collisionless virial condition to an open MHD system. Gas `c cross p` is a
cell-monopole angular-momentum diagnostic; no exact subcell orbital angular
momentum is evolved. Hydro discretization/centroid motion may introduce
torques even though the gravity pairs are central. Track hydro, gravity,
boundaries and source-event torque increments separately.

Use fixed nonzero initial scales: `E_scale=K0+E_th0+E_B0+|U0|`,
`P_scale=M0*v_ref`, `L_scale=M0*R_ref*v_ref`, fixed declared R/v references,
and `F_scale=G*M0^2/R_ref^2`. Never normalize by zero net P/L/H or tune scales
after a failure. Log both absolute and normalized residuals, COM trajectory
against `X_cm(0)+P0*t/M0`, net force/torque, minima of gas density/pressure,
and source/work counters. Treat escaped collisionless material as part of
the total system, even when a bound-remnant catalogue excludes it.

Report raw `H(t)-H(0)` **and** its ledger residual after signed physical
sources/boundaries and separately identified representation changes. Record
radiation loss, external work, feedback/nuclear injection, thermal reservoirs,
and mass-return terms explicitly; internal mass exchanges cancel in total M/P.
No energy/COM/angular-momentum correction is permitted to manufacture a pass.
Force error, tree approximation, timestep error, softening bias, sampling/
relaxation, gas monopole resolution, ambient/domain effects, and source
representation jumps are different error budgets and need separate controls.

Retain the 3D MHD worker's **two explicitly different** magnetic divergence
operators, magnetic energy, A/cleaning residuals and mesh/stencil counters.
Gravity does not establish `div(curl A)=0` for an independent operator.
Snapshots include full-step momenta, epoch, units, softening and source tables,
IC/config hashes, seed/RNG/version, compiler/binary/source identities, actual
resources, dt history, force/backend counters and restart/event state.

## 10. Equilibrium initial conditions and staged merger

### 10.1 Chosen equilibrium method

Recommend an independently implemented **orbit-response velocity optimization**
following Y14's density and velocity-moment merit functions, with all
components in the same potential. Positions sample normalized target
densities; velocities are iteratively adjusted against orbit-averaged density
and prescribed dispersions/streaming. A Jeans/Gaussian velocity assignment
is only an initial proposal, not proof of equilibrium. Implement orbital
integration, target quadrature, merit bins, normalization and deterministic
sampling separately from the evolution force backend. Use the **same softened
kernel** for the equilibrium target; an unsoftened analytic DF generally
does not equilibrate a softened realization. Y14's exact optimization and
Jeans closure are source methods, while using our softened target/tapers is
an engineering adaptation requiring its own source-to-code review.

Density families, from Y14 Eqs. (47),(50),(51):

```text
rho_h(r) = M_h*a/[2*pi*r*(r+a)^3]
rho_b(r) = M_b*b/[2*pi*r*(r+b)^3]
rho_d(R,z) = M_d*exp(-R/R_d)*sech^2(z/z_d)/(4*pi*R_d^2*z_d). (GP-7)
```

The vertical argument is `z/z_d`; Y14 explicitly notes a factor-of-two typo
in an older paper. Here M parameters denote **post-taper masses**, so apply
the taper and renormalize instead of treating the unmodified formula as
already normalized. Proposed C2 outer taper: 1 through `r_t` (or disk R_t),
`1-10s^3+15s^4-6s^5` for `s=(r-r_t)/(r_out-r_t)` in (0,1), zero beyond.
Truncation changes the DF: solve equilibrium after tapering; do not just
delete high-radius/high-energy particles from a previously sampled DF.
No NFW concentration/virial relation is required for this isolated baseline.

First self-gravitating equilibrium fixture: a Plummer density target
`rho=3*M*a^2/[4*pi*(r^2+a^2)^(5/2)]` (D01 Eq. (30)), with a declared outer
taper, `G=M=a=1`, common epsilon ladder. Compute the continuum **softened**
target potential by independent radial/angular quadrature of GP-2 and build
an isotropic DF by an independently reviewed Eddington inversion or the
orbit-response optimizer. Neither the unsoftened Plummer potential nor its
analytic DF is an exact softened equilibrium. Check DF positivity, force/
potential quadrature convergence and distribution moments before evolution.
The Eddington option has no transcribed primary formula in this packet and
requires a source map before implementation; the sourced orbit-response
optimizer is the first recommendation.

For disk/bulge/halo galaxies, iterate the combined softened target potential,
orbit response and chosen anisotropy/streaming constraints to convergence.
Use phase-space symmetries/paired samples only with explicit weights and
stored seed/algorithm; never rescale velocities globally at each evolved
output to hold equilibrium. Optimization stopping is a numeric convergence
test, followed by an independent live evolution with optimization disabled.

### 10.2 Concrete first collisionless fixture

These **proposed project fixture values** are not paper values, an observed
galaxy fit, or a Milky Way model:

| Quantity per galaxy | Proposed value in `G=1, R_d=1, M_gal=1` units |
| --- | --- |
| Halo / stellar disk / stellar bulge masses | 0.85 / 0.12 / 0.03 |
| Halo a / bulge b / disk z_d | 10 / 0.2 / 0.2 |
| Spherical taper interval | 100 to 200 R_d |
| Disk radial taper interval | 8 to 10 R_d; vertical support chosen by normalized density quadrature, not a hard z cut |
| Counts at base resolution | Halo 8192, disk 4096, bulge 1024; also 2x and 4x each |
| Common fixed epsilon | 0.05 R_d; independent 0.025 and 0.1 controls |
| Streams / seeds | Named pinned RNG algorithm/version and separate component streams; proposed integer seeds 1101,1102,1103 (algorithm still to be selected before IC generation) |
| Velocity constraints | Nonrotating halo/bulge with Jeans-consistent axisymmetric dispersions; rotating stellar disk with declared radial/vertical dispersion and streaming profiles |

An exactly spherical density with a fully isotropic velocity tensor is not
generally consistent with a flattened disk potential. Isotropy is reserved
for the spherical single-component fixture; compound galaxies must solve
consistent moment/DF constraints and check positivity.

The numerical dispersion/streaming functions are deliberately **not guessed**
from the density profile. The first IC implementation must choose them from
a positive Jeans/DF solution of the combined target, freeze them in the IC
manifest, and meet the stability gates. This is a remaining physical-model
choice; it cannot be supplied by circular speeds alone. A bar-unstable
physical disk and a bad equilibrium are different findings. First choose a
hot/stable disk; explicitly test radial heating, thickness, m=1/m=2 structure
and seed-to-seed noise rather than assuming stability from optimization.

After isolated relaxation/validation, save the accepted full-step galaxy
snapshots and hashes. If a relaxation stage changes the target significantly,
reject/regenerate; do not relabel the changed galaxy as the specified one.

### 10.3 First reproducible collisionless merger

Duplicate two independently accepted equilibrium galaxies at equal mass,
centers `(-10,0,0)` and `(10,0,0) R_d`, both disk spins initially +z. Assign
disjoint ID namespaces and remove each realization's residual COM position/
velocity once at IC construction, recording the transformation. Proposed
orbit convention is zero initial **orbital** energy measured from the actual
cross-galaxy GP-2 energy `U_cross`, with nominal point-mass pericenter label
`r_p,label=2 R_d`. This label is not the actual pericenter of extended halos.

```text
Mtot=M1+M2; mu=M1*M2/Mtot; d=20*R_d
h=sqrt(2*G*Mtot*r_p,label); v_t=h/d
v_r=-sqrt(-2*U_cross/mu - v_t^2)
v_rel=(v_r,v_t,0)
V1=-(M2/Mtot)*v_rel; V2=(M1/Mtot)*v_rel.                  (GP-8)
```

Reject a negative radicand; do not clip it. Add bulk velocities to every
particle of a galaxy, retaining its internal velocities. Record orbital
E/L and the actual closest approach. This defines a reproducible extended
system IC without falsely calling a point-mass osculating orbit exact.
No gas, ISM, feedback, mass loss or new stars enter this first merger.
Compare a doubled-resolution control, a half-dt control, and accepted-tree
versus tighter-tree settings. Evolve through the encounter and at least five
disk periods after any claimed coalescence. If the run does not coalesce,
report an encounter and extend/review the physical setup; do not infer a
merger from two overlapping density plots.

### 10.4 Gas, then ISM, then magnetic coupling

Next replace `0.02 M_gal` of the stellar disk mass by a gas disk, leaving
stellar disk 0.10 and total M=1, as an explicit new physical configuration.
Propose `R_g=1.5 R_d`, surface density proportional to `exp(-R/R_g)` with
8-to-10 R_g taper and post-taper normalization. Rebuild the equilibrium of
**all** components in the new combined potential; adding gas to a frozen
collisionless equilibrium without adjusting forces/velocities is not valid.

For the unmagnetized gas IC, solve vertical and radial force balance together:

```text
partial_z P = -rho*partial_z Phi
v_phi^2 = R*(partial_R Phi + (partial_R P)/rho).          (GP-9)
```

Solve gas self-gravity iteratively, constrain the integrated surface density,
match the declared ambient pressure, and reject negative `v_phi^2` rather
than taking its absolute value. EOS/entropy profile is a physical input;
it comes from a declared ideal-gas profile for G2 and the ISM contract later.
Initialize conserved integrals by converged cell quadrature. A cell's value
at its generator is not automatically its volume average. Validate the gas
galaxy with cooling/SF/returns off, then enable each ISM channel with the
source-ledger gates and isolated-disk controls. A nonzero magnetic field
adds pressure/tension to GP-9 and must be initialized by a validated 3D A
construction with its own boundary/divergence tests. B=0 stability is not
magnetized-galaxy acceptance.

## 11. Prospective REANA fixtures and pass criteria

Everything in this section is **prospective**. No numerical result, Cargo
test pass, orbit, equilibrium, or merger is claimed. Thresholds are proposed
project choices; freeze concrete fixtures/config hashes and reducer versions
before execution. If a required gate fails, preserve it and stop escalation.
Do not tune thresholds after seeing outcomes. All new executable tests and
evolutions, including kernel/unit tests, run on REANA. One independent case
per workflow, all ready cases submitted concurrently; no aggregate CPU cap.
Preflight/build and scientific dependencies still apply.

Common algebra budget: compare to a separate high-precision reference at
`<=5e-13` relative to a nonzero analytic or summed-magnitude scale for
well-scaled fixtures; report absolute residuals near zero. Use a declared
roundoff bound proportional to accumulated pair magnitudes for larger N,
and reject a result that passes only by an arbitrary floor. Smooth temporal
order fits use at least four dt values, finest-three slope `>=1.8`, with fit
range and uncertainty recorded. Separate fixed-softening time convergence
from softening and sampling bias.

| Gate / cases | Exact prospective design and required comparison | Proposed pass target | CPU / memory per case |
| --- | --- | --- | --- |
| G-PREFLIGHT | New schema/source/kernel tests plus unchanged workspace fmt, all-target/all-feature strict Clippy, debug/release workspace tests, source/reference integrity; immutable binary export | Every applicable command passes; source and binary hashes retained | 24 threads / 32 GiB; builds only here, serial test harness to avoid nested pools |
| G-PAIR | GP-2 rational pair, coincident distinct IDs, extreme mass ratio 1e-6, empty/one-body, invalid states | Rational force/U/Phi within algebra budget; self=0; invalids rejected; paired force/torque residual within roundoff | 1 / 1 GiB |
| G-GRAD | Central finite differences of independently summed U, each coordinate; offsets/epsilon ratios 0,0.01,0.1,1,10,100 | Relative force error <1e-7 on a demonstrated finite-difference plateau; halve difference spacing to show truncation then roundoff; algebraic independent derivative also <5e-13 | 1 / 1 GiB |
| G-SYMMETRY | N=4,32,128 fixed seeded mixed species; translation, 90-degree and general orthogonal rotation, storage permutation, species relabel with same masses/epsilon | Force/potential covariance within 5e-12; net force/torque <5e-13 of summed interaction scales; no force/species branch | 1 / 1 GiB |
| G-KDK | Softened circular binary d=1, m1=1, m2=2, epsilon=0.1; dt=T/{128,256,512,1024}, 100 periods; independent eccentric/plunge integration | Circular phase/position order >=1.8; finest max energy excursion <1e-4 E_scale; COM/P/L <1e-11 of fixed scales; no secular energy trend larger than excursion; reversibility <1e-10 after fixed-list reversal | 1 / 1 GiB |
| G-BOOST/RESTART | Binary and N=128 cluster, fixed dt and joint uniform v boost; restart at accepted full step | Matched deboosted state <1e-10 of fixed scales; serial same-binary restart bit-identical including IDs/epochs/events, or fail with cause | 1 / 1 GiB |
| G-EQUIL-SOURCE | Tapered Plummer G=M=a=1; eps=0.05,0.1; independent quadrature and isotropic DF/response | Potential/force quadrature refinement <1e-6; nonnegative DF; orbit-response density L1 <1%; moments <2% in bins with adequate support | 1 / 2 GiB |
| G-EQUIL-LIVE | Accepted softened sphere; N=256,1024,4096, three seeds; matched dt ladder; direct for small N, validated tree only after its gate | Over 10 crossing times: half-mass radius drift <2%, resolved density/moments <5%, abs(2K+W)/(2K+abs(W))<2% time-mean, energy drift <1e-3; P/L <1e-10; deviations consistent/decreasing with sampling and dt controls | direct 1 / 2 GiB; tree 1 / 4 GiB |
| G-TREE-FORCE | N=128,1024,4096 spheres/disks/two clusters/near-zero-force symmetric points; every theta separately vs direct | At accepted theta: RMS normalized force error <1e-3, p99 <5e-3, max <2e-2; potential error <1e-3; errors decrease toward direct with opening; theta=full-open within algebra budget | 1 / 4 GiB |
| G-TREE-DERIVATIVES | Freeze an accepted node partition, vary leaf positions and masses independently, including node-COM shifts; compare approximate pair energy derivatives | Force and mass-conjugate potential finite differences <1e-7; independent analytic derivatives <5e-13; sum(m*Phi)/2 equals approximate U to algebra budget; sample opening switches separately | 1 / 4 GiB |
| G-TREE-BUDGET | Same ICs and orbit trajectories; explicit mutual and separately labeled one-sided comparator; changing partition/rotation | Mutual net force/torque <1e-11 of fixed interaction scales, COM drift <1e-8 R_ref, orbit energy <1e-3; direct-tightening resolves errors; one-sided residuals reported without symmetry claims | 1 / 4 GiB |
| G-GAS-WORK | Frozen two-cell transfer in static external potential and changing-mass GP-2 fixtures; moving centroids; mixed gas/star source | GP-5 signed first-order residual tends to zero with transfer/time refinement, order >=1.8 for full-step work; thermal uniform-acceleration kick unchanged to roundoff; no duplicate kick energy | 1 / 2 GiB |
| G-HYDROSTATIC | Independent spherical polytropic gas equilibrium integrated with softened gravity, plus external harmonic-potential atmosphere as a source-only control; N_eff=16,32,64, fixed and moving mesh | Density/pressure L1 <1% and Mach <1e-2 after 5 sound-crossing times on finest grid; errors decrease with h and dt; no floors; energy residual <1e-3, net momentum <1e-8 | 2 / 8 GiB |
| G-COLLAPSE | Preregister finite, initially cold adiabatic sphere with explicit smooth core/edge and ambient, G=M=R=1, gamma=5/3, u=0.05; freeze before run; N_eff=16,32,64, eps/R=0.1,0.05,0.025 independently | Compare own independent converged 1D softened radial hydro/Poisson-integral reference: finest binned rho/u/vr scaled L1 <5%, shock radius <2%; total energy residual <5e-3; no negative thermal state; controlled h/dt/eps/domain effects | 2 / 8 GiB |
| G-BIRTH-LEDGER | Finite-interval births with prompt recycling, co-located and displaced/kicked events, restart/failed trial; delayed-return transactions only in their later extension | M/P/metals closure <1e-12, angular momentum <1e-11; raw and adjusted energy explain every term <1e-10 E_scale for algebra fixtures; exact GP-2 representation jump reproduced; F=L+prompt return; activation only at accepted endpoint, interval/age estimate retained, no double source/event or previous kick | 1 / 2 GiB |
| G-GALAXY-ISOLATED | Section 10.2; N,2N,4N; 0.5dt; eps x0.5/x2; minimum 10 periods at 2.2 R_d after preparation | Half-mass radii <2% drift; resolved density/rotation/dispersion/thickness <5%; time-mean virial residual <2%; energy drift <1e-3, COM <1e-6 R_d, P/L <1e-8; no growing m=1 or m=2 amplitude above 0.05 without physical review | 1 / 8 GiB |
| G-GAS-GALAXY | Section 10.4 without ISM, then separate enabled-channel cases; mass resolution ladder, boundary/ambient comparisons, mesh-fixed vs moving control | Gas density/rotation/thickness drift <5% without sources, no-source energy residual <5e-3; within domain/ambient controls central profiles change <1%; all source ledgers pass; boundary limits section 7 | 2 / 16 GiB |
| G-MERGER | Collisionless section 10.3 first; later independently accepted gas and ISM configurations; N/2N, half-dt and tighter-theta controls | Complete configured encounter/coalescence interval; H residual <5e-3, M/P/L ledgers within 1e-8 no-source scales; bound mass/half-mass radius agree <5%, encounter/coalescence timing <10%; source/boundary/representation terms shown separately; independent final review | collisionless 1 / 8 GiB; gas 2 / 16 GiB |

`N_eff` in a gas case is a declared nominal cells-per-radius measure; actual
cell counts/masses/quality are reported. Collapse values are a **new project
fixture**, not an assertion of exact Evrard/S09 initial conditions. Its
independent reference solver is a prerequisite, not an available dataset.
Fix smooth core/edge functions, EOS, analysis bins, final time and reference
convergence before submission; do not compare an arbitrarily softened
collapse to an unsoftened published curve as if they were the same problem.

Tree force normalization is
`e_i=|a_tree-a_direct|/max(|a_direct|, a_floor)` with
`a_floor=1e-3*G*M/R_ref^2` fixed from the fixture; also report absolute errors
and error relative to the sum of pair-acceleration magnitudes so cancellation
is visible. Report errors per species/radius and worst-ID locations. Do not
accept only a global RMS that hides central disk or near-zero-force failures.
The strict force-gradient check applies to direct and to a fixed tree
partition; opening-switch discontinuities are separately sampled, not
mistaken for finite-difference noise.

Analyze isolated profiles outside `max(3*epsilon,2*local_cell_radius)` and in
declared bins with at least 200 effective particles/cells where possible;
report unresolved centers separately. A single seed's noisy bin cannot
establish a 1% physical drift: use paired initial/evolved profiles, three
seeds, sampling uncertainty and increasing support. An underpopulated bin
cannot silently disappear from an acceptance table. Report full profiles
and revise resolution/fixture support *before* the next registered run if
the declared comparison cannot be measured.

Required control matrix separates: (a) dt at fixed N/epsilon/domain;
(b) N at fixed epsilon; (c) epsilon at high N/small dt; (d) domain at fixed
physical profile, ambient density and local resolution; (e) ambient density
and pressure at fixed domain; (f) direct/tree opening; (g) mixed-species
mass ratios and source split scale. A joint N/epsilon change alone cannot
identify an error source. Units are additionally rescaled by independent
L/M/V factors and transformed back to require physical agreement <1e-11 for
kernel fixtures and <1e-8 for orbit trajectories at fixed dimensionless dt.

Each workflow records CPU request/limit equal to declared threads, memory
limit, actual cgroup/CPU availability and pinned image/toolchain. First
reference/tree reductions are serial; gas cases use only their declared
Rayon threads, with internal BLAS/OpenMP threads set to one. The
preflight uses `RUST_TEST_THREADS=1` and an explicit Cargo build-job cap no
larger than its declared CPUs; existing thread-count tests may create their
one declared Rayon pool without concurrent test-harness pools. Proposed case
ceilings: kernel 10 min, orbit 1 h, equilibrium/tree 4 h, gas fixtures 8 h,
galaxy/merger 24 h; calibrate bounded costs before larger cases. A timeout is
an execution failure, never a scientific pass. Resource increases do not
change scientific thresholds. Ready parameter/seed/resolution cases run as
separate concurrent workflows; dependent comparisons wait for prerequisites.
Archive configs, raw snapshots/history, source/binary hashes, independent
reducers, numeric tables, warnings and failures; no service controls or
submissions are part of this design task.

## 12. First implementation slices and remaining decisions

Proposed paths are **future work**, not files created in this task:

1. `crates/gravity/src/{units,state,softening,kernel,direct}.rs`: checked
   types/ID allocator, GP-1/GP-2, deterministic direct evaluator and compact
   diagnostic output. No dependency on the mesh, ISM or MPI. Build the
   independent high-precision REANA fixtures before using its forces.
2. `crates/gravity/src/{kdk,diagnostics}.rs` plus a small collisionless CLI:
   GP-3/GP-4, synchronized restart, pair/orbit/symmetry/unit-rescale gates.
   Keep the current M1 application/source untouched until acceptance.
3. `crates/galaxy-ic/src/{profiles,quadrature,sampling,equilibrium}.rs`:
   softened sphere target, positive equilibrium construction and live drift
   gates, followed by combined halo/disk/bulge optimization. Choose/freeze
   the RNG and actual velocity constraints here.
4. `crates/gravity/src/tree.rs`: mutual monopole candidate with a force/
   potential-consistent fixed-partition path, full-opening parity and direct
   accuracy/budget gates. Higher multipoles/performance follow separately.
5. A new integrator adapter, not a hidden M1 code path: validated 3D gas
   `GasGravityView`, full signed face-mass ledger, GP-5 work, and nonperiodic
   boundaries. Pass hydrostatic/collapse/gas-ledger tests before a gas galaxy.
6. Atomic ISM transactions/lineage, representation-energy review, isolated
   galaxy controls, collisionless merger, then separately accepted gas/ISM/
   magnetic merger. Preserve every configuration's own provenance.

Unresolved choices are bounded rather than paper values invented: exact
disk velocity constraints and seed/RNG implementation; softened/tapered DF
positivity and IC optimizer stopping; the calibrated production timestep
criterion; acceptable finite-cell/self-energy treatment if birth jumps are
not negligible; open-boundary magnetic/gauge closure; collapse reference
implementation; and higher-multipole force/energy continuity. They do not
block implementing the checked particle/direct/KDK reference after its
prerequisite authorization, but they **do** block the corresponding galaxy,
source-enabled or magnetic acceptance. Adaptive softening must derive its
position/volume derivatives from a Hamiltonian; local steps need equal-time
interaction/work bookkeeping; MPI needs global ownership/ID/reduction and
restart equivalence. None is implied by this serial contract.

Only this specification and its source manifest are owned by this work.
Local checks may verify text/JSON/paths/hashes; all executable numerical
validation remains future REANA work. No commits, pushes, workflow controls,
or changes to existing scientific files are included.

Documentation/source integrity actually checked on 2026-11-22: the JSON
parses, all seven source IDs are unique, all six downloaded PDF SHA256 values
match their files, local Markdown links resolve, all GP-1 through GP-9 labels
exist, fences/table columns are consistent, and neither owned file contains
trailing whitespace. Git reports no changes to tracked Rust/Cargo,
benchmarks, scripts, reference evidence or REANA files. These checks are
document/source integrity work, not a numerical validation result; no Cargo
commands or new numerical executable were run.
