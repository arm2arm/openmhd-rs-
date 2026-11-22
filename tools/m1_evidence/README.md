# Read-only M1 evidence tools

These host utilities collect, reduce and freeze existing REANA outputs.
They submit no numerical workflow, evolve no state, build no code and
cannot accept M1. The scientific source, registered cases and numerical
reducers remain unchanged. See [the archive plan](../../docs/M1_FINAL_ARCHIVE_PLAN.md).

Use the repository root as the working directory and fresh output paths.
The [independent source review](../../docs/M1_FINAL_ARCHIVE_DESIGN_REVIEW.md)
at `b402753` requires repairs before complete capture/packaging or reliance
on portable verification. Its eight findings cover wave symlink containment,
connected provenance/coverage, nested inventories, coherent observations,
failure receipts and optimized-interpreter rejection. The following commands
describe the intended workflow; that repaired full path has not run.
After the existing supervisor produces the complete passing verdict:

```sh
python3 tools/m1_evidence/prepare_final_evidence.py --output results/m1_final_complete_collection
python3 tools/m1_evidence/pack_final_review_evidence.py --input results/m1_final_complete_collection --output results/m1_final_output_review/evidence
python3 results/m1_final_output_review/evidence/verify_final_review_evidence.py
```

The collector first requires all 214 cases and seven phase checks, then
executes unchanged strict provenance verifiers and six independent read-only
reducers. The physics collector obtains actual primary geometry/projected
bins from the fresh workflows; historical equal hashes do not substitute
for downloading their bytes. Partial failure preserves the new output.

The packager verifies the closed full collection, records deterministic
compression identities, copies historical packets and frozen source/reference
bytes, and closes its immutable evidence inventory. Its portable verifier
checks archive identities and report coverage without requiring future
development working files to remain frozen. Large raw inputs are identified
by their actual-byte hashes and retrieval provenance, not included here.

At preparation time, the sources have been syntax parsed and inspected.
The complete collector's readiness guard read the actual pending plans,
returned exit 2 and created no output. No downstream complete-input
collection, packaging or portable verification was executed. Source review
has identified the repairs above; final numerical-output review is pending.
The standalone physics collector and unchanged
numerical reducers have already been used on partial fresh observations;
those uses do not validate the new complete archive path.

## Metadata regression execution

`prepare_metadata_reana.py` prepares a separate source/import preflight and,
after its actual successful downloaded result, one REANA workflow per named
metadata unittest. The source package uses committed Git blobs and rejects
working changes in the packaged paths. It includes the host tools and the
two historical reference packets, with exact hashes. It contains no access
credentials and runs no scientific evolution. Each job declares one CPU,
2 GiB memory, a 180-second child timeout and single-thread library settings;
the runtime report records visible CPUs and cgroup limits separately.

After the repaired tools and their metadata tests are committed:

```sh
python3 tools/m1_evidence/prepare_metadata_reana.py snapshot \
  --output results/m1_archive_metadata_source_20261122
```

Submit that directory's `preflight` plan with the unchanged
`scripts/reana_cases.py submit --directory ... --client ...` action. The
client adapter path must be absolute because submission runs inside each
case directory. Download the actual preflight's `outputs/` files and retain
its workflow/status and transport receipts. Then prepare the independent
case plan:

```sh
python3 tools/m1_evidence/prepare_metadata_reana.py cases \
  --snapshot results/m1_archive_metadata_source_20261122 \
  --preflight results/m1_archive_metadata_preflight_download/outputs \
  --output results/m1_archive_metadata_cases_20261122
```

Submit all ready case workflows concurrently through the same submit action.
`reana_metadata_job.py` verifies every uploaded/source byte, runs the selected
test in a child process, rejects skips/expected failures, and exports the
test result, command outcome, logs and runtime with hashes. An optimized
interpreter is rejected. Metadata success cannot accept M1 or substitute for
running the repaired complete collection on the real finished physical data.
These two new runner files have only been source/AST inspected locally;
their preflight, regression cases and complete execution remain unperformed.

Add the separate output review beside `evidence/`, pin its manifest, close a
separate reviewer inventory, then close the final outer archive only after
the coordinator resolves every required finding. Preserve each original
review byte. No utility success is a substitute for that review or an
explicitly scoped M1 acceptance record.
