//! Written deterministic controls; execution is pending independent REANA jobs.

use std::any::TypeId;
use std::collections::BTreeSet;
use std::fmt::Debug;
use std::hash::Hash;

use galaxy_types::{
    AllocationError, CellId, CheckpointError, EntityAllocatorCheckpoint, EntityId, EventAllocatorCheckpoint, EventId,
    IdentityKind, IdentityRegistry, NamespaceKind, ParseEntityIdError, ParticleId, RegistryError,
    SerialEntityAllocator, SerialEventAllocator,
};

type RegistrySnapshot = (Vec<(u64, NamespaceKind)>, Vec<(EntityId, IdentityKind)>);

fn snapshot(registry: &IdentityRegistry) -> RegistrySnapshot {
    (registry.namespaces().collect(), registry.entries().collect())
}

fn restore_registry(saved: &RegistrySnapshot) -> IdentityRegistry {
    let mut registry = IdentityRegistry::new();
    for &(namespace, kind) in &saved.0 {
        registry.reserve_namespace(namespace, kind).unwrap();
    }
    for &(id, kind) in &saved.1 {
        match kind {
            IdentityKind::Cell => registry.register_cell(CellId::new(id)),
            IdentityKind::Particle => registry.register_particle(ParticleId::new(id)),
            IdentityKind::Event => registry.register_event(EventId::new(id)),
        }
        .unwrap();
    }
    registry
}

fn required_id_traits<T: Copy + Eq + Ord + Hash + Debug>() {}

#[test]
fn entity_id_encodes_zero_and_max_payloads() {
    const ZERO: EntityId = EntityId::new(0, 0);
    const MAX: EntityId = EntityId::new(u64::MAX, u64::MAX);
    const ZERO_NAMESPACE: u64 = ZERO.namespace();
    const MAX_COUNTER: u64 = MAX.counter();
    assert_eq!(ZERO_NAMESPACE, 0);
    assert_eq!(MAX_COUNTER, u64::MAX);
    assert_eq!(ZERO.to_string(), "00000000000000000000000000000000");
    assert_eq!(MAX.to_string(), "ffffffffffffffffffffffffffffffff");
    assert_eq!(ZERO.to_string().parse(), Ok(ZERO));
    assert_eq!(MAX.to_string().parse(), Ok(MAX));
}

#[test]
fn entity_id_canonical_namespace_counter_layout() {
    let id = EntityId::new(0x0123_4567_89ab_cdef, 0xfedc_ba98_7654_3210);
    let text = id.to_string();
    assert_eq!(text, "0123456789abcdeffedcba9876543210");
    assert_eq!(text.len(), 32);
    assert!(text.bytes().all(|byte| byte.is_ascii_hexdigit()));
    assert!(!text.bytes().any(|byte| byte.is_ascii_uppercase()));
    assert_eq!(id.namespace(), 0x0123_4567_89ab_cdef);
    assert_eq!(id.counter(), 0xfedc_ba98_7654_3210);
    assert_eq!(text.parse::<EntityId>(), Ok(id));
}

#[test]
fn entity_id_parses_uppercase_and_mixed_case() {
    let expected = EntityId::new(0x0123_4567_89ab_cdef, 0xfedc_ba98_7654_3210);
    for text in [
        "0123456789ABCDEFFEDCBA9876543210",
        "0123456789aBcDeFfEdCbA9876543210",
    ] {
        let id: EntityId = text.parse().unwrap();
        assert_eq!(id, expected);
        assert_eq!(id.to_string(), "0123456789abcdeffedcba9876543210");
    }
}

#[test]
fn entity_id_round_trips_canonical_text() {
    for namespace in [0, 1, 0x0123_4567_89ab_cdef, u64::MAX] {
        for counter in [0, 1, 0x8000_0000_0000_0000, u64::MAX] {
            let id = EntityId::new(namespace, counter);
            assert_eq!(id.to_string().parse::<EntityId>(), Ok(id));
        }
    }
}

