# Independent source review of the first direct-gravity/KDK implementation

2026-11-22. Reviewed subject: Git `8fe734268deee3fe5b6a33d868b2bfeaece06a7b`,
all fourteen delivered gravity files. **Conditional support for the small
collisionless implementation and its independent REANA preflight; one known
contract conflict blocks the registered long-orbit campaign. No gravity
numerical gate or component acceptance is granted.** The source is a partial
G1 implementation, as its author states. It is not a runtime-complete G1
reference packet. Findings 1–2 give concrete dispositions; findings 3–8 record
the supported properties and their limits.

I authored the separate shared identity crate and earlier gravity design work,
and independently reviewed static geometry. I did not author this gravity
implementation or its tests. This review checks its use of the frozen identity
interface, not the correctness or acceptance of my identity component. Its
separate review remains authoritative. M1 acceptance at `309ae41` is only the
named periodic, single-process fixed/rigid 2.5D scope. It permits this work; it
does not validate gravity, moving 3D MHD or the merger.

The [source inventory](g1_source_review_sources.json) pins every subject and
context byte, the exact written selectors and the closed reading/check
boundary under `results/galaxy_g1_source_review_20261122/`. Root's delivery
receipt was checked as context, not substituted for reading the implementation.
All ten Rust modules and both test locations were read completely. No target
import/call, compiled test discovery, Rust parser/compiler/formatter/linter,
kernel/reference evaluation, test, build, evolution or workflow was executed.

1. **High — reconcile the unconditional ceiling with the original G-KDK
   ladder before releasing any long-orbit case.** `crates/gravity/src/kdk.rs`
   10–22,89–95; [parent gravity contract](GRAVITY_PARTICLES_SPEC.md) §6.1
   405–413 and §11 G-KDK row 969; [implementation report](G1_IMPLEMENTATION.md)
   195–210,252–259. `try_step` always calls `timestep_ceiling` and rejects a
   larger supplied integration step. There is no calibration policy, substep
   interpretation or alternative public KDK entrypoint. Both the parent and
   implementation report still request **actual** steps
   `T/{128,256,512,1024}` for `d=1,m=(1,2),epsilon=.1` over 100 periods.

   Independent manual substitution of GP-3 gives, for total mass M,

   ```text
   T = 2*pi*(d^2+epsilon^2)^(3/4)/sqrt(G*M),
   h_max = (1/20)*epsilon^(3/2)/sqrt(G*M),
   (T/1024)/h_max = (5*pi/128)*101^(3/4) > 1.
   ```

   No period or force was evaluated. A particularly loose symbolic lower
   bound is already decisive: `pi>3`,
   `101^(3/4)>100^(3/4)=10*sqrt(10)>30`, hence the ratio exceeds `450/128>1`.
   The other three proposed steps are still larger. Ordinary rounding of
   epsilon, initial orbit inputs or period cannot bridge this margin. Thus
   this API cannot run any of the four original levels as declared. Rejection
   is the correct current guard behavior, not evidence against KDK accuracy.

   **Required disposition:** preserve the current production ceiling and mark
   the original four levels as presently infeasible in the implementation/
   campaign documentation. Before those workflows, explicitly reconcile the
   policy and the registered gate. One possible **unadopted** repair is a
   separately named, source-pinned fixed-step calibration entrypoint that can
   exercise the original ladder while the protected production policy remains
   unchanged; its policy/config identity and checkpoint semantics must be
   explicit. Another is a reviewed gate amendment retaining the original
   levels and their rejection observations while registering an additional
   feasible actual-step ladder with the same accuracy/duration requirements.
   Neither alternative is adopted here. Do not silently enlarge production
   dt, delete the original levels, clip them to the ceiling, or rename an
   output interval containing hidden substeps as the original integration h.
   The ceiling's curvature motivation in the existing G1 source review is
   not an error calibration.

   Smallest future controls: one independent, frozen ceiling-versus-registered-
   step predicate/rejection case, retaining the original four inputs and
   unchanged checkpoint after each rejection; then the separately authorized
   actual-step orbit ladder, with independent period/momentum/reference
   rounding. All original order, energy, P/L/COM, reversal and 100-period gates
   remain open. This conflict does not require withholding otherwise eligible
   short algebra/cache/atomicity controls or their build preflight.

