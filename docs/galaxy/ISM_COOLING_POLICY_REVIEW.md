# Independent AI review of the ISM/cooling policy response

2026-11-22. **Recommendation: revise the entry-event scale and manufactured
cooling ladder before freezing their implementation fixtures.** The original
birth/subinterval interface blocker is resolved in the reviewed documents.
Source-supported pure kernels may proceed after the coordinator records the
M1 prerequisites; private-table access and coupled physical acceptance remain
separate dependencies. This is an independent **AI** source, mathematics,
interface and fixture review, not human peer review or numerical acceptance.

The reviewed response is commit
`6d8f6349948fcb03d8068da97360703fb9186cae` (abbreviated **R** below).
Shared/gravity/bounded-wall context is pinned to
`bed56a4560c4fcbc0d3228c3c58ad3ec5645b5cf` (**C**), even if live files change.
Observed checkout was `c4c82c6777fc6601b62e62aecc0c735f28915ffd`.
`IS` means `ISM_STAR_FORMATION_SPEC.md`; `CR` means `COOLING_RATES_SPEC.md`;
their line locators below refer to R. Context locators refer to C.

| Reviewed response file | SHA256 of committed bytes |
| --- | --- |
| IS | `dd49a189ff768392fe3911b5f50a146cf5fd50f93950548598df4cb1bc164245` |
| ism_star_formation_sources.json | `77ba7f78fb01d800aa4a834c38b68e760dd59f326255897d13f1ec88e729b27b` |
| CR | `71a51e715a1eb02c6b4903ff440c66584d51805fc6f7909cc78d7fa318878688` |
| cooling_rates_sources.json | `e4eadeaebe17a4f566699f1572110be0c5465d6c6f25164ba779b3f7952ef043` |

The companion [inventory](ism_cooling_policy_review_sources.json) pins context,
primary bytes, frozen history and checks. The original
[review](ISM_COOLING_DESIGN_REVIEW.md) and its inventory remain byte-identical
to `f8220efa7b3f0a5ddf9b5f48c0f229dcba0fda63`; their SHA256 values are
`964f8919d23aa2dcb831b4178399a6fa253d1b08fefc4cb110c505e79608be2a` and
`429dcb878b9128e22b8b3efbb7a8478303bfa587dec86327d39b2e745065e3da`.
The correction in disposition 2 belongs to this new review.

I checked committed response bytes and both inventories, retained full primary
sources and the prior source map, re-rendered Black's original Eq. (7), and
manually checked root arguments, BE elimination, metal limits and the fixture
error bound below. Hash/document checks are the only executable work here.
No numerical probe, test, evolution, production reducer, workflow operation,
external outreach, commit or source-code change was performed. None of M1,
a physical root, EOS calibration, one-zone integration, bounded MHD or a merger
is accepted by this report.

Primary locators are one-based PDF pages, with printed pages separately:

| Retained primary bytes | Relevant locators and role |
| --- | --- |
| SH03 final, SHA256 `5d53281a592195c1c0bd024ae9bb08ec82a3994613e441aa8896a22a4e23bed9` | PDF 3–6 / printed 291–294, Eqs. (1)–(23); PDF 9–11 / 297–299, Eqs. (29)–(40), passive metals; PDF 20 / 308, yield example. Governs the retained phase model. |
| KWH96 final, `f6d0f2cdf29adccd2c741ba60cff60a3061d042d9cdddc7869cb83f58749664f` | PDF 6 / 24, Table 1, Eqs. (23)–(24); PDF 7 / 25, Table 2 and ionization equations. |
| KWH96 preprint, `a6cba5ef1e916500d99ae166a42a90cf64aafeee77b5e0253fa65fc418f01d93` | PDF 13, Table 1: negative dielectronic exponent. |
| Black81 final, `2ebb558da80d7331795cbb72b0f48501bd643fa4824f2c8ba7f5381c8bbf74c5` | PDF 4 / 556, Eqs. (7), (9); PDF 5 / 557, Table 3 and stated temperature applicability. Eq. (7) re-rendered directly in this review. |
| Cen92 final, `d0e5ad0a78156ab2e7b75e704ff0e243df0b88a741eaa4ba94381747b8b9f38c` | PDF 5 / 345, Eq. (14); PDF 6 / 346, Eq. (17); PDF 7 / 347, Eq. (27b). |
| FG20 arXiv v2, `b059360fd3024209f6bad58472ee1ec451c2fed4619be223c84f59e411994e89` | PDF 4, Eqs. (7)–(8); PDF 13, Eq. (27); PDF 20, Table D1. Final published PDF remains unavailable; the retained access-denied XML is not a paper. |
| Author FG20 archive, `587a27854de50c95d79901b514d9acee421119ca41ff483eaeea84b6d695d49d` | README and 14 member identities checked. Selected effective **default** member: 15,210 bytes, SHA256 `c6e6030be92c6965c019c53915f31661782eb2cafed058cf9672b7efefc24aaa`. No selection of the .68 or optically thin variant. |

