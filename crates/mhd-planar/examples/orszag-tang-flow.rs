//! Export the fixed-grid velocity history used by the Figure 23 mesh visualization.
use mhd_planar::{Config, Simulation};
use std::error::Error;
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::PathBuf;

fn main() -> Result<(), Box<dyn Error>> {
    let destination = PathBuf::from(
        std::env::args_os()
            .nth(1)
            .ok_or("expected an output directory")?,
    );
    fs::create_dir(&destination)?;
    let n = 64usize;
    let frames = 129usize;
    let mut sim = Simulation::new(Config {
        nx: n,
        ny: n,
        ..Config::default()
    })?;
    let mut order = vec![None; n * n];
    for i in 0..sim.mesh.cells.len() {
        let pos = sim.position(i);
        let [x, y] = pos.map(|v| (v * n as f64).floor() as usize);
        if x >= n || y >= n || order[y * n + x].replace(i).is_some() {
            return Err("fixed-grid centers are not a bijection".into());
        }
        for (coord, index) in pos.into_iter().zip([x, y]) {
            if (coord * n as f64 - (index as f64 + 0.5)).abs() > 1e-9 {
                return Err("unexpected fixed-grid cell center".into());
            }
        }
    }
    let order: Vec<usize> = order
        .into_iter()
        .collect::<Option<_>>()
        .ok_or("missing cell center")?;
    let mut flow = BufWriter::new(File::create(destination.join("velocity.bin"))?);
    flow.write_all(b"OMVFLOW1")?;
    for value in [n as u32, frames as u32] {
        flow.write_all(&value.to_le_bytes())?;
    }
    let mut history = BufWriter::new(File::create(destination.join("history.csv"))?);
    writeln!(
        history,
        "time,steps,rejected_steps,min_density,min_pressure,mass,total_energy,relative_budget_error"
    )?;
    for frame in 0..frames {
        let time = frame as f64 * 0.016;
        sim.advance_to(time)?;
        let diagnostics = sim.diagnostics()?;
        let q = sim.primitives()?;
        if sim.time != time || diagnostics.min_density <= 0.0 || diagnostics.min_pressure <= 0.0 {
            return Err("incomplete or nonphysical flow checkpoint".into());
        }
        flow.write_all(&sim.time.to_le_bytes())?;
        for &i in &order {
            for value in &q[i].velocity[..2] {
                if !value.is_finite() {
                    return Err("nonfinite velocity".into());
                }
                flow.write_all(&value.to_le_bytes())?;
            }
        }
        writeln!(
            history,
            "{:.17e},{},{},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
            sim.time,
            sim.steps,
            sim.rejected_steps,
            diagnostics.min_density,
            diagnostics.min_pressure,
            diagnostics.totals[0],
            diagnostics.totals[4],
            diagnostics.relative_budget_error
        )?;
    }
    flow.flush()?;
    history.flush()?;
    Ok(())
}
