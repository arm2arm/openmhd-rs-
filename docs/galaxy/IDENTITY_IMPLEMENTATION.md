# Persistent identity implementation slice

2026-11-22. Source revised after independent review; **all 26 written tests are unexecuted**.
The new dependency-free `galaxy-types` crate implements persistent identity only.
It does not implement geometry, gravity, source physics, checkpoint files or MPI
allocation. M1's scoped acceptance at
`309ae41f2e180c6f2cb87ab94615f8b60bb63244` covers the named periodic,
single-process fixed/rigid 2.5D profile. It does not accept this component or the
full moving-3D galaxy goal.

The API follows [the integration contract](INTEGRATION_CONTRACT.md#identity-and-immutable-views),
[mesh identities](MESH_3D_SPEC.md#21-types-ownership-and-epochs) and
[gravity identities](GRAVITY_PARTICLES_SPEC.md#3-persistent-state-identity-and-api-boundary).
The crate has module `identity`; every public type is also re-exported at its root.
No existing crate, root workspace manifest/lock or M1 evidence was edited by this
worker. Root must add workspace membership before building the crate, whose
edition, MSRV, license, repository and lints inherit workspace settings.

## Public API and encoding

`EntityId` has private `u64` namespace/counter fields, derived
`Clone/Copy/Eq/Ord/Hash/Debug` (and the corresponding partial traits), and these
constant functions:

```text
EntityId::new(namespace: u64, counter: u64) -> EntityId
EntityId::namespace(self) -> u64
EntityId::counter(self) -> u64
```

All payloads, including `(0, 0)` and `(u64::MAX, u64::MAX)`, are representable.
Ordering compares namespace first, counter second. `Display` produces exactly
32 lower-case ASCII hexadecimal digits: 16 namespace digits, then 16 counter
digits. `FromStr` accepts exactly 32 ASCII hex bytes, including upper-case or
mixed-case input, and canonicalizes through `Display`. It rejects signs,
prefixes, separators, whitespace, non-hex bytes and non-ASCII characters without
trimming. `ParseEntityIdError` distinguishes `InvalidLength { actual }` in bytes
from `InvalidHex { index }`, a zero-based byte position. It retains no input.

`CellId`, `ParticleId` and `EventId` are distinct private-field newtypes with the
same derived traits, `const new(EntityId) -> Self`, and
`const entity(self) -> EntityId`. They have no implicit `From` conversions;
cross-kind use requires an explicit extraction and construction that remains
subject to registry rejection. The particle wrapper does not select DM versus
stellar species. Constructors express kind and preserve payloads; they do not
certify provenance, a valid catalog, physical state or uniqueness.

There is no serde/JSON adapter, numeric `u128` conversion, raw-memory format or
external dependency in this slice. A future serializer must use lossless ID text,
not a JSON number; allocator `u64` fields also require lossless external encoding.
Do not persist a `Hash` output or an assumed Rust struct layout as identity.
Periodic images and ghosts refer to the real owner's ID plus a separate image
key; they do not allocate real IDs.

## Checked registry and allocator contracts

`IdentityRegistry::new()` and `Default` produce an empty authoritative serial
registry. `reserve_namespace(namespace, NamespaceKind)` reserves an explicit
manifest namespace even before an ID is issued. Repeating the same role is
idempotent; changing between `RealEntity` and `Event` is an error. Cells and
particles may share a real namespace; no event may use that namespace, even
with a different counter. Namespace zero is valid for either role, subject to
this same exclusion.

`register_cell`, `register_particle` and `register_event` accept the respective
typed IDs. They check namespace role before payload occupancy. A repeated same
kind returns `RegistryError::DuplicateId`; reinterpreting a cell payload as a
particle, or the reverse, returns `PayloadKindCollision`. Event/real overlap
returns `NamespaceCollision`, including for an equal payload. Every returned
error leaves both registry maps unchanged. Successful registration records both
namespace role and payload kind. There is no removal or `Clone` API: all issued
IDs remain reserved when the physical object retires.

Read-only APIs are `kind(EntityId)`, `namespace_kind(u64)`, `len()`, `is_empty()`,
`entries()` and `namespaces()`. Iteration is canonical ascending payload or
namespace order. `is_empty()` counts issued IDs; reserved empty namespaces do
not make it false. Iterators export values without permitting catalog mutation.

The allocators are distinct non-`Clone` types:

```text
SerialEntityAllocator::new(namespace: u64, next_counter: u64) -> Self
SerialEntityAllocator::from_checkpoint(EntityAllocatorCheckpoint) -> Self
SerialEntityAllocator::restore_checked(EntityAllocatorCheckpoint, &IdentityRegistry)
    -> Result<Self, CheckpointError>
SerialEntityAllocator::checkpoint(&self) -> EntityAllocatorCheckpoint
SerialEntityAllocator::allocate_cell(&mut self, &mut IdentityRegistry)
    -> Result<CellId, AllocationError>
SerialEntityAllocator::allocate_particle(&mut self, &mut IdentityRegistry)
    -> Result<ParticleId, AllocationError>

SerialEventAllocator::new(namespace: u64, next_counter: u64) -> Self
SerialEventAllocator::from_checkpoint(EventAllocatorCheckpoint) -> Self
SerialEventAllocator::restore_checked(EventAllocatorCheckpoint, &IdentityRegistry)
    -> Result<Self, CheckpointError>
SerialEventAllocator::checkpoint(&self) -> EventAllocatorCheckpoint
SerialEventAllocator::allocate_event(&mut self, &mut IdentityRegistry)
    -> Result<EventId, AllocationError>
```

Both checkpoint types have private fields and `const new(namespace,
next_counter: Option<u64>)`, `namespace()` and `next_counter()`. The distinct
checkpoint types prevent accidentally restoring event state as real-entity
state. `Some(0)` starts at zero, `Some(u64::MAX)` permits that last payload once,
and `None` means permanently exhausted. No payload is an exhaustion sentinel.

Cells and particles consume one shared real-entity stream. Each allocation
checks exhaustion, registers exactly its current candidate, then performs
`checked_add(1)`. It never wraps or skips an occupied counter. Counter MAX
transitions to `None` after successful registration. `AllocationError` is either
`Exhausted { namespace }` or `Registry(RegistryError)`; on either returned error,
both cursor and registry remain unchanged. This is single-request in-memory
atomicity. It does not cover memory allocation failure, panic, process loss,
file publication or a physical/source transaction.

Namespace assignment and checkpoint provenance/completeness are caller obligations. Restore
the allocator states **and the complete namespace/issued-ID registry**, including
retired IDs and empty reservations, from the same accepted checkpoint. Rebuild
the registry through the checked reservation/registration methods in any order.
At the imported-catalog boundary, use `restore_checked` before authoritative
allocation. It checks the namespace role and requires `Some(next)` to be strictly
above every retained counter in that namespace. If an issued counter is MAX,
only `None` is coherent. `None` also permits conservative early retirement.
Errors leave the supplied checkpoint and registry unchanged; a successful check
does not add a reservation or an ID. `CheckpointError` distinguishes a registry
role error from `CounterNotAboveHighWater` with the actual candidate/maximum.

The raw `new` and `from_checkpoint` constructors retain their explicit caller
preconditions. Their later allocation rejects an occupied candidate, but does
not detect a free hole below a sparse imported high-water counter. The original
two stale-checkpoint controls test this occupied-candidate guarantee only. A
registry containing counter10 and a raw cursor5 is the review's supported
counterexample to the former broader claim. The new checked boundary rejects
that pair. Use one authoritative allocator per namespace; if further IDs are
imported, check a coherent checkpoint again before resuming allocation. Restoring
only live objects can lose protection against retired/missing payloads, and no
method can infer omitted history. Two independently forked registries or
fabricated checkpoints cannot be made globally unique by Rust wrapper types.
Do not allocate against the authoritative registry during a trial step. A future
source transaction must commit physical state, cursors and registry together, or
restore their coherent accepted checkpoint; this crate supplies no transaction
implementation. Accepted-endpoint births, lineage and rollback semantics remain
owned by the integration/source contracts.

## Written test selectors and execution prerequisites

All selectors below are top-level tests in `crates/galaxy-types/tests/identity.rs`,
not generated or module-prefixed cases. After root integration and an immutable
REANA source/build preflight, each independent workflow should select exactly
one with the following command shape (shown only; **not executed**):

```text
cargo test -p galaxy-types --test identity <selector> -- --exact
```

Prospective per-case declarations: 1 CPU, 2 GiB memory, 180 seconds; no aggregate
scheduling cap. These are proposed declarations, not measured reservations or
runtime observations. Root must review/build the coherent integrated source,
inventory the actual test binary and collect each independent result. No
workflow or execution is included in this delivery.

```text
entity_id_encodes_zero_and_max_payloads
entity_id_canonical_namespace_counter_layout
entity_id_parses_uppercase_and_mixed_case
entity_id_round_trips_canonical_text
entity_id_rejects_wrong_lengths_and_framing
entity_id_rejects_non_ascii_and_non_hex
entity_id_order_is_namespace_then_counter
kind_wrappers_are_distinct_and_preserve_payload
registry_rejects_cell_particle_payload_collision
registry_rejects_duplicate_ids_for_each_kind
registry_rejects_event_real_namespace_overlap_both_orders
namespace_reservations_are_checked_and_atomic
real_allocator_shares_cell_particle_counter_stream
event_allocator_has_separate_sequence_and_checkpoint
real_allocator_issues_max_once_then_stays_exhausted
event_allocator_exhaustion_is_atomic
real_allocator_restart_does_not_reuse_ids
event_allocator_restart_preserves_exhaustion
stale_real_checkpoint_is_rejected_without_advancement
stale_event_checkpoint_is_rejected_without_advancement
allocator_namespace_failure_preserves_allocator_and_registry
allocator_checkpoints_preserve_zero_max_and_exhausted_states
registry_iteration_is_canonical_for_checkpoint_export
checked_real_restore_rejects_sparse_cursor_and_continues_above_high_water
checked_event_restore_rejects_sparse_cursor_and_continues_above_high_water
checked_restore_maximum_and_namespace_guards_are_atomic
```

The written controls cover exact byte layout and mixed-case parsing, malformed
and non-ASCII inputs, ordering/trait availability, distinct type identities,
cross-kind and namespace collisions in both orders, empty reservations, shared
real counters, event independence, zero/MAX/exhausted states, repeated failed
allocations, coherent registry reconstruction, occupied stale-candidate rejection,
and checked sparse high-water restoration for real and event streams. The new
controls also cover above-maximum continuation, MAX exhaustion, wrong namespace
roles, unchanged state on rejection and an empty-registry zero/MAX start.
`TypeId` checks distinguish wrappers; they do not prove absence of a conversion
implementation. The latter is a source-inspected API property. No test substitutes
a plausible physical catalog or numerical evolution for these identity checks.

## Source-only delivery receipt

The original four crate files had these identities at `8a25ebf`, before the
checkpoint revision below. This historical table is not the current source map:

| Path under `crates/galaxy-types/` | Bytes | SHA256 |
| --- | ---: | --- |
| `Cargo.toml` | 272 | `7319fbe5e00208516975bce71e43ff7924f168b33611e0d78d7e618f906ea43d` |
| `src/lib.rs` | 659 | `32137b8217f3632dbfa88a856505c1bf8a0a81dac573ed63407a1b00f3479877` |
| `src/identity.rs` | 14951 | `b2dad224dae53dcb51f1b8729120b44e85ff3c12ebebdee8b6e61d04031bed0e` |
| `tests/identity.rs` | 21401 | `31e3d9848e0a4780df9ac77d479bb29f45484b41586897f3c3680668c85e4d8f` |

Actual local checks were read-only Git context inspection, manual Rust/control
flow review, UTF-8/newline/CR/tab/trailing-whitespace checks, SHA256/byte counts,
literal manifest sections/name, 23 distinct direct test selectors, root/module
exports, private ID fields, absence of dependencies/implicit conversions/removal
APIs, and registration preceding checked cursor advancement. These checks are
not Rust parsing, compilation, formatting, linting or test execution.

One inspection returned 1 because host `python3` lacks stdlib `tomllib`. No
package was installed and no Cargo command was used to replace it. A subsequent
stdlib-only source inventory returned 0 with `errors=[]`, using explicit
manifest literal checks and manual review instead of claiming a TOML parser
result. An earlier bundled reading output was truncated; gravity identity
sections and full NUMERICS/VALIDATION were reread in bounded calls. No failed
test or numerical result was generated by either inspection limitation.

Entry source context is commit `309ae41f2e180c6f2cb87ab94615f8b60bb63244`:

| Context | Bytes | SHA256 |
| --- | ---: | --- |
| `AGENTS.md` | 7625 | `4bf524832c62d83e84310c44e77e05e12213778d95c970e7b2b7b876e7cb0630` |
| `README.md` | 27864 | `534dde576c0777d72b66b45a82afde27b8db5520f40616e067f88bd1a512a7cf` |
| `docs/CODEX_HANDOFF.md` | 152337 | `c6b04b512507cd06d3c5f4d1df1494baee385eae08e711b4e75262aea299e4d1` |
| `docs/ROADMAP.md` | 10929 | `fb51095176fad9e99a1693262a09e30e356611aca4fffae7c40aefd7b715d938` |
| `docs/NUMERICS.md` | 5489 | `ec98427dad7466f165a8a7ba715913e9e4f0fbaf9a9521b12a9c91acfceb492c` |
| `docs/VALIDATION.md` | 20179 | `f79380a2a8bb0a8ea9b2bf05d23104921acef509c608b7e0635b6edbaad6e9c3` |
| `docs/galaxy/INTEGRATION_CONTRACT.md` | 14105 | `1c40c8eb67865585a7bb4bee83d75b537250c5862a838d3f7696ee9c9dc99abf` |
| `docs/galaxy/MESH_3D_SPEC.md` | 79538 | `32e5ed2af3097c8106896fcb262a751ee37fe06dbf927f510e03952b5826b4ac` |
| `docs/galaxy/GRAVITY_PARTICLES_SPEC.md` | 69623 | `15e71e81db4a59ed14bc38897af2178e08a539f6e6af6353cea3a875ee35d6a9` |
| Root `Cargo.toml` | 393 | `aede8b0c436da5b3a57cfa6af3236c7fc358d352ec7d430214476a25890030c1` |
| Root `Cargo.lock` | 20266 | `ea820fe794263bf916f63b11b0ff2f5db48c321b28774ebba3652d6e2bbdaa9d` |
| `rust-toolchain.toml` | 86 | `b323b19900e4b811af0a8facce5ec11249ed135ae5a46ff5c0be90067521e11f` |

During this task root advanced HEAD to
`15ae7f5e0de6ae441eef51be21ca9c1d038ea06b`. The integration-contract delta was
read: it replaces historical pending-M1 wording with the accepted archive link;
its identity interfaces are unchanged. The table pins entry bytes, not later
concurrent edits. Other workers' changes are outside this delivery.

Independent source review, root workspace integration and REANA format/lint/
build/per-selector results remain required before component acceptance. Static
3D geometry, moving/bounded MHD, gravity/work, stable component ICs, gas/ISM/
accepted-endpoint stars and full-duration domain-controlled magnetized merger
validation retain their own unresolved gates.

## Checkpoint review disposition

The independent [identity/execution source review](IDENTITY_AND_EXECUTION_SOURCE_REVIEW.md)
finding1 is addressed in source by the qualified occupied-candidate guarantee
and `restore_checked` for both allocator kinds. The registry's full namespace
range, rather than map length, insertion order or active objects, determines
the high-water counter. Existing raw constructors and the original23 selectors
remain available, and no ID is skipped, wrapped or silently repaired. Three
new selectors bring the written identity inventory to26. No numerical source
or M1 archive is changed by this revision.

This disposition records an implementation decision, not its independent
approval. Source review of the revision, root integration, immutable REANA
format/lint/build preflight and every independently executed method/output
remain pending. No Rust formatter, parser, compiler, target import, test or
new numerical evaluation was run locally.