2. **Low — state the empty-step policy explicitly and exercise that API
   branch.** `kdk.rs` 11–12,66–69,89–92; `diagnostics.rs` 60–70;
   `tests/reference.rs` 47–58; implementation report 195–200. Empty catalog
   construction, direct evaluation, diagnostics and `KdkSystem::new` are
   supported. Empty COM/internal quantities are absent and the virial reason
   is `EmptyCatalog`. However, every positive empty `try_step` returns
   `EmptyTimestep` through `?`; it does not advance freely without a ceiling.
   The phrase “Empty mass has no such timestep” is ambiguous about this
   distinction. The current fail-closed behavior is defensible and agrees
   with the proposed undefined mass-based scale; no free-empty integrator
   is required by this review. Specify “empty KDK steps are rejected” and
   strengthen the existing empty control to construct that system, call a
   positive step, assert `EmptyTimestep` and byte-identical checkpoint/time/
   revision. The existing method tests only the ceiling helper. This is a
   documentation/branch-coverage correction, not a demonstrated arithmetic
   failure or a reason to invent a finite empty mass scale. Its future test
   gets its own independent REANA workflow.

3. **Supported by source and dimensional algebra — one unit map and checked
   collisionless state.** `units.rs` 6–184; `state.rs` 6–141;
   `softening.rs` 6–77; parent GP-1/§3 and shared contract §§Identity/Units.
   The 16-scale array follows the `Quantity` declaration order. With
   `T0=L0/V0`, the implemented force scale is `M0*V0^2/L0`, code G is
   `G_si*M0/(L0*V0^2)`, power is `E0/T0` and volumetric power `p0/T0`.
   `B0^2/mu0_si=rho0*V0^2` gives the implemented B/A scales. The cgs adapter
   converts SI density, specific energy, pressure and volumetric power by
   `1e-3,1e4,10,10`, respectively, and returns through the same SI owner.
   No separate code-G setter or cooling unit system exists. Dimensionless
   G1 is separately tagged and cannot convert to SI, including when a
   physical map happens to derive G-code=1.

   All five physical numeric inputs and positive derived scales are checked;
   provenance must be nonempty. Actual supplied values/provenance remain
   accessible immutably. Particle mass is positive finite; position/momentum
   are finite; p/m must be representable. Velocity input creates stored p
   once; later velocities derive from the actual p/m. `Catalog::new` sorts
   the typed IDs and rejects duplicates across both collisionless labels.
   Zero payload is valid. Fixed class matching is checked even for one
   source. Kind/component/galaxy tags do not select a force branch.

   The synthetic SI/rescaling controls are meaningful small dimensional
   controls, not an astronomical conversion or orbit-rescaling campaign.
   Code-unit time in the catalog/step is explicit; future physical timestamps
   must cross T0 once. `Star` is a gravitational label, not a checked stellar
   population, formation epoch, age, activation event or return ledger. No
   gas kind/centroid/volume or fake geometry epoch is exposed. Run-wide
   cell/particle/event uniqueness, allocator/tombstone/restart state and later
   accepted-endpoint births are separate caller/component responsibilities.

