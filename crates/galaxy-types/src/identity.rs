//! Lossless identities, a serial allocator pair, and a lifetime ID registry.
//!
//! Namespace assignment is an explicit run/IC input. Real cells and particles
//! share a counter stream; events use disjoint namespaces. Periodic images and
//! ghosts retain their owner's ID and must not allocate another real ID.
//!
//! The registry has no removal operation: retired IDs remain reserved. Restore
//! its complete namespace and issued-ID records together with the allocator
//! checkpoints at an accepted transaction boundary. Restoring only the live
//! objects, or forking independent registries, cannot guarantee no reuse.

use std::collections::BTreeMap;
use std::error::Error;
use std::fmt;
use std::str::FromStr;

/// Persistent payload ordered first by namespace, then by counter.
///
/// Every pair of `u64` values is valid, including `(0, 0)`. Construction does
/// not validate uniqueness or namespace assignment. Display is exactly 32
/// lower-case hexadecimal digits; parsing accepts upper-case ASCII hex too.
/// External formats must retain this lossless text, never a JSON number.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct EntityId {
    namespace: u64,
    counter: u64,
}

impl EntityId {
    pub const fn new(namespace: u64, counter: u64) -> Self {
        Self { namespace, counter }
    }

    pub const fn namespace(self) -> u64 {
        self.namespace
    }

    pub const fn counter(self) -> u64 {
        self.counter
    }
}

impl fmt::Display for EntityId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:016x}{:016x}", self.namespace, self.counter)
    }
}

/// Parsing reports byte lengths and byte positions, without retaining input.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ParseEntityIdError {
    InvalidLength { actual: usize },
    InvalidHex { index: usize },
}

impl fmt::Display for ParseEntityIdError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidLength { actual } => {
                write!(f, "expected 32 ASCII hex bytes, received {actual} bytes")
            }
            Self::InvalidHex { index } => write!(f, "invalid ASCII hex byte at index {index}"),
        }
    }
}

impl Error for ParseEntityIdError {}

impl FromStr for EntityId {
    type Err = ParseEntityIdError;

    fn from_str(text: &str) -> Result<Self, Self::Err> {
        let bytes = text.as_bytes();
        if bytes.len() != 32 {
            return Err(ParseEntityIdError::InvalidLength {
                actual: bytes.len(),
            });
        }
        let mut namespace = 0_u64;
        let mut counter = 0_u64;
        for (index, &byte) in bytes.iter().enumerate() {
            let digit = match byte {
                b'0'..=b'9' => u64::from(byte - b'0'),
                b'a'..=b'f' => u64::from(byte - b'a' + 10),
                b'A'..=b'F' => u64::from(byte - b'A' + 10),
                _ => return Err(ParseEntityIdError::InvalidHex { index }),
            };
            let half = if index < 16 {
                &mut namespace
            } else {
                &mut counter
            };
            *half = (*half << 4) | digit;
        }
        Ok(Self::new(namespace, counter))
    }
}

/// A real gas-cell identity, not a local array index or an image identity.
/// Wrapping a payload does not certify catalog validity or uniqueness.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct CellId(EntityId);

impl CellId {
    pub const fn new(entity: EntityId) -> Self {
        Self(entity)
    }

    pub const fn entity(self) -> EntityId {
        self.0
    }
}

/// A dark-matter or stellar particle identity; species is separate metadata.
/// There is deliberately no implicit conversion from another identity kind.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct ParticleId(EntityId);

impl ParticleId {
    pub const fn new(entity: EntityId) -> Self {
        Self(entity)
    }

    pub const fn entity(self) -> EntityId {
        self.0
    }
}

/// A source/lineage event identity, with a namespace disjoint from real IDs.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct EventId(EntityId);

impl EventId {
    pub const fn new(entity: EntityId) -> Self {
        Self(entity)
    }

    pub const fn entity(self) -> EntityId {
        self.0
    }
}

/// A namespace is reserved for either real entities or events, never both.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub enum NamespaceKind {
    RealEntity,
    Event,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub enum IdentityKind {
    Cell,
    Particle,
    Event,
}

