# Unintegrated offline-dependency candidate

`locked_dependencies.py` is proposed for `reana/locked_dependencies.py`.
`test_locked_dependencies.py` is proposed for
`scripts/test_locked_dependencies.py`. The test's repository-relative import
targets that eventual layout; this retained proposal directory is not an
executable test installation. All eight methods remain unexecuted.

`prepare_locked_dependency_bundle.py` is the operator script actually used to
download and checksum the 80 lock-selected archives. It requires Python 3.11
for the standard TOML reader. It does not build or execute package contents.
The actual bundle, three parts and original transport receipts remain under
`results/workspace_locked_dependencies_20261124_attempt01/` in the main checkout.
The receipt copy in this checkpoint deliberately excludes the archive bodies.

The original source-only inspection predates the added coherent descriptor
reads and Cargo-directory symlink rejection. Its original source hashes remain
historical. `static_review.json` and the outer file inventory describe the
current retained candidate; no later import or passing test is implied.

A future REANA workflow would run the existing source/toolchain preparation,
then this installer with the explicit bundle SHA256, then the unchanged
workspace runner. It would have new input/specification identities. Actual
import/control results and offline ordinary/restart build canaries must pass
before releasing a replacement numerical batch. Original failures and
uncertainties stay attached to their original workflows.
