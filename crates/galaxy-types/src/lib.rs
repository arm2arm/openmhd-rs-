//! Shared persistent identities for the galaxy implementation.
//!
//! Typed IDs distinguish entity kinds. Uniqueness additionally requires one
//! authoritative [`IdentityRegistry`] and coherent allocator checkpoints.
//! This crate implements no geometry, gravity, source physics, or distributed
//! allocation, and defines no JSON number representation for an ID.

pub mod identity;

pub use identity::{
    AllocationError, CellId, EntityAllocatorCheckpoint, EntityId, EventAllocatorCheckpoint, EventId,
    IdentityKind, IdentityRegistry, NamespaceKind, ParseEntityIdError, ParticleId, RegistryError,
    SerialEntityAllocator, SerialEventAllocator,
};
