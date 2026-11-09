//! Geometry control only; does not change the registered Brio benchmark or gates.
use mhd_vector_pot::{
    benchmarks::brio_initial,
    general::{Config, Motion, Profile, Simulation},
};
use moving_mesh::{Derivatives, Mesh};
use std::{fs, io::Write, path::Path, time::Instant};
#[path = "support/shock_pattern.rs"]
mod shock_pattern;

fn geometry(mesh: &Mesh, base_cells: usize, path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let mut cells = fs::File::create(path.join("geometry.csv"))?;
    writeln!(cells, "id,base_id,tile,gx,gy,cx,cy,volume,face_count")?;
    let stencil = Derivatives::build(mesh, false)?;
    let mut faces = fs::File::create(path.join("stencils.csv"))?;
    writeln!(
        faces,
        "id,base_id,neighbor,neighbor_base,dx,dy,area,nx,ny,face_dx,face_dy,weight_x,weight_y,baseline_neighbor"
    )?;
    for (i, c) in mesh.cells.iter().enumerate() {
        writeln!(
            cells,
            "{i},{},{},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{}",
            i % base_cells,
            i / base_cells,
            mesh.generators[i][0],
            mesh.generators[i][1],
            c.centroid[0],
            c.centroid[1],
            c.volume,
            c.faces.len()
        )?;
        for (&(f, sign), sample) in c.faces.iter().zip(&stencil.samples[i]) {
            let face = &mesh.faces[f];
            let (j, d) = mesh.neighbour(face, i);
            assert_eq!(sample.index, j);
            let df = mesh.displacement(face, i);
            writeln!(
                faces,
                "{i},{},{j},{},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{}",
                i % base_cells,
                j % base_cells,
                d[0],
                d[1],
                face.area,
                sign * face.normal[0],
                sign * face.normal[1],
                df[0],
                df[1],
                sample.weight[0],
                sample.weight[1],
                stencil.samples[i][0].index
            )?;
        }
    }
    Ok(())
}