#[test]
fn entity_id_rejects_wrong_lengths_and_framing() {
    for text in [
        String::new(),
        "0".repeat(31),
        "0".repeat(33),
        format!("0x{}", "0".repeat(32)),
        format!(" {}", "0".repeat(32)),
        format!("{}\n", "0".repeat(32)),
    ] {
        assert_eq!(
            text.parse::<EntityId>(),
            Err(ParseEntityIdError::InvalidLength { actual: text.len() })
        );
    }
    for text in [
        format!("0x{}", "0".repeat(30)),
        format!("+{}", "0".repeat(31)),
        format!("-{}", "0".repeat(31)),
        format!(" {}", "0".repeat(31)),
        format!("{} ", "0".repeat(31)),
        format!("{}-{}", "0".repeat(15), "0".repeat(16)),
        format!("{}\t{}", "0".repeat(15), "0".repeat(16)),
    ] {
        assert_eq!(text.len(), 32);
        assert!(matches!(
            text.parse::<EntityId>(),
            Err(ParseEntityIdError::InvalidHex { .. })
        ));
    }
}

#[test]
fn entity_id_rejects_non_ascii_and_non_hex() {
    for (text, index) in [
        (format!("g{}", "0".repeat(31)), 0),
        (format!("{}G", "0".repeat(31)), 31),
        (format!("{}é", "0".repeat(30)), 30),
        (format!("{}Ａ", "0".repeat(29)), 29),
        (format!("{}\0", "0".repeat(31)), 31),
    ] {
        assert_eq!(text.len(), 32);
        assert_eq!(
            text.parse::<EntityId>(),
            Err(ParseEntityIdError::InvalidHex { index })
        );
    }
}

#[test]
fn entity_id_order_is_namespace_then_counter() {
    let expected = [
        EntityId::new(0, 0),
        EntityId::new(0, u64::MAX),
        EntityId::new(1, 0),
        EntityId::new(1, 1),
        EntityId::new(u64::MAX, 0),
    ];
    let mut actual = expected;
    actual.reverse();
    actual.sort();
    assert_eq!(actual, expected);
    for pair in actual.windows(2) {
        assert!(pair[0].to_string() < pair[1].to_string());
    }
}

#[test]
fn kind_wrappers_are_distinct_and_preserve_payload() {
    required_id_traits::<EntityId>();
    required_id_traits::<CellId>();
    required_id_traits::<ParticleId>();
    required_id_traits::<EventId>();
    const PAYLOAD: EntityId = EntityId::new(0, u64::MAX);
    const CELL: CellId = CellId::new(PAYLOAD);
    const PARTICLE: ParticleId = ParticleId::new(PAYLOAD);
    const EVENT: EventId = EventId::new(PAYLOAD);
    const EXTRACTED: EntityId = CELL.entity();
    assert_eq!(EXTRACTED, PAYLOAD);
    assert_eq!(PARTICLE.entity(), PAYLOAD);
    assert_eq!(EVENT.entity(), PAYLOAD);
    assert_ne!(TypeId::of::<CellId>(), TypeId::of::<ParticleId>());
    assert_ne!(TypeId::of::<CellId>(), TypeId::of::<EventId>());
    assert_ne!(TypeId::of::<ParticleId>(), TypeId::of::<EventId>());
    let mut cells = BTreeSet::new();
    assert!(cells.insert(CELL));
    assert!(!cells.insert(CellId::new(PAYLOAD)));
    // These freely constructed wrappers alone do not certify uniqueness.
    let mut registry = IdentityRegistry::new();
    registry.register_cell(CELL).unwrap();
    assert!(registry.register_particle(PARTICLE).is_err());
    assert!(registry.register_event(EVENT).is_err());
}

#[test]
fn registry_rejects_cell_particle_payload_collision() {
    let id = EntityId::new(7, 0);
    for (first, second) in [
        (IdentityKind::Cell, IdentityKind::Particle),
        (IdentityKind::Particle, IdentityKind::Cell),
    ] {
        let mut registry = IdentityRegistry::new();
        match first {
            IdentityKind::Cell => registry.register_cell(CellId::new(id)),
            IdentityKind::Particle => registry.register_particle(ParticleId::new(id)),
            IdentityKind::Event => unreachable!(),
        }
        .unwrap();
        let before = snapshot(&registry);
        let result = match second {
            IdentityKind::Cell => registry.register_cell(CellId::new(id)),
            IdentityKind::Particle => registry.register_particle(ParticleId::new(id)),
            IdentityKind::Event => unreachable!(),
        };
        assert_eq!(
            result,
            Err(RegistryError::PayloadKindCollision {
                id,
                existing: first,
                requested: second,
            })
        );
        assert_eq!(snapshot(&registry), before);
        assert_eq!(registry.kind(id), Some(first));
    }
}

