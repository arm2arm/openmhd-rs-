# Independent review: state-dependent generator motion

2026-11-22. **Conditional source/manual-math support for SM1–SM7 on a smooth finite-dimensional branch; general moving physical adoption remains blocked.** The new proposal includes the missing state derivative of generator motion through an augmented Heun stage. No additional algebraic order defect was found under its stated assumptions. Its explicitly unselected path-aware event/exchange algorithm is a real implementation dependency, not a completed topology solution. This independent AI review supplies no numerical, M1, bounded-MHD or merger acceptance.

Subject **S** is `3c85aaa014aa8058e610e49e94def9b0f6ab25e3`. Line numbers below refer to `STATE_DEPENDENT_MESH_MOTION_SPEC.md` at S: 18,033 bytes, SHA256 `2daa87bafaadd02049a3ebeea7f91f9ba74c1ab5d42c73bd3100c010d81ecad9`. Its inventory is separately pinned in [the review inventory](state_dependent_motion_review_sources.json). Parent clarification **C** is `23b77701a02d255501b7c16ea9078a59c1afb474`; historical author context at `aa3a1e1` remains distinct. Observed entry root was `cf3d8533e329ba351ddafb5246e84d036505df10`. The earlier [moving-stage](MOVING_MHD_STAGE_DESIGN_REVIEW.md) and [curl/event](CURL_EVENT_DESIGN_REVIEW.md) reviews remain unchanged.

1. **Blocking for topology adoption: SM8 does not yet define accepted physical exchange.** S:265–298 honestly identifies the problem. At a smooth stage,

   ```text
   rP-rH = -h*(WP-W0)/2 = O(h^2),
   r_dense(1)=rH,             rP generally != r_dense(1).
   ```

   An arbitrarily narrow face event can distinguish these positions; small global state error cannot certify event coverage. P-stage face entries are evaluations at `(rP,YP)`, not observations of the accepted dense path at its endpoint. Conversely, querying an oracle on the dense path creates no accepted face-rate contribution. Refining the coupled problem changes W and hence the path itself; it is not quadrature refinement of one frozen linear movie.

   **Required before an event-coupled implementation:** select and independently review a path-aware controller/quadrature with explicit state/path branch identities, actual evaluated clouds/times, canonical face keys, and the rule by which covered faces enter accepted exchanges. Retain separate physical, GCL, predictor-only and oracle records. Specify which trajectory the independent reference encloses, including its uncertainty relative to event width. Preserve C's E0/E1–E5 mandatory coverage rejection and all absolute/relative exchange/root gates; no oracle-time injection, unlogged remap or coverage-only flag. Smallest prospective REANA controls are a literal P-only face and a literal dense-only transient face, followed by the independently resolved same coupled ODE. SM-PATH is correctly labelled design-blocked; the old prescribed-linear controller is not a substitute.

2. **Supported velocity law, with explicit domain and boundary limits.** SM1:53–79 has velocity units: `h_i` and d are lengths, and `B^2/rho` is squared speed in `mu0_code=1` units. For positive finite volume and thermodynamics, the denominator is nonzero at d=0 and `|u_reg|<alpha*c_sig`. It is a smooth saturation, not P09 Eq.63 or a displacement divided by the current dt. Its bounded amplitude does not bound spatial derivatives, prevent generator collisions, or preserve rank/quality.

   In SM2:81–105, `chi'=30*q^2*(1-q)^2` inside the layer and both first/second derivatives match zero at its joins. Thus the zero/one extension is C2. At an axis wall the corresponding relative normal generator velocity vanishes; corner factors remain well defined when the actual positive distances and h match that stage. This is a mesh velocity boundary law, not the physical Riemann wall speed. Explicit predictor/final/dense positions can still leave the box and must reject. Bounded trace/Cdot/U1–U4 acceptance is not supplied. Freeze literal join/lift/wall cases and the separately labelled alpha=0 and alpha=1/4 controls for SM-LAW; do not switch between them after failure.

