# Independent AI review: softened equilibrium and IC sampling

2026-11-22. **Conditional source/design support, with two reference/diagnostic
clarifications required before freezing the DF/live packet.** The manual
derivations support E1-E5 and the proposed 90-byte/open52 address contract.
The tapered profile is a defensible, falsifiable first G-EQUIL-SOURCE target;
its DF positivity and numerical realization are unknown. Clarify the
Newtonian/untapered control (finding 3) and the virial kinetic-energy frame
(finding 6). A narrow pure-kernel slice is eligible only after the coordinator
records the M1 and implementation prerequisites. This independent **AI**
review is not human peer review, an implemented equilibrium, an accepted
sampler, a galaxy IC or M1 acceptance.

Reviewed equilibrium commit **E** is
`17f85f91a327f8f84d6af4f36f5f3962cc789515`; sampling commit **S** is
`3c521fb88cd35e0f947c88ff5c246d2f687bdfed`. Shared units/ID/gravity/ISM/source
interface context is pinned at **C** =
`a7ef08679cdfce686fc60e431c85c82ae0dfb65f`, irrespective of later live edits.
Observed HEAD at entry was `d12810c3db1561946d3665dad6f7dede9de91e10`.
Below, **EN** means the source note at E, **RS** the sampling spec at S,
and **GP** the gravity contract at C; line numbers refer to those bytes.

| Reviewed subject | SHA256 |
| --- | --- |
| SPHERICAL_EQUILIBRIUM_SOURCE_NOTE.md | `e8aa38178f54ecea765c0b9be7c63c8810571ea81f17d3d1cb900f1946df8798` |
| spherical_equilibrium_sources.json | `01f74be14f380019a47e991d199f2719d4c6a08bd0fe77f80df1b72214316d94` |
| RANDOM_SAMPLING_SPEC.md | `2a5fa6e16d609bb1a8ae91c4905221d73e88b12b0f0a63be1d547b23408f7045` |
| random_sampling_sources.json | `c50a28d1a3669a581d073aa6f1140f244b555c1350892967c20537ca86aa8727` |

The [review inventory](equilibrium_sampling_review_sources.json) pins all
context and primary bytes, actual inspection scopes and manual arguments.
Both author inventories' subject and historical-context receipts match their
stated revisions; their older ISM receipt is not a claim about the revised
ISM context at C. All 15 retained source/render/extracted-vector artifacts
and all 29 NIST archive-member length/hash receipts checked without mismatch.
Direct PDF renders were inspected in memory. Source/document hashing is
integrity work: **no SHA test vector, address/digest draw, RNG mapping probe,
quadrature, DF/CDF evaluation, sampling, build, test or evolution was run**.
Only the two assigned new review files were written.

