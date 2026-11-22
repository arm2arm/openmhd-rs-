//! Unvalidated G1 reference implementation. GP-1/2/4/6 are project equations
//! in docs/galaxy/GRAVITY_PARTICLES_SPEC.md; this is not a gas/tree backend.

pub mod diagnostics;
pub mod direct;
pub mod kdk;
pub mod kernel;
pub mod softening;
pub mod state;
pub mod units;

mod checked;
mod identity;

use std::fmt;

pub use galaxy_types::{EntityId, ParticleId};
pub use identity::Identity;

pub type Vec3 = [f64; 3];

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CacheField {
    Time,
    StateRevision,
    Sources,
    State,
    GravitationalConstant,
    Softening,
    Model,
    Units,
    Backend,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum GravityError {
    InvalidValue(&'static str),
    Nonrepresentable(&'static str),
    DuplicateId(ParticleId),
    MissingId(ParticleId),
    SelfPair,
    UnsupportedSofteningClass,
    CacheMismatch(CacheField),
    CacheSamples,
    PhysicalUnitsRequired,
    EmptyTimestep,
    RevisionOverflow,
    TimeNotAdvanced,
    StepAboveCeiling,
    CountOverflow,
}

impl fmt::Display for GravityError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}

impl std::error::Error for GravityError {}
