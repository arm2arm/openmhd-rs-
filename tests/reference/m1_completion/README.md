# M1 completion evidence

This directory preserves the separate **AI review**, not human peer review or full M1 acceptance. Physical acceptance remains pending; the matched profile also fails its complete irregular-wave order gate (.77243). The historical linear irregular-wave ladder fails its unchanged order gate; the quadratic-only and consistent mixed-cleaning experiments are not accepted.

`ai_review.tar.gz` contains 52 byte-preserved review sources, matrices, diagnostics, captured input records, outputs and documentation. Four compiled local binaries are omitted; their original hashes remain recorded. `ai_archive_provenance.json` hashes the archive and every included/excluded artifact. The embedded `checksums.json` is the original reviewer inventory, including omitted binary hashes.

```sh
tar -xzf tests/reference/m1_completion/ai_review.tar.gz -C /tmp
python3 /tmp/openmhd_consistent_ai/reproduce_rust.py --repo "$PWD"
```

The included README gives exact revisions, reproduction commands and scientific limitations. The Rust reproduction accepts a repository path; the original physical-diagnostic scripts retain captured absolute input paths and require the corresponding raw study outputs. Matrix-only Python diagnostics use `/tmp/openmhd_consistent_ai` and NumPy. Review sources/data are original project work under the repository MIT license; no external solver code is imported here.

The review verifies historical behavior, passive/general operator equivalence, and the existence of growing mixed-cleaning modes. Its matched-derivative control is bounded evidence; it does not prove general irregular-mesh stability, exact curl-gradient cancellation, or M1 acceptance. See [the review report](../../../docs/M1_COMPLETION_AI_REVIEW.md) and [prospective plan](../../../docs/M1_COMPLETION_PLAN.md).


`hll_remaining/` archives the complete 31-run historical HLL loop/shock/vortex packet, including preserved original analysis and corrected/sealed measurements. Its nine ladder gates and six vortex boost pairs pass. `hll_wave_interrupted/` is explicitly a **partial historical archive**, with 119 completed, 8 externally stopped and 57 unexecuted cases. Its complete irregular travelling-wave order is 1.17745 and fails the unchanged 1.8 criterion. These directories do not establish full HLL M1 acceptance. See [illustrated results and reproduction commands](../../../docs/M1_HLL_RESULTS.md).


`compact_design_ai.tar.gz` contains 63 byte-preserved files from the separate compact-derivative design review: actual operator matrices, coupled uniform-Alfvén Jacobians, N256 failure diagnostics, source, hashes and reproduction commands. `compact_design_ai_provenance.json` records every included byte hash and the omitted compiled binary. Extract to `/tmp` and read `/tmp/openmhd_compact_ai/README.md`; `reproduce.py --repo "$PWD"` rebuilds the Rust diagnostic. The physical diagnostic requires the original hash-checked matched-probe raw snapshots. The weak positive irregular coupled mode remains explicitly reported; no compact physical accuracy or M1 acceptance is implied.


`matched_wave_interrupted/` preserves 189 completed, 8 externally stopped and 59 unexecuted configurations out of256. Its measurement source is included, and 1,179 completed-run artifact hashes were verified. The complete regular travelling-wave ladder passes order2.00687; the irregular ladder fails .77243. `wave_probes/` preserves original execution metadata for the quadratic-only, consistent and matched bounded studies, with all24/24/28 listed raw artifact hashes verified. The first two N256 cases were externally stopped; their recorded exit -15 is not a numerical evolution failure. Raw CSVs remain local and their exact rerun commands/hashes are archived. See [the diagnostic figures](../../../docs/M1_WAVE_DIAGNOSTICS.md).


`compact_implementation_ai.tar.gz` preserves 12 review files, with three compiled binaries omitted and hashed in `compact_implementation_ai_provenance.json`. It records the 36 historical bit-identical evolutions and 24 exact passive/general transport comparisons supporting bounded implementation approval at `aae382e`. It does not contain or claim compact physical acceptance.


`wave_probes/figure_inputs.json.gz` contains the measured norms and exact N128 point samples for both diagnostic figures, with a checksum beside it. `plot_m1_wave_probes.py --figure-input ... --output-dir ...` reproduces both PNGs byte for byte without raw solver outputs. The input retains the original raw snapshot hashes; replay is figure reproduction, not a new scientific measurement or acceptance run.


`matched_remaining/` preserves the complete 31-run matched-profile passive/shock/vortex study, original execution analysis, exact reuse origins and corrected/sealed projection inputs. All nine remaining-case ladders and six vortex boost pairs pass. The matched wave-order failure remains separate and blocks M1. All six [matched-study figures](../../../docs/M1_MATCHED_RESULTS.md) reproduced byte for byte from raw measured versus archived data.


`matched_packet_ai.tar.gz` contains 12 files from the separate completed-packet review. Its provenance lists 42 omitted duplicate reproduction files with their hashes. The review verifies the remaining-case passes and the explicitly retained wave/boost failures; it does not approve M1 acceptance.


`wave_probes/compact/` preserves the completed compact N32/64/128/256 ladder, which fails order1.64016 against1.8. `compact_quick/` preserves all48 completed subset runs and reanalysis:14/16 wave boosts pass,2 fail;8/8 loop boosts pass. The full compact acceptance packet was not launched. `wave_probes/compact_comparison_figure_inputs.json.gz` adds compact measured data to the earlier four-profile diagnostic comparison, retaining the original four-profile input separately. See [compact results](../../../docs/M1_COMPACT_RESULTS.md).

`shutdown_diagnostics_ai.tar.gz` preserves the separate **AI review** of interim compact errors, cubic-moment controls and standing-wave failures. Its provenance records every included file and omitted compiled binary. Extract into `/tmp` to restore `openmhd_compact_interim_ai`, `openmhd_cubic_design_ai` and `openmhd_standing_ai`; read each README before reproducing. The standing controls fail even with fixed timestep caps and no rejected steps. The limited coordinate-Jacobian indication is preliminary: directional eigenvector validation and full-HLL controls were **not started** before shutdown. No new candidate or M1 acceptance is approved. See [the restart handoff](../../../docs/M1_RESTART_HANDOFF.md).

`projected_limiter_diagnosis.tar.gz` preserves the resumed root-agent controls and separate AI directional/limiter review (115 files;15 omitted compiled artifacts). Directional checks reject the earlier eigenmode interpretation; actual limiter probes establish a discontinuity. `projected_limiter_implementation_ai.tar.gz` contains62 files from the separate high-precision projection/implementation review; five binaries are omitted with hashes. Adjacent provenance inventories verify every included/excluded artifact. Extracting restores directories named `openmhd_transport_controls`, `openmhd_standing_directional_ai` and `openmhd_projected_limiter_ai`; their READMEs specify exact commands and limitations.

`projected_controls/` preserves the four completed `0f2e5e2` fixed-cap controls, exact execution runner, all28 verified raw hashes and measured boost norms. N32/N64 pass, but full M1 acceptance remains pending. The [illustrated report](../../../docs/M1_PROJECTED_CONTROLS.md) includes reproduction commands; its plot replays `projected_controls/analysis.json.gz` without raw CSVs.