## Numbered dispositions against the thirteen original findings

1. **Birth intervals: original interface blocker closed in design.** IS
   620–653 and C's integration contract 100–142 / gravity contract 576–611
   consistently retain one packet per actual successful nonzero-L source
   subinterval, including event splits. They require
   `start<=formation_time<=end<=activated_at=t_global_end`, preserve the
   midpoint and forbid prior kicks/drifts. Pending plans are private;
   outer rejection restores gas, catalog, allocator, counters, ledgers and
   force state. IS 1184–1239 supplies falsifiable endpoint/rejection/restart/
   ordering cases. B01's `.125,.625` are **formation times**; at activation 1
   the estimated population ages are `.875,.375`. Clarify the phrase
   “midpoint ages” at IS 1197 in the future fixture so the oracle tests the
   correct fields. Midpoints should use IS 630's stable expression.

2. **Atomic coefficients supported; correction to my historical reading.**
   Black's original Eq. (7), printed 556/PDF 4, visibly reads
   `1.50e-10*T^(-0.6353)`, with its printed `T>=5000 K` condition. My original
   review's ancillary `-.6533` transcription was wrong. The author's new
   reading is correct. The retained revision image has SHA256
   `5f70db22cb76ac91d4c9609849c3730219ffab473b731636cfaa8f6508954187`;
   I also rendered the hashed PDF directly, rather than relying on OCR.
   CR 143–152's ten cooling rows and 183–190's seven coefficient assignments
   are byte-identical to the original `23ab618` formulas: **no adopted
   formula changes**. KWH final Table 2 and Cen Eq. (27b) agree on this power.
   C1 remains the justified named negative-sign correction: KWH final
   Table 1's positive exponent conflicts with its preprint Table 1, Black
   Eq. (9)/Table 3 and Cen Eq. (14). No official erratum is asserted.

3. **Finite charge/caloric/thermal policy conditionally adequate; no certified
   implementation exists.** CR 216–240 correctly confines uniqueness to
   the selected nonsingular fixed-T charge branch. With positive backward
   coefficients and nonnegative photo rates, each forward/backward ratio
   has form `a+b/e`, hence is nonincreasing in positive electron density e.
   Mean ionic charge is increasing in those ratios, so `e-Q(e)` is strictly
   increasing. Zero-UV collisional continuity and genuinely singular
   zero-rate networks require the stated separate limits; this is not
   uniqueness of every neutral algebraic solution. CR 250–309 separately
   inventories caloric/thermal roots, distinguishes heat-capacity and
   restoring signs, and fails on unresolved bins/multiple caloric roots.
   The domains, residual scales and finite resource limits are explicit.
   Opposite signs plus a valid fixed-sign derivative enclosure suffice for
   an isolator; same-sign samples do not exclude tangencies. Before a
   certificate can be claimed, select/audit outward-rounded elementary
   functions, nested-charge error propagation and implicit derivatives.
   Eighty-decimal agreement or a finite bracket is not that certificate,
   nor evidence that a physical root exists. Use C03 and C07 before physical
   branch selection.

4. **Signed CMB, units and thermal-energy convention retained.** CR 102–130
   and section 5 keep the previously supported Cen/Thomson derivation with
   modern constants, one SI/cgs adapter, hot density `m_h/V`, and
   `u=3*k_B*T*n_part/(2*rho_h)`. Positive/negative CMB exchange is split into
   nonnegative cooling/heating before taking their difference. Photo rates
   remain per target; no additional electron or `4*pi` factor is supplied
   by this revision. Ionization losses remain in the thermal-loss convention,
   without a duplicate binding-energy sink. C01/C05/C06 must check species
   factors, signed zero, SI/cgs agreement and near cancellation; these source
   statements supply no numerical pass.

