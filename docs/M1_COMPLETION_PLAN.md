# M1 completion: prospective numerical changes and remaining gates

Registered before implementation/evaluation of the completion candidate. Preserve all historical `paper-global-v2` and `bulk-frame-v1` results, defaults and thresholds. The user requests completion of M1; neither available features nor a successful run establish acceptance.

## Continuous A-face completion candidate

The separate AI design review finds that an exact-zero or Bn-only HLLD tie rule cannot resolve path-dependent intermediate states. Stationary rotational waves with finite Bn must also be covered. Introduce an explicit `bulk-frame-hll-v1` profile, retaining bulk-frame gauge/cleaning/stage equations but using a symmetric full-fan average only for the A-face completion. In the face rest frame, with the existing common arithmetic normal B and physical endpoint fluxes, set

```
alpha = max(abs(S_L),abs(S_R))
      = max(abs(v_n,L),abs(v_n,R)) + max(c_f,L,c_f,R)
Ubar = (U_L+U_R)/2 - (F_R-F_L)/(2*alpha)
B_c = Ubar_B; v_c = Ubar_m / Ubar_rho
EMF = n cross F_B,numerical_rest + n*(n dot (v_c cross B_c)) + w_face cross B_c
S_A = EMF - u_aux cross B_c.
```

This alpha encloses the existing HLLD outer-wave estimates. It is a conservative symmetric choice, rather than a fitted degeneracy window. Check finite values and admissibility of Ubar. Keep the numerical induction and conservative gas flux bit-identical to the historical routine for identical inputs; only the A completion/returned completion state changes under the new option. Apply the same B_c in the lab-frame EMF transform and subtraction of u_aux cross B_c. Keep the old API/default behavior and record the new profile in every output. This is an explicit engineering convention for an otherwise unspecified 1D-normal EMF completion, not a claim that Ubar equals the HLLD point state.

Before physical acceptance: test uniform states, positive/negative Bn down through zero, stationary contact and rotational-wave crossings at finite Bn, ULP perturbations, arbitrary normals, normal reversal with left/right swap, three-component joint fluid/grid/auxiliary boosts, density and tangential-field/velocity jumps, and HLL fallback. Existing algebra tolerance remains1e-11 relative-plus-absolute. Check actual numerical induction and full A source, not only gas flux. Diagnose the recorded N64 standing-wave pair with intermediate-time/perturbation measurements and repeat it under the new profile without retuning its gate. Include input-ID permutations and old geometry-equivalence probes. Do not infer that the local convention necessarily fixes the nonlinear physical failure.

## Full M1 validation

Use unchanged `benchmarks/m1/packet-v2.json` configurations and thresholds for the new, separately identified candidate. Preserve each original-profile failure; closure, if justified, is for the reviewed engineering reference and not a claim of exact reproduction of the publication.

- Alfvén: true N-by-N32/64/128/256 regular and jitter.15 grids; travelling/standing, fixed/comoving and joint boosts; t=0,.25,1. Initial curl error separate. Fit finest three L1 values; require order>=1.8 and finest B L1/.1<=.02. N64 dt .0004/.0002/.0001 versus .000025; report physical B and A/phi independently. Use the prospectively clarified wave-amplitude boost scales (rho1,p.1,v.1,B.1,E=.66+.5*v_parallel²) and unchanged relative L1 tolerance1e-8; also retain the alternate previously reported scale table.
- Passive loop: prescribed constant velocity, regular/jittered fixed/comoving N32/64/128/256, separate from conservative MHD. Preserve discrete comoving A/B to1e-10 relative, decreasing fixed A error, finest A L1/peak<=.1. Exclude cusp/edge from analytic pointwise B norms.
- Coupled loop: both geometries and boost family on full ladder, t=1, B boost relative L1<=.001. Report magnetic energy, all three divergence operators and gas changes; no exact passive-reference claim.
- Brio-Wu: general A integrator with gamma2, periodic2x.125 box, Nx256/512/1024, Ny4, interface1, comparison interval[.5,1.5], mean Bx=.75, t=.1. Compare overlap-weighted cell primitive fields with the archived Athena8192 reference and retain reference-refinement uncertainty. Finest scaled L1 thresholds rho.03,p.04,vx.03,By.04; error lower than coarse, Bx error<=1e-8, maximum signal travel<.45.
- Orszag-Tang: full general integrator at N64/128/256, regular/jittered, t=.5, gamma5/3, packet initial data, fixed/comoving boost pairing. Project cell primitive fields by polygon overlap to64x64 bins and compare archived Athena512 results. Finest scaled L1 thresholds rho.06,p.1,Bx.1,By.1; lower errors than coarse, mean-B drift/Bscale<=.001, limited-face dimensionless divB RMS<=.1. Longer t1/2.5 remain outside this initial packet.

Every evolved run must remain finite with strictly positive rho,p; normalized periodic mass/momentum/total-energy budgets<=1e-10, no floors or energy resets. Preserve failed evolution, budget, accuracy and invariance statuses. Any further algorithm change requires a new prospective amendment and separate AI review, not relaxed gates after seeing results. No lower transverse resolution may stand in for a declared square benchmark. Archive exact configs, source/binary hashes, errors, plots and runtime; independently review before M1 closure.
