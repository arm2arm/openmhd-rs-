# Finding6: selector scope clarification only

1. Renamed the existing ordinary direct selector
   `test_recover_python_catalog.RecoveryMetadataTests.test_retained_tree_copy_preserves_partial_and_rejects_change`
   to
   `test_recover_python_catalog.RecoveryMetadataTests.test_retained_tree_copy_preserves_partial_and_rejects_existing_destination`.
   The body preserves partial bytes and an empty directory, rejects a second
   copy into an existing destination, then compares two tree descriptions after
   modifying the retained file. It does **not** exercise an in-flight source
   mutation or `copy_tree`'s final generation-change rejection. No regression
   proof for that unexercised branch is claimed.

2. The revised test is an exact one-line name substitution. Its complete body
   bytes/AST and all21 other methods are identical; the whole module AST is
   identical after restoring the original name. Prospective controls remain22,
   all unexecuted. There is no new suite or production behavior. `before/`
   retains the exact reviewed original test; the root-level test is its complete
   proposed replacement and the unified diff records the entire change.

3. Integrate the revised test with the **reviewed original** production
   `recover_python_catalog.py` (45290 bytes, SHA256
   `f98437cea91a40a54c529d6607301e3e0ba7e4f1f3922392b5a9cbd24016c78a`)
   and its exact four `reading/frozen_tools/` fixtures. Those bytes remain in the
   sealed original20-body proposal; this small revision references and checks
   them without duplicating or editing that packet. The original production
   guard/generation, retry/whole-case selection, unknown history, offline
   verification and failure semantics are unchanged.

The independent finding is `REVIEW.md`, finding6/T265–279, in
`results/galaxy_python_catalog_recovery_source_review_20261122/`. Its61-body
closure and the original20-body closure are checked before and after this
revision. Exact report/source/helper hashes, source AST/body comparisons and
all22 revised selectors are in the accompanying receipts. `inspect_revision.py`
is this author's inert text/AST/JSON/hash/Git construction/checker, not a target
import or an inspector supplied by another author. No target/test/mock,
network, runtime, acquisition or workflow action occurred. Inspection errors,
if any, are separately retained; source checks are not passing tests.

Root may directly integrate this narrow clarification with the independently
reviewed original without another abstract machinery review. Actual immutable
import capability, individual resource-declared REANA methods and authentic
recovery/output verification remain separate requirements. Original175
workflows are never rerun by this revision. Scoped fixed/rigid2.5D M1 acceptance
is unchanged; no new static3D/G1/deforming nonzero-MHD/live-component merger
acceptance follows.
