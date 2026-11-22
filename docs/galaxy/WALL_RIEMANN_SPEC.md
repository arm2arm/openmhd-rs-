# Physical perpendicular-MHD half-Riemann wall pressure

Author revision, 2026-11-22. **Engineering proposal, unimplemented,
unexecuted and awaiting independent review.** This supplies the pressure
missing in finding 2 of [the frozen independent review](BOUNDARY_MHD_DESIGN_REVIEW.md).
It changes no existing solver or M1 source. The physical profile remains
[the finite slip conductor](BOUNDARY_MHD_SPEC.md), not general outflow.
Exact consulted bytes/locators are in [the inventory](wall_riemann_sources.json).

P denotes a verified source statement, D the derivation here and E a new
engineering decision. P26 v1, printed pp.2–3 Eqs.3,7–10,13–14, gives the
conservation/EOS/entropy system. [Takahashi & Yamada 2013 v1](https://arxiv.org/pdf/1310.2330v1)
(TY13), printed p.4 Eqs.2.1–2.8, p.5 Eqs.2.11–2.13, p.6 Eqs.2.17–2.21,
supplies the Bn=0 characteristic limit and jump relations. The reduction,
root policy and fixtures below are independently derived, not their code,
an AREPO algorithm or a claim about uniqueness of arbitrary MHD Riemann fans.
Full source PDFs are available; no equation-access gap exists for these anchors.

## 1. State and wave reduction

**E:** `perpendicular-half-riemann-gamma53-v1` supports ideal gas gamma=5/3,
mu0_code=1, positive finite incident rho0,p0 and tangential Bt0. Incident
thermal pressure is reconstructed independently of magnetic energy, not
read from FaceFlux completion. In the wall frame let outward normal n point
from gas to support, `a=(v-W) dot n`, `vt=(I-nn^T)(v-W)`, Bn=0.
Thus a>0 compresses against the wall; a<0 recedes. The first source-split
multiphase model may use this solver only while its adiabatic face EOS is
the same gamma-law and source/phase fractions are frozen during the solve.
Other EOS/gamma profiles require a new reviewed wave curve.

P/D: for Bn=0, vt and k=Bt/rho are constant through either nonzero-mass
normal wave. Set `r=rho/rho0`, `m=|Bt0|^2/2`,

```text
P=p+m*r^2; e_eff=p/((gamma-1)*rho)+|k|^2*rho/2;
c_f(r)^2=gamma*p/rho+|k|^2*rho.                              (W1)
```

This is one compressible Euler wave family with convex effective pressure
along an isentrope, not a rotational/intermediate-wave selection. The symmetric
mirror problem has wall vn=0 and the same vt on both sides. Its incident-side
positive state is the requested wall state; there is no separate material
ghost or gravitating exterior. At a=0, r=1, pstar=p0, Pi=P0=p0+m exactly.

## 2. Receding rarefaction and vacuum

D: along the isentrope `p=p0*r^gamma`, `Bt=r*Bt0`, and the left-going
Riemann invariant gives

```text
a = -I(r), I(r)=integral_r^1 c_f(q)/q dq, 0<r<1.              (W2)
```

I decreases continuously from I_vac=I(0)>0 to zero. For gamma=5/3 define
`t=r^(1/3)`, `g=gamma*p0/rho0`, `b=|Bt0|^2/rho0`, X=g+b, Y=g+b*t.
The change of variable q=s^3 gives the exact, cancellation-controlled form

```text
I(r)=2*(1-t)*(X+sqrt(X*Y)+Y)/(sqrt(X)+sqrt(Y));
I_vac=I(0).                                                   (W3)
```

It follows from integrating `3*sqrt(g+b*s)`; the formula also has the
continuous gas-only limit `I=3*sqrt(g)*(1-t)` without dividing by b.
For `-I_vac<a<0`, solve W2 for t in (0,1), then
`rho_star=rho0*t^3`, `pstar=p0*t^5`, `Btstar=t^3*Bt0`,
`Pi_star=pstar+m*t^6>0`. For gas only this is
`t=1+a/(3*sqrt(g))`. No absolute value or positive-pressure clipping is used.

For `a<=-I_vac` the mathematical branch reaches vacuum at the wall: r,p,B
there are zero, Pi=0; for strict inequality a vacuum gap opens. This is
**not** an admissible positive-gas production state. Return typed
`WallVacuumEncounter{a,I_vac,bracket}` and reject the hydro trial/campaign
under the first bounded profile, rather than insert a density/pressure floor
or silently switch to an outflow/vacuum-interface model. The pure algebra
fixture records Pi=0 as its expected branch classification. Exact threshold
or unresolved threshold uncertainty also rejects positive-state production.

## 3. Compressive shock and total energy

D from mass, normal momentum and energy jumps: with r>1,

```text
e_eff,star-e_eff,0=(Pi_star+P0)*(1/rho0-1/rho_star)/2;
a^2=(Pi_star-P0)*(1-1/r)/rho0.                               (W4)
```

Tangential kinetic energy cancels because vt is unchanged. Keeping magnetic
internal energy in e_eff is essential; an isentropic compression is not a
shock solution. With u=r-1, `rmax=(gamma+1)/(gamma-1)=4`, W4 gives

```text
dp = [2*gamma*p0*u+(gamma-1)*m*u^3]/[2-(gamma-1)*u];
pstar=p0+dp;
Pi_star=P0+dp+m*(2*u+u^2);
a_shock(r)=sqrt((Pi_star-P0)*u/(rho0*(1+u))).                  (W5)
```

For 0<u<3 all terms of dp are nonnegative, denominators positive, and
a_shock strictly increases from zero to infinity. This establishes a
unique positive compressive root in this reduced branch. The entropy check
is `pstar/r^gamma>=p0` within the declared root uncertainty, never a reset.
Check W4 and all conservation jumps independently. A shock speed into gas
is `s=a-j/rho0`, with `j=rho0*a*r/(r-1)`; record its wave-speed/CFL bound.
For rarefaction record both head `a-c_f,0` and tail `-c_f,star` speeds.

## 4. Bracketing, uncertainty and returned API

E: rarefactions bisect t in [0,1] using monotone W3; no unguarded Newton
step is permitted. Compare a+I_vac with an interval-enclosed threshold:
if its sign cannot be certified at the solve tolerance, return
`WallVacuumThresholdUnresolved`. Shock brackets use
`x=(r-1)/(4-r)`, initially [0,1], double the upper x until W5 encloses a;
use stable `u=3*x/(1+x)`. At most 128 bracket expansions and 256 bisections;
nonrepresentable u<3, overflow, nonfinite values or exhausted brackets return
typed `WallPressureUnresolved`. There is no borrowed HLL pressure fallback.

Both final velocity-wave residual and enclosing Pi width must be <=1e-12
of Vscale=max(c_f0,|a|)>0 and Pscale=P0 respectively, where c_f0
is the positive initial fast speed. These are fixed incident-state scales.
Use conservative floating error enclosures or reject uncertain signs; an
independent high-precision REANA oracle must verify their coverage. Preserve
brackets, branch, iterations and normalized/absolute residuals. Insufficient
precision is an error, not a relaxed gate. Underflow of a positive r/p
is likewise unsupported, not vacuum inferred by rounding.

Return `WallPhysicalState{rho_star,pstar,vt,Btstar,Pi_star,branch,
wave_bounds,root_bracket,error_bounds,incident_hash,geometry/state/time/patch}`.
The API does not take FaceFlux completion as its pressure input. In the wall
frame its conservative flux is `(0,Pi*n,0)` and induction exchange zero.
Apply **one** laboratory ALE transform: `F_E=W dot(Pi*n)` and F_p=Pi*n.
Return physical electromotive value `(W+vt) cross Btstar`; its wall-frame
normal A source `(vt cross Btstar) dot n` may be nonzero. It is not zeroed
because the conservative induction exchange is zero. Gauge terms remain
the separate relative-gauge expressions in the boundary contract.

The old mirrored HLLD/HLL and SignalWeighted completion can be evaluated
only as labelled diagnostic comparators. Their traction/thermal pressure
is not the selected physical Pi. No second `-W_n*U` transform is applied.
Wall impulse/work/torque use the same Pi, area, position and time weight.

## 5. Exact prospective references and resources

All rows are formula-defined, unimplemented and unexecuted, requiring
independent fixture serialization/review and M1/preflight before REANA.
Each signed normal/orientation/boost/field case has its own workflow,
initially 1 thread, 2 GiB, 5 minutes, native libraries one thread; no
aggregate cap. Freeze a separately implemented >=80-decimal-digit reference
from W2/W4 (quadrature/Hugoniot, not the production W3/W5 formulas).
Reference pressure/velocity uncertainty <=1e-13 of P0/c_f,0; production
state/jump error <=1e-10, root and symmetry/boost algebra gates <=1e-12.

| Input, rho=p=1, gamma=5/3 unless stated | Exact expected branch/reference |
| --- | --- |
| a=0, Bt=(1/5,3/10), vt=(3/10,-2/5) | Pi=213/200, unchanged thermodynamics. |
| Same field, a=-1 (review R1–R3) | Rarefaction: X=539/300; Y=(X^(3/2)-13/200)^(2/3); t=(Y-5/3)/(13/100), Pi=t^5+(13/200)*t^6>0. Frozen HLL traction `213/200-sqrt(539/300)<0` is an expected diagnostic counterexample, not production Pi. |
| Same field, chosen r=2 | pstar=1413/400, Pi=1517/400, a=sqrt(1091/800), Btstar=2*Bt0; verify energy Hugoniot. |
| Bt=0, a=-sqrt(5/3) | t=2/3, rho=8/27, p=32/243. |
| Bt=0 and separately Bt as above; a=-I_vac and -I_vac-c_f,0/10 | Vacuum/threshold typed rejection; no positive state or floor. |
| a=+/-c_f,0/10, +/-c_f,0, +10*c_f,0, and negative a=-I_vac/2; Bt=(sqrt(200),0) for beta=.01 | Positive branch only where admissible; independent Hugoniot/isentropic reference, entropy and bracketing coverage. |

Repeat proper orthogonal face rotations, both n signs, W=0 and joint boosts
(2,-1,.5),(10,7,-3); transform wall velocity too. Wrong epochs/EOS/units,
nonpositive input, unbounded bracket and forced uncertainty failures reject
without mutating state or ledgers. These derivations remove an undefined
pressure choice; they do not establish executed accuracy or wall acceptance.
