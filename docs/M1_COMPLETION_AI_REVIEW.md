# Issue #7 continuation: final independent AI review

**The bounded implementation, numerical-evidence, archive and figure review is
complete. Scientific acceptance has not passed.** This is the separate AI
review requested by the user, not human peer review, author confirmation or
paper-equivalence validation. All current full-study executions are finished:
112 original-profile runs, 184 comparator-study runs and 32 prescribed-flow
runs. No execution, archive or figure review remains pending in this scope.
The rejected HLL experiment remains a rejected, partially executed historical
experiment; its 81 completed records are not relabelled as a successful study.

## Final bounded assessment

The reviewed implementation and evidence are suitable for retaining the named
`bulk-frame-signal-v1` engineering comparator and its reproducible measurements.
No unresolved implementation, measurement, archive-integrity or figure-mapping
blocker was found within this reviewed scope after the recorded fixes. This
conclusion does not promote the comparator to the default or accept the full
M1 physical method. The default and historical failures remain intact.

| Reviewed result | Original `paper-global-v2` | `bulk-frame-signal-v1` |
| --- | ---: | ---: |
| Spatial wave gates | 3/8 pass | 3/8 pass |
| Wave boost pairs, both normalizations | 13/32 pass | 31/32 pass |
| Coupled-loop boost pairs | 16/16 pass | 16/16 pass |

All 296 coupled evolutions reach their target times and pass the existing
sampled positivity/periodic-budget checks. The largest recorded normalized
budget residual is `1.683712099e-12`, below `1e-10`. All 32 prescribed-flow
runs, 16 joint-boost pairs and 16 comoving drift gates pass; fixed-grid errors
decrease through N256. The 72 mean-field evolutions preserve the original
profile's 12 diagnostic-only pairs and the two comparators' 12/12 bounded
boost passes each. These successful checks do not cancel failed wave gates.

The unresolved scientific findings remain explicit:

- Five of eight spatial wave ladders fail in each profile. Irregular initial
  LS-curl errors, changing jitter realizations with N and one-degree-of-freedom
  fit uncertainties limit interpretation; no asymptotic or ensemble claim is
  substituted for the observed failures.
- The signal regular N256 standing fixed-grid boost pair fails both field
  normalizations, with magnetic boost L1 `8.10194e-6`; the quarter-time value
  is `4.34685e-14`. Different timestep/rejection counts are observed, while
  root values remain 4 and no HLL fallback occurs. Its cause is unresolved.
  The separate actual-face/common-dt N64 diagnosis is retained with negative
  controls and does not claim exclusive nonlinear causation.
- Physical temporal differences are not second order in this packet; original
  regular standing B is nonmonotone. Frozen C1, the finite same-grid reference,
  cap ratios and aggregate-only timestep records remain explicit. The registered
  temporal protocol requires measurement/reporting, without a numeric time-order
  success gate; none has been invented.
- Coupled-loop comoving drift and magnetic overshoot are finite. Passive
  analytic A/B transport is not an exact coupled-MHD reference, and independent
  divergence operators are not uniformly small or machine zero. No full M1,
  general Galilean invariance, 3D or AREPO-equivalence claim is justified.

## Final archive, figures and documents

The original and comparator compact archives, separate execution/measurement
source maps, immutable execution summaries and corrected summaries are checked.
All 672 original and 1032 comparator raw-file hashes match at both execution
and retained-copy locations. The comparator archive's 18 selected snapshots
include all six initial/quarter/final N256 standing counterexample CSVs.
Its corrected summary matches the independent review across 184 runs, 84 boost
pairs, eight spatial ladders, 12 temporal comparisons and 12 mean-refinement
observations. Reanalysis adds only 16 fit-uncertainty fields/notes to that
packet; every existing value and gate label is unchanged. The original-layer
comparison likewise preserves existing values and failed gates. The prescribed
archive and raw measurements were separately verified earlier in this review.

All four final combined figures reproduce byte for byte from both retained
raw summaries and compact archives, matching the checked-in PNGs. Independent
plot-object checks verify 16 spatial curves, 96 magnetic-only boost points,
16 B/phi temporal curves and six prescribed-flow curves. Profiles, resolutions,
wave/motion/jitter mapping, amplitude/peak normalization, bounds and legends
are correct. The `.02` spatial magnitude bound is explicitly labelled; the
boost figure identifies its magnetic-only scope. The `1e-17` boost and `1e-30`
phi display floors are labelled, with no current values below either floor.
No plotted data are clipped. All four final images were visually inspected.
Previously reviewed wave-only and snapshot images retain their reviewed hashes.

The final results document, README, AGENTS, handoff, roadmap, validation,
backlog and packet README were checked against the measured evidence. They
separate completed execution from failed scientific acceptance, preserve
passive-loop and frozen-C1 scope, and state the exact dimensionless diagnostic
`sqrt(volume/pi)*div(B)/(|B|+1e-12*Bscale)`. Signed mean, RMS and absolute max
remain distinct. The documented limited-face scaled maximum `3.57148e7` and
large loop RMS values match the packet; no values are hidden by a zero or
clipping convention. Historical handoff/increment statements are explicitly
historical. A stale external-reference planning sentence and the unlabeled
spatial bound were corrected during this final review.

The [review evidence directory](../tests/reference/m1_completion/ai_review/)
contains exact commands, source/raw/report/figure hashes and logs.
`candidate_archive_report.json`, `final_figure_report.json` and
`final_review_provenance.json` record the final checks, alongside the earlier
original/archive, loop, wave, temporal, mean-field and prescribed reports.
No new simulation or solver change was made for this final audit. Failed
scientific gates require further prospective work; completing this bounded AI
review is not full M1 scientific acceptance.

## Review chronology — historical checkpoints

The sections below preserve the review sequence and rejected/partial evidence.
**Every earlier statement that execution, evidence, archives or figures are
pending describes that historical checkpoint and is superseded by the final
assessment above.** Scientific limitations and failed gates remain current
unless the final assessment explicitly says otherwise. Historical probe and
partial-report files are preserved unchanged.