3. **Supported acyclic evaluation and fixed-sample Cdot.** S:109–132 builds geometry/C/B/positive primitives, then W, then S3/S4 moment rates, Cdot, auxiliary/raw/face rates and the tangent solve. No current W requires the current Cdot or fA, so this is explicit. The chain rule is

   ```text
   dC/dt = partial_t C + D_r C[W(t,r,Y)],
   d(C*a)/dt = Cdot*a + C*adot.
   ```

   Real sample values are held fixed in the first derivative. There is no additional Wdot term in instantaneous Cdot. Differentiating the augmented right-hand side for the order proof does include W_t/W_r/W_Y. This distinction is correct even though W depends on a through recovered B and thermal pressure. S3/S4 must use the same instantaneous W, including face second moments and separate periodic self-image metric incidences before owner cancellation. C's S5 must differentiate fit residuals, volume length scaling, objective weights, evaluation rows and restored column scales. The F1–F9 selector and raw LS selector have different C/Cdot and sampling contracts. None of this proves their numerical conditioning or consistency. First later case: fixed-real-sample Cdot versus independently rebuilt geometry differences, then transported analytic samples with `C*adot` separately included; retain the parent derivative/uncertainty gates.

4. **Supported old/P/H separation and once-only tangent correction.** SM4/SM5:134–180 give three actual tessellations. Writing `L_s=H_s^-1 C_s^T V_s`, their exact-arithmetic A update is

   ```text
   zP=h*L0*e0,       vH=(h/2)*LP*eP,
   aP=a0+h*fA0,
   aH=a0+(h/2)*(fA0+fAP).
   ```

   The second solve uses CP/VP/eP at the predicted state. Substituting CH/VH would change the RK stage. Final recovery `BH=Bmean+CH*aH` is a state-function evaluation at rH, not an additional projection. It introduces no extra kick, centroid relocation, screened correction or mesh-transport subtraction. Phi and the periodic origin use the same old/P trapezoid; K has its constant run-frame rate. Final auxiliary maps must be rebuilt at `(gH,QH,aH,oH)` rather than reused from P. Epoch/state/velocity/policy/origin identities and atomic retry rollback in S:174–180 are necessary interface constraints, including after sources. A small later no-switch REANA stage fixture must expose both rP/rH and CP/CH; a coincident fixed/rigid case cannot detect the wrong substitution.

5. **Supported GCL signs, stage samples and conditional correction orders.** SM6:182–215 uses actual VP for the predictor and actual VH for the corrector. UP is QP/VP and BP is CP*aP plus Bmean; neither QP/VH nor CH*aP is a valid P observation. In the constant conservative-state limit, assume closed physical face-flux closure and common owner value U. Then the raw exchange gives `Qraw=U*(V0+D*S)` and

   ```text
   Q=Qraw+U*D*deltaS=U*Vend.
   ```

   This proves the stated extensive constant-U algebra on a compatible graph, not preservation of every reconstructed A/B/pressure state. It needs the physical face state and boundary provider to satisfy its uniform-state assumptions. The induction target still divides by the corresponding actual volume; it remains a diagnostic, not a finite-endpoint projection destination.

   For a smooth volume map `J(t,r)` define `G=J_t+J_r*W`. Taylor expansion about Z0 gives

   ```text
   VP-V0-h*G0=O(h^2),
   VH-V0-(h/2)*(G0+GP)=O(h^3).
   ```

   A bounded smooth graph right inverse therefore gives predictor/corrector sweep corrections of those orders. Small/new graph weights, incompatible components or changed topology invalidate this estimate; a graph solve cannot fix missed physical exchange. A gH-only face gets no invented old/P rate or correction edge. Preserve self-image cancellation only in the conservative owner graph, not S4 metric moments. Independent REANA SM-GCL must rebuild both tessellations, check actual closure/component residuals and the unchanged <=1e-12 GCL and <=1e-10 state/budget gates. No mean subtraction or replacement volumes.

6. **Supported conditional augmented-Heun proof; physical order remains unknown.** In SM7:225–257, put `Faug=(W,F)`. The predictor including its O(h^2) GCL perturbation is `ZP=Z0+h*Faug0+O(h^2)`. Smooth reevaluation gives

   ```text
   W_P=W0+h*(W_t+W_r*W0+W_Y*F0)+O(h^2).
   ```

   Finding 4 integrates fA exactly by Heun, the other rates are trapezoidal, and finding 5 changes the Q corrector only at O(h^3). Consequently the complete step has local O(h^3) and conditional global O(h^2) on a fixed finite-dimensional smooth/Lipschitz branch with uniformly bounded derivatives/inverses and controlled solves. This actually includes state-dependent W; the old frozen-old-velocity counterexample is not being silently reused as the desired trajectory. The dense extension is not the exact coupled trajectory.

   Smoothness is an assumption, not established by constant face count. Fit/rank/conditioning/support events, limiter/donor/Riemann/root switches, auxiliary Jacobian brick crossings, geometry degeneracies and positivity failures remain excluded. Fixed relative solve tolerances create an absolute-error temporal floor through inverse amplification. No temporal proof establishes spatial MHD consistency, mean-target agreement, magnetic divergence or pressure stability. SM-STAGE must freeze reference construction/times and certified no-switch windows, use >=4 halvings, order>=1.8 above floors, max lifted generator error<=1e-5 Lmin0 and reference uncertainty<=1e-10 Lmin0, together with the parent state/field gates. Those are prospective requirements, not measured results.

