//! Bounded initial/endpoint face audit of the literal paper source, without a fix.
//! The initial stationary Brio state has u=0, phi=0, and only Az nonzero, so
//! all gauge/transport/cleaning terms vanish in both frozen-auxiliary stages.
use mhd_core::{FaceFlux, IdealGas, Primitive, cross, riemann};
use mhd_vector_pot::{
    benchmarks::brio_initial,
    general::{Config, Motion, Profile, Simulation},
    operators::{PrimitiveGradient, predict},
};
use moving_mesh::{Derivatives, Mesh};
use std::{collections::BTreeMap, fs, io::Write, path::Path};
#[path = "support/centered_fit.rs"]
mod centered_fit;
#[path = "support/shock_pattern.rs"]
mod shock_pattern;

fn components(q: Primitive) -> [f64; 8] {
    [
        q.density,
        q.velocity[0],
        q.velocity[1],
        q.velocity[2],
        q.pressure,
        q.magnetic[0],
        q.magnetic[1],
        q.magnetic[2],
    ]
}

struct Sweep {
    faces: Vec<(Primitive, Primitive, FaceFlux)>,
    az_rate: Vec<f64>,
    fluid_rate: Vec<[f64; 5]>,
}

fn sweep(mesh: &Mesh, q: &[Primitive], g: &[PrimitiveGradient], dt: f64) -> Result<Sweep, String> {
    let mut faces = Vec::new();
    let mut az_rate = vec![0.; q.len()];
    let mut fluid_rate = vec![[0.; 5]; q.len()];
    let perimeter: Vec<f64> = mesh
        .cells
        .iter()
        .map(|c| c.faces.iter().map(|&(f, _)| mesh.faces[f].area).sum())
        .collect();
    for face in &mesh.faces {
        let eos = IdealGas::new(2.)?;
        let left = predict(
            eos,
            q[face.left],
            g[face.left],
            mesh.displacement(face, face.left),
            dt,
        )?;
        let right = predict(
            eos,
            q[face.right],
            g[face.right],
            mesh.displacement(face, face.right),
            dt,
        )?;
        let flux = riemann(
            eos,
            left,
            right,
            [face.normal[0], face.normal[1], 0.],
            [0.; 3],
        )?;
        let emf = cross(flux.velocity, flux.magnetic)[2];
        for (i, sign) in [(face.left, -1.), (face.right, 1.)] {
            az_rate[i] += face.area / perimeter[i] * emf;
            for k in 0..5 {
                fluid_rate[i][k] += sign * face.area * flux.fluid[k];
            }
        }
        faces.push((left, right, flux));
    }
    Ok(Sweep {
        faces,
        az_rate,
        fluid_rate,
    })
}

