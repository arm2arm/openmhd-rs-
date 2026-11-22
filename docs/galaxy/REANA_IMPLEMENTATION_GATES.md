# Execution of the first post-M1 implementation slices

M1 scoped acceptance is complete at `309ae41`. Identity, static 3D geometry
and collisionless direct gravity are separate new components. Written source,
tests, successful compilation and test inventories do not accept those components.

The `galaxy-source-preflight` study in `reana/remote.py` uses the existing
checksum-pinned Rust 1.85.1 bootstrap and environment image. It requires format,
strict all-target/all-feature Clippy and a release workspace build. Its final
command runs `reana/galaxy_preflight.py` **on REANA**. That command compiles debug
and release all-target/all-feature tests with `--no-run`, records Cargo's JSON
artifact messages, and calls each compiled libtest executable with `--list`.
No test method runs in this preflight. No numerical source/kernel/reference
evaluation is authorized locally by this harness.

The exporter binds each exact leaf to its build profile, package manifest,
target/source, executable SHA256 and frozen snapshot/source inventory. It retains
compile/list stdout, stderr and command records, rejects ignored tests pending
explicit disposition, checks source identities before and after, and exports
the actual executables plus catalog. A failed/interrupted preflight retains a
failed report and cannot release dependent cases. External infrastructure loss
still needs authoritative workflow/status/log receipts; command timeout metadata
does not certify descendant cleanup or a successfully finished workflow.

Prospective preflight resources are four CPU threads, 8 GiB and 30 minutes per
compile command, with `RUST_TEST_THREADS=1`, `RAYON_NUM_THREADS=1` and FFI threads
one. The submission YAML must explicitly declare these resources, and actual
visible CPUs/cgroup limits must also be retained. The ordinary legacy YAML's
resource declarations must not be mistaken for this new study's final declaration.

After coherent source review and a real passing preflight, every selected test
leaf gets its own workflow using the exact exported executable and `--exact
--test-threads 1`. Release requires exact catalog coverage, actual one-leaf
execution with no ignored/failed test, snapshot/binary/case identities, terminal
server observation, complete logs and independent output review. Physical
geometry/gravity gates additionally require their independently frozen literal
oracles, norms and convergence evidence; passing a unit leaf is insufficient.
The ten written `GalaxyPreflightMetadataTests.test_*` controls in
`scripts/test_galaxy_preflight.py` cover exact/duplicate selectors, rejection of
benchmark/execution output, frozen-byte replacement and path/link escapes,
Cargo target identity, successful build completion, duplicate targets, binary
escapes and empty-catalog rejection. Their fixtures are inert, labelled synthetic
metadata; they contain no numerical results and never execute Rust. These new
controls also require separate REANA execution. No workflow, test or preflight
has been run by writing these files.

Primary API references consulted for this harness are the
[Cargo JSON-message specification](https://doc.rust-lang.org/cargo/reference/external-tools.html#json-messages)
and [rustc libtest options](https://doc.rust-lang.org/rustc/tests/index.html).
The attempted Rust 1.85.1 documentation URLs were unavailable through the web
tool. The exact Rust 1.85.1
[console discovery source](https://github.com/rust-lang/rust/blob/1.85.1/library/test/src/console.rs)
and [terse formatter](https://github.com/rust-lang/rust/blob/1.85.1/library/test/src/formatters/terse.rs)
were then inspected: the terse discovery path prints one `name: test` line per
leaf and no summary footer. Actual compatibility with the pinned compiler
remains a required REANA observation.
