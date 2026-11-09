//! Run the paper-global-v2 2.5D operator/coupling packet (not the full M1 matrix).
use mhd_vector_pot::benchmarks::{
    alfven_initial, brio_initial, loop_amplitude, loop_initial, vortex_initial,
};
use mhd_vector_pot::diagnostics::{Diagnostics, Divergence, Norms};
use mhd_vector_pot::general::{Config, Initial, Motion, Profile, Simulation};
use moving_mesh::Mesh;
use std::{f64::consts::TAU, fmt::Write as _, fs, path::PathBuf};

fn trace_energy(sim: &Simulation, stream: &mut impl std::io::Write) -> Result<(), String> {
    for (i, r) in sim.energy_rates()?.iter().enumerate() {
        let c = &sim.state().mesh.cells[i];
        writeln!(stream, "{i},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
            sim.time(), c.centroid[0], c.centroid[1], r.thermal, r.kinetic, r.magnetic,
            r.total_rate, r.kinetic_rate, r.magnetic_rate, r.magnetic_rate_fv, r.pressure_rate)
            .map_err(|e| e.to_string())?;
    }
    stream.flush().map_err(|e| e.to_string())
}

fn trace_diagnostics(sim: &Simulation, stream: &mut impl std::io::Write) -> Result<(), String> {
    let d = sim.diagnostics()?;
    writeln!(
        stream,
        "{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
        sim.time(),
        d.min_density,
        d.min_pressure,
        d.normalized_budget
            .iter()
            .map(|v| v.abs())
            .fold(0., f64::max),
        d.magnetic_energy,
        d.divergence_ls.dimensional.rms,
        d.divergence_face.dimensional.rms,
        d.divergence_limited_face.dimensional.rms
    )
    .map_err(|e| e.to_string())
}

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
/// Oriented cell half-planes in each cell's local periodic image.
fn geometry(sim: &Simulation) -> Result<String, String> {
    let mesh = &sim.state().mesh;
    let mut cells = Vec::with_capacity(mesh.cells.len());
    for (i, cell) in mesh.cells.iter().enumerate() {
        let planes: Vec<_> = cell
            .faces
            .iter()
            .map(|&(f, sign)| {
                let face = &mesh.faces[f];
                let d = mesh.displacement(face, i);
                array([
                    sign * face.normal[0],
                    sign * face.normal[1],
                    cell.centroid[0] + d[0],
                    cell.centroid[1] + d[1],
                ])
            })
            .collect();
        cells.push(format!(
            "{{\"id\":{i},\"centroid\":{},\"generator\":{},\"volume\":{:.17e},\"planes\":[{}]}}",
            array(cell.centroid),
            array(mesh.generators[i]),
            cell.volume,
            planes.join(",")
        ));
    }
    Ok(format!(
        "{{\"time\":{:.17e},\"lengths\":{},\"cells\":[{}]}}\n",
        sim.time(),
        array(mesh.lengths),
        cells.join(",")
    ))
}
fn run() -> Result<(), String> {
    let mut case = String::from("smooth");
    let mut profile = Profile::PaperGlobalV2;
    let mut parallel_velocity: f64 = 0.;
    let mut n = 8usize;
    let mut threads = 1usize;
    let mut jitter = 0.;
    let mut ny_override: Option<usize> = None;
    let mut column_jitter = false;
    let mut time = 0.02;
    let mut max_dt = f64::INFINITY;
    let mut checkpoints: Vec<f64> = Vec::new();
    let mut boost = [0.; 3];
    let mut mean_override = [None; 3];
    let mut mesh_velocity = [0.; 2];
    let mut motion = String::from("fixed");
    let mut limited = true;
    let mut energy_trace = false;
    let mut accelerated_projection = false;
    let mut projection_screening = 0.;
    let mut diagnostic_trace = false;
    let mut output = PathBuf::from("results/vector_potential_single");
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == "--help" {
            println!(
                "vector-potential --profile paper-global-v2|paper-state-emf-v1|bulk-frame-v1|bulk-frame-signal-v1|bulk-frame-heun-v1|bulk-frame-heun-spline-v1|bulk-frame-heun-projected-v1|bulk-frame-heun-quadratic-v1 --case uniform|curl|gauge|smooth|deform|alfven|loop|brio-wu|orszag-tang --n N --ny NY --threads 1..24 --jitter J --jitter-mode planar|columns --time T --dt DT --checkpoint T (repeatable)\n  --motion fixed|rigid|fluid|prescribed --mesh-x WX --mesh-y WY\n  --boost-x VX --boost-y VY --boost-z VZ --mean-bx BX --mean-by BY --mean-bz BZ --parallel-velocity V --unlimited --accelerated-projection --projection-screening K --trace-energy --trace-diagnostics --output DIR\nOutputs initial.csv, final.csv and summary.json; f64, periodic, mu0=1. Unit square/gamma=5/3 except Brio: [0,2]x[0,0.125], gamma=2. --ny defaults to 4 for Brio and N otherwise; --jitter-mode columns displaces whole columns along x only (y-invariant rectangles), planar is the registered 2D jitter. --projection-screening K>=0 damps the projected-rate correction (0, the default, is the exact projection). --trace-energy records accepted-state energy rates for fixed/rigid motion. --trace-diagnostics records accepted-step positivity, budget, magnetic energy and three divergence histories."
            );
            return Ok(());
        }
        if arg == "--unlimited" {
            limited = false;
            continue;
        }
        if arg == "--accelerated-projection" {
            accelerated_projection = true;
            continue;
        }
        if arg == "--trace-energy" {
            energy_trace = true;
            continue;
        }
        if arg == "--trace-diagnostics" {
            diagnostic_trace = true;
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
                    "paper-state-emf-v1" => Profile::PaperStateEmfV1,
                    "bulk-frame-v1" => Profile::BulkFrameV1,
                    "bulk-frame-signal-v1" => Profile::BulkFrameSignalV1,
                    "bulk-frame-heun-v1" => Profile::BulkFrameHeunV1,
                    "bulk-frame-heun-spline-v1" => Profile::BulkFrameHeunSplineV1,
                    "bulk-frame-heun-projected-v1" => Profile::BulkFrameHeunProjectedV1,
                    "bulk-frame-heun-quadratic-v1" => Profile::BulkFrameHeunQuadraticV1,
                    _ => return Err("unknown profile".into()),
                }
            }
            "--parallel-velocity" => parallel_velocity = number()?,
            "--n" => n = value.parse().map_err(|_| "invalid n")?,
            "--threads" => threads = value.parse().map_err(|_| "invalid threads")?,
            "--jitter" => jitter = number()?,
            "--projection-screening" => projection_screening = number()?,
            "--ny" => ny_override = Some(value.parse().map_err(|_| "invalid ny")?),
            "--jitter-mode" => {
                column_jitter = match value.as_str() {
                    "planar" => false,
                    "columns" => true,
                    _ => return Err("unknown jitter mode".into()),
                }
            }
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
        "uniform",
        "curl",
        "gauge",
        "smooth",
        "deform",
        "alfven",
        "loop",
        "brio-wu",
        "orszag-tang",
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
    moving_mesh::parallel::with_threads(threads, || {
        let started = std::time::Instant::now();
        let default_ny = if case == "brio-wu" { 4 } else { n };
        let ny = ny_override.unwrap_or(default_ny);
        let lengths = if case == "brio-wu" {
            [2., 0.125]
        } else {
            [1.; 2]
        };
        let mesh = if column_jitter {
            Mesh::lattice_columns(n, ny, lengths, jitter)?
        } else {
            Mesh::lattice(n, ny, lengths, jitter)?
        };
        let mesh_seconds = started.elapsed().as_secs_f64();
        println!("mesh ready: N={n}, threads={threads}, {mesh_seconds:.3} s");
        let initialized = std::time::Instant::now();
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
        } else if case == "brio-wu" {
            [0.75, 0., 0.]
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
            accelerated_projection,
            projection_screening,
            gamma: if case == "brio-wu" { 2. } else { 5. / 3. },
            motion: generator_motion,
            mean_magnetic: mean,
            max_dt,
            limited,
            track_signal_travel: case == "brio-wu",
            magnetic_scale: match case.as_str() {
                "alfven" => 1.,
                "loop" => loop_amplitude(),
                "brio-wu" => 1.,
                "orszag-tang" => 1. / (4. * std::f64::consts::PI).sqrt(),
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
            if case == "brio-wu" {
                return brio_initial(position, boost);
            }
            if case == "orszag-tang" {
                return vortex_initial(position, boost);
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
        let initialization_seconds = initialized.elapsed().as_secs_f64();
        let mut evolution_seconds = 0.;
        fs::create_dir_all(&output).map_err(|e| e.to_string())?;
        let mut trace = if energy_trace {
            use std::io::Write;
            let mut stream = std::io::BufWriter::new(
                fs::File::create(output.join("energy_trace.csv")).map_err(|e| e.to_string())?,
            );
            writeln!(stream, "id,time,x,y,thermal,kinetic,magnetic,total_rate,kinetic_rate,magnetic_rate,magnetic_rate_fv,pressure_rate").map_err(|e| e.to_string())?;
            trace_energy(&sim, &mut stream)?;
            Some(stream)
        } else {
            None
        };
        let mut step_trace = if diagnostic_trace {
            use std::io::Write;
            let mut stream = std::io::BufWriter::new(
                fs::File::create(output.join("accepted_diagnostics.csv"))
                    .map_err(|e| e.to_string())?,
            );
            writeln!(stream,"time,rho_min,p_min,budget_max,magnetic_energy,div_ls_rms,div_face_rms,div_limited_rms").map_err(|e|e.to_string())?;
            trace_diagnostics(&sim, &mut stream)?;
            Some(stream)
        } else {
            None
        };
        fs::write(output.join("initial.csv"), snapshot(&sim)?).map_err(|e| e.to_string())?;
        let initial = diagnostic(&sim.diagnostics()?);
        checkpoints.push(time);
        checkpoints.sort_by(f64::total_cmp);
        checkpoints.dedup();
        let mut history = vec![format!("{{\"time\":0,\"diagnostics\":{initial}}}")];
        let mut failure = None;
        for target in checkpoints {
            let advanced = std::time::Instant::now();
            failure = if trace.is_some() || step_trace.is_some() {
                sim.advance_to_observed(target, |s| {
                    if let Some(stream) = &mut trace {
                        trace_energy(s, stream)?;
                    }
                    if let Some(stream) = &mut step_trace {
                        trace_diagnostics(s, stream)?;
                    }
                    Ok(())
                })
                .err()
            } else {
                sim.advance_to(target).err()
            };
            evolution_seconds += advanced.elapsed().as_secs_f64();
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
        if let Some(stream) = &mut step_trace {
            use std::io::Write;
            stream.flush().map_err(|e| e.to_string())?;
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
            "{{\n\"completed\":{completed},\"requested_time\":{time},\"profile\":\"{}\",\"gauge_reference_velocity\":{},\"gauge_offset\":{},\"case\":\"{case}\",\"n\":{n},\"jitter\":{jitter},\"parallel_velocity\":{parallel_velocity},\"time\":{:.17e},\"dt_cap\":{},\"limited\":{limited},\"motion\":\"{motion}\",\"boost\":{},\"mesh_velocity\":{},\"gamma\":{},\"mean_B\":{},\"Bscale\":{},\n\"geometric_conservation_max\":{:.17e},\"steps\":{},\"dt_min\":{},\"dt_max\":{:.17e},\"rejected_geometry\":{},\"rejected_state\":{},\"rejected_cfl\":{},\"hll_fallbacks\":{},\"hll_fallbacks_attempted\":{},\"auxiliary_coarsenings\":{},\"auxiliary_roots\":{:?},\"auxiliary_origin\":{},\"endpoint_auxiliary_roots\":{:?},\"endpoint_auxiliary_coarsenings\":{},\n\"initial\":{},\n\"final\":{}\n}}\n",
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
            c.endpoint_auxiliary_roots,
            c.endpoint_auxiliary_coarsenings,
            initial,
            diagnostic(&sim.diagnostics()?)
        );
        let summary = if accelerated_projection {
            summary.replacen("{\n", "{\n\"projection_solver\":\"cached-cholesky-pcg\",\"projection_preconditioner_shift\":1e-8,\n", 1)
        } else {
            summary
        };
        let summary = if projection_screening != 0. {
            summary.replacen(
                "{\n",
                &format!("{{\n\"projection_screening\":{projection_screening},\n"),
                1,
            )
        } else {
            summary
        };
        // Historical summaries stay byte-identical: record the opt-in mesh
        // controls only when they differ from the registered lattice.
        let summary = if column_jitter || ny != default_ny {
            summary.replacen(
                "{\n",
                &format!(
                    "{{\n\"ny\":{ny},\"jitter_mode\":\"{}\",\n",
                    if column_jitter { "columns" } else { "planar" }
                ),
                1,
            )
        } else {
            summary
        };
        fs::write(output.join("summary.json"), summary).map_err(|e| e.to_string())?;
        if case == "brio-wu" || case == "orszag-tang" {
            fs::write(output.join("physics.json"), format!(
                "{{\"nx\":{n},\"ny\":{ny},\"lengths\":{},\"signal_travel_x\":{:.17e},\"signal_tracking\":{},\"scope\":\"maximum x characteristics in the rigid mesh frame, accepted reconstructed stages and final closure; not a strict numerical domain-of-dependence proof\"}}\n",
                array(lengths), c.signal_travel_x, sim.config().track_signal_travel,
            )).map_err(|e| e.to_string())?;
            fs::write(output.join("geometry.json"), geometry(&sim)?).map_err(|e| e.to_string())?;
        }
        println!(
            "{case}: t={:.6}, {} steps; {}",
            sim.time(),
            c.steps,
            output.display()
        );
        fs::write(output.join("timing.json"), format!(
        "{{\"threads\":{threads},\"mesh_seconds\":{mesh_seconds},\"initialization_seconds\":{initialization_seconds},\"evolution_seconds\":{evolution_seconds},\"total_seconds\":{}}}\n", started.elapsed().as_secs_f64()
    )).map_err(|e| e.to_string())?;
        if let Some(error) = failure {
            return Err(error);
        }
        Ok(())
    })?
}
fn main() {
    if let Err(error) = run() {
        eprintln!("error: {error}");
        std::process::exit(1);
    }
}