fn audit(
    jitter: f64,
    height: f64,
    copies: usize,
    output: &Path,
) -> Result<(), Box<dyn std::error::Error>> {
    let dt = 1e-6;
    let target = 253;
    let mut sim = Simulation::new(
        shock_pattern::mesh(256, jitter, height, copies)?,
        Config {
            profile: Profile::PaperStateEmfV1,
            motion: Motion::Fixed,
            gamma: 2.,
            mean_magnetic: [0.75, 0., 0.],
            max_dt: dt,
            ..Config::default()
        },
        |x| brio_initial(x, [0.; 3]),
    )?;
    let mesh = &sim.state().mesh;
    let q = sim.primitives()?;
    let derivative = Derivatives::build(mesh, false)?;
    let mut g = vec![[[0.; 2]; 8]; q.len()];
    for k in 0..8 {
        let values: Vec<_> = q.iter().map(|&q| components(q)[k]).collect();
        let raw = derivative.gradient(&values)?;
        let limited = mesh.limit_gradients(&values, &raw)?;
        for (i, gradient) in limited.into_iter().enumerate() {
            g[i][k] = gradient;
        }
    }
    let old = sweep(mesh, &q, &g, 0.)?;
    let end = sweep(mesh, &q, &g, dt)?;
    let measured = sim.energy_rates()?;
    let curl_rate = derivative.gradient(&old.az_rate)?;
    for i in 0..q.len() {
        let magnetic = q[i].magnetic[0] * curl_rate[i][1] - q[i].magnetic[1] * curl_rate[i][0];
        assert!(
            (old.fluid_rate[i][4] / mesh.cells[i].volume - measured[i].total_rate).abs() < 1e-10
        );
        assert!((magnetic - measured[i].magnetic_rate).abs() < 1e-10);
    }
    let mut weight = BTreeMap::<usize, [f64; 2]>::new();
    let samples = &derivative.samples[target];
    for sample in samples {
        for k in 0..2 {
            weight.entry(sample.index).or_default()[k] += sample.weight[k];
            weight.entry(samples[0].index).or_default()[k] -= sample.weight[k];
        }
    }
    let mut cells = fs::File::create(output.join(format!("j{jitter}_cells.csv")))?;
    writeln!(
        cells,
        "id,x,y,volume,rho,p,bx,by,weight_x,weight_y,az_rate,magnetic_rate,total_rate,pressure_rate"
    )?;
    for (i, c) in mesh.cells.iter().enumerate() {
        let w = weight.get(&i).copied().unwrap_or_default();
        writeln!(
            cells,
            "{i},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
            c.centroid[0],
            c.centroid[1],
            c.volume,
            q[i].density,
            q[i].pressure,
            q[i].magnetic[0],
            q[i].magnetic[1],
            w[0],
            w[1],
            old.az_rate[i],
            measured[i].magnetic_rate,
            measured[i].total_rate,
            measured[i].pressure_rate
        )?;
    }
    let perimeter: Vec<f64> = mesh
        .cells
        .iter()
        .map(|c| c.faces.iter().map(|&(f, _)| mesh.faces[f].area).sum())
        .collect();
    for (name, sweep) in [("old", &old), ("endpoint", &end)] {
        let mut file = fs::File::create(output.join(format!("j{jitter}_{name}_faces.csv")))?;
        writeln!(
            file,
            "face,left,right,x,y,area,nx,ny,method,l_rho,l_p,l_bx,l_by,r_rho,r_p,r_bx,r_by,state_emf,flux_emf,flux_energy,target_energy_rate,target_magnetic_rate,target_fv_magnetic_rate"
        )?;
        let mut sum = [0.; 3];
        for (f, face) in mesh.faces.iter().enumerate() {
            let (left, right, flux) = &sweep.faces[f];
            let coefficient: f64 = [face.left, face.right]
                .into_iter()
                .map(|j| {
                    let w = weight.get(&j).copied().unwrap_or_default();
                    (q[target].magnetic[0] * w[1] - q[target].magnetic[1] * w[0]) * face.area
                        / perimeter[j]
                })
                .sum();
            let sign = if face.left == target {
                -1.
            } else if face.right == target {
                1.
            } else {
                0.
            };
            let emf = cross(flux.velocity, flux.magnetic)[2];
            let energy = sign * face.area * flux.fluid[4] / mesh.cells[target].volume;
            let magnetic = coefficient * emf;
            let fv = sign * face.area * mhd_core::dot(q[target].magnetic, flux.induction)
                / mesh.cells[target].volume;
            for (s, value) in sum.iter_mut().zip([energy, magnetic, fv]) {
                *s += value;
            }
            if sign != 0. || weight.contains_key(&face.left) || weight.contains_key(&face.right) {
                writeln!(
                    file,
                    "{f},{},{},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:?},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{emf:.17e},{:.17e},{:.17e},{energy:.17e},{magnetic:.17e},{fv:.17e}",
                    face.left,
                    face.right,
                    face.centroid[0],
                    face.centroid[1],
                    face.area,
                    face.normal[0],
                    face.normal[1],
                    flux.method,
                    left.density,
                    left.pressure,
                    left.magnetic[0],
                    left.magnetic[1],
                    right.density,
                    right.pressure,
                    right.magnetic[0],
                    right.magnetic[1],
                    flux.electromotive[2],
                    flux.fluid[4]
                )?;
            }
        }
        if name == "old" {
            for (a, b) in sum.into_iter().zip([
                measured[target].total_rate,
                measured[target].magnetic_rate,
                measured[target].magnetic_rate_fv,
            ]) {
                assert!((a - b).abs() < 1e-10);
            }
        }
        println!(
            "jitter={jitter} stage={name} target={target} dE={:.17e} dM_curl={:.17e} dM_fv={:.17e}",
            sum[0], sum[1], sum[2]
        );
    }
    let expected_a: Vec<f64> = sim
        .state()
        .potential
        .iter()
        .enumerate()
        .map(|(i, a)| a[2] + 0.5 * dt * (old.az_rate[i] + end.az_rate[i]))
        .collect();
    let expected_q: Vec<[f64; 5]> = sim
        .state()
        .conserved
        .iter()
        .enumerate()
        .map(|(i, q)| {
            std::array::from_fn(|k| q[k] + 0.5 * dt * (old.fluid_rate[i][k] + end.fluid_rate[i][k]))
        })
        .collect();
    let p0 = q[target].pressure;
    sim.advance_to(dt)?;
    assert_eq!(sim.counters().steps, 1);
    let mut a_error = 0.0_f64;
    let mut q_error = 0.0_f64;
    for i in 0..expected_a.len() {
        a_error = a_error.max((sim.state().potential[i][2] - expected_a[i]).abs());
        for k in 0..5 {
            q_error = q_error.max((sim.state().conserved[i][k] - expected_q[i][k]).abs());
        }
    }
    assert!(a_error < 1e-14 && q_error < 1e-14);
    println!(
        "jitter={jitter} one_step_dt={dt} A_assembly_error={a_error:.17e} Q_assembly_error={q_error:.17e} pressure_secant={:.17e}",
        (sim.primitives()?[target].pressure - p0) / dt
    );
    Ok(())
}