### Historical checkpoint: Rejected first completion

The first experiment used an HLL fan-average state to complete the magnetic
field and normal EMF for A, retaining HLLD conservative and tangential
induction fluxes. It removed the known N64 standing-wave boost failure, but
the independent review found a different discontinuity: the HLL fan average
does not tend to the upstream state as an outer wave speed approaches zero.

For the archived valid fixture with `rho=p=1`, `gamma=5/3`,
`B_L=(.5,.3,.1)`, `B_R=(.5,-.4,.2)`, tangential velocities `(.2,.1)` and
`(-.2,.05)`, and normal velocity `cf=1.377325104398016`, a `1e-15` speed
perturbation changes a component of the complete A source by about `.582`.
The conservative flux changes only at roundoff. A joint boost `(100,-1,.8)`
also triggers this jump through subtraction roundoff. The two standalone
counterexamples and the exact rejected core source are archived.

That design is rejected and removed from the supported CLI profiles. Its
partial physical study and the successful bounded N64 observation must not
be presented as acceptance of the design.

### Historical checkpoint: Revised signal-weighted completion

The separately registered `bulk-frame-signal-v1` uses
`U_A=(SR U_L-SL U_R)/(SR-SL)` inside the outer wave fan and the upstream state
outside. The interior weights are positive and sum to one. With common
normal B, this is a convex mixture of admissible conservative states;
internal energy is concave in those states, so admissibility is preserved
in exact arithmetic. The code still checks it in floating point.

The state tends to `U_L` as `SL` approaches zero and to `U_R` as `SR`
approaches zero. Normal reversal exchanges the inputs and weights. Joint
boosts leave face-rest inputs invariant, while the added laboratory
`boost cross B_A` cancels in the complete A source. This establishes these
algebraic properties of the completion, not long-time physical accuracy.
The inherited HLLD/fallback validity switches have not been proved globally
continuous. The default `paper-global-v2` and historical `bulk-frame-v1`
remain unchanged.

Independent repetitions of the original boundary and boost counterexamples
pass for the revised implementation. A separate deterministic 10,000-face
probe gives maximum complete-source reversal error `3.927414e-15` and joint
boost error `5.884182e-15`; conservative and induction fluxes remain
bit-identical to the historical routine for those identical input states.

### Historical checkpoint: Actual standing-wave diagnosis

An independent read-only face probe reconstructs the actual N64 regular
standing-wave inputs using the production raw/limited gradients, predictor and
auxiliary sampler. Its ordinary CFL base replay at t=.25 matches all 4096
archived primitive states exactly. At the initial state, an actual face lies on
`SAL=0` with `Bn=1`: a one-bit normal-velocity change alters the historical
complete source by `2.360845816e-5`, while the gas flux changes by
`2.220446049e-16`. The signal completion changes by `2.428613e-17`.

A short, explicitly separate common-dt (`1e-4`) diagnostic finds an actual
base/boost pair at t=.0001 whose face 461 has `SAL=0` versus
`-2.220446049e-16`. Its complete historical source differs by `1.824959594e-5`
while the transformed conservative flux differs by `2.220446049e-15`; signal
completion on the same inputs differs by `5.828670879e-16`. After two steps,
the historical pair's maximum B-component difference is `7.325292262e-9`,
versus `2.775557562e-17` for the signal-profile control. The compact actual-face
fixture and full diagnostic log are archived.

The negative controls matter: initial direct reversal/boost tests and the
separately initialized boosted pair show only roundoff source differences;
one `1e-6` step gives exactly zero B-pair difference for both profiles; the
quarter-period face scan has only roundoff perturbation sensitivity. This
identifies a roundoff-sensitive stationary rotational-wave completion in the
actual benchmark, and a controlled change removes that sensitivity. It does
not trace the original CFL trajectory's first branch or establish exclusive
nonlinear causation of the historical t=1 failure.

### Historical checkpoint: Transport and evidence handling

The shared donor/face-derivative and divergence refactors preserve the
historical arithmetic order. The new prescribed-flow driver correctly uses
the constant-velocity planar reduction with `u=v`, zero mean B, and
`Ax=Ay=phi=0`. It evolves no gas state and makes no fluid-energy-budget claim.
Its comoving discrete preservation test is separate from coupled-MHD physics.

The review exposed two measurement defects: a missing finest-resolution
error could be substituted by zero, and equally truncated paired snapshots
could pass covariance checks. The corrected code rejects missing metrics
and checks complete cell counts, unit-domain volume and exact output times.

Archive handling now retains original execution and corrected measurement
provenance separately. The review independently exercised a valid reanalyzed
archive, equality of raw and archived reports, rejection of a modified raw
report, and rejection of an unverified plain-summary file shadowing a
verified compressed archive. Plotting excludes failed early-time states
from `t=1` spatial curves and labels failed/missing resolutions and display
floors. The prescribed-flow and bounded N64 snapshot figures have been inspected;
full-packet coupled-MHD figures remain pending.

The full prescribed-flow archive now independently verifies all 32 raw run
hashes, original and corrected provenance, archived source bytes, complete
snapshots, analytic A/B norms and energy/A-integral/extrema. All 16 comoving
initial/final A/B arrays and all 16 boost-pair A/B/volume arrays are bit-identical;
periodic position correspondence also passes. Fixed-grid normalized A L1 errors
at N256 are `0.00059908933093` (regular) and `0.00063110118000` (jittered),
decreasing across N32/64/128/256. Adjacent nonsmooth-loop orders are about
1.40–1.46. This verifies the registered prescribed-flow gates, not coupled-MHD
physics or second-order convergence.

Seven focused Rust tests, thirteen measurement tests and two archive tests
pass in the reviewed revisions. The independent probe logs support this
bounded implementation assessment. The remaining full studies may still
fail convergence, positivity, budget or boost gates; no such result is
preclassified as successful here. Neither issue #7 nor full M1 acceptance
follows from this preliminary review.

