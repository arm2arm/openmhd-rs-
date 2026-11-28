//! Stream moving Voronoi cells and their outward polygon loops as CSV.
use moving_mesh::three_d::motion_io::{self as motion_catalog, HEADER, write_epoch};
use moving_mesh::three_d::sweeps::SharedSweeps3;
use moving_mesh::three_d::*;
use std::collections::BTreeMap;
use std::error::Error;
use std::io::{self, Write};

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    Ok(mhd_parallel::run_cli(&args, run)?)
}

fn run(args: &[String]) -> Result<(), Box<dyn Error>> {
    let sweeps = args.first().is_some_and(|arg| arg == "--sweeps");
    let [file, timesteps @ ..] = &args[usize::from(sweeps)..] else {
        return Err("usage: moving-voronoi3 [--threads N] [--sweeps] CATALOG DT [DT ...]".into());
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
        if sweeps {
            let old = prescribed_motion_rates3(&mesh, &velocities, [0.0; 3])?;
            let new = prescribed_motion_rates3(&step.geometry, &velocities, [0.0; 3])?;
            let euler = SharedSweeps3::euler(&mesh, &old, &step.geometry, dt)?;
            let heun = SharedSweeps3::heun(&mesh, &old, &step.geometry, &new, dt)?;
            for (name, sweep) in [("Euler", euler), ("Heun", heun)] {
                let max_correction = sweep
                    .faces()
                    .values()
                    .map(|f| f.correction.abs())
                    .fold(0.0, f64::max);
                eprintln!(
                    "sweeps step={} rule={name} raw_relative={:.17e} corrected_relative={:.17e} max_abs_correction={max_correction:.17e}",
                    i + 1,
                    sweep.max_raw_relative_defect,
                    sweep.max_corrected_relative_defect
                );
            }
        }
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
