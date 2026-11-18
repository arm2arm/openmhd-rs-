# AI review — serial checkpoint/restart

This is a separate **AI review**, performed by the review agent on 2026-11-05. It is not human peer review or M1 scientific acceptance. The reviewer inspected the implementation and ran independent checks; the implementation agent made the production changes. No unresolved correctness blocker was found in the reviewed checkpoint/restart scope.

The review covers the working-tree implementation based on `352636a9733194601ba6faedd5eb9bf057f21531`, identified by the source hashes in the reviewer evidence. It covers `mhd-io`, exact moving-mesh cache persistence, `general::Simulation` checkpoint methods and accepted-step observer, build compatibility metadata, and the `vector-potential` CLI/context/tests. It also checks the claims in [the restart documentation](CHECKPOINT_RESTART.md). It does not approve the ongoing M1 physical-method validation.

## Findings and fixes

| Finding | Severity | Resolution verified |
|---|---|---|
| Distinct valid analysis targets could produce the same eight-decimal CSV filename. The writer then saved duplicate output names, and its own context decoder rejected the restart. | Medium | The CLI rejects collisions before simulation/output creation. The reviewer independently reproduced the original defect with targets `.001` and `.001000001`, and ran the regression test for the fix. Existing noncolliding filenames remain unchanged. |
| A source/compiler fingerprint did not capture every effective Cargo code-generation setting. | Medium for the proposed compatibility guarantee | The format also checks the SHA-256 of the actual executable. Version 1 deliberately requires the saved original binary; source/build metadata remains an additional compatibility check. |
| Decoded diagnostic counters could contain extreme integers that overflow later unchecked increments. | Low; malformed data with a recomputed checksum | Decode/save validation now bounds counters with substantial headroom for the bounded run and restricts auxiliary-grid roots to the implemented choices. |
| Reusing an output directory could leave stale failure/completion artifacts after interruption. | Low | The driver removes those markers before resuming. The actual-process-kill test verifies successful recovery and removal of a stale failure marker. |

Additional implementation hardening inspected includes relative `--resume saved.chk` paths, refusal to overwrite an analysis filename with a restart file, and preservation of the source checkpoint when its name conflicts with regenerated output. The CLI regression tests exercise the relative-path and destination-conflict cases.

## State and continuation audit

The serialized state includes integrated conservative variables, reduced potential, phi, gauge offset, mesh/connectivity, auxiliary origin, configuration, initial reference velocity, conservation baselines and all counters. The accepted state's mesh and cached geometry must match before saving. Linear derivative coefficients, quadratic samples and compact moments retain their exact bits and order; repeated quadratic cell IDs from different periodic images remain valid. Loading does not refit translated-mesh caches.

The observer executes after the complete accepted update, including auxiliary history and counters. It introduces no additional target times. An autosave retains the currently pending analysis target, including when the accepted step lands exactly on that target. Resume can therefore complete its output once without changing the timestep sequence or duplicating history. The CLI stores original initial/output content, so a fresh output directory does not depend on the previous directory or mesh-cache file.

The envelope validates total length, version and SHA-256 before decoding. Nested lengths are bounded by available bytes; tags, finite values, topology/cache shapes, physical primitive recovery and trailing data are checked. The valid infinite configured timestep cap is preserved. Atomic replacement uses a separate file in the same directory; a post-rename directory-sync failure is correctly documented as occurring after replacement.

## Independently performed checks

- `cargo test -p mhd-io -p moving-mesh -p mhd-vector-pot --lib --locked`: **41 passed** (3 I/O, 10 moving-mesh, 28 vector-potential). The continuation test covers all eight profiles, rigid periodic wrapping, fluid and prescribed motion, changed topology, gauge/origin state, unlimited reconstruction and actual rejected trials. Complete final checkpoint bytes agree with uninterrupted evolution.
- `cargo test -p openmhd --test restart --locked`: **4 passed**, including stops between and exactly at analysis boundaries, fresh-directory recovery, completed-file replay, relative resume paths, rejected overrides/corruption, filename conflicts and an actual killed subprocess.
- A separate reviewer subprocess probe compared fixed paper, fixed projected unlimited, fluid projected and prescribed projected runs. Each used a jittered 6×6 mesh, smooth initial data, final time `.03`, maximum timestep `.002`, and analysis targets `.01`/`.02`. Runs stopped at accepted step 7 and resumed with checkpoint cadence changed from 2 to 3. All four finished at step 15. Each of seven artifacts—initial CSV, two analysis CSVs, final CSV, summary, history and polygons—matched uninterrupted output **byte for byte**.

The reviewer used an isolated Cargo target directory. The [compact public evidence archive](../tests/reference/checkpoint_restart/README.md) preserves reproducible probe code, exact commands/stdout, artifact hashes, compiler/platform information and source hashes. The original executable/raw outputs remain under `results/checkpoint_ai_review/`; the archive explicitly records their omitted paths and hashes. The reviewed executable SHA-256 is `9bd8292f79b9d96e10b8c033d0114b6996123c966ae562f8da75a7fefa8be753`. The reviewer confirmed that the final driver and checkpoint source bytes are embedded in that executable's source fingerprint inputs.

Separately, the implementation agent ran a release-build N32 projected Alfvén case with jitter `.15`, final time `1`, an analysis output at `.25`, and stop/resume at accepted step 200. Its six resulting artifacts matched the frozen pre-checkpoint `fb8bb14` reference. The reviewer independently rechecked the existing six file comparisons and recorded their hashes; the reviewer did not rerun this release experiment. Its original commands, verification and logs are included in the archive with that distinction.

## Limits

This review supports deterministic serial continuation on the same executable and compatible platform. It does not establish cross-build/architecture portability, MPI/HDF5 restart, or long-duration scientific accuracy. Checksums detect accidental corruption, not an author who deliberately changes state and recomputes the checksum. Process-kill recovery was tested; physical power-loss behavior and every filesystem failure point were not fault-injected. Original numerical validation gates remain unchanged.
