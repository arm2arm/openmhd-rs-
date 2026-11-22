# Independent AI review: midpoint-predicted frozen mesh motion

2026-11-22. **Conditional source/manual-mathematics support for MF1–MF5 as a smooth trajectory alternative. No new algebraic blocker was demonstrated under the stated assumptions. Event coverage and a production topology controller remain unresolved adoption prerequisites.** This is an AI review, distinct from the author, not human peer review or numerical evidence. It accepts neither M1 nor moving 3D MHD, bounded operators, gravity, ISM or a galaxy merger.

The subject is **bfd4fd1ae7d08adc5176b45cddb6789c2c958f14**, not a moving working copy. Task-entry context is **97183f33438e406b77680758427af7aaeda6b42e**. The first observed checkout was ebc361ced3daacffd742d34986a570c2d78dfe7b; this difference did not alter the reviewed subject. Other workers' subsequent event-strategy and host-tool changes are excluded. Scientific implementation remains frozen at 2bdcea0d28340e7429e10053a641f92d51fcc696. No whole-working-tree source freeze was imposed.

| Exact reviewed file | Bytes | SHA-256 |
| --- | ---: | --- |
| MIDPOINT_FROZEN_MESH_MOTION_SPEC.md, subject commit | 12951 | 9f90de36282d25a854719e8de4a5688cd56e580588b347027730f73b9a84941f |
| midpoint_frozen_mesh_motion_sources.json, subject commit | 7332 | 5191cfa5d0c83f8b8e3b167b4811526854cdcf32d8a60c459c198b7d2b1f6214 |
| MOVING_MHD_STAGE_SPEC.md, task-entry context | 74430 | 081a64b41617cbb683e14fb39d7607e7ca0f57dce8e75d849f30b1a2d64ac2b4 |
| STATE_DEPENDENT_MESH_MOTION_SPEC.md, task-entry context | 18033 | 2daa87bafaadd02049a3ebeea7f91f9ba74c1ab5d42c73bd3100c010d81ecad9 |
| STATE_DEPENDENT_MOTION_DESIGN_REVIEW.md, unchanged historical review | 14148 | 45cf7c0aff8be3a0c88901f6f1cac8277d74859f7065bee9d2b1d1159a1f6424 |
| MESH_3D_SPEC.md, task-entry context | 79538 | 32e5ed2af3097c8106896fcb262a751ee37fe06dbf927f510e03952b5826b4ac |
| CURL_3D_MEAN_SPEC.md, task-entry context | 26047 | 0d843ed05710a10027cfd9eb9bb34f9e87d36a1fb54739297e2d59f6c6e0613b |
| INTEGRATION_CONTRACT.md, task-entry context | 14105 | 1c40c8eb67865585a7bb4bee83d75b537250c5862a838d3f7696ee9c9dc99abf |

MF line locators below mean the subject's MIDPOINT_FROZEN_MESH_MOTION_SPEC.md. Parent locators refer to the committed context above. The [companion inventory](midpoint_frozen_motion_review_sources.json) pins the required project documents, additional contracts, unchanged independent reviews, primary bytes and this report. The subject's older context at 12ef3b728a953dd93f49f932795c8bb13a651ff5 was checked against that commit: its relevant stage, motion, mesh and shared-contract hashes agree with task-entry context. Historical statements remain historical.

1. **Supported disposition of the prior off-path finding; high-priority event prerequisite remains open.** MF:30–36,86–107,168–206 defines a different algorithm, midpoint-predicted-frozen-path-v1. It does not pretend to implement the stage-by-stage augmented-Heun trajectory. The prior review's finding 1 identified that an Euler generator predictor rP generally differs from the accepted dense path's endpoint rH by O(h²). MF1's private rM is now explicitly excluded from physical exchange and coverage. All physical inner stages instead use one captured linear path, so their predicted and corrected gas/potential states have the same actual endpoint generator geometry. An inner physical Heun predicted gas state remains a legitimate rate stage when its rate enters the selected branch's accepted exchange; it is distinct from the discarded MF1 midpoint predictor.

   This resolves that particular off-path predictor ambiguity. It does not prove that sampled stages encounter every positive-area face on the line. Parent stage:728–1055 retains E0/E1–E5, including the epsilon=2^-28 alias challenge. The limited three-branch controller can agree while missing a narrow event. Mandatory positive-face coverage, accepted rate contributions, noncancelling exchanges and independent actual-surface exchange cannot be replaced by a small global error, GCL closure or agreement between sampled branches.

   **Disposition:** suitable as a conditional smooth-path alternative; general topology/production adoption remains blocked by the already identified coverage/controller requirement. A separately reviewed coverage strategy and actual independent certificates are required. No mutable proposal from the other event-strategy worker was read or presumed successful. No additional MF equation change is requested on this point.

