# Primordial cooling, ionization and UV source contract

Status: **source/design only; unimplemented, unexecuted and not accepted**,
2026-11-22. This is the thermal backend for
[ISM_STAR_FORMATION_SPEC.md](ISM_STAR_FORMATION_SPEC.md), subject to the
[shared integration contract](INTEGRATION_CONTRACT.md). The byte inventory,
equation map, retrieval failures and license findings are in
[cooling_rates_sources.json](cooling_rates_sources.json). No AREPO/GADGET
code was copied. Reading, PDF rendering, transcription and file-integrity
checks are the only local execution in this audit.

Revision `cooling-review-disposition-v2` responds to the separate
[13-finding review](ISM_COOLING_DESIGN_REVIEW.md) committed in `f8220ef`;
the concise joint disposition table is before section 1 of the ISM contract.
Historical reviewed-byte evidence in
[ism_cooling_review_sources.json](ism_cooling_review_sources.json) is
immutable. The current inventory separately pins revised document/context
identities. Supported atomic/CMB formulas are retained; new search,
interpolation, private-input and fixture policies are engineering decisions,
not numerical results or a new physical-accuracy certification.

## 1. Selected scientific profile and acceptance boundary

The proposed profile is `primordial-kwh96-cen92-fg20-v1`:

- Optically thin, low-density, monatomic H/He with `X=.76`, `Y=.24`,
  ionization equilibrium but **not** thermal equilibrium.
- The ten cooling channels and seven ionization/recombination coefficients
  in Katz, Weinberg & Hernquist (1996, KWH), with the explicitly documented
  dielectronic sign correction C1 below.
- Signed nonrelativistic CMB exchange derived from Cen (1992), Eq. (17),
  using a specified modern CMB temperature and CODATA constants. KWH's
  printed high-temperature-only approximation is a comparison profile.
- The **unrescaled FG20 effective default** six-rate UV history,
  `fg20_treecool_eff_default.dat`, from the author's 2020-10-27 archive.
  This is a selected scientific replacement, **not historical SH03 UV
  identity**. It remains an external source input with the unresolved
  redistribution status described in section 6.
- For an isolated first galaxy, freeze `z_uv=0` and the corresponding CMB
  temperature. The integrator's elapsed time is not a cosmological redshift.
  A cosmological reionization evolution is outside this first profile.
- Primordial thermal rates are independent of passive metal tracer `Z`.
  There are no molecules, dust, local radiation, shielding, radiation
  transfer, secondary ionizations, metal lines, cosmic rays or X-ray
  Compton heating. FG20 includes X-rays in its published background and
  tabulated photo rates; that does not add a separate X-ray Compton term.

No numerical cooling curve, threshold density, EOS table, abundance value
computed from these formulas, or thermal evolution was produced in this
task. Equation transcription removes an unavailable-coefficient dependency;
the separate review approves the mapped atomic/CMB equations and named C1
correction as source design, subject to its conditions. This revision resolves
the design policies below; it supplies no evaluated-value or applicability
evidence. Independent review of the revised policies, REANA rate fixtures,
private-input execution prerequisites and threshold calibration remain
prerequisites to physical G3 runs. Pure interfaces and independently written equation
kernels can be prepared after M1 permits that implementation slice.

## 2. Primary sources and version control

