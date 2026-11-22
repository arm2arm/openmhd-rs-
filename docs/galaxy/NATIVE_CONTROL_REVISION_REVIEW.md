# Narrow source review of two native metadata controls

2026-11-22. The coordinator read the complete two-method diff against
`abdfe47188dec67d880ff821562dc176b925f084`, the corresponding production
control flow and the author's delivery receipt. The coordinator did not author
these changes. Findings 3 and 4 of
[the independent pipeline review](NATIVE_PIPELINE_SOURCE_REVIEW.md) are
addressed at source level. All new execution remains REANA-only.

1. The escaping-supervisor callback records the published intent/runtime,
   actual arguments and a marker before its intentional `RuntimeError`.
   Assertions now run after `native.run` returns. They require the complete
   pending intent, exact fixture hashes, runtime and arguments, and the
   specific exception type and sentinel retained by `run`. A swallowed
   `AssertionError` or failure before the intended raise cannot satisfy those
   outside checks. Existing unknown-closure and nonacceptance checks remain.
2. The native-schema negative retains both incomplete-input controls and adds
   exactly eight inert bodies with the matching seven-body artifact map.
   Parseable case/payload inputs reach the result discriminator. The old
   unittest schema and the matched native-schema/failed-status control must
   raise the exact `Actual one-leaf native result` error. Neither can pass
   incidentally at the earlier artifact-count guard. No execution, valid
   native packet or successful scientific observation is fabricated.

Only these two method bodies changed; the author's AST/source inventory
retains all 34 selectors and 37 other class methods unchanged. Root read the
complete diff, checked both delivered hashes and ran the scoped whitespace
check successfully. The production native caller, result validator and
supervisor are unchanged. Current test-file SHA256 values are:

- `scripts/test_galaxy_preflight.py`:
  `f6a7b87208d61a31b03f28aef075320055efb235fef511c4086660a7e91491ce`.
- `scripts/test_galaxy_cases.py`:
  `6ae3ae6a99eeb6c2a20080b20bb6f133e482c67bb938fca4a485d0cafa598ccd`.

The full small diff, causal note and source-only receipt are under
`results/galaxy_native_control_repair_20261122/`; the closed 13-body manifest
is `dffa29f859f73c75a2b32eb1fac409b378ab530dc4e825c88741a27ac0011d8a`.
No target import, mock/test, runtime probe, formatter/compiler or workflow ran
in this revision inspection. The coherent source/import preflight, each
actual metadata/native leaf and independent output review remain required.
This closes the two written-control source findings, without granting a
component, moving-3D or merger acceptance or changing scoped M1 acceptance.
