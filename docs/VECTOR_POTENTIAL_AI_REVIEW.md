# Independent AI review — issue #6

**Disposition: approved for the documented serial 2.5D operator/coupling scope.** A separate agent (`issue6_ai_review`, distinct from the implementation agent) reviewed clean revision `d67e5c052ff4d877e82941e536af9681adc99520` on 2026-11-04. This is an **AI review**, not human scientific peer review or author confirmation. The subsequent evidence commit adds documentation/archived outputs without changing the numerical implementation.

## Scope and equation audit

The reviewer checked all three physical/A components; numerical HLL EMF; `-H^T A`; separate raw/limited fits; old-data endpoint primitive prediction; refreshed A_star/phi_star fits; frozen cleaning C1; shared opposite conservative exchanges; periodic winding and topology changes; timestep/retry immutability; and all three divergence diagnostics. No unresolved implementation blocker was identified.

The earlier independent design review identified v1's fixed auxiliary-origin defect across repeated boosted rebuilds. It accepted the explicitly preregistered v2 persistent-origin amendment, with the origin/corner data frozen on retries and origin advancement only after acceptance. Historical v1 records remain intact.

## Findings and disposition

| Finding | Resolution |
| --- | --- |
| Live distortion implementation needed direct coverage beyond the isolated gauge kernel | Added a PotentialStage fixture with nonzero auxiliary derivatives, all A components and A_z coupling. |
| HLL counts omitted discarded endpoint attempts and partial failed sweeps | Kept accepted-stage counts and added attempted successful-HLL counts, retained even after a later error; added a partial-sweep fixture and explicit semantics. |
| LS conditioning was available internally but absent from output | Added finite-checked neighbour/face indicators to initial/final diagnostics. |
| Nonuniform nonzero-mean-field boost probe differs measurably | Retained as an explicit limitation and added a reproducible observational study pair; #7 must investigate before general invariance claims. No acceptance threshold was changed. |

## Independent verification

The reviewer independently ran `cargo fmt --check`, `cargo clippy --workspace --all-targets --all-features --locked -- -D warnings`, and `cargo test --workspace --locked`; all passed, including **70 Rust tests**. It verified the clean study revision, 27 source hashes and 59 result hashes, and independently checked the numerical gates from the recorded outputs. It did not independently rerun the entire study matrix.

The packet contains 27 registered runs and two additional observations. Maximum normalized conservative-budget error is 1.237e-15; registered mean-zero boost differences are at most 4.663e-15. Curl convergence, uniform mean-field states, retained first-order cleaning behaviour and deforming-mesh refinement meet their declared thresholds.

The reviewer also wrote and rebuilt separate [rectangular-mesh probes](../tests/reference/vector_potential/README.md) against the reviewed revision. Their domain is (1.3,.7), grid 6x8, jitter .15, gamma=5/3, dt cap .0005, t=.01, with nonzero phi and boost (2,-1,.8). Prescribed deforming and fluid-following generator motion were each tested with limiting enabled/disabled. All zero-mean-field transformed physical differences stay below 2.254e-14 over 20 steps, with identical auxiliary roots and no rejections.

## Material limitation and acceptance boundary

Changing the probe to mean_B=(.3,.2,.1) gives maximum magnetic-component differences about 1.99e-5 (prescribed deformation) and 1.96e-5 (fluid following). The square-mesh observation in the main packet gives Bz difference 3.94e-5. Nonuniform mean-field boost invariance is **not established**. A noncommuting discrete curl/gradient response to evolving gauge drift is a possible mechanism, not an established diagnosis.

These observations are outside the registered mean-zero boost and uniform mean-field gates. The review supports closing #6 within its stated operator/coupling scope, with the limitation prominent and investigation assigned to #7. It does not establish the full M1 physical benchmark matrix, general 3D/adaptive evolution, resistivity, entropy closure or paper-level numerical equivalence.