impl IdentityKind {
    const fn namespace_kind(self) -> NamespaceKind {
        match self {
            Self::Cell | Self::Particle => NamespaceKind::RealEntity,
            Self::Event => NamespaceKind::Event,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegistryError {
    NamespaceCollision {
        namespace: u64,
        existing: NamespaceKind,
        requested: NamespaceKind,
    },
    DuplicateId {
        id: EntityId,
        kind: IdentityKind,
    },
    PayloadKindCollision {
        id: EntityId,
        existing: IdentityKind,
        requested: IdentityKind,
    },
}

impl fmt::Display for RegistryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NamespaceCollision {
                namespace,
                existing,
                requested,
            } => write!(
                f,
                "namespace {namespace:016x} is {existing:?}, cannot reserve it as {requested:?}"
            ),
            Self::DuplicateId { id, kind } => write!(f, "duplicate {kind:?} ID {id}"),
            Self::PayloadKindCollision {
                id,
                existing,
                requested,
            } => write!(
                f,
                "ID {id} is {existing:?}, cannot register it as {requested:?}"
            ),
        }
    }
}

impl Error for RegistryError {}

/// One authoritative serial registry of all issued IDs, including tombstones.
///
/// Registering checks namespace role before payload duplication. All returned
/// errors leave both maps unchanged. Memory allocation failure, panic, process
/// loss, storage transactions and distributed coordination are not handled here.
/// The registry intentionally has no `Clone` or removal API.
#[derive(Debug, Default)]
pub struct IdentityRegistry {
    namespaces: BTreeMap<u64, NamespaceKind>,
    entries: BTreeMap<EntityId, IdentityKind>,
}

impl IdentityRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    /// Reserve even an empty namespace from a run manifest. The same role is
    /// idempotent; changing a previously reserved role is rejected.
    pub fn reserve_namespace(
        &mut self,
        namespace: u64,
        kind: NamespaceKind,
    ) -> Result<(), RegistryError> {
        self.check_namespace(namespace, kind)?;
        self.namespaces.insert(namespace, kind);
        Ok(())
    }

    pub fn register_cell(&mut self, id: CellId) -> Result<(), RegistryError> {
        self.register(id.entity(), IdentityKind::Cell)
    }

    pub fn register_particle(&mut self, id: ParticleId) -> Result<(), RegistryError> {
        self.register(id.entity(), IdentityKind::Particle)
    }

    pub fn register_event(&mut self, id: EventId) -> Result<(), RegistryError> {
        self.register(id.entity(), IdentityKind::Event)
    }

    pub fn kind(&self, id: EntityId) -> Option<IdentityKind> {
        self.entries.get(&id).copied()
    }

    pub fn namespace_kind(&self, namespace: u64) -> Option<NamespaceKind> {
        self.namespaces.get(&namespace).copied()
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// Empty means no issued IDs, even if namespaces have been reserved.
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Read-only canonical order for an external lossless checkpoint writer.
    pub fn entries(&self) -> impl Iterator<Item = (EntityId, IdentityKind)> + '_ {
        self.entries.iter().map(|(&id, &kind)| (id, kind))
    }

    /// Includes namespace reservations with no issued IDs yet.
    pub fn namespaces(&self) -> impl Iterator<Item = (u64, NamespaceKind)> + '_ {
        self.namespaces
            .iter()
            .map(|(&namespace, &kind)| (namespace, kind))
    }

    fn check_namespace(
        &self,
        namespace: u64,
        requested: NamespaceKind,
    ) -> Result<(), RegistryError> {
        if let Some(&existing) = self.namespaces.get(&namespace) {
            if existing != requested {
                return Err(RegistryError::NamespaceCollision {
                    namespace,
                    existing,
                    requested,
                });
            }
        }
        Ok(())
    }

    fn register(&mut self, id: EntityId, requested: IdentityKind) -> Result<(), RegistryError> {
        let namespace_kind = requested.namespace_kind();
        self.check_namespace(id.namespace(), namespace_kind)?;
        if let Some(&existing) = self.entries.get(&id) {
            return Err(if existing == requested {
                RegistryError::DuplicateId { id, kind: existing }
            } else {
                RegistryError::PayloadKindCollision {
                    id,
                    existing,
                    requested,
                }
            });
        }
        self.namespaces.insert(id.namespace(), namespace_kind);
        self.entries.insert(id, requested);
        Ok(())
    }
}

