//! Run the paper-global-v2 2.5D operator/coupling packet (not the full M1 matrix).
use mhd_vector_pot::benchmarks::{
    alfven_initial, brio_initial, loop_amplitude, loop_initial, vortex_initial,
};
use mhd_vector_pot::diagnostics::{Diagnostics, Divergence, Norms};
use mhd_vector_pot::general::{Config, Initial, Motion, Profile, Simulation, StepControl};
use moving_mesh::Mesh;
use std::{f64::consts::TAU, fmt::Write as _, fs, path::PathBuf};
#[path = "vector-potential/restart.rs"]
mod restart;

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
fn polygons(mesh: &Mesh) -> Result<String, String> {
    let mut csv = String::from("id,vertex,x,y\n");
    for i in 0..mesh.cells.len() {
        for (j, point) in mesh.polygon(i)?.iter().enumerate() {
            writeln!(&mut csv, "{i},{j},{:.17e},{:.17e}", point[0], point[1])
                .map_err(|e| e.to_string())?;
        }
    }
    Ok(csv)
}
fn run() -> Result<(), String> {
    let options = restart::Options::parse()?;
    let loaded = options
        .resume
        .as_ref()
        .map(|path| Simulation::read_checkpoint(path))
        .transpose()?;
    let mut context = loaded
        .as_ref()
        .map(|(sim, data)| restart::Context::decode(data, sim))
        .transpose()?;
    let original_arguments = context
        .as_ref()
        .map_or_else(|| options.physical.clone(), |c| c.arguments.clone());
    let mut mesh_cache: Option<PathBuf> = None;
    let mut mesh_only = false;
    let mut case = String::from("smooth");
    let mut profile = Profile::PaperGlobalV2;
    let mut parallel_velocity: f64 = 0.;
    let mut n = 8usize;
    let mut nx = None;
    let mut ny = None;
    let mut jitter = 0.;
    let mut time = 0.02;
    let mut max_dt = f64::INFINITY;
    let mut checkpoints: Vec<f64> = Vec::new();
    let mut boost = [0.; 3];
    let mut mean_override = [None; 3];
    let mut mesh_velocity = [0.; 2];
    let mut motion = String::from("fixed");
    let mut limited = true;
    let mut output = options.output.clone().unwrap_or_else(|| {
        options
            .resume
            .as_ref()
            .and_then(|p| p.parent())
            .map(|p| {
                if p.as_os_str().is_empty() {
                    std::path::Path::new(".")
                } else {
                    p
                }
            })
            .map_or_else(
                || PathBuf::from("results/vector_potential_single"),
                PathBuf::from,
            )
    });
    let mut args = original_arguments.clone().into_iter();
    while let Some(arg) = args.next() {
        if arg == "--help" {
            println!(
                "vector-potential --profile paper-global-v2|bulk-frame-v1|bulk-frame-hll-v1|bulk-frame-hll-quadratic-v1|bulk-frame-hll-consistent-v1|bulk-frame-hll-matched-v1|bulk-frame-hll-compact-v1|bulk-frame-hll-projected-v1 --case uniform|curl|gauge|smooth|deform|alfven|loop|brio|vortex --n N --nx NX --ny NY --mesh-cache FILE --mesh-only --jitter J --time T --dt DT --checkpoint T (repeatable)\n  --motion fixed|rigid|fluid|prescribed --mesh-x WX --mesh-y WY\n  --boost-x VX --boost-y VY --boost-z VZ --mean-bx BX --mean-by BY --mean-bz BZ --parallel-velocity V --unlimited --output DIR\nOutputs initial.csv, final.csv and summary.json; f64, mu0=1, periodic; Brio box 2 x .125 and gamma=2, otherwise unit square and gamma=5/3."
            );
            println!(
                "Restart: --checkpoint-steps N [--restart-out FILE] writes full accepted-step state (default DIR/restart.chk).\n  --resume FILE [--output DIR] resumes the saved configuration and target schedule.\n  --stop-after-steps N saves and stops cleanly at accepted step N (requires checkpointing).\n  --checkpoint T remains an analysis CSV time; it is not a restart file."
            );
            return Ok(());
        }
        if arg == "--mesh-only" {
            mesh_only = true;
            continue;
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
            "--mesh-cache" => mesh_cache = Some(PathBuf::from(value)),
            "--case" => case = value,
            "--profile" => {
                profile = match value.as_str() {
                    "paper-global-v2" => Profile::PaperGlobalV2,
                    "bulk-frame-v1" => Profile::BulkFrameV1,
                    "bulk-frame-hll-v1" => Profile::BulkFrameHllV1,
                    "bulk-frame-hll-quadratic-v1" => Profile::BulkFrameHllQuadraticV1,
                    "bulk-frame-hll-consistent-v1" => Profile::BulkFrameHllConsistentV1,
                    "bulk-frame-hll-matched-v1" => Profile::BulkFrameHllMatchedV1,
                    "bulk-frame-hll-compact-v1" => Profile::BulkFrameHllCompactV1,
                    "bulk-frame-hll-projected-v1" => Profile::BulkFrameHllProjectedV1,
                    _ => return Err("unknown profile".into()),
                }
            }
            "--parallel-velocity" => parallel_velocity = number()?,
            "--n" => n = value.parse().map_err(|_| "invalid n")?,
            "--nx" => nx = Some(value.parse::<usize>().map_err(|_| "invalid nx")?),
            "--ny" => ny = Some(value.parse::<usize>().map_err(|_| "invalid ny")?),
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
        "uniform", "curl", "gauge", "smooth", "deform", "alfven", "loop", "brio", "vortex",
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
    let (nx, ny) = (nx.unwrap_or(n), ny.unwrap_or(n));
    checkpoints.sort_by(f64::total_cmp);
    checkpoints.dedup();
    let mut output_names = std::collections::BTreeSet::new();
    for &target in &checkpoints {
        if target != time && !output_names.insert(format!("checkpoint_{target:.8}.csv")) {
            return Err("analysis checkpoint times collide at the eight-decimal output filename precision; choose separated times".into());
        }
    }
    let lengths = if case == "brio" { [2., 0.125] } else { [1.; 2] };
    let mut sim = if let Some((sim, _)) = loaded {
        sim
    } else {
        let mesh = if let Some(path) = &mesh_cache {
            if path.exists() {
                Mesh::decode_lattice(
                    &fs::read_to_string(path).map_err(|e| e.to_string())?,
                    nx,
                    ny,
                    lengths,
                    jitter,
                )?
            } else {
                let m = Mesh::lattice(nx, ny, lengths, jitter)?;
                let temporary = path.with_extension(format!("tmp-{}", std::process::id()));
                fs::write(&temporary, m.encode()?).map_err(|e| e.to_string())?;
                fs::rename(&temporary, path).map_err(|e| e.to_string())?;
                m
            }
        } else {
            Mesh::lattice(nx, ny, lengths, jitter)?
        };
        if mesh_only {
            if mesh_cache.is_none() {
                return Err("--mesh-only requires --mesh-cache".into());
            }
            return Ok(());
        }
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
        } else if case == "brio" {
            [0.75, 0., 0.]
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
            gamma: if case == "brio" { 2. } else { 5. / 3. },
            profile,
            motion: generator_motion,
            mean_magnetic: mean,
            max_dt,
            limited,
            magnetic_scale: match case.as_str() {
                "alfven" | "brio" => 1.,
                "vortex" => 1. / (4. * std::f64::consts::PI).sqrt(),
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
        Simulation::new(mesh, config, |position| {
            if case == "brio" {
                return brio_initial(position, boost);
            }
            if case == "vortex" {
                return vortex_initial(position, boost);
            }
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
        })?
    };
    let max_dt = sim.config().max_dt;
    let mean = sim.config().mean_magnetic;
    let limited = sim.config().limited;
    if context
        .as_ref()
        .is_some_and(|c| c.final_time.to_bits() != time.to_bits())
    {
        return Err("restart driver final target mismatch".into());
    }
    let every = options
        .every
        .unwrap_or_else(|| context.as_ref().map_or(0, |c| c.every));
    let enabled = every > 0 || options.destination.is_some() || options.resume.is_some();
    if options.stop_after.is_some() && !enabled {
        return Err("--stop-after-steps requires --checkpoint-steps or --restart-out".into());
    }
    if options
        .stop_after
        .is_some_and(|n| n <= sim.counters().steps)
    {
        return Err("--stop-after-steps must exceed the restored accepted-step count".into());
    }
    let restart_path = options
        .destination
        .clone()
        .unwrap_or_else(|| output.join("restart.chk"));
    fs::create_dir_all(&output).map_err(|e| e.to_string())?;
    if enabled {
        for file in std::iter::once(&restart_path).chain(options.resume.iter()) {
            let parent = file
                .parent()
                .filter(|p| !p.as_os_str().is_empty())
                .unwrap_or(std::path::Path::new("."));
            fs::create_dir_all(parent).map_err(|e| e.to_string())?;
            let name = file
                .file_name()
                .and_then(|s| s.to_str())
                .ok_or("restart path needs a filename")?;
            if fs::canonicalize(parent).map_err(|e| e.to_string())?
                == fs::canonicalize(&output).map_err(|e| e.to_string())?
                && ([
                    "initial.csv",
                    "final.csv",
                    "summary.json",
                    "history.json",
                    "polygons.csv",
                    "failure.txt",
                ]
                .contains(&name)
                    || (name.starts_with("checkpoint_") && name.ends_with(".csv")))
            {
                return Err(
                    "restart destination conflicts with an analysis output filename".into(),
                );
            }
        }
    }
    let mut context = if let Some(c) = context.take() {
        c
    } else {
        let initial = diagnostic(&sim.diagnostics()?);
        checkpoints.push(time);
        checkpoints.sort_by(f64::total_cmp);
        checkpoints.dedup();
        restart::Context {
            arguments: original_arguments,
            every,
            final_time: time,
            pending: checkpoints,
            history: vec![format!("{{\"time\":0,\"diagnostics\":{initial}}}")],
            initial,
            outputs: vec![("initial.csv".into(), snapshot(&sim)?)],
        }
    };
    context.every = every;
    context.restore_outputs(&output)?;
    if enabled {
        sim.write_checkpoint(&restart_path, &context.encode())?;
    }
    // Do not leave a previous completion/failure marker beside an active restart.
    for name in ["final.csv", "summary.json", "polygons.csv", "failure.txt"] {
        match fs::remove_file(output.join(name)) {
            Ok(()) => {}
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
            Err(e) => return Err(e.to_string()),
        }
    }
    let mut failure = None;
    while let Some(&target) = context.pending.first() {
        let metadata = if enabled {
            context.encode()
        } else {
            Vec::new()
        };
        let outcome = sim.advance_with_observer(target, |accepted| {
            let stop = options
                .stop_after
                .is_some_and(|n| accepted.counters().steps >= n);
            if enabled && (stop || (every > 0 && accepted.counters().steps % every == 0)) {
                accepted.write_checkpoint(&restart_path, &metadata)?;
                println!(
                    "restart saved: step={}, t={:.17e}, {}",
                    accepted.counters().steps,
                    accepted.time(),
                    restart_path.display()
                );
            }
            Ok(if stop {
                StepControl::Stop
            } else {
                StepControl::Continue
            })
        });
        if matches!(outcome, Ok(false)) {
            println!(
                "stopped after accepted step {}; resume with --resume {}",
                sim.counters().steps,
                restart_path.display()
            );
            return Ok(());
        }
        failure = outcome.err();
        println!(
            "{case}: checkpoint t={:.8}, accepted steps={}, status={}",
            sim.time(),
            sim.counters().steps,
            if failure.is_none() { "ok" } else { "failed" }
        );
        context.history.push(format!(
            "{{\"time\":{:.17e},\"diagnostics\":{}}}",
            sim.time(),
            diagnostic(&sim.diagnostics()?)
        ));
        if failure.is_some() {
            break;
        }
        if target != time {
            let name = format!("checkpoint_{target:.8}.csv");
            let data = snapshot(&sim)?;
            fs::write(output.join(&name), &data).map_err(|e| e.to_string())?;
            context.outputs.push((name, data));
        }
        context.pending.remove(0);
        context.write_history(&output)?;
        if enabled {
            sim.write_checkpoint(&restart_path, &context.encode())?;
        }
    }
    context.write_history(&output)?;
    let initial = &context.initial;
    if let Some(error) = &failure {
        fs::write(output.join("failure.txt"), error).map_err(|e| e.to_string())?;
    }
    let completed = failure.is_none();
    fs::write(output.join("final.csv"), snapshot(&sim)?).map_err(|e| e.to_string())?;
    let c = sim.counters();
    fs::write(output.join("polygons.csv"), polygons(&sim.state().mesh)?)
        .map_err(|e| e.to_string())?;
    let summary = format!(
        "{{\n\"quadratic_condition\":{},\"completed\":{completed},\"requested_time\":{time},\"profile\":\"{}\",\"gauge_reference_velocity\":{},\"gauge_offset\":{},\"case\":\"{case}\",\"n\":{n},\"nx\":{nx},\"ny\":{ny},\"lengths\":{:?},\"jitter\":{jitter},\"parallel_velocity\":{parallel_velocity},\"time\":{:.17e},\"dt_cap\":{},\"limited\":{limited},\"motion\":\"{motion}\",\"boost\":{},\"mesh_velocity\":{},\"gamma\":{},\"mean_B\":{},\"Bscale\":{},\n\"integrated_signal_travel\":{:.17e},\"max_signal_x\":{:.17e},\"max_face_signal\":{:.17e},\"geometric_conservation_max\":{:.17e},\"steps\":{},\"dt_min\":{},\"dt_max\":{:.17e},\"rejected_geometry\":{},\"rejected_state\":{},\"rejected_cfl\":{},\"hll_fallbacks\":{},\"hll_fallbacks_attempted\":{},\"auxiliary_coarsenings\":{},\"auxiliary_roots\":{:?},\"auxiliary_origin\":{},\n\"initial\":{},\n\"final\":{}\n}}\n",
        sim.quadratic_condition()
            .map_or("null".into(), |x| format!("{x:.17e}")),
        sim.config().profile.name(),
        array(sim.reference_velocity()),
        array(sim.state().gauge_offset),
        lengths,
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
        c.integrated_signal_travel,
        c.max_signal_x,
        c.max_face_signal,
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
