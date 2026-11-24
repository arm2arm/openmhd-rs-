# M2a completion requirements and current evidence

2026-11-24. **M2a is not complete.** The static analytic comparison slice
passes, but the registered workspace prerequisite and the broader geometry
families are still open. This checkpoint records a coordinator coverage
inspection and fresh read-only REANA observations. It grants no new component
acceptance and leaves the accepted fixed/rigid 2.5D M1 scope unchanged.

On November 24 at 22:48 UTC, the first corrected workspace regression passed
on REANA. The Brio–Wu test confirmed that a rejected trial preserves the
state and succeeds on a shorter step. Its Cargo installation matched all
80 locked packages and 3,328 files. This brought verified coverage to
**371 of 676** debug and release tests at that checkpoint.
[Pilot result](results/m2a_recovery_20261124/corrected_pilot.json) ·
[Raw test and build evidence](results/m2a_recovery_20261124/corrected_pilot.tar.gz).

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
| **G00 — coherent source and regressions** | Format, strict Clippy, build/discovery and selected component leaves have passing records. Two offline-build/restart canaries also pass. | Resolve the outstanding execution-control prerequisites, then obtain complete passing debug/release workspace execution, acquisition and output review. A compile/list catalog or two canaries cannot close the full gate. |
| **G01 — analytic geometry** | All 252 candidate/reference comparisons and 2,016 recorded gate groups pass. | Close G00 and review the full prerequisite boundary before granting G01/M2a prerequisite acceptance. Preserve the already completed comparisons. |
| **G02 — irregular/conditioned geometry** | No complete execution-ready campaign or accepted general-geometry comparison packet. | Freeze jittered 4³/6³/8³ arrays at 0.15 spacing with a specified counter-based seed 20261122; explicit clustered, sliver and boundary-near arrays; a separately reviewed independent general-geometry reference, comparison and resource calibration. Run each original input separately after its prerequisites pass. |
| **G03 — invalid inputs and degeneracies** | Existing methods test several typed failures and exact-contact cases. | Complete the explicit separation ladder at 1e-4/1e-8/1e-12 spacing, remaining degeneracy families and per-case typed rejection/uncertainty accounting. Required smooth fixtures must build successfully; rejection is not a pass for them. |
| **G04 — reproducibility and periodic charts** | Selected bounded input-order and periodic unequal/extreme-winding controls pass. | Complete the G02/G03 reverse-order, fixed shuffle, repetition, 1/2/4-thread, seam, translation and multiple-winding matrix. Check canonical key equality and normalized metric differences separately from reported bitwise determinism. |

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

## Fresh prerequisite observations

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

## Execution disposition and next actions

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

The verified G00 failures hold dependent long validation under the
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
