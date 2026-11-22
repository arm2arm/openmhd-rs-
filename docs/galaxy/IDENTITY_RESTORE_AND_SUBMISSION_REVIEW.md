# Checked restoration and preflight submission: independent source review

2026-11-22. AI source review of the root-authored changes at `c5c3417` (identity)
and `01c0534` (submission wrapper). No code, imports, tests, formatter, compiler,
network request or workflow was executed. This reviewer authored the preceding
`bba2db5` review and is separately authoring the native pipeline described in
`NATIVE_CASE_IMPLEMENTATION.md`; that pipeline is **not independently approved
by this report**. Scoped M1 acceptance remains closed and unchanged.

1. **Prior finding 1: resolved at source level, conditional on the documented
   complete-import contract.** In `crates/galaxy-types/src/identity.rs:428–455`,
   `CounterCursor::from_checked` first checks namespace role, then takes the
   maximum counter over the inclusive namespace range. Lexicographic
   `(namespace,counter)` ordering makes this exactly that namespace's high-water
   counter, including sparse and retired entries. `Some(n)` is rejected when
   `n <= max`; otherwise it is strictly above every imported issued counter.
   No arithmetic increment is used in the check, so maximum counters cannot
   overflow. `None` conservatively retires the stream, even early. Empty
   namespaces permit every `u64` starting counter, including zero and maximum.
   The shared immutable registry reference cannot be mutated by this operation.
   The entity and event entrypoints at lines 511 and 572 select the correct
   namespace roles. Wrong roles are rejected even for exhausted checkpoints.

2. **Caller obligations are now accurate.** The raw constructors remain
   unchecked (`identity.rs:495–510,557–571`); their representability is distinct
   from coherent restoration. `IDENTITY_IMPLEMENTATION.md:116–137` requires all
   issued IDs/tombstones before checked restoration, one authoritative allocator
   per namespace, and rechecking after further imports. An incomplete registry
   or a second independent allocator can invalidate monotonicity; the API does
   not claim to detect that external misuse. This is an explicit interface
   contract rather than an unimplemented completeness certificate. There is no
   new prohibition on any namespace/counter payload.

3. **Written tests support the correction; execution remains absent.** The
   three new selectors cover sparse real/event high-water rejection and
   continuation, maximum/exhausted states, opposite namespace roles, empty
   namespace endpoints and unchanged registry snapshots on failure. Inert
   source comparison confirms all original 23 test function bodies are
   byte-identical and the new total is 26. The sparse controls distinguish
   previously unoccupied stale cursors from already occupied ones. These are
   source observations, not 26 passing tests. Formatting, compilation, strict
   Clippy and each independent REANA leaf remain required.

4. **Submission wrapper supported, with exact declaration scope.**
   `scripts/prepare_galaxy_reana.py:27–53` derives two serial pinned-image steps:
   preparation followed by fixed `galaxy-source-preflight --jobs 4`. Each has
   CPU request/limit `4` and memory **limit** `8Gi`; it does not declare a
   separate memory-request field or prove actual cgroup enforcement. Inputs
   exactly include `snapshot.json`, bootstrap and every source/bundle part.
   Lines 57–86 reject a changed base specification and bind the actual derived
   specification hash in the original top-level snapshot, recording the base
   hash separately. Source/archive digests and the original source versus
   compact export revision distinction are preserved. The selected source's
   historical `reana.yaml` blob is not relabelled as this derived submission.
   There is no self-hash requirement on `snapshot.json`. The three written
   metadata controls exercise declarations, preserved source/archive pins and
   changed-base rejection; all remain unexecuted.

No demonstrated new source blocker was found in these two small root deltas.
They are suitable for coherent source integration and independent REANA
preflight, not component acceptance. Geometry repairs, the gravity review,
native caller/pipeline review, exact final catalog and case preparation,
authoritative acquisition, each actual debug/release leaf and independent
output review remain separate prerequisites. No 3D, gravity, ISM or merger
acceptance follows.

Exact retained Git blobs and the inert comparison receipt are under
`results/galaxy_native_case_source_20261122/root_review/`; the companion JSON
pins every reviewed byte and this report. Two earlier filename-discovery
attempts referenced nonexistent `reana_metadata_transport.py` and
`reana_adapter.py` and exited 2; corrected reads used the actual
`reana_metadata_readonly_adapter.py`. Batched source output was also truncated
and the relevant sources were reread in smaller sections. Neither observation
is a test or scientific failure. New implementation-source checks are reported
separately and do not expand this independent recommendation.
