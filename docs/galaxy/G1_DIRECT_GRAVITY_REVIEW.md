# Source and mathematical check of the direct-gravity reference

2026-11-22. **The units, fixed-common-Plummer pair kernel and collisionless
KDK equations support the proposed first implementation slice, after scoped
M1 acceptance and fixture freezing. No numerical G1 gate is accepted here.**
No gravity implementation, test, orbit or evolution was run. This coordinator
check is separate from the M1 final-output review and from the independent
moving/bounded-MHD and ISM reviews.

The reviewed equations are sections 2, 4 and 6.1 of
[the gravity contract](GRAVITY_PARTICLES_SPEC.md), unchanged byte-for-byte
from the other agent's author commit `c5dbb8a`. Their individual hashes and
the exact current file/source identities are in
[g1_direct_gravity_review_sources.json](g1_direct_gravity_review_sources.json).
The coordinator authored interface amendments elsewhere in that document;
this check does not independently approve those amendments, tree accuracy,
gas coupling, initial conditions or the later merger.

## 1. Units and source identities

GP-1 follows from `x=L0*xcode`, `t=(L0/V0)*tcode`, `m=M0*mcode`:
the force unit is `M0*V0^2/L0` and
`Gcode=Gsi*M0/(L0*V0^2)`. Requiring
`B0^2/mu0_si=(M0/L0^3)*V0^2` gives the stated magnetic scale and `A0=B0*L0`.
The SI-to-cgs density, specific/volumetric energy and power conversions are
dimensionally consistent. Physical base scales and dimensionless G=1 are
separate conventions; three arbitrary physical scales do not also set G=1.

The retained NIST **2022** listing supplies the stated central G and
permeability values. Its actual downloaded bytes, available through the
cooling audit, now have a recorded hash; this closes the earlier gravity
inventory's missing downloaded-byte observation without rewriting history.
G and permeability are measured constants, not exact SI definitions.
IAU B3 p.3 and Prsa et al. p.5 Table 1 confirm the nominal solar GM, with
mass in kg requiring a specified G. Prsa et al. p.8 gives the exact au and
parsec conventions. The relevant nominal-GM pages were visually inspected.

Before G1 execution, freeze the actual f64 scales, conversion expressions,
units hash and force-model identity. Applying a cached evaluation must check
G, epsilon/table/pair rule and backend/config identity as well as source and
geometry epochs. The contract already requires that metadata; an unvalidated
descriptive string is not an implementation of the requirement. Include
wrong-model/unit identity in the invalid-input/restart fixtures.

## 2. Pair force, energy and the source sign discrepancy

Dehnen v1 p.3 Eq.3 supplies the Plummer potential estimator. Directly
differentiating the contract's pair energy, with
`d=xj-xi`, `s=sqrt(d dot d+epsilon^2)`, gives

```text
Uij = -G*mi*mj/s
partial Uij / partial xi = -G*mi*mj*d/s^3
Fi = -partial Uij/partial xi = +G*mi*mj*d/s^3.
```

Thus GP-2 is attractive. Dehnen's printed Eq.4b has the apparent sign
inconsistency already flagged by the author; the page was visually checked.
This is not an author-confirmed erratum. Implement the differentiated GP-2
and test attraction, rather than transcribing that printed force expression.

The symmetric pair sum gives `U=sum(mi*Phi_i)/2` and
`partial U/partial mi=Phi_i` at fixed positions/epsilon. The single computed
pair force gives opposite **forces**, not opposite accelerations for unequal
masses. Its pair torque is `(xi-xj) cross Fi=0` in exact arithmetic.
Compensated accumulation does not make these identities bitwise exact.
Do not subtract net force or recenter momenta to improve the diagnostic.

The stated rational pair has separation 3 and epsilon 4, hence s=5;
substitution gives `U=-6/5`, `Phi=(-3/5,-2/5)`, and
`F0=(18/125,0,0)`. Distinct co-located IDs have zero force and
`Uij=-G*mi*mj/epsilon`; a self ID has no pair term. No numerical evaluation
of these fixtures was performed. Empty/one-source, coincident IDs, unequal
masses and invalid/nonrepresentable states remain required REANA cases.