2. **Supported private MF1 prediction, GCL sign and once-only covariant correction.** MF:40–84 uses the actual geometry at rM=r0+(H/2)W0, actual VM, and primitives from QM/VM together with the matching curl of aM. It does not replace VM with an independently integrated RK volume or sample aM at the old centroid. For a compatible constant conservative density U, closed physical-flux closure and consistent boundary data, the parent orientation gives

       Qraw = U (V0 + D SM),
       D deltaSM = VM - V0 - D SM,
       QM = Qraw + U D deltaSM = U VM.

   Thus the minus sign in EM_Q=delta XQ0-UbarM deltaSM is correct. SM and deltaSM have volume units; UbarM has conserved-density units; EM_Q and Q are extensive. The old two-owner samples are the parent's Euler samples. This proves conservative constant-U algebra under its assumptions, not full magnetic/pressure positivity or a boundary compatibility theorem. Positive predictor validation and graph component compatibility remain real rejection gates.

   Writing L0=H0^-1 C0^T V0, the private potential solve gives zM=delta L0 e0 and hence aM=a0+delta(rA0+L0 e0), a first-order prediction of the parent's tangent ODE. Under smooth actual volume and a uniformly bounded compatible graph right inverse, its Euler GCL perturbation is O(delta²), which is sufficient for MF3. Small/new graph weights, near rank loss, incompatible components or uncontrolled solve errors invalidate that estimate. No component mean subtraction or invented edge is allowed.

   MF:80–94 correctly discards the private state, corrections, physical exchanges and caches after capturing finite nu bits. Its positive midpoint closure is a prerequisite for evaluating W, not an accepted half-step. The private result supplies no hydro flux, wall impulse, source/birth, allocator change or event witness. The physical step restarts from Z0. This is an essential transactional boundary, including if any later physical branch rejects.

3. **Supported requirement to rebuild every physical rate with nu; generator, centroid and fluid velocities stay distinct.** MF:86–107 correctly requires a fresh old physical stage after capture. Parent stage:S3–S12 and mesh:646–683 show why replacing only the generator positions would be insufficient. With d=rR-rL, m=(rL+rR)/2, differentiating the moving bisector equation (x-m)·d=0 gives

       wn(x) = ((nuL+nuR)/2)·n
               + (nuL-nuR)·(x-m)/|d|.

   The normal speed is affine over the face. Reynolds transport then gives Vdot=sum_out A wn(f) and

       cvel = V^-1 sum_out A [(f-c) wn(f) + M_face grad_t(wn)].

   The second-moment term and separate self-image metric incidences cannot be dropped merely because their conservative owner-incidence column cancels. The centroid velocity is generally neither nu nor the fluid velocity. The raw donor transport uses cvel-u; the face solve uses the matching face frame. Cdot holds real samples fixed:

       Cdot = partial_t C + D_r C[nu],
       d(C a)/dt = Cdot a + C adot.

   There is no additional instantaneous Wdot term. The time derivative of the complete right-hand side used in finding 4 does contain the derivative of the state-dependent velocity law.

   Reusing the W0 physical stage would generally introduce an O(H) rate error and O(H²) local error. A manual scalar illustration is Y'=nu: trapezoiding W0 and nu=W0+(H/2)dotW0 gives H W0+(H²/4)dotW0, whereas the required coefficient is H²/2. This is a symbolic control, not an executed test. MF's explicit recomputation of face speeds, cvel, Vdot, Cdot, target, raw/auxiliary maps and tangent defect prevents that substitution.

   Parent S2/S6–S12 still determines the frame and correction composition. The laboratory ALE exchange is consumed once; there is no second mesh-transport subtraction. The captured velocity does not replace fixed run Vref, the fluid-volume-weighted periodic auxiliary-origin rate, the separately bounded box-origin law or Kdot=Vref×Bmean. Final recovery at the actual geometry is not a second screened projection. Nu must be keyed by persistent real CellId, not a mutable row or face index.

