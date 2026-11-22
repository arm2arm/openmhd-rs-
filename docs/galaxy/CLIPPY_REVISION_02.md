# Observed control-loop Clippy repair, 2026-11-22

Full preflight03, `openmhd-galaxy-build-c0ace2e0f517-a03.1`, UUID
`39d3da01-c9d5-42e8-8ffb-8ecca464b862`, used source
`98ee64bd8b9287e1ede05d208de983f7fda69c6f`. Its actual Rust 1.85.1
`cargo fmt --check` returned 0; strict Clippy returned 101 on the single
`needless_range_loop` diagnostic at
`crates/moving-mesh/tests/geometry3_controls.rs:53:18`. Release build,
debug/release no-run, discovery and test methods did not run. Both original
5,903-byte Clippy downloads have SHA256
`d10d99ae613b7e6d3c30825d3d75aab421a100f8a89e1220e6f01215aaa1d145`.

The only Rust edit replaces `for a in 0..3` with
`for (a, shift) in translation.iter().copied().enumerate()` and replaces
the one `translation[a]` operand in `expected_c` with `shift`. `Vec3` is
`[f64; 3]`: the iterator visits indices 0, 1 and 2 in the same order and
copies the same scalar. The inner matrix traversal, indexed vector operands,
arithmetic grouping, additions, formulas, tolerances, comments and quoted
literal bytes remain unchanged. The explicit range-bound tokens 0 and 3
leave the loop header; no formula or threshold literal changes. There is
no lint suppression, new selector, dependency or production algorithm change.

The existing two-line `expected_c` assignment is retained; its expression
line is now 80 columns. This is source inspection, not a measured Rustfmt
result. The complete old-to-new source identity is:

| Generation | Bytes | SHA256 |
| --- | ---: | --- |
| Git/snapshot preimage | 13,370 | `44132ce287b174ef7b415ddba6dcbb55c3f44eedba85d17744fa46e84d72c617` |
| Applied candidate | 13,405 | `bf1a66b2e80432a902ee79fc5356443ae7b4ea36fb4629f69ed8018a20cda3e6` |

The exact preimage matched both Git and the original selected-source pin
before application. Retained byte/diff and lexical checks, source-only
reverse-patch and whitespace checks, and ordered source-name inventories
preserve all 98 registered scoped Rust selectors, including all 17 in this
file. The other six scoped Rust source buffers are unchanged. The original
181-body attempt03 execution boundary and its manifest remain byte-identical
(manifest SHA256
`62af21da63071dd98f067fd523e25c61c636dc321807c10ab1421e11d9062d91`).
Receipts, original/candidate buffers, the complete diff and selector lists
are retained in
[the repair boundary](../../results/galaxy_clippy_control_repair_20261122/).

Root's concurrent Python/reference-helper integration, including its
100-to-114 selector-policy generation, is outside this Rust repair and is
preserved. After the repair's source checks closed at `98ee64b`, root
committed that separate integration at
`d3899ffb238d4f82f6544c2351591a08dd7ec227`; the owned Rust edit remained
uncommitted with the same preimage and candidate. It is not part of the old
preflight03 source generation; no
whole-worktree cleanliness or unchanged-Python claim is made. No local
formatter, compiler, target import, test, mock, reference calculation or
REANA action was performed for this repair. No repaired preflight pass is
claimed. Root review/commit and a fresh coherent REANA format, strict-Clippy,
build, no-run and discovery prerequisite remain mandatory before dependent
cases. M1's accepted fixed/rigid 2.5D scope is unchanged; static geometry,
G1, deforming 3D MHD and the full live-component merger remain unaccepted.