### Historical checkpoint: Bounded N64 snapshot-figure review

The separate review checks `plot_m1_snapshots.py`, its two rendered figures,
`snapshot_provenance.json`, and the snapshot descriptions in
`M1_COMPLETION_RESULTS.md`. All input-archive, script and figure hashes match.
Rerendering into a fresh directory reproduces both PNGs and their provenance
byte for byte. The independent `snapshot_check.py` verifies all 4096 persistent
IDs per input, exact output time, finite positive volumes, unit total volume
and the regular periodic cell-centre mapping. Rendering x across columns and
y up rows is consistent with those coordinates.

One reporting defect was found and fixed: the original shared colour ceiling
of `1.1` silently clipped 132 prescribed-flow and 112 coupled fixed-grid cells.
Their actual maxima are `1.174804415` and `1.165278478` in units of
`B0=0.001/sqrt(4*pi)`. The corrected common ceiling is `1.2`, with a guard
against clipping future inputs, and the text now explicitly reports these
overshoots. Comoving preservation is exactly claimed only for prescribed flow;
the coupled comoving field differs from its initial field by a maximum
cellwise vector magnitude of `1.05815e-7` in this N64 snapshot.

For the standing wave, parallel velocity one gives analytic phase `2*pi*x`;
the displayed `By=.1*sin(2*pi*x)` and `Bz=.1*cos(2*pi*x)` references have the
correct signs. The y-mean solution residual is about `±0.00369713` at t=1.
It includes finite-timestep effects and is labelled solution error. The
separate caption uses the maximum cellwise three-component vector boost norm,
independently recovered as `9.923383415654292e-13`, matching the numeric packet.
It is not a maximum of y-averaged curves or a scalar component maximum.

The final figures were visually inspected and show the data without clipping
or misleading scope. This is a bounded figure/provenance review, not completion
of the still-pending full coupled spatial/temporal evidence review.

### Historical checkpoint: Interim travelling fixed-grid ladder review

This limited review covers the twelve completed base evolutions with travelling
parallel velocity zero, fixed meshes, profiles `paper-global-v2` and
`bulk-frame-signal-v1`, jitter 0/.15 and N64/128/256. The parent execution
packets were still running at inspection. No evolving root report is archived
as a completed packet: the review retains only the inspected run configuration,
command, counters, checked input hashes and independent measurements in
`travelling_ladder_report.json`. The corresponding script imports no production
measurement code and runs no simulation.

All 36 initial/quarter/final snapshots have complete ordered IDs, finite values,
positive volumes summing to the unit domain and exact times 0/.25/1. Fixed-cell
centres and volumes are bit-identical between stages. The configured profiles,
EOS, mean field, mesh velocity and boost match their labels. Frozen source and
binary hashes match execution metadata. Independent volume-weighted vector and
component L1/L2/max errors agree with the run records; the wave is evaluated at
the actual irregular cell centroids with phase `2*pi*(x+t)`. Initial analytic A
agrees within `3.47e-18`, and velocity agrees to roundoff. There is no identified
reference, pairing, geometry or norm mismatch that explains the low order.

| Grid/profile | Final B L1 order | Residual slope SE | Adjacent orders |
| --- | ---: | ---: | --- |
| Regular, original | 2.01643202583 | .00827019504 | 2.03076, 2.00211 |
| Regular, signal | 2.01643202579 | .00827019503 | 2.03076, 2.00211 |
| Jitter .15, original | 1.14065861013 | .28315228702 | 1.63109, .65022 |
| Jitter .15, signal | 1.17846422468 | .26774201789 | 1.64221, .71472 |

Both completed irregular ladders fail the registered order threshold `p>=1.8`.
The initial reconstructed irregular B already has L1 errors
`4.369441632e-4`, `1.431916860e-4`, `1.060010817e-4`, fitting order
`1.021684972` (residual SE `.339375858`; adjacent orders `1.60950`, `.43387`).
The regular initial field fits order `1.999674095`. Thus the irregular slowdown
predates all evolution, Riemann completion and HLL fallback decisions.

At irregular N256 the initial transverse radial error has L1 `1.002493523e-5`,
close to the regular radial error `1.003957839e-5`; the additional transverse
quadrature error is `9.058267052e-5` and normal-field error is
`4.131836166e-5`. Radial/quadrature here mean the projections of `(error By,
error Bz)` onto `(sin phase, cos phase)` and `(cos phase, -sin phase)`.
The latter quadrature and normal-field errors are absent to roundoff on the
regular mesh. This is consistent with asymmetric linear-fit derivative error:
the source initializes analytic centroid A and obtains B from its raw
face-area-weighted neighbour least-squares curl. The neighbour condition remains
about 4.07 at N256, with no geometry/state rejection or auxiliary coarsening.
Initial raw-LS divB RMS is `.0244894`, versus about `.0226407` after evolution;
this independent divergence operator is not assumed to annihilate the curl.

These observations identify an initialization/reconstruction contribution, not
exclusive nonlinear causation of the final error. The deterministic jitter
uses `k=i+N*j`, so its mesh realization changes with resolution. Three-point
residual slope SE has only one residual degree of freedom and is neither an
ensemble uncertainty nor a systematic-error bound. The interim evidence does
not establish an asymptotic order, justify changing a gate, or complete the
pending full coupled spatial/temporal review.

### Historical checkpoint: Completed original-profile spatial wave matrix

The bounded per-run review now covers all **64** completed `paper-global-v2`
spatial Alfvén evolutions, **192** initial/quarter/final snapshots and **32**
boost pairs. The containing execution packet remains active on other cases;
this does not certify unfinished root provenance. `wave_matrix_check.py` and
`wave_metadata_check.py` independently verify the inspected frozen source and
binary hashes, every recorded raw-file hash, names/configurations/commands,
complete persistent IDs, exact times, periodic rigid geometry, analytic
physical norms, boost transforms, output positivity and conservative budgets.
The report preserves the checked per-run inputs separately.

