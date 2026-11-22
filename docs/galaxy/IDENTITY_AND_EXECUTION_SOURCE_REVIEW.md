# Independent AI review: persistent identity and native REANA execution source

2026-11-22. **Source review completed; revise the two narrow items below before
the corresponding execution/integration claims.** The payload, registry and
ordinary serial allocation logic are otherwise supported by inspection. The
compile/list and native one-leaf route is a reasonable basis for the next
immutable REANA preflight. Nothing in this report is compilation, a test pass,
component acceptance or scientific-output approval.

The exact reviewed revision is
`8a25ebf9e70874b681e9c756f4c2db8a7ab8e9e1`. All line numbers below refer to its
Git blobs, retained separately from concurrent working files. I did not author
this identity implementation or the new compile/list/native job. I previously
reviewed the M1 metadata supervisor and M1 outputs; that adjacent authorship is
disclosed, and those older results are not execution evidence for these new
files. This is AI review, not human peer review.

M1 was already accepted at `309ae41f2e180c6f2cb87ab94615f8b60bb63244` for its
named periodic, single-process fixed/rigid 2.5D configuration. This report does
not reopen or expand it. Full deforming 3D MHD, gravity, ISM/SF and the live
gas/DM/old/new-star merger retain their own gates.

## Numbered findings and dispositions

### 1. Medium — qualify the stale-cursor claim and establish the imported-catalog high-water obligation

`docs/galaxy/IDENTITY_IMPLEMENTATION.md:112–118` correctly makes checkpoint
freshness a caller obligation, but then claims that a stale cursor against a
complete registry fails. That latter sentence is too broad. The exact allocator
candidate is checked only for namespace role and exact occupancy:
`identity.rs:290–306,392–407`; both public restore constructors copy a raw cursor
without validation (`429–436,469–476`). The registry legitimately permits sparse
imported payloads and out-of-order reconstruction.

Manual counterexample, **not executed**: register `ParticleId(EntityId(7,10))`,
then restore the raw real cursor `(7,Some(5))`. Counter 5 is free and the namespace
has the correct role. Registration succeeds, the cursor becomes 6, and allocation
has occurred below the imported high-water counter 10. The same argument applies
to events in an event namespace. No duplicate payload is created; this is an
unchecked global-monotonicity/restore-coherence condition, not a collision bypass.
The written `stale_real_checkpoint_is_rejected_without_advancement` and
`stale_event_checkpoint_is_rejected_without_advancement` controls
(`tests/identity.rs:451–496`) exercise an **occupied** candidate, so do not prove
the sparse case.

**Minimal resolution:** retain raw constructors if desired, but correct the
unconditional stale claim and state the exact import/restore precondition:
before authoritative allocation, the accepted cursor must be coherent with the
complete namespace/tombstone checkpoint and strictly above every previously
issued/imported counter in that namespace. If the maximum is `u64::MAX`, no next
counter exists and the allocator must be exhausted. A checked restore/import
boundary can enforce this; alternatively the consuming catalog must explicitly
perform and test it before first use. Reconstructing a registry in arbitrary
order must remain legal. Do not silently skip occupied candidates or outlaw
zero payloads as a repair.

This is a documentation correction now and a mandatory catalog-integration
obligation, not a demand for a new physical transaction system in this crate.
One sparse real/event high-water control at that chosen checked boundary, with
unchanged state on rejection and valid above-maximum continuation, is the
smallest justified REANA addition. The existing coherent-checkpoint proof remains
valid: within one stream, registration precedes checked increment; failed
registration leaves the cursor untouched; retained occupied/tombstone payloads
cannot be reissued.

### 2. Medium — preserve “launch may have occurred” when native supervision does not return

`reana/galaxy_test_case.py:221` initializes `command={'status':'not_launched'}`.
At `270–271`, the local command is replaced only after `supervise` returns.
`except BaseException` at `284–289` catches an escaping interruption, but the
external-evidence marker is set only when an existing cleanup field is exactly
False. With the initial object that field is absent. The finalizer then writes
the unchanged `not_launched` command at `292–298`.

