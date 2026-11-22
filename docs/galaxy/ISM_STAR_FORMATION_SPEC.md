# Multiphase ISM, star formation and feedback source contract

Status: **design only; unimplemented and unexecuted**, 2026-11-22. This is an
independent Rust implementation contract for a published SH03-like reference,
not an AREPO port, Illustris/TNG prescription, or accepted galaxy model.
The machine-readable source inventory is
[ism_star_formation_sources.json](ism_star_formation_sources.json).
The companion [cooling contract](COOLING_RATES_SPEC.md) and
[cooling source inventory](cooling_rates_sources.json) contain the completed
atomic/CMB transcription and selected FG20 external-input audit. Shared
units, identities and birth timing follow
[INTEGRATION_CONTRACT.md](INTEGRATION_CONTRACT.md).

The prerequisite is scoped M1 acceptance of frozen numerical source
`2bdcea0d28340e7429e10053a641f92d51fcc696`, then the relevant M2 3D
geometry/operator/motion and G1/G2 gravity/particle gates in
[GALAXY_MERGER_PLAN.md](../GALAXY_MERGER_PLAN.md). M1 still needs its fresh
physical campaign and final output review. This document neither changes M1
nor authorizes coupled 3D/new-physics execution before those gates.

Revision `ism-policy-units-fixtures-v3` addresses the separate
[policy review](ISM_COOLING_POLICY_REVIEW.md) committed in `444d9a6`, of
the prior four-file response `6d8f634`. Both independent reviews and their
reviewed-byte inventories remain immutable. This is a narrow event-unit,
manufactured-fixture and wording correction; all supported physical
equations, birth interfaces and the half-open SF draw law are retained.

| Policy-review item | Disposition | Evidence/status |
| --- | --- | --- |
| 10: event dimensions | Entry remains the specific-energy guard `u-u_eff`, scaled by fixed `u_ref=u_SN`; cloud exhaustion uses mass guard `m_c`, scaled by fixed `M_ref`. Section 9a registers unit/parcel representations. | Manual dimensions only; event/oracle numerical evidence remains unexecuted. |
| 13: manufactured ladders | Shared L01/L02 base `dt0=tau/16`, k=`0..4`; preregister k=5 additionally for L02 heating only, with its order fit on levels 3/4/5. Distinguish exact discrete BE from continuum; CONSTANT is exact algebra/ledger evidence. | Retain the failed heating-ladder counterexample and the refined all-history bound below; these are manual compatibility checks, not numerical passes. |
| B01 wording | `.125,.625` are formation times; activation at 1 gives population ages `.875,.375`. | Actual source intervals, midpoint metadata and activation are unchanged. |

The earlier `ism-review-disposition-v2` addressed the separate
[13-finding AI review](ISM_COOLING_DESIGN_REVIEW.md), committed in `f8220ef`,
and the coordinator's `4162235` birth reconciliation, read at checkout
`66370fa9b9dfdb01e5772c2b9801463e27aa338a`. The original reviewed-byte
receipts remain unchanged in [the review inventory](ism_cooling_review_sources.json).
The source inventories identify this revision separately; source approval
of equations is not numerical, physical, M1 or galaxy acceptance.

| Review finding | Concrete disposition in this revision | Evidence still required |
| --- | --- | --- |
| 1: subinterval/activation conflict | Section 7 preserves every actual successful nonzero-L subinterval packet; all activate atomically at the global endpoint, with `formation_end<=activated_at`. | Endpoint/rollback/restart cases in section 9a. |
| 2: atomic formulas/C1 | Retain supported formulas and named C1. Original Black Eq. (7) reinspection corrects the review's ancillary `-.6533` reading to `-.6353`, with no coefficient change. | Independent evaluated-value fixtures; historical review preserved. |
| 3: root uniqueness | Cooling section 4a separates the unique nonsingular fixed-T charge closure from enumerated caloric/thermal roots; sections 4a/8a here specify EOS/implicit roots. | Independent branch inventories and root evidence. |
| 4: CMB/units | Retain supported signed law and constants. | Independent SI/cgs and cancellation fixtures. |
| 5: UV interpolation | Cooling section 6 freezes exact-q-node and one-ULP endpoint policies. | Parser/interpolator implementation fixtures, not an exact-UV accuracy claim. |
| 6: private external data | Cooling section 6a defines an immutable operator-supplied private handle and output allowlist. | Owner authorization for REANA project tests already exists; actual private platform access/retention remains unverified, with no public raw distribution. |
| 7: analytic interval | Name `kwh96-evaluation-1e3-1e8-v1`, with explicit low-T extension and applicability conditions. | Physical timescale/optical-depth evidence for any claimed physical fixture. |
| 8: SH03 equations | Keep supported mass/thermal/pressure/SN equations unchanged. | REANA algebra and evolving-source evidence. |
| 9: threshold/EOS | Section 4a freezes finite density/hot-fraction brackets and restoring-branch continuation. | Actual roots, stability and calibration; no threshold number is adopted. |
| 10: BE/events | Section 8a fixes residuals, finite implicit searches, near-empty scales and located events. | Admissibility, temporal convergence and rollback; no positivity theorem. |
| 11: passive metals | Section 7 fixes `0<=Z<=.02` as an engineering tracer range and stable small-L formulas. | Tracer/ledger tests; no chemically consistent metal-rich EOS claim. |
| 12: gravity/IDs/packets | Include all new-new, gas-new and old-source GP-2 terms with stable serial IDs and no prior motion. | Raw energy plus the gravity contract's representation and refinement gates. |
| 13: concrete packet | Sections 9a and cooling 8a register scalar/one-zone/endpoint inputs and independent oracles. | Immutable implementation/preflight, execution and separate output review; G4 ICs remain outstanding. |

The intended endpoint remains the fully deforming 3D **magnetized** live
dark-matter/gas/existing-and-new-star merger, including accepted bounded MHD
and isolated-galaxy controls. Scalar source work does not substitute for it.

## 1. Sources, versions and the first scientifically defined profile

