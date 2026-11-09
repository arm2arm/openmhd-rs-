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

fn audit(jitter: f64, output: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let dt = 1e-6;
    let target = 253;
    let mut sim = Simulation::new(
        Mesh::lattice(256, 4, [2., 0.125], jitter)?,
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

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let destination = std::env::args()
        .nth(1)
        .ok_or("usage: paper-shock-audit NEW_DIRECTORY")?;
    let path = Path::new(&destination);
    fs::create_dir(path)?;
    for jitter in [0., 0.15] {
        audit(jitter, path)?;
    }
    Ok(())
}
