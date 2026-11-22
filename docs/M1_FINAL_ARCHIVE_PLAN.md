# Final M1 evidence and review archive boundary

2026-11-22. **Prepared workflow; complete-input execution, separate final
output review and M1 acceptance remain pending.** This implements the
packaging sequence of [the acceptance plan](M1_FINAL_ACCEPTANCE_PLAN.md),
without changing scientific source, numerical thresholds or execution policy.

The provisional packet at `tests/reference/m1_acceptance/` remains immutable:
its 69-entry parent inventory pins the separately closed nine-file source-review
subpacket. It must not acquire new unlisted files or have its historical
review rewritten. Its verifier intentionally checks the current working tree
against M1 while that candidate is under review. This is appropriate before
M1 acceptance, but is not a perpetual requirement that later M2 development
leave every scientific working file frozen.

## Freeze actual completed evidence first

Wait for the existing supervisor's final registered verdict. Then run the
prepared read-only [prepare_final_evidence.py](../tools/m1_evidence/prepare_final_evidence.py)
with a new `--output` directory. Its required inputs are all 214 completed
cases, seven passing phase checks, pinned preflight binary/source identities,
unchanged registered specifications, all four strict phase verifications and
all six independent reductions. The reductions cover 99 boost pairs, eight
spatial ladders, twelve temporal comparisons, twelve primary shocks and six
primary vortices. Temporal orders remain observations. Its 238 raw inputs
are 214 final CSVs, eighteen primary geometry files and six projected-bin files.
Missing inputs or failed gates cannot produce a successful complete collection.

The second prepared host utility,
[pack_final_review_evidence.py](../tools/m1_evidence/pack_final_review_evidence.py), takes
that complete collection with `--input` and a fresh immutable `--output`
ending in `evidence`. It verifies the complete original inventory before
copying selected reports, receipts, plans/specifications/checkpoints, command
logs and exact analysis sources. JSON compression uses gzip mtime zero and
records both original and stored byte identities. Large actual raw files stay
in the original local/REANA artifacts; this archive explicitly retains their
identities and workflow retrieval provenance, not a claim that it contains
their bytes. The independent projected vortex bins are included.

It also copies the unchanged provisional packet and complete historical A/B
archive into separate labelled directories. Frozen scientific source is read
from Git revision `2bdcea0d28340e7429e10053a641f92d51fcc696` and checked against
the submission snapshot, including all 226 scientific/configuration files,
the toolchain and retained external-reference files. These historical bytes
are stored, so later development is not confused with a changed M1 candidate.
The current review-context documents are separately labelled. This is an
evidence export, not a claim that a relocated source-review script or partial
source layout is a standalone build environment.

Its copied `verify_final_review_evidence.py` checks the closed inventory,
encoding/original hashes, historical source catalog, completed phase coverage
and report-level gates without depending on the development working tree.
It is a consistency verifier, not an independent rerun of every numerical
operator or a replacement for the separate reviewer. At preparation time,
the sources have been syntax-parsed and inspected. The collector's readiness
guard read the actual pending plans, returned exit 2 and created no output;
downstream full-input collection, packaging and portable verification remain
unperformed.

## Keep review and acceptance outside the reviewed evidence

Use a new sibling final packet, provisionally
`tests/reference/m1_final_acceptance/`, rather than adding files inside the
old closed provisional packet. Its intended structure is:

```text
evidence/sha256.json            # closes all implementing-agent evidence
evidence/...                   # immutable after the review begins
review/review_sha256.json       # closes every separate-reviewer file
review/...                     # report, reviewed-byte identities, receipts
acceptance.json                # coordinator writes only after all gates/review pass
archive_sha256.json             # final outer closure
```

The separate AI output reviewer pins `evidence/sha256.json`, checks the exact
fresh numerical outputs and relevant scope/limitations, and closes its own
review subpacket. It never edits the evidence it is reviewing. The final
outer inventory pins both nested manifests, the acceptance record and other
outer payloads; its verifier must also reject extra or missing files inside
each nested boundary. Do not make a review hash depend on an outer manifest
that in turn depends on the review: the dependency is evidence, then review,
then acceptance/outer closure. No circular self-hash is permitted.

The outer acceptance record must identify the exact configuration, source,
binary, immutable evidence and reviewer manifests, report any resolved
findings, and explicitly scope acceptance to the single-process periodic
fixed/rigid 2.5D engineering reference. The default profile's historical
failures, smooth-extrema tradeoff, and lack of deforming/3D/MPI/local-step/
paper-equivalence acceptance remain visible. Archive verification alone
cannot write this record or accept M1. Update the current status and roadmap
only after this sequence and the separate review actually succeed.
