# Independent review of the G1 literal-input draft and mass-ratio addendum

2026-11-22. **Source/manual-mathematics review only. Neither proposal is adopted or a frozen executable fixture.** The exact ignored subjects and their original closed boundaries are identified below and in [the review inventory](g1_literal_proposal_review_sources.json). No float parser, force/square-root kernel, numerical reference, test or evolution was called.

**Disposition: no demonstrated mathematical blocker in the proposed small controls or the mass-ratio derivation.** They are conditionally suitable source material for the existing G1 fixture-preparation step after actual M1 acceptance. They are not runtime-complete inputs, independent evaluated reference tables, or evidence for any numerical gate. The concrete serialization and negative-case qualifications in findings 1 and 6 must survive that preparation; they do not introduce another abstract review chain or alter a registered threshold.

| Exact subject | Bytes | SHA-256 |
| --- | ---: | --- |
| Draft `literal_inputs.proposal.json` | 24141 | `1ff075a6c456adf1ff053d335539930cd23816a73e1a13c5cc5311cff837cf18` |
| Draft `DERIVATION_AND_GAPS.md` | 15529 | `600d389e59e3c294a89548294227a5cea0e2d40514340c91de7d5de32197ae5f` |
| Draft `sha256.json` — 23 body files | 3860 | `53f94f3eb5c0e029b81ef268f19280f72af2a830dd3688f39477e9163781dcb0` |
| Addendum `MASS_RATIO_DERIVATION.md` | 5432 | `983b3383d0a41b92470b57daed0b8c6a11cf656445afa75c21b0648b06c17764` |
| Addendum `literal_input.addendum.json` | 3286 | `886f824007a57caa31c1d2460d5a150e823619ce8127b232ed61b3660be70903` |
| Addendum `source_receipt.json` | 1647 | `9a3335a7bc289df869d6151f4082568901a703b67aec8274e335b9cb4b0544f6` |

The addendum's three-body-file manifest SHA-256 is `877c90b5e8ddbd2788b763550ab6bece3c7b13cdbc1520cf49dbb294dfc4a8f3`. The draft context is Git `721a951a266b5be99907b2cb2e48a303b0eb0ae1`; the addendum context is `5e44eee8dec17407cf81ef089c2e891981853f77`. Current context was captured at `962336380030327a5f89cb394ee8059928c8c2a9`. The current gravity contract remains 69623 bytes, SHA-256 `15e71e81db4a59ed14bc38897af2178e08a539f6e6af6353cea3a875ee35d6a9`. Relevant gravity/shared/G1-review bytes agree across those contexts. Current README/HANDOFF/ROADMAP status has a separate role from the older draft context; it is not new mathematical evidence. Frozen scientific source remains `2bdcea0d28340e7429e10053a641f92d51fcc696`.

I did not author either reviewed proposal or `G1_DIRECT_GRAVITY_REVIEW.md`. I previously authored ISM/cooling contracts, narrow gravity/spherical interface and virial-frame corrections, metadata tooling and its separate runtime proposal, and adjacent independent source reviews. This review independently checks the two new drafts' mathematics and compatibility with the pinned source boundary; it does not self-approve my earlier physical interfaces, population model, gas/source coupling or metadata results. The existing G1 review's separate conflict disclosure is preserved.

1. **Supported, with a concrete encoding qualification — the inputs are exact source descriptions, not checked runtime catalogs.** Draft §§2,5 and JSON `encoding`, `id_literals`, `catalog_controls`, `invalid_*`; addendum `sources`/`model`. The 32-hex payloads encode namespace 1/counters 1–3, carry explicit ParticleId wrappers and join expectations by persistent ID. Per-case IDs are unique; reuse across independent cases is not a duplicated source within a run. Common G=1 and epsilon=4 are dimensionless algebra inputs. All valid coordinates/momenta in the original draft are small exact dyadics; the addendum's nontrivial dyadic q is assessed in finding 4. Species labels specify GravitySource inputs only, not validated stellar ages/populations or an active galaxy IC.

   The 14 invalid descriptions distinguish nonpositive/nonfinite mass, G and epsilon; nonfinite coordinates; duplicate persistent payload; wrong wrapper/kind; missing validated gas geometry; and nonrepresentable ordinary displacement. In particular, opposite maximum-finite positions differ by `(2-2^-52)*2^1024`, exceeding maximum finite binary64 `(2-2^-52)*2^1023`. That is a semantic rejection under the parent contract, not an infinite separation returning zero force. Nonfinite values are explicit invalid tokens, not valid JSON scientific numbers. A GasCell invalid description does not furnish a valid gas geometry/epoch control. These are not existing Rust error variants or an exhaustive overflow/allocator/rollback suite.

   The two JSON documents explicitly use different unadopted formats: nested `id` versus flat `id_wrapper/id_payload_hex`, and softening-class spelling `0x0000` versus `0000`. This is not a scientific contradiction or an adopted-schema failure. When producing a runtime fixture, map both into one explicit checked encoding; do not concatenate them as if their layouts already implemented that encoding. Preserve the separation of constructor validation from an empty-catalog shortcut: invalid model/source input is never evidence for a valid zero-force result.

