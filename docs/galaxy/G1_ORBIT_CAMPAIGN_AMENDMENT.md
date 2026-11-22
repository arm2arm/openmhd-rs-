# G1 orbit campaign: protected ceiling and additional actual-step ladder

2026-11-22. **Preregistered campaign amendment and manual mathematics only.**
No period, force, endpoint, guard, test or orbit was evaluated in this author
task. M1 acceptance at `309ae41f2e180c6f2cb87ab94615f8b60bb63244` retains
its periodic fixed/rigid single-process 2.5D scope. Gravity, 3D moving-MHD,
ISM and merger acceptance remain open.

This implements the coordinator's disposition of finding 1 in the complete
[independent G1 source review](G1_SOURCE_REVIEW.md), committed at
`3e525cc79d21f0baad40ae270b2f553b744d4962` for gravity subject
`8fe734268deee3fe5b6a33d868b2bfeaece06a7b`. That historical review and the
original manual proposals remain unchanged. This author wrote the gravity
implementation; this amendment is not an independent approval of it.

## Decision and retained history

The production `timestep_ceiling` and `KdkSystem::try_step` API are unchanged:

```text
h_max = (1/20)*sqrt(epsilon^3/(G*M_total)),
positive supplied actual integration h > h_max -> StepAboveCeiling.
```

There is no bypass, relaxed ceiling, calibration entrypoint, clipping,
automatic retry or hidden subcycling. An output interval containing smaller
steps cannot be labelled an actual integration step of the original size.

Keep the same isolated common-Plummer circular-binary target: dimensionless
G=1, d=1, m=(1,2), epsilon=.1, fixed masses/epsilon and a 100-period duration.
The two ladder roles are explicit:

| Ladder | Role with the existing protected API | Required evidence |
| --- | --- | --- |
| Original actual h = T/{128,256,512,1024} | Retained history and deliberately infeasible integration requests; all four require rejection observations, never orbit evolutions under those labels. | Actual supplied period/step bits, ceiling observation, typed `StepAboveCeiling`, unchanged accepted checkpoint/time/revision after each rejected request. |
| Additional actual h = T/{8192,16384,32768,65536} | Preregistered integration ladder, symbolically below the ideal ceiling; no actual binary64 feasibility or orbit pass is asserted. | Independently frozen actual rounded inputs, period/momentum/endpoint references and uncertainty; observed guards; then one independent 100-period integration workflow per level after all prerequisites. |

The additional four levels are actual KDK step arguments. They are not output
cadences or a relabelling of substeps. Fit the temporal order over the finest
three added levels, T/{16384,32768,65536}, after all four levels and their
reference comparisons are complete. The old four requests remain in the
campaign record with rejection outcomes; they contribute no orbit trajectory
or fitted order. A documented expected rejection can pass its negative
control, not the physical orbit gate.

## Independent symbolic feasibility check

From unchanged GP-3, with M=m1+m2, a circular softened relative orbit obeys
`omega^2=G*M/(d^2+epsilon^2)^(3/2)`. Thus, for positive ideal parameters,

```text
T = 2*pi*(d^2+epsilon^2)^(3/4)/sqrt(G*M),
h_max = epsilon^(3/2)/(20*sqrt(G*M)),
(T/n)/h_max = (40*pi/n)*(1+(d/epsilon)^2)^(3/4).
```

For ideal d=1, epsilon=1/10, the last factor is `101^(3/4)`. For the finest
original level n=1024,

```text
(T/1024)/h_max = (5*pi/128)*101^(3/4)
 > (5*3/128)*100^(3/4)
 = (15/128)*10*sqrt(10)
 > 450/128 > 1.
```

Only `pi>3` and `sqrt(10)>3` are used. The original n=128,256,512 steps are
larger still, so none of the original four can evolve under the fixed guard.
This is a policy incompatibility, not an observed KDK accuracy failure.

For the coarsest added level n=8192, use `pi<4` and monotonicity of the
positive three-quarter power:

```text
(T/8192)/h_max = (5*pi/1024)*101^(3/4)
 < (5*4/1024)*144^(3/4)
 = (20/1024)*12*sqrt(12)
 < (20/1024)*48 = 15/16 < 1.
```

Here `sqrt(12)<4`; each finer added level halves the ideal ratio. The common
factor `sqrt(G*M)` cancels, so the symbolic comparison does not require
evaluating it or the orbital period.

