# Read-only M1 evidence tools

These host utilities collect, reduce and freeze existing REANA outputs.
They submit no numerical workflow, evolve no state, build no code and
cannot accept M1. The scientific source, registered cases and numerical
reducers remain unchanged. See [the archive plan](../../docs/M1_FINAL_ARCHIVE_PLAN.md).

Use the repository root as the working directory and fresh output paths.
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
collection, packaging or portable verification was executed. Independent
review remains pending. The standalone physics collector and unchanged
numerical reducers have already been used on partial fresh observations;
those uses do not validate the new complete archive path.

Add the separate output review beside `evidence/`, pin its manifest, close a
separate reviewer inventory, then close the final outer archive only after
the coordinator resolves every required finding. Preserve each original
review byte. No utility success is a substitute for that review or an
explicitly scoped M1 acceptance record.
