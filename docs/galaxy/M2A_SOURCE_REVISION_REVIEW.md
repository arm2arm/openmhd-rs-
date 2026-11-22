# Independent review of the three narrow static-geometry repairs

2026-11-22. The coordinator reviewed the complete four-file revision against
`ba49c54dca152505ce42e29e60ff32013ca2fa87` and the three findings in
[M2A_SOURCE_REVIEW.md](M2A_SOURCE_REVIEW.md). The coordinator did not author
these Rust changes. The revised source addresses all three findings within
their original scope. Actual compilation, formatting, lint and numerical
results remain unobserved; this review releases source for the required REANA
preflight, not geometry acceptance.

1. Both failing format witnesses now use `CellId::entity()`, whose existing
   `EntityId` return type implements the canonical `Display`. No ID API or
   production geometry changes were introduced.
2. The extended arithmetic control constructs an odd two-limb integer
   `2^64-1` before multiplication and checks both its representation and its
   square. For base `B=2^32`, the independently expanded square
   `(B^2-1)^2 = 1+(B-2)*B^2+(B-1)*B^3` gives the asserted little-endian
   words `[1,0,B-2,B-1]`. Subtraction from `2^128` requires four-word borrow;
   adding a half then tests alignment and subsequent carry. Negative finite
   subnormal and ordinary-value decoding now have explicit assertions. These
   are useful written controls for the previous coverage gap; their answers
   were checked by manual integer algebra, without evaluating the candidate.
3. Every changed area assertion uses the same positive analytic expected
   area as its denominator. The expected expressions and `1e-10` threshold
   are preserved. This matches the specified reference-relative gate.

The root source receipt is
`results/galaxy_goal_tools_20261122/m2a_narrow_revision_root_review_20261122.json`.
All four delivered identities match, all 28 lexical test selectors are
unchanged, and the complete `exact.rs` production prefix before its test
module is byte-identical. Owned-path `git diff --check` passed. The reviewed
current source identities are:

| Path | Bytes | SHA256 |
| --- | ---: | --- |
| `crates/moving-mesh/tests/geometry3_analytic.rs` | 10100 | `495e23c19f6c9cd14a497da41a969ac50772098722430b0fc6ca17869f94efea` |
| `crates/moving-mesh/tests/geometry3_controls.rs` | 11686 | `ef7d40cf829ddbb64e997d300c9789c8b21d582a59eebdfd8300b24b6e87805c` |
| `crates/moving-mesh/src/three_d/exact.rs` | 12372 | `82a24b4a5481695d8a68400bc7a3926472d9219622cf00f43c256443420e285b` |
| `docs/galaxy/M2A_IMPLEMENTATION.md` | 27057 | `4f44720ba0ab929aac74f4275a8fa7a87d2118002038606e562435dac78a5b07` |

No Rust parser, compiler, formatter, linter, test discovery, test, reference
calculation or workflow ran in this review. The original review's conversion,
conditioning, transformation/reference and resource limitations remain.
Immutable REANA preflight, each independent method, exact input/reference
comparisons and independent output review are still required. Scoped M1
acceptance is unchanged; moving 3D MHD and merger gates remain open.
