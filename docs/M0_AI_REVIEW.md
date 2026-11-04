# Independent AI review of the M0 specification and reference packet

**Recommendation: accept the M0 specification and initial reference-packet criteria for issues #1 and #2 at the reviewed revision.** No material blocker remains within that scope. This recommendation does not certify the general solver or an M1 scientific result.

- Reviewed revision: `acdbbdd998e2319179fdbe0709f3f153c0985131`.
- Review date: 2026-11-04.
- Reviewer: separate delegated Codex AI review agent, task identity `/root/m0_review`.
- Review type: independent AI examination of the submitted source audit, proposed engineering contracts and generated evidence. The reviewer supplied feedback during preparation and checked the resulting committed changes. This is **not human peer review, author confirmation, or a review by the paper's authors**.
- Reviewed materials: [source specification](PAPER_IMPLEMENTATION_SPEC.md), [engineering profile](M0_ENGINEERING_DECISIONS.md), [operator audit](M0_OPERATOR_CHECKS.md), [benchmark packet](M0_BENCHMARK_PACKET.md), [machine-readable configuration](../benchmarks/m0/packet.json), supporting kernels/scripts and [external reference archive](../tests/reference/external_mhd/provenance.json).

The recommendation applies to the identified commit. Later numerical changes require their own review; adding this report or updating status/link metadata does not constitute review of an unseen algorithm change.

## Evidence and methods actually used