fn cells(sim: &Simulation, path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let mut file = fs::File::create(path)?;
    writeln!(file, "id,x,y,volume,rho,p,vx,vy,vz,bx,by,bz")?;
    for (i, (c, q)) in sim
        .state()
        .mesh
        .cells
        .iter()
        .zip(sim.primitives()?)
        .enumerate()
    {
        writeln!(
            file,
            "{i},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
            c.centroid[0],
            c.centroid[1],
            c.volume,
            q.density,
            q.pressure,
            q.velocity[0],
            q.velocity[1],
            q.velocity[2],
            q.magnetic[0],
            q.magnetic[1],
            q.magnetic[2]
        )?;
    }
    Ok(())
}
fn diagnostic(sim: &Simulation, file: &mut fs::File) -> Result<(), String> {
    let d = sim.diagnostics()?;
    let bx = sim
        .primitives()?
        .iter()
        .map(|q| (q.magnetic[0] - 0.75).abs())
        .fold(0., f64::max);
    writeln!(file, "{:.17e},{},{:.17e},{:.17e},{bx:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
        sim.time(),sim.counters().steps,d.min_density,d.min_pressure,
        d.normalized_budget.iter().map(|v| v.abs()).fold(0.,f64::max),
        d.divergence_ls.dimensional.rms,d.divergence_ls.dimensional.max,
        d.divergence_face.dimensional.rms,d.divergence_face.dimensional.max,
        d.divergence_limited_face.dimensional.rms,d.divergence_limited_face.dimensional.max,
        d.mean_magnetic_drift[0],d.mean_magnetic_drift[1],d.mean_magnetic_drift[2])
        .map_err(|e| e.to_string())
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() < 5 || (args.len() - 5) % 2 != 0 {
        return Err("usage: paper-shock-geometry NX NY JITTER TIME NEW_DIRECTORY [--pattern-height H] [--repeat N]".into());
    }
    let nx: usize = args[0].parse()?;
    let ny: usize = args[1].parse()?;
    let jitter: f64 = args[2].parse()?;
    let time: f64 = args[3].parse()?;
    let mut height = None;
    let mut copies = 1_usize;
    for option in args[5..].chunks(2) {
        match option[0].as_str() {
            "--pattern-height" => height = Some(option[1].parse::<f64>()?),
            "--repeat" => copies = option[1].parse()?,
            _ => return Err("unknown pattern option".into()),
        }
    }
    let patterned = height.is_some() || copies != 1;
    if nx > 256
        || ny > 16
        || !(1..=4).contains(&copies)
        || ny * copies > 16
        || !(0. < time && time <= 0.04)
        || (patterned && ny != 4)
    {
        return Err("geometry probe bounds exceeded".into());
    }
    let path = Path::new(&args[4]);
    fs::create_dir(path)?;
    let start = Instant::now();
    let mesh = if patterned {
        shock_pattern::mesh(nx, jitter, height.unwrap_or(0.125), copies)?
    } else {
        Mesh::lattice(nx, ny, [2., 0.125], jitter)?
    };
    geometry(&mesh, nx * ny, path)?;
    let lengths = mesh.lengths;
    let mut sim = Simulation::new(
        mesh,
        Config {
            profile: Profile::PaperStateEmfV1,
            motion: Motion::Fixed,
            gamma: 2.,
            mean_magnetic: [0.75, 0., 0.],
            ..Config::default()
        },
        |x| brio_initial(x, [0.; 3]),
    )?;
    cells(&sim, &path.join("initial.csv"))?;
    let mut rates = fs::File::create(path.join("initial_rates.csv"))?;
    writeln!(
        rates,
        "id,total_rate,magnetic_rate,magnetic_rate_fv,pressure_rate"
    )?;
    for (i, r) in sim.energy_rates()?.iter().enumerate() {
        writeln!(
            rates,
            "{i},{:.17e},{:.17e},{:.17e},{:.17e}",
            r.total_rate, r.magnetic_rate, r.magnetic_rate_fv, r.pressure_rate
        )?;
    }
    let mut history = fs::File::create(path.join("history.csv"))?;
    writeln!(
        history,
        "time,steps,rho_min,p_min,bx_error,budget_max,div_ls_rms,div_ls_max,div_face_rms,div_face_max,div_limited_rms,div_limited_max,mean_bx_drift,mean_by_drift,mean_bz_drift"
    )?;
    diagnostic(&sim, &mut history)?;
    let result = sim.advance_to_observed(time, |sim| {
        diagnostic(sim, &mut history)?;
        if start.elapsed().as_secs_f64() > 25. {
            return Err("geometry probe wall-time limit".into());
        }
        Ok(())
    });
    if let Err(error) = &result {
        fs::write(path.join("failure.txt"), error)?;
    }
    cells(&sim, &path.join("final.csv"))?;
    fs::write(
        path.join("status.txt"),
        format!(
            "nx={nx}\nny={}\npattern_rows={ny}\ncopies={copies}\nlength_x={}\nlength_y={}\njitter={jitter}\nrequested_time={time}\ncompleted={}\ntime={:.17e}\nseconds={:.6}\nrejected_state={}\nrejected_geometry={}\n",
            ny * copies,
            lengths[0],
            lengths[1],
            result.is_ok(),
            sim.time(),
            start.elapsed().as_secs_f64(),
            sim.counters().rejected_state,
            sim.counters().rejected_geometry
        ),
    )?;
    result.map_err(Into::into)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn repeated_pattern_preserves_local_periodic_geometry() {
        for jitter in [0., 0.15] {
            for height in [0.03125, 0.125] {
                let base = shock_pattern::mesh(64, jitter, height, 1).unwrap();
                for copies in [2, 4] {
                    let repeated = shock_pattern::mesh(64, jitter, height, copies).unwrap();
                    repeated.validate().unwrap();
                    for (i, c) in repeated.cells.iter().enumerate() {
                        let original = &base.cells[i % 256];
                        assert!((c.volume / original.volume - 1.).abs() < 1e-11);
                        assert!((c.centroid[0] - original.centroid[0]).abs() < 1e-12);
                        assert!(
                            (c.centroid[1] - (i / 256) as f64 * height - original.centroid[1])
                                .abs()
                                < 1e-12
                        );
                        let neighbors = |m: &Mesh, cell: usize| {
                            let mut rows: Vec<_> = m.cells[cell]
                                .faces
                                .iter()
                                .map(|&(f, _)| {
                                    let (j, d) = m.neighbour(&m.faces[f], cell);
                                    (j % 256, d, m.faces[f].area)
                                })
                                .collect();
                            rows.sort_by_key(|r| r.0);
                            rows
                        };
                        let a = neighbors(&base, i % 256);
                        let mut b = neighbors(&repeated, i);
                        assert_eq!(a.len(), b.len());
                        for a in &a {
                            // One base neighbor can occur in distinct periodic images.
                            // Match its physical displacement, not global-index order.
                            let matched = b.iter().position(|b| {
                                a.0 == b.0
                                    && (a.1[0] - b.1[0]).abs() < 1e-12
                                    && (a.1[1] - b.1[1]).abs() < 1e-12
                                    && (a.2 - b.2).abs() < 1e-12
                            });
                            assert!(
                                matched.is_some(),
                                "jitter={jitter} height={height} copies={copies} cell={i} unmatched={a:?}"
                            );
                            b.remove(matched.unwrap());
                        }
                    }
                }
            }
        }
    }

    #[test]
    fn compression_preserves_generator_pattern_and_baseline_is_exact() {
        let original = Mesh::lattice(64, 4, [2., 0.125], 0.15).unwrap();
        let baseline = shock_pattern::mesh(64, 0.15, 0.125, 1).unwrap();
        assert_eq!(format!("{original:?}"), format!("{baseline:?}"));
        let compressed = shock_pattern::mesh(64, 0.15, 0.03125, 1).unwrap();
        for (a, b) in original.generators.iter().zip(&compressed.generators) {
            assert_eq!(a[0], b[0]);
            assert_eq!(a[1] * 0.25, b[1]);
        }
        assert!(shock_pattern::mesh(64, 0.15, f64::NAN, 1).is_err());
        assert!(shock_pattern::mesh(64, 0.15, 0.125, 0).is_err());
    }
}
