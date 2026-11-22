//! Serial sorted-ID i<j oracle. One raw pair force, accumulated with both signs.
use crate::checked::{Sum, VectorSum, add, div, mul, norm};
use crate::identity::f64_bytes;
use crate::kernel::pair;
use crate::softening::GravityModel;
use crate::state::Catalog;
use crate::{CacheField, GravityError, Identity, ParticleId, Vec3};

#[derive(Clone, Debug)]
pub struct DirectConfig {
    revision: u64,
    identity: Identity,
}

impl DirectConfig {
    /// Revision is a configuration identity, not a change to the physical law.
    pub fn new(revision: u64) -> Self {
        let mut bytes = b"gravity-backend-v1\0serial-sorted-i<j-Neumaier\0".to_vec();
        bytes.extend_from_slice(&revision.to_be_bytes());
        Self {
            revision,
            identity: Identity::new(bytes),
        }
    }

    pub fn revision(&self) -> u64 {
        self.revision
    }
    pub fn identity(&self) -> &Identity {
        &self.identity
    }
}

impl Default for DirectConfig {
    fn default() -> Self {
        Self::new(0)
    }
}

#[derive(Clone, Debug)]
pub struct CachePins {
    time_bits: u64,
    state_revision: u64,
    sources: Identity,
    state: Identity,
    g_bits: u64,
    epsilon_bits: u64,
    model: Identity,
    units: Identity,
    backend: Identity,
}

impl CachePins {
    fn new(catalog: &Catalog, model: &GravityModel, config: &DirectConfig) -> Self {
        Self {
            time_bits: catalog.time().to_bits(),
            state_revision: catalog.revision(),
            sources: catalog.source_identity().clone(),
            state: catalog.state_identity().clone(),
            g_bits: model.g().to_bits(),
            epsilon_bits: model.softening().epsilon().to_bits(),
            model: model.identity().clone(),
            units: model.units().identity().clone(),
            backend: config.identity().clone(),
        }
    }

    pub fn time_bits(&self) -> u64 {
        self.time_bits
    }
    pub fn state_revision(&self) -> u64 {
        self.state_revision
    }
    pub fn sources(&self) -> &Identity {
        &self.sources
    }
    pub fn state(&self) -> &Identity {
        &self.state
    }
    pub fn model(&self) -> &Identity {
        &self.model
    }
    pub fn units(&self) -> &Identity {
        &self.units
    }
    pub fn backend(&self) -> &Identity {
        &self.backend
    }

    fn validate(&self, expected: &Self) -> Result<(), GravityError> {
        for (matches, field) in [
            (self.time_bits == expected.time_bits, CacheField::Time),
            (
                self.state_revision == expected.state_revision,
                CacheField::StateRevision,
            ),
            (self.sources == expected.sources, CacheField::Sources),
            (self.state == expected.state, CacheField::State),
            (
                self.g_bits == expected.g_bits,
                CacheField::GravitationalConstant,
            ),
            (
                self.epsilon_bits == expected.epsilon_bits,
                CacheField::Softening,
            ),
            (self.model == expected.model, CacheField::Model),
            (self.units == expected.units, CacheField::Units),
            (self.backend == expected.backend, CacheField::Backend),
        ] {
            if !matches {
                return Err(GravityError::CacheMismatch(field));
            }
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug)]
pub struct ForceSample {
    id: ParticleId,
    force: Vec3,
    specific_potential: f64,
    force_scale: f64,
    potential_scale: f64,
}

impl ForceSample {
    pub fn id(&self) -> ParticleId {
        self.id
    }
    pub fn force(&self) -> Vec3 {
        self.force
    }
    pub fn specific_potential(&self) -> f64 {
        self.specific_potential
    }
    pub fn force_scale(&self) -> f64 {
        self.force_scale
    }
    pub fn potential_scale(&self) -> f64 {
        self.potential_scale
    }
}

#[derive(Clone, Debug)]
pub struct Evaluation {
    pins: CachePins,
    samples: Vec<ForceSample>,
    pair_energy: f64,
    energy_scale: f64,
    net_force_scale: f64,
    torque_scale: f64,
    pair_count: u64,
}

impl Evaluation {
    pub fn pins(&self) -> &CachePins {
        &self.pins
    }
    pub fn samples(&self) -> &[ForceSample] {
        &self.samples
    }
    pub fn pair_energy(&self) -> f64 {
        self.pair_energy
    }
    pub fn energy_scale(&self) -> f64 {
        self.energy_scale
    }
    pub fn net_force_scale(&self) -> f64 {
        self.net_force_scale
    }
    pub fn torque_scale(&self) -> f64 {
        self.torque_scale
    }
    pub fn pair_count(&self) -> u64 {
        self.pair_count
    }