| Wave | Jitter | Mesh | B order over N64/128/256 | N256 B L1/.1 | Spatial gate | Boost passes / 4 |
| --- | ---: | --- | ---: | ---: | --- | ---: |
| Travelling | 0 | Fixed | 2.016432 | .000242756 | Pass | 4 |
| Travelling | 0 | Comoving | 2.016432 | .000242756 | Pass | 4 |
| Travelling | .15 | Fixed | 1.140659 | .001018392 | Fail: order | 0 |
| Travelling | .15 | Comoving | 1.140659 | .001018392 | Fail: order | 0 |
| Standing | 0 | Fixed | -.551693 | .035287124 | Fail: order and magnitude | 1 |
| Standing | 0 | Comoving | 2.016432 | .000242756 | Pass | 4 |
| Standing | .15 | Fixed | .914212 | .004820197 | Fail: order | 0 |
| Standing | .15 | Comoving | 1.140659 | .001018392 | Fail: order | 0 |

Thus **3/8** spatial gates pass, and **13/32** boost pairs pass under both
reported normalizations; **19/32** fail under both, with no mixed classification.
All 32 pairs have valid periodic geometry/time/volume correspondence. The
regular fixed standing-wave magnetic errors at N32/64/128/256 are
`.00443943`, `.00164234`, `.00447519`, `.00352871`; its fitted negative order
must not be presented as convergence. Its residual slope SE is `.516440`;
the irregular fixed standing-wave fit has residual SE `.392927`. Full values,
component/vector norms and each normalization's verdict are retained in the
review report. At parallel velocity zero, the declared fixed and bulk-comoving
mesh velocities are both zero, so those two labelled ladders are duplicate
numerical configurations, not independent mesh-motion evidence.

All 64 runs pass the sampled positivity and budget checks. The minimum recorded
cell density and pressure are `.8454981` and `.0656057`. The largest normalized
budget in the original histories is `1.68372e-12`; independently summing the raw
cell states with `math.fsum` gives at most `1.17752e-15`. Their
maximum reduction-order difference is `1.68391e-12`, below the `1e-10` budget
gate. This verifies the recorded output times; it does not invent unavailable
per-step diagnostic histories.

The earlier irregular initialization/curl findings remain applicable. They do
not explain away the additional regular fixed standing-wave evolution failure.
At the original-profile review checkpoint the signal matrix still had two runs
pending; its completed assessment follows below. All coupled-loop/temporal
evidence, final archives and full-study figures remain outside these bounded
wave reviews.

### Historical checkpoint: Completed signal-profile spatial wave matrix

The same independent checks now cover all **64** completed
`bulk-frame-signal-v1` spatial Alfvén evolutions, **192** snapshots and **32**
boost pairs. Frozen source/binary and per-run raw hashes, command/configuration
matching, physical norms, thermodynamic recovery, rigid geometry, boost
transforms, output positivity and budgets all verify. This remains a per-run
wave review; the containing loop/temporal execution packet is still active.

| Wave | Jitter | Mesh | B order over N64/128/256 | N256 B L1/.1 | Spatial gate | Boost passes / 4 |
| --- | ---: | --- | ---: | ---: | --- | ---: |
| Travelling | 0 | Fixed | 2.016432 | .000242756 | Pass | 4 |
| Travelling | 0 | Comoving | 2.016432 | .000242756 | Pass | 4 |
| Travelling | .15 | Fixed | 1.178464 | .000991513 | Fail: order | 4 |
| Travelling | .15 | Comoving | 1.178464 | .000991513 | Fail: order | 4 |
| Standing | 0 | Fixed | 1.580708 | .001936986 | Fail: order | 3 |
| Standing | 0 | Comoving | 2.016432 | .000242756 | Pass | 4 |
| Standing | .15 | Fixed | 1.248904 | .002381998 | Fail: order | 4 |
| Standing | .15 | Comoving | 1.178464 | .000991513 | Fail: order | 4 |

Only **3/8** spatial gates pass. Every finest-error magnitude is below `.02`,
but five ladders miss order `1.8`. The regular fixed standing-wave order
improves from the original negative value to `1.580707550` (residual SE
`.009095928`; adjacent orders `1.564953`, `1.596462`) and remains a failure.
The irregular fixed standing-wave order is `1.248903606` (residual SE
`.224760713`). The earlier initialization diagnostics and changing-jitter/
non-ensemble uncertainty caveats remain applicable.

**31/32** boost pairs pass under both reported normalizations. The regular
fixed standing-wave N256 pair fails **both**; there are no mixed verdicts.
Its t=1 vector magnetic and transformed-velocity L1 differences are
`8.101939153e-6` and `8.521586692e-6`. Wave-amplitude normalization gives
`8.101939153e-5` and `8.521586692e-5`; mean-field/initial-speed normalization
gives `8.101939153e-6` and `8.479295678e-6`, all well above `1e-8`.
Density, pressure and energy relative L1 discrepancies also exceed the gate.
The maximum magnetic vector difference is `.0005880464544`.

The failed pair is correctly paired: final coordinate discrepancy is
`2.13163e-14`, volume differences are zero, and positivity/budgets pass.
Its magnetic boost L1 is only `4.34685e-14` at t=.25, so the larger separation
appears later. Neither run uses HLL fallback, state/geometry rejection or
auxiliary coarsening; both auxiliary-root sets are `{4}`. Accepted steps differ
(`10308`/`10331`, with `9726`/`9772` CFL rejections). Saved root sequences
have lengths `10308`/`10331` and contain only `4`, so their equality fails
through different lengths, not an observed root-size transition. No new
evolution probe was run and the remaining cause is not isolated. The successful bounded N64 result must not be generalized to all
resolutions or to general coupled Galilean invariance.

