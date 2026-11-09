//! Geometry control only; does not change the registered Brio benchmark or gates.
use mhd_vector_pot::{
    benchmarks::brio_initial,
    general::{Config, Motion, Profile, Simulation},
};
use moving_mesh::Mesh;
use std::{fs, io::Write, path::Path, time::Instant};

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
    if args.len() != 5 {
        return Err("usage: paper-shock-geometry NX NY JITTER TIME NEW_DIRECTORY".into());
    }
    let nx: usize = args[0].parse()?;
    let ny: usize = args[1].parse()?;
    let jitter: f64 = args[2].parse()?;
    let time: f64 = args[3].parse()?;
    if nx > 256 || ny > 16 || !(0. < time && time <= 0.04) {
        return Err("geometry probe bounds exceeded".into());
    }
    let path = Path::new(&args[4]);
    fs::create_dir(path)?;
    let start = Instant::now();
    let mut sim = Simulation::new(
        Mesh::lattice(nx, ny, [2., 0.125], jitter)?,
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
            "nx={nx}\nny={ny}\njitter={jitter}\nrequested_time={time}\ncompleted={}\ntime={:.17e}\nseconds={:.6}\nrejected_state={}\nrejected_geometry={}\n",
            result.is_ok(),
            sim.time(),
            start.elapsed().as_secs_f64(),
            sim.counters().rejected_state,
            sim.counters().rejected_geometry
        ),
    )?;
    result.map_err(Into::into)
}
