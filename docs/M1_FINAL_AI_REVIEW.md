# Independent AI review of the final M1 candidate

Review date: 2026-11-21. Reviewer: separately dispatched AI reviewer, distinct
from the implementing coordinator; no delegation. This is **AI review**, not
human peer review, author confirmation, or an M1 acceptance record.

**Recommendation: conditionally approve the named engineering reference within
the registered single-process, periodic, fixed/rigid 2.5D scope.** I found no
scientific source defect requiring a new numerical change in the inspected
candidate. Acceptance is still blocked by the absence of the completed fresh
integrated-source physical campaign and its final evidence review. Historical
campaign A passes its registered checks and its independently repeated
reductions; it cannot by itself certify the later integrated binary.

## Exact review boundary and evidence

The numerical source reviewed is development revision
`2bdcea0d28340e7429e10053a641f92d51fcc696`. Working HEAD at review was
`a6271b00e2871adaba3bbe8efe7b5ff9995dfcde`; its additional material is
documentation/read-only analysis. The reviewer verified **226** frozen
scientific/configuration files against both their snapshot hashes and
`git show 2bdcea0:<path>`. The full file inventory and raw-input identities
are in [input_verification.json](../tests/reference/m1_acceptance/review/input_verification.json).

Frozen snapshot SHA256:
`b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f`.
The one-commit export fixture is not substituted for the development revision.

The configuration is:

```text
bulk-frame-heun-quadratic-v1 --projection-screening 1 --riemann hlld-pressure --potential-limiter smooth-extrema
```

It uses iterative Jacobi-preconditioned projection, historical trial fraction
1, CFL .3, synchronized steps, f64, dimensionless units with mu0=1, periodic
boundaries, one process, and the declared two/four-thread Rayon case pools.
Gamma is 5/3 except Brio–Wu, which uses 2. `paper-global-v2` remains the
binary default, with its documented failed controls retained.