**Unresolved follow-up:** identify the onset and amplification of this N256
late-time boost discrepancy under explicitly controlled timestep histories.
The quarter-time control, valid geometry, constant root sizes and absent HLL
fallback narrow the recorded observations but do not assign an exclusive
cause. `bulk-frame-signal-v1` remains a bounded engineering comparator.

All 64 signal runs pass sampled positivity/budgets. Minimum recorded density
and pressure are `.9760520` and `.0984578`. The largest original-history
normalized budget is `1.68352e-12`; independent raw-state summation gives at most
`1.17752e-15`, with maximum reduction-order difference `1.68372e-12`.
All 32 boost pairs pass geometry/time/volume correspondence. These findings do
not establish full issue #7 or M1 scientific acceptance; loop/temporal evidence,
final archives and full-study figures remain pending.

### Historical checkpoint: Completed mean-field comparison matrix

The bounded review now covers all **72** completed `mean_*` evolutions in the
signal-study checkout: three named profiles, regular/jittered meshes, N8/16/32/64
at dt cap `.00025`, and N16 caps `.001`/`.0005`, each with a joint fluid/grid
boost pair at t=.02. The independent checker verifies frozen source/binary and
all per-run raw hashes, configuration and actual command arguments, complete
initial/final snapshots, the analytic initial constructor, prescribed rigid
geometry, EOS recovery and recorded dimensional/dimensionless divergence norms.
Final physical fields are compared after velocity and total-energy boost
transforms; no analytic final A or gauge-independent A error is assumed.

All **72/72** runs pass sampled positivity/budgets. All **36/36** pairs have
valid periodic geometry/time/volume correspondence and matching complete
auxiliary-root sequences. Minimum recorded density and pressure are
`.9998654204` and `.9997529794`. The largest original-history normalized budget
is `2.75124e-14`; independent raw-state summation gives at most `1.87751e-16`.

| Profile | Registered boost classification | Worst transformed physical component max |
| --- | --- | ---: |
| `paper-global-v2` | 12 diagnostic pairs; no retrospective gate | `3.937114025e-5` |
| `bulk-frame-v1` | 12/12 pass | `9.547918012e-15` |
| `bulk-frame-signal-v1` | 12/12 pass | `9.325873407e-15` |

The two comparator profiles satisfy the registered componentwise `1e-9` gate,
matching-root and positivity/budget requirements. Their magnetic vector boost
L1 residuals lie around `2.4e-17`–`1.8e-16`. All successive refinement orders
are retained in the numeric report; orders inferred from these roundoff-scale
values are not meaningful physical-accuracy estimates.

For `paper-global-v2`, regular-grid magnetic boost L1 decreases from
`8.239733227e-6` at N8 to `5.338044031e-7` at N64, with successive observed
orders `1.061764`, `1.403488`, `1.482962`. The jittered residual decreases from
`8.565783938e-6` to `1.192545165e-6`, with orders `1.116290`, `1.037706`,
`.690546`. At N16 the dt-cap ladder changes the residual very little: it remains
about `3.9472e-6` (regular) and `3.95e-6` (jittered). Every cap is reached,
with 20/40/80 accepted steps for `.001`/`.0005`/`.00025` and no CFL rejection.
These are registered boost-residual refinement observations, not exact
physical-solution convergence or retrospective success/failure gates. They are
also distinct from the still-pending physical wave temporal packet.

This short-time N<=64 mean-field result does not supersede the signal profile's
failed N256 standing-wave boost comparison at t=1, establish general Galilean
invariance or complete M1. The exact inspected per-run evidence is retained in
`mean_matrix_report.json`; no unfinished global execution provenance is
certified. Coupled loops, physical temporal comparisons, final archives and
full-study figures remain pending.

### Historical checkpoint: Reviewed complete-wave figures

The limited figure review covers `plot_m1_wave_review.py`,
`reviewed_wave_convergence.png`, `reviewed_wave_boost.png`, their provenance and
the corresponding additions to `M1_COMPLETION_RESULTS.md`. The two immutable
64-run input reports retain their previously reviewed hashes; neither reports
nor solver sources were changed for this review.

The independent figure checker inspects the rendered plot objects as well as
the numeric inputs. All 16 spatial curves map to the correct profile, wave,
jitter and motion, use N32/64/128/256 and magnetic vector L1 divided by `.1`,
and display the correct fitted order and gate label. The original negative
standing-wave order and all inadequate orders remain visible. The `.02` line
is explicitly the finest-resolution magnitude bound; both profiles' 3/8
spatial verdict totals agree with the reviewed reports. No curve is clipped.

Both 8-by-4 heat maps have the correct row/resolution mapping, raw-value
annotations and magnetic vector boost L1/.1 normalization. Red boxes apply
only to the magnetic `1e-8` threshold (19 original cells, one signal cell).
The panel titles separately count full physical-field verdicts under both
normalizations (13/32 and 31/32); the caption states the distinction. Both
panels share log colour limits `1e-16` to `.1`. Their actual ranges are
`5.89585e-14`–`.0572693` and `1.33443e-14`–`8.10194e-5`, so no data are clipped;
the lower display floor is labelled even though these inputs exceed it.

The final figures were visually inspected. Rendering into a fresh directory
reproduces both PNGs and `wave_review_plot_provenance.json` byte for byte.
Exact figure/script/input hashes, dependency versions and the independent
artist checks are archived in `wave_figure_review_provenance.json` and its
probe/log. The documents correctly identify the profiles and complete-wave
scope, without claiming completion of the active loop/temporal packet or full
M1 acceptance. No outstanding defect was found in this bounded figure review.

### Historical checkpoint: Completed physical temporal packet

This bounded AI audit covers all 16 `temporal_*` evolutions in each frozen
original and signal checkout: N64, fixed periodic unit-square meshes, regular
and jitter `.15`, travelling and standing waves, caps `.0004`, `.0002`,
`.0001` and `.000025`, through t=1. All 32 evolutions and 96 complete snapshots
at t=0, `.25`, 1 are verified against per-run raw hashes, commands, manifest
configuration, frozen source and binary hashes. The containing execution
packets are still running; their observed metadata hashes are recorded only
as inspected bytes, not certified completed provenance.

