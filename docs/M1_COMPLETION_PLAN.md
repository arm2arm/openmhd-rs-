# Issue #7 continuation: prospective face completion and remaining runs

Registered before measuring the new implementation. Historical profiles, packets,
thresholds and failures remain unchanged. This is an engineering experiment,
not an equation attributed to the paper or an independently reviewed method.

## First experiment: HLL A-face completion (rejected during AI review)

Add `bulk-frame-hll-v1`: the existing bulk-frame gauge plus an HLL average
completion for the magnetic field and normal EMF supplied to the A equation.
Retain the HLLD/HLL conservative and tangential induction fluxes exactly.
In the face rest frame, when SL < 0 < SR, use

```
U_H = (SR U_R - SL U_L - F_R + F_L)/(SR-SL)
B_A = magnetic components of U_H
v_A = momentum components of U_H / rho_H
EMF_A = n cross F_induction + n [n dot (v_A cross B_A)] + w cross B_A
```

Outside the fan use the upstream state. Apply this convention on every face;
there is no fitted small-Bn/contact-speed threshold. The A source remains
`EMF_A - u cross B_A`. The HLL state is a completion of the missing information,
not a replacement of the numerical tangential EMF by `v_A cross B_A`.
Reject nonfinite/inadmissible completion states. Conservative fluxes, frozen C1,
limiting, auxiliary interpolation, timestep bounds and default profile are unchanged.

For normal reversal plus L/R exchange, HLL U is unchanged and the induction
flux reverses; the complete A source must be unchanged. Joint boosts leave
face-rest inputs unchanged and cancel between the EMF and u-cross-B terms.
HLL averages are continuous through Bn=0 and contact speed=0 because their
denominator is SR-SL, not the collapsed rotational-wave gap. These identities
do not prove long-time convergence or physical invariance.

**Review finding:** the HLL fan average does not approach the upstream state
as SL or SR approaches zero. A reviewer constructed a valid outer-wave fixture
with an O(1) complete A-source jump despite roundoff-sized conservative-flux
changes. The physical study was stopped with 81 completed records out of 184;
unfinished runs are not successes. Its source snapshot and failed-design evidence
are retained. This candidate is removed from the supported CLI profiles.

## Revised prospective completion: signal-weighted state

Before new measurements, register `bulk-frame-signal-v1`, using the same gauge
and unchanged conservative/tangential numerical fluxes, but replacing U_H by

```
U_A = (SR U_L - SL U_R)/(SR-SL)    if SL < 0 < SR
U_A = U_L                        if SL >= 0
U_A = U_R                        if SR <= 0
```

The interior weights are positive and sum to one. This is a convex mixture of
the common-Bn conservative states, not an HLL Riemann average. It preserves
positive density and internal energy by concavity of internal energy in the
conservative state. It tends to the appropriate upstream state at both outer
wave boundaries; reversal swaps the weights and inputs. Use B_A and v_A from
this state to complete the same EMF expression above. This new engineering
convention deliberately adds no fitted threshold. It does not prove continuity
across inherited HLLD/fallback validity switches or accuracy of the coupled method.

Repeat all registered tests, adding vn=±cf+delta, delta=0,±1e-15,±1e-12, density
contrasts and boost=(100,-1,.8) for the reviewer's outer-wave fixture. Preserve
the rejected experiment and report all spatial/temporal and boost failures.

Before physical measurements test the complete A source at 1e-11 against
face reversal/rotation, signed Bn/contact-speed sweeps, ULP perturbations,
joint 3D boosts, density and tangential jumps, uniform states, finite-Bn
rotational waves and an HLL fallback. Verify bit-identical conservative fluxes
against the historical routine. Add persistent-cell permutation and coupled
boost tests. Test the known N64 regular standing-wave pair at t=1 without
changing its 1e-8 relative gate. Report the old failure and the new result
separately; a successful comparator alone does not establish the old failure's
exclusive cause.

## Prescribed-flow loop

Add a separate planar prescribed-flow Voronoi transport driver for constant
v=(2,1), fixed/rigid meshes, regular/jitter=.15 N32/64/128/256, t=1 and joint
boost=(2,-1). Reuse the general solver's limited A reconstruction and donor
face-derivative operator. With u=v, mean B=0, Ax=Ay=phi=0, the planar potential
equation reduces to `(w-v) dot grad_upwind Az`; no gas or cleaning dynamics are
evolved. Use explicit two-stage Heun on the immutable rigid geometry and
dt <= .3 min_i r_i/|v-w|. This is the constant-velocity reduction, not a
coupled-MHD exact solution. Report A and raw-LS B error, discrete comoving
drift, magnetic energy and independent LS/arithmetic-face/limited-face
divergences. Use the unchanged packet gates: comoving relative A/B drift
<=1e-10, decreasing fixed A error and N256 A L1/peak <=.1. Report boost
differences separately. No mass/momentum/total-fluid-energy budget applies.

## Execution and assessment

Run the full original-profile physical spatial/temporal packet from a frozen
checkout, then the new comparator and prescribed-flow packet. Archive compact
numeric evidence and source/binary/configuration hashes, keeping failed and
missing gates explicit. Run format, Clippy, workspace tests, M0 checks and
the #6 regression. Final assessment must distinguish implemented work items
from scientific gates that fail and from separate review still outstanding.
