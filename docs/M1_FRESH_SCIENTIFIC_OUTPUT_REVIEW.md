# Independent AI review of the completed fresh M1 scientific outputs

Review date: 2026-11-22. Reviewer: separately dispatched AI reviewer, distinct from the implementing coordinator; no delegation. This is **AI review**, not human peer review or milestone acceptance.

**Recommendation: support the scientific-output portion of the named M1 candidate, conditional on preserving the exact reviewed identities in the final evidence boundary.** The completed fresh outputs satisfy the unchanged registered scientific gates. I found no demonstrated scientific-output blocker in this campaign. This closes the missing fresh-physical-output condition in the earlier [source review](M1_FINAL_AI_REVIEW.md#L7), within its stated scope; it does not close the remaining metadata, collection, portable-archive or joint final-review conditions. **M1 remains unaccepted.**

## Review boundary and identities

Entry HEAD was `642ac1b1de549d0d0bfcf3e6c3ddb4cefe803eb6`. The scientific development revision is still `2bdcea0d28340e7429e10053a641f92d51fcc696`. I compared all **226** files in the original scientific/configuration review map with that revision's Git blobs, the submission snapshot and the working scientific files; all agree. The exported fixture revision `8aa9dcbfa19b314970042e840d561d0ef5838489` is a separate provenance identity, not a replacement development revision.

| Identity | SHA256 |
| --- | --- |
| Submission `snapshot.json` | `b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f` |
| Exported per-case binary | `18afcf0308338e2ea0ea7ef5e03dba46af9d7025f3ccf4a6a48ebbfe800d0725` |
| Per-case source archive, assembled from the staged parts | `4c0f9cfa8d178e7204162e1f1e8d42e6112f18f1748baf761fedb8e7e087cc37` |
| Completed seven-phase verdict | `c59840c3dcf1997234f22b569d51653db74ef32516b1f889a585dc60d5060ee6` |
| Root's 238-input identity checkpoint, independently joined below | `83c49eaa044c6b4295d246b89f58319667956d98439c2fab5c402929f801d7d7` |

The verdict is `results/followup_iter_verdict_20261121.json`; its whole bytes equal the retained `fresh_all_phase_verdict_checkpoint_20261122.json`. Its `full_m1_accepted` is false.

The configuration is `bulk-frame-heun-quadratic-v1 --projection-screening 1 --riemann hlld-pressure --potential-limiter smooth-extrema`, **iterative projection**, trial fraction **1**, CFL .3, f64, globally synchronized steps, one process and declared two/four-thread Rayon pools. No accelerated-projection or trial-fraction override appears in the 214 recorded commands. The JSON null trial-fraction option means the unchanged historical default 1. Units are dimensionless with mu0=1; gamma is 5/3 except Brio–Wu's 2. The physical scope is periodic **fixed/rigid 2.5D**. `paper-global-v2` remains the binary default with its failed controls preserved.

I read the required project context, acceptance/full-validation plans, previous independent source review, production gate paths, independent reducer/input-adapter sources, reference contracts and existing reports. I used source/hash/JSON/CSV inspection and arithmetic on existing reported values. I did **not** import or call target modules, rerun a reducer, test, build, preflight, numerical operator, probe or evolution, or use a network/workflow/service client. In particular, I did not inspect the changing whole-catalog metadata acquisition directory. No source observations, evidence packets or previous reviews were edited.

The retained boundary is `results/m1_fresh_scientific_output_review_20261122/`: **2,953** listed files, **140,433,679** bytes, excluding its own manifest. Its `sha256.json` SHA256 is `68ce16f592fa46e7ce92447f44e358cf4f057a12d3a462c6d6892dd47ce2c687`. It contains exact inspected source/context/report/metadata copies and reviewer receipts; `used_input_identities.json` identifies 14,768 used input paths, including the staged inputs and original large raw artifacts. The large raw data and binary parts are identified by original paths and hashes rather than claimed included in this review boundary. The companion [source inventory](m1_fresh_scientific_output_review_sources.json) pins this report and the closed receipt manifest without a hash cycle.

## Numbered findings and dispositions

### 1. Supported: complete fresh execution and input coverage, independently joined

The registered configurations, actual plans, case specifications, payloads and resource declarations agree for **48 medium + 24 mean + 112 waves + 30 physics = 214** cases. For every case I joined its plan name/directory, workflow name/version/UUID, staged case/payload/runner/snapshot/preflight input hashes, execution receipt, record hash and logical record, downloaded artifact manifest, current run map and checkpoint. All 214 executions record completion, return code zero, the required single-case gate, the same snapshot and exported binary; checkpoints contain no observation errors, execution failures or required scientific failure. The recorded workflow states are terminal finished/version 1. This is assessment of retained observations, not a new platform query.

Every command's candidate/profile, limiter, screening, mesh motion/velocity, boost, n/jitter, target time, gamma, solver and applicable dt/column/mean-field arguments agree with its case. Each case has its declared two/four threads and its own workflow/resources. Reassembling the staged source/binary inputs by hashing their bytes gave the identities above; nothing was executed.

I independently hashed and joined **all 238 actually present fresh raw inputs**: 214 final CSVs, 18 primary geometry files and six primary vortex projected-bin files. The joins include the actual remote manifest prefix `outputs/raw/<case>/<file>`, per-run hash, execution/workflow receipt and root identity checkpoint. All 238 hashes also equal the corresponding historical A inputs. That equality is a result of checking fresh files and their fresh receipts; no historical A file was substituted for a missing fresh input.

I also parsed all **214 final CSVs / 2,688,256 cells / 1,501,580,629 bytes** directly: expected row count and sequential IDs, exact final time, all stored fields finite, and positive final volume/density/pressure. This was representation inspection, not an independent rerun of an analytic norm, geometry integral, divergence operator or time integration. Each file remained unchanged during its read. Detailed per-case/raw receipts are in `phase_and_raw_joins.json` and `raw_csv_representation_receipt.json`.

### 2. Supported with disclosed control failures: exact seven-phase inventory and short/preflight provenance

The actual verdict contains the exact seven phase/check inventories derived from the frozen producer, with **58/58** true checks and no phase error: bounded-short 6, medium 10, mean 12, wave calibration 5, vortex calibration 3, physics 9 and waves 13. I checked the underlying coordinates, cases and measurements described below, rather than relying on this all-true object. The definitions are [fanout_campaign_verdict.py:52](../scripts/fanout_campaign_verdict.py#L52), [:78](../scripts/fanout_campaign_verdict.py#L78), [:123](../scripts/fanout_campaign_verdict.py#L123), and [run_m1_campaign.py:59](../scripts/run_m1_campaign.py#L59). Exact names are retained in `final_scalar_provenance_receipt.json`.

The bounded workflow `openmhd-fu-bounded-iter-20261121.1` completed its four source-defined stages: shock-short 4 records, symmetry 8, short waves 21, quick physics 20. I checked all 12 downloaded artifact hashes, and the actual summary/analysis/run-map bytes inside its raw tar against the stage receipts. `waves_short` correctly uses `analysis.json`. Its separately built binary is **`090acac224588ff802f430290627f1f59ce764b0797e007c66708b0668c3a6ea`**, not the 214-case export. The short gate's 216-entry source map matches the frozen submission snapshot exactly: 215 shared entries equal the earlier 226-file map, plus `rust-toolchain.toml`; 11 files in the broader review map are not listed by that bounded recorder. There is no changed shared scientific file. Its own generated source-archive hash differs from the per-case upload archive; neither archive nor binary equality between these two build paths is asserted.

Two important negative observations remain visible. Symmetry's two planar `paper-global-v2` controls fail conservative/curl positive-state closure near t=.00336, so its process returns 1 and `all_gates_passed=false`; the registered bounded gate explicitly checks the symmetric family and **candidate** planar family. Quick physics has two N16 jittered vortex drift values about .001654, above .001, so its broad all-grid diagnostic flag is false. The frozen bounded policy gates the finest quick grid of each family, while requiring every quick run to complete, remain positive/conservative and pass boosts ([run_m1_bounded.py:71–99](../scripts/run_m1_bounded.py#L71)). Those selected checks pass. These controls are not relabelled passes or failures of the final 214-case matrix; the full N64/128/256 vortex diagnostics all pass below.

The actual preflight's 12 artifact hashes also agree. The earlier independent review already inspected the successful fmt, strict Clippy, 236 debug Rust, 245 release/all-target Rust, 163 Python, release build, M0 and reference-integrity results ([M1_FINAL_AI_REVIEW.md:81](M1_FINAL_AI_REVIEW.md#L81)). These are historical executed checks whose provenance was rejoined here, **not new executions or newly counted test passes**.

### 3. Supported: all 99 independent boost pairs, both normalizations and correct frames

The six completed independent reports have these exact stored identities:

| Report | Coverage | SHA256 |
| --- | --- | --- |
| `tests/reference/m1_acceptance/fresh/medium_independent.json.gz` | 48 / 24 pairs | `9ba2358ae25a3fdba1d63d36e510593651b0afa7532e3480e93f8c89817cf457` |
| `tests/reference/m1_acceptance/fresh/mean_independent.json.gz` | 24 / 12 pairs | `22971970065e0e665dd35685ff8b04e594f90dfc471686f7ddbb9224d2bafe9b` |
| `results/independent_fresh_waves_checkpoint_20261122_0021.json` | 112 / 48 pairs; 8 spatial, 12 temporal comparisons | `537d7bf7320c81c7a4d2357ebe0fb490d9b7359d0f1cfc5d02e3fe5cc453b05b` |
| `results/independent_fresh_physics_boost_complete_20261122/report.json` | 30 / 15 pairs | `adaaf0fef8a4e127f733e528cc764d72e9c503e464579eabfd68fc9410872709` |
| `results/independent_fresh_shock_checkpoint_20261122_0001/independent_reference.json` | 12 primary cases / 4 ladders | `ac65789b65e3080893aaf85c0c63b876a84826b62b6c27cc2a8859eea3e93efa` |
| `results/independent_fresh_vortex_checkpoint_20261122_0005/independent_reference.json` | 6 primary cases / 2 four-field ladders | `b1b6930147d97700f8171debf21b4607f1d061365a8211dd791c0ff49a8cd24d` |

I read the independent measurement programs completely: `reduce_waves.py`, `reduce_boost_pairs.py` (used for medium and physics), `reduce_mean.py`, `reduce_shock.py`, `reduce_vortex.py`, and `prepare_inputs.py`. Their exact sources/hashes, imports, stage sources and source/run-map fingerprints are retained. They do not import production norm, polygon-clipping, bin-integration or evolution routines; the medium/physics adapter shares the separately inspected independent wave utilities. They remain measurements of production-generated states and diagnostics, not a second MHD implementation.

All report inputs bind to the fresh raw hashes. The full wave report records **zero reused cases and pairs**. Its 112-case map and manifest, physics-boost's 30-case map/checkpoint and all 54 physics input receipts, and primary reference maps/snapshots are joined to the actual fresh records. The older read-only capture used for the physics context establishes these bytes; it does not certify repaired final-collector lifecycle or archive safety.

The pair partition is exact and non-overlapping within each phase: **24 + 12 + 48 + 15 = 99**. The 16 temporal runs are not falsely counted as boost pairs. The independent measurements use volume-weighted L1/L2, actual positions/volumes and the prescribed joint boost (2,-1,0), including the inverse kinetic-energy transform

`E_rest = E_boost − rho v_boost·b + rho |b|²/2`.

This equals inversion of the usual forward Galilean kinetic transform. Spatial comparisons remove the periodic boost translation. The wave reducer checks both amplitude (.1 for B/v) and mean-field/initial-speed conventions (B=1; speed=max(sqrt(parallel²+.01),sqrt(1/6))), with fixed rho/p/energy scales. Loop's magnetic scale is `.001/sqrt(4pi)` with the separate .001 gate; physics uses the pinned problem scales and fixed initial budget speed/energy scales. See [reduce_waves.py:83](../tests/reference/m1_acceptance/reduce_waves.py#L83) and [reduce_boost_pairs.py:16](../tests/reference/m1_acceptance/reduce_boost_pairs.py#L16).

Existing recorded maxima, compared directly with the unchanged limits:

| Family | Largest independent normalized L1 | Limit |
| --- | ---: | ---: |
| Medium Alfvén, amplitude / alternate | 2.92602e-12 / 7.16724e-13 | 1e-8 each |
| Full Alfvén, amplitude / alternate | 1.29942e-11 / 2.29514e-12 | 1e-8 each |
| Medium / full coupled-loop B | 4.41303e-14 / 1.90200e-9 | .001 |
| Nonuniform mean-field, transformed components | 9.32587e-15 | 1e-9 |
| Shock/vortex, normalized components | 7.40772e-11 | 1e-8 |

All reported position/relative-volume limits also pass (1e-11 for wave/mean; 1e-9 for physics). This establishes the registered matched-boost observations, not general Galilean invariance or a coupled-loop exact-solution theorem.

### 4. Supported: actual mean refinement and the selected calibration observations

The mean checkpoint contains exactly four candidate rows: jitter 0/.15 crossed with n/dt refinement. Coordinates are n=[8,16,32,64] at dt=.00025 and dt=[.001,.0005,.00025] at n=16. I tied every value to the selected actual boost pair, checked finite nonnegative measurements and the exact successive-order array lengths. Their B residuals are roughly 2.7e-17–1.94e-16; negative or noisy apparent orders at roundoff are recorded, not hidden. The frozen gate asks that refinement be **measured**, not that these residuals attain an accuracy order ([run_m1_campaign.py:76](../scripts/run_m1_campaign.py#L76)).

The wave calibration is exactly the two N128, jitter .15, parallel=0, fixed-motion, unconstrained-dt base/boost cases selected at [fanout_campaign_verdict.py:156](../scripts/fanout_campaign_verdict.py#L156). Their actual B L1/.1 values are **.0031641022277521355 / .0031641022277231244**, below .02. Selection is not replaced by an unrelated passing spatial row. The selected N128 jittered unboosted vortex also completes: drift **9.41445e-5**, limited-face dimensionless RMS **.0253198**, with correct candidate configuration. Calibration is not a substitute for the complete ladders.

### 5. Supported: all eight spatial gates; temporal observations retain their proper scope

The full fresh independent report contains all eight four-resolution Alfvén ladders (N32/64/128/256), positive finite B L1 errors, and the registered finest-three fits. Production and independent recorded analytic errors, slopes and residual standard errors agree; the largest scalar difference checked is **6.22e-15**. The comparison uses `256*binary64_epsilon*max(1,abs(a),abs(b))` only as a roundoff-consistency scale, including near-zero quantities. It is not a scientific error budget or new acceptance tolerance.

| jitter | parallel | motion | Finest-three order | Residual slope SE | Finest B L1/.1 |
| ---: | ---: | --- | ---: | ---: | ---: |
| 0 | 0 | fixed | 1.936239197 | .01556623 | .000709546 |
| 0 | 0 | comoving | 1.936239197 | .01556623 | .000709546 |
| 0 | 1 | fixed | 1.958991724 | .01571197 | .000928843 |
| 0 | 1 | comoving | 1.936239197 | .01556624 | .000709546 |
| .15 | 0 | fixed | 1.909855768 | .03929900 | .000803223 |
| .15 | 0 | comoving | 1.909855768 | .03929900 | .000803223 |
| .15 | 1 | fixed | 1.883387107 | .03702710 | .001107388 |
| .15 | 1 | comoving | 1.909855768 | .03929900 | .000803223 |

All meet **order>=1.8** and **finest B L1/.1<=.02**, unchanged. For x=log h, y=log error at the three equally spaced finest grids, the least-squares slope is `(y64−y256)/log 4`; the middle observation affects the residual. The recorded standard error is `sqrt(SSE/((3−2)*sum((x−mean(x))²)))`, with **one residual degree of freedom** ([reduce_waves.py:199](../tests/reference/m1_acceptance/reduce_waves.py#L199)). I checked this algebra and the recorded scalar consistency, not a new regression. These SEs neither enclose discretization error nor establish a probabilistic confidence interval; no uncertainty threshold was invented.

The 16 temporal cases supply **12 actual comparisons against four same-grid N64 dt=2.5e-5 references**. Every requested cap .0004/.0002/.0001 is attained by recorded dt_max; reference and comparison identities/configurations agree. Those 16 runs record no state/CFL rejections. The very small landing dt_min values (about 1.12e-14–8.26e-14 in the comparison runs) are explicitly retained; they do not replace attained bulk dt caps. The report separates physical B and bx/by/bz from gauge-dependent ax/ay/az/phi ([reduce_waves.py:117](../tests/reference/m1_acceptance/reduce_waves.py#L117)). Recorded successive B orders range **1.98025–2.07538**. These are finite fine-dt, same-spatial-grid comparisons, not a zero-dt solution or an independently bounded temporal truncation error. The registered gate requires completed finite measurements, **no temporal order threshold**.

### 6. Supported: primary shock references and separate Bx/seam diagnostics

All 18 full shock cases retain completion/state/budget/boost and signal-tracking/seam checks. The **12 regular/column cases** have the Bx gate and duplicated `bx_max_error`/`bx.final.max` values in agreement; each is <=1e-8. The six planar-jitter cases explicitly have `gate_applies=false`, `passed=null`, no invented `bx_preserved` true flag, and measured Bx values. The largest planar-inclusive final Bx error is **.0290931**, which is disclosed as a diagnostic. The independent primary shock calculation separately measures final Bx directly from its raw snapshots: maximum **1.03251e-14** across the 12 primary cases, equal to the production recorded maximum for each case. This is more than matching boosted errors to each other.

All shock cases record active signal tracking and nonnegative accumulated travel; maximum **.3912509705 < .45**. The source diagnostic accumulates x-characteristic travel in the rigid mesh frame over the accepted reconstructed stages/final closure. It is the registered sampled seam-isolation diagnostic, not a proof about all nonlinear characteristics between samples. Exact semantics and the planar amendment remain [run_m1_physics.py:233](../scripts/run_m1_physics.py#L233), `benchmarks/m1/shock-bx-amendment.json`, and the unchanged packet.

All **12 primary reference cases / four ladders** use the exact fresh final/geometry inputs. The independent reducer reconstructs rectangles from raw oriented face planes and verifies their volumes, rather than importing production polygons. It shifts to the shock rest frame, integrates the pinned 8192-cell Athena primitive samples with 50-digit Decimal prefix integrals over the central periodic analysis window x=[.5,1.5], and checks analysis volume .125 ([reduce_shock.py:100](../tests/reference/m1_acceptance/reduce_shock.py#L100)). It retains L1/L2 and its independent Bx result. All four ladders have nx=[256,512,1024], finest errors below coarsest, and satisfy the unchanged component limits:

| Finest scaled L1, maximum over primary ladders | rho | p | vx | By |
| --- | ---: | ---: | ---: | ---: |
| Measured | .00236359 | .00247548 | .00505077 | .00332600 |
| Limit | .03 | .04 | .03 | .04 |

Largest independent/production reference-norm disagreement is **3.82e-16**. The gate is finest below coarsest, not an unstated requirement of strict improvement at every intermediate grid. Planar profile errors remain diagnostics rather than a missing gated reference ladder.

### 7. Supported: every vortex diagnostic and both independent four-field reference ladders

All **12** full vortex cases, including jittered cases and both boosts, satisfy the actual per-case recorded-history gates, not merely the six primary norms: maximum `mean_B_drift_over_Bscale_max` **.0004738514 <= .001** and named `limited_face_dimensionless_divB_RMS_max` **.04028185 <= .1**. I checked the exact named key/flag sets, finite values and limited-face maximum against the history; the source explicitly takes the norm of the history mean-B drift divided by the fixed B scale ([run_m1_physics.py:241](../scripts/run_m1_physics.py#L241)).

The three reported divergence operators remain distinct: raw neighbour least-squares DxBx+DyBy, arithmetic shared-face flux, and shared-face flux after independently neighbour-limited linear B reconstruction. Their dimensionless normalization is `sqrt(V/pi)*div(B)/(|B|+1e-12*Bscale)`, with volume-weighted mean/RMS/absolute maximum. The registered gate selects the **limited-face RMS**. None is the candidate quadratic curl stencil, and div(curl)=0 is not asserted; phi cleans div(a). The unchanged [diagnostics source](../crates/mhd-vector-pot/src/diagnostics.rs#L160) and prior source review remain applicable.

All **six primary regular vortex cases**, both N64/128/256 ladders and all four fields, have independent raw-face/64x64-bin overlap integration, rest-frame periodic translation, volume/centroid/coverage checks, and independently retained bins ([reduce_vortex.py:87](../tests/reference/m1_acceptance/reduce_vortex.py#L87)). Both independent and production arrays contain 4,096 finite entries for rho/p/Bx/By in each case; their existing array values differ by at most **4.20e-15**. These are averages of the **primitive pressure field**, as defined by the reference packet, not pressure recovered from averaged conserved energy. I compared the existing arrays and their identity/shape; I did not rerun the geometric integral.

| Finest scaled bin L1, maximum over both ladders | rho | p | Bx | By |
| --- | ---: | ---: | ---: | ---: |
| Measured | .00738817 | .01592673 | .01447317 | .01247431 |
| Limit | .06 | .1 | .1 | .1 |

Each finest value is below its coarsest value. Largest independent/production norm disagreement is **1.12e-16**. Jittered vortex reference errors remain reported diagnostics, while their state/budget/drift/divergence/boost obligations are all applied.

### 8. Supported with limits: reference provenance, budgets, retries and deliberate engineering tradeoffs

The external references are the pinned Athena++ **v24.0**, revision `209a9258ee158d1965557f1a5c4193101b704dd9`, CT/HLLD reference family described in `docs/M0_BENCHMARK_PACKET.md` and `tests/reference/external_mhd/provenance.json`. The actual Brio8192 gzip SHA is `9fd60e9c2e15939f4e9f162451cec12b8324910d3e1b59d192a78c8be606a878`; vortex512 gzip SHA is `099ee67270521db7df3e927f7c9374d16b28eff0fe12ce5658914c2838adc9e9`; the packet SHA is `dbdbea9346a6c6cdc67aa97d238545039e630caef2d390e87cba966e8212aae9`. Report reference/packet hashes, provenance and retained coarser references agree. These are finite-resolution independent-code references, not exact solutions or paper/AREPO output. No reference was rebuilt or evolved here.

The pinned coarse-to-fine sensitivity estimates are Brio rho/p/vx/By **.0002391/.0001795/.0003934/.0002534**, and vortex rho/p/Bx/By **.006428/.012074/.009864/.008812**. In particular, vortex reference sensitivity is material relative to its measured errors. These estimates are neither independent statistical errors nor rigorous enclosures, and I do not subtract them to improve a gate.

All 214 recorded histories start at zero, end at the requested target, increase in time and agree with summary endpoints. All recorded densities/pressures are positive and all five fixed-scale conservative budgets meet 1e-10:

| Phase | Smallest recorded rho | Smallest recorded p | Largest absolute normalized budget |
| --- | ---: | ---: | ---: |
| Medium | .9977057 | .09972971 | 5.14e-14 |
| Mean | .9998667 | .9997622 | 2.70e-14 |
| Waves | .9977057 | .09972971 | 7.24e-13 |
| Physics | .08062182 | .02275036 | 2.36e-13 |

Across the full matrix the receipts record **957,006 accepted steps**, **463,020 CFL retries**, zero geometry/state rejections, **1,227,457 accepted-stage HLL fallbacks** and **1,582,625 attempted-stage fallbacks**. These are disclosed features of the actual computation. Recorded histories are finite observations; the source's accepted-closure contract supplies the per-step admissibility policy. This review does not independently rerun intermediate states, face fluxes, conservative sums or divergence operators, or prove positivity/TVD. The prior source review's conservative equal/opposite face exchange, absence of energy/pressure repair, induction/curl recovery coupling, screened normal-equation tolerances and reevaluated Heun analysis still apply to the unchanged 226 source files.

The candidate's bulk gauge, screened projected rate, pressure blend, quadratic field recovery and smooth-extrema A-advection limiter remain deliberate engineering departures. The owner-selected A tradeoff remains disclosed: historical fixed passive-loop error was 3–10% worse and rim potential undershoot 17–36% larger than the historical limiter, neither a registered M1 gate ([M1_FINAL_AI_REVIEW.md:122](M1_FINAL_AI_REVIEW.md#L122)). Fresh raw equality to A is not a new limiter-comparison experiment or an extrema/entropy theorem. The historical prescribed-flow 32-run/16-pair/two-ladder evidence and its source-applicability argument remain the earlier review's evidence; this campaign did not reproduce that ladder with the fresh binary. No paper/AREPO equivalence, general Galilean invariance, deforming-mesh, full3D, gravity, SF or merger acceptance follows.

### 9. Resolved inspection discrepancies; final boundary work remains blocking for acceptance

Two medium/mean observer maps were reserialized after their independent reductions. Their logical records exactly equal the retained reducer inputs, but their current byte hashes differ. Medium's report binds decoded `fresh/medium_runs.json.gz` SHA **`9a722715c3bf56c9ab25d3edd9ef9f3dde2d5645dfa978b4bf3d2db9181228e1`**, versus current observer map **`a657e4d3bcf076c4408d34bfcff609ddcac3ea8c4875c48538a40737181b4fd0`**. Mean's corresponding hashes are **`73cc759927079eb7d3fce39c18ccf7ac3616b2706b5976a89193a958e433f099`** and **`ad40cafe5a7793f98e8703aef32d4497dfd44208a03a9efeddc7dca5a1e95ffe`**. The original bytes are retained and verified, not silently replaced by logical equality in the source hash claim. Final collection must preserve this explicit original/derived link.

Old `fresh/README.md`, incremental-report scope strings and the prior source review contain then-accurate pending/partial statements. Their current full arrays and immutable final checkpoints establish completion; I have not retroactively rewritten historical prose or reviews.

The manual receipt records **seven nonzero exploratory/static inspections** and their resolutions: guessed stage filename; absent external README; guessed top-level diagnostics field; wrong guessed remote artifact prefix; the serialization assumption above; the 216/226 bounded inventory assumption; and the wrong guessed short-wave summary path. Failed script versions are retained. Corrected checks succeeded without changing a scientific value or threshold. None is evidence that the physical method failed. The final CSV and source/Git/hash/JSON inspections succeeded; no new unit-test pass is claimed.

**Required before coordinator-scoped M1 acceptance, still open here:**

1. Complete and independently review actual whole-catalog metadata acquisition, including the four real baseline failures. The assignment reports the original 173 workflows as 169 finished / four failed; I did not treat that changing acquisition as a closed reviewed input.
2. Integrate the reviewed metadata fixture/runtime/collector/portable repairs only after the baseline acquisition boundary, freeze coherent source and perform its real source/import/capability preflight. Run each selected metadata method in its own resource-declared REANA workflow, collect its actual outputs and independently review them. Source approval or synthetic fixture flags cannot replace these executions.
3. Perform a complete immutable scientific collection from the completed fresh campaign, preserving all 214 case/execution/config identities, 238 actual input links, exact original/derived report maps, 99 pairs, all ladders/diagnostics and the short/preflight provenance distinctions. The older physics capture does not establish the repaired collector's lifecycle behavior.
4. Execute actual packaging and copied portable verification, including the original/captured manifests, omitted-large-raw identities, nested historical/source/reviewer closures, command/log/process ownership and final integrated schemas. No full collection/packaging/portable success is inferred here.
5. Close and separately hash the final reviewer boundary, then obtain the separate joint numerical-output/archive review resolving any new findings. The coordinator can consider M1 acceptance only after all required gates and evidence reviews are complete. The final moving3D/gravity/ISM/SF/merger work remains a later validated program.

Accordingly, **scientific-output support is affirmative for these exact files and this declared fixed/rigid 2.5D candidate; final immutable-output-boundary review and every acceptance flag remain false.**