#[test]
fn registry_rejects_duplicate_ids_for_each_kind() {
    let mut registry = IdentityRegistry::new();
    let cell = CellId::new(EntityId::new(4, 0));
    let particle = ParticleId::new(EntityId::new(4, 1));
    let event = EventId::new(EntityId::new(5, 0));
    registry.register_cell(cell).unwrap();
    registry.register_particle(particle).unwrap();
    registry.register_event(event).unwrap();
    let before = snapshot(&registry);
    for (result, id, kind) in [
        (registry.register_cell(cell), cell.entity(), IdentityKind::Cell),
        (
            registry.register_particle(particle),
            particle.entity(),
            IdentityKind::Particle,
        ),
        (registry.register_event(event), event.entity(), IdentityKind::Event),
    ] {
        assert_eq!(result, Err(RegistryError::DuplicateId { id, kind }));
        assert_eq!(snapshot(&registry), before);
    }
    assert_eq!(registry.len(), 3);
}

#[test]
fn registry_rejects_event_real_namespace_overlap_both_orders() {
    let mut real_first = IdentityRegistry::new();
    real_first
        .register_particle(ParticleId::new(EntityId::new(8, 0)))
        .unwrap();
    let before = snapshot(&real_first);
    assert_eq!(
        real_first.register_event(EventId::new(EntityId::new(8, 99))),
        Err(RegistryError::NamespaceCollision {
            namespace: 8,
            existing: NamespaceKind::RealEntity,
            requested: NamespaceKind::Event,
        })
    );
    assert_eq!(snapshot(&real_first), before);

    let mut event_first = IdentityRegistry::new();
    event_first
        .register_event(EventId::new(EntityId::new(8, 0)))
        .unwrap();
    let before = snapshot(&event_first);
    for result in [
        event_first.register_cell(CellId::new(EntityId::new(8, 99))),
        event_first.register_particle(ParticleId::new(EntityId::new(8, 100))),
    ] {
        assert_eq!(
            result,
            Err(RegistryError::NamespaceCollision {
                namespace: 8,
                existing: NamespaceKind::Event,
                requested: NamespaceKind::RealEntity,
            })
        );
    }
    assert_eq!(snapshot(&event_first), before);
}

#[test]
fn namespace_reservations_are_checked_and_atomic() {
    let mut registry = IdentityRegistry::new();
    registry
        .reserve_namespace(0, NamespaceKind::RealEntity)
        .unwrap();
    registry
        .reserve_namespace(u64::MAX, NamespaceKind::Event)
        .unwrap();
    assert!(registry.is_empty());
    assert_eq!(registry.namespace_kind(0), Some(NamespaceKind::RealEntity));
    assert_eq!(registry.namespace_kind(1), None);
    let before = snapshot(&registry);
    registry
        .reserve_namespace(0, NamespaceKind::RealEntity)
        .unwrap();
    assert_eq!(snapshot(&registry), before);
    assert!(registry.reserve_namespace(0, NamespaceKind::Event).is_err());
    assert!(
        registry
            .register_event(EventId::new(EntityId::new(0, 0)))
            .is_err()
    );
    assert!(
        registry
            .register_cell(CellId::new(EntityId::new(u64::MAX, 0)))
            .is_err()
    );
    assert_eq!(snapshot(&registry), before);
}