2. **Supported — GP2 differentiation and all supplied pair/triplet targets.** Draft §3 and its ID-keyed expectations. At fixed masses/epsilon, with `d=xj-xi` and positive `s=sqrt(d·d+epsilon²)`,

   ```text
   dUij/dxi = -G mi mj d/s³,     Fi<-j = +G mi mj d/s³.
   dU/dmi = Phi_i,              U = sum_i mi Phi_i / 2.
   ```

   The force is attractive. Computing one pair vector and its negation preserves raw pair force symmetry; unequal masses imply unequal accelerations. The pair torque is `(xi-xj) cross Fij=0` in exact arithmetic. Compensated accumulation does not turn this into a bitwise identity for arbitrary sums.

   Independent manual substitution gives the following compact checks; the full derivation is retained in `manual_derivations.md` within the reading boundary:

   | Control | Independent manual check |
   | --- | --- |
   | Axis masses 2,3; d=(3,0,0); epsilon=4 | `s=5`, `F_A=(18,0,0)/125`, `Phi=(-3/5,-2/5)`, `U=-6/5`; accelerations `(9,0,0)/125` and `(-6,0,0)/125`. |
   | Oblique d=(1,2,2), same masses/epsilon | `d²=9`, `F_A=(6,12,12)/125`; `x_A cross F_A=(-12,60,-54)/125` and the opposite B torque. Specific potentials and pair U match the axis case. |
   | Distinct co-located IDs | `d=0` makes F zero while `Phi=(-3/4,-1/2)` and `U=-3/2`. Skipping this off-diagonal pair would be wrong. |
   | Three masses 2,3,5 at x=0,3,0 | Pair energies `(-6/5,-5/2,-3)`, total `-67/10`; force x-components `(18,-63,45)/125`; potentials `(-37/20,-7/5,-11/10)`; half the mass-weighted sum is `-67/10`. |

   The third source's co-location with the first does not erase its finite AC energy. Empty/one-source catalogs have no unordered pairs, so U and existing samples' F/Phi are zero; empty COM and the mass-based timestep are undefined, as stated. None of these is a successful numerical observation.

3. **Supported — raw moment scales retain cancellation information and zero cases.** Draft §5/`normalizations_for_later_review`, addendum `analytic_scales_for_later_review`. Per-ID force uses the sum of analytic/reference pair-force magnitudes, specific potential the summed absolute specific contributions, and energy the summed absolute pair energies. `S_netF=2 sum_pairs |Fij|` is a force scale; `S_netTau=sum_pairs (|xi|+|xj|)|Fij|` has torque units and depends on the stated origin. It is not the absolute net torque, which vanishes for these exact central pairs.

   For the axis pair the scales are `36/125` and `54/125`. For the oblique pair, `|Fij|=6*sqrt(1+4+4)/125=18/125`, while `|x_A|=sqrt(21)` and `|x_B|=sqrt(34)`, giving the stated torque scale. For the triplet, the two nonzero force magnitudes are `18/125` and `45/125`; their factor-two sum is `126/125`, and the position-weighted torque scale is `3*(18+45)/125=189/125`. These are symbolic norms, not square-root evaluations.

   The common `<=5e-13` algebra budget remains tied to nonzero declared analytic/summed scales, with raw component and absolute residuals retained. A zero scale cannot be repaired by a tuned denominator floor. A near-zero cancellation point still needs its independent scale/roundoff analysis. Larger-N operation counts and accumulated roundoff bounds are honestly absent; no claim here supplies them. No force subtraction, COM/momentum recentering or diagnostic repair is permitted.