fn reconstruction_controls(output: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let target = 253;
    let mut summary = fs::File::create(output.join("rates.csv"))?;
    writeln!(
        summary,
        "height,jitter,variant,stage,total_rate,magnetic_rate,pressure_rate,minimum_pressure_rate,minimum_cell,budget_residual"
    )?;
    for height in [0.125, 0.03125] {
        for jitter in [0., 0.15] {
            let sim = Simulation::new(
                shock_pattern::mesh(256, jitter, height, 1)?,
                Config {
                    profile: Profile::PaperStateEmfV1,
                    gamma: 2.,
                    mean_magnetic: [0.75, 0., 0.],
                    ..Config::default()
                },
                |x| brio_initial(x, [0.; 3]),
            )?;
            let mesh = &sim.state().mesh;
            let q = sim.primitives()?;
            let stencil = Derivatives::build(mesh, false)?;
            let mut samples =
                fs::File::create(output.join(format!("h{height}_j{jitter}_kink_samples.csv")))?;
            writeln!(
                samples,
                "id,cx,cy,bx,by,neighbor,dx,dy,area,weight_x,weight_y,neighbor_Az"
            )?;
            for (i, primitive) in q.iter().enumerate().take(256).skip(253) {
                for (&(f, _), s) in mesh.cells[i].faces.iter().zip(&stencil.samples[i]) {
                    let (j, d) = mesh.neighbour(&mesh.faces[f], i);
                    assert_eq!(j, s.index);
                    writeln!(
                        samples,
                        "{i},{:.17e},{:.17e},{:.17e},{:.17e},{j},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
                        mesh.cells[i].centroid[0],
                        mesh.cells[i].centroid[1],
                        primitive.magnetic[0],
                        primitive.magnetic[1],
                        d[0],
                        d[1],
                        mesh.faces[f].area,
                        s.weight[0],
                        s.weight[1],
                        sim.state().potential[j][2]
                    )?;
                }
            }
            let mut free = vec![[[0.; 2]; 8]; q.len()];
            let mut centered = free.clone();
            let mut slopes =
                fs::File::create(output.join(format!("h{height}_j{jitter}_slopes.csv")))?;
            writeln!(
                slopes,
                "id,component,value,free_x,free_y,free_limited_x,free_limited_y,centered_x,centered_y,centered_limited_x,centered_limited_y"
            )?;
            for k in 0..8 {
                let values: Vec<_> = q.iter().map(|&p| components(p)[k]).collect();
                let raw_free = stencil.gradient(&values)?;
                let raw_centered = centered_fit::gradient(mesh, &values)?;
                let limited_free = mesh.limit_gradients(&values, &raw_free)?;
                let limited_centered = mesh.limit_gradients(&values, &raw_centered)?;
                for i in 0..q.len() {
                    free[i][k] = limited_free[i];
                    centered[i][k] = limited_centered[i];
                    writeln!(
                        slopes,
                        "{i},{k},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
                        values[i],
                        raw_free[i][0],
                        raw_free[i][1],
                        limited_free[i][0],
                        limited_free[i][1],
                        raw_centered[i][0],
                        raw_centered[i][1],
                        limited_centered[i][0],
                        limited_centered[i][1]
                    )?;
                }
            }
            for variant in [
                "baseline",
                "centered_all",
                "centered_magnetic",
                "zero_magnetic",
                "riemann_B_254",
                "riemann_B_255",
                "riemann_B_254_255",
                "riemann_B_all",
                "riemann_Bx_254_255",
                "riemann_By_254_255",
            ] {
                let mut g = free.clone();
                // Counterfactual inputs only: never modify Simulation or its
                // closure B below. These states are not consistent with A.
                let mut input = q.clone();
                if variant.starts_with("riemann_") {
                    for (i, value) in input.iter_mut().enumerate() {
                        if variant == "riemann_B_all"
                            || (i == 254 && variant != "riemann_B_255")
                            || (i == 255 && variant != "riemann_B_254")
                        {
                            if !variant.starts_with("riemann_By_") {
                                value.magnetic[0] = 0.75;
                            }
                            if !variant.starts_with("riemann_Bx_") {
                                value.magnetic[1] = if mesh.cells[i].centroid[0] < 1. {
                                    1.
                                } else {
                                    -1.
                                };
                            }
                        }
                    }
                    for k in 5..8 {
                        let values: Vec<_> = input.iter().map(|&p| components(p)[k]).collect();
                        let raw = stencil.gradient(&values)?;
                        let limited = mesh.limit_gradients(&values, &raw)?;
                        for (gradient, value) in g.iter_mut().zip(limited) {
                            gradient[k] = value;
                        }
                    }
                }
                for i in 0..q.len() {
                    match variant {
                        "centered_all" => g[i] = centered[i],
                        "centered_magnetic" => g[i][5..].copy_from_slice(&centered[i][5..]),
                        "zero_magnetic" => g[i][5..].fill([0.; 2]),
                        _ => {}
                    }
                }
                for (stage, dt) in [("old", 0.), ("endpoint", 1e-6)] {
                    let rates = sweep(mesh, &input, &g, dt)?;
                    let curl = stencil.gradient(&rates.az_rate)?;
                    let mut file = fs::File::create(
                        output.join(format!("h{height}_j{jitter}_{variant}_{stage}_cells.csv")),
                    )?;
                    writeln!(
                        file,
                        "id,bx,by,total_rate,magnetic_rate,pressure_rate,az_rate"
                    )?;
                    let mut pressure_min = (f64::INFINITY, 0);
                    let mut target_rates = [0.; 3];
                    let actual = if variant == "baseline" && dt == 0. {
                        Some(sim.energy_rates()?)
                    } else {
                        None
                    };
                    for i in 0..q.len() {
                        let e = rates.fluid_rate[i][4] / mesh.cells[i].volume;
                        let m = q[i].magnetic[0] * curl[i][1] - q[i].magnetic[1] * curl[i][0];
                        let p = e - m; // gamma=2 and stationary initial velocity.
                        if let Some(actual) = &actual {
                            assert!((e - actual[i].total_rate).abs() < 1e-10);
                            assert!((m - actual[i].magnetic_rate).abs() < 1e-10);
                        }
                        if p < pressure_min.0 {
                            pressure_min = (p, i);
                        }
                        if i == target {
                            target_rates = [e, m, p];
                        }
                        writeln!(
                            file,
                            "{i},{:.17e},{:.17e},{e:.17e},{m:.17e},{p:.17e},{:.17e}",
                            q[i].magnetic[0], q[i].magnetic[1], rates.az_rate[i]
                        )?;
                    }
                    let budget = (0..5)
                        .map(|k| {
                            let sum: f64 = rates.fluid_rate.iter().map(|r| r[k]).sum();
                            let scale: f64 = rates.fluid_rate.iter().map(|r| r[k].abs()).sum();
                            sum.abs() / (1. + scale)
                        })
                        .fold(0., f64::max);
                    assert!(budget < 1e-13);
                    writeln!(
                        summary,
                        "{height},{jitter},{variant},{stage},{:.17e},{:.17e},{:.17e},{:.17e},{},{budget:.17e}",
                        target_rates[0],
                        target_rates[1],
                        target_rates[2],
                        pressure_min.0,
                        pressure_min.1
                    )?;
                    let mut faces = fs::File::create(
                        output.join(format!("h{height}_j{jitter}_{variant}_{stage}_faces.csv")),
                    )?;
                    writeln!(
                        faces,
                        "face,left,right,area,nx,ny,l_bx,l_by,r_bx,r_by,energy_flux,state_emf"
                    )?;
                    for (f, face) in mesh
                        .faces
                        .iter()
                        .enumerate()
                        .filter(|(_, f)| f.left == target || f.right == target)
                    {
                        let (l, r, flux) = rates.faces[f];
                        writeln!(
                            faces,
                            "{f},{},{},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
                            face.left,
                            face.right,
                            face.area,
                            face.normal[0],
                            face.normal[1],
                            l.magnetic[0],
                            l.magnetic[1],
                            r.magnetic[0],
                            r.magnetic[1],
                            flux.fluid[4],
                            cross(flux.velocity, flux.magnetic)[2]
                        )?;
                    }
                }
            }
        }
    }
    Ok(())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() == 2 && args[1] == "--reconstruction-controls" {
        let path = Path::new(&args[0]);
        fs::create_dir(path)?;
        return reconstruction_controls(path);
    }
    if args.len() != 1 && args.len() != 3 {
        return Err("usage: paper-shock-audit NEW_DIRECTORY [PATTERN_HEIGHT COPIES]".into());
    }
    let height = if args.len() == 3 {
        args[1].parse()?
    } else {
        0.125
    };
    let copies = if args.len() == 3 { args[2].parse()? } else { 1 };
    let path = Path::new(&args[0]);
    fs::create_dir(path)?;
    for jitter in [0., 0.15] {
        audit(jitter, height, copies, path)?;
    }
    Ok(())
}