#[test]
fn real_allocator_shares_cell_particle_counter_stream() {
    let mut registry = IdentityRegistry::new();
    let mut allocator = SerialEntityAllocator::new(0, 0);
    let cell = allocator.allocate_cell(&mut registry).unwrap();
    let particle = allocator.allocate_particle(&mut registry).unwrap();
    let other_cell = allocator.allocate_cell(&mut registry).unwrap();
    assert_eq!(cell.entity(), EntityId::new(0, 0));
    assert_eq!(particle.entity(), EntityId::new(0, 1));
    assert_eq!(other_cell.entity(), EntityId::new(0, 2));
    assert_eq!(registry.kind(cell.entity()), Some(IdentityKind::Cell));
    assert_eq!(registry.kind(particle.entity()), Some(IdentityKind::Particle));
    assert_eq!(
        allocator.checkpoint(),
        EntityAllocatorCheckpoint::new(0, Some(3))
    );
    assert_eq!(registry.len(), 3);
}

#[test]
fn event_allocator_has_separate_sequence_and_checkpoint() {
    let mut registry = IdentityRegistry::new();
    let mut real = SerialEntityAllocator::new(9, 0);
    let mut events = SerialEventAllocator::new(10, 0);
    let cell = real.allocate_cell(&mut registry).unwrap();
    let event = events.allocate_event(&mut registry).unwrap();
    let particle = real.allocate_particle(&mut registry).unwrap();
    assert_eq!(cell.entity(), EntityId::new(9, 0));
    assert_eq!(particle.entity(), EntityId::new(9, 1));
    assert_eq!(event.entity(), EntityId::new(10, 0));
    assert_eq!(real.checkpoint(), EntityAllocatorCheckpoint::new(9, Some(2)));
    assert_eq!(
        events.checkpoint(),
        EventAllocatorCheckpoint::new(10, Some(1))
    );
    assert_eq!(registry.len(), 3);
}

#[test]
fn real_allocator_issues_max_once_then_stays_exhausted() {
    let mut registry = IdentityRegistry::new();
    let mut allocator = SerialEntityAllocator::new(12, u64::MAX - 1);
    assert_eq!(
        allocator.allocate_cell(&mut registry).unwrap().entity(),
        EntityId::new(12, u64::MAX - 1)
    );
    assert_eq!(allocator.checkpoint().next_counter(), Some(u64::MAX));
    assert_eq!(
        allocator.allocate_particle(&mut registry).unwrap().entity(),
        EntityId::new(12, u64::MAX)
    );
    let exhausted = allocator.checkpoint();
    let before = snapshot(&registry);
    assert_eq!(exhausted.next_counter(), None);
    for _ in 0..2 {
        assert_eq!(
            allocator.allocate_cell(&mut registry),
            Err(AllocationError::Exhausted { namespace: 12 })
        );
        assert_eq!(
            allocator.allocate_particle(&mut registry),
            Err(AllocationError::Exhausted { namespace: 12 })
        );
        assert_eq!(allocator.checkpoint(), exhausted);
        assert_eq!(snapshot(&registry), before);
    }
}

#[test]
fn event_allocator_exhaustion_is_atomic() {
    let mut registry = IdentityRegistry::new();
    let mut allocator = SerialEventAllocator::new(u64::MAX, u64::MAX);
    assert_eq!(
        allocator.allocate_event(&mut registry).unwrap().entity(),
        EntityId::new(u64::MAX, u64::MAX)
    );
    let before = snapshot(&registry);
    let exhausted = allocator.checkpoint();
    assert_eq!(exhausted.next_counter(), None);
    for _ in 0..2 {
        assert_eq!(
            allocator.allocate_event(&mut registry),
            Err(AllocationError::Exhausted {
                namespace: u64::MAX
            })
        );
        assert_eq!(allocator.checkpoint(), exhausted);
        assert_eq!(snapshot(&registry), before);
    }
}

#[test]
fn real_allocator_restart_does_not_reuse_ids() {
    let mut registry = IdentityRegistry::new();
    registry
        .reserve_namespace(25, NamespaceKind::Event)
        .unwrap();
    let mut original = SerialEntityAllocator::new(24, 0);
    let retired = original.allocate_cell(&mut registry).unwrap();
    original.allocate_particle(&mut registry).unwrap();
    let checkpoint = original.checkpoint();
    let saved = snapshot(&registry);
    let mut restored = restore_registry(&saved);
    let mut resumed = SerialEntityAllocator::from_checkpoint(checkpoint);
    assert_eq!(snapshot(&restored), saved);
    assert_eq!(
        resumed.allocate_particle(&mut restored).unwrap().entity(),
        EntityId::new(24, 2)
    );
    let before = snapshot(&restored);
    assert_eq!(
        restored.register_cell(retired),
        Err(RegistryError::DuplicateId {
            id: retired.entity(),
            kind: IdentityKind::Cell,
        })
    );
    assert_eq!(snapshot(&restored), before);
    assert_eq!(restored.namespace_kind(25), Some(NamespaceKind::Event));
}