4. **Supported — the mass-ratio addendum's exponent, significand, rounding and softened formulas.** `MASS_RATIO_DERIVATION.md`, paragraphs beginning “Since”, “With N”, “For the isolated”; JSON `q_manual_literal`. From `2^19<1000000<2^20`, the reciprocal lies strictly between `2^-20` and `2^-19`. A normal binary64 number in this binade has exponent -20 and spacing `2^(-20-52)=2^-72`. The stated division remainder gives

   ```text
   2^72 = 4722366482869645213696
        = 4722366482869645 * 1000000 + 213696,
   0 < 213696 < 500000.
   ```

   Thus N is strictly nearer than N+1; ties-even is never invoked in this case. Independently expanding the hex significand in integer blocks gives

   ```text
   0x10c6f7 = 1099511;       0xa0b5ed8d = 2696277389;
   0x10c6f7a0b5ed8d = 1099511*4294967296 + 2696277389
                    = 4722366482869645.
   ```

   N lies between `2^52=4503599627370496` and `2^53=9007199254740992`, so it is the full 53-bit normal significand. The unbiased exponent is -20, the biased exponent `1023-20=1003=0x3eb`, and the 52 fraction bits are `0c6f7a0b5ed8d`. Positive sign/exponent/fraction therefore give bits `3eb0c6f7a0b5ed8d` and hexfloat `0x1.0c6f7a0b5ed8dp-20`. This is an independent manual integer argument, not a parser observation or generated f64 array.

   The exact dyadic q is below `1/1000000` by `213696/(1000000*2^72)`, with relative deficit `213696/2^72`; the proposal correctly distinguishes them. With masses `(1,q)`, separation 3 and epsilon 4, GP2 gives `F_A=3q/125`, `F_B=-3q/125`, potentials `(-q/5,-1/5)`, `U=-q/5`, and accelerations `(3q/125,-3/125)` along x. Force scales `3q/125`, potential scales `(q/5,1/5)`, energy `q/5`, raw net-force scale `6q/125` and torque scale `9q/125` follow directly. The large small-body acceleration must not become a denominator that conceals small-force error. Pair forces remain equal and opposite; the addendum's phrase “unequal-force/acceleration distinction” is best read as the distinction between forces and unequal accelerations, already unambiguous in its equations.

   The addendum closes only the original draft's missing **input meaning** for the registered ratio. It neither edits that historical missing-input statement nor supplies force-output bits, a conversion-test result or an evaluated independent reference. Future references must use this exact q, not silently replace it with the exact decimal rational or another dyadic.

5. **Supported — ideal KDK targets are distinct from references at actual rounded endpoints.** Draft §4 and `kdk_controls`. For the free mass 2, p=(2,-4,6), h=1/8, drift gives `(9/8,-9/4,27/8)` and unchanged p, with `K=(4+16+36)/4=14`. That is a no-pair drift control, not a fitted temporal-order experiment.

   For the initially resting axis pair, the half kick is `+/-9/1000`; dividing by the respective masses and drifting gives `x_A=9/16000`, `x_B=23997/8000`, and separation `D=9597/3200`. Define `S` as the positive square root of `D²+16`, `f=6D/S³`, `P=9/1000+f/16`. The stated endpoint forces `+/-f`, momenta `+/-P`, `U1=-6/S` and `K1=5P²/12` follow. The Hamiltonian difference is not asserted zero. No S or endpoint-force value was evaluated.

   The force-at-actual-rounded-endpoint reference is a separate required target. In particular the non-dyadic half kicks and displacements cannot be silently replaced by ideal rational endpoints in that oracle. Retain actual rounded endpoint coordinates/momenta, rebuild the immutable force-source view and new epoch/hash, and evaluate the endpoint reference there. A symbolic ideal-step comparison must be separately labelled and account for rounding. The draft explicitly requires this distinction.

   The conservative ceiling comparisons also check manually: the pair inequality reduces to `1/64<=4/125`, i.e. `125<=256`; the free-body one to `1/64<=2/25`, i.e. `25<=128`. These prove membership beneath the proposed ceiling only, not accuracy or stability. Exact fixed-mass/fixed-epsilon KDK is a symmetric Hamiltonian composition; floating reversal, state-dependent step selection and source events inherit no exact theorem. The registered long-orbit controls are still absent.

6. **Required preparation already disclosed — cache, runtime identity and physical-unit evidence remain incomplete.** Draft §§2,5, `force_epoch_input`, `cache_and_epoch_negative_control_descriptions`; addendum `pending`. The six descriptions distinguish G, epsilon, kernel/table/model, unit-map, backend/config, and endpoint state/source identities. Time/state/source hash and applicable gas geometry epoch are separate checks. A source event can invalidate a cache without changing geometry; matching source bytes alone cannot override a wrong force model or epoch. Relabelling and permutation preserve the stated ID-keyed mathematical answers, but relabelling can change source identity. Canonical source encoding must be fixed before byte/hash equality is asserted.

   Converting the compound STATE description into executable negatives must avoid incidental coverage: independently exercise each claimed stale time/revision/source identity so that another mismatch cannot mask an omitted check. Likewise, the missing-gas-epoch description needs an actual separately validated gas view before it can test a gas-cache transition. This is a qualification of the stated future coverage, not evidence that the unimplemented constructor failed.

   Actual source/model/unit/cache serialization and checked runtime views remain absent in both documents. G=1 does not choose physical SI scales; the parent UnitSystem and independent rescaling controls are still required, including actual f64 conversions and their identities. Neither descriptive strings nor invented zero hashes discharge them. No astronomical SI constants or physical scales need adoption for the covered dimensionless algebra proposal.