| Source | Consulted version and exact locators | Role/limitation |
| --- | --- | --- |
| [Katz, Weinberg & Hernquist 1996](https://articles.adsabs.harvard.edu/pdf/1996ApJS..105...19K), ApJS 105, 19-35, DOI 10.1086/192305 | Final published pp. 24-25, Tables 1-2, Eqs. (23)-(40); also complete [arXiv v1](https://arxiv.org/pdf/astro-ph/9509107v1), including Table 1 on PDF p. 13 | Primary adopted primordial network. Published Table 1 and preprint differ at C1. Rendered original tables were inspected; extracted mathematical glyphs alone were not trusted. |
| [Black 1981](https://articles.adsabs.harvard.edu/pdf/1981MNRAS.197..553B), MNRAS 197, 553-563 | Final pp. 556-557, Eqs. (7), (9), Table 3 | Primary source cited by KWH; corroborates negative dielectronic exponent. Eq. (7) was re-rendered in this revision to check the review's separate exponent claim. Its larger network is not imported. |
| [Cen 1992](https://articles.adsabs.harvard.edu/pdf/1992ApJS...78..341C), ApJS 78, 341-364, DOI 10.1086/191630 | Final p. 345, Eqs. (12)-(16); p. 346, Eq. (17); p. 347, Eqs. (26)-(28) | High-temperature modification lineage and signed CMB exchange. Eq. (17) was visually checked. We do not import Cen's transport, cross-section implementation or extra processes. |
| [Faucher-Giguère 2020](https://arxiv.org/pdf/1903.08657v2), MNRAS 493, 1614-1632, DOI 10.1093/mnras/staa302 | Downloaded arXiv v2, revised 2020-01-29; Eqs. (7)-(8), PDF p. 4; section 3, pp. 11-14; Appendix D, Table D1, PDF p. 20 | Complete v2 read for rate conventions/effective-history scope. Author archive README identifies FG20 with the published model and distinguishes older FG19. Published-PDF retrieval returned access-denied XML, so no claimed final-page/equation parity beyond verified metadata. |
| [FG20 author data](https://galaxies.northwestern.edu/uvb-fg20/) | Downloaded author page, ZIP and README, plus exact selected member | Machine-readable six rates and units, including distinction between default and `.68` heating-rescaled variant. No explicit redistribution grant found in those artifacts. |
| [Fixsen 2009](https://arxiv.org/pdf/0911.1955v2), ApJ 707, 916-920, DOI 10.1088/0004-637X/707/2/916 | arXiv v2, 2009-11-10, abstract and temperature determination | `T_CMB,0=2.72548 K` central value. Regenerated PDF prints a later TeX date; the arXiv version label remains v2. |
| [NIST CODATA listing](https://physics.nist.gov/cuu/Constants/Table/allascii.txt) | Downloaded listing labelled **2022 CODATA adjustment** | Pinned numerical physical constants, not current values inferred from memory. |

Hashes refer to actual downloaded bytes, not to a URL's future contents.
PDFs, HTML, the ZIP and extracted data remain in ignored
`results/galaxy_ism_design_20261122/`. The repository contains the scientific
contract and source metadata only. Neither an arXiv nonexclusive-distribution
license nor the repository's MIT license is asserted to license the author's
separate data archive. See section 6 before any data vendoring/publication.

## 3. Units, inputs and sign conventions

One SI `UnitSystem` owns all simulation conversions. The cooling boundary
adapter converts physical SI quantities to cgs exactly once:

```text
rho_cgs [g cm^-3] = 1e-3 * rho_SI [kg m^-3]
u_cgs   [erg g^-1] = 1e4 * u_SI [J kg^-1]
n_cgs   [cm^-3] = 1e-6 * n_SI [m^-3]
Lambda_SI [J m^-3 s^-1] = 0.1 * Lambda_cgs [erg cm^-3 s^-1]
integrated_energy_SI [J] = 1e-7 * integrated_energy_cgs [erg]
```

These are boundary conversions; code-unit scales come from the shared SI
map. Do not multiply a rate by volume, density, `a`, `h` or the unit system
twice. Rates are local **proper** rates, not comoving.

Inputs are hot/ordinary gas mass density `rho_h>0`, specific **thermal**
energy `u_h>0`, abundance convention, six externally supplied photo rates,
`z_uv`, CMB mode and full model identity. In a multiphase cell `rho_h=m_h/V`
uses the total averaging cell volume; it is not `rho_total`, cloud internal
density, or a guessed hot filling-factor density. At zero hot mass the
caller bypasses the rate solve and uses the ISM phase limiting branch.

Return nonnegative atomic cooling channels `C_j`, nonnegative photoheating
`H_photo`, signed CMB exchange `C_CMB`, species numbers, `T`, `mu`, all
solver residuals and a signed net loss:

```text
C_CMB_loss = max(C_CMB,0); H_CMB = max(-C_CMB,0)
C_total = sum_j C_j + C_CMB_loss
H_total = H_photo + H_CMB
Lambda_net = C_total - H_total                   # erg cm^-3 s^-1
du_h/dt|ordinary = -Lambda_net/rho_h               # erg g^-1 s^-1
```

The source ledger stores the integrals of **both** `C_total` and `H_total`;
their difference is signed `Q_rad`. An ionization-energy reservoir is not
added to `u_h`: this is KWH's thermal-energy/collisional-loss convention.
Collisional ionization losses appear in Table 1 and must not be subtracted
again by evolving a second binding-energy state. Photoheating is excess
photon energy per target atom, not the ionization threshold energy. The
reference assumes a Maxwellian common electron/ion temperature.

The composition convention uses proton mass `m_p` and `m_He=4*m_p`, as in
the published primordial model, rather than a new atomic-mass fit:

```text
n_H  = X*rho_h/m_p
n_He = Y*rho_h/(4*m_p)
n_part = n_H+n_He+n_e
mu = rho_h/(m_p*n_part)                           # dimensionless
u_h = 3*k_B*T*n_part/(2*rho_h)
```

## 4. Complete adopted atomic coefficient map

Let temperature `T` be in kelvin, `T_n=T/(10^n K)`,
`D5=1+sqrt(T_5)`, `D6=1+T_6^0.7`. Density products below use `cm^-3`.
Each coefficient times its density product is `erg cm^-3 s^-1`.
The normalization constants therefore carry the temperature powers
implicit in a kelvin-valued argument; they are not unit-free fit numbers.

| ID / KWH Table 1 process | Coefficient | Density product |
| --- | --- | --- |
| `exc_hi` H I excitation | `7.50e-19*exp(-118348.0/T)/D5` | `n_e*n_HI` |
| `exc_heii` He II excitation | `5.54e-17*T^(-0.397)*exp(-473638.0/T)/D5` | `n_e*n_HeII` |
| `ion_hi` H I ionization | `1.27e-21*sqrt(T)*exp(-157809.1/T)/D5` | `n_e*n_HI` |
| `ion_hei` He I ionization | `9.38e-22*sqrt(T)*exp(-285335.4/T)/D5` | `n_e*n_HeI` |
| `ion_heii` He II ionization | `4.95e-22*sqrt(T)*exp(-631515.0/T)/D5` | `n_e*n_HeII` |
| `rec_hii` H II radiative recombination | `8.70e-27*sqrt(T)*T_3^(-0.2)/D6` | `n_e*n_HII` |
| `rec_heii` He II radiative recombination | `1.55e-26*T^0.3647` | `n_e*n_HeII` |
| `rec_heiii` He III radiative recombination | `3.48e-26*sqrt(T)*T_3^(-0.2)/D6` | `n_e*n_HeIII` |
| `dielectronic_heii` He II dielectronic recombination, **C1** | `1.24e-13*T^(-1.5)*exp(-470000.0/T)*(1+0.3*exp(-94000.0/T))` | `n_e*n_HeII` |
| `free_free` | `1.42e-27*g_ff*sqrt(T)` | `n_e*(n_HII+n_HeII+4*n_HeIII)` |

KWH Eq. (23):

```text
g_ff=1.1+0.34*exp(-(5.5-log10(T))^2/3.0)
```

**C1, `kwh96-dielectronic-sign-correction-v1`:** the visually inspected
published KWH Table 1, printed p. 24, has `exp(+470000.0/T)` in this cooling
term. The preprint's Table 1, PDF p. 13, has the negative sign. Black's
original Table 3, p. 557, also has the negative sign, as do Black Eq. (9),
p. 556, and KWH's associated recombination coefficient in Table 2. Adopt
the **negative** exponent with this explicit correction identifier. The
positive printed exponent is not silently evaluated, and no different
coefficient magnitude is inferred. The separate independent review now
supports this named negative-sign correction, including Cen Eq. (14),
p. 345, as another primary corroboration. This audit is evidence of
a source discrepancy, not a claim to have found an official erratum.

**Correction to review finding 2's ancillary lineage statement:** the
re-rendered original Black Eq. (7), p. 556/PDF p. 4, visibly prints
`T^(-0.6353)`, agreeing with the adopted KWH coefficient and Cen Eq. (27b),
p. 347. The review's `-.6533` reading is not supported by these source
bytes. Record this revision's image/hash separately; leave the independent
review and its historical inventory untouched. No coefficient or named C1
correction changes, and no identity of all Black/KWH expressions is implied.

KWH Table 2, p. 25, gives coefficients in `cm^3 s^-1`:

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

Here `c_i` is collisional ionization. The independently named `Gamma_i`
photoionization rate has units `s^-1`. The recombination fit is the adopted
optically thin KWH convention; do not silently replace it by a case-B,
on-the-spot or modern-fit table. Dielectronic recombination affects the
He I/He II balance and its own thermal channel once each. It is not a
separate baryon loss. No unresolved coefficient remains in this chosen
ten-channel/seven-coefficient network; independent validation is pending.

### Ionization and energy solve

KWH Eqs. (25)-(38) are equivalent to the following equations without
division by electron abundance:

```text
(c_HI*n_e + Gamma_HI)*n_HI = alpha_HII*n_e*n_HII
(c_HeI*n_e + Gamma_HeI)*n_HeI
    = (alpha_HeII+alpha_d)*n_e*n_HeII
(c_HeII*n_e + Gamma_HeII)*n_HeII = alpha_HeIII*n_e*n_HeIII
n_HI+n_HII = n_H
n_HeI+n_HeII+n_HeIII = n_He
n_e = n_HII+n_HeII+2*n_HeIII
```

Proposed pure routine `ionization_at_temperature(rho,T,photo_rates)` solves
the nonnegative physical branch with element and charge residual checks.
At fixed positive `n_e`, normalize the two H weights `alpha_HII*n_e` and
`c_HI*n_e+Gamma_HI`; normalize the three He weights constructed from the
two forward and two backward rates. Use scale-normalized products to avoid
overflow, not a change of the equations. Close charge neutrality with a
bracketed scalar solve on `0<=n_e<=n_H+2*n_He`. Vanishing-rate cases take
explicit limits. When all photo rates vanish, select the collisional
equilibrium ratios by continuity from positive electrons; the identically
neutral zero-electron algebraic root at any temperature is not the chosen
high-temperature physical branch. Do not inject an electron floor.

Explicit normalized weights are `H:(b,a)` and `He:(d*k,c*k,c*j)`, with
`a=c_HI*e+Gamma_HI`, `b=alpha_HII*e`,
`c=c_HeI*e+Gamma_HeI`, `d=(alpha_HeII+alpha_d)*e`,
`j=c_HeII*e+Gamma_HeII`, `k=alpha_HeIII*e` at electron trial e.
For finite positive recombination coefficients and nonsingular nonnegative
photo rates, each forward/backward ratio is nonincreasing with e. Mean
ionic charge Q(e) is therefore nonincreasing and `e-Q(e)` strictly
increasing: the selected physical fixed-T charge root is unique. This
argument does not certify u/T, thermal, threshold, EOS or implicit roots.
Use log-scaled weights, with an explicit zero-UV collisional-ratio limit;
underflow must not silently manufacture a singular network. If an exact
zero-rate synthetic case has a unique stated limiting distribution use it;
if the distribution is undetermined return `SingularIonizationNetwork`.

For energy input, `temperature_from_thermal_energy` brackets roots of
`3*k_B*T*n_part(T)/(2*rho_h)-u_h=0` in the accepted domain. Each temperature
trial uses the ionization solve. Reject an unbracketed or ambiguous root
and report the input/residuals. Do not reuse a neutral or fully ionized
`mu` for all temperatures. Thermal equilibrium is a **different** root of
`Lambda_net=0` and can have multiple stable/unstable branches. Any cached
table must retain this distinction and the full model identity.

### 4a. Finite root inventory and thermal selection

`bounded-root-inventory-v1` freezes the numerical policy below. It is not
a theorem of physical uniqueness or proof that a finite sample sees every
root. All bin certificates, detected roots, unresolved bins and branch
decisions are retained as diagnostics under the private-output rules.

| Root | Search coordinate/domain | Residual scale and acceptance |
| --- | --- | --- |
| Fixed-T electron charge | `eta=e/(n_H+2*n_He)` on `[0,1]`, with analytic one-sided limits at zero | Charge and element residuals divided by their positive nuclear/charge totals <=`1e-12`; eta bracket width <=`1e-13`. Analytic physical-limit handling precedes division. |
| Caloric inversion at fixed rho/u/UV | `log10 T=3+i/256`, `i=0..1280`, initial bins over `[1e3,1e8] K` | `abs(u(T)-u_input)/max(abs(u_input),abs(u(T)),u_c)<=1e-12`, `Delta ln T<=1e-12`. Require one isolated root and positive caloric derivative there. |
| Ordinary thermal equilibrium | Same T grid, fixed rho/UV | `abs(Lambda)/max(C_total+H_total,1e-80 erg cm^-3 s^-1)<=1e-12`, `Delta ln T<=1e-10`. Retain all roots, not merely the first stable root. |
| Threshold/EOS/BE | ISM sections 4a/8a specify finite density, hot-fraction and F coordinates | Use their residual scales/admissibility in addition to this bin-certification policy. |

Each initial bin is either excluded by a validated outward-bounded residual
enclosure that omits zero, or isolated by opposite-sign endpoints plus an
outward-bounded derivative enclosure of fixed nonzero sign. Exact boundary
zeros are explicitly tested and deduplicated only when their certified
isolating brackets coincide. A same-sign sample alone cannot exclude a
tangency or two roots. Bins not certified are bisected dyadically, at most
20 additional levels and 262144 leaves per scalar inventory. Refine isolated
roots by safeguarded bisection (at most 256 iterations) until both width and
residual criteria pass. Include rounding/truncation error of nested charge
solves in enclosures; an unvalidated libm interval estimate cannot be called
a certificate. The independent REANA oracle must audit the enclosure/root
implementation. The particular future interval library/rounding
implementation is not selected or licensed by this document.

Failure to isolate/exclude a bin is `UnresolvedRootInventory`; there is no
fallback to a sign scan or a single Newton iterate. A caloric inventory with
zero roots gives `NoCaloricRoot`, more than one `MultipleCaloricRoots`, and
nonpositive/uncertified heat capacity `CaloricBranchInvalid`. Out-of-domain
energy gives `EnergyOutsideEvaluationInterval`; return the original
rho/u/UV identity, bounds and residual evidence, without clipping T or
reusing a neighbouring solution. Caloric multiplicity is not resolved by
history in this initial profile. A generic missing physical source is
`SourceIdentityError`, distinct from a numeric root failure.

A thermal root is labelled isochorically restoring only if the interval
for `dLambda/du` is strictly positive on its isolated neighbourhood; this
is the local stability diagnostic for `du/dt=-Lambda/rho`. Negative is
unstable and a zero/uncertified sign is marginal/unresolved. For a specified
initial T, the adjacent enumerated roots/domain ends bound its scalar
cooling basin. Select the first restoring root in the direction set by
the signed initial cooling rate only when every intervening bin is
certified and no root is crossed; otherwise return `ThermalBranchLost` or
`MultipleThermalBranches`. Multiple roots elsewhere remain visible.
An initial exact restoring root stays at it; no finite-time step jumps
across it. This scalar rule does not prove stability of consuming
multiphase dynamics; the ISM's regulation criterion and finite-phase
perturbation evidence are separate. No physical threshold, root count or
stability outcome is supplied by this source-only revision.
An empty thermal-root inventory is a valid reported inventory; a request
for an equilibrium then returns `NoThermalRoot`. Ordinary evolution can
continue within its certified domain without a thermal fixed point, but
cannot step outside that domain. An exact unstable starting equilibrium is
reported as `UnstableThermalInitialRoot` for branch-selection requests.
An exactly certified marginal root is `MarginalThermalRoot`; if the
neighbourhood or zero derivative cannot be certified, use
`UnresolvedRootInventory` instead of inventing a stability sign.

## 5. CMB audit and adopted signed exchange

KWH Eq. (24), p. 24, is

```text
C_KWH_highT = 5.41e-36*n_e*T*(1+z_uv)^4  [erg cm^-3 s^-1].
```

It is a high-temperature loss approximation, not a complete heating law.
For the selected reference use the separately named
`cen92-thomson-cmb-codata2022-fixsen09-v1`. Cen Eq. (17), p. 346,
visually checked in the original, is

```text
dU_th/dt = -(8/3)*sigma_T/(m_e*c)*(n_e/n_part)
           *(1-T_r/T)*E_r*U_th.
```

Cen's `u` in that equation is an **internal energy density**, unlike the
specific `u_h` in the ISM contract; `E_r` is radiation energy density.
Substitute `U_th=3*n_part*k_B*T/2` and blackbody `E_r=a_R*T_r^4` to get
the adopted volumetric **loss** convention:

```text
T_r = T_CMB,0*(1+z_uv)
a_R = 8*pi^5*k_B^4/(15*h^3*c^3)
C_CMB = 4*sigma_T*a_R*k_B/(m_e*c) * n_e*T_r^4*(T-T_r).
```

This derivation, rather than an invented replacement for `5.41e-36`, fixes
the normalization and sign. It gives heating for `T<T_r`, zero at `T=T_r`,
and cooling for `T>T_r`; exactly zero electrons gives zero exchange.
It does not impose `T>=T_r` as a pressure/temperature floor. Evaluate the
law in SI with `n_e` converted once, or entirely in cgs with consistently
converted constants, and compare both paths in prospective fixtures.

The selected central `T_CMB,0=2.72548 K` is from Fixsen's arXiv v2 abstract
and determination (`±.00057 K` measurement uncertainty). Holding the central
value fixed is an engineering input, not a statement that the measurement
is exact. This is an amendment to historical KWH normalization. The pinned
2022 CODATA listing gives:

| Constant | Value adopted in shared SI map | Status |
| --- | --- | --- |
| `k_B` | `1.380649e-23 J/K` | Exact SI defining value |
| `h` | `6.62607015e-34 J s` | Exact SI defining value |
| `c` | `299792458 m/s` | Exact SI defining value |
| `m_p` | `1.67262192595e-27 kg` | CODATA central value; not exact |
| `m_e` | `9.1093837139e-31 kg` | CODATA central value; not exact |
| `sigma_T` | `6.6524587051e-29 m^2` | CODATA central value; not exact |

Compute `a_R` from the defining constants, with the exact expression and
floating-point convention pinned; do not independently round it and the
derived coefficient inconsistently. SI/cgs conversions and changed CMB
normalization require numerical review/fixtures, not local probes here.

The assumptions are Thomson scattering, blackbody CMB and nonrelativistic
thermal electrons with the same temperature as ions. No Klein–Nishina,
relativistic, two-temperature or diffuse X-ray Compton correction is
implied. Cen's adjacent Eq. (18) treats an X-ray background separately;
it is deliberately not part of this reference. CMB exchange already
includes both heating and cooling; do not also add the KWH term.

## 6. Selected FG20 history, bytes, interpretation and license audit

The [author page](https://galaxies.northwestern.edu/uvb-fg20/) links
[`fg20_102720_rescaled.zip`](https://galaxies.northwestern.edu/files/2020/10/fg20_102720_rescaled.zip).
The ZIP contains the **default**, `.68` heating-rescaled and optically thin
tables, spectra and README; its filename does not mean every member is
rescaled. Archive SHA-256:

```text
587a27854de50c95d79901b514d9acee421119ca41ff483eaeea84b6d695d49d
```

Selected member: `fg20_treecool_eff_default.dat`, 15,210 bytes,
195 rows, no header, seven whitespace-separated numeric columns; SHA-256:

```text
c6e6030be92c6965c019c53915f31661782eb2cafed058cf9672b7efefc24aaa
```

README SHA-256:

```text
df0e37f35c9b8abae618094e162b5a9ef0133be5a119cb8e2957200e05e88939
```

The author's README explicitly identifies the columns as
`log(1+z), Gamma_HI, Gamma_HeI, Gamma_HeII, qdot_HI, qdot_HeI, qdot_HeII`.
`Gamma` has units `s^-1` and `qdot` has units `erg s^-1` **per target atom**.
FG20 Eqs. (7)-(8) and (27) verify the latter normalization:

```text
Gamma_i = 4*pi*integral_nu_i^infinity J_nu*sigma_i/(h*nu) dnu
qdot_i = 4*pi*integral_nu_i^infinity
         J_nu*sigma_i*(h*nu-h*nu_i)/(h*nu) dnu
H_photo = n_HI*qdot_HI + n_HeI*qdot_HeI + n_HeII*qdot_HeII.
```

A six-rate input already contains the `4*pi` and cross-section integrations.
Do not multiply by them again, divide `qdot` by `Gamma`, or multiply by
electron density. Cross-section data is therefore **not a blocking input
for this selected table path**. Direct spectral recomputation would require
its own complete cross-section and integration audit; KWH's Osterbrock
reference alone is not that audit.

The author README distinguishes:

| Member | Meaning | Selection |
| --- | --- | --- |
| `fg20_treecool_eff_default.dat` | Fiducial FG20, default reionization parameters in the paper | Selected; gives the published default a reproducible name |
| `fg20_treecool_eff_rescaled_heating_rates_068.dat` | Same effective model, **all three photoheating** rates multiplied by `.68` to match Gaikwad et al. 2020 calibration | Audited identity only, not adopted; no second rescaling |
| `fg20_treecool_thin.dat` | Direct homogeneous-background spectral integrals, invalid homogeneous assumption before reionization | Not selected; useful distinct comparison input |
| `fg19_updated031220.zip` on the page | Earlier FG19 reference model | Not downloaded/adopted; not interchangeable with FG20 v2 |

FG20 section 3 constructs **effective** rates before reionization for
homogeneous photoionization-equilibrium simulations; no corresponding
effective spectrum is supplied. At late times the rates are spectral
integrals. Section 3.3/Eqs. (33)-(34) give fiducial reionization parameters,
including H I `z_rei=7.8` and He II `z_rei=3.5`; this is not SH03's `z~6`
modified HM96 history. The first isolated `z_uv=0` use does not simulate
these reionization events. Changes of UV model, history, normalization or
effective/thin/rescaled choice invalidate threshold/EOS calibration hashes.

### Table axis and interpolation contract

Use `q=log10(1+z)`. The README writes `log(1+z)` without spelling out the
base; the base-ten interpretation is supported by Appendix D's redshifts/
rates and the unselected thin table's `q=1.0413926851582251` endpoint for
the stated `z=10` limit. Retain this interpretation in the model manifest
and independently confirm it in the future printed-row parser fixtures;
it is not an inferred AREPO code path.
The selected table's axis runs from `q=0.000` through `0.970`, in steps
`.005`, inclusive. Its exact redshift domain is
`0<=z<=10^0.970-1`. This is **not** the spectrum's nominal `z<=10` domain.
The selected effective table has tiny positive `1e-40` entries; retain
them as table data, not an inferred exact zero or a floating-point floor.
No extra rows are invented beyond the supplied axis.

Freeze independent interpolation `fg20-lograte-log1pz-v2` (the v1 intent
with explicit floating-point boundaries), using IEEE binary64 round-to-
nearest ties-to-even. Queries have distinct `NodeIndex(i)`, `AxisQ(q)` and
`Redshift(z)` variants. `NodeIndex` (`0<=i<195`) and an `AxisQ` bit-equal
to a parsed axis value return the **parsed row exactly**, without log/exp.
For other interior q, linearly interpolate `log10(rate)` in q for each of
the six positive channels and exponentiate. Do not snap near an interior
node; an inverse-redshift round trip is not promised to identify that node.
The independent formula oracle checks implementation agreement, not
accuracy against an unavailable exact effective UV spectrum.

Canonical parsed axis nodes are `q_i=RN64(i/200)`, `i=0..194`.
`q_hi=q_194`, `z_hi=RN64(10^(97/100)-1)`; RN64 here defines rounding of
the mathematical value, not a promise that an arbitrary system pow/log
implementation is correctly rounded. Their reference bit patterns and
log/exp error bounds must be generated/verified independently on REANA
before use; no numeric bit vector is fabricated in this task. The query
boundary policy is deliberately narrow and asymmetric at zero:

| Query | Frozen action |
| --- | --- |
| q or z equals +0 or -0 | Canonical zero; return first row. |
| `AxisQ(q_hi)` or `Redshift(z_hi)` | Return final parsed row. |
| Exactly `nextUp(q_hi)` or `nextUp(z_hi)` | Normalize to final node, return an `EndpointRounded` flag. This single-ULP input normalization is declared; it is not interpolation beyond the source domain. |
| Two or more representable values above the upper bound | `UvOutOfRange`; no tolerance scaled to the whole table. |
| Any negative nonzero q/z, including `nextDown(0)` | `UvOutOfRange`; no negative-redshift extrapolation. |
| `nextDown(q_hi)` or another interior q | Interpolate; no blanket endpoint snapping. |
| Interior redshift z | Form q with an independently bounded `log1p(z)/ln(10)` path; then apply the q rule. If rounding places q one ULP above q_hi, use the same flagged normalization; a larger excursion is `UvTransformError`. |
| NaN or infinity, invalid NodeIndex | Typed input error, no evaluation or state mutation. |

Parsing first checks the immutable selected member's exact byte hash and
15,210-byte length, then ASCII (no BOM), exactly 195 nonempty records and
seven finite decimal/scientific-notation tokens per record, each of six
rates strictly positive, and the exact decimal axis `i*.005`. Whitespace
within the already hashed file is accepted; a header, duplicate/missing/
out-of-order axis, extra column, zero/negative/nonfinite rate, wrong member
or changed printing is an error, never sorted/repaired or silently accepted
under the FG20 identity. Hash/format errors retain the private input handle
and record number, not offending table lines in logs. Synthetic parser
fixtures use a separately labelled identity/schema; they cannot impersonate
the selected hash. A zero-aware table is a different profile. There is no
UV shutoff, spectrum reconstruction or logarithm of signed net cooling.

Appendix D Table D1 on arXiv PDF p. 20 was visually checked against the
archive's conventions and late-time values. It is a coarser printed table,
not a substitute for the selected 195-row file. Future parser fixtures must
independently check several printed rows, table-axis interpretation,
first/last rows and exact-node preservation. These are prospective tests,
not executed numerical comparisons in this task.

### Redistribution finding (unresolved, explicitly bounded)

The author page offers downloads and README gives instructions for using
TREECOOL data in simulations. **Neither the downloaded page, README nor
archive contains a LICENSE/COPYING file or an explicit grant to redistribute
or relicense the data.** The arXiv record's license is nonexclusive
distribution to arXiv, not a verified downstream data license. The attempted
published PDF download is an access-denied response, not license evidence.
Thus the author-provided scientific use context is verified, but a
redistribution grant compatible with vendoring/public redistribution is
**not verified**. Do not label this dataset MIT, BSD, CC BY, or public domain.

The accepted **source-design route** is operator-supplied immutable PRIVATE
input, not an approved public data-distribution path. Concrete platform
access/retention verification and applicable operator authorization are
still execution prerequisites, not permissions inferred from this review.
No user permission or external contact is requested in this source task.
Before public redistribution, archive a verified applicable grant or audit
an explicitly licensed replacement, name it and recalibrate. No fetcher,
mirror, repo raw-data import, raw public workflow input/output or claim
that MIT covers the data is part of this contract.

### 6a. Private input API and artifact boundary

Design-only Rust interface (no implementation/dependency selected):

```rust
struct PrivateUvInputHandle { /* operator-bound read-only capability */ }
struct UvIdentityReceipt { /* source URLs, model/member names, lengths, hashes */ }
struct PrivateUvModel { /* immutable parsed bytes/rows; not Serialize or Debug */ }
fn load_private_uv(handle: PrivateUvInputHandle, expected: UvIdentityReceipt)
    -> Result<PrivateUvModel, PrivateInputError>;
fn photo_rates(model: &PrivateUvModel, query: UvQuery)
    -> Result<PrivatePhotoRates, UvInputError>;
```

The operator supplies the **member** through a read-only private capability;
the archive need not be uploaded. Independently verify the member hash
before parsing, retain its archive hash as source provenance, and require
the same immutable member on restart. A receipt/hash mismatch fails closed.
The implementation has no URL/network fetch method. Handles contain no
public path/credential and byte buffers/parsed rows cannot be implicitly
serialized or printed. A public config/checkpoint holds the model identity
receipt and z/query policy, not the handle secret, table, row arrays or six
UV-rate values. Restart resolves the private capability anew; missing
input gives `PrivateUvInputUnavailable`, not a cached-table fallback.

| Artifact class | Explicit allowlist / exclusions |
| --- | --- |
| Public provenance receipt | Source URLs, article/version and selected member names, source/implementation/config hashes, byte lengths and instructions to obtain the same operator input independently. No raw lines, rate vectors, private locator or credentials. A hash neither confers permission nor guarantees future availability. |
| Config/checkpoint | Typed physical state, accepted packet/ID/ledger state, radiation redshift and public identity receipt only. No table/archive, parsed table, cached UV samples, six-rate RadiationState serialization or private capability secret. |
| Public diagnostic log | Case IDs, typed error codes, record numbers, counters, normalized errors/root counts and source hashes. No input excerpts, offending tokens, raw photo-rate vectors, interpolation dumps, spectra, table grids or secrets. |
| Public scientific output | Approved derived gas/particle state, T/mu/abundance fields, SFR/metals, integrated source energy budgets and convergence/error summaries. A numerical scan that reproduces the external UV rows/vectors is excluded; publication allowlist review must distinguish physical derived histories from data copies. |
| Private review artifacts | Raw member/optional archive, per-channel UV targets and numerical oracle traces only in the verified private input/review store, under the operator's applicable authorization and retention policy. They never enter the public artifact bundle. |
| Working memory/scratch | Read-only input and immutable memory are preferred. Any required scratch is private, excluded from automatic artifact collection, and subject to the verified cleanup/retention policy; no table copies in configs/checkpoints/logs. |

The future execution packet must record actual input/output access controls,
which principals/services can read them, storage and artifact visibility,
job-log visibility, retention/backups, scratch cleanup, publication export
allowlist and applicable operator authorization. Verify those controls on the
specific platform before submitting a private-input job. **No such remote
access plan, retention guarantee or authorization has been verified here.**
Failure is `PrivateInputPolicyUnverified` and blocks only the dependent
private-data execution; source/algebra and independently generated synthetic
fixtures can be prepared without that data. Do not infer that upload to
REANA is authorized merely because private operator input is a supported
design. Existing ignored local reading material is not a public mirror.

## 7. Domain, integration, threshold and failure behavior

Accept `kwh96-evaluation-1e3-1e8-v1` as the **analytic evaluation interval**
`10^3<=T<=10^8 K`, finite positive density, and the selected UV axis above.
This is a named engineering evaluation scope, not a published physical-
accuracy domain at arbitrary density.
Black p. 557 states roughly `5e3-5e5 K` applicability for his unmodified
expressions; KWH explicitly uses Cen modifications at higher temperature.
The `[1e3,5e3) K` tail is explicitly a model extension beyond Black's stated
interval; KWH's Cen modifications above `1e5 K` are the specified hot-end
lineage, not a new precision guarantee. No source here provides a universally
accurate hard density interval or a justification for optically thin cold
dense gas. Low-density collisional/escape assumptions and the use of hot
coarse-grained density are model limitations to record in each run.

Cooling section 8a freezes actual analytic-model density/T/UV cases. Calling
one of them physically applicable additionally requires measured/justified
optical thinness and low-density escape, electron/ion equilibration and
ionization/recombination relaxation short compared with thermal/dynamical
change. Register the physical parcel/path length and compute
`tau_nu=sum N_i*sigma_i(nu)` from separately audited cross sections if making
that claim; a six-rate input alone does not supply an optical-depth audit.
As a quantitative engineering applicability gate require the slowest
nonconserved relaxation time of the independently constructed local
ionization-rate Jacobian <=`.01*min(t_thermal,t_dynamical,t_flow)` where
finite, with `t_thermal=U_th/[V*(C_total+H_total)]`, `t_flow=ell/|v_rel|`
and a separately justified electron-ion equilibration time. Require
`tau_nu<=.01` at the relevant edges/weighted bands and compare collision
rates with audited critical-density/de-excitation rates where physical
accuracy is claimed. Missing path, cross sections, critical-density or
equilibration evidence leaves a fixture an **analytic-model equation test**,
not a failed numerical test and not a physically validated plasma model.
The thresholds `.01` are engineering applicability criteria, not KWH
constants. Physical galaxy applicability is a separate dependent G3/G4
review; no invented source values satisfy it here.

No public density/temperature table is substituted for this analytic
network. The fixed `1000 K` cold-cloud reservoir is never cooled through
this ordinary/hot backend. An attempted hot/ordinary state outside an
accepted domain returns `RateDomainError` and preserves the failed state;
it does not impose a cell temperature, energy or pressure floor. The first
physical packet must bound initial and expected evolved states, register
domain checks, and stop if they are exceeded. A larger or different network
requires primary sources and a new model revision.

Recommended initial implementation is direct coefficients plus nested
bracketed abundance/temperature solves, not a precomputed cooling curve.
The ISM integrator owns conservative implicit source transactions, event
locations and retries; this backend is a pure rate evaluator. It cannot
mutate energy, create stars or choose a timestep. Return
`C_j,H_photo,C_CMB,T,mu,species,residuals,model_hash` with distinct errors
for domain, malformed data, root ambiguity, nonconvergence and source
identity mismatch. No derivative is exposed until its implicit-ionization
dependence is derived and tested; an ordinary frozen-species derivative
cannot be labelled the full equilibrium derivative.

For ordinary cooling, solve `dU/dt=-V*Lambda_net` with the conservative
source stepper. Subdivide/retry on its accuracy bound or located thermal
equilibrium/ISM branch event. Energy is not clipped after the solve.
For multiphase cooling the ISM `f` switch controls whether a positive rate
forms cold mass or acts as a hot thermal loss. Negative net loss is heating
and never a positive condensation rate. Store gross cooling and heating
separately even when they nearly cancel. No caller can add both signed CMB
and its positive-only historical approximation.

Threshold/EOS calibration is a dependent numerical deliverable:

1. Pin atomic correction, constants, composition, CMB mode, FG member,
   interpolation and `z_uv`, as well as `u_c,u_SN,A0,beta,t0` and `u_4`
   conventions in the ISM specification.
2. Implement/compare the published SH03 Eq. (23) approximation and the
   explicitly amended `full-rate-continuity-v1` scalar root from the ISM
   contract. UV-dependent ionization/heating and CMB terms do not generally
   scale as `rho^2`; do not cancel density dependence to force Eq. (18).
3. On REANA, archive brackets, all candidate roots, branch/uniqueness
   evidence, threshold, EOS/cold fractions, pressure/energy continuity
   residuals and the ordinary thermal-equilibrium difference from the
   chosen `u_4`. No adopted numerical threshold exists yet.
4. Calibrate the reference at frozen `z_uv=0`. Varying the UV redshift or
   model requires an explicit decision to recompute the threshold/EOS or
   retain a fixed calibration as a named variant; neither is automatic.

## 8. Prospective REANA fixtures and first implementation slices

All entries below are **unimplemented/unexecuted**. Follow the ISM
specification's one-zone, branch, ledger, timestep and isolated-disk gates
as well as these backend cases. Each temperature/density/redshift/model
member is an independent REANA workflow, ready cases submitted concurrently,
with declared resources and no aggregate CPU/memory cap. A shared immutable
build/preflight dependency may precede them; use 2 threads/8 GiB there and
1 thread/2 GiB per scalar-rate case, no nested thread pools.

| Fixture family | Measurements and proposed gate |
| --- | --- |
| `rates-coefficients` | Independently transcribed Table 1/2 formulas and independently evaluated reference values for every channel at registered temperatures including `1e3,1e4,1e5,1e6,1e8 K` where accepted. Relative error <=`1e-10` with declared absolute zero scale; report underflow separately. Include C1 sign evidence and verify that the positive printed exponent is not production behavior. |
| `rates-ionization` | UV-zero and selected UV cases over density/T ladder; nuclear and charge normalized residuals <=`1e-12`, species nonnegative, neutral/fully ionized limits, zero-electron physical branch, self-consistent `u-T-mu` round trip <=`1e-10`. Independent reference must not call the production solve. |
| `rates-uv-input` | Hash failure/malformed table errors, 195 rows/seven columns, axis ordering, exact nodes and independent printed Appendix D checks; no mutation on invalid input. Interpolation agrees with independent formula <=`1e-12`; all endpoint/out-of-domain behavior explicit. This does not quantify FG20's observational uncertainty. |
| `rates-cmb` | Signed Cen expression, zero electrons, `T=T_r`, both signs around it, SI/cgs equality <=`1e-12`, high-T trend and recorded normalization difference from KWH. Use a separate pure Compton fixture near CMB temperatures, bypassing the named atomic evaluation interval; this does not extend the full network domain. |
| `rates-net-balance` | Independently sum each physical channel and verify sign changes/near cancellation without log(net). Relative channel errors <=`1e-10`, net absolute tolerance based on gross-channel scales, not division by a vanishing net. |
| `rates-domain` | Every boundary, invalid density/energy/z, failed bracket, no root and ambiguous root returns a typed failure and preserves input/source IDs; no invented extrapolation, clipping or floors. |
| `rates-thermal-time` | Ordinary one-zone implicit cooling/heating with independent high-accuracy oracle, constant-density runs and dt ladder. Finest scaled temperature/energy error <=`1e-3`, first-order fitted slope >=`.9`, integrated channel/source balance <=`1e-10`; no unregistered equilibrium crossing. |
| `rates-threshold` | Selected full-rate threshold roots and approximate SH03 comparison. Equilibrium residual <=`1e-12`, one-sided amended pressure/energy jump <=`1e-8`, all roots and approximation differences retained. No pass if rate/domain/license input requirements are missing. |

Before implementation, independently review the revised solver, evaluation
interval and private-input policies against the conditional source approval.
After permitted M1
prerequisites, the first reviewable slices are (1) typed pure coefficient
and constants functions with explicit correction ID, (2) immutable photo-rate
parser/interpolator and manifest validation, (3) ionization and `u-T` roots,
(4) channel assembly/CMB evaluator and typed failures, then (5) threshold
calibration and the already specified conservative ISM integration. Each
slice's executable verification runs only on REANA. Actual fixture inputs
are registered in section 8a and ISM section 9a; reference values,
container/source hashes and independent reducer identities must be frozen
before running. This design supplies no manufactured
successful outcomes.

Remaining unavailable inputs are the exact historical SH03-modified UV
history, verified FG20 redistribution permission, and direct final FG20
published-PDF comparison. Those limitations are distinct from the now
transcribed atomic/CMB equations and actual downloaded default FG20 rates.
Numeric threshold/EOS calibration and all scientific execution/acceptance
remain future gated work, not source facts.

### 8a. Registered scalar inputs and oracle independence

Registry `ism-cooling-cases-v2` below is **design data**, not an executable
packet or evaluated reference output. Every Cartesian-product member or
malformed-input variant is a separate future REANA case/workflow after
M1, applicable source/design review and an immutable implementation/build
preflight. Scalar cases use 1 thread/2 GiB; shared preflight uses 2 threads/
8 GiB. Ready independent cases run concurrently without an aggregate cap.
Private FG20 cases additionally wait for section 6a's authorization/access/
retention verification. Zero-UV and independently generated synthetic
cases have no dependency on that private table. No workflow is launched now.

| Case IDs | Frozen inputs | Independent oracle and gate |
| --- | --- | --- |
| `CR-C01(T_i)` | Each of the 10 cooling and 7 ionization coefficients at T=`[1e3,5e3,1e4,1e5,5e5,1e6,1e8] K`; constants/composition fixed above. Channel-assembly vector `(ne,nHI,nHII,nHeI,nHeII,nHeIII)=(7,2,3,5,11,13) cm^-3` deliberately tests nonunit density and charge factors, not charge-equilibrated plasma. | Separate 80-decimal transcription from KWH/Cen/Black locators, not the production coefficient functions; each coefficient/channel `abs(error)<=1e-10*abs(ref)+1e-300` in its stated unit. Record underflow; no unit-density-only shortcut. This tests adopted model equations, not atomic-data accuracy. |
| `CR-C02(n_i,T_j,U_k)` | `n_H,hot=[1e-8,1e-6,1e-3,1,1e2] cm^-3`, the preceding seven T, UV=`zero` or `private-FG20-default-z0`; `rho_h=m_p*n_H,hot/X`. For caloric inversion, request the energy formed independently from the specified T and abundance oracle. | Independent high-precision normalized H/He chain plus charge solver, separate from production enclosures; nuclear/charge residual <=`1e-12`, u/T round trip <=`1e-10`, retain full T-root inventory. These are analytic-model cases, including densities not granted universal physical applicability. |
| `CR-C03-SYN(kind)` | Pure root-policy providers: with `w=log10(T)-5.5`, caloric `u=u_c+u_SN*(20+w^3-w)`, request `u_c+20*u_SN`; thermal `Lambda=C0*(w+1)*w*(w-1)`, monotone caloric `u=u_SN*T/1e6`, `C0=1e-23 erg cm^-3 s^-1`. Nonnegative channels are `C=C0*(1+max(poly,0)), H=C0*(1+max(-poly,0))`. Start T=`1e4` or `1e7 K` in separate cases. | Analytic roots `w=-1,0,1`: caloric multiplicity must fail, not select one; thermal inventory retains all three and selects the connected restoring low/high branch respectively. These manufactured providers are not a primordial cooling curve. |
| `CR-C03-SYN-NO/TANGENT` | Caloric `u=u_SN*T/1e6`, target `u_SN*1e3` (above the finite T interval); thermal `Lambda=C0` or `C0*(w-.5)^2`. | `EnergyOutsideEvaluationInterval`, empty thermal inventory/`NoThermalRoot`, or marginal exact-node tangent/`MarginalThermalRoot`, respectively. Uncertified tangent bins fail `UnresolvedRootInventory`; never silently report no root from same-sign endpoints. |
| `CR-C03-SYN-TH/EOS` | Pure threshold residual in `q=log10 n_H,total`: `R0*(q+4)*q` or `R0`, `R0>0`, over the registered density bracket. EOS continuation provider `g=.04*(1-2*s)-(x-.5)^2`, `s=log10(rho/rho_th)/3`. | Two threshold candidates or none produce the matching typed errors. EOS restoring branch starts at x=.7, reaches a marginal fold at s=.5 and is lost beyond it; no jump to a disconnected/borrowed root. No physical density threshold is inferred from these polynomials. |
| `CR-C04-FG-NODE/MID(i)` | Private selected input; all `NodeIndex(i)`, i=`0..194`, and q-midpoints `(2*i+1)/400`, i=`0..193`. | Independently parsed decimal bytes and 80-decimal log-interpolation expression. Exact nodes preserve parsed bits; normalized interpolation disagreement <=`1e-12`. Printed Appendix D comparisons use its displayed precision only. Numerical vectors/oracle targets stay private. |
| `CR-C04-EDGE(type,side)` | Both q/z interfaces: exact endpoints, adjacent representable values on each side and two ULPs outside, +/-0, NaN, +/-infinity; invalid node indices -1 and 195. | Section 6 actions/flags exactly; independent correctly rounded mathematical endpoint definitions and transform checks. No interior-node fuzzy snapping. |
| `CR-C04-MALFORM(kind)` | Wrong member/hash/length; header/BOM; 194/196 records; 6/8 columns; duplicate/reversed/missing axis; zero, negative, NaN/infinite or nonnumeric rate; extra token. | Production identity failures precede parsing. Isolated parser-error cases use explicit synthetic expected-byte receipts so their structure checks are reached; no changed file may retain FG20's identity. Errors/logs contain codes/record numbers, no raw UV values or excerpts. |
| `CR-C04-SYN` | Independent three-row parser schema, q=`[0,.5,1]`; each row's six rates is `[a,2a,3a,4a,5a,6a]` with a=`[1,10,100]` in the declared units. Node/midpoint queries and the malformed variants above. | Exact powers and log-linear interpolation supply a data-independent formula oracle; labelled synthetic, never selected as FG20 or as physical radiation. |
| `CR-C05(ne,z,T)` | Pure CMB: ne=`[0,1e-8,1,1e2] cm^-3`, z=`[0,3]`, T=`[T_r/2,T_r,2*T_r,1e3,1e8] K`; no atomic call below 1e3 K. | Independent cgs versus SI derivations, normalized difference <=`1e-12`, exact zero/sign checks; compare the high-T KWH normalization without adding it. Constants use independent NIST transcription. |
| `CR-C06(sign,k)` | Manufactured gross C=`C0`, H=`C0*(1+sign*2^-k)`, sign=`[-1,+1]`, k=`[0,20,40]`, `C0=1e-23 erg cm^-3 s^-1`. | Exact difference and sign, error scaled to C+H (absolute `1e-12` of that scale); no division by vanishing net or log(net). Physical channel assembly is separately checked by C01/C02. |
| `CR-C07-ROOT(n_i,U_k)` | For every C02 density and UV state, enumerate caloric/ordinary thermal T bins from section 4a. For physical SH03 threshold/EOS use the finite total-density and h brackets in ISM 4a, no guessed numeric threshold. | Separate interval/root inventory plus a separately written high-precision species solver; audit excluded bins/tangencies, all root brackets and derivative signs. Empty/multiple/lost branches follow typed policies. Actual calibration and stability remain future observations. |

All arbitrary-precision reference code is to be written independently of
the production Rust coefficient, root and source routines. Do not call those
routines through FFI or use their cached tables/Jacobians as oracle inputs.
Freeze oracle source/container versions and bytes in the future immutable
packet. For scalar values use at least 80 decimal digits and repeat at 100;
the change must be <=`1e-20` of the declared nonzero comparison scale.
For roots require both independently verified residuals and finite bracket
coverage, not matching one production iterate. The oracle is not thereby
experimental atomic truth. No numerical references, transform bit vectors,
root counts for the physical model or pass/fail results were generated here.

Source, parser and analytic one-zone fixtures must not write private table
values into public config/checkpoint/log artifacts. Section 6a controls
their outputs as well as runtime outputs. Public receipts carry identity
and acquisition instructions; detailed private oracle traces require the
same verified access/retention boundary as the input.
