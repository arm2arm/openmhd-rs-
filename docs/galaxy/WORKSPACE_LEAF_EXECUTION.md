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

Eighteen direct [metadata controls](../../scripts/test_galaxy_workspace_case.py)
are written for the new route. They use inert byte fixtures and no actual
compiler or numerical method. At this source checkpoint they are **unexecuted**;
a new immutable import-only parent and separate per-method REANA executions
must precede release of the 490 Rust leaves. The source-layout build parent
is also a prerequisite, not an assumed pass. This document grants no G00,
3D geometry, gravity, moving-MHD or merger acceptance. Scoped M1 is unchanged.
