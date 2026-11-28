//! Collisionless trajectory table format shared by single-process and MPI drivers.
use crate::{
    EntityId, ParticleId,
    diagnostics::measure,
    kdk::KdkSystem,
    softening::SofteningClass,
    state::{CollisionlessKind, Particle, ParticleMetadata},
};
use std::{error::Error, io::Write};
type Result<T> = std::result::Result<T, Box<dyn Error>>;
pub fn parse_particles(input: &str) -> Result<Vec<Particle>> {
    let mut particles = Vec::new();
    for line in input
        .lines()
        .filter(|line| !line.trim().is_empty() && !line.starts_with('#'))
    {
        let fields: Vec<_> = line.split_whitespace().collect();
        let [id, population, mass, x, y, z, vx, vy, vz] = fields.as_slice() else {
            return Err("expected nine fields per initial particle".into());
        };
        let metadata = ParticleMetadata {
            kind: CollisionlessKind::DarkMatter,
            softening: SofteningClass::new(0),
            component: 0,
            galaxy: population.parse()?,
        };
        particles.push(Particle::from_velocity(
            ParticleId::new(EntityId::new(1, id.parse()?)),
            mass.parse()?,
            [x.parse()?, y.parse()?, z.parse()?],
            [vx.parse()?, vy.parse()?, vz.parse()?],
            metadata,
        )?);
    }
    if particles.is_empty() {
        return Err("empty initial catalog".into());
    }
    Ok(particles)
}

pub fn snapshot(
    system: &KdkSystem,
    step: usize,
    states: &mut impl Write,
    ledger: &mut impl Write,
) -> Result<()> {
    let catalog = system.catalog();
    let forces = system.forces();
    let sums = measure(catalog, system.model(), system.config(), forces)?;
    let time = catalog.time();
    for p in catalog.particles() {
        let a = forces.sample(p.id())?.force().map(|f| f / p.mass());
        write!(
            states,
            "{step},{time:.17e},{},{},{:.17e}",
            p.id().entity().counter(),
            p.galaxy(),
            p.mass()
        )?;
        for value in p.position().into_iter().chain(p.velocity()).chain(a) {
            write!(states, ",{value:.17e}")?;
        }
        writeln!(states)?;
    }
    write!(
        ledger,
        "{step},{time:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
        sums.mass, sums.kinetic_lab, sums.pair_energy, sums.hamiltonian_lab
    )?;
    for value in sums
        .momentum
        .into_iter()
        .chain(sums.angular_momentum_origin)
    {
        write!(ledger, ",{value:.17e}")?;
    }
    writeln!(ledger)?;
    Ok(())
}