7. **Supported source/version boundaries — published equations are not these toy ICs.** The complete retained [Dehnen v1](https://arxiv.org/pdf/astro-ph/0011568v1) and [Hairer lecture 2](https://www.unige.ch/~hairer/poly_geoint/week2.pdf) were available with the exact hashes in the inventory. Their already retained full-page renders were directly inspected: Dehnen p3 §1.3 Eq3 gives the Plummer potential; its printed Eq4b shows the apparent sign discrepancy described in the parent review. This is not an official erratum. Direct differentiation in finding 2 is the authority for the attractive GP2 sign. Hairer p2 Theorem2/Eq2 reduces to the stated separable KDK for `T=sum p²/(2m)`; it does not furnish these initial conditions or prove a measured floating-point result. No new code/dependency/license adoption follows from either citation.

   The units, pair and KDK blocks in the current gravity file independently match the existing G1 review's respective scoped hashes `361d2c388114033939bc596de3cdf52f4b4e36f330eb52aa8100195b7c57c439`, `f5316a98765c68594bea69ef7bacab8b256f3dfefd7f3cdaf9673b7155671719` and `f1cbbdf35c81abfc9a381ad7c53e6ab4d95520d8e0896bb1b1cbf44bf945023d`. That does not relabel the whole current 69623-byte file as its historical 63112-byte reviewed subject or approve coordinator/other-author interface amendments. Root's proposal receipt is retained as identity/scope context only.

8. **Conditional eligibility and limits — preserve every existing evidence boundary.** These ten original valid controls plus one ratio proposal are a useful algebra/input basis, not completion of G-PAIR or G1. After actual M1 acceptance, finish their exact runtime encoding, actual rounded-state/bit controls and independent high-precision references as part of the already required fixture preparation, with reference uncertainties and accumulated-roundoff rules. There is no need to invent extra physical parameters or numerical values to make this source review pass.

   The original gates remain: common algebra `<=5e-13`; independent-U gradient plateau `<1e-7` and analytic derivative `<5e-13`; seeded mixed N=4/32/128 symmetry/covariance `<=5e-12` with raw force/torque `<5e-13` scales; at least four dt values/finest-three temporal order `>=1.8`, the registered 100-period softened circular binary plus eccentric/plunge controls, energy/COM/P/L/reversal limits, fixed-list boosts/restart and physical rescaling. Orbit epsilon0.1, periods/momenta, seeded transformations and high-precision histories are not supplied by these drafts. No small relabel control or one-step symbolic result substitutes for them. Each future independent executable case runs only on REANA with explicit resources after its immutable preflight; ready-case concurrency has no aggregate scheduling cap. The proposed 1CPU/1Gi requests and cost ceilings remain unmeasured labels.

   This task does not reopen or accept M1 output, control its active acquisition, freeze a fixture, implement gravity, or alter any scientific source. Tree, gas work/centroids, birth/representation energy, equilibrium, domain/ambient, bounded and genuinely deforming full3D nonzero-MHD, and published multiphase ISM/SF/feedback coupling remain separate required gates. The full-duration live-gas/DM/old/new-star isolated-gravity merger remains the goal, not a collisionless or B=0 replacement. All numerical/physical acceptance flags remain false.

Actual checks: complete reads of both proposal notes/JSONs and the existing G1 review; relevant current gravity/shared contract and project-policy reading; original 23-file and three-body-file closure/hash verification; all twelve draft-context Git relations and addendum source/context relations; 68 initial identity/closure checks and 219 corrected inert JSON/lexical/ID checks; visual reinspection of the two complete primary equation pages; and manual algebra/integer reasoning above. The retained review boundary is lean: exact proposal/receipt bytes, the relevant four current gravity/shared-review files, the two complete primaries and their equation-page/text artifacts, and focused receipts; unrelated large project context is pinned by hash/Git rather than copied again.

One extra generic lexical inspection exited nonzero because it misclassified three ID vectors as hexfloat vectors, two scale dictionaries as scalar rationals, and one boolean marker as a rational. Its original failed receipt is preserved; a typed correction resolved all six inspection errors without changing a proposal. No truncated read was credited in this review. The companion inventory records final document/closure checks and the unresolved execution limits. No target import/call, float/force/sqrt/high-precision/RNG/geometry/reference evaluation, test/mock/probe, build/reducer/evolution, REANA/network/private-configuration/workflow/service action, commit/push or delegation occurred.