#[test]
fn event_allocator_restart_preserves_exhaustion() {
    let mut registry = IdentityRegistry::new();
    let mut allocator = SerialEventAllocator::new(31, u64::MAX);
    let last = allocator.allocate_event(&mut registry).unwrap();
    let saved = snapshot(&registry);
    let mut restored = restore_registry(&saved);
    let mut resumed = SerialEventAllocator::from_checkpoint(allocator.checkpoint());
    assert_eq!(
        resumed.allocate_event(&mut restored),
        Err(AllocationError::Exhausted { namespace: 31 })
    );
    assert_eq!(
        resumed.checkpoint(),
        EventAllocatorCheckpoint::new(31, None)
    );
    assert_eq!(snapshot(&restored), saved);
    assert_eq!(restored.kind(last.entity()), Some(IdentityKind::Event));
}

#[test]
fn stale_real_checkpoint_is_rejected_without_advancement() {
    let mut registry = IdentityRegistry::new();
    let mut original = SerialEntityAllocator::new(41, 7);
    let stale = original.checkpoint();
    let issued = original.allocate_cell(&mut registry).unwrap();
    let before = snapshot(&registry);
    let mut resumed = SerialEntityAllocator::from_checkpoint(stale);
    assert_eq!(
        resumed.allocate_cell(&mut registry),
        Err(AllocationError::Registry(RegistryError::DuplicateId {
            id: issued.entity(),
            kind: IdentityKind::Cell,
        }))
    );
    assert_eq!(resumed.checkpoint(), stale);
    assert_eq!(
        resumed.allocate_particle(&mut registry),
        Err(AllocationError::Registry(RegistryError::PayloadKindCollision {
            id: issued.entity(),
            existing: IdentityKind::Cell,
            requested: IdentityKind::Particle,
        }))
    );
    assert_eq!(resumed.checkpoint(), stale);
    assert_eq!(snapshot(&registry), before);
}

#[test]
fn stale_event_checkpoint_is_rejected_without_advancement() {
    let mut registry = IdentityRegistry::new();
    let mut original = SerialEventAllocator::new(42, 7);
    let stale = original.checkpoint();
    let issued = original.allocate_event(&mut registry).unwrap();
    let before = snapshot(&registry);
    let mut resumed = SerialEventAllocator::from_checkpoint(stale);
    assert_eq!(
        resumed.allocate_event(&mut registry),
        Err(AllocationError::Registry(RegistryError::DuplicateId {
            id: issued.entity(),
            kind: IdentityKind::Event,
        }))
    );
    assert_eq!(resumed.checkpoint(), stale);
    assert_eq!(snapshot(&registry), before);
}

#[test]
fn checked_real_restore_rejects_sparse_cursor_and_continues_above_high_water() {
    let mut registry = IdentityRegistry::new();
    registry
        .register_particle(ParticleId::new(EntityId::new(7, 10)))
        .unwrap();
    registry
        .register_cell(CellId::new(EntityId::new(7, 2)))
        .unwrap();
    let before = snapshot(&registry);
    for next_counter in [0, 5, 10] {
        let checkpoint = EntityAllocatorCheckpoint::new(7, Some(next_counter));
        assert!(matches!(
            SerialEntityAllocator::restore_checked(checkpoint, &registry),
            Err(CheckpointError::CounterNotAboveHighWater {
                namespace: 7,
                next_counter: actual,
                highest_issued: 10,
            }) if actual == next_counter
        ));
        assert_eq!(snapshot(&registry), before);
        assert_eq!(checkpoint.next_counter(), Some(next_counter));
    }
    let checkpoint = EntityAllocatorCheckpoint::new(7, Some(11));
    let mut restored = SerialEntityAllocator::restore_checked(checkpoint, &registry).unwrap();
    assert_eq!(snapshot(&registry), before);
    assert_eq!(restored.allocate_cell(&mut registry).unwrap().entity(), EntityId::new(7, 11));
    assert_eq!(restored.allocate_particle(&mut registry).unwrap().entity(), EntityId::new(7, 12));
    assert_eq!(restored.checkpoint().next_counter(), Some(13));
}