    pub fn validate_for(
        &self,
        catalog: &Catalog,
        model: &GravityModel,
        config: &DirectConfig,
    ) -> Result<(), GravityError> {
        self.pins
            .validate(&CachePins::new(catalog, model, config))?;
        if self.samples.len() != catalog.particles().len()
            || self
                .samples
                .iter()
                .zip(catalog.particles())
                .any(|(s, p)| s.id != p.id())
        {
            return Err(GravityError::CacheSamples);
        }
        Ok(())
    }

    /// Inspect a sample only after validate_for at the caller's force epoch.
    pub fn sample(&self, id: ParticleId) -> Result<&ForceSample, GravityError> {
        self.samples
            .binary_search_by_key(&id, ForceSample::id)
            .map(|i| &self.samples[i])
            .map_err(|_| GravityError::MissingId(id))
    }

    pub fn acceleration(
        &self,
        catalog: &Catalog,
        model: &GravityModel,
        config: &DirectConfig,
        id: ParticleId,
    ) -> Result<Vec3, GravityError> {
        self.validate_for(catalog, model, config)?;
        let mass = catalog.particle(id)?.mass();
        let f = self.sample(id)?.force;
        Ok([
            div(f[0], mass, "acceleration")?,
            div(f[1], mass, "acceleration")?,
            div(f[2], mass, "acceleration")?,
        ])
    }

