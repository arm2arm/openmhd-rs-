# Narrow review of the gravity ceiling and empty-step source revision

2026-11-22. The coordinator reviewed the complete Rust/contract/report delta
and [orbit campaign amendment](G1_ORBIT_CAMPAIGN_AMENDMENT.md) against
`8fe734268deee3fe5b6a33d868b2bfeaece06a7b` and findings 1–2 of the
[independent source review](G1_SOURCE_REVIEW.md). The coordinator selected
the additional ladder but did not author these Rust changes. This review
checks that implementation of the decision and its explicit mathematical
limits. It is not independent numerical orbit evidence or gravity acceptance.

The protected ceiling and all ten production Rust files are byte-identical.
The original four requests remain as negative guard controls, and the new
actual-step ladder is explicitly preregistered rather than reported as run.
The original duration, physical thresholds, independent-reference and
eccentric/plunge/boost/restart requirements remain. There is no bypass,
clipping, hidden subcycling or replacement of integration h by output cadence.

For ideal stated inputs, direct substitution gives
`(T/n)/h_max=(40*pi/n)*101^(3/4)`. The old finest level exceeds `450/128>1`.
The new coarsest level is below `15/16`, using `pi<4` and
`101^(3/4)<144^(3/4)=12*sqrt(12)<48`. These are manual symbolic bounds.
They do not certify an evaluated period, the rounded epsilon/ICs, accumulated
clock, guard arithmetic or endpoints. The amendment correctly leaves those
independent references and actual observations mandatory before long cases.

The strengthened dt/revision method supplies a standard-f64 period only to
exercise guard rejection. Its resting momenta are explicitly not a circular
IC. Every original request checks the ceiling predicate, typed rejection and
unchanged checkpoint/time/revision. The empty-catalog method now constructs
the public KDK system, checks positive-step `EmptyTimestep` and unchanged
accepted state. This matches the current API rather than inventing a free
empty drift. All original assertions and all 39 lexical selectors are retained.

All six delivered file hashes match the author's closed source receipt
`results/galaxy_g1_source_repair_20261122/checks.json`, SHA256
`ab38ab3fd6266aa973180fddf08945af6a85ed471185db450eb7c7480cd9ed34`.
Root independently compared the ten production files to the frozen Git blobs;
no production change was found. The changed Rust file is 29105 bytes, SHA256
`7b0729a680df7f2ebda5c06383af1cc6f426ccf227aeb9b4dfbf085411050496`.
The amendment is 9284 bytes, SHA256
`324b84ace382ac5c79380e3a92f0d54ce6be1859ebbd0dadd9243448fc331973`.
The source/report inventories preserve their historical identities separately
from current receipts. Owned-path whitespace and JSON checks passed.

No target import, period/force/reference evaluation, guard, test, formatter,
compiler, linter or workflow ran in this review. No new blocking source
mismatch was identified in these narrow repairs. Findings 1–2 are addressed
at source level and the current short controls are eligible for immutable
REANA format/strict-Clippy/build/discovery preflight. Each selected method,
independent rounded-input reference, four long levels and their complete
output review remain required. M1's accepted scope is unchanged; gravity,
deforming nonzero-MHD and the live-component merger remain unaccepted.