I read the required project/status/validation/acceptance/merge/audit documents,
inspected the candidate's source paths, the six independent reducers and
input adapter, and the registered production case/verdict paths. I also
consulted the primary [paper HTML, sections 4–5](https://arxiv.org/html/2609.35989v1#S4),
particularly equations 69–76 and 80–92, to check the departure classification.
The published endpoint procedure, Riemann-state induction source and frozen
second-stage cleaning source differ from this candidate. Its cubic deposition,
bulk gauge, projected rate, pressure blend and relaxed extrema policy must
remain engineering choices, not descriptions of unpublished AREPO behavior.
The existing M0 specification remains the detailed publication source map.

All new software tests/evolutions used here were executed by the existing
REANA campaign. Locally I ran only read-only integrity checks and reductions
of existing observations. I neither launched numerical probes nor changed,
restarted, cancelled, or submitted workflows, and did not alter the live driver.

## Verification actually performed

1. The supplied `verify_packet.py` returned **0 before adding review files**:
   25 archived files, 99 independent boost pairs, 112 wave cases, 18 primary
   reference cases, and 226 unchanged frozen scientific files. Independently,
   the reviewer verified the 94-file iterative-campaign archive, the original
   25-file packet, and the prescribed packet's 12 archived hashes.
2. For all **214 A cases**, the reviewer matched archived and local plans,
   run maps and checkpoints byte-for-byte; checked registered options,
   commands, resources, completed receipts, snapshot/binary/payload identities,
   receipt-to-raw-record hash and logical identity; and hashed each final CSV.
   A's per-case binary is
   `492b56e0b8f70519ac950f9f49c889dbaf462e97732eaf12e9be86f593ea8471`.
3. I reran all six inspected independent reducers, with fresh caches/output
   paths, on retained A observations: waves, medium, mean, physics boosts,
   primary shocks and primary vortices. All returned **0**. All six resulting
   reports are logically identical to the provisional reports, including the
   complete wave report with zero reused cases/pairs. Compact reviewer copies
   are under [review/](../tests/reference/m1_acceptance/review/README.md);
   duplicate raw-output copies generated during reduction were removed.
4. I independently refitted all eight spatial ladders with ordinary log-space
   regression and recomputed their residual standard errors. This uses no
   production measurement code. The results agree within 1e-13 with the
   packet's independently reduced fits.
5. The **fresh current-source preflight passes** on actual downloaded artifacts,
   independently hashed against all 12 entries of its artifact manifest.
   `execution.json` and `preflight.json` agree on all eight successful commands:
   fmt; strict all-targets/all-features Clippy; 236 debug Rust tests; release
   workspace build; 163 Python tests; 13 M0 algebra checks; reference integrity;
   and 245 release/all-target Rust tests. I inspected the relevant named test
   successes in both Rust logs, rather than inferring them from wrapper status.

Fresh preflight: `openmhd-m1-final-preflight-20261121.1`, execution ended
`2026-11-21T02:14:16.040890+00:00` (workflow completion was reported later).
Exported binary SHA256:
`18afcf0308338e2ea0ea7ef5e03dba46af9d7025f3ccf4a6a48ebbfe800d0725`.
The live log had submitted the short bounded workflow at 02:17:40 UTC; no
fresh physical phase pass is claimed by this review.

**Packaging finding, not a physical failure:** after adding the explicitly
permitted `review/` files, the supplied verifier returns **1 at line 23**.
[Its recursive file-set equality](../tests/reference/m1_acceptance/verify_packet.py#L20)
includes the new reviewer files although its immutable 25-file manifest does
not. No manifested input changed. The reviewer verifier explicitly checks the
original manifest entries and separately inventories reviewer outputs. The
coordinator must make the final verifier/archive boundary cover both packets
(or explicitly exclude a separately hashed review subpacket); do not remove
findings, change numerical thresholds, or call this a failed physical method.
I have not changed the existing verifier or evidence manifest.

## Source findings and deliberate departures

| Path / anchor | Independent assessment |
| --- | --- |
| [Conservative face exchange](../crates/mhd-vector-pot/src/general.rs#L484) | Each face is evaluated once; its five fluid exchanges are accumulated with opposite signs into the two owners in deterministic face order. Parallel work produces indexed face results, and the serial accumulation fixes summation/error order. Heun averages two conservative rates. No magnetic-energy reset or nonconservative pressure repair is hidden here. |
| [Face flux and ALE transform](../crates/mhd-core/src/lib.rs#L480) | Both states use a shared arithmetic normal B at preserved reconstructed gas pressure. The complete eight-entry HLLD/HLL flux blend precedes the laboratory transform; intentional blending and failed-HLLD fallback have distinct method labels. Signal-weighted completion changes the returned A-face state/normal EMF completion, not the already selected conservative flux. Face-state admissibility is checked; it does not prove admissibility of arbitrary later cells. |
| [Pressure stencil](../crates/mhd-vector-pot/src/general/pressure_blend.rs#L36) | Omega is the cube of the minimum positive pressure ratio over all faces incident on either owner. Its factorization into per-cell minima preserves that definition. The same scalar blends fluid and induction entries. There is no case-name, direction or row-symmetry switch. This is a distinct MHD engineering extension, not the cited HLLC-ADC method itself. |
| [Bulk gauge and sources](../crates/mhd-vector-pot/src/operators.rs#L524) | Stored periodic a, separate constant offset C with Cdot=Vref cross mean_B, and source (u−Vref) cross mean_B consistently retain the intended mean-field split. The distortion contracts H transpose with a; omitting the original offset-distortion term is deliberate. Advection uses b=w−u and the receiving cell's donor sign. Numerical induction EMF replaces the literal returned-state product in this candidate. None establishes arbitrary-flow Galilean invariance. |
| [Curl/recovery](../crates/mhd-vector-pot/src/operators.rs#L191), [quadratic fit](../crates/moving-mesh/src/quadratic.rs#L13) | All three A/B components are retained with z derivatives zero. B=mean_B+(Dy az,−Dx az,Dx ay−Dy ax), from unlimited double-neighbour quadratic derivatives; div(a) and grad(phi) use the corresponding raw path. Periodic images are separate fit samples, the intercept is free, weights are inverse distance, QR is reorthogonalized and poor rank/conditioning rejects. This wider field-recovery stencil is a selected departure. |
| [Screened projection](../crates/mhd-vector-pot/src/projected_rate.rs#L444) | The actual C and its volume-weighted transpose include baseline subtraction consistently. H=C transpose V C and D=diag(H); the code solves (H+κD)δ=C transpose V(target−Cr), then returns r+δ. κ=1 changes the objective; it is not just a preconditioner. Jacobi CG starts at zero, targets recursive relative residual 1e-11, checks the true residual at 1e-9 and stops after at most 24N iterations. RHS norm <=1e-30 returns the original rate. These are normal-equation residual tolerances, not universal bounds on physical-field error. |
| [Projection target](../crates/mhd-vector-pot/src/general.rs#L1212) | Both stages rebuild the target from the same selected induction face flux, including its rigid-frame Bn*w completion. The z completion uses the fixed gauge reference velocity. It is a target for correcting A's rate, not a second accepted finite-volume B state. Screening leaves a residual magnetic-rate mismatch. Conservative total energy plus curl recovery is an empirical coupling validated by the shock/vortex gates, not a proven discrete magnetic-energy identity. |
| [Heun stage reevaluation](../crates/mhd-vector-pot/src/general.rs#L1497) | Provisional Q/V and curl(a) refresh primitives, primitive/A limiters, auxiliary deposition, face solves, projected rate and cleaning. The final Q/a/phi update averages old and provisional rates; the origin also receives the trapezoidal update. Final recovery uses the new curl and the existing conserved energy. Cached accepted closure is the closure of that state. This is reevaluated Heun, not the historical frozen-source endpoint prescription. |
| [Motion/retry restriction](../crates/mhd-vector-pot/src/general.rs#L752), [rigid endpoint](../crates/mhd-vector-pot/src/general.rs#L658) | Heun rejects fluid-following and nonuniform prescribed motion. Rigid translation preserves metric/stencil data while updating periodic images. Rejected trials keep Q/a/phi/origin/offset immutable and halve dt; invalid closures have no floor or repair. The selected first-trial fraction is 1. Fixed/rigid validation cannot authorize deforming-mesh physical use. |
| [Smooth auxiliary velocity](../crates/mhd-vector-pot/src/auxiliary.rs#L181) | Continuous cubic deposition feeds periodic Hermite bicubic interpolation, with volume weights, persistent translated origin and 4/2/1 root fallback. The provisional stage rebuilds it. This is a documented 2.5D engineering representation, not the paper's adaptive tricubic implementation. |

### Limiter disposition

The [smooth-extrema implementation](../crates/moving-mesh/src/lib.rs#L880)
matches its registered definition. For a neighbour displacement d it compares
`qj−qi−Gi·d` and `Gj·d−(qj−qi)`; equal signs permit the smaller magnitude,
then the largest confirmed allowance widens the corresponding bound before
one factor in [0,1] scales that cell's gradient. For a quadratic, both
residuals equal one half d transpose H d. That confirms the curvature
interpretation, not smoothness of arbitrary data. A two-cell extremum can
also survive. Only the separate A face-advection copy uses this policy;
primitive limiting and raw curl/cleaning derivatives retain their own paths.

The bounded measurements explicitly record 3–10% worse fixed-mesh passive-loop
errors and 17–36% larger rim potential undershoot than the historical limiter.
No registered gate tests either quantity. The owner-authorized configuration
decision accepts that measured tradeoff; I find it scientifically acceptable
for this explicitly named benchmark reference with these disclosures. It is
not TVD, an extrema-preservation guarantee, or a general positivity/entropy
stability result. It must not become an undocumented binary default.

### Divergence and budget interpretation

[Diagnostics](../crates/mhd-vector-pot/src/diagnostics.rs#L160) measure three
distinct operators on recovered cell B: raw neighbour LS Dx Bx+Dy By;
arithmetic shared-face flux sum; and the shared-face sum after separate
neighbour-extrema-limited linear B reconstructions. Normalization is
sqrt(V/pi)*div(B)/(|B|+1e-12*Bscale), with a fixed benchmark Bscale. Signed
volume mean, RMS and absolute maximum are reported. These are independent
of the candidate quadratic curl; no machine-zero local div(curl) follows.
Phi cleans div(a), not B. The registered vortex gate selects the limited-face
dimensionless RMS; the other two remain reported diagnostics.

The five conserved budgets use fixed initial reference scales, including
nonzero momentum scales. The independent reducers inspect recorded histories
and snapshots; they do not independently rerun face fluxes, stepwise extrema
or divergence operators. Source inspection supplies the conservative exchange
and positive accepted-closure contracts. A's largest recorded normalized
budget is 7.2367e-13, below 1e-10. Across the 214 cases there are 957,006
accepted steps, 463,020 CFL retries, no recorded geometry/state rejections,
and 1,227,457 accepted-stage HLL fallbacks. These actual counters must remain
visible; passing gates does not imply an evolution without fallback or retry.

## Physical evidence and gate coverage

### Alfvén, loop and mean-field results from A

The independently rerun wave reduction covers all 112 runs: 64 Alfvén,
32 coupled loops and 16 temporal runs. Its 48 pairs and eight spatial ladders
pass, and 12 temporal comparisons are measured. The other phases add 24
medium, 12 mean-field and 15 physics pairs, for **99** pairs with no omitted
case. Analytic norms are independently rebuilt, including the corrected R1
potential convention and the wave phase sign. The wave fit uses N64/128/256,
not the more favorable coarse two-point observations.

| Jitter | Parallel speed | Mesh | B L1 fitted order | Residual standard error | Finest B L1 / .1 |
| ---: | ---: | --- | ---: | ---: | ---: |
| 0 | 0 | fixed | 1.9362392 | .0155662 | .00070955 |
| 0 | 0 | comoving | 1.9362392 | .0155662 | .00070955 |
| 0 | 1 | fixed | 1.9589917 | .0157120 | .00092884 |
| 0 | 1 | comoving | 1.9362392 | .0155662 | .00070955 |
| .15 | 0 | fixed | 1.9098558 | .0392990 | .00080322 |
| .15 | 0 | comoving | 1.9098558 | .0392990 | .00080322 |
| .15 | 1 | fixed | 1.8833871 | .0370271 | .00110739 |
| .15 | 1 | comoving | 1.9098558 | .0392990 | .00080322 |

All meet the registered order >=1.8 and amplitude-relative error <=.02.
With only three deterministic points, the residual standard error has one
residual degree of freedom; it is a fit diagnostic, not a confidence interval
or a justified probabilistic guarantee that the asymptotic order exceeds 1.8.

Both boost normalizations are actually checked. In the wave matrix the
largest Alfvén amplitude-normalized component/vector comparison is
1.2994e-11 (limit 1e-8); the coupled-loop maximum B L1 divided by
.001/sqrt(4*pi) is 1.9020e-9 (limit .001). Mean-field maximum transformed
component discrepancy is 9.3259e-15 (limit 1e-9); all 12 pairs also check
positions, volumes and auxiliary roots. These bounded joint fluid/grid
boosts do not establish invariance for unrelated boosts or deforming meshes.

All four N64 temporal groups attain each requested maximum dt cap
(4e-4, 2e-4, 1e-4) against 2.5e-5, with no state/CFL rejections. Very small
reported minimum dt values, about 1.1e-14–8.3e-14, are landing residuals;
they do not describe the main step size. Successive B orders are
1.9803–2.0754. A/phi and physical B are reported separately, and the
reference has finite dt. This supports second-order behavior in these
same-grid tests. **There is no registered temporal-order pass threshold**, and
none is added here. It is not a general physical time-accuracy theorem.

### Shock/vortex references and scopes

The reference is independently implemented Athena++ revision
`209a9258ee158d1965557f1a5c4193101b704dd9` (packet tag v24.0), not an exact
Riemann solution or the paper authors' output. The archived provenance pins
inputs, commands, compiler, binaries, license and outputs; the fresh REANA
reference check passes. Brio uses 8192 cells; the vortex uses the 512-squared
reference reduced to the declared 64-squared bins. Reference refinement
changes are retained, not set to zero: Brio scaled L1 .00018–.00039,
vortex .00643/.01207/.00986/.00881 for rho/p/Bx/By. These bound the practical
resolution interpretation; they are not statistical error bars. I did not
re-evolve Athena or assert independent reproduction of its binary build.

The shock reducer independently integrates the decimal reference over
rectangles reconstructed from raw face planes, using 50-digit prefix
integrals and periodic/rest-frame interval intersections. It verifies cell
areas and full analysis-window coverage, rather than trusting production
polygons. All twelve regular/column base/boost cases and four ladders pass.
At nx1024 the largest primary errors over those families/frames are
rho .002364, p .002476, vx .005051, By .003326, versus .03/.04/.03/.04;
each finest error is below its coarsest error. Maximum independent/production
norm disagreement is 3.8164e-16.

The vortex reducer similarly reconstructs regular-cell rectangles from raw
planes and integrates periodic intersections into all 4096 bins, checking
coverage before measuring independently normalized errors. Six primary cases
and both ladders pass; finest errors are .007388/.015927/.014473/.012474
versus .06/.1/.1/.1, and improve over N64. Maximum norm disagreement is
1.1103e-16. These independent reference reductions cover the primary meshes;
the all-30-case physics boost reduction separately covers jittered cases.

The [approved Bx amendment](../benchmarks/m1/shock-bx-amendment.json) is applied
as written: regular and nonuniform y-invariant column shocks retain the
1e-8 Bx gate and primary profile limits. Planar-jitter Bx/profile errors
remain diagnostics, never counted as successful Bx/profile gates. The
maximum final primary Bx error independently observed is 1.0326e-14;
the all-mesh diagnostic maximum is .02910 and must not be hidden behind it.
All shock families retain state, budgets, boost and seam checks. Maximum
recorded signal travel is .391251, below .45; this is the registered
stage-sampled isolation diagnostic, not a rigorous nonlinear propagation
theorem. Vortex primary reference limits apply to regular meshes;
positivity/budgets/boost and mean-field/divergence apply to both families.
Maximum recorded vortex mean-field drift is .000473852 (limit .001), and
limited-face normalized divergence RMS .0402819 (limit .1). All 15 physics
pairs pass; largest normalized component L1 is 7.4078e-11 (limit 1e-8).

## Prescribed-flow applicability: approved within its historical scope

The historical `constant-flow-voronoi-v1` evidence has 32 completed runs,
16 passing pairs, 16 passing comoving checks and two passing fixed-grid
ladders. Finest A L1/peak is .00059909/.00063111 on regular/jittered meshes,
below .1, with decreasing ladder errors. All 12 archive hashes verify.

The old claim that the entire current gradient prefix is byte-unchanged
would be false. I specifically inspected the changed dependencies:

- Driver, `Transport`, divergence diagnostics and the `TransportStencil`
  fragment are unchanged. Loop initialization/reference prefix is unchanged
  in the current applicability record. `Transport` uses the historical
  neighbour limiter, linear curl, constant relative velocity and Heun
  transport; the new coupled projection/pressure/gauge/limiter paths are not
  called. Equal fluid/grid velocity takes the unchanged exact-copy branch.
- `Derivatives::gradients` uses the same sample baseline, weighted subtraction
  and sample summation order as scalar `gradient`. `limit_all` preserves
  per-component neighbour extrema, face traversal and factor operations.
  The scalar error path is retained. The underlying `fit_derivatives` suffix
  is byte-identical to the transport execution archive.
- The driver creates no Rayon pool; indexed map/try_map therefore use their
  ordered serial branch. Per-cell edge maps cannot collide because owner ID
  is part of every key. Their final BTreeMap face ordering is unchanged.
- Mesh clipping preserves crossing arithmetic, vertex order and, even for
  all-inside clips, the reference's vertex rotation before centroid/area
  sums. Ordered tree pruning skips only planes beyond the polygon bounding
  circle, using conservative periodic image bounds; surviving planes retain
  their original pass/ID/image order. This supports unchanged geometry and
  stencils for the historical cases by mathematical inspection.
- Current-source REANA debug **and** release logs pass scalar/batched equality,
  reference/optimized clipping, all-pairs pruning, geometry/thread equality,
  irregular comoving-loop preservation and both-sign transport covariance/
  refinement tests. I inspected their source coverage and named successes.

Together, this supplies the requested current-source applicability
justification for retaining the historical kinematic evidence. **It is not
current-binary full-ladder reproduction**, nor coupled gas/energy validation.
No further prescribed-flow campaign is required by this scoped review if
these frozen dependencies remain unchanged. A later transport/mesh/operator
change requires a fresh applicability assessment or REANA reproduction.

## Conditions that remain before M1 acceptance

1. Finish the existing integrated-source campaign without duplicating it.
   Verify its actual short bounded results, 48 medium and 24 mean cases and
   precondition before accepting its 112 wave and 30 physics results. Every
   registered case, seven phase checks and both retained calibration checks
   must pass. Missing/download observations must be recovered and checked,
   not silently counted complete or called a physical failure.
2. Recheck the exact registered cases/options, source/snapshot identities,
   declared resources, execution receipts, artifact manifests, actual
   commands, and the preflight binary above for all per-case workflows.
   The short bounded wrapper may build its own binary of the same immutable
   snapshot, as the registered sequence permits; retain its distinct hash.
   No .95 trial fraction, cached projection or mixed limiter/flux metadata
   can stand in for A.
3. Independently reduce the fresh 112 wave inputs, 99 total boost pairs,
   twelve primary shocks and six primary vortices. Alternatively, prove
   byte identity **for every raw input being reused**, including geometry
   and projected-bin inputs, with the already reduced A artifacts. A reused
   error table, matching final norm, or a handful of identity controls is
   insufficient. Keep adapters visibly separate from original provenance.
4. Inspect the new eight fit values/uncertainties, both wave boost
   normalizations, temporal actual caps/rejections/A/phi/B, all state/budget/
   mean-field/divergence/Bx/seam scopes, and actual fallback/retry counts.
   Apply the existing thresholds; explain material changes rather than
   assuming the integrated build repeats historical A.
5. Archive the actual fresh outputs and compact independent reductions with
   hashes, fix the structural verifier coverage issue described above, and
   obtain the coordinator-requested final output review. This source review
   remains applicable only while the pinned scientific files stay identical.

Completion would validate this named **single-process 2.5D fixed/rigid
engineering reference**. It would not establish paper/AREPO equivalence,
general Galilean invariance, a TVD/positivity theorem, 3D or deforming-mesh
physical acceptance, MPI, local steps or adaptation. Historical default
failures and rejected comparators remain part of the scientific record.

No milestone is marked accepted by this report.