The reviewer read the repository instructions and required planning/numerical documents, inspected the relevant primary-paper sections and equations against local extracted text and HTML, and visually inspected rendered PDF pages 7, 15, 16, 18, 19 and 20 for the disputed formulas and benchmark resolution. The source was [Springel, Mayer & Pakmor, arXiv:2609.35989v1](https://arxiv.org/html/2609.35989v1). Its PDF SHA-256 was independently checked as `6e12da18a86c57536fc26f2baf86d15d6db2e378e040a59bc9b82870b2dfcb84`, matching the extraction record. This review does not claim a new line-by-line audit of every deferred extension or every published test.

The reviewer examined the Rust point-source/cleaning implementation and tests, independently derived the cleaning amplification matrix with SymPy, and independently evaluated its repeated application with NumPy matrix powers. The reference-data review inspected the pinned Athena source and input definitions, checked the initial vortex fields after the documented coordinate shift, and independently recomputed refinement errors from native Athena tables using array reshaping and block averaging rather than the project's table parser.

At the final reviewed revision, the reviewer ran:

| Check | Observed result |
| --- | --- |
| `python3 scripts/check_m0_spec.py` | All 13 algebra checks passed |
| `python3 scripts/check_reference_packet.py` | Archive hashes, grids, finite positive sample states and history times passed |
| `cargo fmt --check` | Passed |
| `cargo clippy --all-targets --all-features -- -D warnings` | Passed |
| `cargo test --workspace --locked` | All 37 Rust tests passed |

The reviewer also ran the release `gauge-cleaning` example during the source audit; its Rust implementation is unchanged in the final target. All recorded source/input hashes were compared with the committed files, all archived payload hashes were checked, and the final native initial/final snapshot hashes were matched to provenance. Conservation residuals were recomputed directly from the final archived histories, including the shock boundary-stress contribution.

The reviewer did **not** independently rebuild and rerun Athena. The parent task generated those simulations using an independent solver implementation; this reviewer audited their source/configuration/provenance and independently recomputed the relevant diagnostics from their outputs.

## Source map and discrepancy findings

No substantive transcription error was found in the reviewed core equation/stencil map. In particular, the Jacobian convention requires `-H^T A`; the cleaning gradient and mean-field correction have the documented positive signs; the default neighbour fit has a free intercept and excludes the target observation; curl uses unlimited derivatives; and face-centre advection uses a separate derivative stencil with the stated donor direction. The endpoint primitive predictor, centroid correction and frozen cleaning source are represented with their distinct dependencies.

| Finding | Independent disposition |
| --- | --- |
| R1, Alfvén potential, p. 18, (99)-(101) | Confirmed in the rendered PDF. The printed potential does not curl to the stated field. The adopted periodic `Ay=.1 sin(2pi x)/(2pi)`, `Az=.1 cos(2pi x)/(2pi)` plus `mean_B=(1,0,0)` produces the stated field and is accepted as an explicitly derived benchmark correction. |
| R2, cleaning explanation, p. 7, (43)-(44) | Confirmed missing scalar factor in the variable-coefficient bracket, dimensionally inconsistent inertial coefficient, and the divergence/curl wording problem. The constant-coefficient rederivation gives `r/(beta cs)` multiplying the second time derivative. Evolving the primary equations (41)-(42) avoids relying on these explanatory misprints. |
| R3, surface sum, derivative vector and stage brackets | Confirmed the target surface-area notation issue, the need to select derivative entries from the four-entry fit vector, and incomplete printed brackets in (80)/(86). The separated terms are consistent with the earlier source equations. |
| R4, Brio-Wu resolution, pp. 19-20 | Confirmed the caption's 512 cells and prose's 100 cells are inconsistent. The packet declares its own resolution ladder and does not claim to identify the unpublished run behind the figure. |

These remain attributed findings, **not author-confirmed errata**. The Orszag-Tang normalization is consistent with its stated magnetic field.

## Cleaning temporal order

Equation (90), including the following sentence on p. 16, explicitly retains the initial divergence and sound speed. For the longitudinal mode `Ax=a cos(kx)`, `phi=p sin(kx)`, define `q=alpha cs^2 k` and `kappa=beta cs/r`. The exact coefficient evolution has matrix

```text
L = [[0, k], [-q, -kappa]].
```

The frozen-source step differs from `I + dt L + dt^2 L^2/2` by

```text
[[0, 0], [0, dt^2 k q/2]].
```

This independently confirms the missing second-order coupling term in the scalar update. Repeated matrix multiplication reproduced relative errors `.0435027314367`, `.0214526193974`, `.0106503064994` and `.00530601252348` for 40/80/160/320 steps. The finest observed order is `1.0051949638`; the separately named reevaluated-Heun comparator gives `2.0013088385`.

The first-order result is accepted as a property of this isolated printed prescription. It is a pure gauge mode with zero physical curl and analytic spatial derivatives. It establishes neither full-solver magnetic/fluid error order nor stability or gauge contamination on irregular stencils. Retaining the reference update while exposing this limitation is preferable to relabelling a changed source update as the printed method.

## Engineering decisions and review resolutions

The profile's choices are acceptable as explicit implementation contracts, with their listed implementation fixtures still required before physical certification:

| Topic | Review disposition |
| --- | --- |
| U1: primitive predictor, face motion and energy | The solenoidal material B predictor is a declared choice consistent with the continuum constraint. Omitting the estimated `v div(B)` contribution preserves predictor boost covariance despite a discrete divergence residual. The face-velocity sign follows differentiation of the Voronoi bisector. Paired conservative updates and the absence of an energy reset are clearly separated from this predictor. |
| U2: endpoint reconstruction | Rebuilding neighbour/face stencils from endpoint geometry and predicted A/phi, while retaining old-data predicted Riemann primitives and frozen cleaning source data, resolves the previously ambiguous dependencies. Limiter anchoring and raw/limited derivative separation are explicit. |
| U3: auxiliary field | Membership, centred difference jets, 4-to-2-to-1 root coarsening, boundary inheritance, fine-level value-before-derivative ordering and spacing factors are defined. The translating frame is boost covariant: boosting both centre motion and initial mean velocity leaves the sampling coordinate unchanged. This is an engineering temporal extension, not a discovered paper prescription. |
| U4-U5: cleaning and timestep policy | Initial and predicted/recovered endpoint sound speeds, old/new radii, initial rate evaluation before dt selection, retry behavior and retention of equation (90) are explicit. The added timestep restrictions are safety choices, not a nonlinear-stability proof. |
| U6 and later features | Periodic serial scope and the deferral of general boundaries, entropy closure, diffusion, Hessians, Poisson inversion, fluid adaptation, local stepping, gravity and cosmology are acceptable M0 boundaries. |

The final draft resolves review feedback about endpoint sound-speed selection, active-coordinate projection in 2.5D, analytic versus finite-difference Hermite jets, deterministic jitter, tolerance precedence, jittered shock projection and case-specific magnetic diagnostic scales. The packet also distinguishes rigid-motion exactness from the geometric-conservation and temporal-convergence measurements needed for deforming meshes.

## Independent benchmark references

The reference source is Athena++ v24.0, revision `209a9258ee158d1965557f1a5c4193101b704dd9`; its license is retained. The solver implementation and magnetic representation are independent of OpenMHD-RS, although both use the published HLLD method. The packet explicitly distinguishes its PLM setup from the paper figure's piecewise-constant reference.

The reviewer checked the Alfvén correction, periodic Brio potential, loop curl, Orszag-Tang potential and Athena coordinate shift. The shifted native vortex initial density/pressure/velocity and staggered-curl cell-average magnetic fields match the specified formulas, including finite-cell averaging factors, within `1.4e-14` in the inspected high-resolution output.

Independent recomputation of the final reference refinement differences gave:

| Field | Brio 4096 to 8192, on 4096 bins | Vortex 256^2 to 512^2, on 64^2 bins |
| --- | --- | --- |
| rho | 0.0002390608208951 | 0.0064279039144281 |
| p | 0.0001794666388262 | 0.0120744563676982 |
| vx | 0.0003934297486947 | Not a packet profile gate |
| Bx | Constant 0.75 | 0.0098643959741196 |
| By | 0.0002533764862757 | 0.0088122959543700 |

These match the archived metrics to floating-point roundoff and satisfy the declared profile thresholds. They quantify refinement sensitivity on the stated bins; they are not rigorous error bounds or proof of a unique shock solution.

The independent shock boundary rates are `(mass,px,py,pz,E)=(0,.9,-1.5,0,0)`. Direct recomputation from the final high-precision histories gives maximum absolute budget residuals:

| Run | Maximum residual |
| --- | --- |
| Brio 4096 | `7.8825834748e-14` |
| Brio 8192 | `1.3922196729e-13` |
| Vortex 256^2 | `5.4428683782e-14` |
| Vortex 512^2 | `1.5264733921e-12` |

All pass the `1e-10` threshold. Final histories have one initial time, strictly increasing times and the required final time. The earlier apparent budget failure came from appended histories with differing output precision; it is not used as physical evidence. The final rerun and the guard against repeated/nonmonotone histories resolve that provenance defect without changing a numerical gate.

The registration history is disclosed: the packet began at `56c6b1e`, the missing Brio velocity refinement tolerance was added at `624b211` before computing refinement metrics, and history/parser/conservation checks were strengthened later. Prior pilot outcomes were already known. This is prospective registration for the new candidate profile, not a claim that every choice was made without any prior experimental knowledge.

## Acceptance boundary

The reviewed commit meets the **M0 equation-to-code specification, explicit-deviation, operator-evidence and initial reference/configuration packet criteria** under the user-selected AI review process. I recommend accepting those deliverables for issues #1 and #2. This report does not itself change issue state.

The general `paper-global-v1` solver, auxiliary interpolation implementation, complete endpoint stages, coupled gauge behavior and deforming geometry still need implementation and their specified tests. No new candidate solver has passed the packet's physical gates. The present evidence does not establish arbitrary-operator machine-zero magnetic divergence, general positivity/stability, paper-level numerical equivalence, long-time vortex agreement, a 3D/MPI method, or an M1/scientific release. Human scientific peer review and author confirmation have not occurred.
