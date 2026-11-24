# Results retention and first cleanup — 2026-11-24

Nineteen intermediate wave-checkpoint directories were compressed, verified
and removed from the old worktree's expanded `results/` tree. All 1,755 regular
data files remain in individually indexed local archives. Their original
10,701,733,315 bytes occupy 3,998,976,019 compressed bytes, a reduction of
**6.24 GiB** before small inventory overhead. This is storage compaction and
grants no new scientific or test acceptance.

The archived directories are exactly
`independent_fresh_waves_checkpoint_20261122_0002` through `0020`.
Checkpoint `0001`, which contains original symbolic links, and the final
expanded checkpoint `0021` remain. All twenty-one observation JSON sidecars,
original campaign outputs, final scientific collection, failure receipts and
unfinished validation campaigns remain in place. The old `results/` tree now
occupies approximately **104.40 GiB**, down from **114.37 GiB**.

## What has been checked and rendered

| Evidence | Recorded state | Retention limit |
| --- | --- | --- |
| [Accepted M1 reference](../tests/reference/m1_final_acceptance/README.md) | The registered 214-case fixed/rigid 2.5D campaign, final collection, reductions and separate review are complete. The compact acceptance packet is committed. | Its export explicitly omits large raw inputs while retaining their identities. Figures and summaries do not contain every original byte. |
| [Static 3D comparisons](galaxy/STATIC_GEOMETRY_COMPARISON_RESULTS.md) | All 252 registered analytic comparisons passed. [Three actual-driver PNG/SVG figures](galaxy/STATIC_GEOMETRY_VISUALIZATION.md) were rendered on REANA and visually inspected. Their inputs, transcripts, renderer and provenance are committed. | This covers static geometry. The separate animated 3D preview illustrates prescribed motion and is not a moving-MHD validation result. |
| [Current infrastructure and workspace validation](galaxy/OFFLINE_BUILD_CANARY_RESULTS_20261124.md) | Eleven dependency-installer controls and both ordinary/restart offline-build canaries passed. | The original 216-method collection/review and wider Rust campaign remain incomplete. Their operational evidence is retained. |

The cleanup read and checked all **2,590** member hashes in the committed M1
outer/evidence/review inventories and the actual/static and preview rendering
inventories before and after compaction. No published artifact changed.
These were retained-byte checks; no project import, test, numerical reducer
or renderer was executed locally.

## Archive location and verification

The compressed archives and full per-file inventories are outside every
worktree scheduled for deletion:

```text
/Users/arm2arm/orca/archives/openmhd-rs-/wave-checkpoints-20261124-attempt02/
```

The [summary](results_retention_20261124/summary.json),
[final inspection](results_retention_20261124/final_inspection.json),
[operation journal](results_retention_20261124/events.jsonl) and
[receipt inventory](results_retention_20261124/sha256.json) record every archive
hash, original member hash/size/mode and completed removal. These small records
are committed. **The compressed data archives are local to this laptop, not
pushed to GitHub or independently backed up.**

Each archive was read back and every member compared with the original
inventory. The source tree was checked again, moved to a temporary location
beside its archive and checked once more before removing that expanded copy.
Any failed check stops removal. An initial attempt stopped at checkpoint
`0001` because the regular-file guard found symbolic links; it removed no
source data. The retained revision excludes that checkpoint rather than
following or changing its links.

To recover an archived checkpoint, compare its archive SHA256 with the summary
and extract it into an **empty** directory. For example:

```sh
shasum -a 256 /Users/arm2arm/orca/archives/openmhd-rs-/wave-checkpoints-20261124-attempt02/independent_fresh_waves_checkpoint_20261122_0020.tar.gz
mkdir -p /tmp/openmhd-checkpoint-restore
tar -xzf /Users/arm2arm/orca/archives/openmhd-rs-/wave-checkpoints-20261124-attempt02/independent_fresh_waves_checkpoint_20261122_0020.tar.gz -C /tmp/openmhd-checkpoint-restore
```

The extraction recreates the original checkpoint directory name. Its adjacent
`.inventory.json` supplies every original file's expected SHA256 and length.
Historical commands that refer to an archived checkpoint's old expanded path
require restoring that checkpoint first.

This first cleanup does not make the complete `results/` tree disposable.
The remaining unique inputs, complete operational capsules and unfinished
campaign evidence still need retention outside the worktrees before those
workspaces can be deleted without losing data.