5. **UV node/ULP policy is defined, with a declared endpoint amendment.**
   CR 451–499 specifies bit-exact node returns, correctly rounded mathematical
   node/endpoint definitions, log-rate interpolation in q, no fuzzy interior
   snapping, and a flagged one-ULP upper normalization. That tiny extension
   is a numerical input convention, not the exact mathematical source domain
   or new UV samples. Negative nonzero inputs and two-ULP exterior inputs
   fail. Independently bounded `log1p/ln(10)`, endpoint bit vectors, parsed
   bits, each channel, malformed receipts and transform errors still need
   C04. The positive `1e-40` entries remain data; no zero replacement is
   justified. Archive/member/default/.68/thin identities are unchanged.
   Log interpolation is an engineering rule, not AREPO identity or an exact
   effective-spectrum accuracy result.

6. **Private input route supported as design; platform verification remains
   operationally incomplete.** CR 501–567 excludes raw tables, rate vectors,
   oracle targets and capabilities from public configs/checkpoints/logs;
   restart re-resolves the immutable hashed member and fails if unavailable.
   Public derived states/budgets require the stated export allowlist; a scan
   reproducing table rows is not made safe by calling it derived output.
   The owner's existing authorization covers project tests on REANA:
   **this review does not require a new user permission**. It also does not
   establish the actual principals, log/artifact visibility, retention/
   backups, private scratch cleanup and restart input route. Verify a concrete
   private path for both input and oracle artifacts before table-dependent
   execution; `PrivateInputPolicyUnverified` then has a real operational
   meaning. This dependency does not block source kernels, UV-zero cases or
   independently generated synthetic fixtures. Scientific-use context is not
   a verified redistribution grant. Public raw distribution remains unresolved;
   the arXiv license supplies no downstream data grant. Historical SH03 UV
   identity and final FG20 published-PDF comparison remain unavailable.

7. **Named analytic interval is acceptable as a computational scope, with
   explicit physical limits.** CR 571–612 now distinguishes the chosen
   `1e3..1e8 K` interval from Black's stated roughly `5e3..5e5 K` interval,
   the low-T extension and KWH/Cen hot modifications. Neither all finite
   positive densities nor the C02 density ladder is thereby a physically
   validated domain. Keep hot vs total n_H separate, fixed isolated `z_uv=0`,
   explicit T/u/UV domain errors, and bypass cooling at zero hot mass. Optical
   depth, path/cross sections, critical-density/escape data, ionization
   relaxation and electron-ion equilibration are actual physical prerequisites
   for a claimed physical case. Missing ancillary data leaves an analytic
   equation test; it does not make its numerical result fail or qualify a
   cold dense merger parcel. No temperature floor/domain extrapolation is
   authorized.

8. **Finite-phase equations and BE elimination supported under stated
   assumptions.** SH03 final Eqs. (5)–(12), (13) and (40), and IS sections
   3/7 retain the supported phase/source/pressure algebra. For fixed V and
   one fixed f branch, write `d=u_h-u_c`. The three source identities imply
   `h*d=h0*d0+beta*u_SN*F-Q_rad`. For f=0, `Q_rad=C*d` and
   `h+C=h0+beta*(1+A)*F`, yielding IS 957's expression for d(F).
   `c=F*t_star/dt` then gives its R_F. For f=1, C=0 gives the stated mass
   residual and R_T (IS 944–977). A and t_star must use the new **total**
   density and cooling the new hot density. These reductions are algebra,
   not solved roots or a positivity theorem. Recheck the original residuals,
   branch/admissibility and common integrated transfers independently.
   Pressure remains the mixture-energy pressure; no EOS reset or second
   prompt SN injection is justified.

9. **Threshold/EOS search and branch meaning now explicit; calibration open.**
   IS 297–350 distinguishes a finite total-density threshold search from
   its hot-density rate argument, restricts the EOS hot-fraction oracle,
   and requires connected restoring root tubes without nearest-root jumps.
   `g_x<0` is restoring for the declared diagnostic
   `dot x=g/[rho*(u_h_eq-u_c)]`, with fixed positive denominator. It is not
   a stationary consuming-phase solution: the actual finite-phase fraction
   equation also contains
   `-(1+A*beta)*x/t_star+(1-beta)*x^2/t_star` alongside `Lambda/[rho*d]`.
   The revision explicitly makes this distinction. Positive `dP/drho`, root
   count, connected-tube enclosures through density intervals and independent
   finite-phase perturbations remain required. The finite brackets do not
   prove a root/threshold exists. The `2^-40` oracle hot-fraction bound must
   never become an evolved mass floor. C03-TH/EOS can falsify branch switching;
   C07 and continuity/EOS perturbations must establish any actual calibration.