4. **Supported MF3–MF5 chain rule, conditional on uniform smoothness and controlled inner solves.** MF:111–166 includes the necessary velocity-law derivative. At (t0,Z0,W0), let A=G(t,Z;W(t,Z)), with G=(nu,F) and partial derivatives of G holding nu fixed. Direct differentiation gives

       A_t = G_t + G_nu W_t,
       A_Z A0 = G_Z A0 + G_nu W_Z A0,
       A_t + A_Z A0 = G_t + G_Z A0 + G_nu dotW0,
       dotW0 = W_t + W_Z A0.

   MF1 yields ZM=Z0+(H/2)A0+O(H²), so nu=W0+(H/2)dotW0+O(H²). Substituting into the frozen-nu flow expansion reproduces the exact augmented-ODE acceleration coefficient. G_nu includes the identity generator block **and F_nu**, including face/ALE, centroid/volume, Cdot, target, raw, auxiliary and tangent-solve dependence. The full W_Z includes dependence through recovered B and thermal pressure, not only position. Omitting those terms would invalidate the argument; the definition of F at MF:120–126 explicitly includes them.

   For r'=r, r0=1, MF gives rM=1+H/2 and r1=1+H+H²/2. The exact endpoint is exp(H); its first missing term is H³/6. This verifies the stated scalar Taylor control manually. It does not prove the chosen spatial MHD operator is physically consistent.

   For a stable smooth second-order inner method, a uniform eta=H/N gives accumulated O(H eta²). More generally, sum_j eta_j³ <= H eta_max² <= H³ for positive subintervals summing to H. The actual parent comparison branches are uniform dyadic branches; no new variable-step controller is selected here. The constants must stay bounded over the registered H/branch family: derivatives, graph/projection inverses, stencil/fit scaling, positive closures and compatible GCL corrections matter. Constant face count alone does not establish this. Donor, limiter, Riemann, root, auxiliary-brick, support, rank and topology switches can break the smooth argument.

   Fixed relative residual gates do not supply an O(H³) absolute macro error bound. In scaled norms, midpoint-state error epsilon_M affects nu through the W sensitivity and hence the endpoint at scale H L_W epsilon_M; nu storage/evaluation error contributes H epsilon_nu. Physical increment-solve errors accumulate with the stability/inverse factors. These errors and spatial/conditioning floors must be exposed in the future convergence packet. MF:158–166 already limits its claim accordingly. I found no new missing smooth-order term or required tolerance change. Local O(H³)/conditional global O(H²) is supported only for the same smooth finite-dimensional ODE with those assumptions; positivity, spatial convergence, general Galilean invariance and endpoint source order remain unproved.

5. **Supported inner-path identity, outer retry semantics and two distinct reference targets; literal records still need freezing.** MF:168–198 correctly freezes H, Z0, nu, time origin, scales and path digest before the three physical comparison branches. Equal macro times must use the same declared generator cloud recipe, although branch Q/a/auxiliary states and physical rates differ. The physical old/predicted stage times must be the actual MF2 times, not sequentially drifted approximations. Parent E0's retained dyadic bits, exact time tags, winding/image conventions and rounded-cloud recipe remain applicable. The exact rational numerical path and the geometry produced by the rounded evaluations have separate checks.

   Shortening/rejecting the outer H must discard nu and all branch work and rerun MF1 from the accepted snapshot. Macro-refined paths normally differ. Comparing them measures coupled trajectory/operator/state error, not fixed-movie quadrature error. No inter-branch interpolation of A, hidden conservative remap of Q, oracle-time injection or accepted-face credit from a discarded branch is authorized. Parent minimum-interval rejection, actual-nu moving-face CFL, typed failures, epoch invalidation, accepted-counter/ID/source/RNG rollback and restart rebuilding all remain in force. Diagnostic W at an inner state is not authority to change nu.

   The reference distinction can be seen without a numerical evaluation. At tau=theta H, the scalar example's linear numerical path is

       1 + theta H + (theta/2)H²,

   while the coupled exact trajectory is

       1 + theta H + (theta²/2)H² + O(H³).

   Their interior difference is theta(1-theta)H²/2+O(H³), despite endpoint second order. An exact fixed-path exchange oracle therefore need not enclose the coupled augmented-ODE trajectory. Conversely, a coupled trajectory reference cannot silently replace the prescribed-path surface/centroid exchange reference. MF:188–198 states this distinction correctly.

   **Remaining fixture prerequisite, not a new algebra blocker:** the exact rounded inputs, path/digest/attempt/branch records, independent coupled-reference construction, literal history times, no-switch enclosures and uncertainty allocation are not yet a frozen executable packet. Parent SM:317–323 and MF:217–249 explicitly leave them for independent literal review. Both reference types and the selected-branch physical witnesses must be identifiable in that packet before any numerical case is run.