#[test]
fn checked_event_restore_rejects_sparse_cursor_and_continues_above_high_water() {
    let mut registry = IdentityRegistry::new();
    registry
        .register_event(EventId::new(EntityId::new(8, 10)))
        .unwrap();
    registry
        .register_event(EventId::new(EntityId::new(8, 2)))
        .unwrap();
    let before = snapshot(&registry);
    for next_counter in [0, 5, 10] {
        let checkpoint = EventAllocatorCheckpoint::new(8, Some(next_counter));
        assert!(matches!(
            SerialEventAllocator::restore_checked(checkpoint, &registry),
            Err(CheckpointError::CounterNotAboveHighWater {
                namespace: 8,
                next_counter: actual,
                highest_issued: 10,
            }) if actual == next_counter
        ));
        assert_eq!(snapshot(&registry), before);
        assert_eq!(checkpoint.next_counter(), Some(next_counter));
    }
    let mut restored = SerialEventAllocator::restore_checked(
        EventAllocatorCheckpoint::new(8, Some(11)), &registry,
    ).unwrap();
    assert_eq!(snapshot(&registry), before);
    assert_eq!(restored.allocate_event(&mut registry).unwrap().entity(), EntityId::new(8, 11));
    assert_eq!(restored.checkpoint().next_counter(), Some(12));
}

#[test]
fn checked_restore_maximum_and_namespace_guards_are_atomic() {
    let mut registry = IdentityRegistry::new();
    registry.register_cell(CellId::new(EntityId::new(9, u64::MAX))).unwrap();
    registry.register_event(EventId::new(EntityId::new(10, u64::MAX))).unwrap();
    let before = snapshot(&registry);
    assert!(matches!(SerialEntityAllocator::restore_checked(
        EntityAllocatorCheckpoint::new(9, Some(u64::MAX)), &registry,
    ), Err(CheckpointError::CounterNotAboveHighWater { highest_issued: u64::MAX, .. })));
    assert!(matches!(SerialEventAllocator::restore_checked(
        EventAllocatorCheckpoint::new(10, Some(u64::MAX)), &registry,
    ), Err(CheckpointError::CounterNotAboveHighWater { highest_issued: u64::MAX, .. })));
    assert!(matches!(SerialEntityAllocator::restore_checked(
        EntityAllocatorCheckpoint::new(10, None), &registry,
    ), Err(CheckpointError::Registry(RegistryError::NamespaceCollision { .. }))));
    assert!(matches!(SerialEventAllocator::restore_checked(
        EventAllocatorCheckpoint::new(9, None), &registry,
    ), Err(CheckpointError::Registry(RegistryError::NamespaceCollision { .. }))));
    assert_eq!(snapshot(&registry), before);
    let mut real = SerialEntityAllocator::restore_checked(
        EntityAllocatorCheckpoint::new(9, None), &registry,
    ).unwrap();
    let mut events = SerialEventAllocator::restore_checked(
        EventAllocatorCheckpoint::new(10, None), &registry,
    ).unwrap();
    assert_eq!(real.allocate_cell(&mut registry), Err(AllocationError::Exhausted { namespace: 9 }));
    assert_eq!(events.allocate_event(&mut registry), Err(AllocationError::Exhausted { namespace: 10 }));
    assert_eq!(snapshot(&registry), before);
    let empty = IdentityRegistry::new();
    assert_eq!(SerialEntityAllocator::restore_checked(
        EntityAllocatorCheckpoint::new(0, Some(0)), &empty,
    ).unwrap().checkpoint(), EntityAllocatorCheckpoint::new(0, Some(0)));
    assert_eq!(SerialEventAllocator::restore_checked(
        EventAllocatorCheckpoint::new(u64::MAX, Some(u64::MAX)), &empty,
    ).unwrap().checkpoint(), EventAllocatorCheckpoint::new(u64::MAX, Some(u64::MAX)));
    assert!(empty.is_empty());
}