7. **Supported law-level joint boost; no full coupled invariance proof.** SM1/SM2 are equivariant under one constant boost of positions, fluid velocities, periodic origin or translating box and Wbox: d/h/thermal p/rho/B remain invariant and W gains the boost. This assumes the conservative gas energy and momentum receive the correct laboratory transformation. The parent auxiliary-origin law, gauge/K law, constant run Vref, face frame/returned fluxes and selected field sampling must all transform consistently. SM3 consumes the already laboratory-ALE flux once; there is no second `-U*w_n` or `-B*w_n`. Changing Vref after a gravity kick or birth would change the method. SM:259–263 correctly keeps endpoint gravity/source splitting first order, invalidates W caches and gives newborns no preceding kick. Joint-boost/restart and active-source/work tests remain independent future gates; the scalar W argument does not close them.

8. **Energy/mean and sampling scope is preserved; no hidden repair is authorized.** S:41–51,210–223 and C's section2/S10 explicitly distinguish point A, point-LS B used as an FV surrogate, and shared-face cell-average B. Same-ODE time errors must use matching representations; physical B norms for the shared-face selector require actual analytic cell averages. Q uses actual cell integrals. Keep common physical total energy and the magnetic variance/reconstruction distinction of the frozen curl review. The `(g0,a0)->(gH,a0)->(gH,aH_raw)->(gH,aH)` ledger plus separate P closure records each recovered magnetic change at fixed samples; conservative Q_E supplies only declared face/wall/source changes, so the partition change is opposite in thermal energy. This is accounting, not an energy or positivity theorem. The shared-face periodic mean identities do not imply exact target matching; raw LS has no such mean theorem. Preserve independent divergence/target/normal/mean diagnostics, beta=.01 predicted/final positivity rejection and all partition gates. No pressure reset, Bmean retuning, mean subtraction or hidden heat source may cure failure.

9. **Implementation disposition and source limits.** No correction to SM1–SM7 equations is required by this manual review. After M1 and independently frozen inputs/preflight, a small named periodic law/tangent/smooth-stage slice is eligible; it cannot claim event-resolved moving MHD. Finding 1's controller/quadrature selection blocks topology adoption. Literal maps, spatial/mean/projection/Cdot/conditioning evidence, bounded U1–U4, gravity/work/source splitting, stable isolated multicomponent galaxies and the full domain/ambient/encounter matrix remain prerequisites to the actual merger. C clarifies sampling and periodic PQR meanings without changing F1–F9/S1–S19; its new metadata/event semantics have not acquired numerical approval from being read here.

   P09's complete retained v3 PDF (67 pages, 9,354,438 bytes, SHA256 `dfe38502394b15a0b05bbb1f610b0e1533198594e33681e22a507162cc2d10f4`) was inspected at printed pp.16–17 Eqs.31–40, p.22 Eq.63 and p.25 Eq.73/context, with fresh renders of all four equation pages. It supports the ALE/motion context, not SM1–SM8. The arXiv strip is v3, 31 October 2009; its printed recompile date is 26 November 2024. P26 v1's complete 37-page PDF is separately pinned; pp.6–10,12–13,15–16 gauge/fit/raw/stage context was consulted, with fresh p.9/p.16 renders. Neither paper publishes this augmented projection/GCL/event construction or an AREPO-equivalence result.

The review inventories record the exact committed subjects/parents, source bytes and fresh reading artifacts under ignored `results/galaxy_motion_jeans_review_20261122/`. All 34 byte/hash entries in the two author inventories checked with **zero mismatches**; that includes retained render/text receipts, not numerical evidence. Pinned historical contexts were checked against their own commits rather than a changing working copy. Source parsing, hashing, PDF extraction/rendering and the manual algebra above were the only checks. No numerical executable/test/probe, geometry backend, RNG/DF evaluation, build, production reducer, service/workflow control, commit, push or delegation occurred. Scientific source `2bdcea0` and all earlier independent reviews remain unchanged. All future independent cases require separate REANA workflows, declared resources and their scientific/review/preflight prerequisites, with no aggregate resource cap.
