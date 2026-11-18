# AI review: projected-profile perturbations and cleaning diagnostics

**Separate AI review, limited to the evidence below. This is not human peer review or M1 acceptance.** The projected limiter removes the previously diagnosed common-factor discontinuity, but the tested finite-amplitude standing-wave perturbations still show physical amplification over a finite interval. Disabling only phi divergence forcing substantially reduces fine-grid quarter-time magnetic error. Neither observation establishes a validated replacement algorithm or an asymptotic stability result.

All three studies use the frozen implementation [`fb8bb14bf362a9eb42c2f32d6ec8c1252482790d`](https://github.com/arm2arm/openmhd-rs-/commit/fb8bb14bf362a9eb42c2f32d6ec8c1252482790d), before the separate checkpoint/restart work. No production numerical files were changed by this review. The experiments use serial `f64`, the ideal-gas EOS with gamma=5/3, nondimensional mu0=1, and periodic unit-square geometry. Each archive contains its exact commands, frozen source identities, executable/dependency hashes, measurements and qualified README.

| Evidence | Archive and inventory | Retained / omitted files |
|---|---|---:|
| Projected N8 coordinate operators, actual directions and finite-time trajectories | [Archive](../tests/reference/m1_completion/projected_standing_operator_ai.tar.gz), [provenance](../tests/reference/m1_completion/projected_standing_operator_ai_provenance.json) | 530 retained; 3 compiled artifacts and 4 large matrix CSVs omitted |
| Same actual perturbations with full two-wave HLL and projected limiting | [Archive](../tests/reference/m1_completion/projected_hll_standing_ai.tar.gz), [provenance](../tests/reference/m1_completion/projected_hll_standing_ai_provenance.json) | 99 retained; 2 compiled artifacts omitted |
| N256 quarter-time phi-forcing isolation | [Archive](../tests/reference/m1_completion/projected_cleaning_n256_ai.tar.gz), [provenance](../tests/reference/m1_completion/projected_cleaning_n256_ai_provenance.json) | 19 retained; 4 large raw CSVs omitted |

The original complete inventories contain 536, 100 and 22 files respectively, excluding each inventory itself. Every inventoried byte was checked before packing, including omitted files. Omitted data remain under the absolute persistent paths recorded in each provenance file; their SHA-256 hashes and sizes are retained. These are compact evidence archives, not complete raw-data distributions. Analyses requiring omitted CSVs need those local files or a reproduced evolution/operator calculation. Replaying an included figure is not independent solver validation.

The N8 standing wave has transverse amplitude .1, density 1, pressure .1, parallel velocity 1 and mean B=(1,0,0), with a regular 8×8 mesh and stationary generators. The reduced-potential reference velocity remains fixed when perturbations are applied. Rate matrices use central coordinate epsilon 1e-7; endpoint matrices use dt=1e-4. The unlimited matrices match the earlier compact unlimited controls bit for bit.

The leading limited coordinate rate eigenvalue is 7.70624 and the leading endpoint gain is 1.00077630. Actual directional responses do not reproduce these as genuine Jacobian eigenmodes: the leading rate direction has projection 2.67433 and a 78.6% vector discrepancy, while the selected endpoint direction gives gain 1.00027602. Opposite one-sided responses differ. The continuous projection is piecewise smooth at changing active constraints, so a coordinate finite-difference matrix alone is not a validated Fréchet derivative. The review evaluated 64 directions at four amplitudes, both signs, and independently checked 4,096 directional statistics.

Two directions were then evolved directly: the leading real coordinate mode and the phase with the largest tested actual local physical gain. Two amplitudes, 1e-6 and 1e-8, and both signs give four trajectories per direction and reconstruction choice. The common dt cap is .0002; output targets are 0, .0002, .01, .05, .1, .25, .5 and 1. All trajectories have 5,003 accepted steps, no CFL/state/geometry rejection and positive recovered density/pressure. The physical norm is

$$
\left[\sum_i V_i\left(\rho_{\mathrm{background},i}|\delta\mathbf v_i|^2+|\delta\mathbf B_i|^2\right)\right]^{1/2}.
$$

Potential and phi norms are reported separately; they are gauge-sensitive quantities with different dimensions, not a combined physical energy. The 1,536 independently recomputed snapshot norms/gains agree within 7.49e-16 relative. Maximum absolute conservative-budget drift is 2.89e-15.

| Actual direction | Projected HLLD final physical gain | Same direction with unlimited reconstruction | Projected full-HLL control |
|---|---:|---:|---:|
| Leading real coordinate direction | 14.16660 | .19214 | 5.47525 |
| Largest tested local-gain phase | 3.41212 | .01605 | 3.31229 |

The displayed final gains are representative across both signs and amplitudes; exact ranges and histories are archived. The leading projected direction grows through gains 1.49409, 2.22585, 3.71391 and 14.16660 at t=.1, .25, .5 and 1. The other history is non-monotone. This is actual finite-time physical amplification, not merely a coordinate eigenvalue or a gauge-only norm effect. It does not prove asymptotic instability about a discrete equilibrium: the unperturbed numerical wave also evolves, no exact continuum perturbation reference is supplied, and transient or non-normal growth is not excluded. These diagnostics do not create a retroactive acceptance gate.

The full-HLL isolation changes exactly one branch in frozen `mhd-core`: `hlld(eos, l, r, [sl, sr], [pl, pr])` becomes `None::<(State, State)>`, selecting the existing two-wave HLL fallback. It retains SL/SR, supersonic upwinding, symmetric A-face completion, projected limiting, cleaning and timestep choices. Original core SHA-256 is `634fa1d8290a40901171b1cedd42575122e078e6e0617155b306c721f1ee0c8b`; modified core SHA-256 is `998803b1ea4b9f55cc0c14701dc5a621b8f72b4e60e352070fd012e7f52065a4`. The two directions and every initial background/perturbed snapshot match the HLLD controls byte for byte. All eight perturbed HLL trajectories have zero rejections; 768 independently recomputed norms agree within 6.22e-16 relative, with maximum absolute budget drift 3.22e-15. Full HLL reduces the first amplification but does not remove growth in either tested direction. No HLL spectrum or worst-case HLL direction was measured, and this result does not justify adopting a new production flux.

The N256 cleaning control extends the [sealed N64/N128 isolation](../tests/reference/m1_completion/compact_cleaning_diagnostics_ai_provenance.json). It reuses the exact same modified binary, SHA-256 `ffcb2bb20155f93cc8473af99babc8b73ba5ab5f522e421b03c354e4d9a8aa96`. Its only scientific patch replaces the divergence argument to `Cleaning::begin` by zero. Frozen `general.rs` SHA-256 is `04af7242017bc3a1c40ed00ac421ca722fe7891bcad091943c69de9fe06a9053`; modified SHA-256 is `2238141396215a100aae331b85987f594fa5ea1906424f74a423c6a31d5ff8f5`. All cleaning timestep bounds, other equations and the adaptive policy remain unchanged. Initial phi is zero and remains exactly zero.

This irregular travelling-wave run uses jitter .15, parallel velocity zero, fixed mesh and the exact cached geometry, stopping at t=.25. The control and baseline initial CSVs are byte-identical; paired IDs, coordinates, volumes and times agree exactly. The baseline was captured and hash-verified while its N256 evolution was ongoing. That original interim evidence is preserved unchanged; the completed baseline and its final t=1 convergence gate are reviewed below.

| N256 quarter-time measurement | Projected baseline checkpoint | Phi-forcing-disabled diagnostic |
|---|---:|---:|
| Magnetic vector L1 error | 2.19393489e-5 | 9.88920947e-6 |
| Velocity vector L1 error | 1.82876572e-5 | 7.57975073e-6 |
| Bz RMS after removing constant and physical-x fundamental | 2.60302498e-5 | 5.23391216e-6 |

Magnetic L1 decreases 55.0%; the Bz residual decreases 79.9%. Its high logical-index frequency energy fraction decreases from .9636 to .1660. This index-space FFT diagnoses cell-scale variation; it is not an exact Fourier transform on irregular physical coordinates. The fitted fundamental uses physical centroids and volume weights. The earlier N128 no-forcing magnetic L1 is 3.95501182e-5, nearly four times the N256 value, but this quarter-time observation is not a full-time convergence result. The N256 control has 2,305 accepted steps, 2,227 CFL retries, no state/geometry rejection, positive states and maximum normalized budget residual 5.05e-16. All six raw-artifact digests and source/binary/cache/final control seals were verified.

These interventions support a growing cleaning-branch contribution to fine-grid contamination. They do not uniquely distinguish direct discrete curl(grad(phi)), local damping variation, frozen-C1 temporal treatment, auxiliary interpolation or feedback through the fluid solution. The intervention can also change the later adaptive schedule. Substantial error remains, and production cleaning stays enabled. The separate seam investigation retains the circular-wave cancellation and decreasing measured residual; seam correlation alone does not establish an auxiliary-field cause. The three included figures were visually inspected, with guide slopes explicitly distinguished from fits.

For archive verification, the sidecar JSON contains each retained member hash, every omission, the complete original inventory hash and the compressed archive hash. Packing uses sorted USTAR members, mode 0644, zero timestamps/UID/GID, empty owner names, and gzip level 9 with timestamp zero and no filename. Two independent packings were byte-identical, and every extracted member was checked against the captured source bytes. Archive SHA-256 values are:

- `projected_standing_operator_ai.tar.gz`: `94ea2f3b105564c6762b11b74716e153e6819dd937a92648f76de27b816a6c60`
- `projected_hll_standing_ai.tar.gz`: `4dcba2cee3ccb71ece727804dcb893397de5db19c3e71436c4b069d0e88fb4a3`
- `projected_cleaning_n256_ai.tar.gz`: `9e10d36440cf7856babde4174856cacfa13323c895a9671e3fb4d4383941c94d`

Reproduction instructions are in each archived README and provenance. They require the frozen revision and specified dependencies; diagnostic source variants must remain separate from production. Use one BLAS thread for Python analysis. No further evolutions were performed for this documentation/archive task, and no new candidate or M1 acceptance is approved here.

The subsequently completed frozen projected ladder **fails the registered convergence-order gate**. The [compact full-probe archive](../tests/reference/m1_completion/projected_probe) retains the original manifest, runs and provenance byte for byte, all four summaries and histories, execution logs, independent review script/results, and raw-data hashes. Its [archive provenance](../tests/reference/m1_completion/projected_probe/archive_provenance.json) records compressed and uncompressed digests; large CSVs remain at the recorded local paths.

| Square grid | Independently recomputed final magnetic vector L1 |
|---|---:|
| 32 × 32 | .001761056258556284 |
| 64 × 64 | .0003882974543627325 |
| 128 × 128 | .00009451105060308065 |
| 256 × 256 | .00003989265086703633 |

The least-squares order over N64/128/256 is **1.6414836751489905**, below the unchanged minimum **1.8**. Adjacent orders are 2.18121, 2.03861 and 1.24436. The finest error divided by the analytic wave amplitude .1 is .00039892651, passing its separate maximum .02 criterion; that does not override the failed order. This is a completed bounded irregular travelling-wave ladder, not the full M1 physical/temporal matrix, and it does not justify closing M1.

The separate AI packet review verifies all 28 raw-artifact digests, both final metadata seals, 28 source/configuration hashes against the exact Git revision and frozen checkout, the executable, four mesh-cache hashes and eight cache-producer geometry-source identities. All 288 independently recomputed component/vector L1, L2 and maximum errors agree with the execution ledger within 3.04e-18 absolute. The three stored times have complete ordered cell IDs, identical fixed geometry, finite fields and positive density/pressure. Conservative totals were independently recomputed; maximum recorded normalized budget across stored times is 1.11e-14. No invalid-state or geometry rejection occurred; the archived counters retain all CFL retries. N256's launcher reports 4,930.526252375 monotonic seconds.

The captured N256 quarter CSV hash, `6a8abef35636fa4f3737c199b350fd4bb76e3c08ca4abd3ab49ca71f4fa5effe`, agrees exactly with the completed run's final seal, and the no-forcing initial CSV matches the now-sealed baseline. Thus the earlier cleaning-isolation comparison has a confirmed final execution provenance. Its reduced quarter-time error still does not establish a production fix, full-time convergence, or a unique causal mechanism. No solver was rerun for this final evidence review.
