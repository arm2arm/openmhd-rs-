//! Save full collisionless KDK endpoints and the accelerations used there.
//! Input rows contain id, population, mass, x, y, z, vx, vy, vz in code units.
use gravity::diagnostics::measure;
use gravity::direct::DirectConfig;
use gravity::kdk::KdkSystem;
use gravity::softening::{FixedPlummer, GravityModel, SofteningClass};
use gravity::state::{Catalog, CollisionlessKind, Particle, ParticleMetadata};
use gravity::units::UnitSystem;
use gravity::{EntityId, ParticleId};
use std::error::Error;
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::Path;

type Result<T> = std::result::Result<T, Box<dyn Error>>;

fn read_particles(path: &Path) -> Result<Vec<Particle>> {
    let input = fs::read_to_string(path)?;
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

fn snapshot(
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

fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    Ok(mhd_parallel::run_cli(&args, run)?)
}

fn run(args: &[String]) -> Result<()> {
    let [input, epsilon, dt, steps, stride, output] = args else {
        return Err(
            "usage: gravity-trajectory [--threads N] INITIAL EPSILON DT STEPS OUTPUT_STRIDE OUTPUT_DIRECTORY"
                .into(),
        );
    };
    let dt: f64 = dt.parse()?;
    let steps: usize = steps.parse()?;
    let stride: usize = stride.parse()?;
    if steps == 0 || stride == 0 || steps % stride != 0 {
        return Err("output stride must divide positive step count".into());
    }
    let catalog = Catalog::new(0.0, 0, read_particles(Path::new(input))?)?;
    let model = GravityModel::new(
        UnitSystem::dimensionless_g1(),
        FixedPlummer::new(epsilon.parse()?, SofteningClass::new(0))?,
    );
    let mut system = KdkSystem::new(catalog, model, DirectConfig::default())?;
    let directory = Path::new(output);
    fs::create_dir(directory)?;
    let mut states = BufWriter::new(File::create(directory.join("particles.csv"))?);
    let mut ledger = BufWriter::new(File::create(directory.join("conservation.csv"))?);
    writeln!(
        states,
        "step,time,id,population,mass,x,y,z,vx,vy,vz,ax,ay,az"
    )?;
    writeln!(
        ledger,
        "step,time,mass,kinetic,potential,energy,px,py,pz,lx,ly,lz"
    )?;
    snapshot(&system, 0, &mut states, &mut ledger)?;
    for step in 1..=steps {
        system.try_step(dt)?;
        if step % stride == 0 {
            snapshot(&system, step, &mut states, &mut ledger)?;
        }
    }
    states.flush()?;
    ledger.flush()?;
    Ok(())
}
