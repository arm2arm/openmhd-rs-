# M2a completion requirements and current evidence

**2026-11-25. The 512-cell jittered mesh passed all eleven independent checks.** The original
budget stopped at 500 million predicate operations. The new run used
1,907,489,046 operations in 810.54 seconds and returned 4,063 shared faces.
REANA compared the complete Rust transcript with the independent reference.
All cell IDs and face keys matched. The relative total-volume error was bounded
by 2.17 × 10⁻¹⁹ and the largest relative face-area error by 3.37 × 10⁻¹³.
On the co-spherical cube the opt-in driver reproduced the original transcript
byte for byte and passed all eleven metrics.
[Qualification results](results/m2a_general_20261125/predicate-budget-qualification.json) ·
[Raw workflow receipts](results/m2a_general_20261125/predicate-budget-qualification.tar.gz).

The calibrated build passed all **28 geometry-specific Rust tests in both
debug and release**, giving 56 independent REANA results. Each profile covered
seven analytic fixtures, seventeen geometry and input checks, and four
exact-arithmetic tests. The record includes the executable hash and raw Rust
test output for every workflow.
[56 geometry test results](results/m2a_general_20261125/calibrated-geometry-controls.json).

**The full workspace regression gate passed on the calibrated build.** All
338 debug and 338 release selections have verified passing results. REANA ran
611 prebuilt tests and eight application restart tests with the geometry
feature enabled. The other 57 selections use earlier passing workflows whose
test executables match the calibrated build byte for byte. The archive also
retains the earlier eight restart runs that used the default feature set.
[All 676 results](results/m2a_general_20261125/calibrated-workspace.json) ·
[Workflow receipts](results/m2a_general_20261125/calibrated-workspace-receipts.tar.gz).

