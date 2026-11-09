//! Bounded, separately named CT experiment; see docs/M1_CT_COMPARATOR.md.
use mhd_core::Primitive;
use mhd_vector_pot::{
    benchmarks,
    ct::{Config, Diagnostics, PROFILE, Simulation},
};
use moving_mesh::Mesh;
use std::{
    fs::{self, File},
    io::{BufWriter, Write},
    path::Path,
    time::Instant,
};

fn snapshot(sim: &Simulation, path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let mut f = BufWriter::new(File::create(path)?);
    writeln!(f, "id,x,y,volume,rho,vx,vy,vz,p,bx,by,bz,energy")?;
    for (i, q) in sim.recover(&sim.state)?.iter().enumerate() {
        let c = &sim.mesh.cells[i];
        let x: [f64; 2] = std::array::from_fn(|k| {
            (c.centroid[k] + sim.config.mesh_velocity[k] * sim.time).rem_euclid(sim.mesh.lengths[k])
        });
        writeln!(
            f,
            "{i},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
            x[0],
            x[1],
            c.volume,
            q.density,
            q.velocity[0],
            q.velocity[1],
            q.velocity[2],
            q.pressure,
            q.magnetic[0],
            q.magnetic[1],
            q.magnetic[2],
            sim.state.fluid[i][4] / c.volume
        )?;
    }
    Ok(())
}
fn trace(f: &mut impl Write, sim: &Simulation, d: &Diagnostics) -> std::io::Result<()> {
    writeln!(
        f,
        "{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
        sim.time,
        d.min_density,
        d.min_pressure,
        d.budget_max,
        d.magnetic_energy,
        d.div_ct_max,
        d.div_ct_rms,
        d.div_ls_rms,
        d.div_face_rms
    )?;
    f.flush()
}
fn run() -> Result<bool, Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.iter().any(|s| s == "--help") {
        println!(
            "ct-comparator --case brio-wu|alfven --n N --jitter J --parallel V --time T --dt DT --boost-x X --boost-y Y --output DIR"
        );
        return Ok(true);
    }
    if args.len() % 2 != 0 {
        return Err("arguments require flag/value pairs".into());
    }
    let allowed = [
        "--case",
        "--n",
        "--jitter",
        "--parallel",
        "--time",
        "--dt",
        "--boost-x",
        "--boost-y",
        "--output",
    ];
    for pair in args.chunks_exact(2) {
        if !allowed.contains(&pair[0].as_str()) {
            return Err(format!("unknown flag {}", pair[0]).into());
        }
    }
    let arg = |key: &str, default: &str| {
        args.chunks_exact(2)
            .find(|p| p[0] == key)
            .map_or_else(|| default.to_string(), |p| p[1].clone())
    };
    let case = arg("--case", "brio-wu");
    let n: usize = arg("--n", "256").parse()?;
    let jitter: f64 = arg("--jitter", "0.15").parse()?;
    let parallel: f64 = arg("--parallel", "0").parse()?;
    let target: f64 = arg("--time", "0.02").parse()?;
    let max_dt: f64 = arg("--dt", "inf").parse()?;
    let boost = [
        arg("--boost-x", "0").parse()?,
        arg("--boost-y", "0").parse()?,
        0.,
    ];
    if !target.is_finite() || target < 0. || !parallel.is_finite() {
        return Err("invalid time or parallel velocity".into());
    }
    let output = arg("--output", "results/ct_comparator");
    let output = Path::new(&output);
    fs::create_dir_all(output)?;
    let (lengths, ny, gamma, mean) = match case.as_str() {
        "brio-wu" => ([2., 0.125], 4, 2., [0.75, 0.]),
        "alfven" => ([1., 1.], n, 5. / 3., [1., 0.]),
        _ => return Err("unknown CT case".into()),
    };
    let start = Instant::now();
    let mut sim = Simulation::new(
        Mesh::lattice(n, ny, lengths, jitter)?,
        Config {
            gamma,
            mean_xy: mean,
            mesh_velocity: [boost[0], boost[1]],
            max_dt,
            ..Config::default()
        },
        |x| {
            if case == "alfven" {
                (
                    benchmarks::alfven_initial(x, parallel, boost).potential[2],
                    benchmarks::alfven_exact(x, 0., parallel, boost),
                )
            } else {
                let init = benchmarks::brio_initial(x, boost);
                (
                    init.potential[2],
                    Primitive {
                        density: init.density,
                        pressure: init.pressure,
                        velocity: boost,
                        magnetic: [0.75, if x[0] < 1. { 1. } else { -1. }, 0.],
                    },
                )
            }
        },
    )?;
    snapshot(&sim, &output.join("initial.csv"))?;
    let mut rates = BufWriter::new(File::create(output.join("initial_energy_rates.csv"))?);
    writeln!(rates, "id,dE,dK,dM,dp")?;
    for (i, r) in sim.energy_rates()?.iter().enumerate() {
        writeln!(
            rates,
            "{i},{:.17e},{:.17e},{:.17e},{:.17e}",
            r[0], r[1], r[2], r[3]
        )?;
    }
    rates.flush()?;
    let mut history = BufWriter::new(File::create(output.join("accepted_diagnostics.csv"))?);
    writeln!(
        history,
        "time,min_density,min_pressure,budget_max,magnetic_energy,div_ct_max,div_ct_rms,div_ls_rms,div_face_rms"
    )?;
    trace(&mut history, &sim, &sim.diagnostics()?)?;
    let mut error = None;
    while sim.time < target {
        if let Err(e) = sim.step(target) {
            error = Some(e);
            break;
        }
        trace(&mut history, &sim, &sim.diagnostics()?)?;
    }
    snapshot(&sim, &output.join("final.csv"))?;
    let d = sim.diagnostics()?;
    let status = if error.is_some() {
        "failed"
    } else {
        "completed"
    };
    let error_json = error
        .as_ref()
        .map_or("null".to_string(), |e| format!("{e:?}"));
    let dt_json = if max_dt.is_finite() {
        max_dt.to_string()
    } else {
        "null".into()
    };
    fs::write(
        output.join("summary.json"),
        format!(
            "{{\n  \"profile\":{PROFILE:?},\"case\":{case:?},\"n\":{n},\"ny\":{ny},\"jitter\":{jitter},\"parallel\":{parallel},\"boost\":{:?},\"max_dt\":{dt_json},\n  \"status\":{status:?},\"error\":{error_json},\"target\":{target},\"time\":{:.17e},\"steps\":{},\"rejections\":{},\n  \"hll_fallbacks\":{},\"hll_fallbacks_attempted\":{},\"wall_seconds\":{},\n  \"min_pressure_final\":{},\"budget_final\":{},\"div_ct_max_final\":{},\"full_m1_accepted\":false\n}}\n",
            boost,
            sim.time,
            sim.steps,
            sim.rejections,
            sim.hll_fallbacks,
            sim.hll_fallbacks_attempted,
            start.elapsed().as_secs_f64(),
            d.min_pressure,
            d.budget_max,
            d.div_ct_max
        ),
    )?;
    println!(
        "{PROFILE} {case} n={n} jitter={jitter}: {status} at {:.9}, {:.3}s",
        sim.time,
        start.elapsed().as_secs_f64()
    );
    if let Some(e) = error {
        eprintln!("{e}");
    }
    Ok(status == "completed")
}
fn main() {
    match run() {
        Ok(true) => (),
        Ok(false) => std::process::exit(1),
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(2);
        }
    }
}