4. **Supported GP-2 implementation — attractive force, specific potential,
   unordered pairs and raw reductions.** `kernel.rs` 15–42;
   `direct.rs` 161–205; `checked.rs` 26–121. For `d=xj-xi` and
   `s=sqrt(d·d+epsilon^2)`, differentiation gives

   ```text
   Uij=-G*mi*mj/s,
   partial Uij/partial xi=-G*mi*mj*d/s^3,
   Fi<-j=+G*mi*mj*d/s^3;   Fj<-i=-Fi<-j,
   partial U/partial mi=Phi_i;   U=(1/2)*sum_i mi*Phi_i.
   ```

   The code uses this attractive sign and counts U once. It does not mistake
   Phi for total energy or equal forces for equal accelerations. Self-ID
   pairs fail; different IDs at the same position retain finite negative
   U/Phi and zero pair force. Epsilon is one immutable positive common class;
   epsilon=0, adaptive/mixed softening, periodic images/minimum-image gravity
   and external potentials are absent.

   Sorted `i<j` calls compute a pair vector once and add its negation to the
   other owner. In exact arithmetic the pair torque is
   `(xi-xj) cross Fi=0`. Forces, Phi, U and diagnostics use fixed-order checked
   Neumaier sums. There is no residual force subtraction, momentum recentering
   or energy repair. This is neither bitwise global cancellation nor exact
   floating angular-momentum/energy conservation. The returned candidate
   magnitude sums are diagnostics, not independent acceptance denominators.

   `mul/div` reject nonzero operands rounded to zero and all nonfinite
   results. Ordinary displacement, squares, s-cubed, pair masses, norms and
   diagnostic scales can reject extreme finite inputs even when another
   rescaled formula might succeed. That conservative domain restriction is
   disclosed; no full-range accuracy theorem is claimed. O(N²) work, serial
   reduction, linear arrays and the additional KDK endpoint pass are explicit;
   no measured cost/resource feasibility follows. G-PAIR/G-GRAD and larger-N
   independent reference/roundoff controls remain necessary.

5. **Supported exact cache binding — full bytes participate, with independent
   stale-field controls.** `identity.rs` 1–32; `state.rs` 86–129;
   `softening.rs` 53–59; `direct.rs` 15–78,110–158,217–258.
   Versioned prefixes, fixed-width big-endian words, sized byte bodies and
   sorted fixed 32-byte EntityId text make the stated encodings unambiguous
   on the declared 64-bit target. Full state includes time/revision, complete
   source body, momentum and analysis tags. Unit identity includes actual SI
   inputs, provenance and derived scales; a compulsory separate unit pin
   accompanies the model pin. Backend revision/algorithm is pinned. Derived
   `Identity` equality compares digest **and complete canonical bytes**.

   `validate_for` checks time bits, revision, sources, full state, G bits,
   epsilon bits, model, units and backend before checking sample length/IDs.
   The nine private controls poison exactly one field each, so an earlier
   mismatch cannot conceal an omitted later check. The public control also
   constructs real changed contexts, including momentum-only, tags-only,
   class-table and physical-G1-unit changes. Read-only `sample` inspection
   requires caller epoch validation; `acceleration`, KDK and diagnostics
   perform that validation before consumption. No mutable evaluation/cache
   rebinder is public. This is an implementation identity, not a durable
   interchange format, source-provenance substitute or validated future gas
   cache. The dependency's EntityId/ParticleId formatting and ordering are
   checked only as the supplied interface, not independently approved here.