Each of the 24 comparisons uses the same-profile, same-grid `.000025`
reference. Initial snapshots are bitwise identical within each ladder;
persistent IDs, times, centroids and volumes are exact matches at both output
times. Analytic initial A/velocity, sampled physical errors, EOS recovery,
positivity, conservative budgets and reported divergence RMS are checked
independently. All 32 pass the existing sampled positivity/budget requirement:
minimum rho `.9760567492`, minimum p `.09726765274`, maximum recorded normalized
budget `7.78857e-14` and independently reduced budget `3.10862e-15`.

All caps are reached, with zero CFL/state/geometry rejections, root value 4
throughout and no auxiliary coarsening. The following accepted aggregate
statistics are identical across profiles/waves/jitters for each cap:

| Cap | Steps | Minimum accepted dt | Maximum accepted dt |
| --- | ---: | ---: | ---: |
| `.0004` | 2501 | `4.796163466e-14` | `.0004` |
| `.0002` | 5001 | `8.260059303e-14` | `.0002` |
| `.0001` | 10002 | `1.121325255e-14` | `.0001` |
| `.000025` | 40001 | `2.345346140e-14` | `.000025` |

A clock-only repeated-cap calculation landing at `.25` and 1 reproduces all
three statistics exactly, including the tiny residual steps. This supports
cap-limited integration with output-time truncation. There is no saved
per-step dt trace, so the aggregate agreement does not reconstruct or certify
every accepted dt; the solver still has adaptive CFL bounds and retry logic.
The tiny minimum is not evidence of a severe CFL reduction in this packet.

Final vector-B L1 differences to the same-grid reference and the two adjacent
cap-ratio slopes are:

| Profile | Wave | Jitter | B L1 at caps `.0004`, `.0002`, `.0001` | Adjacent slopes |
| --- | --- | ---: | --- | --- |
| Original | travelling | 0.0 | `2.925950e-05, 1.381605e-05, 5.957674e-06` | `1.082560, 1.213524` |
| Original | travelling | 0.15 | `2.898124e-05, 1.367258e-05, 5.891440e-06` | `1.083834, 1.214594` |
| Original | standing | 0.0 | `1.453722e-04, 1.775812e-04, 1.623519e-04` | `-0.288728, 0.129355` |
| Original | standing | 0.15 | `1.869026e-04, 1.379825e-04, 8.069927e-05` | `0.437801, 0.773858` |
| Signal | travelling | 0.0 | `2.925950e-05, 1.381605e-05, 5.957674e-06` | `1.082560, 1.213524` |
| Signal | travelling | 0.15 | `2.791829e-05, 1.317613e-05, 5.678565e-06` | `1.083284, 1.214329` |
| Signal | standing | 0.0 | `9.811779e-06, 4.752246e-06, 2.084934e-06` | `1.045905, 1.188608` |
| Signal | standing | 0.15 | `1.029610e-05, 6.134510e-06, 3.103276e-06` | `0.747078, 0.983156` |

The original regular standing-wave magnetic difference is nonmonotone; its
negative coarse slope is retained. The signal comparator improves this N64
comparison, but its irregular standing-wave slopes remain below one and this
result does not override the failed N256 boost comparison. All component
L1/L2/max values and quarter-time comparisons are retained in the report.

Total A and phi are measured separately in each profile's own gauge. Their
final vector-A/phi L1 at the finest measured cap `.0001`, and adjacent slopes,
are:

| Profile | Wave | Jitter | A L1 / phi L1 at `.0001` | A slopes | phi slopes |
| --- | --- | ---: | --- | --- | --- |
| Original | travelling | 0.0 | `8.211156e-07 / 1.557208e-08` | `1.086846, 1.216102` | `1.099642, 1.222454` |
| Original | travelling | 0.15 | `8.740250e-07 / 1.592489e-08` | `1.085378, 1.215369` | `1.099674, 1.222461` |
| Original | standing | 0.0 | `3.260173e-06 / 4.241489e-07` | `0.195201, 0.402048` | `0.045225, 0.187021` |
| Original | standing | 0.15 | `2.418014e-06 / 4.751257e-07` | `0.684614, 0.786590` | `0.571339, 0.738714` |
| Signal | travelling | 0.0 | `8.211168e-07 / 1.559024e-08` | `1.086846, 1.216102` | `1.099649, 1.222456` |
| Signal | travelling | 0.15 | `8.424574e-07 / 1.594898e-08` | `1.084771, 1.215084` | `1.099839, 1.222540` |
| Signal | standing | 0.0 | `6.264621e-07 / 6.149104e-08` | `1.052122, 1.231732` | `1.037406, 1.215801` |
| Signal | standing | 0.15 | `6.245831e-07 / 6.117402e-08` | `1.088507, 1.210380` | `1.085403, 1.212749` |

These are finite-reference differences, not exact time-discretization errors.
For illustration, a leading error `C*dt` compared with nonzero
`dt_ref=.000025` gives adjacent apparent slopes `1.099536`, `1.222392` for
these caps. A slope above one therefore does not establish second-order time
accuracy. The frozen-C1 prescription is unchanged: endpoint cleaning retains
initial div(A) and sound speed. These coupled physical measurements neither
replace the separate gauge-mode test nor identify an exclusive source of the
observed physical-B error.

The regular travelling Bx differences are about `1.5e-16` in both profiles;
regular standing signal Bx differences are about `2e-15`. Their stored
positive/negative cap-ratio slopes describe roundoff, not accuracy order.
The original regular standing Bx difference is much larger, about
`4.5e-5`–`6.6e-5`, and is not labelled roundoff. Reduced-A comparisons are also
archived; their vector norms differ from total-A norms by at most `1.02e-20`
in these unboosted same-profile ladders.