    pub fn canonical_bytes(&self) -> Vec<u8> {
        use crate::identity::sized_bytes;
        let mut bytes = b"gravity-evaluation-v1\0".to_vec();
        bytes.extend_from_slice(&self.pins.time_bits.to_be_bytes());
        bytes.extend_from_slice(&self.pins.state_revision.to_be_bytes());
        for id in [
            &self.pins.sources,
            &self.pins.state,
            &self.pins.model,
            &self.pins.units,
            &self.pins.backend,
        ] {
            sized_bytes(&mut bytes, id.bytes());
        }
        bytes.extend_from_slice(&self.pins.g_bits.to_be_bytes());
        bytes.extend_from_slice(&self.pins.epsilon_bits.to_be_bytes());
        bytes.extend_from_slice(&self.pair_count.to_be_bytes());
        for value in [
            self.pair_energy,
            self.energy_scale,
            self.net_force_scale,
            self.torque_scale,
        ] {
            f64_bytes(&mut bytes, value);
        }
        bytes.extend_from_slice(&(self.samples.len() as u64).to_be_bytes());
        for s in &self.samples {
            bytes.extend_from_slice(s.id.entity().to_string().as_bytes());
            for value in s.force {
                f64_bytes(&mut bytes, value);
            }
            for value in [s.specific_potential, s.force_scale, s.potential_scale] {
                f64_bytes(&mut bytes, value);
            }
        }
        bytes
    }
}

pub fn evaluate(
    catalog: &Catalog,
    model: &GravityModel,
    config: &DirectConfig,
) -> Result<Evaluation, GravityError> {
    let particles = catalog.particles();
    for p in particles {
        if p.softening() != model.softening().class() {
            return Err(GravityError::UnsupportedSofteningClass);
        }
    }
    let mut forces = vec![VectorSum::default(); particles.len()];
    let mut potentials = vec![Sum::default(); particles.len()];
    let mut force_scales = vec![Sum::default(); particles.len()];
    let mut potential_scales = vec![Sum::default(); particles.len()];
    let mut energy = Sum::default();
    let mut energy_scale = Sum::default();
    let mut net_force_scale = Sum::default();
    let mut torque_scale = Sum::default();
    let mut pair_count = 0_u64;
    for (i, left) in particles.iter().enumerate() {
        for (j, right) in particles.iter().enumerate().skip(i + 1) {
            let contribution = pair(model, left, right)?;
            let f = contribution.force_on_left;
            forces[i].add(f)?;
            forces[j].add(f.map(|v| -v))?;
            potentials[i].add(contribution.specific_potential_left)?;
            potentials[j].add(contribution.specific_potential_right)?;
            let magnitude = norm(f)?;
            force_scales[i].add(magnitude)?;
            force_scales[j].add(magnitude)?;
            potential_scales[i].add(contribution.specific_potential_left.abs())?;
            potential_scales[j].add(contribution.specific_potential_right.abs())?;
            energy.add(contribution.energy)?;
            energy_scale.add(contribution.energy.abs())?;
            net_force_scale.add(mul(2.0, magnitude, "net-force scale")?)?;
            let radii = add(
                norm(left.position())?,
                norm(right.position())?,
                "torque scale radii",
            )?;
            torque_scale.add(mul(radii, magnitude, "torque scale")?)?;
            pair_count = pair_count
                .checked_add(1)
                .ok_or(GravityError::CountOverflow)?;
        }
    }
    let mut samples = Vec::with_capacity(particles.len());
    for (i, p) in particles.iter().enumerate() {
        samples.push(ForceSample {
            id: p.id(),
            force: forces[i].value()?,
            specific_potential: potentials[i].value()?,
            force_scale: force_scales[i].value()?,
            potential_scale: potential_scales[i].value()?,
        });
    }
    Ok(Evaluation {
        pins: CachePins::new(catalog, model, config),
        samples,
        pair_energy: energy.value()?,
        energy_scale: energy_scale.value()?,
        net_force_scale: net_force_scale.value()?,
        torque_scale: torque_scale.value()?,
        pair_count,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::EntityId;
    use crate::softening::FixedPlummer;
    use crate::state::{CollisionlessKind, Particle, ParticleMetadata};
    use crate::units::UnitSystem;

    // Deliberately poison exactly one private pin, keeping all others equal.
    // Real changed-context controls live in tests/reference.rs as well.
    fn isolated_pin(field: CacheField) {
        let class = crate::softening::SofteningClass::new(0);
        let p = Particle::from_momentum(
            ParticleId::new(EntityId::new(0, 0)),
            2.0,
            [0.0; 3],
            [0.0; 3],
            ParticleMetadata {
                kind: CollisionlessKind::DarkMatter,
                softening: class,
                component: 0,
                galaxy: 0,
            },
        )
        .unwrap();
        let catalog = Catalog::new(0.0, 0, vec![p]).unwrap();
        let model = GravityModel::new(
            UnitSystem::dimensionless_g1(),
            FixedPlummer::new(4.0, class).unwrap(),
        );
        let config = DirectConfig::default();
        let mut cache = evaluate(&catalog, &model, &config).unwrap();
        match field {
            CacheField::Time => cache.pins.time_bits = 1,
            CacheField::StateRevision => cache.pins.state_revision = 1,
            CacheField::Sources => cache.pins.sources = Identity::new(b"different source".to_vec()),
            CacheField::State => cache.pins.state = Identity::new(b"different state".to_vec()),
            CacheField::GravitationalConstant => cache.pins.g_bits = 2.0_f64.to_bits(),
            CacheField::Softening => cache.pins.epsilon_bits = 2.0_f64.to_bits(),
            CacheField::Model => cache.pins.model = Identity::new(b"different model".to_vec()),
            CacheField::Units => cache.pins.units = Identity::new(b"different units".to_vec()),
            CacheField::Backend => {
                cache.pins.backend = Identity::new(b"different backend".to_vec())
            }
        }
        assert_eq!(
            cache.validate_for(&catalog, &model, &config),
            Err(GravityError::CacheMismatch(field))
        );
    }

    #[test]
    fn cache_time_guard_isolated() {
        isolated_pin(CacheField::Time);
    }
    #[test]
    fn cache_revision_guard_isolated() {
        isolated_pin(CacheField::StateRevision);
    }
    #[test]
    fn cache_sources_guard_isolated() {
        isolated_pin(CacheField::Sources);
    }
    #[test]
    fn cache_state_guard_isolated() {
        isolated_pin(CacheField::State);
    }
    #[test]
    fn cache_g_guard_isolated() {
        isolated_pin(CacheField::GravitationalConstant);
    }
    #[test]
    fn cache_epsilon_guard_isolated() {
        isolated_pin(CacheField::Softening);
    }
    #[test]
    fn cache_model_guard_isolated() {
        isolated_pin(CacheField::Model);
    }
    #[test]
    fn cache_units_guard_isolated() {
        isolated_pin(CacheField::Units);
    }
    #[test]
    fn cache_backend_guard_isolated() {
        isolated_pin(CacheField::Backend);
    }
}
