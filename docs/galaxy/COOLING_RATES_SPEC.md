# Primordial cooling, ionization and UV source contract

Status: **source/design only; unimplemented, unexecuted and not accepted**,
2026-11-22. This is the thermal backend for
[ISM_STAR_FORMATION_SPEC.md](ISM_STAR_FORMATION_SPEC.md), subject to the
[shared integration contract](INTEGRATION_CONTRACT.md). The byte inventory,
equation map, retrieval failures and license findings are in
[cooling_rates_sources.json](cooling_rates_sources.json). No AREPO/GADGET
code was copied. Reading, PDF rendering, transcription and file-integrity
checks are the only local execution in this audit.

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
it does not replace independent review or REANA validation. Source review of
C1, the requested validity domain and the UV-use/distribution boundary,
followed by rate fixtures and threshold calibration, remains a prerequisite
to physical G3 runs. Pure interfaces and independently written equation
kernels can be prepared after M1 permits that implementation slice.

## 2. Primary sources and version control

| Source | Consulted version and exact locators | Role/limitation |
| --- | --- | --- |
| [Katz, Weinberg & Hernquist 1996](https://articles.adsabs.harvard.edu/pdf/1996ApJS..105...19K), ApJS 105, 19-35, DOI 10.1086/192305 | Final published pp. 24-25, Tables 1-2, Eqs. (23)-(40); also complete [arXiv v1](https://arxiv.org/pdf/astro-ph/9509107v1), including Table 1 on PDF p. 13 | Primary adopted primordial network. Published Table 1 and preprint differ at C1. Rendered original tables were inspected; extracted mathematical glyphs alone were not trusted. |
| [Black 1981](https://articles.adsabs.harvard.edu/pdf/1981MNRAS.197..553B), MNRAS 197, 553-563 | Final pp. 556-557, Eq. (9), Table 3 | Primary source cited by KWH; corroborates negative dielectronic exponent. Its larger network is not imported. |
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
coefficient magnitude is inferred. An independent source reviewer must
confirm this finding before physical execution. This audit is evidence of
a source discrepancy, not a claim to have found an official erratum.

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

For energy input, `temperature_from_thermal_energy` brackets roots of
`3*k_B*T*n_part(T)/(2*rho_h)-u_h=0` in the accepted domain. Each temperature
trial uses the ionization solve. Reject an unbracketed or ambiguous root
and report the input/residuals. Do not reuse a neutral or fully ionized
`mu` for all temperatures. Thermal equilibrium is a **different** root of
`Lambda_net=0` and can have multiple stable/unstable branches. Any cached
table must retain this distinction and the full model identity.

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

Proposed independent interpolation `fg20-lograte-log1pz-v1`: at an exact
stored axis point return the parsed row; otherwise linearly interpolate
`log10(rate)` in `q` for each of the six positive rates separately and
exponentiate. `z=0` returns the first row. Reject negative, nonfinite or
out-of-range `z`, malformed/misordered rows and nonpositive rates in this
profile. No extrapolation, clamping, UV shutoff, spectrum reconstruction,
or net-rate logarithm is allowed. This is an **engineering** interpolation
choice, not a verified AREPO algorithm or an instruction printed by FG20.
If another table includes exact zeros, it needs its own explicit zero-aware
rule; do not apply this positive-table profile silently.

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

Selection is conditional on an **external-input** model: a future run
manifest identifies the author URL, archive/member hashes and the table
supplied by the operator; source code is independently written. This design
does not authorize a fetcher, mirror, repo data import, workflow data
publication or a legal conclusion. Before such redistribution, obtain and
archive a specific permission/license or audit an explicitly licensed
replacement and name/recalibrate it. No message to an author or external
service was sent. This remaining source/packaging dependency is a finding,
not replaced by an assumed license or an invented UV curve.

## 7. Domain, integration, threshold and failure behavior

The proposed *requested* thermal domain for source review/fixtures is
`10^3<=T<=10^8 K`, finite positive density, and the selected UV axis above.
This is an engineering domain request, not a published accuracy guarantee.
Black p. 557 states roughly `5e3-5e5 K` applicability for his unmodified
expressions; KWH explicitly uses Cen modifications at higher temperature.
The whole requested KWH fit domain, especially its low-T tail and hot SN
end, must be independently reviewed. No source here provides a universally
accurate hard density interval or a justification for optically thin cold
dense gas. Low-density collisional/escape assumptions and the use of hot
coarse-grained density are model limitations to record in each run.

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
| `rates-cmb` | Signed Cen expression, zero electrons, `T=T_r`, both signs around it, SI/cgs equality <=`1e-12`, high-T trend and recorded normalization difference from KWH. Use a separate pure Compton fixture near CMB temperatures, bypassing the requested atomic-domain bound; this does not extend the full network domain. |
| `rates-net-balance` | Independently sum each physical channel and verify sign changes/near cancellation without log(net). Relative channel errors <=`1e-10`, net absolute tolerance based on gross-channel scales, not division by a vanishing net. |
| `rates-domain` | Every boundary, invalid density/energy/z, failed bracket, no root and ambiguous root returns a typed failure and preserves input/source IDs; no invented extrapolation, clipping or floors. |
| `rates-thermal-time` | Ordinary one-zone implicit cooling/heating with independent high-accuracy oracle, constant-density runs and dt ladder. Finest scaled temperature/energy error <=`1e-3`, first-order fitted slope >=`.9`, integrated channel/source balance <=`1e-10`; no unregistered equilibrium crossing. |
| `rates-threshold` | Selected full-rate threshold roots and approximate SH03 comparison. Equilibrium residual <=`1e-12`, one-sided amended pressure/energy jump <=`1e-8`, all roots and approximation differences retained. No pass if rate/domain/license input requirements are missing. |

Before implementation, independent review must sign off this transcription,
C1, the requested domain and the external-data policy. After permitted M1
prerequisites, the first reviewable slices are (1) typed pure coefficient
and constants functions with explicit correction ID, (2) immutable photo-rate
parser/interpolator and manifest validation, (3) ionization and `u-T` roots,
(4) channel assembly/CMB evaluator and typed failures, then (5) threshold
calibration and the already specified conservative ISM integration. Each
slice's executable verification runs only on REANA. Actual fixture input
values, reference values, container/source hashes and independent reducer
must be frozen before running; this design supplies no manufactured
successful outcomes.

Remaining unavailable inputs are the exact historical SH03-modified UV
history, verified FG20 redistribution permission, and direct final FG20
published-PDF comparison. Those limitations are distinct from the now
transcribed atomic/CMB equations and actual downloaded default FG20 rates.
Numeric threshold/EOS calibration and all scientific execution/acceptance
remain future gated work, not source facts.