There is a concrete reachable interruption window after process launch. The
unchanged supervisor catches `KeyboardInterrupt` during its primary wait, but
not an interrupt during its cleanup `finally`, including the TERM grace sleep
or subsequent writer scan (`reana_metadata_job.py:509–578`, specifically
`537–553`). If interrupted there, its local receipt does not return to the
new caller's assignment. The native job consequently publishes a failed result
with an inaccurate not-launched command and no required external-terminal flag,
although launch occurred and writer closure is unknown. This is a source-derived
trace, not an observed process leak or a false passing test. The old metadata
caller already addresses its side of this distinction with durable pending
intent before supervision (`reana_metadata_job.py:735–747,766–773`).

**Minimal repair in the new native caller:** persist the actual argv/cwd and
source/payload/binary/runtime linkage before entering supervision, marking launch
intent and writers unsettled. If supervision raises rather than returning a
closure receipt, preserve that state as a typed supervision failure/unknown
closure, set external terminal evidence required, and never recast it as
not-launched or settled. Retained log digests in that case are observations of
partial bytes, not closed-writer certification. No guessed PID/PGID, emergency
numeric signal or universal descendant recovery is required. The reused
supervisor need not be changed to make the new caller honest.

Add one REANA metadata control that interrupts/raises after the supervision call
has begun and verifies the durable intent, failed outcome and unknown-closure
marker. A prelaunch validation failure should continue to say not-launched.
This is required before releasing native leaf workflows. It need not block
ordinary identity source work or be described as a numerical-method failure.

### 3. Supported — lossless payloads, typing, registry exclusion and returned-error atomicity

`identity.rs:17–96` implements the declared namespace-first 32-hex encoding.
Each half consumes exactly 16 nibbles, so the accumulator fits its `u64` at every
step. Parsing measures bytes, rejects framing/non-ASCII/nonhex input, and accepts
uppercase hex without changing canonical output. Derived field ordering agrees
with fixed-width lowercase lexical ordering. All `u64` pairs, including `(0,0)`,
are intentionally representable.

The private-field wrappers (`99–141`) are distinct types with explicit extraction
and construction, without implicit cross-kind conversion. Raw construction is
not catalog validation. Registry role checks (`277–306`) prohibit event/real
namespace overlap even at different counters, and exact occupancy prohibits
cell/particle payload reuse. Checking occurs before either map is changed.
The registry has no removal/Clone API; canonical value iterators preserve empty
namespace reservations and issued tombstones. These conclusions assume one
authoritative serial registry and the declared caller-owned checkpoint/namespace
provenance; independent registry forks cannot be made globally unique by types.

The allocator registers before advancing with `checked_add`; MAX is issued once,
then `None` denotes exhaustion. Returned exhaustion/registry errors leave both
objects unchanged. This is single-request in-memory atomicity. The implementation
honestly excludes allocation panic, process/storage loss, authoritative trial
rollback, physical birth transactions and future distributed allocation. A
`ParticleId` is not a valid stellar population or a source event by itself.

### 4. Supported conditionally — compile/list and ordinary one-leaf semantics align with their sources

The new remote branch (`reana/remote.py:174–185`) is selected before legacy study
branches and returns exactly fmt, strict all-target/all-feature Clippy, release
workspace build, then the compile/list exporter with four build jobs. It does
not call the old aggregate numerical study. `expected_parent_commands`
(`galaxy_test_case.py:79–89`) matches those four commands, allowing only the
documented Python executable-name normalization.

The exporter (`galaxy_preflight.py:86–137,163–224`) selects successful Cargo test
artifacts, binds manifest/root-source/target/profile/features/executable, rejects
duplicates and path/link escapes, lists exact selectors in debug and release,
rejects ignored tests pending disposition, copies/hash-checks executables, and
fences the selected source inventory and snapshot before/after. Empty unit-test
targets can be recorded without inventing leaves; a wholly empty test catalog is
rejected. Failed compile/list paths do not produce a complete passing preflight.
The complete status is written before archive export but an export exception
rewrites it failed; parent return status and artifact closure must also be used.