Regular meshes have no HLL fallbacks. Jittered counts for caps `.0004`,
`.0002`, `.0001`, `.000025` are `[245,480,964,3889]` (original travelling),
`[910,2281,4131,15537]` (original standing), `[229,476,977,3982]` (signal
travelling), and `[66,129,253,1000]` (signal standing). Accepted and attempted
counts agree; these are face evaluations, not rejected timesteps, and do not
by themselves establish the cause of any temporal residual.

The temporal requirement was checked directly against
`M1_WAVE_LOOP_PLAN.md` (wave/loop protocol), `M1_COMPLETION_PLAN.md`
(frozen C1 and execution/assessment), and `packet-v2.json`'s Alfvén temporal
block, with the inherited `M0_BENCHMARK_PACKET.md` and
`M0_ENGINEERING_DECISIONS.md` contract also checked. The explicit order>=1.8
gate applies to the spatial N ladder. The temporal block specifies N64,
these three caps, the `.000025` reference, and separate B/A/phi reporting;
it supplies no numeric physical temporal-order gate. This conclusion does
not rely on the runner's absence of a pass label. The reporting requirements
are fulfilled, while nonmonotone/sublinear magnetic behavior and lack of
demonstrated second-order physical time accuracy remain limitations.
No new temporal gate is introduced, and all inadequate, negative and
roundoff-scale slopes remain explicit. Exact per-run evidence,
source/config/raw hashes, norms and timing counters are in
`temporal_matrix_report.json`, with the independent checker, log and
`temporal_matrix_review_provenance.json`. Coupled loops, final archives and
remaining full-study figures are still outside this review; full M1 is not
accepted.

### Historical checkpoint: Partial coupled-loop matrix review

The bounded loop audit currently covers 60 completed evolutions and 180
snapshots at t=0, `.25`, 1: 30 evolutions in each frozen profile. Both N256
jittered comoving base/boost pairs are still absent from the inspected completed
records (four runs total), so this is explicitly an incomplete matrix.
`loop_partial_report.json` preserves those missing names and observed statuses;
no complete-loop or global-packet certificate is issued.

All reviewed source/binary/raw hashes, commands/configurations, initial loop
states, output times, persistent IDs, periodic rigid geometry and EOS recovery
agree. The independent checker verifies all passive Az/B L1/L2/max comparisons,
including exclusions at the analytic cusp/edge, and magnetic-energy histories.
It also independently reduces dimensional and dimensionless signed mean,
RMS and maximum norms from all three CSV divergence-operator columns, plus
div(A)/phi. This is a check of reported operator values and reductions, not a
new reconstruction of the face stencils. Signed-mean comparison accounts for
cancellation when scaled values are large.

All 60 reviewed evolutions pass the existing sampled positivity/conservation
gate: minimum rho `.9999999729`, minimum p `.9999999561`, maximum recorded
normalized budget `1.47157e-13` and independently reduced budget `2.42029e-14`.
All 30 available boost pairs pass the registered magnetic vector L1 divided by
`.001/sqrt(4*pi)` threshold `.001`, with valid geometry/time pairing. The
largest normalized residual is `1.294792e-9` in the original jittered fixed
N256 pair; its quarter-time raw B L1 is `2.909249e-12`, final `3.652541e-13`.
This passing result is not labelled bitwise invariance or roundoff-only.

Two reviewed pairs have unequal auxiliary-root sequence lengths: original
jittered fixed N256 (20164/20165 steps) and signal regular comoving N256
(22259/22300). Every root entry is 4; no root-size transition or coarsening
occurs. Their step/CFL-rejection counts differ; matching roots are diagnostic,
not an added coupled-loop gate. No reviewed run has a state/geometry rejection
or HLL fallback. Existing CFL rejection counts remain in the report.

The complete fixed-grid passive-reference ladders decrease with N in both
profiles and jitter families. The following N256 values are diagnostics of
finite-field coupled MHD, not exact coupled-solution error gates:

| Profile | Jitter | Passive Az L1 / initial peak | Passive B L1 / amplitude | Magnetic energy / initial |
| --- | ---: | ---: | ---: | ---: |
| Original | 0 | `.000581300` | `.0203112` | `.9826304` |
| Original | .15 | `.000618252` | `.0209668` | `.9848717` |
| Signal | 0 | `.000591538` | `.0208562` | `.9802992` |
| Signal | .15 | `.000622909` | `.0211925` | `.9834567` |

Fixed passive-A adjacent slopes are about 1.40–1.47. No second-order
requirement or prescribed-flow A threshold is imported into this nonsmooth
coupled test. Comoving discrete fields do change: regular N256 vector-B
maximum initial/final difference is about `3.99132e-7` in either profile, and
magnetic energy ratios are about `.99997067`. Finite magnetic feedback remains
present; exact comoving preservation is a result of the separate prescribed
packet, not these coupled evolutions. Final magnetic maxima also reach
`|B|/amplitude=1.212006` (original) and `1.210086` (signal). The N64 snapshot
figure's guarded ceiling of 1.2 must not silently clip these if future figures
use the larger-resolution inputs.

Independent divergence diagnostics are not uniformly small. Across reviewed
final snapshots, dimensional RMS maxima for raw LS, arithmetic-face and
limited-face operators are about `.000171364`, `.000246583`, `.000363723`.
The fixed normalization `r*div(B)/(|B|+1e-12*Bscale)` can be very large where
local B is zero or tiny: initial RMS maxima are `2.02537e9`, `2.54234e9`,
`1.51164e9` respectively. These finite values and the dimensional counterparts
are retained; they are not replaced by zero or used to claim machine-zero
divergence. No coupled-loop divergence success threshold is present in the
registered packet.

The partial review and exact inspected hashes are archived with
`loop_matrix_check.py`, `loop_partial_check.log` and
`loop_partial_review_provenance.json`. The checker supports
`--require-complete`, which refuses a complete-matrix output while any run is
unfinished. The final four loop evolutions, final whole-packet provenance,
compact archives and remaining figures still require review. Full M1 is not
accepted.

