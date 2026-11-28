//! Stream moving Voronoi cells and their outward polygon loops as CSV.
use moving_mesh::three_d::motion_io::{self as motion_catalog, HEADER, write_epoch};
use moving_mesh::three_d::*;
use std::collections::BTreeMap;
use std::error::Error;
use std::io::{self, Write};

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    Ok(mhd_parallel::run_cli(&args, run)?)
}

fn run(args: &[String]) -> Result<(), Box<dyn Error>> {
    let [file, timesteps @ ..] = args else {
        return Err("usage: moving-voronoi3 [--threads N] CATALOG DT [DT ...]".into());
    };
    if timesteps.is_empty() {
        return Err("provide at least one positive timestep".into());
    }
    let mut steps = Vec::new();
    let mut time = 0.0;
    for arg in timesteps {
        let dt: f64 = arg.parse()?;
        let next = time + dt;
        if !dt.is_finite() || !next.is_finite() || next <= time {
            return Err("timestep must advance the finite simulation clock".into());
        }
        steps.push((next, dt));
        time = next;
    }
    let catalog = motion_catalog::read_catalog(file)?;
    let velocities: BTreeMap<_, _> = catalog
        .flow
        .into_iter()
        .map(|(id, gas)| (id, gas.velocity))
        .collect();
    let mut mesh = HalfSpaceOracle3::build_motion_epoch(catalog.domain, &catalog.generators)?;
    let mut out = io::BufWriter::new(io::stdout().lock());
    writeln!(out, "{HEADER}")?;
    write_epoch(&mut out, 0, 0.0, &mesh)?;
    for (i, (time, dt)) in steps.into_iter().enumerate() {
        let step = advance_generators3(&mesh, &velocities, dt)?;
        let mut kept = 0;
        let mut born = 0;
        let mut lost = 0;
        for change in step.face_changes.values() {
            match change {
                FaceChange3::Retained { .. } => kept += 1,
                FaceChange3::Appeared(_) => born += 1,
                FaceChange3::Disappeared(_) => lost += 1,
            }
        }
        mesh = step.geometry;
        write_epoch(&mut out, i + 1, time, &mesh)?;
        eprintln!(
            "step={} time={time:.17e} retained={kept} appeared={born} disappeared={lost}",
            i + 1
        );
    }
    out.flush()?;
    Ok(())
}
