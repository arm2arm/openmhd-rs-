# M1 restart handoff — 2026-11-05

Work was stopped for laptop shutdown. **M1 and issue #7 remain open.** No experimental candidate has passed every registered gate. Do not merge this branch as completed M1 or close the issue based on passing unit tests or the shock/vortex results alone.

## Saved state

- Workspace: `/Users/arm2arm/orca/workspaces/openmhd-rs-/M0`; development branch `arm2arm/M0`.
- Current scientific implementation: `aae382e` (`bulk-frame-hll-compact-v1`); subsequent commits add measurements, reports and archives. The original default remains `paper-global-v2`.
- All requested M1 cases and measurement tools are implemented. Latest checks: 112 Rust tests, formatting, strict Clippy, locked release build, 28 Python measurement/geometry tests, 13 M0 algebra checks and independent-reference integrity checks pass. The label-only measurement amendment received a separate AI review.
- Completed raw simulations remain under workspace `results/`. Numeric ledgers, commands, source/binary/raw hashes, reference projections and plot inputs are checked into `tests/reference/m1_completion/`. Large raw CSVs are retained locally.
- Temporary diagnostic directories have persistent copies under `results/review_resume/`. Their source and data are also preserved in `tests/reference/m1_completion/shutdown_diagnostics_ai.tar.gz`, with binary hashes in its provenance. Do not depend on `/tmp` surviving reboot. The local working chronology is also preserved in `results/M1_ACTIVE_HANDOFF.md`.

## What finished and what failed

The historical HLL and matched profiles each completed the 31-run prescribed-loop/shock/vortex packet and pass those gates. See [HLL results](M1_HLL_RESULTS.md) and [matched results](M1_MATCHED_RESULTS.md). Their irregular-wave orders fail: 1.17745 and .77243. The matched subset also fails three primary wave-boost comparisons.

The latest compact candidate completed its full fixed irregular travelling-wave ladder and a separate 48-run N32/64 wave/loop subset. See [compact results](M1_COMPACT_RESULTS.md).

| Compact result | Observation | Gate |
|---|---:|---:|
| N64 final B L1 | .000388397583 | Part of spatial fit |
| N128 final B L1 | .0000946208533 | Part of spatial fit |
| N256 final B L1 | .0000399762622 | Finest relative error .000399763 passes .02 |
| Finest-three order | **1.640159** | **Fails 1.8** |
| Regular standing fixed N32 boost, maximum normalized L1 | **1.03153e-5** | **Fails 1e-8** |
| Regular standing fixed N64 boost, maximum normalized L1 | **1.35202e-5** | **Fails 1e-8** |

All compact runs stay positive and conservative. The subset passes 14/16 wave boost pairs and 8/8 coupled-loop boost pairs. The full compact mean/temporal/physical packet was not launched after these failures. Earlier profiles' physical results cannot substitute for a future candidate's own validation.

The completed directories are `results/m1_compact_probe`, `results/m1_compact_quick` and `results/m1_matched_remaining_final`. The matched wave study and earlier superseded experiments retain explicit interruption controls; externally stopped and unexecuted cases must not be counted as solver failures or passes.

## Separate AI diagnosis and limits

The reviewer is `/root/issue6_ai_review`; all review claims are labelled AI review, not human peer review. Implementation review verified 36 historical evolutions bit-identical and 24 compact passive/general transport rates exactly equal. Completed matched archives, reference comparisons and figure replay received separate checks; see [the review log](M1_COMPLETION_AI_REVIEW.md).

Current diagnostic evidence:

1. Compact initialization is approximately second order. Fine evolved errors contain short-wavelength Bz/vz contamination. The discrete curl of the cleaning gradient is nonzero and correlates with that noise; this is not a unique causal proof.
2. Fixed-cap standing controls also fail: N32 dt=.0002 gives maximum normalized boost L1 about 7.99e-6; N64 dt=.0001 gives about 5.84e-6. Paired step counts match, with no CFL/state rejections. Adaptive timestep branching is therefore not necessary for the failures.
3. Initial finite-amplitude rates and one-step boost comparisons agree to roundoff. The discrepancy develops during evolution.
4. A preliminary full nine-variable finite-amplitude N8 limited-operator probe shows positive coordinate-Jacobian growth around 6.59 and endpoint-map spectral radius around 1.000711 at dt=1e-4. Limiter ties are not differentiable: these matrices alone do not prove a physical unstable mode. Unlimited and constant-background controls do not show the same strong indication. Actual directional perturbation checks were not started before shutdown.
5. Cubic moment correction and uniform damping controls do not justify another implementation: small coupled growing modes remain, and grid-scale phi contamination is not automatically reduced. They are diagnostic contingencies, not approved candidates. The cleaning decay time is R/(beta*cs); beta*R/cs is the diffusive step bound.

No new solver/profile, threshold, CFL coefficient, limiter policy or cleaning stage has been changed in response to these last findings.

## Resume here

1. Read the completed compact report, AI handoff and current Git status. Preserve all failures and user changes.
2. Restore diagnostic sources/data from the checked-in shutdown archive or `results/review_resume/` if `/tmp` was cleared. Recreate the frozen `aae382e` source checkout and pinned build only if needed; never overwrite completed output directories.
3. Test the extracted finite-amplitude mode using actual one-sided and symmetric perturbations, distinguishing limiter-direction effects from a true growing solution. Inspect primitive versus A limiting and point-A/FV transport coupling.
4. If warranted, compare full two-wave HLL or symmetric-fan conservative/induction fluxes as small operator controls. The present profile changes only the A-face completion; it still uses HLLD fluid/induction fluxes. This is a hypothesis to assess, not authorization to silently replace the method.
5. Register and separately review any justified algorithm change under a new profile. Run the small standing boost controls and the complete irregular wave ladder before another full expensive packet. Keep every original threshold.
6. Only after all required physical, temporal, conservation, positivity and invariance evidence passes: finish the separate AI scientific review, update the roadmap, merge/push main and close #7/M1.

There is no reliable M1 completion-time estimate until the numerical blockers are resolved. Earlier estimates assumed a passing candidate and no longer apply.