These strict ideal bounds show a symbolic feasibility margin only. Binary64
epsilon=.1 is the actually rounded dyadic input, not exact 1/10; period,
initial COM positions/momenta, guard arithmetic, step bits and accumulated
clock/endpoints also round. No evaluated or interval-enclosed certificate for
those actual operations is supplied here. Their independently bounded
reference packet and actual guard observations remain prerequisites. The
manual margin is not a replacement for that packet or a claim that a
production solver has passed it.

## Preserved physical gates and execution boundary

All original comparisons remain: the same 100-period softened circular
target, at least four integration levels, finest-three phase/position order
`>=1.8` with the declared fit/uncertainty, finest maximum energy excursion
`<1e-4 E_scale`, COM/P/L `<1e-11` of the fixed scales, no secular energy trend
larger than the excursion, and fixed-list reversibility `<1e-10`. The
independent eccentric/plunge reference and G-BOOST/RESTART comparisons remain
required: matched deboosted state `<1e-10` and same-binary accepted-full-step
restart bit identity including the applicable IDs/epochs/events, or a retained
failure cause. Reference uncertainties, cancellation/roundoff scales and all
other parent gates are unchanged. No raw force, momentum, torque or energy
repair is allowed.

Before a long level runs, its independent packet must pin the actual rounded
period, ICs, primary momenta, supplied h, complete accepted h/clock history,
100-period endpoint convention and high-precision comparison at actual
rounded endpoint inputs. Ideal symbolic endpoints and force-at-rounded-state
references stay separate. No candidate kernel supplies its own independent
orbit reference. Rounded final-time handling cannot introduce undeclared
clipping/substeps or change the claimed integration ladder. No numerical
literal/reference generation is part of this amendment.

After narrow independent revision review, coherent source/input/reference
freeze and mandatory immutable format/strict-Clippy/build/selector preflight,
each eligible written method and each long level is its own REANA workflow
with explicit resources. The existing written-control request is
1 CPU/1 GiB/180 seconds/one test thread; prospective long-orbit requests remain
1 CPU/1 GiB with the parent's one-hour ceiling, subject to bounded cost
preparation before release. These are unmeasured declarations. If they are
insufficient, retain the timeout/failure and revise resources before another
attempt without changing scientific thresholds. No long campaign starts
before the independent reference/prerequisite gates pass; ready independent
cases have no aggregate scheduling cap.

## Written branch controls and review dispositions

In test target `reference`, the existing selector
`rejected_dt_and_revision_leave_complete_accepted_state_unchanged`
is strengthened without renaming it. In addition to its
original dt/revision negatives it constructs masses1,2 separated by1 with
epsilon=.1 and uses a `std::f64::consts::PI`/`powf`/`sqrt` period expression
only to exercise the four original guard requests. Resting momenta are
deliberate: the ceiling depends on total mass/epsilon, and the control is
not a circular-orbit IC. It checks each h exceeds the observed ceiling,
requires `StepAboveCeiling`, and checks byte-identical accepted checkpoint,
time bits and revision after each attempt. This unexecuted small method
cannot supply an independent period/orbit reference or any passing evolution.

Finding 2 is also explicit: `KdkSystem::new` accepts an empty checked catalog,
but a positive finite empty `try_step` returns `EmptyTimestep` without advancing.
The existing `empty_catalog_has_no_pairs_and_no_com_or_timestep` selector
in target `reference` retains its original force/COM/ceiling assertions and additionally
checks that public KDK branch and unchanged checkpoint/time/revision.
All **39 original direct selector names** remain; actual compiled discovery
and execution are still pending.

| Independent finding | Author disposition | Evidence still required |
| --- | --- | --- |
| 1, high: original orbit ladder violates the unconditional ceiling | Ceiling and production code unchanged; old requests retained as rejection controls; additional actual-step ladder registered with unchanged duration/accuracy/conservation/reference gates. | Independent revision review, actual rounded-input/reference certificate, observed guard outcomes and all four independent long evolutions/comparisons. |
| 2, low: empty KDK step branch implicit/untested | Explicit `EmptyTimestep` policy and strengthened existing empty test; no free-empty integrator or artificial mass scale. | Immutable preflight and actual independent execution/output inspection of that existing selector. |

The exact current source/test/doc receipts and preserved historical inventory
are recorded in [SOURCE_INSPECTION.json](../../crates/gravity/SOURCE_INSPECTION.json).
No production Rust, API, GP equation, historical review or M1 evidence is
changed. This author correction does not accept gravity, coupled gas/source
work, equilibrium, bounded/deforming nonzero-MHD or the full live
gas/DM/old/new-star ISM/feedback merger.
