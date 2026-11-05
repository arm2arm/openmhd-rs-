# M1 completion — separate AI review

This is a separate AI review by agent `/root/issue6_ai_review`, not human peer review or author confirmation. The reviewer has read-only tasks and independent local numerical probes. Full M1 acceptance remains pending the complete physical packet. Bounded approvals below permit further evaluation; they do not certify M1.

## Continuous face completion

At `25aaace`, the reviewer found no formula or profile-wiring defect. Both stages select the new completion, the historical profiles retain their behavior, and identical face inputs preserve the gas and numerical induction flux arrays bit for bit. The conservative alpha=max(abs(SL),abs(SR)) matches the preregistered construction.

Independent checks included a 2,000-face varied-state probe with **500 actual HLL fallbacks**. Conservative/induction flux arrays were unchanged; full A-source reversal/boost relative-plus-absolute error was at most6.92e-16. The reviewer independently recalculated the standing-wave preflight: B boost L1=4.0148915033686693e-14, maximum transformed physical-component error=7.281952818516402e-13 and analytic magnetic L1=.0015548126960180453. This removes the observed failure in that fixture; it does not identify the unique historical internal-wave cause or establish full physical accuracy.

Requested permanent regressions were added and independently passed: nonuniform asserted HLL fallback, continuity across finite-normal-field stationary rotational waves, rotated-output equivalence, a six-step rectangular exact-geometry comparison and reversed cell IDs. Existing zero/signed-normal-B and three-component boost tests remain.

## Remaining cases and measurement audit

At `3249360`, no evolution-equation defect was found in passive Voronoi transport, the Brio/Orszag–Tang initial data or polygon export. Review identified three measurement blockers, corrected before acceptance:

1. Brio comparison now averages fine reference primitives onto each clipped candidate cell before taking absolute differences. Separate y rows are retained. Tests detect reversed averaging order and cancellation between rows; an independent shifted-image fixture also passed.
2. Vortex boosts use explicitly documented fixed relative scales and independently require paired times/geometry, positive states and conservative budgets.
3. Reanalysis verifies immutable execution metadata, raw/reference hashes and separate measurement provenance; the original execution summary remains intact.

Follow-up review required actual configuration/dimension/count/time checks, initial magnetic representation errors, archived reference-refinement sensitivity and distinct failed/missing statuses. These were added. A known failed member now remains a failure even in an incomplete ladder. Private passive state prevents callers from invalidating its cached stencils/timestep.

## Exact mesh reuse and provenance

Independent serialization tests verify exact f64-bit geometry round trips, rejection of invalid/truncated/mismatched requests and bit-identical evolved state. Cache reuse retains original ordered-clipping geometry rather than substituting an analytic Cartesian constructor. Producer revision/binary/source and cache hashes are retained.

The reviewer identified and requested fixes to reused-run bookkeeping: immediately write the copied ledger even if no new run starts, preserve and hash the exact captured source ledger/provenance/manifest bytes, and retain the original per-run execution origin through subsequent reuse. Those fixes and the mixed failed/missing-status test were independently checked; five completion-measurement and seven wave-measurement tests passed.

## Irregular-grid consistency investigation

The reviewer independently measured nonzero leading Taylor moments on exact cached jittered meshes. At N64/128/256, N times RMS quadratic derivative moment is .09684/.08821/.12200 for neighbour derivatives and .02730/.01976/.02513 for face derivatives. N times RMS perimeter first moment is .01271/.00753/.01114. These individual operators can have O(h) terms on irregular meshes; regular-grid moments are at roundoff. This does not establish the order or the source of error in the complete coupled evolution.

The reviewer approved a separately named quadratic-A reconstruction experiment as a justified investigation. Using its derivatives for B is an explicit engineering choice; the paper prefers the direct-neighbour B fit. Quadratic curl alone does not remove the face-advection and perimeter-source consistency terms, and initial curl error is not a strict lower bound on final physical error. Actual full t=1 ladders must determine acceptance. See the prospective choices and unchanged gates in [M1_COMPLETION_PLAN.md](M1_COMPLETION_PLAN.md).


## QR correction and complete-rate design review

At `989c6a9`, the reviewer independently verified full reorthogonalization of the selected QR residual against the earlier basis. The accepted near-collinear polynomial fixture's coefficient error fell from 2.63e-4 to 2.45e-8; its permanent condition-scaled roundoff regression passes. Preserve the original quadratic-only physical probe at73dd508, including its N128 error increase, separately from corrected-revision acceptance evidence.

