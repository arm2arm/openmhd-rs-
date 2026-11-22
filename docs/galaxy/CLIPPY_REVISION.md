# Observed strict-Clippy loop revision

2026-11-22, source-only. Applied exactly the four candidate files in
`results/galaxy_observed_clippy_repair_proposal_20261122/`, whose twelve-body
manifest SHA256 is `186bf7127c23ac02528874a74c802237ba481d0f4f9a46d39c1ece6cceebb456`.
There is **no passing repaired preflight yet**.

The actual original workflow `openmhd-galaxy-build-d882f8e7dd42-a02.1`, UUID
`52d0060e-5aaa-43c8-b641-ec1a1eb4f20e`, used source `4712d7e` and snapshot
`d882f8e7dd42a1d7ba036b51256897a36b8c816a0ff516df2cd0b30903ea2e9d`.
Rust 1.85.1 format returned **0**; strict Clippy returned **101**. Its complete
6,794-byte log has SHA256
`1a92f9e39687d2def42b14dd156bf21e16369046a9d38a11475b4d894876d15e`.
The fail-fast workflow did not proceed to release build, debug/release no-run
compilation, discovery/export or test methods. The closed original 235-body
execution packet, previous formatter generation, source archives and submissions
remain unchanged.

The six original `needless_range_loop` sites and source reasoning are:

| Original site | Exact rewrite and preserved order |
| --- | --- |
| `clip.rs:250` | Enumerate `planes[..6]`; the sole caller constructs six axis/side planes before calling. Corner intersections already require indices 0–5. The same six support filters, normal references and face/budget operations occur in order; a short inventory is not silently truncated. |
| `exact.rs:141` | Enumerate immutable `large`, copying the same `u32` limbs in ascending order; zero extension, left-associated addition, carry and output sequence are unchanged. |
| `exact.rs:152` | The corresponding borrow loop preserves both left-associated subtractions, sign/zero handling, normalization and all resource bounds. |
| `moments.rs:260` | Enumerate the same `3x3` affine array in row-major order; `Sum: Copy` permits the same consuming `get` through each reference. Successive division/diagonal subtraction/absolute-value/max operations are unchanged. |
| `oracle.rs:314` | Copy each `n[b]` in ascending order; surrounding incidence/component order, accumulator target and left-associated products are unchanged. |
| `oracle.rs:322` | The affine residual retains the same row-major nine `Sum::get` reads and successive max operands. |

No threshold, numerical formula, gate, error branch, dependency, test selector or
lint allowance was changed. Array/slice iteration replaces only indexing-loop
syntax and its index reads. This is manual operand/order/borrow inspection, not
an evaluated numerical equivalence experiment or a compiler result. The reviewer
previously applied the formatting-only generation and executed the original
preflights, but did not author the static-geometry algorithm or this proposal.

Exact source-generation map (paths are under `crates/moving-mesh/src/three_d/`):

| File | Before bytes / SHA256 | After bytes / SHA256 |
| --- | --- | --- |
| `clip.rs` | 11968 / `4c8fe39d8915c2fb596673084bbf681647a6947b62db24b3d568184e3b2d13c2` | 11999 / `00a9f699da69daada553e87fa195b4b98aadded70c055da9000db16047b822dc` |
| `exact.rs` | 13579 / `83297922ce2e009e26be57dac6fb62ff7b62334892a01d81b1d8d815bffb6bdd` | 13609 / `914b194779fc0b0ab32f62b66d077480aeceb562201cd3fd794f3595e9b73f31` |
| `moments.rs` | 11777 / `df9ed630e30d2a6db6a38428284cea73e8a18f572bb62bc0e1d9dc3929969a44` | 11825 / `dd0725771005b3c693a1217fd8650d4b5a61a65b811b3a263e756e714ee216be` |
| `oracle.rs` | 21558 / `8f632cfacbb6a30da6c077154366abb2ddff6c9702a0438713ca8ecb0beb4146` | 21655 / `ee25584937609c06391a12133e91bc7226a4ea65a495b3ea7f8565ae19753ec7` |

Lean receipts are in `results/galaxy_observed_clippy_repair_20261122/`: complete
diff, exact before/after files, manual review and write intent, 55 pre-write
checks plus eight post-write checks, errors=[]. All preimages matched both the
proposal and original snapshot/Git bytes before writing. All 98 scoped direct
Rust source test names retain their order (26 identity, 39 gravity, 28 new
geometry, five existing mesh-library tests); their complete lexical inventory
is retained. All other 4,887 tracked files retained their bytes through the
application, including M1 scientific/archive files and current Python/native
helpers. Parallel coordinator commits were preserved, not treated as a whole
worktree freeze. `git diff --check` passed; no formatter, compiler, tests,
numerical/reference calculation or workflow action was run in this repair.

One formatter-layout uncertainty is explicit: the shortened carry assignment
remains split over two lines although its joined text would occupy 98 columns.
Its exact proposed layout was retained; no formatter outcome is inferred from
that source observation. Root must freeze the coherent source and obtain actual
REANA format/strict-Clippy/build/list evidence before dependent independent
leaves/reference gates. Existing historical source-inspection hashes retain
their earlier meaning. Scoped M1 acceptance is unchanged; static geometry,
gravity, deforming nonzero-MHD gas/live particles, ISM/feedback and the full
galaxy merger remain separately unaccepted.
