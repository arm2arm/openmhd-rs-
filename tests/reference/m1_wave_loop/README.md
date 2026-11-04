# Issue #7 evidence packet

The measured study is an incremental packet: the complete mean-field boost ladder plus coupled Alfvén/loop N32/64 runs (96 original study evolutions and 48 further bulk-frame physical evolutions). The `bulk/` directory contains the latter packet. It is **not full M1 acceptance**. N128/256, the Alfvén temporal packet, prescribed-flow irregular loops and the unresolved degenerate-face convention remain separate work. See the results document for exact executed/failed/unexecuted gates.

`summary.json.gz` contains diagnostics, norms and status for all executed runs; `execution_provenance.json` records the Rust source/binary and exact commands. Measurement provenance identifies any later correction of analysis independently from the evolution revision. Selected raw snapshots are retained as deterministic gzip streams; full snapshots can be reproduced with the study command. Plotting accepts this packet or the raw result directory.

`ai_degenerate_face.rs` and its output are independent **AI review** probes of the unresolved zero-normal-field face-state convention. `ai_pruning_probe.rs` independently checks ordered pruning against exhaustive clipping. These are observations/probes, not claims of physical benchmark acceptance.