/// Serial real-entity allocator state. `None` is exhausted, not a free counter.
/// Constructing a checkpoint does not prove its provenance or freshness.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct EntityAllocatorCheckpoint {
    namespace: u64,
    next_counter: Option<u64>,
}

impl EntityAllocatorCheckpoint {
    pub const fn new(namespace: u64, next_counter: Option<u64>) -> Self {
        Self {
            namespace,
            next_counter,
        }
    }

    pub const fn namespace(self) -> u64 {
        self.namespace
    }

    pub const fn next_counter(self) -> Option<u64> {
        self.next_counter
    }
}

/// Distinct event allocator state; it cannot be passed as an entity checkpoint.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct EventAllocatorCheckpoint {
    namespace: u64,
    next_counter: Option<u64>,
}

impl EventAllocatorCheckpoint {
    pub const fn new(namespace: u64, next_counter: Option<u64>) -> Self {
        Self {
            namespace,
            next_counter,
        }
    }

    pub const fn namespace(self) -> u64 {
        self.namespace
    }

    pub const fn next_counter(self) -> Option<u64> {
        self.next_counter
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AllocationError {
    Exhausted { namespace: u64 },
    Registry(RegistryError),
}

impl fmt::Display for AllocationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Exhausted { namespace } => {
                write!(f, "ID counter exhausted for namespace {namespace:016x}")
            }
            Self::Registry(error) => fmt::Display::fmt(error, f),
        }
    }
}

impl Error for AllocationError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Registry(error) => Some(error),
            Self::Exhausted { .. } => None,
        }
    }
}

/// A raw checkpoint disagrees with the complete imported namespace registry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CheckpointError {
    Registry(RegistryError),
    CounterNotAboveHighWater {
        namespace: u64,
        next_counter: u64,
        highest_issued: u64,
    },
}

impl fmt::Display for CheckpointError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Registry(error) => fmt::Display::fmt(error, f),
            Self::CounterNotAboveHighWater {
                namespace,
                next_counter,
                highest_issued,
            } => write!(
                f,
                "next counter {next_counter} is not above issued counter {highest_issued} in namespace {namespace:016x}"
            ),
        }
    }
}

impl Error for CheckpointError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Registry(error) => Some(error),
            Self::CounterNotAboveHighWater { .. } => None,
        }
    }
}

#[derive(Debug)]
struct CounterCursor {
    namespace: u64,
    next_counter: Option<u64>,
}

impl CounterCursor {
    fn from_checked(
        namespace: u64,
        next_counter: Option<u64>,
        registry: &IdentityRegistry,
        kind: NamespaceKind,
    ) -> Result<Self, CheckpointError> {
        registry
            .check_namespace(namespace, kind)
            .map_err(CheckpointError::Registry)?;
        let highest_issued = registry
            .entries
            .range(EntityId::new(namespace, 0)..=EntityId::new(namespace, u64::MAX))
            .next_back()
            .map(|(id, _)| id.counter());
        match (next_counter, highest_issued) {
            (Some(next_counter), Some(highest_issued)) if next_counter <= highest_issued => {
                Err(CheckpointError::CounterNotAboveHighWater {
                    namespace,
                    next_counter,
                    highest_issued,
                })
            }
            _ => Ok(Self {
                namespace,
                next_counter,
            }),
        }
    }

    fn allocate(
        &mut self,
        registry: &mut IdentityRegistry,
        kind: IdentityKind,
    ) -> Result<EntityId, AllocationError> {
        let counter = self.next_counter.ok_or(AllocationError::Exhausted {
            namespace: self.namespace,
        })?;
        let id = EntityId::new(self.namespace, counter);
        registry
            .register(id, kind)
            .map_err(AllocationError::Registry)?;
        // No returned error is possible after registration. MAX is issued once;
        // None records exhaustion without wrapping or reserving a payload.
        self.next_counter = counter.checked_add(1);
        Ok(id)
    }
}