### Historical checkpoint: Completed original packet and archive

The original `paper-global-v2` packet has all 112 runs completed: 64 spatial
waves, 32 coupled loops and 16 physical temporal runs. This final original-only
review reuses the earlier independent numerical measurements after exact
raw/source/configuration matching, and independently measures the last two
N256 jittered comoving loop evolutions. It does not certify the still-unfinished
signal packet or the combined final figures.

The completed original loop matrix has 32/32 sampled positive/conservative
runs and 16/16 passing magnetic boost pairs. The last pair has magnetic vector
boost L1/amplitude `1.002710773e-13`, final periodic position difference
`1.38112e-13` and identical volumes. Both runs have 19178 accepted steps,
8214 CFL rejections, root value 4 throughout, no coarsening, no state/geometry
rejections and no HLL fallback. The base N256 jittered comoving passive Az
L1/peak is `1.59015e-7`, passive B L1/amplitude `.00375810` and magnetic-energy
ratio `.999970327`. Maximum initial/final B drift is `4.14495e-7`; finite
magnetic feedback is retained. The final adjacent passive-A slope is `.853232`,
a reported coupled passive-reference observation without a prescribed-flow
accuracy gate. The original loop matrix's worst normalized boost residual
remains `1.294792e-9`, below the registered `.001` threshold.

For `tests/reference/m1_completion/original`, the independent archive check
verifies the exact 20-file manifest inventory, every archived file hash,
execution and measurement source tar members against their distinct source
maps, and the frozen execution binary hash. It verifies all 672 per-run raw
file hashes in both the original `/tmp` execution location and the retained
`results/issue7_completion_20261106/original` copy. The 12 selected compressed
snapshot files also match the raw hashes. Execution `manifest/runs/summary`
hashes, immutable `execution_summary`, corrected `summary`, measurement input
hashes and both provenance files form separate checked layers; neither source
revision nor the original summary is relabelled as the later measurement code.

All 112 run records map to the independently reviewed wave, temporal and loop
reports. The corrected archive's 48 boost pairs, eight spatial ladders and
12 temporal comparisons agree with those reports across 8760 numeric checks;
the largest independent reduction/fit difference is `1.15e-14` in a fitted
spatial slope. Execution-to-measurement changes are exactly 88 metadata
additions/wording edits: eight residual-fit standard errors and their scope
notes, four empty diagnostic series for the new profile name, 32 Alfvén
normalization clarification notes, and 12 sets of cap-reached/actual-max-dt
notes. Every existing numeric result and gate label is unchanged.

The archive therefore retains the original scientific limitations: only 3/8
spatial wave ladders pass; 13/32 wave boost pairs pass both normalizations and
19/32 fail both. Nonmonotone/sublinear physical temporal behavior remains
reported without inventing a temporal success gate. Archive integrity is not
scientific acceptance of those failed results.

Exact reuse links, source/raw/archive hashes and commands are retained in
`original_loop_report.json`, `original_loop_review_provenance.json`,
`original_archive_report.json` and `original_archive_review_provenance.json`,
with independent checker sources and logs. The earlier partial loop report
remains immutable. The signal profile's final two loop evolutions and final
archive, combined figures and overall issue assessment remain pending; full
M1 is not accepted.

### Historical checkpoint: Completed coupled-loop matrix

The full loop checker has now run with `--require-complete` against both
finished execution inputs. It verifies 64/64 evolutions, 192 complete snapshots
and 32/32 boost pairs: all sampled positivity/conservative-budget requirements
and all 16 magnetic boost gates per profile pass. The previous 60-run partial
report and 32-run original report remain immutable; all their per-run
measurements are exactly equal to the corresponding entries in the full
report after fresh raw/config/source validation.

The last signal N256 jittered comoving pair has magnetic boost L1/amplitude
`9.717153666e-14`, final periodic position difference `1.381117443e-13` and
identical cell volumes. Both evolutions take 19178 accepted steps with 8214
CFL rejections, root value 4 throughout, no coarsening, no state/geometry
rejection and no HLL fallback. Its base magnetic-energy ratio is
`.9999703268777589`, passive Az L1/peak `1.590151863e-7` and passive B
L1/amplitude `.003758097183`. The maximum discrete initial/final B difference
is `4.144951253e-7`; these coupled comoving fields are not unchanged.

All eight base resolution sequences are now complete. Fixed passive-A
adjacent slopes remain about 1.40–1.47. The newly completed jittered comoving
finest slope is `.853232` for both profiles. These passive-reference
observations do not acquire a prescribed-flow success gate or a second-order
requirement. N256 comoving magnetic-energy ratios are approximately
`.9999706684` on regular meshes and `.9999703269` on jittered meshes for both
profiles. Final dimensional divergence RMS maxima over the full loop matrix
are `.000275961` (raw LS), `.000405436` (arithmetic face) and `.000466632`
(limited face); these update the smaller partial-sample maxima above. Full
signed-mean/RMS/max values and their fixed-floor dimensionless counterparts
remain archived without a machine-zero divergence claim.

Across all 64 runs, minimum rho is `.9999999729`, minimum p `.9999999552`,
maximum recorded normalized budget `1.47157e-13`, and independently reduced
budget `2.42029e-14`. Worst normalized magnetic boost L1 is `1.294792e-9`
for the original profile and `3.088036e-12` for signal, both below `.001`.
Passing the loop-specific gate does not override the signal N256 standing
Alfvén boost failure or establish general Galilean invariance.

Exact full-loop evidence is in `loop_matrix_report.json`,
`loop_matrix_check.log` and `loop_matrix_review_provenance.json`, using the
previously archived checker source. No simulation or solver change was made.
The final signal execution/measurement/archive layers, combined final figures
and final documentation/overall assessment remain pending. Full M1 is not
accepted.