10. **Revise the entry-event dimensional scale; retain the other BE controls.**
    IS 368–371 defines the entry guard by `u-u_eff`, a **specific** energy;
    the event fixture at 1158 uses that same guard. IS 1028–1031 instead
    normalizes entry energy by `U_ref=M_ref*u_SN` (999–1001), a **total**
    energy. This compares incompatible units and makes an implementation's
    event accuracy depend on its mass-unit/parcel representation. Keep the
    `1e-10` threshold: either define the guard as `U_th-m_g*u_eff` and scale
    by U_ref, or retain `u-u_eff` and scale by `u_SN=U_ref/M_ref`. Also name
    the cloud-exhaustion mass guard's scale (M_ref is consistent); the current
    scale list omits it. This is an event-interface implementation blocker,
    not a physical cooling failure.

    The fixed outer M_ref/U_ref scales, `2^-40` error scales, separate actual
    reservoir admissibility, original residual/ledger checks, finite
    retries, no-progress errors and event enclosure requirement are otherwise
    sensible fail-closed policies (IS 932–1043). Positive dt homotopy samples
    alone do not certify connection to dt=0: implement an analytic/enclosed
    starting tube and parametric coverage between continuation points, or
    fail unresolved. Regularizing with `S=F/dt` avoids the formal `F/dt`
    singularity in a zero-step analysis. Tiny positive h/d is not proof that
    hot energy was resolved after cancellation. Test all-cold rejection,
    zero-cloud ordinary gas, tiny phases, folds, missed/coalesced events and
    rollback; do not infer monotonicity or uniqueness from BE or the grid.

11. **Passive metals are a declared approximation; the real duration/IC must
    fit it.** IS 669–715 correctly uses locked L, stable `-log1p(-r)` and
    `b(r)=sum r^k/[k*(k+1)]`; for `0<r<=2^-8` the remaining positive tail
    after k=8 is bounded by `r^9/[90*(1-r)]`. L=0 needs no division or packet.
    The complement remains a ledger, not a repair. X=.76/Y=.24 are effective
    primordial **thermal** fractions while Z traces existing baryons; this
    is not a chemically consistent H+He+Z species evolution. The `.02`
    ceiling is an engineering limit, not evidence that metal cooling is
    negligible. Range crossing is a terminal retained failure, not grounds
    to clip enrichment, suppress SF or keep retrying. Before the actual
    merger, freeze its initial metallicities, intended duration and IC/source
    histories and establish that the declared model can cover them. Do not
    shorten the configured encounter to evade this limit. A genuine violation
    requires a new reviewed model/profile; it does not invalidate the pure
    small-L kernel.

12. **Joint GP-2/ID/energy contract supported; scalability remains unproved.**
    For coincident equal-softening births from one parent, IS 744–755's
    `Delta W=-(G/epsilon)*[(m0-sum L_i)*sum L_i+sum_(i<j)L_i*L_j]`
    follows directly from all gas-new and distinct new-new pairs. Contributions
    from external old sources cancel only for this special coincident,
    unchanged-softening fixture; production uses complete before/after sums,
    including cross-parent new-new and changed old-source terms. Preserve raw H,
    adjusted explanatory energy and cumulative `sum abs(Delta W_rep)<=1e-4`
    of initial binding energy, with separate mass/dt/epsilon controls.
    Decreasing epsilon at fixed packet mass can increase the jump.
    Typed namespace/counter IDs, dry-run allocation and atomic commit agree
    with C's sorted immutable force-epoch contract (gravity 241–249) and
    IS 823–886. B03/B05 must expose stale epochs, counters or arrival-order
    effects. Deterministic first references do not certify an eventual
    stochastic, SHA-counter or merged-cohort production mode; those require
    separate selection, statistical/ledger evidence and representation study.

