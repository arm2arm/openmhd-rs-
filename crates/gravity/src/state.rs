use crate::checked::{div, finite, mul, positive, vector};
use crate::identity::{f64_bytes, sized_bytes};
use crate::softening::SofteningClass;
use crate::{GravityError, Identity, ParticleId, Vec3};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CollisionlessKind {
    DarkMatter,
    Star,
}

/// Analysis labels and the selected common-softening class. No label changes G.
#[derive(Clone, Copy, Debug)]
pub struct ParticleMetadata {
    pub kind: CollisionlessKind,
    pub softening: SofteningClass,
    pub component: u16,
    pub galaxy: u32,
}

#[derive(Clone, Debug)]
pub struct Particle {
    id: ParticleId,
    kind: CollisionlessKind,
    mass: f64,
    position: Vec3,
    momentum: Vec3,
    softening: SofteningClass,
    component: u16,
    galaxy: u32,
}

impl Particle {
    pub fn from_momentum(
        id: ParticleId,
        mass: f64,
        position: Vec3,
        momentum: Vec3,
        metadata: ParticleMetadata,
    ) -> Result<Self, GravityError> {
        positive(mass, "particle mass")?;
        vector(position, "particle position")?;
        vector(momentum, "particle momentum")?;
        for p in momentum {
            div(p, mass, "particle velocity")?;
        }
        Ok(Self { id, kind: metadata.kind, mass, position, momentum,
            softening: metadata.softening, component: metadata.component, galaxy: metadata.galaxy })
    }

    pub fn from_velocity(
        id: ParticleId,
        mass: f64,
        position: Vec3,
        velocity: Vec3,
        metadata: ParticleMetadata,
    ) -> Result<Self, GravityError> {
        positive(mass, "particle mass")?;
        vector(velocity, "particle velocity")?;
        let mut momentum = [0.0; 3];
        for (out, v) in momentum.iter_mut().zip(velocity) {
            *out = mul(mass, v, "initial momentum")?;
        }
        Self::from_momentum(id, mass, position, momentum, metadata)
    }

    pub fn id(&self) -> ParticleId { self.id }
    pub fn kind(&self) -> CollisionlessKind { self.kind }
    pub fn mass(&self) -> f64 { self.mass }
    pub fn position(&self) -> Vec3 { self.position }
    pub fn momentum(&self) -> Vec3 { self.momentum }
    pub fn softening(&self) -> SofteningClass { self.softening }
    pub fn component(&self) -> u16 { self.component }
    pub fn galaxy(&self) -> u32 { self.galaxy }

    pub fn velocity(&self) -> Vec3 {
        self.momentum.map(|p| p / self.mass)
    }

    pub(crate) fn moved(&self, position: Vec3, momentum: Vec3) -> Result<Self, GravityError> {
        Self::from_momentum(self.id, self.mass, position, momentum, ParticleMetadata {
            kind: self.kind, softening: self.softening, component: self.component, galaxy: self.galaxy,
        })
    }

    fn source_bytes(&self, bytes: &mut Vec<u8>) {
        bytes.extend_from_slice(self.id.entity().to_string().as_bytes());
        bytes.push(match self.kind { CollisionlessKind::DarkMatter => 0, CollisionlessKind::Star => 1 });
        bytes.extend_from_slice(&self.softening.value().to_be_bytes());
        f64_bytes(bytes, self.mass);
        for value in self.position { f64_bytes(bytes, value); }
    }
}

/// Checked, sorted, immutable collisionless state. No gas/geometry placeholder.
#[derive(Clone, Debug)]
pub struct Catalog {
    particles: Vec<Particle>,
    time: f64,
    revision: u64,
    sources: Identity,
    state: Identity,
}

impl Catalog {
    pub fn new(time: f64, revision: u64, mut particles: Vec<Particle>) -> Result<Self, GravityError> {
        finite(time, "catalog time")?;
        particles.sort_by_key(Particle::id);
        for pair in particles.windows(2) {
            if pair[0].id == pair[1].id {
                return Err(GravityError::DuplicateId(pair[0].id));
            }
        }
        let count = u64::try_from(particles.len()).map_err(|_| GravityError::CountOverflow)?;
        let mut source_bytes = b"gravity-sources-v1\0collisionless\0".to_vec();
        source_bytes.extend_from_slice(&count.to_be_bytes());
        for p in &particles { p.source_bytes(&mut source_bytes); }
        let sources = Identity::new(source_bytes);
        let mut state_bytes = b"gravity-catalog-v1\0".to_vec();
        f64_bytes(&mut state_bytes, time);
        state_bytes.extend_from_slice(&revision.to_be_bytes());
        sized_bytes(&mut state_bytes, sources.bytes());
        for p in &particles {
            for v in p.momentum { f64_bytes(&mut state_bytes, v); }
            state_bytes.extend_from_slice(&p.component.to_be_bytes());
            state_bytes.extend_from_slice(&p.galaxy.to_be_bytes());
        }
        Ok(Self { particles, time, revision, sources, state: Identity::new(state_bytes) })
    }

    pub fn particles(&self) -> &[Particle] { &self.particles }
    pub fn time(&self) -> f64 { self.time }
    pub fn revision(&self) -> u64 { self.revision }
    pub fn source_identity(&self) -> &Identity { &self.sources }
    pub fn state_identity(&self) -> &Identity { &self.state }

    pub fn particle(&self, id: ParticleId) -> Result<&Particle, GravityError> {
        self.particles.binary_search_by_key(&id, Particle::id)
            .map(|i| &self.particles[i]).map_err(|_| GravityError::MissingId(id))
    }
}
