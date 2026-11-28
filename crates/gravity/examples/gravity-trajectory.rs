//! Save full collisionless KDK endpoints and the accelerations used there.
//! Input rows contain id, population, mass, x, y, z, vx, vy, vz in code units.
use gravity::direct::DirectConfig;
use gravity::kdk::KdkSystem;
use gravity::softening::{FixedPlummer, GravityModel, SofteningClass};
use gravity::state::Catalog;
use gravity::trajectory::{parse_particles, snapshot};
use gravity::units::UnitSystem;
use std::error::Error;
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::Path;

type Result<T> = std::result::Result<T, Box<dyn Error>>;

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
    let catalog = Catalog::new(0.0, 0, parse_particles(&fs::read_to_string(input)?)?)?;
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
