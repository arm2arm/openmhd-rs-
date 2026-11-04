use mhd_planar::{Case, Config, Simulation};
use std::{
    env,
    fs::File,
    io::{BufWriter, Write},
    path::PathBuf,
};

fn run() -> Result<(), String> {
    let mut config = Config::default();
    let mut end_time = 0.1;
    let mut output: Option<PathBuf> = None;
    let mut ny_explicit = false;
    let mut args = env::args().skip(1);
    while let Some(flag) = args.next() {
        if flag == "--help" {
            println!(
                "openmhd --case orszag-tang|brio-wu|uniform|smooth --nx N --ny N --time T\n  --jitter [0,0.25] --cfl (0,0.4] --boost-x V --boost-y V\n  --mesh-vx V --mesh-vy V --first-order --output cells.csv\nExperimental planar MHD; fixed or rigidly translating periodic Voronoi mesh."
            );
            return Ok(());
        }
        if flag == "--first-order" {
            config.second_order_space = false;
            continue;
        }
        let value = args
            .next()
            .ok_or_else(|| format!("missing value for {flag}"))?;
        match flag.as_str() {
            "--case" => {
                config.case = match value.as_str() {
                    "orszag-tang" => Case::OrszagTang,
                    "brio-wu" => Case::BrioWu,
                    "uniform" => Case::Uniform,
                    "smooth" => Case::Smooth,
                    "magnetic-pressure" => Case::MagneticPressure,
                    _ => return Err(format!("unknown case: {value}")),
                }
            }
            "--nx" => config.nx = value.parse().map_err(|_| "invalid nx")?,
            "--ny" => {
                config.ny = value.parse().map_err(|_| "invalid ny")?;
                ny_explicit = true;
            }
            "--time" => end_time = value.parse().map_err(|_| "invalid time")?,
            "--cfl" => config.cfl = value.parse().map_err(|_| "invalid cfl")?,
            "--jitter" => config.jitter = value.parse().map_err(|_| "invalid jitter")?,
            "--boost-x" => config.boost[0] = value.parse().map_err(|_| "invalid boost-x")?,
            "--boost-y" => config.boost[1] = value.parse().map_err(|_| "invalid boost-y")?,
            "--mesh-vx" => {
                config.mesh_velocity[0] = value.parse().map_err(|_| "invalid mesh-vx")?
            }
            "--mesh-vy" => {
                config.mesh_velocity[1] = value.parse().map_err(|_| "invalid mesh-vy")?
            }
            "--output" => output = Some(value.into()),
            _ => return Err(format!("unknown flag: {flag}")),
        }
    }
    if !ny_explicit {
        config.ny = if config.case == Case::BrioWu {
            4
        } else {
            config.nx
        };
    }
    let mut sim = Simulation::new(config)?;
    let initial = sim.diagnostics()?;
    sim.advance_to(end_time)?;
    let d = sim.diagnostics()?;
    if let Some(path) = output {
        let mut writer = BufWriter::new(File::create(path).map_err(|e| e.to_string())?);
        writeln!(writer, "id,x,y,volume,az,rho,vx,vy,p,bx,by").map_err(|e| e.to_string())?;
        for (i, q) in sim.primitives()?.iter().enumerate() {
            let x = sim.position(i);
            writeln!(writer,"{i},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
                x[0],x[1],sim.mesh.cells[i].volume,sim.az[i],q.density,q.velocity[0],q.velocity[1],
                q.pressure,q.magnetic[0],q.magnetic[1]).map_err(|e| e.to_string())?;
        }
        writer.flush().map_err(|e| e.to_string())?;
    }
    println!(
        "case,nx,ny,jitter,time,steps,rejected_steps,hll_fallbacks,mass,px,py,pz,energy,budget_error,min_rho,min_p,magnetic_energy,mean_bx,mean_by,div_ls_rms,div_face_rms,div_face_max,smooth_l1,stencil_condition,div_limited_rms,initial_mean_bx,initial_mean_by,mean_b_drift,cfl_rejections,invalid_rejections"
    );
    println!(
        "{},{},{},{:.17e},{:.17e},{},{},{},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{},{}",
        sim.config.case.name(),
        sim.config.nx,
        sim.config.ny,
        sim.config.jitter,
        sim.time,
        sim.steps,
        sim.rejected_steps,
        sim.hll_fallbacks,
        d.totals[0],
        d.totals[1],
        d.totals[2],
        d.totals[3],
        d.totals[4],
        d.relative_budget_error,
        d.min_density,
        d.min_pressure,
        d.magnetic_energy,
        d.mean_b[0],
        d.mean_b[1],
        d.div_ls_rms,
        d.div_face_rms,
        d.div_face_max,
        d.smooth_l1,
        moving_mesh::Derivatives::build(&sim.mesh, false)?.worst_condition,
        d.div_limited_rms,
        initial.mean_b[0],
        initial.mean_b[1],
        ((d.mean_b[0] - initial.mean_b[0]).powi(2) + (d.mean_b[1] - initial.mean_b[1]).powi(2))
            .sqrt(),
        sim.cfl_rejections,
        sim.invalid_rejections
    );
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("openmhd: {e}");
        std::process::exit(1);
    }
}
