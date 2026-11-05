//! Run the paper-global-v2 2.5D operator/coupling packet (not the full M1 matrix).
use mhd_vector_pot::benchmarks::{alfven_initial, loop_amplitude, loop_initial};
use mhd_vector_pot::diagnostics::{Diagnostics, Divergence, Norms};
use mhd_vector_pot::general::{Config, Initial, Motion, Profile, Simulation};
use moving_mesh::Mesh;
use std::{f64::consts::TAU, fmt::Write as _, fs, path::PathBuf};

fn norms(n: Norms) -> String {
    format!(
        "{{\"mean\":{:.17e},\"rms\":{:.17e},\"max\":{:.17e}}}",
        n.mean, n.rms, n.max
    )
}
fn array<const N: usize>(a: [f64; N]) -> String {
    format!(
        "[{}]",
        a.iter()
            .map(|x| format!("{x:.17e}"))
            .collect::<Vec<_>>()
            .join(",")
    )
}
fn divergence(d: &Divergence) -> String {
    format!(
        "{{\"dimensional\":{},\"dimensionless\":{}}}",
        norms(d.dimensional),
        norms(d.dimensionless)
    )
}
fn diagnostic(d: &Diagnostics) -> String {
    format!(
        "{{\"neighbour_condition\":{:.17e},\"face_condition\":{:.17e},\"totals\":{},\"normalized_budget\":{},\"budget_scales\":{},\"rho_min\":{:.17e},\"rho_max\":{:.17e},\"p_min\":{:.17e},\"p_max\":{:.17e},\"magnetic_energy\":{:.17e},\"mean_B\":{},\"mean_B_drift\":{},\"div_B_ls\":{},\"div_B_face\":{},\"div_B_limited\":{},\"div_A\":{},\"phi\":{}}}",
        d.neighbour_condition,
        d.face_condition,
        array(d.totals),
        array(d.normalized_budget),
        array(d.budget_scales),
        d.min_density,
        d.max_density,
        d.min_pressure,
        d.max_pressure,
        d.magnetic_energy,
        array(d.mean_magnetic),
        array(d.mean_magnetic_drift),
        divergence(&d.divergence_ls),
        divergence(&d.divergence_face),
        divergence(&d.divergence_limited_face),
        norms(d.divergence_a),
        norms(d.phi)
    )
}
fn snapshot(sim: &Simulation) -> Result<String, String> {
    let mut csv = String::from(
        "id,time,x,y,volume,rho,p,vx,vy,vz,bx,by,bz,ax,ay,az,phi,energy,div_a,div_b_ls,div_b_face,div_b_limited,reduced_ax,reduced_ay,reduced_az\n",
    );
    let state = sim.state();
    let total_potential = sim.total_potential();
    let q = sim.primitives()?;
    let fit = sim.magnetic_fit()?;
    let d = sim.diagnostics()?;
    for (i, c) in state.mesh.cells.iter().enumerate() {
        write!(&mut csv, "{i}").map_err(|e| e.to_string())?;
        let values = [
            sim.time(),
            c.centroid[0].rem_euclid(state.mesh.lengths[0]),
            c.centroid[1].rem_euclid(state.mesh.lengths[1]),
            c.volume,
            q[i].density,
            q[i].pressure,
            q[i].velocity[0],
            q[i].velocity[1],
            q[i].velocity[2],
            q[i].magnetic[0],
            q[i].magnetic[1],
            q[i].magnetic[2],
            total_potential[i][0],
            total_potential[i][1],
            total_potential[i][2],
            state.phi[i],
            state.conserved[i][4] / c.volume,
            fit.divergence_a[i],
            d.divergence_ls.values[i],
            d.divergence_face.values[i],
            d.divergence_limited_face.values[i],
            state.potential[i][0],
            state.potential[i][1],
            state.potential[i][2],
        ];
        for value in values {
            write!(&mut csv, ",{value:.17e}").map_err(|e| e.to_string())?;
        }
        csv.push('\n');
    }
    Ok(csv)
}
fn run() -> Result<(), String> {
    let mut case = String::from("smooth");
    let mut profile = Profile::PaperGlobalV2;
    let mut parallel_velocity: f64 = 0.;
    let mut n = 8usize;
    let mut jitter = 0.;
    let mut time = 0.02;
    let mut max_dt = f64::INFINITY;
    let mut checkpoints: Vec<f64> = Vec::new();
    let mut boost = [0.; 3];
    let mut mean_override = [None; 3];
    let mut mesh_velocity = [0.; 2];
    let mut motion = String::from("fixed");
    let mut limited = true;
    let mut output = PathBuf::from("results/vector_potential_single");
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == "--help" {
            println!(
                "vector-potential --profile paper-global-v2|bulk-frame-v1|bulk-frame-hll-v1 --case uniform|curl|gauge|smooth|deform|alfven|loop --n N --jitter J --time T --dt DT --checkpoint T (repeatable)\n  --motion fixed|rigid|fluid|prescribed --mesh-x WX --mesh-y WY\n  --boost-x VX --boost-y VY --boost-z VZ --mean-bx BX --mean-by BY --mean-bz BZ --parallel-velocity V --unlimited --output DIR\nOutputs initial.csv, final.csv and summary.json; f64, periodic unit square, mu0=1, gamma=5/3."
            );
            return Ok(());
        }
        if arg == "--unlimited" {
            limited = false;
            continue;
        }
        let value = args
            .next()
            .ok_or_else(|| format!("missing value for {arg}"))?;
        let number = || {
            value
                .parse::<f64>()
                .map_err(|_| format!("invalid number for {arg}"))
        };
        match arg.as_str() {
            "--case" => case = value,
            "--profile" => {
                profile = match value.as_str() {
                    "paper-global-v2" => Profile::PaperGlobalV2,
                    "bulk-frame-v1" => Profile::BulkFrameV1,
                    "bulk-frame-hll-v1" => Profile::BulkFrameHllV1,
                    _ => return Err("unknown profile".into()),
                }
            }
            "--parallel-velocity" => parallel_velocity = number()?,
            "--n" => n = value.parse().map_err(|_| "invalid n")?,
            "--jitter" => jitter = number()?,
            "--time" => time = number()?,
            "--checkpoint" => checkpoints.push(number()?),
            "--dt" => max_dt = number()?,
            "--motion" => motion = value,
            "--mesh-x" => mesh_velocity[0] = number()?,
            "--mesh-y" => mesh_velocity[1] = number()?,
            "--boost-x" => boost[0] = number()?,
            "--boost-y" => boost[1] = number()?,
            "--boost-z" => boost[2] = number()?,
            "--mean-bx" => mean_override[0] = Some(number()?),
            "--mean-by" => mean_override[1] = Some(number()?),
            "--mean-bz" => mean_override[2] = Some(number()?),
            "--output" => output = PathBuf::from(value),
            _ => return Err(format!("unknown argument {arg}")),
        }
    }
    if ![
        "uniform", "curl", "gauge", "smooth", "deform", "alfven", "loop",
    ]
    .contains(&case.as_str())
    {
        return Err("unknown case".into());
    }
    if !parallel_velocity.is_finite()
        || !time.is_finite()
        || time < 0.
        || checkpoints
            .iter()
            .any(|t| !t.is_finite() || *t <= 0. || *t > time)
        || !boost.iter().chain(&mesh_velocity).all(|x| x.is_finite())
    {
        return Err("nonfinite/negative run parameter".into());
    }
    let mesh = Mesh::lattice(n, n, [1.; 2], jitter)?;
    let generator_motion = match motion.as_str() {
        "fixed" => Motion::Fixed,
        "rigid" => Motion::Rigid(mesh_velocity),
        "fluid" => Motion::Fluid,
        "prescribed" => Motion::Prescribed(
            mesh.generators
                .iter()
                .map(|x| [0.1 * (TAU * x[1]).sin(), 0.1 * (TAU * x[0]).cos()])
                .collect(),
        ),
        _ => return Err("unknown motion".into()),
    };
    let mut mean = if case == "uniform" || case == "deform" {
        [0.3, 0.2, 0.1]
    } else if case == "alfven" {
        [1., 0., 0.]
    } else {
        [0.; 3]
    };
    for (b, override_value) in mean.iter_mut().zip(mean_override) {
        if let Some(value) = override_value {
            *b = value;
        }
    }
    let config = Config {
        profile,
        motion: generator_motion,
        mean_magnetic: mean,
        max_dt,
        limited,
        magnetic_scale: match case.as_str() {
            "alfven" => 1.,
            "loop" => loop_amplitude(),
            _ => {
                if mean == [0.; 3] {
                    0.001 * TAU
                } else {
                    0.3
                }
            }
        },
        ..Config::default()
    };
    let mut sim = Simulation::new(mesh, config, |position| {
        if case == "alfven" {
            return alfven_initial(position, parallel_velocity, boost);
        }
        if case == "loop" {
            return loop_initial(position, boost);
        }
        let (x, y) = (TAU * position[0], TAU * position[1]);
        let mut q = Initial {
            density: 1.,
            pressure: 1.,
            velocity: [0.; 3],
            potential: [0.; 3],
            phi: 0.,
        };
        match case.as_str() {
            "uniform" => {
                q.velocity = [0.4, -0.2, 0.3];
                q.potential = [0.1, -0.05, 0.03];
            }
            "gauge" => {
                q.pressure = 0.6;
                q.potential = [0.001 * x.cos(), 0., 0.];
            }
            "deform" => q.pressure = 0.01,
            _ => {
                q.velocity = [
                    0.2 + 0.05 * y.sin(),
                    -0.1 + 0.03 * x.cos(),
                    0.04 * (x + y).sin(),
                ];
                q.potential = [0.001 * y.sin(), 0.001 * x.cos(), 0.001 * x.sin() * y.sin()];
            }
        }
        for (v, b) in q.velocity.iter_mut().zip(boost) {
            *v += b;
        }
        q
    })?;
    fs::create_dir_all(&output).map_err(|e| e.to_string())?;
    fs::write(output.join("initial.csv"), snapshot(&sim)?).map_err(|e| e.to_string())?;
    let initial = diagnostic(&sim.diagnostics()?);
    checkpoints.push(time);
    checkpoints.sort_by(f64::total_cmp);
    checkpoints.dedup();
    let mut history = vec![format!("{{\"time\":0,\"diagnostics\":{initial}}}")];
    let mut failure = None;
    for target in checkpoints {
        failure = sim.advance_to(target).err();
        history.push(format!(
            "{{\"time\":{:.17e},\"diagnostics\":{}}}",
            sim.time(),
            diagnostic(&sim.diagnostics()?)
        ));
        if failure.is_some() {
            break;
        }
        if target != time {
            fs::write(
                output.join(format!("checkpoint_{target:.8}.csv")),
                snapshot(&sim)?,
            )
            .map_err(|e| e.to_string())?;
        }
    }
    fs::write(
        output.join("history.json"),
        format!("[{}]\n", history.join(",")),
    )
    .map_err(|e| e.to_string())?;
    if let Some(error) = &failure {
        fs::write(output.join("failure.txt"), error).map_err(|e| e.to_string())?;
    }
    let completed = failure.is_none();
    fs::write(output.join("final.csv"), snapshot(&sim)?).map_err(|e| e.to_string())?;
    let c = sim.counters();
    let summary = format!(
        "{{\n\"completed\":{completed},\"requested_time\":{time},\"profile\":\"{}\",\"gauge_reference_velocity\":{},\"gauge_offset\":{},\"case\":\"{case}\",\"n\":{n},\"jitter\":{jitter},\"parallel_velocity\":{parallel_velocity},\"time\":{:.17e},\"dt_cap\":{},\"limited\":{limited},\"motion\":\"{motion}\",\"boost\":{},\"mesh_velocity\":{},\"gamma\":{},\"mean_B\":{},\"Bscale\":{},\n\"geometric_conservation_max\":{:.17e},\"steps\":{},\"dt_min\":{},\"dt_max\":{:.17e},\"rejected_geometry\":{},\"rejected_state\":{},\"rejected_cfl\":{},\"hll_fallbacks\":{},\"hll_fallbacks_attempted\":{},\"auxiliary_coarsenings\":{},\"auxiliary_roots\":{:?},\"auxiliary_origin\":{},\n\"initial\":{},\n\"final\":{}\n}}\n",
        sim.config().profile.name(),
        array(sim.reference_velocity()),
        array(sim.state().gauge_offset),
        sim.time(),
        if max_dt.is_finite() {
            format!("{max_dt:.17e}")
        } else {
            "null".into()
        },
        array(boost),
        array(mesh_velocity),
        sim.config().gamma,
        array(mean),
        sim.config().magnetic_scale,
        c.geometric_conservation_max,
        c.steps,
        c.min_dt.map_or("null".into(), |d| format!("{d:.17e}")),
        c.max_dt,
        c.rejected_geometry,
        c.rejected_state,
        c.rejected_cfl,
        c.hll_fallbacks,
        c.hll_fallbacks_attempted,
        c.auxiliary_coarsenings,
        c.auxiliary_roots,
        array(sim.state().auxiliary_origin),
        initial,
        diagnostic(&sim.diagnostics()?)
    );
    fs::write(output.join("summary.json"), summary).map_err(|e| e.to_string())?;
    println!(
        "{case}: t={:.6}, {} steps; {}",
        sim.time(),
        c.steps,
        output.display()
    );
    if let Some(error) = failure {
        return Err(error);
    }
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("error: {error}");
        std::process::exit(1);
    }
}
