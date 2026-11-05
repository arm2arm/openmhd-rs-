# M1 completion evidence

This directory preserves the separate **AI review**, not human peer review or full M1 acceptance. Physical acceptance remains pending. The historical linear irregular-wave ladder fails its unchanged order gate; the quadratic-only and consistent mixed-cleaning experiments are not accepted.

`ai_review.tar.gz` contains 52 byte-preserved review sources, matrices, diagnostics, captured input records, outputs and documentation. Four compiled local binaries are omitted; their original hashes remain recorded. `ai_archive_provenance.json` hashes the archive and every included/excluded artifact. The embedded `checksums.json` is the original reviewer inventory, including omitted binary hashes.

```sh
tar -xzf tests/reference/m1_completion/ai_review.tar.gz -C /tmp
python3 /tmp/openmhd_consistent_ai/reproduce_rust.py --repo "$PWD"
```

The included README gives exact revisions, reproduction commands and scientific limitations. The Rust reproduction accepts a repository path; the original physical-diagnostic scripts retain captured absolute input paths and require the corresponding raw study outputs. Matrix-only Python diagnostics use `/tmp/openmhd_consistent_ai` and NumPy. Review sources/data are original project work under the repository MIT license; no external solver code is imported here.

The review verifies historical behavior, passive/general operator equivalence, and the existence of growing mixed-cleaning modes. Its matched-derivative control is bounded evidence; it does not prove general irregular-mesh stability, exact curl-gradient cancellation, or M1 acceptance. See [the review report](../../../docs/M1_COMPLETION_AI_REVIEW.md) and [prospective plan](../../../docs/M1_COMPLETION_PLAN.md).
