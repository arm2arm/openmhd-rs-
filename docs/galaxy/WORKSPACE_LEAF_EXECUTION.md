# Source-layout Rust test execution

The remaining full-workspace execution gap is 490 profile-specific leaves:
676 actually compiled/listed debug/release leaves less the separately executed
186 component leaves. This is a coverage gap in the current evidence, not a
claim that these methods have never run historically.

Eight restart leaves use Cargo's compile-time `CARGO_BIN_EXE_vector-potential`.
An exported libtest executable alone does not preserve that application path.
The existing [exported-binary runner](../../reana/galaxy_test_case.py) retains
its explicit portability restriction.

The new [workspace runner](../../reana/galaxy_workspace_case.py) prepares the
same frozen source layout with the unchanged REANA bootstrap, rebuilds only
the selected target without running methods, compares the resulting libtest
listing with the actual parent catalog, then runs one exact leaf. For a
restart target it requires Cargo's actual non-test `vector-potential` artifact
and records both executable digests before and after the test. No scientific
Rust source, assertion, tolerance or default changes.

The separate build-input parent contains all 205 original Rust/Cargo/toolchain
files, two literal compiler fixtures and the two unchanged bootstrap/preflight
sources: 209 files, each byte-identical to the passing Rust05 generation.
Its private one-commit bundle is an explicit input fixture, not project history.
The parent runs format, strict Clippy, release build and debug/release compile
and discovery with zero methods. Its logical catalog must match the original
676-leaf catalog. The large exported binary archive is not needed by this
source-rebuild route; metadata/log acquisition does not claim to verify that
unacquired archive.

Each numerical test gets its own REANA workflow: four build jobs, one libtest
thread, 8 GiB declared memory and a bounded 1,800-second wait per command.
The actual machine/cgroup observations remain separate from declarations.
Compiler selection uses absolute installed Rust1.85.1 paths and the scalar
Cargo configuration form validated by the standalone driver build. Inherited
Cargo/Rust target, wrapper and flag overrides are removed. Each compiler,
build, list and test command uses the unchanged held-leader supervisor.

The ordinary eight-output capsule retains every stage's command and raw logs,
the original bootstrap runtime, actual Cargo artifact messages, tool and binary
hashes and the one-leaf witness. Failed or uncertain stages do not pass; an
escaping supervisor retains its pending/unknown evidence. All required input
and source bytes are checked again after the leaf. A failed capsule cannot be
relabelled as complete by acquiring only its successful files.

The original eighteen direct metadata controls passed as separate REANA
workflows. The source-layout parent also completed format, strict Clippy,
release build and compile/list discovery, with zero test methods. Its 464
metadata/log artifacts were acquired and checked; the binary archive was not.

The first numerical release exposed a runner defect before any compiler/test
stage: the metadata reader's 16 MiB limit was applied to the 35,341,752-byte
Cargo executable. The original submission closed with 118 acknowledged,
three uncertain and 369 stopped-before-submission entries. Actual failed and
stopped workflows remain failed or stopped. Stop requests that the server
rejected for queued/created jobs are retained; these are not successful stops.

The correction retains the 16 MiB metadata limit and gives compiler, Cargo
and test/application executables a separate 128 MiB limit at both read fences.
That generation contained twenty-one direct
[metadata controls](../../scripts/test_galaxy_workspace_case.py), including
inert files with Cargo's actual recorded length, a same-length tool mutation,
and the metadata/executable upper bounds. The corrected generation at
`1b734a213d05ad067fd61725c72862122b4d972e` passed its actual import-only
preflight and all twenty-one independent REANA controls. The complete original
capture and separate offline verification returned zero. Root retained-byte
review checked 3,981 relations without errors; the author/root review is
disclosed and does not claim a delegated independent review.

The original twenty-acknowledged/one-uncertain submission stays unchanged.
The uncertain case kept its original UUID: only its missing original `job.py`
was uploaded, all seven actual input digests matched, and one UUID-only start
succeeded. No control was rerun.

The corrected Rust release uses distinct workflow names. The ordinary
`field-loop` leaf passed. The restart build succeeded, but the runner rejected
its normal `vector-potential` executable before list or test invocation; the
other 488 leaves remain held. The actual restart executable is 86,220,496
bytes, below the 128 MiB bound. Its failed capsule pins the libtest executable
and retains both successful compiler/build stages. It supplies no passing
restart result.

The remaining rejection is attributed to the reader's single-link condition.
[Cargo's Rust1.85 branch](https://github.com/rust-lang/cargo/blob/rust-1.85.0/src/cargo/core/compiler/mod.rs#L527-L549)
documents hard-linking root outputs from `deps`. The original capsule does
not record the rejected file's link count, so this is a source-supported
diagnosis. A separate read-only stat workflow could not see the old workflow's
filesystem and supplies no inode evidence.

The new correction permits hard links only in generated Cargo target-file
reads. Metadata, source inputs and tool reads keep their single-link rule.
Each selected test/application executable now records device, inode, link
count, size and timestamps from its held descriptor; the post-test fence
requires that exact identity and content hash. Symlinks and oversized files
remain rejected. Four additional direct controls cover a linked executable,
mutation through its alias, strict input/tool rejection and target size/link
guards. The correction at `614c2040f851acfd76ed5a91f5d44a68dc759cfd`
passed its actual import-only preflight and all twenty-five controls as
independent REANA workflows. The original packet has 25 passing leaves,
200 artifacts and 250 successful UUID-linked transports; collection and the
separate offline verification returned zero. Root checked 4,669 retained-byte
relations including the reading closure, with no errors. This is disclosed
author/root review, not a delegated independent review. The original
24-acknowledged/one-uncertain map and same-UUID missing-input recovery remain
unchanged.

The two new Rust canaries also passed: the ordinary `field-loop` leaf and
`cli_resume_is_self_contained_and_preserves_schedule`. Their actual Cargo
records include the restart application's 86,220,496 bytes and link count two.
The libtest and application hashes and held file identities agree across the
test fences. Both eight-output capsules, their terminal same-UUID observations
and the 866-check root review are retained. These actual records demonstrate
the corrected reader handling a Cargo root-output hard link; the rejected old
file's original link count remains unmeasured.

The remaining 488 leaves use their own distinct workflows from the same
released generation. The single submission settled with 480 acknowledged and
ten uncertain entries, including the two original canaries; no row remains
pending. The ten uncertain cases retain their original unique version-one
UUIDs. Nine used missing-input repairs; case0059 instead retained a truncated
`parent/commands.json`, verified it as an exact prefix of the original, and
replaced only that file. All nineteen actual inputs matched before each
workflow's single first start. The original uncertain submission rows remain
unchanged. No test method was rerun.

The source fence closed with all 306 tracked source-member pins and all 9,310
staged input files unchanged. These are launch and provenance results, not a
complete 490-pass claim. Final results require complete acquisition and output
review. Scientific Rust sources and all test assertions remain unchanged.

The old generation's last retained inventory has 22 failed, 96 stopped and three
intentionally unstarted created workflows; the original submission and all
failed stop attempts remain preserved.

See [the retained checkpoint receipts](results/workspace_leaf_20261123/README.md).
This document grants no G00, 3D geometry, gravity, moving-MHD or merger
acceptance. Scoped M1 is unchanged.