The static 3D builder keeps the supplied generator positions fixed. The
sliver and nearly coincident fixtures therefore exercise their original
geometry. A triangle area or tetrahedron volume too close to its arithmetic
error bound produces a typed rejection. Centroid-directed generator motion
is specified separately for moving meshes. The proposed velocity correction
vanishes when a generator sits at its cell centroid, even for a very small
cell. AREPO's centroid steering and its later iterative Lloyd scheme address
cell shape. Removing a cell by derefinement is a separate resolution change.
[Metric check](../../crates/moving-mesh/src/three_d/moments.rs) ·
[Proposed mesh velocity](STATE_DEPENDENT_MESH_MOTION_SPEC.md#2-explicit-state-dependent-velocity-law) ·
[Springel (2010)](https://arxiv.org/abs/0901.4107) ·
[Mocz et al. (2015)](https://arxiv.org/abs/1503.07868).

**Original build. G00 and G01 passed.** REANA produced a verified passing result
for every workspace test, **338 debug and 338 release**. The static analytic
campaign passed all 252 comparisons and all 2,016 gate groups. **M2a remains
open.** The independent reference returned 512 cells and 4,063 shared faces for
the 8³ jittered mesh. The Rust driver stopped after 215.25 seconds at its
500,000,000-operation predicate budget and returned no cells. The other five
irregular base meshes passed all eleven comparison metrics. The opt-in analytic
qualification and the common-build irregular and reproducibility campaign remain open.
[Base results](results/m2a_general_20261125/base_results.json) ·
[Raw REANA receipts for all 34 workflows](results/m2a_general_20261125/base_workflow_receipts.tar.gz).
[Workspace release](results/workspace_g00_20261125/g00-release.json) ·
[Analytic comparisons](STATIC_GEOMETRY_COMPARISON_RESULTS.md).

The workspace review counted 186 component tests, 184 original workspace
tests, 52 offline Cargo tests, one isolated Cargo retry and 253 tests from
the archived build. Each entry has a distinct terminal workflow UUID and a
unique combination of profile, Cargo target, source and test name. The build
passed formatting, strict Clippy, release compilation and test discovery.
Git comparison with build revision `6c19410` found identical Rust sources,
Cargo manifests, lockfile and toolchain configuration. [All 676 results](results/workspace_g00_20261125/workspace_full_676.json).

Fifty workflows needed their input transfer completed before their first
successful start. For 41 of them, a smaller gzip encoding transferred the
full executable. The downloaded bytes decoded to the SHA-256 digest of the
original build member, and the remote runner verified that executable before
running the test. The receipt archive contains the raw test output for
all 676 cases and retains the transfer history for the affected workflows.
[Workflow receipts](results/workspace_g00_20261125/workspace_receipts.tar.gz).

The debug qualification exercised repeated periodic geometry. The release
qualification checked compression and the exact baseline. Each workflow listed
the executable's tests, checked the ignored-test list and ran its one named
test. Each restart test compiled in Cargo's source layout so it could launch
its companion process. The evidence includes all five terminal workflow IDs
and their raw results. [Qualification and restart receipts](results/workspace_recovery_20261125/runner_qualification.tar.gz).

At 08:30 UTC, the isolated retry of case 0049 passed its periodic shock-fit
refinement and offset-invariance test. Its original attempt reached the
1,800-second Cargo timeout. With the same staged inputs and resource limits,
the retry compiled in 82.5 seconds and ran the test in 1.9 seconds. Both
workflow UUIDs, the failed build and the passing output are retained.
[Retry verification](results/workspace_recovery_20261125/verification.json) ·
[Raw workflow and build receipts](results/workspace_recovery_20261125/pilot_receipts.tar.gz).

The exact workspace preflight build was recovered for the remaining
regressions. All 394 archive parts and all 114 compiled executables matched
the preflight manifest. The 256 outstanding tests use 47 target/profile
combinations at the time of recovery. The selected `paper-shock-geometry` tests were 0051 and 0295.
The three restart tests used the source-layout route.
[Build identities and remaining restart selectors](results/workspace_recovery_20261125/verification.json).

At 07:49 UTC, REANA listed 63 of the 306 planned corrected workflows. All 49 finished
workflows have verified test outputs. Eleven stopped after reaching the
30-minute Cargo compile limit. Five recorded a timeout and six recorded a
cleanup failure. None reached its Rust test. Three workflows were created
without starting, and the remaining 243 had no allocation. A separate check
of the original 490 workflows still found 207 marked running and five pending.
[Workflow identities, failed-stage records and verified coverage](results/m2a_recovery_20261124/workspace_20261125_0752.json).

A new periodic coincidence control returned the expected `CoincidentGenerators`
error for two distinct IDs at the same wrapped position. On the periodic cube,
the serial repeat reproduced the native output byte for byte after accounting
for the case label. Changing one surface-coordinate bit made the repeat check
fail as intended. All 24 right-side face incidences matched their expected
coordinates, including 12 across the periodic boundary. The chart check
detected a deliberately introduced half-box offset.
[Geometry control outputs](results/m2a_recovery_20261124/workspace_20261125_0752.json).

On November 24 at 22:48 UTC, the first corrected workspace regression passed
on REANA. The Brio–Wu test confirmed that a rejected trial preserves the
state and succeeds on a shorter step. Its Cargo installation matched all
80 locked packages and 3,328 files. This brought verified coverage to
**371 of 676** debug and release tests at that checkpoint.
[Pilot result](results/m2a_recovery_20261124/corrected_pilot.json) ·
[Raw test and build evidence](results/m2a_recovery_20261124/corrected_pilot.tar.gz).

At 22:49 UTC REANA finished freezing 84 generator arrays for the new
campaign. The catalog lists 12 mesh families, seven input variations and
252 selections across one, two and four threads. The 22 control results
include three fresh downloads and one explicitly mapped replacement for
a stalled workflow. [Geometry control results](results/m2a_recovery_20261124/general_controls.json) ·
[Frozen inputs and campaign](M2A_GENERAL_CAMPAIGN.md#executed-controls-and-frozen-inputs).

The [continuation record](M2A_COMPLETION_PROGRESS_20261124.md) traces the
216-method execution checks, the network interruption and the corrected
306-case regression plan. The earlier observations are dated below.

## What is already supported

- All **252 static analytic comparisons** passed: seven families, three
  scales, six coordinate permutations and two translations, with all **2,016
  registered gate groups** passing in the recorded outputs. The
  [scientific results](STATIC_GEOMETRY_COMPARISON_RESULTS.md) retain their
  source, independent-reference and actual execution boundaries.
- All **28 written static geometry methods** passed individually in **both
  debug and release**: 56 original REANA workflows within the complete
  186-method component packet. They cover analytic geometry, exact-arithmetic
  controls, selected input errors, canonical ordering, periodic image charts
  and epoch handling. The earlier original and relocated offline checks both
  returned zero. These unit/control results are narrower than the complete
  G02–G04 matrices.
- This inspection rechecked all **2,352 retained bodies** belonging to those
  56 geometry workflows against their original manifest. All 28 current
  source test names match the executed selectors. The inspected geometry
  implementation, test files, exporter, shared identity root, Cargo manifests,
  lockfile and toolchain bytes still match actual compiled candidate revision
  `58fe532f642e17f4961ce1ce7497882a88cbf069`.

Seven of the geometry methods directly exercise difficult inputs or
reproducibility. Each passed on REANA in both debug and release. The table
shows what the assertions in those 14 tests establish.

| Input | Observed behavior |
| --- | --- |
| Invalid catalogs and domains | Duplicate IDs, coincident generators, NaN coordinates, invalid widths, empty and oversized catalogs, positions outside the domain, and a winding on a bounded domain returned their expected errors. |
| Extreme image indices and length scales | Equal extreme windings preserved the one-cell mesh with three faces and six incidences. An unrepresentable winding difference or physical moment scale returned its expected error. |
| Reversed input order | The two-generator bounded case reproduced the cell volumes, centroids, central moments and face areas bit for bit. Face keys and polygons also matched. |
| Unequal periodic windings | The eight-cell cube retained 24 shared faces. Each cell had six distinct neighbour images, and the opposite face incidences used the expected chart translations. |

These 14 results are included in the workspace count. The irregular-mesh and
cross-thread comparisons below still need their own outputs.
[Original Rust test output, workflow IDs and artifact hashes](results/m2a_recovery_20261124/difficult_input_witnesses.json).

The implementation remains the small serial `HalfSpaceOracle3`. No accelerated
geometry backend has been adopted. The existing G01 decoder accepts only the
seven registered analytic families with zero trajectory windings; it is not a
ready-made jitter, sliver or winding campaign runner.

## Completion checklist

The requirements remain those registered in
[the mesh specification, section 9](MESH_3D_SPEC.md#9-prospective-reana-fixtures-gates-and-dependencies).
No threshold or required family is removed by this checklist.

| Gate | Existing evidence | Work required to close it |
| --- | --- | --- |
| **G00 — coherent source and regressions** | Format, strict Clippy, build/discovery and 216 execution controls passed. The original and calibrated builds each have verified passing results for all 676 debug/release test selections. | Complete. |
| **G01 — analytic geometry** | All 252 original candidate/reference comparisons and 2,016 gate groups passed. | Verify the same analytic fixtures with the opt-in executable. |
| **G02 — irregular and thin cells** | The original jittered 4³ and 6³ lattices, clustered points, slivers and boundary-near points passed all eleven metrics. The opt-in build also passed all eleven on the 8³ jittered mesh. | Confirm all six on the common qualified build. |
| **G03 — invalid inputs and degeneracies** | Debug and release tests verified typed rejections for duplicate IDs, coincident points, invalid domains and nonfinite coordinates. A periodic case with unequal winding vectors also returned the expected coincidence error. The three separations from 1e−4 to 1e−12, co-spherical cube and coplanar array passed all eleven metrics. The nearly coplanar case returned the registered typed uncertainty in tetrahedron volume. | All six single-thread base outcomes are accounted for. Retain the ambiguity when evaluating transformed inputs. |
| **G04 — reproducibility and periodic charts** | Selected input-order and winding controls passed. The periodic cube also passed the serial repeat and chart checks, with successful detection of one altered bit and a half-box displacement. | Compare all registered reorderings, repeats, translations and periodic seam crossings across one, two and four threads. Check canonical cell and face identities, normalized geometry and bitwise agreement. |

G02 retains the registered relative total-volume and surface-normal closure
limits of `1e-10`, and the declared tensor/centroid and independent-oracle
comparison limits of `1e-9`. G04 retains `1e-10` normalized agreement and exact
canonical keys away from zero-area events. Resource/ambiguity rejection must be
reported explicitly; it cannot silently replace a required successful mesh.
The oracle's hard 512-generator bound is not a measured runtime guarantee.

Full 3D derivatives/curl/gauge operators belong to **M2b**. Coupled mesh motion,
GCL, topology events and MHD evolution belong to **M2c** and subsequent gates.
Those are not added as new conditions for M2a. The animation on the main README
remains a separately labelled kinematic illustration.

## Original workflow observations on November 24

Normal-TLS GETs at **15:39:48 UTC on 2026-11-24** still observe the following
original execution-control workflows:

| Original case | Original UUID | State |
| --- | --- | --- |
| 0123 | `ceb8d3ab-de2a-4112-a2c5-c4a81ea8b6f2` | queued |
| 0125 | `63224758-14f6-43ac-acb1-64af7fa77285` | queued |
| 0180 | `218c9734-b666-4638-ac4d-d72856913a17` | pending |

Separate UUID-targeted status and log reads at 15:41:49–50 UTC agree. All three
have empty available workflow logs and no job-log entries. The service is
reachable; these observations do **not** identify why execution has stalled.
These three states prevent whole216 completion, strict collection and final
output review. Their original versions, submission uncertainty history and
inputs are preserved.

At the owner's request, one fresh replacement for each of these three stalled
methods was submitted at **15:59:52 UTC**. All three replacements finished and
passed their exact single method, with **24 artifacts and 30 successful
UUID-linked transports**; separate offline validation returned zero at
16:03:14 UTC. The [rerun record](STALLED_PREREQUISITE_RERUN_RESULTS_20261124.md)
retains the original-to-replacement identities and complete captured outputs.
The originals remain unchanged. This closes the requested three-method rerun;
it does not silently substitute new identities into the original whole216
packet or close the broader G00 workspace gate.

A finite GET-only observation of **all 490 remaining workspace leaves** closed
at **15:40:59 UTC**:

| Server state | Workflows |
| --- | ---: |
| finished | 184 |
| failed | 94 |
| running | 207 |
| pending | 5 |

Every current UUID agrees with the previous original inventory. These are
server states, not a new 490-case numerical verdict. The earlier retained
output inspection attributed 93 failures to compile-stage timeouts with
dependency-fetch evidence, and retained one failed server workflow despite a
clean raw leaf. The full original batch is nonpassing and nonterminal.
The [offline canaries](OFFLINE_BUILD_CANARY_RESULTS_20261124.md) demonstrate
the corrected build-input route for two selected leaves; they do not upgrade
the failed original batch or provide its missing method results.

## Disposition at the original workflow inspection

1. Incorporate the explicit three-method replacement proof into the complete
   execution-control prerequisite disposition and output review, preserving
   original UUIDs and receipts. The requested reruns now pass; they do not
   alter the original whole216 packet's coverage or identity requirements.
2. Complete the workspace regression gate using the qualified offline input
   route and a reviewed release that explicitly retains the failed original
   batch. Existing workflow results must not be renamed or silently replaced.
3. Freeze/review the missing G02–G04 input/reference/reducer packets and their
   exact resource declarations. Preserve the existing G01 source and results.
4. After the relevant prerequisites pass, execute each independent case on
   REANA, collect complete outputs, reduce the unchanged registered limits and
   complete a separate scientific output review.
5. Record scoped M2a acceptance only after every required row closes. That
   decision would still not accept M2b/M2c, full moving 3D MHD or a merger.

At that earlier checkpoint the G00 failures held dependent long validation under the
[owner execution policy](../REANA.md#current-execution-policy-2026-11-11).
The earlier coverage-inspection attempt performed no workflow mutation, test execution, compilation,
geometry/reference arithmetic or scientific-source edit. No new agent was
started. No previously running workflow was reset or promoted to passing.
The separately recorded owner-authorized replacement executions above occurred
after that inspection.

The [machine-readable assessment](results/m2a_finalization_20261124/assessment.json)
records **18,141 inert identity/coverage relations with no errors**, including
the full fresh GET inventory and the selected old geometry body hashes.
The [reading manifest](results/m2a_finalization_20261124/source_and_reading_pins.json)
identifies the exact inputs. Its compact `reading.tar.gz` retains 2,025 original
source/requirements/observation/log bodies; the 2,352 selected native result
bodies remain in the named external original packet and have their hashes
listed separately. The published checkpoint is not a self-contained copy of
the complete scientific campaigns. This is coordinator inspection, not a new
independent-agent review or a numerical acceptance claim.