The field meanings used by the parser agree with the official
[Cargo JSON-message contract](https://doc.rust-lang.org/cargo/reference/external-tools.html#json-messages),
including test-profile executable artifacts and the build-finished message.
Cargo JSON is build provenance, not a test result. The retained exact Rust
1.85.1 [console](https://github.com/rust-lang/rust/blob/1.85.1/library/test/src/console.rs#L173)
and [terse formatter](https://github.com/rust-lang/rust/blob/1.85.1/library/test/src/formatters/terse.rs#L187)
support `name: test` discovery without a terse footer. The exact
[pretty formatter](https://github.com/rust-lang/rust/blob/1.85.1/library/test/src/formatters/pretty.rs#L209)
supports the serial named completion and final counts consumed by the witness;
`--show-output` adds successful captured diagnostics before the final summary.
The source CLI supports the selected exact/thread/color/show-output options.
These are source checks for the declared ordinary ASCII libtest targets, not an
observed Rust 1.85.1 run or a universal parser for custom harnesses.

The native input path (`galaxy_test_case.py:92–196,227–280`) ties the job and
supervisor to the snapshot, the parent source/catalog to captured prerequisite
commands and artifact digests, the selected leaf to a unique binary/catalog
record and its listing argv, and binary parts to actual uploaded bytes. It
reassembles the hash/size-checked executable and requests exactly one selector
with one test/Rayon/FFI thread. Passing requires supervised return0, reaped direct
child, stopped writers, a matching one-pass/zero-failure/zero-ignored witness and
unchanged inputs. This supports the ordinary success path, subject to finding 2
and actual future execution evidence.

The unchanged supervisor is SHA256
`8d8a39844b631eb17d46f897bea71ae2464be1e400c75a54dd6c091a1fd2dbc3`,
identical to the accepted context. Its prior actual Linux REANA evidence supports
reuse of that implementation, not a pass of this new caller. It requires held
unreaped leader identity/`WNOWAIT`, private PID/PGID/SID authority and same-UID
process/writable-log-FD observation. It does not certify arbitrary daemon escapes,
UID changes, host/pod/interpreter loss, infrastructure cleanup or resource
reservations. Direct-child timeout excludes validation/extraction/finalization.
The parent exporter also explicitly retains interrupted commands as needing
external terminal evidence; its subprocess timeout is not group containment.

### 5. Open integration items — explicitly pending, not delivered execution defects or passes

At this revision the root workspace does not yet include `galaxy-types`
(`Cargo.toml:2`); the implementation note explicitly says root owns this addition
(`IDENTITY_IMPLEMENTATION.md:15–17`). The compile/list job can complete against
the old workspace while discovering no new identity leaf. Therefore the reviewed
release selection must require the actual new package/target and the complete
expected 23 identity names (per selected build profile), rather than treating any
nonempty workspace catalog as identity coverage. Integrate the crate/dependencies
and coherent lock/source inventory before freezing the real build.

The snapshot addition includes `tools/` and the existing upload-boundary method
now names the reused supervisor and rejects `tools/.env.private`
(`prepare_reana.py:14–36`, `test_reana.py:48–59`). No private input was inspected.
This preserves the existing selected-file packaging policy; it is not an audit
or certification of every possible secret filename.

The new job's eight download filenames intentionally match the old read-only
adapter allowlist, but its native result/libtest witness are **different schemas**.
The old Python-child output validator must not certify them. Future case
preparation and native output acquisition must bind original source, actual
preflight/export, binary/catalog/selector, case/payload, actual server UUID/version
and all eight downloaded bodies, validating the native schemas and supervision
receipt. The present server observation checks a uniquely finished version1 by
name/status; it is not itself a transport certificate or original UUID receipt.
Those downstream pieces are openly pending, so this report does not label their
absence as a newly discovered completed-path failure.

The standalone target filter correctly excludes the existing old restart tests
with embedded `CARGO_BIN_EXE` absolute paths (`galaxy_test_case.py:175–180`). The
new pure identity crate is dependency-free. Future gravity and geometry targets
must additionally have their actual filesystem/dynamic/runtime dependencies
checked during case preparation; naming a manifest does not prove portability.
This review does not assess the concurrent gravity/geometry implementation.

## Written-test assessment and smallest next execution

I read all **23 Rust controls** against the actual API. The first eight cover
encoding/framing/ASCII/ordering/traits/wrappers; four cover registry collisions
and namespace reservations; four cover shared real/event streams and MAX
exhaustion; seven cover restart/exhaustion, occupied stale cursors, namespace
failure atomicity, raw checkpoint states and canonical registry export. They
use deterministic literal inputs and do not claim physical catalog validity.
The TypeId checks establish different Rust types; absence of implicit conversion
is a separate source property. Finding 1 is the missing sparse high-water scope.

I read all **16 Python metadata controls**: ten Cargo/list/source parsers and six
libtest witnesses. Their placeholders and strings are explicitly nonphysical and
do not execute Rust. Positive parser controls are present; the malformed Cargo
fixtures preserve the successful artifact while varying the intended completion,
duplicate or path condition. Witness negatives retain an otherwise valid shape
while mutating counts, selector, aggregate/duplicate completion or summary. The
bench/execution-output rejection is deliberate. None exercises the complete
native `validate_inputs`/`run` path, real Cargo execution, process cleanup or
upload/server/download identity. The additional assertions in the old
upload-boundary method are also unexecuted here.

After the two scoped corrections and normal root integration, the necessary
next evidence is concrete:

1. Freeze coherent source and selected cases, including the new metadata
   controls' separate REANA execution route. Add the targeted high-water and
   supervision-exception controls where their corresponding boundary lives.
   A labelled nonphysical valid dependency fixture plus a wrong binary/catalog
   binding is useful to exercise the currently untested native dependency path;
   it must not masquerade as a successful real preflight.
2. Run the actual source/build/import prerequisite on REANA, with explicit
   resource declarations and actual runtime/cgroup observations. Inspect the
   real Rust 1.85.1 compile/list/output/export bytes and the selected new target
   inventory. The proposed four-CPU/8Gi build resources and per-leaf 1CPU/2Gi/180s
   remain declarations, not capability or hard-reservation observations.
3. Prepare checksum/UUID-bound inputs and run each selected metadata/native
   method in its own resource-declared REANA workflow. Acquire and independently
   assess exact one-leaf results, raw logs, input/catalog/binary/runtime linkage
   and stopped-writer receipts. A native test pass is not component/physical
   acceptance. Literal geometry/gravity oracles and their numerical gates remain
   separate from this identity/execution source review.

No new abstract source-approval loop is requested absent a material correction;
the outstanding source fixes are the specific items 1–2 above. No fmt, Clippy,
Cargo build/test/list, target Python import, guard, fixture, native method or
workflow was executed for this review.

## Reviewed-byte and receipt boundary

The companion `identity_and_execution_review_sources.json` pins all 27 captured
Git source/context blobs, 23/16 exact selectors, primary-byte identities, this
report and the closed reading boundary. Key delivered source SHA256 values:

| Frozen subject | Bytes | SHA256 |
| --- | ---: | --- |
| `crates/galaxy-types/src/identity.rs` | 14951 | `b2dad224dae53dcb51f1b8729120b44e85ff3c12ebebdee8b6e61d04031bed0e` |
| `crates/galaxy-types/tests/identity.rs` | 21401 | `31e3d9848e0a4780df9ac77d479bb29f45484b41586897f3c3680668c85e4d8f` |
| `reana/galaxy_preflight.py` | 12270 | `ea2fe3fbf5356a71f25a1dc7fca9bda4caf354c17d1bae934638886af2469f6c` |
| `reana/galaxy_test_case.py` | 17140 | `f61b15baba25d2d433d83c925bc5c76c9371e7ec5ff47f9425fb04d9808e0615` |
| `scripts/test_galaxy_preflight.py` | 10970 | `9ba5c5f4c300aceb1de787405289648bef5223ec42b63087246524d1e00c9045` |

Retained boundary:
`results/galaxy_identity_execution_review_20261122/sha256.json`, **42 body files,
762604 body bytes**, manifest SHA256
`e34dc84cc0ee56f2e19656de9d8b8a76a1b9f5d0519ee752a2c5c321c19ec7e7`.
It includes exact committed source, complete official primary bytes, inert
capture/AST/hash scripts and manual traces. The report pins that earlier closure;
the companion inventory can subsequently pin the report without a hash cycle.

Actual static receipt: **54 checks, errors=[]**, including exact Git captures,
selector counts/uniqueness, unchanged supervisor, primary byte identities and
scoped `git diff --check` return0. Some combined reading outputs were truncated;
relevant omitted portions were reread in bounded calls. A wholly truncated
earlier inspection response is not counted as a passing check. No failed target
test, numerical result or newly observed runtime capability was produced. The
author's separately reported host `tomllib` inspection failure remains historical
and is not relabelled a build/test failure.

Recommendation: **conditionally support this narrow identity and execution
source direction, with findings 1–2 resolved at the stated boundaries and all
actual REANA/source/output prerequisites retained.** This grants no component,
gravity, 3D, ISM or merger acceptance and does not alter scoped M1 acceptance.