6. **Unchanged event meanings and thresholds are necessary; a linear path does not weaken E1–E5.** Parent stage:861–1055 independently defines positive two-dimensional face area and actual accepted face-rate witnesses: I_surface=integral_time integral_face F; Jsurf=integral_time integral_face abs(F); Jface=integral_time abs(integral_face F); Jcent=integral_time abs(Xcent); and Jarea=integral_time area. Their meanings remain separate. Absolute value of a signed net exchange is not Jsurf; matched candidate/reference centroid rules do not establish actual-surface accuracy. Physical exchange and GCL correction retain separate ledgers. Absence of an event contribution can pass a global tolerance and still fail mandatory coverage.

   MF:200–206 preserves these definitions and epsilon=2^-28 explicitly. The root enclosure must resolve event width, not merely a small fraction of the macro interval. Parent E5's root width <=min(1e-10 H,1e-8 Wlo), positive width lower bound, and reference uncertainties remain prerequisites; uncertain zero channels require the registered absolute/enclosure treatment. They cannot be normalized by an uncertain zero reference. The existing Jcent mass/Jarea comparisons require candidate error plus reference uncertainty <=1% of the certified positive reference lower bound, <=0.1% reference uncertainty, and the separate root contribution bounds. No event certificate, root, flux, quadrature or literal array was evaluated here.

   The smallest useful future controls are the already requested predictor-only and actual-linear-path-only positive-face cases, plus discarded-branch/oracle-only witness negatives and the original short-face false-acceptance/minimum-interval controls. They must retain distinct MF1 versus physical records, exact full canonical image keys and accepted face-rate contributions. Passing a smooth MF scalar or GCL case cannot discharge them. A certified-linear-path proposal remains a separate source review, not an assumed result of this report.

7. **Supported convex-box reasoning, with bounded and source interfaces still conditional.** MF:208–215 is correct for a cuboid translating at constant Wbox. In its comoving chart,

       q(tau) = q0 + tau (nu-Wbox)
              = (1-tau/H) q0 + (tau/H) qH.

   Exact strict inclusion of both endpoints in that convex box gives exact segment inclusion. It does not prove admissibility of rounded evaluated clouds, positive cells, collision-free generators or acceptable conditioning. Every required actual cloud still needs its boundary/geometry check. SM2's instantaneous C2 wall taper is not a finite frozen-step barrier; neither W0-only CFL nor the vanishing instantaneous relative normal velocity is sufficient. A time-dependent/non-affine box trajectory would require a different argument and is outside this assertion.

   The physical wall Riemann speed is Wbox, not nu or the centroid rate. The first bounded choice remains a conducting slip box, unbounded collisionless particles and isolated gravity. Boundary:780–790 keeps the box-frame target T=Wbox distinct from the periodic fixed-Vref target, with rate difference -(Wbox-Vref)*d_returned. This is the already open U3 reconciliation, not a new MF fix or permission to retune Vref. Bounded differentiated constrained maps, moving Cdot/GCL, U1–U4, reflection and domain/ambient/full-duration influence remain prerequisites. The inherited fixed-wall-pressure algebra was not reopened without a new interaction defect.

   The field representation tuple also remains unchanged: point A, selected point-LS B as an FV surrogate or shared-face cell-average B, actual conservative Q/V, and the matching analytic/reference sampling. Periodic shared-face mean cancellation is conditional on its paired identity; raw LS has no such theorem. Neither implies exact physical target matching. Retain geometry/raw/projection magnetic-transfer diagnostics and the opposite thermal change at fixed Q_E, along with beta=.01 predicted/final positive-closure rejection. No Bmean adjustment, pressure floor or hidden heat source is authorized.

   Integration:IDs/epochs/source activation and gravity:383–492 still govern coupling. Gravity uses actual volume centroids and the declared transported-mass work, not an assumption that nu equals fluid or centroid velocity. Accepted kicks/source updates invalidate W/state/source caches before the next private prediction. Newborns activate atomically at the accepted endpoint and receive no earlier kick; fixed run Vref does not change. No source event occurs in MF1 or a hydro comparison branch. Source/thermal/magnetic and radiation/SN ledgers stay separate. Gamma-law smooth controls do not establish multiphase sound-speed, pressure or source compatibility. The endpoint source split retains its stated order; MF4 does not upgrade it.