#[test]
fn allocator_namespace_failure_preserves_allocator_and_registry() {
    let mut registry = IdentityRegistry::new();
    registry
        .reserve_namespace(51, NamespaceKind::Event)
        .unwrap();
    registry
        .reserve_namespace(52, NamespaceKind::RealEntity)
        .unwrap();
    let before = snapshot(&registry);
    let mut real = SerialEntityAllocator::new(51, 0);
    let mut events = SerialEventAllocator::new(52, u64::MAX);
    let real_before = real.checkpoint();
    let events_before = events.checkpoint();
    assert_eq!(
        real.allocate_cell(&mut registry),
        Err(AllocationError::Registry(RegistryError::NamespaceCollision {
            namespace: 51,
            existing: NamespaceKind::Event,
            requested: NamespaceKind::RealEntity,
        }))
    );
    assert!(real.allocate_particle(&mut registry).is_err());
    assert_eq!(
        events.allocate_event(&mut registry),
        Err(AllocationError::Registry(RegistryError::NamespaceCollision {
            namespace: 52,
            existing: NamespaceKind::RealEntity,
            requested: NamespaceKind::Event,
        }))
    );
    assert_eq!(real.checkpoint(), real_before);
    assert_eq!(events.checkpoint(), events_before);
    assert_eq!(snapshot(&registry), before);
}

#[test]
fn allocator_checkpoints_preserve_zero_max_and_exhausted_states() {
    for namespace in [0, u64::MAX] {
        for next in [Some(0), Some(u64::MAX), None] {
            let real = EntityAllocatorCheckpoint::new(namespace, next);
            let events = EventAllocatorCheckpoint::new(namespace, next);
            assert_eq!(real.namespace(), namespace);
            assert_eq!(events.namespace(), namespace);
            assert_eq!(real.next_counter(), next);
            assert_eq!(events.next_counter(), next);
            assert_eq!(
                SerialEntityAllocator::from_checkpoint(real).checkpoint(),
                real
            );
            assert_eq!(
                SerialEventAllocator::from_checkpoint(events).checkpoint(),
                events
            );
        }
    }
    let mut registry = IdentityRegistry::new();
    let mut exhausted =
        SerialEntityAllocator::from_checkpoint(EntityAllocatorCheckpoint::new(0, None));
    assert_eq!(
        exhausted.allocate_cell(&mut registry),
        Err(AllocationError::Exhausted { namespace: 0 })
    );
    assert!(registry.is_empty());
    assert_eq!(registry.namespace_kind(0), None);
}

#[test]
fn registry_iteration_is_canonical_for_checkpoint_export() {
    let mut registry = IdentityRegistry::new();
    registry
        .reserve_namespace(99, NamespaceKind::Event)
        .unwrap();
    registry
        .register_particle(ParticleId::new(EntityId::new(2, 9)))
        .unwrap();
    registry
        .register_event(EventId::new(EntityId::new(3, 0)))
        .unwrap();
    registry
        .register_cell(CellId::new(EntityId::new(2, 0)))
        .unwrap();
    registry
        .register_cell(CellId::new(EntityId::new(0, 7)))
        .unwrap();
    assert_eq!(
        registry.entries().collect::<Vec<_>>(),
        vec![
            (EntityId::new(0, 7), IdentityKind::Cell),
            (EntityId::new(2, 0), IdentityKind::Cell),
            (EntityId::new(2, 9), IdentityKind::Particle),
            (EntityId::new(3, 0), IdentityKind::Event),
        ]
    );
    assert_eq!(
        registry.namespaces().collect::<Vec<_>>(),
        vec![
            (0, NamespaceKind::RealEntity),
            (2, NamespaceKind::RealEntity),
            (3, NamespaceKind::Event),
            (99, NamespaceKind::Event),
        ]
    );
    assert_eq!(
        snapshot(&restore_registry(&snapshot(&registry))),
        snapshot(&registry)
    );
}