The primary physical source is Springel & Hernquist, MNRAS **339**, 289-311
(2003), DOI [10.1046/j.1365-8711.2003.06206.x](https://doi.org/10.1046/j.1365-8711.2003.06206.x).
Both the complete [arXiv v1](https://arxiv.org/pdf/astro-ph/0206393v1) and the
[published full text via ADS](https://articles.adsabs.harvard.edu/pdf/2003MNRAS.339..289S)
were downloaded and consulted. The arXiv record lists only v1, submitted
2002-06-22; the downloaded 25-page PDF prints a 2018 TeX date, which is not a
new arXiv version or publication date. The published PDF has 23 pages, printed
289-311, and records acceptance on 2002-10-17. All unqualified SH03 equation
numbers below refer to **the final published paper**. Hashes and local reading
paths are in the JSON; copyrighted papers remain under ignored
`results/galaxy_ism_design_20261122/`.

The consulted core equations retain their numbering between versions, but
pagination changes: published pp. 291-294 correspond to arXiv pp. 3-6;
published pp. 297-299 to arXiv pp. 10-12. The arXiv Eq. (40) calls the yield
`p`; final Eq. (40) uses `y_star`. This document uses the published symbol.
Published Eq. (3) gives the **positive magnitude** of evaporation; its actual
cold-mass sink has the minus sign in Eq. (5). Eq. (29) prints `m_h u_u`;
the consistent quantity is `m_h u_h`, fixed unambiguously by Eqs. (13), (19)
and the definitions, not a new energy variable. Equation (2)'s prose about
energy per mass of stars can be ambiguous; its mathematical normalization,
`beta*u_SN = (1-beta)*epsilon_SN`, is the contract.

**First profile proposed here: `sh03-finite-phase-ira-v1`.** Evolve the SH03
finite-phase mass/thermal equations, primordial optically thin cooling and
instantaneous recycling, a common gas velocity, and immediately independent
collisionless star particles. Use the effective mixture pressure of Eq. (13).
Use the self-regulated EOS and Eq. (23) as source-mapped equilibrium and
calibration references. Initially create deterministic variable-mass stellar
packets from each accepted source interval, as specified in section 7.
This combines the phase physics of SH03 section 5.1 with immediate gas/star
decoupling motivated by section 5.2; it does **not** reproduce SH03's hybrid
gas-plus-star SPH particles or claim AREPO implementation identity.

This finite-phase choice makes the gas energy equation and SN budget explicit
before an equilibrium acceleration is attempted. It avoids silently assigning
an equilibrium pressure while conserving an incompatible thermal energy.
`sh03-equilibrium-ira-v1` is a **later, separately reviewed acceleration**:
the algebra in section 4 is ready to implement as an oracle, but a coupled
instantaneous-equilibrium integrator must first demonstrate its energy/work
limit against the finite-phase reference. It cannot be enabled by replacing
`P` with `max(P,P_eff)` or resetting internal energy.

The initial reference has no winds, delayed AGB/SN Ia mass return, resolved
SN blast injection, AGN, molecular network, metal-line cooling, self-shielding,
cosmic rays, conduction between resolved cells, IMF variation, or eEOS
interpolation parameter. Metals are a locally mixed advected tracer and an
explicit nucleosynthetic source. These omissions define the model; they do
not claim that this model alone produces realistic merger outflows or cosmic
stellar masses. SH03 itself motivates an additional wind model in section 4.

## 2. Variables, units, state and invariants

The first galaxy runs use isolated, non-expanding **physical** coordinates,
global synchronized timesteps and `f64`. One shared SI-based `UnitSystem`
owns fixed `L_unit` [m], `M_unit` [kg], `V_unit` [m/s], hence
`t_unit=L_unit/V_unit`, `rho_unit=M_unit/L_unit^3`, and
`u_unit=V_unit^2`. A single explicit cooling adapter converts SI to the
cgs inputs/outputs defined below (`m -> 100 cm`, `kg -> 1000 g`,
`J -> 10^7 erg`); the ISM module does not own a competing unit system.
Record numerical conversion constants and their source in the run manifest.
No hidden cosmological `a` or `h` factors are permitted.
The physical background redshift `z_uv` is an explicit frozen radiation
input for an isolated run, not the integration time.

| Symbol | Definition and unit |
| --- | --- |
| `V`, `m_g` | Cell volume [cm^3] and gas mass [g]. |
| `rho=rho_c+rho_h` | Total coarse-grained gas mass density, `m_g/V` [g/cm^3]. Does not include collisionless stars or dark matter. |
| `rho_c`, `rho_h` | Cold/hot **mass per total averaging volume**, `m_c/V`, `m_h/V` [g/cm^3]. Not the internal density within an individual molecular cloud or a cloud filling factor. |
| `u_c`, `u_h` | Cold/hot thermal energy per phase mass [erg/g = cm^2/s^2]. `u_c` is fixed; `u_h` evolves. |
| `U_th` | Cell thermal energy `m_c*u_c+m_h*u_h` [erg]. |
| `x` | Cold mass fraction `m_c/m_g`, dimensionless. |
| `beta` | Promptly returned fraction of **gross formed** stellar mass; dimensionless, `0<beta<1`. Not the total lifetime return fraction. |
| `t_star` | Gross cold-cloud consumption time [s], not the long-lived stellar depletion time. |
| `A` | Dimensionless cloud evaporation mass per prompt-return mass; `A>=0`. |
| `u_SN` | SN energy per prompt-returned mass [erg/g]; not per long-lived stellar mass. |
| `epsilon_SN` | SN energy per **net locked** stellar mass, as fixed by Eq. (2): `beta*u_SN/(1-beta)` [erg/g]. |
| `F`, `L`, `R`, `E_ev` | Integrated gross formed mass, net locked mass `(1-beta)F`, prompt recycled mass `beta F`, and evaporated mass `A beta F` [g]. |
| `Lambda_net` | Volumetric **loss** rate `C_total-H_total`, [erg/cm^3/s], including signed CMB exchange; positive means gas loses energy, negative means net heating. The call uses actual hot density `rho_h`, not total `rho`, except in the explicitly labelled equilibrium derivation. |
| `f` | SH03 switch: `0` routes cooling to phase condensation; `1` applies ordinary thermal cooling/heating. Not a star-formation efficiency. |
| `Z`, `y_star` | Gas metal mass fraction and freshly synthesized metal mass per net locked stellar mass, dimensionless. |

For the ideal monatomic components, `gamma=5/3` and
`u(T)=k_B*T/[(gamma-1)*mu*m_p]`, where `mu` here is dimensionless. SH03's
temperature expression uses a mean **particle mass**; do not multiply by
`m_p` twice. The ordinary hot phase's `mu` comes from ionization equilibrium.
For the reference parameter conversion, explicitly choose neutral primordial
`mu_c=1/(X+Y/4)` for `u_c` and `u_4`, and fully ionized primordial
`mu_SN=1/(2X+3Y/4)` for `u_SN`. These explicit conversion conventions are
engineering choices, not an unquoted extra SH03 parameter table.

Store `m_c` and total gas energy, derive `m_h=m_g-m_c` and
`u_h=(U_th-m_c*u_c)/m_h`. The admissible two-phase state has
`m_g>0`, `0<=m_c<m_g`, `u_h>u_c`, `0<=Z<=.02`, finite variables and positive
pressure. Ordinary gas has `m_c=0`; its energy is not interpreted as an
unresolved cold component. A zero-hot-mass state must never enter a division
by `rho_h` or `u_h-u_c`. Invalid states cause source-step rejection/error,
with counters; no clipping into an apparently physical solution.

Hydrodynamics advects `m_c` and metal mass conservatively with the gas mass
flux and bounded fractions; it evolves the gas total energy. The mixture
pressure is `P=(gamma-1)*U_th/V`. All pressure work and dissipative heating
changes the remaining thermal reservoir with fixed `u_c`, and therefore the
hot energy; phase masses change by advection and the specified local sources.
This common-velocity, common-cell closure is a finite-volume engineering
adaptation of SH03, not separately resolved cold and hot fluids.

## 3. Published equation-to-code map

These source equations omit hydrodynamic adiabatic work, gravity and transport,
which are supplied by the validated gas/dynamics operators. The derivatives
in this section describe a fixed averaging volume during a local source call.
Let `s=rho_c/t_star` and `q=(1-f)*Lambda_net/(u_h-u_c)`.

| Published location | Exact source contract | Proposed pure Rust routine |
| --- | --- | --- |
| p. 291, Eq. (1) | `dot rho_star=(1-beta)*s`; gross formation `s`; prompt return `beta*s`. | `formation_rates` |
| p. 291, Eq. (2) | `dot e_SN=beta*s*u_SN=epsilon_SN*dot rho_star`; `u_SN=(1-beta)*epsilon_SN/beta`. | `sn_budget` |
| p. 291, Eq. (3); p. 292, Eqs. (5)-(6) | Evaporation magnitude `A*beta*s`; subtract from cold, add to hot. | `exchange_rates` |
| p. 292, Eq. (4) | Condensation `q` transfers hot to cold at fixed phase energies; thermal energy lost per mass is `u_h-u_c`. | `condensation_rate` |
| p. 292, Eq. (5) | `dot rho_c=-(1+A*beta)*s+q`. | `phase_rhs` |
| p. 292, Eq. (6) | `dot rho_h=beta*(1+A)*s-q`. | `phase_rhs` |
| p. 292, Eq. (7) | `dot U_th/V=-Lambda_net+beta*s*u_SN-(1-beta)*s*u_c`. | `thermal_rhs`, ledger |
| p. 292, Eq. (8) | `dot(rho_c*u_c)=-(1+A*beta)*s*u_c+q*u_c`. | Independent cold-energy check |
| p. 292, Eq. (9) | `dot(rho_h*u_h)=beta*s*(u_SN+u_c)+A*beta*s*u_c-[(u_h-f*u_c)/(u_h-u_c)]*Lambda_net`. | Independent hot-energy check |
| p. 292, Eq. (10) | `rho_h*dot u_h=beta*s*[u_SN-(A+1)*(u_h-u_c)]-f*Lambda_net`. | `hot_specific_rhs` oracle |
| p. 292, Eqs. (11)-(12) | For `f=0`, `u_h_eq=u_c+u_SN/(A+1)`; `tau_h=t_star*rho_h/[beta*(A+1)*rho_c]`. | `hot_equilibrium`, `relaxation_time` |
| p. 293, Eqs. (13), (19) | `P_eff=(gamma-1)*rho*[(1-x)*u_h+x*u_c]`. | `mixture_pressure` |
| p. 293, Eq. (20) | `A=A0*(rho/rho_th)^(-4/5)`. | `evaporation_coefficient` |
| p. 294, Eq. (21) | `t_star=t0*(rho/rho_th)^(-1/2)`. | `formation_timescale` |
| pp. 293-294, Eqs. (14)-(18), (22)-(23) | Equilibrium, threshold and EOS derivation in section 4. | `equilibrium`, `calibrate_threshold` |
| pp. 297-298, Eqs. (30)-(38), section 5.1 | Explicit mass-exchange discretization; source oracle, not blindly copied as the new integrator. | `source_step` |
| p. 298, Eq. (39), section 5.2 | Published net-mass stochastic law, section 7. | Future `sh03_generation_plan` |
| p. 298, Eq. (40), section 5.3 | `dot Z=(1-beta)*y_star*x/t_star` in a closed box. | `metal_ledger` |

The identities are `dot rho_c+dot rho_h+dot rho_star=0` and
`dot(rho_c*u_c)+dot(rho_h*u_h)=Eq.(7)`. Do not add an independent heating
term `A beta s (u_h-u_c)`: evaporating clouds consumes the hot reservoir's
specific energy through mass dilution, already represented in Eq. (10).
Likewise, condensation removes thermal energy once through `Lambda_net`.
Taking both Eq. (7) and a second explicit cooling subtraction would double it.

SH03 section 5.1, Eq. (32), treats hot-mass cooling implicitly and prevents
`m_h'` falling below half its previous value in one step. Eqs. (35)-(37)
then conserve total mass. That half-mass condition is a timestep/robustness
restriction, not a physical cooling law. This contract rejects/subdivides a
step that violates its limits instead of silently altering the cooling rate.

## 4. Equilibrium EOS, threshold derivation and branches

At fixed volume the quasi-steady pressure condition used by SH03 is

```text
K = beta*u_SN - (1-beta)*u_c > 0
Lambda_net(rho_h,u_h_eq) = K*rho_c/t_star                  [Eq. 14]
```

It is an energy/pressure regulation condition. It does not mean that both
phase masses are individually constant while stellar mass grows. In
particular, solving `dot rho_c=0` as a replacement for Eq. (14) gives a
different cold fraction.

SH03 next uses the high-temperature density-squared scaling
`Lambda_net(rho_h,u_h)=(rho_h/rho)^2*Lambda_net(rho,u_h)`. Then

```text
y = t_star*Lambda_net(rho,u_h_eq)/(rho*K)                  [Eq. 16]
x = y*(1-x)^2
x = 1 + 1/(2*y) - sqrt(1/y + 1/(4*y*y))                 [Eq. 18]
u_eff_eq = (1-x)*u_h_eq + x*u_c
P_eff_eq = (gamma-1)*rho*u_eff_eq                        [Eq. 19]
```

For implementation, the derived equivalent expression
`x=2*y/[1+2*y+sqrt(1+4*y)]` avoids subtraction cancellation at small `y`.
Use `x=0` at `y=0`; use a scaled evaluation for large `y` without forming
overflowing `4*y` or `2*y`. For example compute the hot fraction
`1-x=2/[1+sqrt(1+4*y)]`, with `sqrt(1+4*y)=2*sqrt(y+1/4)` evaluated without
an intermediate overflow. Form `u_eff=u_c+(1-x)*(u_h_eq-u_c)` using the hot
fraction rather than subtracting an `x` rounded to one. Negative `y` does
not have a star-forming equilibrium under these assumptions; it is not
clamped to a positive value. As `y -> 0+`, `x~y`; as `y -> infinity`,
`1-x~y^(-1/2)`. At `x=0`, the formal `tau_h` is infinite: there is no SN
relaxation until clouds exist. `u_h_eq` approaches `u_c` for very large `A`,
and `u_c+u_SN` as `A -> 0`. Division safeguards must not change these limits.

**Important cooling qualification:** photoionization changes ion fractions
with density and photoheating is not generally quadratic in density. The
finite-phase profile always evaluates the backend at the actual `rho_h`.
The closed form Eq. (18) is exact only for the stated density-squared
approximation. A separate `full_rate_equilibrium` oracle solves

```text
Lambda_net((1-x)*rho,u_h_eq) - K*x*rho/t_star = 0
```

on `0<=x<1`, retaining the full radiation-dependent rates. Report absent or
multiple roots; a bracketed continuous root following the stable branch must
be established before use. Do not silently use total-density UV cooling in
Eq. (18) and call it the full-rate solution.

SH03's threshold calibration on p. 294 is:

```text
T_SN/A0 ~ 10^5 K                                        [Eq. 22]
u_h0 = u_c + u_SN/(A0+1)
x_th = (u_h0-u_4)/(u_h0-u_c)
     = 1 + (A0+1)*(u_c-u_4)/u_SN
Lambda_2(u) = Lambda_net(rho,u)/rho^2
rho_th = [x_th/(1-x_th)^2] * K/[t0*Lambda_2(u_SN/A0)]     [Eq. 23]
```

`u_4` is the declared specific energy at `10^4 K`. The printed Eq. (23)
evaluates the cooling coefficient at the approximate hot energy `u_SN/A0`,
not exactly `u_h0`. It assumes density independence of `Lambda_2` in this
temperature range. Preserve that approximation in a named
`published-eq23` calibration mode; quantify its actual continuity residual.
No fixed number such as `n_H=0.13 cm^-3` has been verified from the consulted
SH03 parameter text, and none is installed as a universal threshold here.

The proposed finite-phase reference uses **`full-rate-continuity-v1`**, an
explicit engineering refinement of Eq. (23), once the rate package exists.
Solve the scalar equation

```text
Lambda_net((1-x_th)*rho_th,u_h0; radiation)
    = K*x_th*rho_th/t0
```

with `x_th` as above, requiring `u_c<u_4<u_h0`, `K>0`, positive cooling,
a verified bracket and a unique selected root. This enforces
`u_eff_eq(rho_th)=u_4` using the same backend as evolution. Record both
threshold calibrations and their difference; this is not a claim that
AREPO uses this refinement. No root, ambiguous roots, or an unavailable
backend is a blocking model-configuration error. A user-specified physical
`rho_th` is a separate calibration override and forfeits automatic
continuity until checked; do not combine it silently with derived Eq. (23).

Pressure/energy can be continuous at the onset while the derivative of the
EOS and the volumetric SFR are discontinuous: `x_th` is generally nonzero.
There is no requirement of SFR continuity or a globally constant polytropic
index. Compute `n_eff=d ln P_eff/d ln rho` from the pinned closure and report
it; SH03 Fig. 1 even softens below `4/3` at sufficiently high density.
Neither a global `gamma_eff=4/3` nor a Jeans pressure floor is this model.

### 4a. Finite threshold/EOS root and continuation policy

`ism-root-inventory-v1` is numerical engineering, not an SH03 algorithm or
proof of physical stability. Use the certified-bin inventory rules in
cooling section 4a; no sign-scan alone certifies that all roots were found.
Freeze the following **finite** searches for this reference:

- Threshold: total-gas `n_H,total=X*rho/m_p` in `[1e-8,1e4] cm^-3`,
  initial log10 nodes `-8+i/128`, `i=0..1536`. The hot-density argument
  remains `(1-x_th)*rho`; it is never confused with this total-density axis.
  Inventory the full-rate threshold residual and retain every bracket/root.
  `published-eq23` is separately evaluated/reported with its approximation.
- EOS: `rho/rho_th` in `[1,1e3]`, intersected with the preceding total-density
  bracket. Register density nodes `rho_k=rho_th*10^(3*k/256)`, `k=0..256`,
  stopping at the bracket boundary and including that boundary. At each
  density inventory `h=1-x` on `[2^-40,1]`, using `log2(h)=-j/32`,
  `j=0..1280`. A root below this hot-fraction search is an oracle-domain
  failure, not a hot-mass floor in the evolved finite-phase state.
- Every rate call must have a uniquely admissible caloric T root in the
  named evaluation interval. A density root that needs an invalid T is
  invalid, not an excuse to borrow the last valid temperature.

For the full-rate EOS write
`g(x;rho)=Lambda((1-x)*rho,u_h_eq)-K*x*rho/t_star`.
Require a **restoring regulation root**, `partial g/partial x<0`, with its
derivative interval strictly negative. This criterion follows the diagnostic
frozen-density, frozen-`u_h_eq` regulation equation
`dot x=g/[rho*(u_h_eq-u_c)]`: a positive cold-fraction perturbation must
produce a negative restoring response. The hot-energy relaxation of Eq. (10)
also has positive tau at nonzero clouds. This is a stated *regulation
diagnostic*, not a claim that the full consuming finite-phase system has a
stationary mass equilibrium or that its dynamics are proved stable.
Independent finite-phase perturbation/time-integration evidence must check
that interpretation. Also require `dP_eff/d rho>0` on the selected branch;
do not replace a failing branch by a pressure floor.

At the threshold require exactly one admissible threshold candidate whose
onset EOS root satisfies that criterion. Zero candidates gives
`NoThresholdRoot`; more than one gives `MultipleThresholdRoots`; a
non-isolated/zero-slope candidate gives `UnresolvedRootInventory` or
`MarginalRegulationRoot`. Do not choose the lowest density after the fact.
Continue its EOS branch through the registered density ladder, subdividing
each density interval dyadically (at most 20 levels) and certifying a
connected root tube with negative g_x. All other roots remain in the
inventory. Two possible connected continuations give `MultipleEosBranches`;
loss of the selected tube, a fold, domain exit or non-restoring derivative
gives `EosBranchLost`. No nearest-root jump, crossing to a disconnected
stable root, or extrapolated root is permitted. Runtime entry requests
outside the calibrated tube fail; no equilibrium acceleration is enabled.

Scale threshold/EOS residuals by
`max(C_total+H_total, abs(K*x*rho/t_star), 1e-80 erg cm^-3 s^-1)` and
require residual `<=1e-12` of that scale. Root bracket widths must satisfy
`Delta ln(rho)<=1e-10` and `Delta ln(h)<=1e-10`, respectively. Derivative
signs and root counts need certified brackets as well as small residuals.
Record continuity against both chosen `u_4` and independently enumerated
ordinary thermal equilibrium. Thermal/root selection uses cooling section
4a; absence or multiplicity cannot be hidden in a single continuity number.
Threshold values, EOS slopes, stable tubes and these physical comparisons
are **unexecuted calibration evidence**, not results supplied here.

### Runtime branch contract (explicit engineering adaptation)

1. For `rho<=rho_th`, use ordinary single-phase cooling, `m_c=0`, `f=1`,
   SFR=0. On downward crossing, mix any remaining clouds into hot gas at
   unchanged `m_g`, momentum, `U_th` and metals. Thus `u_h'=U_th/m_g`;
   the energy to evaporate clouds comes from the existing hot reservoir,
   consistent with the p. 298 prescription. No heat is created to enforce a
   chosen final temperature. Locate the density crossing in the coupled step.
2. For `rho>rho_th`, ordinary hot/shock-heated gas first remains single
   phase and cools. It can enter the multiphase branch when a valid
   equilibrium exists and its actual `u=U_th/m_g` falls to or below
   `u_eff_eq(rho)`, with `u_c<u<u_h_eq` and equilibrium hot temperature
   at least `10^5 K`. Repartition at **fixed total energy** using
   `x_seed=(u_h_eq-u)/(u_h_eq-u_c)`, `m_c=x_seed*m_g`, `u_h=u_h_eq`.
   This energy-conserving initialization is an engineering choice; the
   paper does not specify an equivalent finite-volume entry algorithm.
   It must be independently checked, not described as an AREPO algorithm.
3. In an existing multiphase cell with `rho>rho_th`, use Eq. (5)-(10).
   Condensation is enabled (`f=0`) only for positive `Lambda_net` and
   actual hot `T_h>=10^5 K`; otherwise use `f=1`, no condensation, and
   ordinary hot heating/cooling. Existing cold clouds can continue to form
   stars and evaporate while `rho>rho_th`. A truly single-phase cell has
   `s=0`. SH03 motivates the hot-temperature requirement on p. 292, but
   this exact sign guard/event policy is an engineering specification.
   A negative cooling rate is never used to manufacture a positive cloud
   growth rate. This is a density/temperature model switch, not a numerical
   evaluation of the general Field instability criterion.
4. Treat changes of the density, temperature or cooling-sign branch as
   source events: split/redo the trial, reevaluate the branch, and record
   the crossing. Do not repeatedly repartition an already multiphase cell
   to equilibrium. If clouds are exhausted, enter the single-phase branch
   at conserved energy; do not divide by a vanished phase mass.

The background-dependent ordinary thermal equilibrium need not lie exactly
at `10^4 K`. Threshold continuity is with the **declared** `u_4` reference;
also report continuity against the backend's actual ordinary equilibrium.
If that difference matters for the isolated-disk fixture, choose a separately
named calibration using the actual ordinary equilibrium and review it before
the run. Do not add heat or a floor to conceal it.

## 5. Cooling, heating and ionization package

The selected proposed backend is `primordial-kwh96-cen92-fg20-v1`, fully
specified in [COOLING_RATES_SPEC.md](COOLING_RATES_SPEC.md): the atomic
network below with correction C1, signed Cen (1992) CMB exchange using
Fixsen/CODATA constants, and the author's **unrescaled FG20 effective
default** six-rate table. For the first isolated reference freeze `z_uv=0`.
This deliberately named replacement has actual downloaded, hashed bytes;
it does not recover historical SH03 UV identity. Its archive/README supports
scientific simulation use but supplies no verified redistribution license;
the external-input boundary and remaining packaging dependency are explicit
in the cooling contract. No rate/backend or threshold has been executed.

SH03 p. 292 specifies primordial H/He in ionization equilibrium with a
modified Haardt & Madau (1996) UV background, reionizing near `z~6`, with
details referred to Davé et al. (1999). It does not print a complete
machine-readable UV/rate table. Neither an arbitrary file named `TREECOOL`
nor a modern UV model can establish historical source equivalence.

The full [Katz, Weinberg & Hernquist (1996) published text](https://articles.adsabs.harvard.edu/pdf/1996ApJS..105...19K)
was consulted, especially section 3.1-3.2, pp. 24-25, Tables 1-2 and
Eqs. (23)-(40). Its [arXiv v1](https://arxiv.org/pdf/astro-ph/9509107v1) is
also archived, but its PDF text extraction corrupts mathematical glyphs;
OCR is not an accepted coefficient transcription. KWH adopts primordial
`X=0.76`, `Y=0.24` (p. 25). The required contract is:

| Input | Required content and primary locator | Verification boundary |
| --- | --- | --- |
| Atomic cooling | H I and He II collisional excitation; H I, He I, He II collisional ionization; H II, He II, He III radiative recombination; He II dielectronic recombination; free-free emission with ionic charge factors. KWH Table 1, p. 24; Gaunt factor Eq. (23). | Coefficients visually transcribed below; the published dielectronic sign discrepancy is explicitly corrected from primary sources. Independent review and REANA rate fixtures remain required before executable acceptance. |
| Ionization coefficients | Collisional ionization and radiative/dielectronic recombination rates, KWH Table 2, p. 25; rate balance Eqs. (25)-(28), number/charge conservation Eqs. (30)-(38). | Coefficients and equilibrium system transcribed below; no executed rate comparison is claimed. |
| Photoionization/heating | For `i=H I,He I,He II`, provide `Gamma_i=integral[4*pi*J_nu*sigma_i/(h*nu)] dnu` [s^-1] and `epsilon_i=integral[4*pi*J_nu*sigma_i*(h*nu-h*nu_i)/(h*nu)] dnu` [erg/s per target atom]. Heating is `sum n_i*epsilon_i`; KWH Eqs. (29), (39)-(40). | The `4*pi`, thresholds, spectrum, cross sections, interpolation and redshift range must be pinned together. Cross sections referred to Osterbrock (1989) by KWH; no complete cross-section audit is claimed. A verified six-rate UV table can avoid implementing spectral cross sections. |
| Ion fractions and EOS | `n_H=X*rho_h/m_p`, `n_He=Y*rho_h/(4*m_p)`, species nonnegative, nuclear totals and charge neutrality; solve H/He ionization equilibrium and `T=(gamma-1)*mu(T)*m_p*u_h/k_B` self-consistently. | Tolerance and all species residuals must be tested, including the neutral limit without division by zero `n_e`. Thermal equilibrium is not assumed. |
| Compton term | KWH Eq. (24), p. 24: `C_Compton=5.41e-36*n_e*T*(1+z_uv)^4` [erg/cm^3/s], a historical high-T approximation. Selected reference instead uses signed Cen Eq. (17), p. 346, with `T_CMB,0=2.72548 K` and CODATA 2022 constants. | The primary derivation and exact normalization are in the cooling contract. Do not add both laws; signed CMB heating/cooling avoids an invented low-T extension and is explicitly a model amendment. |
| Background history | [Haardt & Madau 1996](https://arxiv.org/abs/astro-ph/9509093), DOI `10.1086/177035`; [Davé et al. 1999](https://arxiv.org/abs/astro-ph/9807177), DOI `10.1086/306722`, arXiv pp. 5-6. Davé describes an updated mean quasar spectral slope `-1.8` versus `-1.5` and discusses model-dependent normalization. | Those prose choices do not uniquely recover historical SH03 rates. The new reference selects FG20 default as an explicit replacement, with primary author table/version/units/domain/interpolation and license limitations in the cooling contract. Historical equivalence remains unavailable. |

The first coefficient package must supply the audited analytic rates and
source-tracked UV input, or a licensed, hashed, unit-documented alternative
table with independent values. The selected UV archive's external-input/
redistribution boundary is described in the cooling contract. Tables need
axes (`rho` versus `n_H`, `T` versus `u`, `z`), interpolation rule, validity
domain, ionization convention, signs, abundance assumptions and per-channel
rates. Never logarithmically interpolate a signed net rate across zero:
interpolate nonnegative cooling/heating channels separately and subtract.
Do not extrapolate outside a table without a named, source-supported rule;
return a domain error and retain the failed input.

### Visually checked primordial atomic rate transcription

This is an equation contract, not executed code or a table of computed rate
values. Let `T` be in kelvin, `T_n=T/10^n K`,
`D5=1+sqrt(T_5)`, `D6=1+T_6^0.7`. The following Table 1 factors multiply
the stated density product, with densities in `cm^-3`, to give volumetric
cooling in `erg/cm^3/s`:

| Process | Factor | Density product |
| --- | --- | --- |
| H I excitation | `7.50e-19*exp(-118348.0/T)/D5` | `n_e*n_HI` |
| He II excitation | `5.54e-17*T^(-0.397)*exp(-473638.0/T)/D5` | `n_e*n_HeII` |
| H I ionization | `1.27e-21*sqrt(T)*exp(-157809.1/T)/D5` | `n_e*n_HI` |
| He I ionization | `9.38e-22*sqrt(T)*exp(-285335.4/T)/D5` | `n_e*n_HeI` |
| He II ionization | `4.95e-22*sqrt(T)*exp(-631515.0/T)/D5` | `n_e*n_HeII` |
| H II radiative recombination | `8.70e-27*sqrt(T)*T_3^(-0.2)/D6` | `n_e*n_HII` |
| He II radiative recombination | `1.55e-26*T^(0.3647)` | `n_e*n_HeII` |
| He III radiative recombination | `3.48e-26*sqrt(T)*T_3^(-0.2)/D6` | `n_e*n_HeIII` |
| He II dielectronic recombination, corrected sign | `1.24e-13*T^(-1.5)*exp(-470000.0/T)*(1+0.3*exp(-94000.0/T))` | `n_e*n_HeII` |
| Free-free | `1.42e-27*g_ff*sqrt(T)` | `n_e*(n_HII+n_HeII+4*n_HeIII)` |

KWH Eq. (23) is
`g_ff=1.1+0.34*exp(-(5.5-log10(T))^2/3.0)`. Sum the ten channels plus
the declared Compton term and subtract photoheating to obtain `Lambda_net`.
There is no molecular, metal or metastable-helium cooling channel added from
another source. In particular, Black's larger Table 3 contains processes
that KWH does not retain; consulting it for a sign does not import its full
network.

**Source discrepancy C1:** KWH's **published** Table 1, p. 24, prints
`exp(+470000.0/T)` in the dielectronic cooling term. KWH arXiv v1 Table 1,
PDF p. 13, instead prints `exp(-470000.0/T)`, as does Black (1981),
[Table 3, p. 557](https://articles.adsabs.harvard.edu/pdf/1981MNRAS.197..553B),
the primary source cited by KWH. Black's Eq. (9), p. 556, and KWH Table 2
also have the negative sign in the associated recombination coefficient.
The proposed reference therefore uses the **negative** sign, explicitly
labelled `kwh96-dielectronic-sign-correction-v1`. This is a primary-source
correction, not faithful evaluation of that printed positive exponent; a
separate source reviewer must confirm it before physical execution.
No later correction to the coefficient magnitude is adopted without another
primary-source audit.

KWH Table 2 coefficients in `cm^3/s` are:

```text
alpha_HII   = 8.4e-11*T^(-1/2)*T_3^(-0.2)/D6
alpha_HeII  = 1.5e-10*T^(-0.6353)
alpha_d     = 1.9e-3*T^(-1.5)*exp(-470000.0/T)
              *(1+0.3*exp(-94000.0/T))
alpha_HeIII = 3.36e-10*T^(-1/2)*T_3^(-0.2)/D6
c_HI        = 5.85e-11*sqrt(T)*exp(-157809.1/T)/D5
c_HeI       = 2.38e-11*sqrt(T)*exp(-285335.4/T)/D5
c_HeII      = 5.68e-12*sqrt(T)*exp(-631515.0/T)/D5
```

Here `c_i` is collisional ionization, distinct from photoionization
`Gamma_i` [s^-1]. A numerically safe algebraic equilibrium system equivalent
to KWH Eqs. (25)-(38), without forming `Gamma_i/n_e`, is

```text
(c_HI*n_e + Gamma_HI)*n_HI = alpha_HII*n_e*n_HII
(c_HeI*n_e + Gamma_HeI)*n_HeI
    = (alpha_HeII+alpha_d)*n_e*n_HeII
(c_HeII*n_e + Gamma_HeII)*n_HeII = alpha_HeIII*n_e*n_HeIII
n_HI+n_HII = n_H
n_HeI+n_HeII+n_HeIII = n_He
n_e = n_HII+n_HeII+2*n_HeIII
```

Solve the nonnegative physical ionized root with normalized residual checks;
in the zero-UV limit the collisional-equilibrium ratios are taken by
continuity from positive electron abundance, not the spurious all-neutral
zero-electron algebraic solution at arbitrarily high `T`. Obtain
`mu=rho_h/[m_p*(n_H+n_He+n_e)]` and solve its temperature/energy relation
self-consistently. Table coefficients specify the model but do not prove
accuracy outside their physical approximation. Black p. 557 states a
`5e3-5e5 K` applicability interval for his unmodified expressions; KWH
explicitly applies Cen's high-temperature modifications. The new package
must register its KWH fit domain and review high-T use and optical-thin/
low-density assumptions, with no extrapolation to molecules, optically thick
gas or arbitrarily relativistic temperatures. Those applicability checks
remain part of rate-package source review. The selected signed Cen CMB law
does not require the historical KWH approximation's `T>>T_CMB` restriction.

The historical SH03 UV table is **not recovered**. The selected replacement
is `fg20_treecool_eff_default.dat` from the author's 2020-10-27 archive,
SHA-256 `c6e6030be92c6965c019c53915f31661782eb2cafed058cf9672b7efefc24aaa`.
The `.68` heating-rescaled and optically thin members are different models,
not silent updates. Six tabulated photo rates avoid a missing spectral
cross-section implementation. An explicitly named zero-UV collisional
fixture uses `Gamma_i=epsilon_i=0` but does not replace the selected galaxy
background. No numerical threshold or successful thermal evolution is
fabricated. Independent source/domain review, the declared UV external-input
policy and prospective REANA rate/threshold fixtures still precede physical
G3 use; they do not prevent completing pure interfaces/equation kernels.

Metals do not change primordial rate abundances or cooling in the reference.
`X=.76,Y=.24` are **effective primordial thermal fractions**, even with a
passive bookkeeping `Z`; they are not physical H/He fractions to be added
to Z. `X+Y+Z` is not asserted to be a species-fraction sum. No extra baryon
or gravity mass is created. Section 7's registered range/failure policy
limits this approximation; renormalizing X/Y by `(1-Z)` would be a separately
sourced/recalibrated closure, not a correction to this one.

## 6. Parameters: publication facts versus proposed configuration

| Quantity | Verified published statement | Proposed reference setting/status |
| --- | --- | --- |
| `beta` | SH03 p. 291: Salpeter slope `-1.35`, mass interval `0.1-40 M_sun`, massive stars `>8 M_sun` gives `0.106`; typically use `0.1`. | `0.1`, explicit calibration choice consistent with the typical value. |
| SN budget | p. 291: `10^51 erg/SN`, approximate `epsilon_SN=4*10^48 erg/M_sun`, `T_SN~10^8 K`; exact Eq. (2) relation above. | Pin `T_SN=10^8 K` using `mu_SN`, derive `u_SN` and `epsilon_SN`; treating this approximate published temperature as an exact round number is engineering. Do not also enforce the approximate `4*10^48` as an independent exact constraint. |
| `T_c` | p. 292: typically about `1000 K`, insensitive for `T_c<<10^4 K`. | `1000 K` and neutral `mu_c`; this fixed cold reservoir is a physical model parameter, not a cell pressure floor. |
| `A0` | p. 294, Eq. (22): `T_SN/A0~10^5 K`, hence `A0~1000`. | `1000`, with full Eq. (11) in calculations. |
| `t0` | p. 294 / Fig. 2 and p. 295: `2.1 Gyr` gives the fiducial disk calibration; examples also use `8.4` and `0.53 Gyr`. | `2.1 Gyr`; a calibration knob, not a universal star-formation constant. |
| `rho_th` | p. 294, Eq. (23), determined from pressure continuity and cooling. | Derived only after rate review; proposed full-rate-continuity amendment in section 4. No adopted numerical value yet. |
| `y_star` | p. 298 defines yield per locked mass; p. 308 uses `0.02` in a displayed enrichment result. | `0.02` is a proposed constant-tracer calibration, not a detailed IMF/element yield table or a universally exact solar abundance. |
| `N_g` | p. 298, section 5.2: roughly `1-4` generations discussed. | Not used by the deterministic first profile. A mass-resolution choice for a future stochastic profile. |
| `gamma`, `X,Y` | Monatomic primordial gas conventions; KWH p. 25 gives `X=.76,Y=.24`. | `gamma=5/3`, rates use those abundances. |

The [AREPO public GitLab parameter page](https://gitlab.mpcdf.mpg.de/vrs/arepo/blob/master/documentation/source/parameterfile.md)
was located and its indexed contents checked on 2026-11-22. A direct raw
download and commit-history request were blocked by a bot challenge; the
saved `.md` response is **HTML, not source Markdown**. It is retained and
labelled as a failed retrieval. The official
[AREPO 1.0 hosted manual](https://arepo-code.org/wp-content/userguide/parameterfile.html#cooling-and-star-formation)
and its [page source](https://arepo-code.org/wp-content/userguide/_sources/parameterfile.md.txt)
were retrieved and hashed. Its footer says 2019 and no source commit is
exposed in the downloaded page. Therefore these are pinned consulted manual
bytes, **not a verification of the current master implementation/defaults**.

The manual maps `FactorSN` to `beta`, `FactorEVP` to evaporation,
`TempSupernova`, `TempClouds`, and `MaxSfrTimescale` to their SH03 concepts;
it documents `CritPhysDensity` in `cm^-3`, `TreecoolFile`, and an extra
`TemperatureThresh` hot-gas eligibility control. It does not by itself
resolve which number-density species is used for every conversion or prove
that a numeric value is a default. Our contract uses explicit `rho` in mass
units and `n_H=X*rho/m_p`. The exact AREPO current-source threshold,
temperature guard and parameter normalization remain **unverified** and are
not copied. The manual also documents numerical `MinGasTemp`/`MinEgySpec`
floors; these are not imported as multiphase physical closure.

No external code is copied and no third-party source license compatibility
is claimed. Mathematics is independently implemented; redistributing rate
tables, copying code, or adding a dependency needs a separate license audit.
Illustris/TNG winds, cooling, enrichment and eEOS modifications require
their own versioned publication/source contract.

## 7. Conservative spawning, recycling and source ledgers

During a local source interval, take the cell volume and bulk velocity
`v=p_g/m_g` as fixed. This is an operator split, not a claim that a moving
cell volume is constant over a whole hydro step. Integrate gross formation
`F=integral(m_c/t_star)dt`, evaporation
`E_ev=integral(A*beta*m_c/t_star)dt`, and condensation
`C=integral[V*(1-f)*Lambda_net/(u_h-u_c)]dt` with the **same quadrature**
as the thermal equation. `A` generally varies, so do not replace its
integral by an unrelated final `A*beta*F`.

```text
L=(1-beta)*F; R=beta*F
m_c' = m_c - F - E_ev + C
m_h' = m_h + R + E_ev - C
m_g' = m_g - L
m_star_new = L
p_g' = p_g - L*v;   p_star_new = L*v
U_th' = U_th + Q_SN - Q_rad - L*u_c
Q_SN = beta*u_SN*F
Q_rad = integral(V*Lambda_net dt)       # signed: negative for net heating
```

The prompt return is an internal mass cycle, not a second mass addition
after subtracting only `L` from gas. In a conceptual gross ledger, move
`F` cold gas into the birth population, return `R` to hot gas, and leave
`L` collisionless. In the stored state, materialize only `L`. Both views
must yield identical mass and momentum. Evaporation and condensation
transfer internal phase mass and phase energy, with no net momentum kick.

Each **actual successful source subinterval** with `L>0` plans exactly one
independent deterministic packet, including subcycles and branch-event
splits. An interval with `L=0` creates no packet. The entire source
transaction and particle materialization occur **only at an accepted full-step
endpoint `t_global_end`**, at the gas volume centroid used by the gravity source,
with velocity `v` of that endpoint source transaction and a unique birth ID.
The star joins the ordinary collisionless force/integration path starting
there, with `at_time=activated_at=t_global_end`; it receives no preceding
fractional kick **or drift**. Keep each actual
`formation_interval=[formation_start,formation_end]` and use the stable
midpoint expression `formation_start+(formation_end-formation_start)/2`
for `formation_time`, explicitly a first-order population-age estimate.
Validate finite ordered times and
`formation_start<=formation_time<=formation_end<=activated_at`.
The final inequality may be strict: a first subcycle can end before a
second subcycle, while both activate together. Never overwrite its interval
with the global-step interval or merge packets to satisfy an old validator.
The source plan accumulates pending packets without placing them in the
live force catalog. Atomic endpoint acceptance commits **all** gas deltas,
packets, IDs, source counters, ledgers and force-cache invalidation together.
No local plan attempt mutates the live accepted state. A rejected local
interval has no deltas or packet in its parent's private source plan;
previous successful pending intervals can be retained only within that
same uncommitted outer trial. An outer source/hydro/gravity rejection
discards the entire pending plan/allocations and restores the accepted state
exactly. Delayed returns are disabled, so
this metadata does not define an age-dependent return algorithm.
`birth_mass=L` means
long-lived mass after instantaneous recycling, `current_mass=L` remains
constant in this profile, and separate `gross_formed_mass=F` and
`prompt_returned_mass=R` prevent IMF/return ambiguity. Store birth metallicity,
parent gas ID, model/parameter hash and source transaction ID. Existing
stars must have explicit configured formation epochs; do not infer measured
ages or silently fill an unknown epoch.

**Why deterministic packets first:** finite-phase cooling/heating and
recycling then share exactly the same integrated `F` and conserve each
event, without storing collisionless mass in a gas element waiting for a
spawn. Variable packet masses and particle count growing with source
interval count are explicit costs. No packet merging or minimum-mass
suppression is allowed in the reference; timestep/softening convergence
must establish adequate collisionless sampling before disk use. This is a
documented alternative to SH03 Eq. (39), not a claim of stochastic equivalence
at fixed resolution. The first disk is a small reference, not the production
performance target. A code that cannot afford it must implement/review the
stochastic extension below before proceeding, not retain hidden stellar mass.

### Metals and non-thermal energy accounting

For a source-only closed box, use the same locked `L` and a constant yield.
The continuous Eq. (40) integrates to

```text
Z_g' = Z_g + y_star*ln(m_g/m_g')
M_Z_g' = m_g'*Z_g'
M_Z_star_new = M_Z_g + y_star*L - M_Z_g'
Z_star_new = M_Z_star_new/L
```

This is an analytically integrated engineering discretization of the closed
box, and the deterministic packet has the mass-weighted metallicity of its
formation interval. Set `r=L/m_g` and compute
`Delta Z=-y_star*log1p(-r)`. For packet metallicity use
`Z_star=Z_old+y_star*b(r)`, where
`b(r)=1+(1-r)*log1p(-r)/r`. For `0<r<=2^-8`, use the explicit stable series
`b(r)=sum_(k=1..8) r^k/[k*(k+1)]`, whose positive remainder is bounded by
`r^9/[90*(1-r)]`; above that switch use the log1p expression. Form packet
metal mass as `L*Z_star`, rather than subtracting nearly equal gas metal
masses and dividing by L. At `L=0` use the unchanged gas metals and no packet,
without evaluating `b(0)`. Retain the complement identity as an independent
ledger check, not a post-solve residual correction. Newly produced
`y_star*L` is bookkeeping within the existing baryon mass, not an additional
gas/gravity mass or a claim of separately conserved physical H/He species.
Retain inherited, locked, prompt-return,
newly synthesized and advected metal ledger entries separately. Verify
`Delta(M_Z_g+M_Z_star)=y_star*L` and all mass fractions are admissible.
For a passive primordial thermal model, also record its tracer approximation
as in section 5. With `y_star=0`, metal mass is strictly conserved. This
exact closed-box update does not apply across simultaneous advective mixing:
transport and local sources have distinct ledgers.

Freeze `passive-primordial-tracer-Z002-v1`: `0<=Z<=.02` for initial gas,
new gas and every packet, with the stated constant `y_star=.02` reference
and `y_star=0` control. This ceiling limits the tracer to at most two percent
of existing baryon mass; it is an **engineering scope bound**, not a primary
source accuracy threshold or proof that metal cooling is negligible.
Even at this Z the omitted thermal physics may matter, so the first runs
test the specified approximate model. Initial violation is
`TracerRangeError`; an evolved/enriched violation is `TracerRangeExceeded`.
Retain the offending state/request and last accepted state, reject the whole
outer transaction and stop that configured evolution rather than clip Z,
dilute it, renormalize thermal X/Y, or indefinitely retry a genuine range
crossing. For `y_star>0`, the source-only allowed locked fraction satisfies
`r<=-expm1(-(.02-Z_old)/y_star)`; this is a diagnostic bound, not mass
suppression. No new metals are separate gravity sources. Changing this range
or thermal composition requires a new profile and applicability review.

The gas total-energy source includes the thermal change above and the kinetic
energy removed with `L`, namely `-L*|v|^2/2`. The newborn star receives that
same kinetic energy. A collisionless star has no hydrodynamic thermal state;
export `L*u_c` into a cumulative **unresolved stellar binding/thermal energy
ledger**, not into an extra gas heating event. With no gravity/transport:

```text
Delta(E_gas_total + K_stars + E_star_unresolved) + Q_rad - Q_SN = 0
```

In MHD, the source leaves `A`, its mean flux, `B`, volume and magnetic energy
unchanged. It removes no arbitrary fraction of magnetic energy with stellar
mass. The plasma mass-to-flux ratio can change; this is the explicitly
assumed unresolved flux-retention model, not a claim about protostellar
magnetic flux transport. Any subsequent cell deletion/remap needs the
accepted M2 vector-potential transfer contract. The first profile forbids
complete gas-cell conversion and uses fractional-step mass limits so a
positive gas/geometry state remains.

At birth, use the same position and the agreed softening/source policy as the
removed gas contribution. Record the complete before/after gravitational
potential-energy change as `Delta W_birth`, including co-located mutual/self-
exclusion representation changes **even with identical softenings**, and any
gas/star softening or quadrupole difference. It is not SN energy and cannot
be hidden in radiation or used to replace the raw energy history. The gravity
contract's representation-error convergence gate still applies; the gravity
integrator supplies its own work/energy residual.
For a joint endpoint with packets `L_i` from one parent, common position and
common fixed Plummer epsilon, manual GP-2 algebra gives
`Delta W=-(G/epsilon)*[(m_g0-sum L_i)*sum L_i + sum_(i<j)L_i*L_j]`.
The second sum must include **all same-step packet-packet pairs**. This is
only a coincident equal-softening fixture formula; the production ledger
uses independent complete before/after GP-2 sums including gas-new,
new-new, old stars, dark matter, other gas and changes of old-source terms.
Sequentially summing incomplete one-packet jumps is not that joint ledger.
Retain raw H and the gravity contract's cumulative
`sum abs(Delta W_representation)<=1e-4*abs(W_initial)` gate, plus mass,
source-substep and epsilon refinement. Packet-count dependence is measured,
not absorbed into SN/radiation or removed by implicit merging.
Momentum and center-of-mass position transfer are exact for coincident
centroids; angular momentum uses this declared source-position approximation
and must be measured under spatial refinement.

**No double counting:** in the finite-phase profile `Q_SN` is inserted once
in Eq. (7), creates the hot/cold pressure structure, and drives evaporation
through Eq. (10). Stars from that population have zero additional prompt
thermal/kinetic SN injection. In a future equilibrium profile, the same SN
budget is already represented by the closure; its diagnostic `Q_SN` is not
a second resolved source. An added wind/resolved-SN channel must name an
energy partition, debit the shared budget consistently, and recalibrate/test
the closure or explicitly introduce a separate additional physical source.
SH03's phenomenological wind extension is not automatically a conservative
budget split with an unchanged EOS, so it is not silently enabled here.

### Counter-based stochastic extension (proposed, not the first profile)

The published equilibrium method has constant-interval hazard
`lambda=(1-beta)*x/t_star`, target locked star mass `m_s=m0/N_g` and

```text
D = m_g*(-expm1(-lambda*dt))
p = D/m_s                                                 [Eq. 39]
E[Delta M_star]=p*m_s=D
Var(Delta M_star)=m_s^2*p*(1-p)                            # one trial
```

It spawns at most one generation per trial and converts the residual gas on
the final generation (p. 298). For a frozen hazard this is the exact
exponential expected depletion, not simply `lambda*m_g*dt`. If `m_s<m_g`,
the one-trial limit `p<=1` is equivalent to
`lambda*dt<=-ln(1-m_s/m_g)`. Proposed stricter control is `p<=0.1`;
subdivide the interval and recompute state/rates, never clip `p` to one.
Variable hazards require integrated `H=integral lambda dt` and consistent
source quadrature. Sampling an independent Poisson count and capping it at
the available mass biases expectation and is not this law.

Equation (39) is **not drop-in compatible** with finite-phase energy ledgers:
it removes a net equilibrium mass while SN regulation is treated smoothly.
For a future finite-phase stochastic variant, use a separately named
`finite-phase-packet-tauleap-v1`: freeze the local rates over a source
subinterval, choose a gross packet `F_p=m_s/(1-beta)`, and Bernoulli
`p=(m_c/t_star)*dt/F_p`. An event applies the *entire coupled transaction*
`F_p,R_p,E_ev_p,Q_SN_p` and locked `m_s`, with inherited metals removed
and `y_star*m_s` added consistently. Require before drawing
`(1+A*beta)*F_p<=0.1*m_c`, `m_s<=0.1*m_g`, `p<=0.1` and admissible
hot energy; otherwise lower packet mass or subdivide/reject the plan.
No event can overdraw the cold phase. Condensation and ordinary cooling are
integrated separately with their own ledger. Frozen-rate event expectations
then reproduce the published differential sources to first order in `dt`;
they do not reproduce the Eq. (39) exponential finite-step law. Demonstrate
convergence as both `dt` and packet mass decrease before replacing the
deterministic profile. Do not attach smooth SN heating on top of event SN
heating. Packet-count efficiency is a later engineering decision.

Reproducible random access can use a domain-separated SHA-256 counter stream,
independently specified here (no imported RNG code):

```text
digest = SHA256("openmhd-sf-uniform-v1\0" || seed[32]
                || parent_cell_id_u128_le || accepted_source_counter_u128_le
                || draw_index_u64_le)
r = little_endian_u64(digest[0..8])
U = (r >> 11) * 2^-53                                     # [0,1)
event iff U < p
```

Use explicit fixed byte widths; hash the stream definition into provenance.
Canonical identities are `EntityId { namespace:u64, counter:u64 }`, wrapped
as distinct `CellId`, `ParticleId`, and `EventId` types, serialized as 32 hex
digits. For hashing, `parent_cell_id_u128_le` means the two fixed-width
little-endian fields in namespace-then-counter order, not a platform-native
struct memory image. A checkpointed **serial monotone allocator** assigns
particle and event IDs in sorted transaction order; hashes never allocate
canonical entity IDs. Store parent/birth-ordinal lineage separately. The
deterministic profile uses the same allocator without random draws.
Commit counters/IDs only when the entire source/hydro transaction is
accepted; rejected trials do not consume RNG state or create particles.
Restart stores seed, counters, lineage, model and rate hashes. Sorting
transactions by stable ID and using a fixed reduction order gives scheduling
and same-step restart parity. Timestep changes/refinement change event
partitions, so byte-identical individual star histories are **not promised**:
their expected mass/rate and statistical convergence are the contract.
Refined children would receive canonical allocated IDs and separate parent/
child-ordinal lineage, under an accepted refinement policy. Refinement is
disabled initially.

## 8. Integration and proposed Rust boundaries

All names below are **new design**, not claims that crates or APIs exist.
Keep cooling, phase algebra, source planning and mutation separate. No
changes to the existing numerical source are part of this document.

```rust
// Proposed crate: galaxy-ism (Rust 2024, f64, no global mutable RNG).
// Shared UnitSystem, CellId/ParticleId/EventId and serial ID allocator.
struct IsmParameters { /* beta, u_c, u_sn, a0, t0, threshold, yield, hashes */ }
struct RadiationState<'a> {
    // z_uv, public identity receipt, borrowed private photo rates;
    // not Serialize/Debug; no UV rate vector in config/checkpoint/logs
}
struct CoolingInput { /* rho_hot_cgs, u_hot_cgs, primordial abundance */ }
struct CoolingEvaluation {
    // nonnegative cooling/heating channels, signed net loss, T, mu,
    // ion fractions, residuals, optional source-verified derivatives
}
trait PrimordialRates {
    fn evaluate(&self, x: CoolingInput, uv: &RadiationState<'_>)
        -> Result<CoolingEvaluation, CoolingError>;
}
struct PhaseState { /* m_g, m_c, U_th, volume, metal_mass, branch */ }
struct Equilibrium { /* x, u_hot, u_eff, pressure, tau, validity */ }
struct SourcePlan {
    // immutable input identity + actual successful source subintervals
    // + one pending birth per nonzero-L subinterval + phase increments
    // + all integrated source channels + proposed counter updates
}
fn equilibrium(/* parameters, rho, rates, uv, approximation label */)
    -> Result<Equilibrium, ModelError>;
fn plan_source(/* state, params, rates, uv, dt, stable id/counters */)
    -> Result<SourcePlan, SourceError>;
fn validate_plan(/* old state, source plan, scales */) -> Result<(), SourceError>;
fn commit_source(/* gas state, collisionless-star store, source plan */)
    -> Result<(), CommitError>;
```

`commit_source` is atomic across phase variables, conservative gas state,
metal state, particle insertion, counters and ledgers. Failure leaves the
old state unchanged. Prepared IDs for GP2 ordering are a dry run from the
checkpointed allocator snapshot; only atomic outer-step acceptance advances
that allocator. Concurrent plans may not reserve or consume IDs. Cooling
errors are distinct from no-equilibrium,
ineligible, source-step-too-large, geometry/transfer and linear-solve errors.
The ISM crate never owns a mesh, computes a force or starts a thread pool.
Pass immutable local quantities from M2/G2; independent calls may use the
caller's Rayon pool later. Unit conversion occurs once at the interface.

The first deterministic integrator is a conservative **backward-Euler local
source solve**, with hydro/transport and source splitting documented as
first-order in coupled time accuracy. At fixed `V`, solve the three
equations in section 7 for `m_c'`, `m_h'`, `U_th'`, using `s'`, `A'`,
`t_star'`, `Lambda_net'`, `u_h'` evaluated at the new state and
`F=dt*m_c'/t_star'`, `E_ev=dt*A'*beta*m_c'/t_star'`,
`C=dt*V*(1-f)*Lambda_net'/(u_h'-u_c)`. The density in `A'`/`t_star'` is
`(m_c'+m_h')/V`; `f` is fixed only within a located branch interval.
Use a safeguarded residual solve in positive variables/brackets; reject
ambiguous/unbracketed roots, nonconvergence and out-of-domain rate calls.
Do not accept a Newton iterate simply because an iteration cap was reached.
Conservation comes from the common integrated transactions, not from a
post-solve renormalization. A separate higher-accuracy oracle is required
for REANA temporal tests; it must not call this production stepper.

Proposed local accuracy limits are `L<=0.1*m_g`,
`F+E_ev<=0.1*m_c` when a cold reservoir exists,
`abs(Delta m_h)<=0.5*m_h`, and
`abs(Delta U_th)<=0.1*max(U_th,m_g*u_c)` away from exact equilibrium.
The latter is an accuracy scale, not a thermal floor; it is never written
into the state. Use estimated rates to propose `dt`, then check the actual
accepted increments. For zero/tiny reservoirs use creation-aware absolute
scales fixed in section 8a, rather than divide by zero or forbid physical
creation from zero. Stiffness can require subcycling or the global step to
shrink; count both. Root tolerance is proposed `1e-12` in each scaled source
residual, with acceptance-budget tolerance checked independently.
All constants here are engineering proposals and must be registered in the
future packet before execution, not represented as SH03 values.

Sources operate once at each accepted full-step endpoint, outside the
existing MHD Heun stages in this first-order split. Do not inject at both
stages without weights. Finish the agreed G2 gravity kicks/drift for the
pre-existing entities, then commit endpoint sources and new particles;
there is no retrospective midpoint gravity kick for newborn stars. Preserve
`formation_time` and `activated_at` as different fields. A source/hydro/gravity
retry rolls back all births and
ledger changes. A second-order Strang/implicit method is a later named
change requiring temporal evidence, not inferred from the hydro integrator.

### 8a. Frozen admissibility, implicit roots and located source events

The following is `conservative-be-source-search-v1`, an engineering policy
to be independently implemented/reviewed. Backward Euler and a small
residual do **not** prove positivity, uniqueness or physical stability.
Every accepted root must satisfy all state, branch, domain, timestep,
tracer and ledger conditions; none is repaired by clipping or borrowing a
previous root. A strictly all-cold cell or `u_h<=u_c` is invalid for the
two-phase solve. Zero-cloud ordinary gas is valid with F=0 and no cloud
division. A one-sided limiting RHS fixture is not permission to call cooling
at zero hot mass.

Reduce the proposed three-equation BE solve algebraically before searching.
Let `d0=u_h0-u_c`, `m0=m_g0`, and for a trial F define

```text
m(F)=m0-(1-beta)*F; rho(F)=m(F)/V
t(F)=t0*(rho(F)/rho_th)^(-1/2); A(F)=A0*(rho(F)/rho_th)^(-4/5)
c(F)=F*t(F)/dt; h(F)=m(F)-c(F).
```

For fixed `f=0`, eliminating the cooling integral from the mass/energy
identities gives, by manual algebra,

```text
d(F)=[m_h0*d0+beta*u_SN*F]/[m_h0+beta*(1+A(F))*F]
R_F(F)=c(F)-m_c0+(1+A(F)*beta)*F
       -dt*V*Lambda(h(F)/V,u_c+d(F))/d(F).
```

Inventory F on `[0,.1*m0/(1-beta)]`, restricting to admissible positive
`h(F),d(F)`, the frozen branch and the stated fraction limits. Endpoint
F=0 is tested explicitly. For `f=1`, first inventory the independent mass
equation `F*[t(F)/dt+1+A(F)*beta]-m_c0=0` on that same finite interval.
For each admissible mass root, `c=m_c0-(1+A*beta)*F`, `h=m(F)-c` and
inventory the thermal residual in **T** on `[1e3,1e8] K`:

```text
R_T(T)=h*[u(T,h/V)-u_c]-m_h0*d0-beta*u_SN*F
       +dt*V*Lambda(h/V,T).
```

Here `u(T,rho_h)` and `Lambda(rho_h,T)` use the fixed-T charge closure;
`f=0`'s energy call additionally needs the unique caloric inversion.
Recover all integrated transfers from that one solution and recheck the
original three residuals. This reduction does not change the supported
SH03 equations. If no admissible root exists, return `NoImplicitRoot`;
if more than one survives, return `MultipleImplicitRoots`; an unresolved
bin is `UnresolvedRootInventory`. In f=1 require the root connected to the
dt=0 initial state without crossing the nearest scalar thermal-equilibrium
barrier in an autonomous cooling-only interval. Such a fixed point is
approached asymptotically, not crossed to another thermal basin.

Use cooling section 4a's certified-bin inventory, with the T grid there.
For F use normalized `F/F_max` nodes `i/1024` (`i=0..1024`) plus `2^-j`
(`j=1..52`), deduplicated and sorted. Require branch continuity by solving
homotopy steps `dt*2^-j`, `j=20,19,...,0`, from the initial state, retaining
the admissible root tube. A different root reached after a fold is not a
continuation. If the starting increment is not resolved, the tube cannot
be certified, or an intermediate step has multiple admissible roots,
reject/halve the source interval. At most 20 such halvings and 4096
successful source subintervals per outer step are allowed; overflow gives
`SourceResolutionLimit`, rolls back the outer trial and requests a smaller
global step. A global retry limit of 20 then fails with the retained input
and cause. Missing source identity, true tracer-range violation and invalid
initial state are terminal errors rather than indefinitely retryable ones.

At the outer step's accepted input freeze `M_ref` to that parent's positive
gas mass and `U_ref=M_ref*u_SN`; these stay fixed through its source
subcycles. Define the positive fixed **specific** energy
`u_ref=U_ref/M_ref=u_SN`; it has SI units J/kg, unlike total U_ref in J.
Let `M_abs=2^-40*M_ref`, `U_abs=M_abs*u_SN`. They are **error
scales**, never mass or energy added to state. For each cold/hot residual
use the maximum of its old mass, trial mass, magnitudes of participating
integrated transfers and M_abs. For the energy residual use the maximum
of old/trial thermal energy, Q_SN, gross cooling/heating integrals,
`L*u_c` and U_abs. Require each normalized residual <=`1e-12`; transfer/
combined ledgers independently meet `1e-10` of the fixed M_ref/U_ref scales.
An unresolved subtraction of hot energy or a nonpositive result is
`PhaseEnergyResolutionError`, not a hot-temperature epsilon.

Fraction controls use the same absolute scales:
`F+E_ev<=.1*max(m_c0,M_abs)`,
`abs(Delta m_h)<=.5*max(m_h0,M_abs)`, `L<=.1*m0`, and
`abs(Delta U_th)<=.1*max(U_th0,U_abs)` away from an exact fixed point.
Always separately require actual positive gas/hot mass, nonnegative cold
mass and valid energy; the absolute scales do not permit overdrawing a
small reservoir. A created-from-zero cold component is an explicit entry/
synthetic case; no production backend call with m_h=0 is made.

Locate density-threshold, hot-T=`1e5 K`, cooling-sign, entry-energy,
cloud-exhaustion and domain events in the attempted source trajectory.
Probe 16 equal time subintervals and bisect every detected event bracket;
an interval enclosure must exclude missed events before accepting the rest.
Re-solve from the same accepted left state at every trial time, not by
linear interpolation of unrelated final states. For an isolated crossing
solve the BE residuals together with the guard `g_event=0`, using dt as the
additional bracketed unknown. Require bracket width
`<=max(2^-40*dt_global,16*ulp(t_global_end))` and guard error <=`1e-10`
of its dimensionally matching scale:

| Event | Guard | Fixed/reference scale |
| --- | --- | --- |
| Density | `rho-rho_th` | `rho_th`, mass/volume |
| Hot temperature | `T_h-1e5 K` | `1e5 K` |
| Net loss | `Lambda_net` | Gross cooling+heating with the cooling contract's same-unit absolute scale |
| Entry | `g=u-u_eff` (specific energy) | Positive fixed `u_ref=u_SN=U_ref/M_ref`, J/kg in SI; **not** U_ref |
| Cloud exhaustion | `m_c` (mass) | Positive fixed `M_ref`, kg in SI; **not** M_abs or a phase-mass floor |

Domain/admissibility events retain their typed input/bound checks. At a
located boundary record incoming/outgoing branch and
direction; reevaluate the outgoing RHS once, with no conservative-state
snap or repeated equilibrium projection. Coalesced events use the order
domain/admissibility check, density exit, cloud exhaustion, entry, then
T/sign switch; ambiguous simultaneous outcomes fail `AmbiguousSourceEvent`.
Do not treat a stationary zero guard as endlessly repeated crossings.
An event root not isolated within 128 bisections, a non-progressing time
within 16 ULPs, or an uncertified interval gives `SourceEventUnresolved`.
Thermal fixed-point barriers use the no-crossing rule above rather than
an artificial finite-time sign-crossing. Hydro-driven density events require
the coupled driver to retry/split its global step consistently; the local
fixed-V routine cannot invent a hydro path. All resulting successful
subinterval packets retain their actual intervals under section 7.

## 9. Prospective REANA fixtures and gates

**None of the cases or thresholds below has been implemented or executed.**
They are proposed measurable gates to be frozen before running new code.
All new unit tests, algebra probes, stochastic sampling and evolutions run
on REANA, including fixtures that could run quickly on this machine. Local
work in this task was primary-source reading, extraction and integrity
checks only. Use one independent case per workflow, explicit resources,
and concurrent submission of ready cases with **no aggregate CPU/memory
cap**. Preflight/build dependencies remain required, and a known failed
required gate prevents escalation to long disk/merger runs. No workflow is
submitted or controlled by this design task.

All workflows pin source/configuration/rate/table hashes, compiler/container,
units, physical boundaries, seed/IDs, timestep controls, resources, raw
histories and reducer source. Proposed shared build preflight: 2 CPU threads,
8 GiB, no nested FFI/BLAS/OpenMP pools; run format, Clippy all targets/features,
workspace tests and build there. Subsequent fixtures reuse the exact binary.
Each case below is a *case family*: every parameter/resolution/seed member
is its own independent workflow, with only dependent reductions waiting.

| Case family and prerequisites | Resources per member | Measurements and proposed acceptance gate |
| --- | --- | --- |
| `ism-algebra`: pure source kernels | 1 thread, 2 GiB | Eq. (1)-(10) mass/energy identities, both `f` branches, beta/A limits, cooling zero/sign, hot/cold zero limits, unit conversions; scaled residual <=`1e-12`; invalid domains rejected with no mutation. Independent hand-derived reference values must accompany the future packet. |
| `ism-rates`: audited coefficients/table only | 1 thread, 2 GiB | Use cooling section 8a's exact T/density/source cases and independent values. Analytic fixtures <=`1e-10` relative plus its absolute scale; interpolation **implementation** agreement <=`1e-12` against an independent formula, not accuracy against an unavailable exact effective UV spectrum; abundance/charge residual <=`1e-12`; signed zero crossing preserved. Missing required private input means blocked, never skipped/pass. |
| `ism-onezone-hot-relax`: frozen nonzero masses/A, `f=0` analytic Eq. (10) oracle | 1 thread, 2 GiB | `u_h(t)=u_h_eq+(u_h(0)-u_h_eq)*exp(-t/tau_h)` for the deliberately frozen-coefficient operator. Production source RHS and separate integrator must reproduce the approach; fitted backward-Euler order >=`.9` on three finest dt values, finest error <=`1e-3`. This operator fixture is separate from evolving phase masses. |
| `ism-onezone-coupled`: constant volume, no forces/transport, audited rates | 1 thread, 2 GiB | Independent high-accuracy integration of full finite-phase Eqs. (5)-(10), cooling/SN/stellar histories, positivity, phase depletion and heating limits. On dt ladder `dt0/2^k`, `k=0..4`, finest scaled state and locked-mass errors <=`1e-3`, fitted finest-three time order >=`.9`, integrated mass/momentum/metal/source-energy residual <=`1e-10`. Freeze `dt0`, final time and oracle tolerance in packet. |
| `ism-equilibrium-threshold`: calibrated backend | 1 thread, 2 GiB | Log-density ladder around `rho_th`; Eq. (18) vs independent quadratic root in exactly quadratic cooling; normalized equilibrium residual <=`1e-12`; full-rate root and Eq. (18) compared with approximation labelled. `full-rate-continuity-v1` energy/pressure jump <=`1e-8` between one-sided limits; published Eq. (23) discrepancy recorded, not erased. No SFR derivative/continuity gate. |
| `ism-branch-crossings`: ordinary/multiphase transitions | 1 thread, 2 GiB | Prescribed compression/expansion around threshold, hot shock then cooling, net-heating sign crossing, no-cloud initialization and cloud exhaustion. Each repartition preserves mass, energy, momentum and metals <=`1e-12`; no repeated equilibrium projection; crossing-time/state differences converge with dt and finest relative error <=`1e-3`. |
| `ism-cooling-limits`: source solver and rate domain | 1 thread, 2 GiB | Analytic constant/exponential cooling fixtures as **manufactured** backends (not physical cooling curves); optically thin atomic cases separately. Stiff trial limits trigger subdivision, not mass/energy clipping; 100% rejected trials leave state/IDs unchanged; no negative mass/energy. Implicit solve never steps over a thermal equilibrium root without its registered event policy. Accuracy <=`1e-3` at finest dt; EXP supplies first-order trend. CONSTANT supplies exact algebra/ledger evidence with no meaningful fitted truncation-error slope. |
| `ism-ledger`: deterministic and future event paths | 1 thread, 2 GiB | Every birth plus recycling, evaporation, cooling and condensation satisfies section 7; closed box `Z=Z0+y*ln(M0/Mg)` and stellar metal complement <=`1e-10`; mass, each momentum component, kinetic transfer, cold-energy export and SN/radiation combined budget <=`1e-10`. Test boosts with a nonzero momentum scale and source `B` unchanged. |
| `ism-stochastic-expectation`: only after stochastic variant implemented | 1 thread, 2 GiB | Fixed planned `p=.01,.1`, independent seeds, `10^6` Bernoulli trials per member; empirical locked mass within `5*sqrt(N*p*(1-p))*m_s` of expectation, variance within 2% where expected successes >=`10^4`. Eq. (39) exponential and finite-phase tau-leap expectations assessed separately. Freeze seed list; no retrying seeds until passing. |
| `ism-stochastic-refinement`: accepted sampler | 1 thread, 4 GiB | Packet masses `m_s,m_s/2,m_s/4`, dt caps `dt,dt/2,dt/4`, fixed total gas mass and physical rates, >=64 preregistered seeds. Ensemble mean SF histories agree with deterministic reference within five standard errors plus 1% discretization allowance; variance declines consistently with packet mass. Report fitted changes and all seeds; do not promise matching individual births. |
| `ism-restart-thread-timestep`: accepted source implementation | 1 or 4 threads, 4 GiB | Same logical dt sequence: uninterrupted/restart and thread-order permutations have identical birth IDs, transactions and state; same source input evaluates deterministic ordering. Reject/retry produces same committed plan as a directly accepted matching trial. dt ladder controls coupled state/SFR error, not only integrated mass; finer step comparison <=1% and first-order trend before disk use. |
| `ism-isolated-layer`: G2 + source/rate gates | 2 threads, 8 GiB | Solve a self-gravitating vertical sheet with the declared EOS independently; compare vertical density, pressure, scale height and integrated SFR against that solution (SH03 Fig. 2 is a qualitative publication cross-check, not digitized truth). Finest normalized profiles/SFR <=5%, decreasing error on three spatial resolutions; pressure-work and source-energy ledger residual <=`1e-8`. |
| `ism-isolated-disk`: accepted M2/G1/G2 and every applicable G3 gate | 4 threads, 16 GiB initially; re-register after calibration if needed | Jointly pin equilibrium IC, ambient medium, isolated gravity, halo/stars/gas, orbit-time unit, softenings and gas mass ladder with gravity worker/coordinator. At three mass resolutions and a halved-dt control, compare rotation/dispersion/scale height and annular SF histories over at least two declared disk orbital times. Proposed finest-two SFR history and stellar mass agreement <=10%, median resolved annular vertical/rotation errors <=5%, dt sensitivity <=2%, source/baryon budget residual <=`1e-8`, no unaccounted energy/floor correction or invalid accepted state. Domain-size/ambient and softening controls must also pass the G4 IC contract. These gates do not assert observed-galaxy realism. |

For all norms use scales fixed from the configuration, including a nonzero
momentum/energy scale if the net value vanishes. Archive residual histories,
minimum gas/phase mass and pressure, actual dt/substeps/retries, branch counts,
cooling root failures, rate-domain misses, numbers and mass spectrum of stars,
SFR (gross and locked), metals, `Q_SN`, radiative cooling and photoheating
separately, `E_star_unresolved`, `Delta W_birth`, gravity work and any boundary
flux. Coupled magnetized fixtures retain the accepted M2 independent
divergence and magnetic-energy diagnostics. A zero-source gas/particle
control must reproduce the accepted dynamics; enabling ISM must not alter
the frozen M1 configurations.

An isolated disk's Kennicutt comparison must state whether rates mean gross
formed or net long-lived mass, the adopted IMF conversion, aperture and gas
definition. Do not refit `t0`, yield, threshold or UV after seeing a failed
gate; a recalibrated variant gets a new named packet and retains the failure.
The sheet/disk IC files and exact ladder sizes are integration deliverables
owned jointly with G4, not supplied or executed by this source document.
No merger run is scientifically eligible until those concrete fixtures and
their independent review pass.

### 9a. Registered one-zone, ledger and endpoint inputs

`ism-cooling-cases-v3` freezes the following proposed cases, without
evaluating them. Each row member, refinement value, rejection point or
thread/restart variant is its **own future REANA workflow**. Scalar/ledger
cases use 1 thread/2 GiB; ordering variants use their named 1/2/4 threads
and 2 GiB. No aggregate cap applies. M1, source/design review and an
immutable implementation/preflight precede every executable case; live
gravity/M2 prerequisites additionally precede coupled cases. Pure transaction
fixtures may use an independently written GP-2 oracle/mock catalog and do
not claim an implemented gravity or moving-MHD solver.

Common one-zone inputs: `M_ref=1 kg`, `gamma=5/3`, `beta=.1`, `A0=1000`,
`T_c=1000 K`, `T_SN=1e8 K`, `t0=2.1 Gyr`, `y_star=.02`, `Z0=.001`,
the declared neutral/ionized conversion conventions, fixed V, v=0 and B=0.
Use the shared SI map; `1 Gyr=1e9*365.25*86400 s` (Julian-year engineering
conversion). Initial total density is `rho0=m_p*n_H,total/X`,
`V=M_ref/rho0`, `m_c0=x0*M_ref`, `m_h0=(1-x0)*M_ref`; initialize hot
u from the independent charge/temperature oracle at **hot** density.

For source-model tests only, set synthetic threshold
`n_H,total,th=1e-3 cm^-3` under
`source-model-fixture-threshold-1e-3-v1`. This is an explicitly controlled
coefficient/branch input, **not** a derived or physically adopted SH03
threshold; it never qualifies disk/merger calibration. Physical threshold
tests separately use the finite root inventory in section 4a.

| Case | Frozen state/backend and time ladder | Required measurements |
| --- | --- | --- |
| `IS-O01` frozen-coefficient hot relaxation | `m_c=m_h=M_ref/2`, `A=1000`, `t_star=t0`, f=0, masses deliberately frozen; `u_h0=u_c+2*u_SN/(A+1)`. Let `tau=t0/[beta*(A+1)]`, `dt0=tau/16`, `tfin=2*tau`, k=`0..4`, `dt=dt0/2^k`. | Analytic exponential from Eq. (10), normalized by `u_h0-u_h_eq`; finest error <=`1e-3`, finest-three order >=`.9`. This is an operator test, not evolving phase masses. |
| `IS-O02` coupled f=0 | `n_H,total=1 cm^-3`, `x0=.5`, `T_h0=3e5 K`, UV zero, signed CMB z=0, physical analytic KWH rates and synthetic threshold above. `dt0=t0/2^22`, `tfin=t0/2^18`; k=`0..4`. | Full evolving masses/energy/metals, guards and SFR, no frozen hot mass. Compare independent oracle at t=`j*tfin/32`, j=`0..32`; state/locked-mass finest error <=`1e-3`, finest-three order >=`.9`, integrated ledgers <=`1e-10`. If an event/domain violation occurs, retain it as evidence, not retune the state after seeing the result. |
| `IS-O03` existing clouds f=1 cooling | `n_H,total=.1 cm^-3`, `x0=.2`, `T_h0=2e4 K`, UV zero, signed CMB z=0; same dt/time ladder and synthetic threshold. | Same evolving-source/oracle gates, including ordinary hot cooling with continuing cloud SF/evaporation. Temperature below 1e5 selects f=1; no positive condensation manufactured from a heating rate. |
| `IS-O04-SYN` f=1 heating | O03 state, **manufactured** `C=0`, `H=rho_h*u_SN/t0`, so `Lambda=-H`; same ladder. The backend still uses the declared caloric relation. | Heating sign, source ledger, no condensation and same temporal/positivity/error gates. This formula is fixture forcing, not a physical cooling curve or adopted radiation source. |
| `IS-O05-PRIVATE` ordinary UV | `n_H,total=1e-6 cm^-3`, `x0=0`, `T_h0=2e4 K`, private FG20 default z=0 plus signed CMB; same ladder, fixed V. | No SF, caloric and thermal root inventory/basin, signed channel histories and temporal gates. Numerical traces with photo-rate values remain private. No thermal-equilibrium outcome is assumed. |
| `IS-O06` density exit | `n_H,total=(1+1e-6)*1e-3 cm^-3`, `x0=.9`, `T_h0=3e5 K`, UV zero/CMB z=0; same ladder and synthetic threshold. | Locate source mass-loss density crossing, preserve energy on cloud mixing and actual packet subintervals. Compare event time/state with independent event oracle to `1e-3*dt0` at finest; no repeated equilibrium reset or skipped interval. If no crossing occurs, report a case-design failure for review rather than assert success. |

The following manufactured ordinary-cooling and reservoir cases instantiate
the limiting families without claiming a physical cooling curve:

| Case | Inputs and exact model oracle | Gate |
| --- | --- | --- |
| `IS-L01-CONSTANT/EXP` | Ordinary gas, no F, Mref=1 kg, fixed V, `n_H=1e-6 cm^-3`; provider `u(T)=u_SN*T/1e6`, initial T=`1e6 K`, `tau=t0/2^20`. Constant `Lambda=rho*u0/tau`, final time `tau/2`, or exponential `Lambda=rho*u/tau`, final time `2*tau`. `dt0=tau/16`, k=`0..4`, dt=`tau/(16*2^k)`. Hold tau, physical rates and final times fixed. | Independent continuum and exact discrete BE oracles below; CONSTANT is exact state/ledger/algebra evidence without a meaningful fitted first-order slope. EXP retains the `1e-3` finest error and finest-three order >=`.9` gates. Separate attempted step `8*tau` must reject/subdivide for accuracy/domain, retaining original inputs and no state/ID change; it is not accepted beyond the registered final time. |
| `IS-L02-BARRIER` | Same ordinary provider/mass/density, `u_eq=u_SN/10`, initial T=`1e4` or `1e6 K`; `Lambda=rho*(u-u_eq)/tau`, nonnegative C/H split by sign. Final time `2*tau`, shared nominal dt0=`tau/16`, k=`0..4`, with fixed physical rates/tau/time. **Heating T0=1e4 K additionally registers k=5**; cooling T0=1e6 K keeps k=`0..4`. | Separate continuum and exact discrete BE references; no equilibrium crossing. Keep all-history component norms and the `1e-3`/order/ledger/event gates unchanged. Heating uses finest-three levels 3/4/5 for order; retain the k=4 history counterexample and k=5 bound below. |
| `IS-L03-RESERVOIR(x,beta,A,dt)` | Pure fixed-coefficient source kernel, dimensionless `m=V=t_star=u_SN=u_h=1`, `u_c=.01,Z=.001`, Lambda=0; x=`[0,2^-52,2^-40,.5,1-2^-40,1-2^-52,1]`, beta=`[0,.1]`, A=`[0,1000]`, attempted dt=`[2^-20,2^-4,1]`. Full Cartesian expansion; not a physical density/threshold fixture. | Independent mass/energy residual algebra and high-precision BE reference; exact x=1 invalid hot reservoir, x=0 valid no-SF ordinary limit. Near-empty cases must meet section 8a scales or fail typed resolution/admissibility; no mass/energy floor. Large attempted steps obey subdivision/rejection limits. |

For calibrated threshold continuity freeze
`rho/rho_th=1` and `1±2^-k`, k=`[4,8,12,16,20]`, within the registered
density bracket; evaluate independent one-sided limits and retain finite-
offset truncation errors rather than demand that the physical finite-offset
pressure difference vanish. EOS regulation probes use
`rho/rho_th=[1,2,10,100,1000]`, intersected with that bracket, and cold-fraction
perturbations `Delta x=±[1e-4,1e-6]` where admissible. The frozen-rho/hot-energy
regulation RHS and its derivative supply a local restoring-sign check;
full consuming-phase perturbations still need the independent finite-phase
oracle and do not assert a stationary solution. No threshold or stability
outcome is presumed.

| Case | Frozen input | Gate |
| --- | --- | --- |
| `IS-EVENT-SYN(kind)` guard-only paths | On dimensionless s=`t/t_guard` in `[0,1]`, prescribe `rho/rho_th=.9+.2*s` and reverse, `T_h/(1e5 K)=.9+.2*s` and reverse, `Lambda/C0=1-2*s`, or `g=u-u_eff=e0*(1-2*s)`, with positive volumetric-rate C0 and positive **specific-energy** e0. Each crosses at s=.5. Cloud-mass guard `m_c=.1*M_ref*(1-s)` reaches zero at s=1 and is normalized by M_ref. | Test event isolation/outgoing branch and repartition identities, including simultaneous density/T/sign at .5 under the fixed priority. These are guard/transaction paths, **not** a conservative hydro or physical source evolution; no omitted pressure work is called an energy-conserving trajectory. Time bracket and `1e-10` guard budgets in section 8a apply, including entry scale u_ref, never U_ref. Representation cases are below. |
| `IS-METAL(r,y)` | `m_g=1` in mass units, `Z0=.001`, r=`[0,2^-52,2^-20,2^-8,.01,.1]`, y=`[0,.02]`. Invalid initial Z=`[-1e-6,.020001]`; evolved ceiling case `Z0=.0199,r=.1,y=.02`. | Independent logarithmic closed-box and small-r series; packet and gas complements <=`1e-10` of fixed metal/mass scale, no cancellation at tiny r or division at r=0. Explicit range errors, no added gravity mass or thermal X/Y change. |

`IS-EVENT-REP(units,q,kind)` is the guard-only representation registry.
Use synthetic `t_guard=1 s`, `u_ref=u_SN=1e6 J/kg`,
`rho_th=1e-21 kg/m^3`, `C0=1e-30 J/(m^3*s)`, baseline `M_ref=1 kg`,
`e0=u_ref/4` and constant `u_eff=u_ref/2` for the entry path. These
synthetic dimensional anchors are not replacements for the physical SH03
parameters. For the density path use fixed `V=M_ref/(.9*rho_th)` so the
initial mass equals M_ref; for other paths use constant rho=`2*rho_th`
and `V=M_ref/(2*rho_th)`. Only the designated guard varies in each case;
these are independent interface paths, not a jointly self-consistent plasma.

Freeze unit representations SI, cgs and code units with base units
`mass=2 kg, length=3 m, time=5 s, temperature=2 K`. Conversion is algebraic:
specific-energy unit=`9/25 J/kg`, density unit=`2/27 kg/m^3`,
volumetric-rate unit=`2/375 J/(m^3*s)`; total U and specific u must use
their separate dimensions. In cgs, the anchors are
`u_ref=1e10 erg/g`, `rho_th=1e-24 g/cm^3`,
`C0=1e-29 erg/(cm^3*s)`, `M_ref=1e3 g`, same seconds/kelvin;
volume is the SI volume times `1e6`. Evaluate all guards/scales with the
same conversion, not a mix of specific and total energy.

For every unit representation, parcel multipliers q=`[2^-20,1,2^20]`
scale **both** M_ref and V by q at fixed intensive state/path; masses,
U_ref, total U and extensive transfers scale by q, while u_ref, e0,
rho, T and volumetric rates do not. The normalized entry and cloud guards
are respectively `(1-2*s)/4` and `.1*(1-s)` in every representation.
Their analytical events are s=.5 and s=1; compare outgoing branches and
normalized event brackets/guard residuals with section 8a's unchanged
tolerances, after unit conversion. Probe the .5 event at
`s=.5±2^-20`; for cloud exhaustion probe the incoming side `s=1-2^-20`,
then the zero-cloud outgoing branch without accepting a negative mass.
Do not demand bit equality of floating times across unit encodings.
Every unit/q/guard member is a separate future REANA workflow, 1 thread/
2 GiB after M1/source/immutable-preflight prerequisites. This tests source
guard representation invariance only; changing physical parcel mass does
**not** assert gravity, mesh, collisional sampling or galaxy invariance.

For coupled one-zone norms use initial M_ref and
`U_ref=M_ref*u_SN`, with component denominators
`max(abs(initial component), abs(oracle component), 1e-8*M_ref)` for masses
and `max(abs(initial U),abs(oracle U),1e-8*U_ref)` for thermal energy.
The locked-star history uses `max(L_oracle(tfin),1e-8*M_ref)`; report
component errors as well as the maximum norm. Fit time order using the
three finest positive errors; if oracle/roundoff prevents a meaningful fit,
mark it inconclusive and refine the reference, not passed by an invented
slope. All nonzero-L source subintervals still create distinct packets.

#### Discrete and continuum fixture oracles; manual compatibility checks

Let `a=dt/tau`, `z=t/tau=n*a` for a uniform nominal step. Exact discrete
BE references are `u_n=u0-n*dt*u0/tau` for CONSTANT,
`u_n=u0*(1+a)^(-n)` for EXP, and
`u_n=u_eq+(u0-u_eq)*(1+a)^(-n)` for BARRIER. The distinct continuum
references replace those factors by `1-z` or `exp(-z)`. Neither reference
may call the production stepper. Agreement with exact discrete BE diagnoses
the numerical solve under the existing residual/ledger tolerances;
comparison with the continuum supplies the `1e-3` accuracy and nonzero-error
order evidence. Agreement with another BE calculation alone cannot supply
continuum-order evidence. For an actual nonuniform accepted history,
the discrete exponential factor is `product_j(1+dt_j/tau)^(-1)`; retain
every dt_j, subcycle, rejection and event. Continuum targets stay at the
same physical times/rates/tau for every refinement.

The shared nominal ladder has `a_k=1/(16*2^k)`, k=`0..4`:
EXP/BARRIER at `tfin=2*tau` have `N_k=32*2^k`; k=4 gives N=512 and
dt=`tau/256`. L02 heating additionally has k=5, nominal N=1024 and
dt=`tau/512`, and fits order on levels 3/4/5. EXP and L02 cooling retain
k=`0..4`, fitting levels 2/3/4. CONSTANT at `tfin=tau/2` has
`N_k=8*2^k` (finest 128), k=`0..4`.
The existing accuracy/admissibility/event controls remain active; declared
subcycling can change those actual counts (notably coarse heating steps).
Do not insert extra adaptive work to manufacture a gate/order pass or
describe a subcycled run as uniform nominal BE. Order fits use measured
positive errors and the recorded work/history; an unmeasurable or distorted
fit is inconclusive, not an invented slope. CONSTANT has zero BE truncation
error for any accepted partition, so its state/ledger/algebra check has
**no meaningful fitted first-order slope**; oracle/roundoff still limit its
numerical comparison. EXP supplies temporal-order evidence.

The following are manual inequalities, not executed values or a production
pass. For `a=1/256`, write
`D(z)=(1+a)^(-z/a)-exp(-z)>=0`. Using
`ln(1+a)>=a-a^2/2`,
`D(2)<=exp(-2)*(exp(1/256)-1)<1/(7*255)<1e-3`.
For every registered sample in `0<=z<=2`,
`D(z)<=z*exp(-z)*a/[2*(1-a)]<3/[16*255]<1e-3`, since
`max(z*exp(-z))=1/e<3/8`. EXP's energy denominator is its initial
`M_ref*u_SN`, so these bound its actual component norm, not just an
arbitrary amplitude. They show the revised ladder can satisfy the gate;
an unimplemented solver still has to demonstrate it.

For L02 cooling, initial `u0=u_SN`, `u_eq=.1*u_SN`: the component
denominator remains initial `M_ref*u_SN`, and its normalized error is
`.9*D(z)<.9*3/[16*255]<1e-3`. For L02 heating, initial
`u0=.01*u_SN`, the actual denominator is
`M_ref*u_SN*(.1-.09*exp(-z))` for z>0, exceeding the `1e-8*U_ref`
scale. Thus its normalized error is
`.9*D(z)/(1-.9*exp(-z))`, **not** just `.09*D(z)`.
At the final time this is `<9/(61*255)<1e-3`, using `exp(-2)<1/7`.

However the existing history gate also checks z=.5 (sample j=8 of 32).
There n=128 and the opposite alternating-log bound gives
`-128*ln(1+1/256)>=-.5+b`, `b=383/393216`. Hence
`D(.5)>exp(-.5)*b`. Since `exp(-.5)>3/5`, the heating component error
is `>(27/23)*(383/393216)>1e-3`. This is the retained genuine
**history-fixture incompatibility** of the k=`0..4` heating sub-ladder;
the finest initial fractional heating increment `9/257<.1` does not force
additional subcycling. Do not claim the whole history passes from its
endpoint bound, change its denominator, loosen the gate or add hidden work.
The coordinator selected an **additional preregistered k=5 for L02 heating
only**, retaining levels 0..4 and all rates, tau, final times, component
denominators and error/order/ledger/event thresholds. For `a=1/512` and
`0<=z<=2`, the same bound gives

```text
E_heat(z) <= [ .9*z/(exp(z)-.9) ] * a/[2*(1-a)]
          < .9*a/[2*(1-a)] = 9/(20*511) < 1e-3,
```

since `exp(z)>=1+z` and `z/(z+.1)<=1` for z>=0 (zero error at z=0).
This is a uniform all-history component bound for **exact BE on the
registered uniform ladder**. Retain the old k=4 counterexample as history;
its final-time bound alone was insufficient. The k=5 addition is a
pre-execution fixture refinement, not a numerical pass or a post-result
tolerance change. Finite precision, enclosure/oracle error, branch failures
and accepted-step admissibility still need independent evidence. Record
both the exact nominal ladder and every actual accepted substep; do not
conceal extra work or remove the unchanged failure policies.

The independent temporal oracle uses a separately transcribed phase RHS,
80-decimal species/rate calculations and adaptive fifth-order Radau IIA,
not the production BE reduction, coefficient functions, root cache or
Jacobian. Set normalized local relative/absolute targets `1e-14`; repeat
at `1e-16` and require histories to change by <=`1e-8` of the above scales.
Cross-check nonstiff segments with a separately written adaptive order-eight
explicit integration using the same independent transcription. Freeze both
oracle source/container identities before execution. This is a prospective
oracle requirement, not an implemented solver, dependency adoption or a
source of computed reference values in this revision.

#### Atomic endpoint, rejection and same-step gravity packet

`IS-B01` is a synthetic transaction/algebra fixture with dimensionless
`G=1`, common fixed Plummer `epsilon=.1`, parent gas ID `(namespace=1,
counter=1)`, mass 1, cold mass .5, volume 1, `u_c=.01,u_h=1`,
`v=(2,-1,.5)`, centroid `(1,2,0)`, code B=`(.1,-.2,.3)`,
`Z0=.001,beta=.1,y=.02,A=0`. Hold A/B/volume fixed during the transaction.
Other pre-existing GP-2 sources are gas `(1,2)`, mass 2 at `(3,0,0)`;
old star `(2,1)`, mass 3 at `(0,4,0)`; dark matter `(3,1)`, mass 4 at
`(-2,-1,0)`. Their velocities are zero. All use the same epsilon.

Supply two independently verified **manufactured source plans**, not
claimed BE integrations: `[0,.25]` with `F=1/100`, and `[.25,1]` with
`F=1/50`; C=Q_rad=0 and Q_SN=`beta*u_SN*F`, using fixture `u_SN=1`.
Their locked masses are `9/1000` and `9/500`, and their actual midpoint
formation times `.125` and `.625` activate at **1**, giving estimated
population ages `.875` and `.375` at activation. This exercises commit validation,
not the physical SFR law; it cannot substitute for O02/O03. Next particle
counter in namespace 2 is 2; event namespace 4 starts at counter 1.
Prepared serial IDs are a dry run of the sorted checkpointed allocator;
its stored counters advance only during atomic commit. The independent
GP-2 evaluator performs full pair sums
before and after and separately verifies the multi-packet formula in
section 7, including the new-new pair. Do not merely compare two calls
to the production force/energy routine. Exact mass/momentum/metadata
budgets are `1e-12`, angular momentum `1e-11`, and energy/representation
explanations `1e-10` on fixed nonzero fixture scales. Instrumented force/
integrator callbacks must show no birth kick/drift before activation, all
new IDs included in the next force epoch, and no stale catalog cache.

Freeze each of these additional cases independently:

- `IS-B02`: split the second plan into `[.25,.5]` with F=`1/200` and
  `[.5,1]` with F=`3/200`, as if an event were located at .5. Retain three
  packets and their actual midpoints; no implicit aggregation. Total F is
  unchanged while the new-new potential terms need not be unchanged.
- `IS-B03-REJECT(stage)`: force failure before the first plan, after the first
  successful pending subinterval, while solving the second, after all
  pending plans but before commit, in full GP-2 ledger validation, and in
  final outer hydro/gravity acceptance. Independently inject outer rejection
  at geometry/remap validation, each MHD stage, gravity kick/drift validation
  and the source/outer-acceptance boundary; cases with pending plans must
  discard the whole pending catalog. Also test duplicate event/particle
  ID, allocator overflow, reversed/late interval, nonfinite age, wrong model
  receipt and insufficient phase/metals/energy. Every case restores gas,
  catalog, ledgers, allocator/counters and force epochs exactly; the next
  accepted retry matches a clean run with that accepted interval sequence.
- `IS-B04-RESTART(point)`: restart from the last accepted checkpoint before
  planning, after a rejected outer trial, and after atomic endpoint commit.
  A crash with one pending subinterval restarts from the preceding accepted
  checkpoint and regenerates it. Mid-outer-step checkpoint is rejected
  (`CheckpointNotAccepted`); no partial pending journal is persisted in
  this first profile. Restart after commit does not duplicate births.
- `IS-B05-ORDER`: thread counts `[1,2,4]`, normal/reversed/shuffled parent
  evaluation and plan arrival order, sort by accepted interval, parent ID
  and local ordinal for commit. In the two-parent variant gas `(1,2)` also
  forms plans with all masses/F/volume scaled by 2, its own centroid/velocity
  retained. Compare complete ID/ledger/catalog/state bits against the
  serial order. All cross-parent new-new pairs are included jointly.
- `IS-B06-REFINE(k,j,epsilon)`: subdivide each B01 interval into `2^k`
  equal intervals with proportional F, k=`0..4`; separately scale the
  parent mass/cold mass/volume/F by `2^-j`, j=`0..4`, with old background
  sources fixed, and epsilon=`[.2,.1,.05]`. Include a joint control
  `epsilon=.1*(2^-j)^(1/3)`. Compare complete raw H, every representation
  pair and exact fixture formula; **do not require decreasing epsilon at
  fixed mass to reduce the jump**, since it scales as `1/epsilon` here.
  These local synthetic scaling tests expose discretization dependence;
  they do not replace a fixed-galaxy-mass G4 spatial/mass/softening study
  or its cumulative `1e-4` binding-energy bound.

The private UV access plan, actual physical threshold/EOS, coupled sheet
solution and G4 disk/merger IC/mesh/softening/orbit-time packet remain
explicit dependencies. The source registry freezes inputs and failure
semantics only; all reference values, runtime resource adequacy, root/
stability outcomes, temporal evidence and physical applicability are
unexecuted. A source-free dynamics control, nonzero-B coupled run, every
accepted independent magnetic-divergence diagnostic, domain/ambient/wall
controls and live new-star gravity remain required for the moving merger.

## 10. First reviewable implementation slices and open dependencies

After the coordinator records prerequisite acceptance, implement small slices:

1. Add typed units, parameter validation, state/ledger/birth records and pure
   Eqs. (1)-(21) kernels with no driver hook. Implement both equilibrium
   approximation labels. Run their new tests only through REANA preflight.
2. Independently review these dispositions against the completed source
   review: finite root/event policies, analytic evaluation interval, selected
   UV identity and private-input boundary. Implement the `PrimordialRates`
   backend and the frozen independent fixture registry only after prerequisites;
   private UV cases additionally need verified platform access/retention
   within the owner's existing REANA project-test authorization. Then
   calibrate the numerical threshold/EOS.
   Manufactured rate backends remain explicitly synthetic.
3. Implement the atomic conservative local implicit transaction, branch events,
   deterministic births and metals, with one-zone/ledger/temporal REANA cases.
   Review source partition, thermal solve and invalid-state behavior separately.
4. Add conservative cold/metal transport and the agreed M2/G2 source ordering,
   then source-free identity, boost, restart and isolated-layer fixtures.
   Inspect gravitational-birth energy and magnetic flux retention explicitly.
5. If particle count requires it, review and implement one named stochastic
   variant with the counter/expectation/refinement packet. No implicit switch
   between deterministic, Eq. (39), and tau-leap laws.
6. Assemble the concrete G4 isolated-disk packet, obtain independent source/
   output review and demonstrate its convergence before enabling merger ICs.
   A later equilibrium acceleration must first reproduce the finite-phase
   source and pressure-work limit in its declared fast-regulation regime.

**Blocking dependencies for physical use:** review of this policy revision
against the separate source approval; independently implemented finite-root
enclosures and oracles; actual FG20 private platform input/restart/artifact
access/retention verification; resulting REANA rate/source/endpoint fixtures,
physical-applicability evidence, numerical threshold/EOS calibration and
tracer-domain validity for the configured ICs and full merger duration.
The owner already authorized REANA project tests; no renewed permission is
required. Source kernels and synthetic/UV-zero fixtures are independent of
private-data access, subject to their M1/implementation/preflight gates.
No redistribution route is selected. Historical SH03 UV identity and
current FG20 data redistribution permission remain unavailable findings,
not missing invented curves. The
current AREPO master implementation/defaults are not source-verified, and
no AREPO compatibility claim depends on them. The numerical finite-phase
equations, equilibrium approximation, threshold derivation, prompt return,
energy and metal normalization in this contract have explicit final-paper
locators. No unresolved cooling coefficient is replaced with an invented
algorithm, and no acceptance or execution result is claimed.