/// One shared monotone stream for real cells and particles.
///
/// Each call registers its ID before advancing. Exhaustion or a registry error
/// leaves both allocator and registry unchanged. No occupied counter is skipped.
/// Restore this checkpoint with the complete registry, not just active objects.
#[derive(Debug)]
pub struct SerialEntityAllocator {
    cursor: CounterCursor,
}

impl SerialEntityAllocator {
    /// Raw construction; the caller must establish namespace/cursor provenance.
    pub const fn new(namespace: u64, next_counter: u64) -> Self {
        Self::from_checkpoint(EntityAllocatorCheckpoint::new(
            namespace,
            Some(next_counter),
        ))
    }

    /// Raw restoration; use `restore_checked` at an imported-catalog boundary.
    pub const fn from_checkpoint(checkpoint: EntityAllocatorCheckpoint) -> Self {
        Self {
            cursor: CounterCursor {
                namespace: checkpoint.namespace,
                next_counter: checkpoint.next_counter,
            },
        }
    }

    /// Check the cursor against every retained real ID in the namespace.
    ///
    /// Import the complete registry, including retired IDs, before this call.
    /// `Some(next)` must exceed its high-water counter; `None` retires the
    /// stream. This checks coherence, not completeness/provenance. Do not add
    /// further imported IDs or fork the namespace's allocator after restoration.
    pub fn restore_checked(
        checkpoint: EntityAllocatorCheckpoint,
        registry: &IdentityRegistry,
    ) -> Result<Self, CheckpointError> {
        Ok(Self {
            cursor: CounterCursor::from_checked(
                checkpoint.namespace,
                checkpoint.next_counter,
                registry,
                NamespaceKind::RealEntity,
            )?,
        })
    }

    pub const fn checkpoint(&self) -> EntityAllocatorCheckpoint {
        EntityAllocatorCheckpoint::new(self.cursor.namespace, self.cursor.next_counter)
    }

    pub fn allocate_cell(
        &mut self,
        registry: &mut IdentityRegistry,
    ) -> Result<CellId, AllocationError> {
        self.cursor
            .allocate(registry, IdentityKind::Cell)
            .map(CellId::new)
    }

    pub fn allocate_particle(
        &mut self,
        registry: &mut IdentityRegistry,
    ) -> Result<ParticleId, AllocationError> {
        self.cursor
            .allocate(registry, IdentityKind::Particle)
            .map(ParticleId::new)
    }
}

/// An independent event stream, with a namespace checked against real entities.
#[derive(Debug)]
pub struct SerialEventAllocator {
    cursor: CounterCursor,
}

impl SerialEventAllocator {
    /// Raw construction; the caller must establish namespace/cursor provenance.
    pub const fn new(namespace: u64, next_counter: u64) -> Self {
        Self::from_checkpoint(EventAllocatorCheckpoint::new(namespace, Some(next_counter)))
    }

    /// Raw restoration; use `restore_checked` at an imported-catalog boundary.
    pub const fn from_checkpoint(checkpoint: EventAllocatorCheckpoint) -> Self {
        Self {
            cursor: CounterCursor {
                namespace: checkpoint.namespace,
                next_counter: checkpoint.next_counter,
            },
        }
    }

    /// Check the event cursor against the complete retained event namespace.
    ///
    /// The same completeness/provenance and single-stream obligations as
    /// `SerialEntityAllocator::restore_checked` apply. Reimporting IDs requires
    /// another checked restoration before allocation resumes.
    pub fn restore_checked(
        checkpoint: EventAllocatorCheckpoint,
        registry: &IdentityRegistry,
    ) -> Result<Self, CheckpointError> {
        Ok(Self {
            cursor: CounterCursor::from_checked(
                checkpoint.namespace,
                checkpoint.next_counter,
                registry,
                NamespaceKind::Event,
            )?,
        })
    }

    pub const fn checkpoint(&self) -> EventAllocatorCheckpoint {
        EventAllocatorCheckpoint::new(self.cursor.namespace, self.cursor.next_counter)
    }

    pub fn allocate_event(
        &mut self,
        registry: &mut IdentityRegistry,
    ) -> Result<EventId, AllocationError> {
        self.cursor
            .allocate(registry, IdentityKind::Event)
            .map(EventId::new)
    }
}