The separate AI design review gives bounded approval to the prospectively registered `bulk-frame-hll-consistent-v1` experiment. Positive centroid-triangle source weights preserve constants and affine sources; quadratic donor reconstruction minus the receiver's quadratic term reproduces unlimited quadratic advection. The same per-component limiter factor must scale gradient and Hessian, including the receiver term. Constant-v/u manufactured full-rate identities are appropriate; variable velocity can make the source quadratic, for which refinement rather than exactness is required.

The reviewer independently assembled small unlimited scalar-advection matrices at N8/16, regular/jitter.15, with relative velocity (-2,-1), for historical linear, quadratic-only and consistent reconstructions. All twelve had no positive-real eigenvalue above1e-9 and Heun amplification at the existing .3 timestep bound at most1 plus roundoff. This is limited linearized evidence, not a nonlinear stability proof or justification to omit the unchanged coupled, temporal, positivity, boost, shock or vortex gates. Implementation review and full physical acceptance remain separate.


## Consistent-profile implementation review

At `cbc7d80`, with runner checks at `042392a`, the separate reviewer found no implementation blocker. Independently compiled comparisons against `62e3528` covered all four historical profiles, fixed/rigid/fluid motion, limited/unlimited reconstruction and six steps: all 24 evolutions preserved potential, phi, conserved states, generators and gauge offset bit for bit. A separate 24-case probe found exactly identical passive/general transport rates on regular/jittered rectangular meshes, constant/smooth/jump data and reversed cell IDs. Four selected Rust consistency tests, five completion-measurement tests and seven wave-measurement tests also passed independently. The full workspace has103 passing Rust tests.

This is bounded implementation/provenance approval, not physical accuracy or M1 acceptance. The probes at `cbc7d80` began before the later runner check requiring every successful snapshot and rechecking the binary digest; audit those frozen records explicitly before accepting their evidence.


## Cleaning-operator diagnosis and matched experiment

The independent reviewer verified raw snapshot hashes and found that the quadratic-only N128 final error is dominated by Bz/vz short-wavelength structure: RMS Bz error .00309 versus .0000886 in the linear profile. A weighted constant/sine/cosine fit leaves97.9% of Bz error energy outside the fundamental. This observation alone does not identify a unique cause.

Actual operator matrices establish positive modes of div_Q grad_linear on regular and jittered N8/16 meshes. With cell-radius damping included, the mixed cleaning subsystem has positive growth rates1.46475/2.92950 (regular) and .53217/1.11873 (jitter.15). LL and QQ controls are non-growing to roundoff in these samples. The regular N16 Fourier fixture and its magnetic curl injection are recorded in the prospective plan and a permanent Rust regression.

The reviewer gives bounded design approval to the separately registered matched-gradient experiment at83edecd. On irregular N16 jitter.15, the QQ curl-gradient operator is still nonzero (infinity norm40.23, versus99.93 for QL); no general cancellation or stability theorem is claimed. Only14.2% of the observed quadratic Bz error power lies in the regular-mesh QL positive-symbol region, so a controlled physical comparison remains necessary before assigning the entire nonlinear failure to mixed cleaning.

The matched implementation at `f9a11f0` received separate bounded implementation approval after independent reruns of both matched-cleaning tests. The complete workspace has105 passing Rust tests. The review sources, matrices, captured records, results and reproduction commands are preserved in [the AI archive](../tests/reference/m1_completion/README.md), with all included bytes verified against the reviewer's original inventory.

## Evidence archive review

Separate review initially withheld approval because projections were not sealed, measurement/reuse input digests were incompletely checked, terminal outcomes/artifacts were not required, and copying reread potentially changed bytes. Corrections bind projections to the sealed measured summary, validate captured reuse/input records, support both existing ledger schemas with consistent exit codes, require successful artifacts, preserve interruption controls, and publish only a completed private staging directory.

The reviewer approved the corrected archive script (SHA256 `f2d14825809d37492789a14773733fa1b5c6d26718ccb1755a388670d6101cc8`) within scope. Independently passed7 archive,5 completion and7 wave measurement tests; accepted a real completed48-run wave packet; rejected active/partial studies; and verified an end-to-end archive's9 compressed/uncompressed digests. Altered projections and existing destinations were rejected without publishing output. This approval covers ledgers/figure inputs with raw CSVs retained locally, not physical acceptance.
