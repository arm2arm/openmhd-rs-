# Branch consolidation — 2026-11-23

`main` now includes every local and origin branch tip observed before this
integration. The previous main checkout was fast-forwarded to `26d4fa6`, then
the recovery branch `924a27d` and scientific-case branch `311e7de` were merged
with their histories. Existing branches and worktrees are retained.

The merge commits are `3afce8c` and `c98411f`. The exact starting refs and
static checks are in [the integration record](branch_consolidation_20261123.json).

The only content conflict was the Python runner's selected test catalog. That
selection describes an immutable execution generation, rather than all tests
ever present in the repository. The integration generation selects 216 direct
methods: the current 25 workspace controls, 90 recovery controls, 79 standalone
build/geometry controls, and 22 acquisition controls. Earlier catalogs and
their actual results retain their original source identities and outcomes.

The scientific branch supplies the observed Cargo scalar-override correction.
Two acquisition-helper pins are updated to the matching corrected preparer and
record validator. The original failed inline-table build and the original
acquisition controls remain historical evidence; changing these pins does not
reinterpret those packets.

Scientific Rust sources and their test assertions, Cargo dependencies,
numerical gates, plots, reference packets and the M1 acceptance record remain
unchanged relative to `26d4fa6`.
All incoming source files otherwise retain their branch bytes. The original
490-workflow validation continues from its separate, unchanged checkout and
source snapshot.

Static checks verify ref ancestry, exact scientific-tree identities, Python
syntax, the reconciled helper pins and retained branch bytes. Integrated
execution requires a new immutable REANA import parent and separate per-method
workflows; earlier branch results do not constitute a pass for this new source
generation. No component or scientific acceptance is broadened by this merge.

The integration source is committed and pushed at `0bc9e50`. One import-only
parent, `openmhd-merge216-50cf56ecaf2c-preflight.1`, was submitted and remains
running in the last actual observation at 15:46:30 UTC. Its UUID is
`af081aab-5b7c-4465-9683-3bf342536d29`. No test methods have been submitted:
their release requires the actual successful import certificate. The 354-member
snapshot, original submission and closed host commands are retained with
[the execution evidence](branch_consolidation_20261123/evidence/sha256.json).

The separate original 490-workflow scientific batch was observed at 15:44:37
UTC: 165 finished, 78 failed, 242 running and five pending. These are server
workflow states, not reviewed method-pass counts. The local stop-submission
fence is set. An original failed workflow's job logs and a failed diagnostic
artifact GET are retained; the cause is not established. This consolidation
does not turn that incomplete batch into a successful workspace-test result.
