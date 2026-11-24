# Offline inputs for the unchanged Rust workspace

Three inspected original490 failures timed out while Cargo fetched dependencies,
before list or leaf execution. The original failed workflows and their source
remain unchanged. This helper addresses dependency acquisition only; it changes
no Rust implementation, test, threshold, lockfile or compiler selection.

`reana/locked_dependencies.py` installs the checksum-verified crates.io archives
from the actual frozen `Cargo.lock` into a private Cargo directory source. It
checks the explicit descriptor digest, complete bounded parts, whole archive,
lock, exact package inventory, package checksums and safe regular member paths.
It generates Cargo's per-file checksums and offline configuration, retaining
original package files and the installation/configuration hashes in the prepared
runtime. It does not invoke Cargo, a build script or a crate.

The original input preparation downloaded all 80 locked archives successfully.
The 7,557,120-byte bundle has SHA256
`08b62e8ceb5328799679f6ccfea312722b44bdfbb39d48c0d88c24bcdb254d2c`;
the unchanged lock has SHA256
`bf66aca946318a2ae19b48ab6a65462ee0fe756e35fd4e746c7945253a0d792e`.
The archives remain external under
`results/workspace_locked_dependencies_20261124_attempt01/`.
The [earlier checkpoint](VALIDATION_CHECKPOINT_20261124.md) retains the initial
source proposal and download receipts.

Eleven direct `LockedDependencyTests` methods cover successful materialization,
altered descriptor/lock/parts, traversal, links, duplicates, existing Cargo
selection, pre-read size bounds and registered cohort boundaries. They must run
individually on REANA after a real import-only parent. The existing Python
pipeline now supports two exact whole-suite cohorts: its original `integration`
default and `locked-dependencies`. Arbitrary file subsets remain invalid. For
the new source generation:

```sh
python3 scripts/prepare_galaxy_python_reana.py snapshot \
  --cohort locked-dependencies --output <fresh-source> --prefix openmhd-offline
```

Acquisition and offline validation use the frozen snapshot's declared complete
cohort. Source, payload, certificate, command, cleanup, transport and full-case
coverage checks remain required. The original216 execution uses its separately
retained exact original four host helpers; later validators must not replace
those original bytes.

At source integration, all eleven methods and the installer remain unexecuted.
Actual import/method/output evidence and offline ordinary/restart canaries are
required before any new Rust campaign. No failed original result is upgraded,
and this change grants no component or merger acceptance.

The [2026-11-24 actual output checkpoint](RESTORED_OUTPUT_CHECKPOINT_20261124.md)
now closes the eleven-control import/execution/acquisition/offline prerequisite:
all eleven passed, and a relocated copy also verified successfully. Two new
ordinary/restart offline-build canaries have received one verified-input first
start each. Their actual build and output review remain pending; the historical
source-integration status above is preserved.

Both [actual ordinary/restart offline-build canaries](OFFLINE_BUILD_CANARY_RESULTS_20261124.md)
have now passed with complete terminal output capsules and matching actual
configuration/installation records. Wider release still requires closure of
the original merged-source216 prerequisite and its full output review.