6. **Supported private-trial KDK and scoped restart — rounded inputs are
   retained rather than replaced by symbolic endpoints.** `kdk.rs` 24–134;
   `state.rs` 80–84; parent GP-4. Under fixed masses/common epsilon and
   representable states, the force/kick/drift signs match the separable
   Hamiltonian Verlet composition. The drift uses half-kicked momentum, and
   the final kick uses forces freshly evaluated at the actual rounded drift
   positions. Since full momentum belongs to the cache state pin, the code
   intentionally reevaluates at those same positions after the final kick
   instead of relabelling the half-momentum cache. Each evaluation still
   computes each unordered pair once.

   All fallible operations, including final diagnostics, precede assignments
   to accepted catalog/cache. A returned error preserves that accepted pair;
   no ID/RNG source is consumed. The failure-after-private-drift test's dyadic
   construction is coherent by manual reasoning: initial x=`3*2^510`,
   v=`2^511`, h=`1/2` leads to trial x=`2^512`; the diagnostic squared norm
   then overflows although the stated initial squares are finite. Its actual
   error path remains unexecuted. Allocation panic/OOM/process loss are not
   Result atomicity guarantees.

   `end=fl(old_time+dt)` must be finite and strictly advancing; revision cannot
   wrap. `StepReport` retains supplied code dt, start pins, actual rounded
   drift state/forces and final full-state forces/diagnostics. Integration dt
   is not silently replaced by `end-old_time`, and exact mathematical
   positions/clock increments are not asserted. Independent endpoint targets
   must use those actual bit patterns and report clock rounding separately.
   The epsilon4 pair test checks ideal position fractions within its stated
   tolerance and distinguishes the two cache states; it supplies no independent
   final-force/final-momentum reference. An additional candidate reevaluation
   at the same positions is a cache consistency check, not such an oracle.

   Private in-memory checkpoints contain catalog/model/units/config/cache and
   validate on restore. Same-binary short restart and velocity-reversed fixed
   lists are written; there is no durable decoder, cross-binary restore or
   source/allocator/RNG checkpoint. The symbolic second-order/symplectic/
   reversal argument does not prove floating long-time behavior, arbitrary
   adaptive step policies or future gas/source coupling.

7. **Supported raw laboratory/internal diagnostics and honest zero scales.**
   `diagnostics.rs` 8–105; parent GP-6/internal. M/P, origin L, lab kinetic
   energy and H are raw. COM velocity is P/M; internal kinetic energy is
   accumulated directly from velocity deviations, not the subtraction of
   large bulk energies. Internal L uses relative position and momentum; W
   uses `(x-Xcm)·F`. The virial residual is
   `abs(2*Kint+W)/(2*Kint+abs(W))`, not `2*Klab+W` or `2*K+U`.

   For a uniform boost b, exact algebra gives
   `H'=H+b·P+M*|b|^2/2`, while Kint/W are invariant. The written small boost
   and nonzero-P/L controls check the intended distinction and preserve raw
   state. Arbitrarily large boosts/coordinates have no roundoff certificate.
   Empty COM is absent; a zero/nonpositive virial scale is typed undefined,
   never a pass or a denominator floor. Nonfinite diagnostic intermediates
   fail. Collisionless global diagnostics supply neither per-tag interaction
   ledgers nor gas thermal/magnetic/surface/birth-work accounting. Later gas
   energy is not implicitly included in this H.

8. **Conditional source eligibility, not numerical acceptance — all 39
   selectors and remaining integration work are explicit.** The independent
   lexical inventory agrees with the author: nine library cache guards and
   thirty integration methods, no ignored direct methods. The author's line
   locators refer to `#[test]`; the companion inventory additionally records
   each following function line. Every method body was read. Exact selectors
   are in the inventory/closed `selectors.json`; they were not discovered by
   running a target. The eps4 axis/oblique/coincident/triplet, equal masses
   and exact rounded-q targets match the reviewed manual fractions. q is
   the retained `0x3eb0c6f7a0b5ed8d` dyadic, not exact decimal `1/1000000`.
   No new conversion, square root or force was evaluated in this review.

   The written positives precede/use meaningful negatives: actual changed
   cache context, one-source wrong class, constructor errors, time/revision/
   ceiling errors and a private-trial failure with unchanged checkpoint.
   Small permutation/translation/right-angle/relabel controls and short
   boosts/reversal/restart do not cover seeded N=4/32/128, general rotations,
   cancellation/operation-count bounds, independent high-precision GP-2/
   gradient/rounded-endpoint references, a physical astronomical unit map,
   long eccentric/plunge orbits or complete G-KDK/G-BOOST histories. Those
   omissions are disclosed rather than manufactured evidence. Finding 1
   adds a concrete feasibility issue to that missing long-campaign work.

   Manual Rust reading found no additional demonstrated syntax/trait/type
   defect in these files: error Debug bounds, immutable borrows, array/iterator
   use, shared ParticleId access and sha2 Digest conversion are coherent.
   This is not compilation, strict Clippy, format or MSRV evidence. The root
   `7ddfa77` context inherits Rust2024/MSRV1.85/MIT/workspace lints. Gravity
   adds only the local galaxy-types path and exact `sha2=0.10.9`, already
   present elsewhere. Independent lock-block comparison confirms all 80
   registry blocks are byte-identical, with only two new path entries and
   moving-mesh's path dependency changed. The cached sha2 archive matches
   the unchanged lock checksum. Its actual normalized manifest and complete
   MIT grant were read; the compatible MIT election retains that notice.
   This is no fresh dependency adoption or complete future-release notice
   audit. The upstream sha2 manifest supplies edition2018 and no rust-version;
   actual new integrated build/MSRV behavior remains a REANA prerequisite.

   **Actionable next sequence:** resolve/document findings 1–2 without altering
   physical thresholds; freeze the coherent shared-ID/gravity/workspace/lock
   source; run the required immutable REANA format/strict-Clippy/build and
   compiled-selector preflight; then execute each eligible method independently
   in its own workflow and independently review actual outputs. The written
   method requests are 1CPU/1GiB/180s/one test thread, prospective declarations,
   not reservations, measured costs or passes. Root owns the build preflight
   and applicable workspace resources. Ready independent cases have no
   aggregate cap. Complete literal/reference/error-budget preparation before
   dependent high-precision/gradient/orbit cases, and resolve finding 1 before
   the registered long matrix. No source review accepts a failed preflight or
   replaces the independent numerical-output decision.

