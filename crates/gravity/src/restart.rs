//! Rank-independent collisionless KDK restart. Recompute the exact force cache on
//! the new layout and compare it with the saved complete evaluation fingerprint.
use crate::{
    EntityId, ParticleId,
    direct::DirectConfig,
    kdk::KdkSystem,
    softening::{GravityModel, SofteningClass},
    state::{Catalog, CollisionlessKind, Particle, ParticleMetadata},
};
use mhd_io::{Decoder, Encoder, digest, seal, unseal};
use mhd_parallel::layout::Layout;

pub fn encode(system: &KdkSystem) -> Vec<u8> {
    let mut e = Encoder::new();
    e.string("openmhd-collisionless-kdk-v1");
    e.bytes(system.model().identity().bytes());
    e.bytes(system.config().identity().bytes());
    e.float(system.catalog().time());
    e.u64(system.catalog().revision());
    e.usize(system.catalog().particles().len());
    for p in system.catalog().particles() {
        let id = p.id().entity();
        e.u64(id.namespace());
        e.u64(id.counter());
        e.boolean(p.kind() == CollisionlessKind::Star);
        e.u64(u64::from(p.softening().value()));
        e.u64(u64::from(p.component()));
        e.u64(u64::from(p.galaxy()));
        e.float(p.mass());
        e.floats(&p.position());
        e.floats(&p.momentum());
    }
    e.bytes(&digest(&[&system.forces().canonical_bytes()]));
    seal(1, &e.finish())
}
pub fn decode_on<L: Layout>(
    bytes: &[u8],
    model: GravityModel,
    config: DirectConfig,
    layout: &L,
) -> Result<KdkSystem, String> {
    layout.agree(&digest(&[
        bytes,
        model.identity().bytes(),
        config.identity().bytes(),
    ]))?;
    let mut d = Decoder::new(unseal(bytes, 1)?);
    if d.string()? != "openmhd-collisionless-kdk-v1"
        || d.bytes()? != model.identity().bytes()
        || d.bytes()? != config.identity().bytes()
    {
        return Err("incompatible gravity checkpoint model, units or backend".into());
    }
    let time = d.float()?;
    let revision = d.u64()?;
    let count = d.count(97)?;
    let mut particles = Vec::with_capacity(count);
    for _ in 0..count {
        let id = ParticleId::new(EntityId::new(d.u64()?, d.u64()?));
        let kind = if d.boolean()? {
            CollisionlessKind::Star
        } else {
            CollisionlessKind::DarkMatter
        };
        let metadata = ParticleMetadata {
            kind,
            softening: SofteningClass::new(
                u16::try_from(d.u64()?).map_err(|_| "softening class overflow")?,
            ),
            component: u16::try_from(d.u64()?).map_err(|_| "component ID overflow")?,
            galaxy: u32::try_from(d.u64()?).map_err(|_| "galaxy ID overflow")?,
        };
        particles.push(
            Particle::from_momentum(id, d.float()?, d.floats()?, d.floats()?, metadata)
                .map_err(|e| e.to_string())?,
        );
    }
    let expected = d.bytes()?;
    d.finish()?;
    let catalog = Catalog::new(time, revision, particles).map_err(|e| e.to_string())?;
    let system = KdkSystem::new_on(catalog, model, config, layout).map_err(|e| e.to_string())?;
    if digest(&[&system.forces().canonical_bytes()]) != expected {
        return Err("restored force cache differs from saved endpoint".into());
    }
    Ok(system)
}