8. **Source eligibility and unchanged prospective gates.** MF:217–249 is a dependency list, not a frozen fixture or completed gate. There is no demonstrated missing MF formula requiring a replacement proposal. After actual M1 acceptance, approved static geometry/operators, independently reviewed literal inputs/reference construction and immutable source/import preflight, a narrowly labelled periodic law/tangent/no-switch smooth-stage slice is eligible for implementation and individual REANA cases. It is not eligible to claim event-resolved, bounded or production moving MHD from this source review.

   The following registered gates remain unchanged:

   | Family | Required measurement, with original scope |
   | --- | --- |
   | SM-LAW | SM1/SM2 dimensions, d=0, taper joins, weak/nonzero B, three-axis lifts, joint boost; alpha=0 and alpha=1/4 separately labelled. |
   | Midpoint SM-STAGE | At least four macro halvings, independent same augmented-ODE reference, order>=1.8 above exposed floors; history maximum lifted generator error <=1e-5 Lmin0 and reference uncertainty <=1e-10 Lmin0, with the parent's state/field gates and selected B meaning. Retain private ZM, nu, actual paths and inner errors. |
   | SM-GCL / geometry | Genuine irregular nonuniform 3D deformation; independently rebuilt actual midpoint/physical endpoint volumes; GCL<=1e-12 and state/budget<=1e-10, component compatibility and centroid identities. |
   | SM-PATH / S-EVENT | Mandatory E1–E5 coverage; physical exchange error<=1e-3 and decreasing with refinement; Jcent mass/Jarea<=1% with <=0.1% reference uncertainty and original root bounds; epsilon 2^-28 alias and typed unresolved controls. Parent three-branch discrepancy<=1e-4 is a controller comparison, not a coverage proof. |
   | SM-PHYSICS / S-PARTITION / S-BOOST | Genuine full-vector nonzero B; spatial order>=1.8, field/state boost<=1e-8, budget<=1e-10; raw mean<=1e-9 B_scale and signed/sum-absolute excess partition<=1e-3 initial EB where prescribed, independent divergence/target/normal residuals and positive predicted/final closures. |
   | SM-BOUND/SOURCE | U1–U4/moving-wall operators, gravity work, active births/ISM, retry/restart and domain/ambient/full-duration isolated-galaxy/encounter controls. No rigid, planar or zero-field replacement. |

   A compact falsifiable first packet should expose: (a) private W0 versus physical nu rate/cache identity and no leaked exchange; (b) no-switch full-rank genuine-3D midpoint/order controls against an independent coupled ODE; (c) same-H inner refinement versus recomputed-H outer rejection, ID/lift/epoch/RNG restoration; (d) the distinct coverage/witness negatives in finding 6; and (e) constant translating-box rounded-cloud/taper and accepted-source/restart records as their prerequisites become ready. These are selections from existing required controls, not new thresholds or generated arrays. Independent references must not reuse the candidate production operator as their oracle.

   Each ready resolution, dt, branch/control, boost and restart remains a separate resource-declared REANA workflow after the appropriate dependency gates, with no aggregate resource cap. Parent stage:1147–1176 supplies initial per-case envelopes (for example S-FRAME/S-INC 1 thread/2 GiB/5 min and S-ORDER 2 threads/8 GiB/2 h); a literal midpoint case must declare its own sufficient resources before submission. None was submitted or executed here.

## Primary evidence and inspection limits

The complete retained PDFs were hashed and their relevant equation pages inspected directly, using fresh local text extraction/renders as recorded in the receipt boundary:

| Primary | Exact complete bytes | Inspected equation/page scope |
| --- | --- | --- |
| Springel 2009, arXiv:0901.4107v3, 67 pages | 9354438 bytes; SHA-256 dfe38502394b15a0b05bbb1f610b0e1533198594e33681e22a507162cc2d10f4 | Printed p.16 Eq.31; p.17 Eqs.32–34 and face-frame context; p.22 Eq.63; p.25 Eq.73/context. All four equation pages freshly rendered and visually read. |
| Springel, Mayer & Pakmor, arXiv:2609.35989v1, 37 pages | 14060781 bytes; SHA-256 6e12da18a86c57536fc26f2baf86d15d6db2e378e040a59bc9b82870b2dfcb84 | Gauge/fit/raw/stage context on pp.6–10,12–13,15–16; p.9 Eqs.61–66 and pp.15–16 Eqs.80–92 freshly rendered and visually read. |