13. **Concrete fixtures improved, but the L01 ladder cannot meet its stated
    finest BE gate.** IS 1143 fixes exponential `du/dt=-u/tau`, u0=u_SN,
    tfin=2*tau, dt0=tau/4, k=0..4. At the finest registered step dt=tau/64,
    exact BE gives `u_N/u0=(65/64)^(-128)`, whereas the continuum oracle is
    `exp(-2)`. IS 1161–1168 normalizes this energy error by the initial
    `U_ref` here. With a=1/64, the alternating-log bound gives

    ```text
    -128*ln(1+a) >= -2 + 1/64 - 1/6144 = -2 + 95/6144
    (65/64)^(-128) - exp(-2)
       > exp(-2)*(95/6144) > 95/49152 > 1e-3.
    ```

    This is a manual inequality, not an executed integration. The finest
    per-step fractional decrement is only `1/65<.1`, so the stated accuracy
    control does not force an extra split; T remains inside the domain.
    A compliant registered BE run can therefore fail IS 1074's gate without
    an implementation error. Keep `1e-3`: preregister a finer ladder (for
    example the tau/16 base used by O01), or additional fine levels and
    explicit accepted substep histories. Recheck L02's shared relaxation
    ladder too. Do not silently add adaptive work or loosen the gate after
    execution. Constant cooling is exactly integrated by BE, so its zero
    truncation error cannot supply a meaningful fitted first-order slope;
    classify it as exact algebra/ledger evidence and use EXP for temporal
    order. This fixture correction is required before freezing that packet.

    The separately transcribed 80/100-decimal scalar and Radau/independent
    explicit temporal oracles (CR 720–729; IS 1171–1180) have useful explicit
    scales and refinement requirements. They must remain independent of
    production coefficients, Jacobians, caches and BE elimination. No oracle
    implementation, enclosure certificate, reference value or observed order
    exists in the reviewed design. Synthetic thresholds/paths are explicitly
    synthetic, not substitutes for calibrated or coupled physics.

## Smallest future falsification packet and implementation disposition

All cases below are prospective **individual REANA workflows**, after M1 and
their own immutable implementation/preflight prerequisites. Retain the
registered thresholds. Scalar/transaction members use 1 thread/2 GiB;
ordering members separately use 1/2/4 threads and 2 GiB. Shared preflight is
2 threads/8 GiB; ready independent cases have no aggregate resource cap.
These are first diagnostic subsets, not permission to omit the registered
Cartesian families before their eventual acceptance.

| First independent cases | What must be falsifiable before escalation |
| --- | --- |
| C01 at 1e3, 1e4, 1e8 K; C05 at T_r/2,T_r,2T_r; C06 cancellation | Coefficient/source signs and species factors, domain distinction, SI/cgs and signed CMB; separately transcribed high-precision values. |
| C03 three/no/tangent roots, TH/EOS fold, one zero-UV C02/C07 state | All-root coverage and outward certificates, caloric multiplicity, marginal/unresolved distinction, no branch jump; include a deliberately uncertifiable bin that must fail. |
| C04-SYN, q/z endpoint/ULP/malformed variants | Exact nodes vs interior interpolation, input identity before parse, correctly rounded transform bounds; no dependency on a real private table. |
| Entry/sign/cloud event paths after disposition 10's unit fix | Known t=.5/t=1 guards under equivalent mass/unit representations; outgoing branches, cloud scale, coalesced priority, missed-root enclosure and no repeated stationary event. |
| Revised L01-CONSTANT/EXP and L02; O01 | Exact discrete BE and continuum oracles separately, accepted dt histories, unchanged finest-error/order targets; no invented slope for exact constant loss. |
| L03 zero/tiny phases and one O02/O03 member | Original BE residuals, finite hot-energy resolution, continuation toward dt=0, physical-domain/admissibility failures, evolving-mass vs frozen-operator distinction; then the full registered refinements. |
| METAL r=0,2^-52,2^-8 and ceiling crossing; B01/B02/B03/B04/B05 | Stable small-L metals, no floors/repair, real formation vs activation ages, joint new-new energy, every rollback/ID/epoch boundary, accepted-checkpoint restart parity. B06 then measures representation refinement. |
| Private C04 and O05 only after the verified private access/artifact/restart route | Same member bytes and oracle identity, no public raw rate leaks; platform retention proof is independent of numerical agreement. |

The shared C context selects a conducting-slip finite box with zero normal B,
compact interior A, no imposed mean field and unbounded collisionless
particles; its bounded operators remain unaccepted (integration 144–176).
The actual G4 sheet/disk/merger ICs, duration, ambient/domain sizes, field
topology, softenings and isolated/gravity/moving-MHD evidence remain
unexecuted dependencies (IS 1079–1100,1251–1258). Their declared domain,
boundary/tracer failures and raw/adjusted budgets must be retained. This
source review preserves the final live, deforming **3D gas+DM+existing/new
stars magnetized merger** objective and supplies no shortcut around those
gates.
