use super::{MpiLayout, Result, save, shared_input};
use gravity::{
    direct::DirectConfig,
    kdk::KdkSystem,
    restart,
    softening::{FixedPlummer, GravityModel, SofteningClass},
    state::Catalog,
    trajectory::{parse_particles, snapshot},
    units::UnitSystem,
};
use mhd_parallel::layout::Layout;
use std::{io::Write, path::Path};

pub fn run(layout: &MpiLayout<'_>, args: &[String], restore: bool) -> Result<()> {
    let [file, eps, dt, steps, stride, out] = args else {
        return Err("gravity[_restart] INPUT EPSILON DT STEPS OUTPUT_STRIDE DIRECTORY".into());
    };
    let dt = dt.parse::<f64>()?;
    let steps = steps.parse::<usize>()?;
    let stride = stride.parse::<usize>()?;
    if steps == 0 || stride == 0 || steps % stride != 0 {
        return Err("stride must divide a positive step count".into());
    }
    let input = shared_input(layout, file)?;
    let model = GravityModel::new(
        UnitSystem::dimensionless_g1(),
        FixedPlummer::new(eps.parse()?, SofteningClass::new(0))?,
    );
    let mut sim = if restore {
        restart::decode_on(&input, model, DirectConfig::default(), layout)?
    } else {
        KdkSystem::new_on(
            Catalog::new(0., 0, parse_particles(std::str::from_utf8(&input)?)?)?,
            model,
            DirectConfig::default(),
            layout,
        )?
    };
    let mut states = Vec::new();
    let mut ledger = Vec::new();
    let root = layout.rank() == 0;
    if root {
        writeln!(
            states,
            "step,time,id,population,mass,x,y,z,vx,vy,vz,ax,ay,az"
        )?;
        writeln!(
            ledger,
            "step,time,mass,kinetic,potential,energy,px,py,pz,lx,ly,lz"
        )?;
        snapshot(
            &sim,
            usize::try_from(sim.catalog().revision())?,
            &mut states,
            &mut ledger,
        )?;
    }
    for j in 1..=steps {
        sim.try_step_on(dt, layout)?;
        if root && j % stride == 0 {
            snapshot(
                &sim,
                usize::try_from(sim.catalog().revision())?,
                &mut states,
                &mut ledger,
            )?;
        }
    }
    let checkpoint = restart::encode(&sim);
    layout.agree(&checkpoint)?;
    if root {
        let output = Path::new(out);
        std::fs::create_dir(output)?;
        save(output, "particles.csv", &states)?;
        save(output, "conservation.csv", &ledger)?;
        save(output, "checkpoint.bin", &checkpoint)?;
    }
    Ok(())
}