P09 supplies the generator/face/instantaneous-volume context. Its thresholded sound-speed and separate displacement/dt regularizers are not the selected SM1 saturation. P26 supplies vector-potential/auxiliary/mean/stage context, including a different published source/time treatment. Neither publishes MF1–MF5, the selected tangent/GCL composition or this event controller. Those are project engineering derivations. The P09 arXiv v3 strip and later printed recompilation date are not conflated. This review made no new network retrieval or official metadata query; the author's earlier metadata-recheck statement is historical, not a new action by this reviewer. No external code was adopted.

Actual checks were Git-blob capture; SHA-256/byte comparisons; source/JSON/relative-link inspection; retained PDF extraction/rendering and visual equation reading; and the manual derivations above. Both complete subject files were read. Relevant parent stages, frozen curl/event/boundary reviews and shared mesh/gravity/source interfaces were inspected at the pinned revisions. Required project context bytes were retained and consulted for mission, status, scientific limits and execution dependencies; this is not a fresh audit of every historical handoff result.

All **14** identities listed in the author inventory check matched, including its historical contexts checked at their own commits. All **37** retained/Git receipt comparisons and the subject's **four** relative documentation links passed the read-only checks. These are source/provenance checks, not numerical evidence. Two nonzero inspection commands are retained honestly: a git-show request for nonexistent GRAVITY_SOURCE_COUPLING_SPEC.md (exit128), resolved to the actual INTEGRATION_CONTRACT/GRAVITY_PARTICLES_SPEC; and an equation-locator search using nonexistent selected_equation_pages filenames (exit2), resolved to the retained P09_equation_pages.txt/P26_equation_pages.txt and successful corrected searches. Neither was an integrity or scientific failure. Some combined tool output was truncated; relevant sections were reread narrowly. No truncated output was treated as a pass.

The closed ignored [reading boundary](../../results/galaxy_midpoint_motion_review_20261122/sha256.json) contains **56 files**, 36,542,593 stored bytes. Its 9,087-byte manifest SHA-256 is **d4230d3b8a44cd860ba56bcee8059350f7f4aa1d33c96153d7a3a502c46cd7bb**. It excludes itself and the two owned review documents. The companion inventory pins this report and that manifest, avoiding a circular hash. It also retains exact source captures, primary PDFs/text/renders, manual derivation and inspection receipts. Earlier reviews and source observations were not edited.

No target module import, numerical test/probe, geometry/flux/operator evaluation, matrix factorization, root/RNG/quadrature/orbit evaluation, numerical fixture generation, build, reducer/evolution, snapshot/collector/verifier, workflow/service/network/private-configuration action, commit, push or delegation occurred. No empirical order, root/geometry enclosure, conditioning, event, physical or acceptance result was produced.

## Recommendation and remaining acceptance boundary

**Support the named midpoint alternative as a conditional smooth source design; request no new MF1–MF5 equation repair on the evidence inspected.** Keep the known event/controller dependency and literal/reference-packet preparation open. Do not promote this conclusion to topology, bounded moving-MHD or physical adoption. Both the alternative and the previously reviewed augmented-Heun proposal remain distinct, unimplemented choices until a later selection and its actual evidence.

The unchanged [fresh M1 scientific-output review](../M1_FRESH_SCIENTIFIC_OUTPUT_REVIEW.md), SHA-256 428f6fc47d69da4788e850ec510a1eb80c0de84d9739d965ca2a013a407083d2, independently supports the completed named fixed/rigid 2.5D candidate's registered scientific outputs. It grants no M1 acceptance, and it was not reopened here. Final metadata174/source/import-preflight/per-method output review, a coherent real full scientific collection, actual archive packaging and copied portable verification, separately closed reviewer boundaries and final joint output/archive review remain required before coordinator-scoped M1 acceptance. This task reviewed none of those changing acquisition paths or tools.

After actual M1 acceptance, the static-operator and literal-fixture gates, immutable preflight and each separate REANA case still precede the narrow slice described above. Independent coupled trajectory/event evidence, moving bounded Cdot/GCL and U1–U4, gravity/source work/activation, equilibrium, ambient/domain and full-duration live-merger gates remain open. The end goal stays genuinely deforming full 3D moving-Voronoi nonzero-MHD gas with live DM and old/new stars, isolated gravity and the published multiphase ISM/SF/feedback model. This review supplies no substitute for that goal and keeps all acceptance flags false.