The proposed mixed-class RMS softening is a different future choice. This
check supports the first **common positive fixed epsilon** profile only.

## 3. Canonical KDK and its precise limits

[Hairer's 2010 lecture 2](https://www.unige.ch/~hairer/poly_geoint/week2.pdf),
p.2 Theorem 2/Eq.2, gives the separable Hamiltonian Verlet construction.
With `T=sum(p_i^2/(2*mi))` and the fixed GP-2 U, it reduces to GP-4.
The full primary PDF was retained and that equation page rendered/inspected.

Independently, define the exact subflows
`K_h:(x,p)->(x,p-h*grad U(x))` and
`D_h:(x,p)->(x+h*M^-1*p,p)`. Both preserve the canonical symplectic form:
their shear blocks are symmetric because the Hessian of U and `M^-1` are
symmetric. `K_(h/2) D_h K_(h/2)` is its own reversed-step adjoint;
consistency plus that symmetry gives order two for the smooth fixed system.
It does not conserve the original Hamiltonian exactly. Floating-point maps
do not inherit exact symbolic symplecticity or exact time reversal.

Each fixed predetermined step remains a composition of symplectic maps.
To reverse a variable predetermined sequence, reverse its order and signs
(or reverse momenta and replay the reversed positive sequence). A generic
state-dependent timestep controller is a different map. Output landing,
adaptive decisions, tree switching and source events are not certified by
the fixed-step argument. Keep full-step momenta in restart snapshots.

Joint translation/boost covariance also follows in exact arithmetic: pair
displacements leave F unchanged, and adding `mi*b` to each momentum advances
the translated position by `b*h` at each drift. Compare the same prescribed
step list; large-coordinate cancellation remains a finite-precision limit.
This is a direct-kernel/KDK property, not general moving-MHD invariance.

The conservative timestep scale has a useful independent bound. For the
pair potential the displacement Hessian has transverse eigenvalue `1/s^3`
and radial eigenvalue `(epsilon^2-2*r^2)/s^5`, before `G*mi*mj`.
Both absolute values are at most `epsilon^-3`. For a perturbation z,

```text
|z^T Hessian(U) z| <= (G/epsilon^3)*sum_(i<j) mi*mj*|zi-zj|^2
 <= (G*Mtotal/epsilon^3)*sum_i mi*|zi|^2.
```

The second inequality follows by expanding the pair sum and removing
`|sum mi*zi|^2`. Thus `sqrt(G*Mtotal/epsilon^3)` bounds the mass-normalized
curvature scale. This supports the dimensions and conservative character
of the proposed `.05` ceiling; it is not an optimal timestep, global-error
bound, or proof of stability through physical gravitational instabilities.
The registered binary/cluster timestep ladders still decide accuracy.

## 4. Coupling boundary and next evidence

Differentiating GP-2 when gas masses/centroids vary yields GP-5 with the
declared **outward** face mass rate: a face i-to-j contributes
`q*(Phi_j-Phi_i)` to potential-energy change, so its total gas work is
`q*(Phi_i-Phi_j)`. Sharing that work equally gives the stated per-cell sign.
This is an independent semidiscrete identity, not acceptance of the proposed
finite-step gas split. Springel v2 PDF p.28 Eq.96 motivates using actual
face mass transport; its sign convention and adaptive-softening model must
not be substituted for GP-2. Its p.26 discussion explicitly warns that simple
operator splitting can fail near hydrostatic equilibrium.

G2 still needs its matched gas-work, hydrostatic/collapse, centroid, thermal
correction, boundary and tree gates. The same physical kernel must define
potential/forces/energy at both endpoints. This review does not accept an
unspecified softened equilibrium, disk DF, production RNG, birth transaction
or a collisionless-only calculation as the completed galaxy-merger goal.

After M1 acceptance, freeze concrete per-case G-PAIR/G-GRAD/G-SYMMETRY,
G-KDK and G-BOOST/RESTART inputs and independent high-precision references;
do not import the production kernel into the reference. Preserve the
existing algebra/convergence/conservation thresholds. Each executable test
and evolution runs on REANA after the new immutable preflight, with explicit
per-case resources and concurrent ready workflows. There is no executable
evidence in this source check, and no scientific code was changed.
