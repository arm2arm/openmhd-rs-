# Static candidate execution and Cargo configuration correction

This source revision prepares actual static geometry comparisons and corrects
an observed standalone-build failure. It changes no Rust scientific kernel,
registered error threshold, reference arithmetic, M1 scope or historical packet.
The new code and nine new controls are unexecuted until the REANA results say
otherwise. Root is the sole coding/review agent for this revision.

## Observed Cargo failure

The original standalone build used source
`2900bbe3efc8500c16a79a16e918a3293a12ce30`, workflow
`openmhd-driverbuild-2900bbe-a01.1`, UUID
`6de1c87c-9971-446c-b3ca-665bd752f8e1`. Preparation succeeded. The actual
supervised `rustc -Vv` returned zero with closed writers. The following
geometry Cargo command returned 101 before compilation because the old
`--config env.RUSTC={value=...,force=true,relative=false}` argument set an inline
table. Gravity compilation and numerical execution were never reached.

Original receipts, raw logs, authoritative failed-state observations and the
GET-only forensic captures remain in the original checkout under
`results/galaxy_standalone_driver_build_execution_20261123_attempt01/`.
Two attempted failure-only artifact names were absent and their nonzero GETs
remain nonpassing; the actual failure closure is `files.sha256.json`.

The correction retains the direct environment selection and the three
`build.rustc*` overrides. Each of the six forced environment entries is now
expressed with separate dotted `.value`, `.force` and `.relative` scalar
overrides. The producer, preparer pin and record validator use the same revised
argv contract. The previous source remains available for reading the failed
packet; the new validator is for the new builder source, not a reinterpretation
of that failure.

Primary support is Cargo's [0.86 configuration parser](https://github.com/rust-lang/cargo/blob/0.86.0/src/cargo/util/context/mod.rs)
and its [configuration reference](https://github.com/rust-lang/cargo/blob/0.86.0/src/doc/src/reference/config.md).
The parser accepts dotted-key expressions ending in scalar values and explicitly
rejects inline-table values. These source checks do not substitute for an actual
successful invocation of the pinned Cargo 1.85.1 executable.

## One-case geometry wrapper

`reana/galaxy_geometry3_candidate_case.py` consumes a once-rounded literal input,
its independently acquired exact reference, the exported standalone executable
as contiguous one-MiB parts and an explicit root release. It retains the
original held-leader supervisor, durable launcher, bridge, design and reducer
source hashes. It launches the actual executable once with one thread, checks
successful child/writer closure, then evaluates the existing eight exact-error
gates on REANA. Failed, missing and unresolved gates remain nonpassing.

The standard eight output files retain runtime, original command/partial logs,
raw candidate stdout and the full comparison. A supervisor exception preserves
unknown closure and does not authorize arithmetic. The 300-second timeout covers
the direct candidate wait; it is not a claimed whole-job arithmetic deadline.

Release inputs name separately scoped original318, later90, native186,
standalone-build, reference252 and wrapper-control output reviews plus M1.
These digests supply internal links. The remote wrapper explicitly does not
authenticate external server observations or grant component acceptance. Root
must check the actual build/source/binary/UUID/input/reference joins before
submission and review the resulting outputs afterward.

No moving trajectory, fluid/MHD state or gravity is manufactured. Actual static
candidate transcripts may later be rendered by the existing reviewed
`scripts/plot_geometry3.py` on REANA. The earlier 3D motion illustration remains
an illustration, not candidate numerical evidence.

## Validation scope

The selected later cohort has 79 ordinary direct unittest methods: 29 builder,
13 preparer, 28 record-validator and nine new geometry-wrapper controls. The
registry change selects this cohort only; all parent execution/validation
machinery is otherwise unchanged. The complete original318 and provider90
proofs remain separate external prerequisites.

The new controls use visibly incomplete nonphysical metadata and unexecuted
dummy binary bytes. They test actual-input bindings, retained failure envelopes,
unknown supervision, exact gate inventories and optimized-execution rejection.
They do not construct a passing complete physical packet. All new imports,
methods, actual Cargo builds, geometry evaluations and plotting must run on
REANA after the required immutable source/import and output checks.