The full goal remains a validated deforming full-3D moving-Voronoi magnetized
gas/DM/old/new-star system with isolated gravity, published multiphase ISM/
SF/feedback and a controlled full-duration merger. Gas geometry/GP-5 work,
birth representation-energy and signed energy/metals ledgers, tree accuracy,
positive equilibrium/IC/live drift, bounded U1–U4/moving-MHD, state-dependent
topology/motion and domain/ambient controls remain required and unexecuted
for this component. None follows from M1 or these collisionless labels.

Reviewed authority includes the retained complete [Dehnen v1 PDF](https://arxiv.org/pdf/astro-ph/0011568v1),
20 pages, 674989 bytes, SHA256
`6d1b778745aa433fe5021549ed4cd4def0b9dc28810aca0a2681d5ec53d53dbc`:
PDF p3 §1.3 Eq3 and the apparent printed Eq4b sign discrepancy were visually
inspected in a fresh complete-page render, with pp1–4 context. This is not
an official erratum; differentiation fixes GP-2's sign. The complete
[Hairer January–February 2010 lecture2 PDF](https://www.unige.ch/~hairer/poly_geoint/week2.pdf),
18 pages, 378909 bytes, SHA256
`f4f15ff5124fb685870e13b36e54cbc4edc96744199b518ec12e1c5cf006f0fb`,
was retained; p2 Theorem2/Eq2 was freshly rendered/visually inspected with
pp1–4 context. It supports separable Verlet, not these ICs, the ceiling
coefficient, encoding or a floating-point result. No external code was copied.

Actual source checks: all 13 manifest body identities plus the manifest itself;
39 unique direct source selectors and their attribute locators; exact retained
Git/proposal/primary bytes; JSON parsing, UTF-8/newline/whitespace, local review
links and closed inventory checks; 80 unchanged registry blocks and the public
cached sha2 archive checksum. Required project docs were read/revisited; the
current HANDOFF acceptance section was reread and its historical remainder
retained as earlier-read context, not re-reviewed scientific evidence.

Inspection limitations are retained honestly: several oversized displays were
truncated and affected subject/document portions were reread narrowly. A
locator search included a nonexistent historical directory (exit2), then was
repeated against the actual retained paths. A check generator misread the
inventory object's shape (exit1), and its correction initially compared fn
lines to attribute locators (exit1); both failures are retained, and the
corrected source checks have errors=[]. No subject was changed to make an
inspection pass. These were document/source inspections, not tests. No M1
evidence, historical review, scientific code or other worker file was edited.