| Primary source bytes actually consulted | Equation/page scope and limits |
| --- | --- |
| [Barnes 2012 v3](https://arxiv.org/pdf/1205.2729v3), SHA256 `124bb32e6ff58aaf7aeba2f6ecd1556c334000b9ff42aef2e08c3f4d63c55282` | Complete 17-page PDF retained. PDF/printed pp. 2,6-8 read; pp. 6 and 8 rendered directly. Eq. (5)-(7), smoothing/source distinction; section 4.1 Eq. (19), isolated potential; section 4.2 Eq. (21), underlying density in softened-potential inversion; p. 7, sampling/probe correlations. Publisher text was unavailable; no equivalence to a final publisher version is asserted. |
| [Eddington 1916](https://articles.adsabs.harvard.edu/pdf/1916MNRAS..76..572E), `28913d32414f33545aba35e8c36b80006f5395f28a3fb8cbf0f59e536be5db2d` | Complete 14-page scan retained. PDF pp. 8-9 / printed 579-580, section 7 and start of 8 read; p. 9 rendered directly, including Abel equations, positivity qualification and finite-cutoff footnote. Historic variables are not copied as the project's normalization. |
| [NIST FIPS 180-4, August 2015](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf), `0455b406d89648d20cbde375561e19c245b9815e894164c2670772e3d54deb82` | Complete 36-page PDF retained; PDF pp. 12,27-28 / printed 7,22-23 read and rendered directly: section 3.1 word/hex convention and sections 6.2.1-6.2.2 SHA-256 computation/output. This is source/interface inspection, not a cryptographic implementation audit or validation. |
| [Official NIST byte-vector archive](https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Algorithm-Validation-Program/documents/shs/shabytetestvectors.zip), `929ef80b7b3418aca026643f6f248815913b60e01741a44bba9e118067f4c9b8` | README and response-file format/header/Len=0 entry inspected; complete archive and five extracted materials checked by byte length/hash. Stored MD values were read, never recomputed as test vectors. Monte Carlo materials are retained, not a claimed executed gate. |

## Findings and implementation dispositions

1. **Supported derivation: angular potential, force and stable center.**
   For `A=r^2+s^2+epsilon^2`, angular integration of the actual GP-2 kernel
   gives `integral_-1^1 (A-2*r*s*mu)^(-1/2) dmu=(s_plus-s_minus)/(r*s)`.
   Since `s_plus^2-s_minus^2=4*r*s`, EN 43-60's two E2 forms agree, including
   the factor `-8*pi*G` in the nonsubtractive form. Differentiation gives
   E3; acceleration is `-Phi'(r)*x/r`, not positive outward force. At the
   center the force is zero and its linearization is `-Phi''(0)*x`.

   `K^2-B^2=4*s^2*epsilon^2` proves EN 65-71's rationalized derivative.
   `K+B>0` for positive epsilon, hence Phi' is strictly positive at r>0 for
   the nonzero positive density. This is an exact-arithmetic sign argument,
   not a floating quadrature certificate. Near r=0,
   `Phi''(0)=4*pi*G*epsilon^2*integral s^2*rho/(s^2+epsilon^2)^(5/2) ds`
   is finite positive; Phi has units of squared speed and Phi'' of inverse
   time squared. Kernel evaluation still needs scaling/finite-value checks
   and independently bounded quadrature. Barnes Eq. (19) uses **smoothed**
   enclosed mass, not the raw particle enclosed mass: a finite-epsilon
   exterior field is not exactly `G*M_raw(<r)/r^2`. Use only its isolated
   asymptote `Phi~-G*M/r`. Barnes Eq. (20) as printed shows a positive sum;
   it must not override the project's explicit negative GP-2 potential and
   zero-at-infinity convention. No official correction to that paper is
   asserted here.

2. **Supported target density and normalization; no accepted DF follows.**
   EN 25-41 fixes positive finite `G=M=a=1`, epsilon/a=.05,.1, rt=10a,R=20a.
   In the taper, `tau_q=-30*q^2*(1-q)^2<=0`, and tau/tau_q/tau_qq match
   `(1,0,0)` at q=0 and `(0,0,0)` at q=1. Thus the extended density is
   nonnegative, compactly supported and C2; its third derivative need not
   match. Write `rho_P=3*M*a^2/[4*pi*(r^2+a^2)^(5/2)]`. Then
   `C=M/[4*pi*integral_0^R s^2*rho_P(s)*tau(s) ds]` is finite,
   dimensionless and greater than one. It renormalizes the **post-taper**
   mass; M cancels from this dimensionless shape normalization. Compute and
   archive C independently, do not reapply the taper to sampled particles.
   These input choices and the quintic taper are project choices, not Barnes
   fixture values. They define a testable candidate rather than prove its
   phase-space admissibility.

3. **Clarify the limiting control before its packet is frozen.** EN 129-130
   calls for an “epsilon->0 Plummer control.” At fixed rt,R,C from E1,
   epsilon->0 yields a **Newtonian tapered, renormalized** density, not the
   usual analytic infinite Plummer potential/DF. In particular, C remains
   greater than one. Freeze either a Newtonian spherical reference for the
   unchanged tapered density, or an explicitly separate untapered control
   with tau=1, R=infinity and C=1 (or a demonstrated taper-removal limit).
   Do not compare the finite-taper result to the analytic untapered formula
   and call a difference numerical failure. This is a reference-identity
   clarification; it changes neither the finite-epsilon target nor `<1e-6`.

4. **Supported inversion, energy shift and endpoint coefficients.** EN
   75-107 correctly shifts only the DF energy zero:
   `Psi=Phi(R)-Phi(r)`, `calE=Phi(R)-(v^2/2+Phi(r))`. GP-2 retains its
   infinity zero; neither the force domain nor live particles are cut at R.
   The DF's physical domain is `0<calE<=Psi(0)`, zero for calE<=0; requests
   above Psi(0) have no inverse-density argument and must be rejected, not
   extrapolated. Make that upper-domain check explicit in the DF interface.

   Starting from `rho=4*pi*integral v^2*f(Psi-v^2/2) dv` gives E4's
   `4*pi*sqrt(2)` coefficient. Abel convolution of its derivative supplies
   `1/(sqrt(8)*pi^2)`, including the `rho_Psi(0)/sqrt(calE)` boundary term.
   Here f is a **mass** phase-space density, with units density/speed^3;
   rho_PsiPsi has units density/speed^4. No particle-mass or G factor belongs
   in this kinematic inversion prefactor. Eddington printed 580 explains
   positivity as a separate condition and gives a finite-cutoff example;
   Barnes p. 8 explicitly requires the **underlying** density, not smoothed
   Poisson density, in the derivative.

   Let `L=R-rt`. Near R, `tau=10*((R-r)/L)^3+O((R-r)^4)` and
   `Psi=Phi'(R)*(R-r)+O((R-r)^2)`, so
   `C_edge=10*C*rho_P(R)/[L^3*Phi'(R)^3]>0` and rho_Psi(0)=0.
   Inserting `rho_PsiPsi~6*C_edge*Psi` in E4 gives
   `f~(2*sqrt(2)/pi^2)*C_edge*calE^(3/2)`, as stated. The substitution
   `Psi=calE*(1-u^2)` gives E5's `sqrt(calE)/(sqrt(2)*pi^2)` prefactor.
   For the center, z=r^2 has `Psi_z(0)=-Phi''(0)/2<0`; the two chain-rule
   derivative formulas at EN 103-104 are correct. Use analytic/controlled
   z derivatives, not a radial floor or raw cancelling r-derivative ratios.
   Split integrals at taper joins and their mapped Psi values; the transformed
   integrand is not rendered infinitely smooth by C2 matching.

5. **Numerical prerequisites remain substantial and explicit.** Positive
   density and monotone potential establish an invertible radial relation,
   not a nonnegative DF. The positive cutoff asymptote only controls that
   limit. No global sign, DF value, accepted energy grid, quadrature accuracy
   or table has been demonstrated. Before a DF/CDF slice, freeze an immutable
   packet with parameter/energy domains, C and potential-offset receipts,
   quadrature/precision refinement, center/edge error scales, derivative and
   interpolation error controls, root brackets and unresolved-sign semantics.
   State how the existing source density/moment budgets apply to Eddington
   reconstruction and its interpolant; GP 874 labels its density L1 clause
   as orbit-response, while no inversion-specific reconstruction tolerance
   is yet frozen. Do not infer a pass from a few matching moments.
   Signed uncertainty must not be replaced by abs(f), clipping small negative
   values, trimming energies or renormalizing a density mismatch.

   EN 117-139's independent angular/radial force and Abel paths, density
   reconstruction and Jeans moment are appropriate complementary checks.
   The Jeans equation is `d(rho*sigma_r^2)/dr=-rho*Phi'`; zero edge pressure
   gives its stated integral and correct density-times-speed-squared units.
   Freeze independent oracles that do not call E2/E5 production routines or
   share their derivative/table cache. Check r=0, r~epsilon, both joins,
   cutoff and highest binding energies; show an actual finite-difference
   plateau rather than one matching difference step. Require the interpolant
   to reconstruct densities, moments and CDF integrals, not just nodal f.
   Preserve the existing source/live thresholds and all failures. Their
   absence here is an unexecuted prerequisite, not evidence of a negative DF.

6. **Correct the virial frame before live-reference acceptance.** EN 148-149
   and GP 669 recommend `2K+W`; GP 661 defines K as lab-frame kinetic energy,
   while GP 660/666 use COM angular momentum/force moment. A raw independent
   sample generally has nonzero P, and the proposed sampler forbids hidden
   COM repair. For an isolated fixed-mass catalog,
   `I_cm=sum m*|x-X_cm|^2` obeys
   `I_cm''/2=2*K_int+W`, where
   `K_int=K_lab-|P|^2/(2*M)` and `W=sum (x-X_cm) dot F`.
   Consequently `2*K_lab+W` has the additional bulk term `|P|^2/M` and is
   not the internal equilibrium diagnostic under a boost. Define a distinct
   K_int field and apply the unchanged 2% G-EQUIL-LIVE virial target with
   its internal denominator. Retain raw K_lab and raw energy for conservation.
   Numerically form K_int from velocity deviations about P/M; the subtraction
   identity alone can cancel under a large bulk boost. Compute this diagnostic
   without changing the stored velocities.

   GP 678-690 already correctly retains fixed nonzero scales and the COM
   trajectory `X_cm(0)+P0*t/M`. P/L gates must remain **changes/residuals**
   from the actual initial catalog, not a requirement for zero sampled P/L.
   State which center/frame is used for density and moment bins. The
   `(N-1)/N` conditional mean field at a sampled particle follows only under
   the independent equal-mass sampling model: the N-1 other sources each
   have mass M/N. Independent external probes instead include all N sources
   and have the continuum mean. SHA determinism is not proof of that
   probabilistic independence. Keep finite-N self-exclusion, correlations,
   COM motion and relaxation as measured controls; no G/velocity/self-energy
   correction, selective seed retry or live recentering is justified.

7. **Address length, typed identity and transaction semantics supported.**
   RS 24-61 has a 21-character ASCII domain (7+1+2+1+7+1+2), plus one NUL:
   22 bytes. Adding seed 32, component 8, namespace 8, counter 8, purpose 4
   and draw 8 yields exactly 90, with the stated half-open offsets. All
   integers are explicitly little endian; the identity is namespace then
   counter, irrespective of native u128/struct layout. For the asymmetric
   challenge, the namespace bytes must be `08 07 06 05 04 03 02 01`, the
   counter bytes `11 10 0f 0e 0d 0c 0b 0a`, and purpose 0x1001 bytes
   `01 10 00 00`. These are manual field checks, not executed addresses.

   Seed labels specify the first eight little-endian bytes plus 24 zeros;
   retain the full 32-byte seed, not only its decimal label. Six purposes
   are distinct and draw zero is explicit. A valid tuple has an unambiguous
   message, but distinct messages need not have distinct SHA outputs.
   Preserve checked ParticleId allocation, disjoint/collision-checked
   namespaces, explicit component maps and no rank/index/hash-allocated IDs.
   Stage contiguous candidates and allocator state privately; any failure
   rolls back the whole catalog, and overflow never wraps or consumes IDs.
   u64::MAX is a valid draw input, not authorization to increment past it.

8. **Open52 endpoint and multiplicity claims proved manually.** For
   `k=r>>12`, `U=(2*k+1)*2^-53` with `0<=k<=2^52-1`.
   Every integer k is exact in binary64. Below 2^52 the spacing is at most
   one half, so adding .5 is exact; power-of-two scaling is exact here.
   Thus `2^-53<=U<=1-2^-53`, strictly excluding zero and one. Each k has
   exactly the 2^12 low-bit choices `r=2^12*k+j`, `0<=j<2^12`.
   This proves equal preimage counts **conditional on uniform u64 words**,
   not IID behavior, a period, collision freedom or a certified simulation
   RNG. FIPS specifies a hash, not this address or sampling law.

   For the rejected 53-bit midpoint, take k=2^53-1. `k+.5` is halfway
   between adjacent binary64 integers there; ties-to-even chooses 2^53,
   yielding U=1 after scaling. The unchanged SF map `k*2^-53` instead is
   exact on `[0,1-2^-53]`. Its half-open Bernoulli law and separate SF
   domain/counters must not be substituted with open52. The SF hash/mapping
   source block at C is byte-identical to S's historical context. No mapping
   values or SHA vectors were executed to reach these conclusions.

9. **CDF and isotropic transforms are normalized conditionally, not accepted
   numerically.** RS 93-109's radial CDF integrates the mass probability
   `4*pi*r^2*rho/M`; speed density `4*pi*v^2*f/rho` has units inverse speed
   and integrates to one by E4 at a valid r with positive rho/Psi.
   Generalized inverse `inf{x:F(x)>=U}` chooses the left edge at an exact
   plateau tie. That convention matters on a finite midpoint lattice even
   when a continuous uniform would hit a given plateau height with zero
   probability. It must be implemented with interval/bracket uncertainty,
   not “nearest node” or arbitrary plateau midpoint selection.

   Before the CDF/inverse slice, freeze enclosures/tolerances, monotone
   interpolation, exact endpoint limits and failure behavior for a rounded
   r=R or nonpositive/unresolved rho/Psi. F_v is not defined by dividing by
   rho(R)=0. Open U alone is not a proof that numerical table/inverse
   arithmetic cannot return an invalid endpoint. Reject the construction
   on unresolved input/inverse rather than clip r/v/f, retry a seed or draw
   another address. Synthetic plateau, endpoint, bad-normalization,
   nonmonotone and unresolved-sign cases should precede physical sampling.

   For ideal independent continuous uniforms, mu=2U-1 and phi=2*pi*U give
   `dOmega=dmu*dphi`; the stated stable transverse factor represents
   `sqrt(1-mu^2)`. Separate position/velocity purposes give the intended
   isotropic nonstreaming law under those assumptions. The discrete lattice,
   rounded TAU/trigonometry and inverse errors require diagnostics; do not
   claim exact continuous isotropy or cross-platform trig bits. This model
   supplies no rotating multicomponent disk DF or gas pressure equilibrium.

10. **Hash interface, provenance and prospective gates: suitable scope,
    unexecuted.** FIPS section 3.1's word convention and section 6.2.2's
    ordered output words do not conflict with RS's explicit little-endian
    interpretation of the first eight output bytes. Keep the standard digest
    bytes unchanged; do not reverse the digest/words to accommodate the
    sampling conversion. At C, `mhd_io::digest` (lib.rs 11-17) sequentially
    updates supplied slices; mhd-io/Cargo.toml pins `sha2="=0.10.9"`, and
    Cargo.lock 704-711 records registry checksum
    `a7507d819769d01a365ab707794a4084392c824f54a7a6a7862f8c3d0892b283`.
    No build, dependency change or implementation certification occurred.

    RS 148-152 separates official vector, independent literal-address,
    synthetic float-edge, schedule/rollback and equilibrium tests. The
    Len=0 response's Msg=00 is a placeholder: hash zero message bits, not a
    zero byte. Include chunked vs concatenated messages, wrong-endian/domain
    controls, direct literal field assertions, overflow, duplicate/imported
    IDs and failure after partial staged catalog. Python and Rust builders
    must be independently assembled; comparing the same erroneous shared
    serializer is insufficient. A suite pass is informal implementation
    evidence, never CAVP certification or proof of RNG statistics.

    Materialize RS 124-137's provenance as a mandatory catalog manifest:
    full seed, stream/purpose/component maps, each **original sampling**
    namespace/counter and draw index (zero here), current-ID remapping,
    M/N/C/epsilon/taper/units and mass-DF convention, potential shift,
    exact reference/table/interpolator/error-control hashes, binary/architecture,
    and any one-time rotation/COM/bulk transform with raw and transformed
    diagnostics. Storing the tuple map is sufficient; copying 90 bytes per
    draw is unnecessary if it reconstructs those exact bytes. Import/restart
    must not regenerate under remapped IDs and call it the old realization.
    Preserve the raw catalog hash and raw bytes or a verified reconstruction
    path using the original addresses/tables/binary. A floating transform's
    formal inverse alone does not guarantee recovery of the raw bits.
    Same address yields the same word; changing N can alter masses,
    ID layouts or accepted tables and does not promise the same catalog.
    Spherical deterministic access also does not certify an eventual SF RNG
    or a stratified/paired/merged production scheme.

## Smallest future independent packet and remaining gates

All executable cases below remain **unimplemented/unexecuted** and must be
individual REANA workflows after scoped M1 acceptance, source/design review
and immutable preflight. Do not run them locally. Keep declared per-case
resources and no aggregate cap. GP's preflight is 24 threads/32 GiB with a
serial test harness; RNG cases are 1 thread/1 GiB, schedule members separately
1/2/4 threads/1 GiB, source/quantile/direct live members 1 thread/2 GiB.
Tree live members (1 thread/4 GiB) additionally wait for their tree gate.

| Next packet | Required falsification before escalation |
| --- | --- |
| Literal-address, official short/long vectors and synthetic float edges | Independent message bytes and standard digest bytes; prefix-to-u64 order; all six purposes and max/overflow distinctions; exact open52 endpoints and unchanged SF half-open bits. No DF is needed. |
| Virial-frame algebra before live diagnostics | One frozen catalog and a uniform velocity boost: `K'=K+b dot P+M*b^2/2`, `P'=P+M*b`, while K_int and W are invariant. Keep the raw catalog and energy; no COM repair. |
| E2/E3 source, separately for epsilon/a=.05,.1 | Independent angular/radial GP-2 potential/force, center limits and finite-difference plateau, mass C, both joins and isolated asymptote. Clarify the distinct Newtonian tapered / untapered analytic controls first. Retain `<1e-6`. |
| E4/E5 DF and synthetic Abel/endpoint providers | Independent inversion, cutoff coefficient and center derivatives, sign uncertainty across the full energy domain, rho reconstruction and independent Jeans moments under precision/quadrature/table refinement. Frozen grids/scales/tolerances/reference hashes are still missing inputs, not accepted values. |
| Synthetic inverse and then accepted physical CDF cases | Left-edge plateau ties, endpoint brackets, injected nonmonotonicity/normalization/sign errors, no redraw/clipping; conditional speed and radial normalization, probability-space inverse enclosures and independent direction moments. |
| Schedule/restart/rollback catalog | All preregistered seeds, storage orders, 1/2/4 threads, partial failure, allocator overflow and explicit import remap; compare canonical tuples/words/uniform bits and same-build accepted catalogs. No seed selection by favorable COM or equilibrium outcome. |
| Accepted sphere's N=256,1024,4096 / three seeds / matched dt ladders | Raw and internal-frame diagnostics, finite-N self/probe controls, corrected virial definition and existing 10-crossing-time source/live gates; separate direct/tree, sampling, dt and softening errors. These numerical gates cannot be inferred from the algebra. |

A concrete synthetic plateau challenge can use `a=1/2+2^-53`, an actual
open52 lattice value, and a dimensionless CDF on `[0,3]`: `F=a*x` through 1,
`F=a` on `[1,2]`, and `F=a+(1-a)*(x-2)` through 3. At U=a its generalized
inverse is exactly 1, not the plateau midpoint. This is a manufactured
policy fixture, not a computed DF or a production reference implementation.

No observed quadrature error, DF sign, reconstruction residual, sampling
moment, live drift or statistical adequacy is supplied by this report. The
final goal remains the genuinely deforming 3D magnetized live gas+DM+old/new
star merger, including isolated compound galaxy/ambient/boundary controls,
rotating disk construction, gas/MHD force balance and accepted ISM coupling.
The spherical component reference cannot replace any of those dependencies.
