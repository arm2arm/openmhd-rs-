//! Initial-state feasibility probe only; no time evolution or production changes.
use mhd_core::{FaceCompletion, IdealGas, Primitive, riemann_with_completion};
use mhd_vector_pot::{
    benchmarks::brio_initial,
    general::{Config, Profile, Simulation},
    operators::{PrimitiveGradient, predict},
};
use moving_mesh::{Derivatives, Mesh, Vec2};
use std::{collections::BTreeMap, fs, io::Write, path::Path};

struct Curl<'a> {
    mesh: &'a Mesh,
    derivative: Derivatives,
}
impl<'a> Curl<'a> {
    fn new(mesh: &'a Mesh) -> Result<Self, String> {
        Ok(Self {
            mesh,
            derivative: Derivatives::build(mesh, false)?,
        })
    }
    fn apply(&self, a: &[f64]) -> Result<Vec<Vec2>, String> {
        Ok(self
            .derivative
            .gradient(a)?
            .into_iter()
            .map(|d| [d[1], -d[0]])
            .collect())
    }
    /// C^T V with the same sample-baseline subtraction as Derivatives::gradient.
    fn transpose(&self, b: &[Vec2]) -> Vec<f64> {
        let mut result = vec![0.; self.mesh.cells.len()];
        for (i, samples) in self.derivative.samples.iter().enumerate() {
            let first = samples[0].index;
            for s in samples {
                let value =
                    self.mesh.cells[i].volume * (s.weight[1] * b[i][0] - s.weight[0] * b[i][1]);
                result[s.index] += value;
                result[first] -= value;
            }
        }
        result
    }
    fn diagonal(&self) -> Vec<f64> {
        let mut result = vec![0.; self.mesh.cells.len()];
        for (i, samples) in self.derivative.samples.iter().enumerate() {
            let mut row: BTreeMap<usize, Vec2> = BTreeMap::new();
            for s in samples {
                for k in 0..2 {
                    row.entry(s.index).or_default()[k] += s.weight[k];
                    row.entry(samples[0].index).or_default()[k] -= s.weight[k];
                }
            }
            for (j, d) in row {
                result[j] += self.mesh.cells[i].volume * (d[0] * d[0] + d[1] * d[1]);
            }
        }
        result
    }
    fn norm(&self, b: &[Vec2]) -> f64 {
        b.iter()
            .zip(&self.mesh.cells)
            .map(|(b, c)| c.volume * (b[0] * b[0] + b[1] * b[1]))
            .sum::<f64>()
            .sqrt()
    }
}
fn dot(a: &[f64], b: &[f64]) -> f64 {
    a.iter().zip(b).map(|(a, b)| a * b).sum()
}
fn subtract(a: &[Vec2], b: &[Vec2]) -> Vec<Vec2> {
    a.iter()
        .zip(b)
        .map(|(a, b)| [a[0] - b[0], a[1] - b[1]])
        .collect()
}
struct Projection {
    rate: Vec<f64>,
    iterations: usize,
    normal_relative_residual: f64,
}
fn project(curl: &Curl<'_>, initial: &[f64], target: &[Vec2]) -> Result<Projection, String> {
    let rhs = curl.transpose(&subtract(target, &curl.apply(initial)?));
    let rhs_norm = dot(&rhs, &rhs).sqrt();
    if rhs_norm <= 1e-30 {
        return Ok(Projection {
            rate: initial.to_vec(),
            iterations: 0,
            normal_relative_residual: 0.,
        });
    }
    let diagonal = curl.diagonal();
    if diagonal.iter().any(|d| !d.is_finite() || *d <= 0.) {
        return Err("invalid normal-operator diagonal".into());
    }
    let mut delta = vec![0.; initial.len()];
    let mut r = rhs.clone();
    let mut z: Vec<_> = r.iter().zip(&diagonal).map(|(r, d)| r / d).collect();
    let mut direction = z.clone();
    let mut rz = dot(&r, &z);
    for iteration in 1..=8 * initial.len() {
        let applied = curl.transpose(&curl.apply(&direction)?);
        let denominator = dot(&direction, &applied);
        if !denominator.is_finite() || denominator <= 0. {
            return Err(format!(
                "nonpositive normal-operator curvature at iteration {iteration}"
            ));
        }
        let alpha = rz / denominator;
        for i in 0..r.len() {
            delta[i] += alpha * direction[i];
            r[i] -= alpha * applied[i];
        }
        if dot(&r, &r).sqrt() / rhs_norm < 1e-11 {
            let true_applied = curl.transpose(&curl.apply(&delta)?);
            let relative = rhs
                .iter()
                .zip(true_applied)
                .map(|(b, a)| (b - a).powi(2))
                .sum::<f64>()
                .sqrt()
                / rhs_norm;
            if relative > 1e-9 {
                return Err(format!("normal residual drift: {relative}"));
            }
            return Ok(Projection {
                rate: initial.iter().zip(delta).map(|(a, d)| a + d).collect(),
                iterations: iteration,
                normal_relative_residual: relative,
            });
        }
        z = r.iter().zip(&diagonal).map(|(r, d)| r / d).collect();
        let next = dot(&r, &z);
        for i in 0..direction.len() {
            direction[i] = z[i] + (next / rz) * direction[i];
        }
        rz = next;
    }
    Err("normal solve did not converge within 8N iterations".into())
}

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
fn probe(nx: usize, jitter: f64, output: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let started = std::time::Instant::now();
    let sim = Simulation::new(
        Mesh::lattice(nx, 4, [2., 0.125], jitter)?,
        Config {
            profile: Profile::BulkFrameHeunSplineV1,
            gamma: 2.,
            mean_magnetic: [0.75, 0., 0.],
            ..Config::default()
        },
        |x| brio_initial(x, [0.; 3]),
    )?;
    let mesh = &sim.state().mesh;
    let q = sim.primitives()?;
    let curl = Curl::new(mesh)?;
    let mut gradients: Vec<PrimitiveGradient> = vec![[[0.; 2]; 8]; q.len()];
    for k in 0..8 {
        let values: Vec<_> = q.iter().map(|&q| components(q)[k]).collect();
        let limited = mesh.limit_gradients(&values, &curl.derivative.gradient(&values)?)?;
        for (g, d) in gradients.iter_mut().zip(limited) {
            g[k] = d;
        }
    }
    let eos = IdealGas::new(2.)?;
    let mut faces = Vec::new();
    let mut target = vec![[0.; 2]; q.len()];
    let mut energy = vec![0.; q.len()];
    for face in &mesh.faces {
        let reconstruct = |i| predict(eos, q[i], gradients[i], mesh.displacement(face, i), 0.);
        let flux = riemann_with_completion(
            eos,
            reconstruct(face.left)?,
            reconstruct(face.right)?,
            [face.normal[0], face.normal[1], 0.],
            [0.; 3],
            FaceCompletion::SignalWeighted,
        )?;
        for (i, sign) in [(face.left, -1.), (face.right, 1.)] {
            for k in 0..2 {
                target[i][k] += sign * face.area * flux.induction[k] / mesh.cells[i].volume;
            }
            energy[i] += sign * face.area * flux.fluid[4] / mesh.cells[i].volume;
        }
        faces.push(flux);
    }
    let baseline: Vec<_> = mesh
        .cells
        .iter()
        .map(|c| {
            let perimeter: f64 = c.faces.iter().map(|&(f, _)| mesh.faces[f].area).sum();
            c.faces
                .iter()
                .map(|&(f, _)| mesh.faces[f].area / perimeter * faces[f].electromotive[2])
                .sum()
        })
        .collect();
    let old_brate = curl.apply(&baseline)?;
    let measured = sim.energy_rates()?;
    let magnetic_rate = |i: usize, b: Vec2| q[i].magnetic[0] * b[0] + q[i].magnetic[1] * b[1];
    let mut agreement = 0.0_f64;
    for i in 0..q.len() {
        for (a, b) in [
            (energy[i], measured[i].total_rate),
            (magnetic_rate(i, old_brate[i]), measured[i].magnetic_rate),
            (magnetic_rate(i, target[i]), measured[i].magnetic_rate_fv),
        ] {
            agreement = agreement.max((a - b).abs() / (1. + b.abs()));
        }
    }
    if agreement > 1e-11 {
        return Err(format!("baseline assembly mismatch: {agreement}").into());
    }
    let projection = project(&curl, &baseline, &target)?;
    let next_brate = curl.apply(&projection.rate)?;
    let mut file = fs::File::create(output.join(format!("n{nx}_j{jitter}_cells.csv")))?;
    writeln!(
        file,
        "id,x,y,volume,bx,by,energy_rate,baseline_magnetic_rate,fv_magnetic_rate,projected_magnetic_rate,baseline_pressure_rate,fv_pressure_rate,projected_pressure_rate,baseline_az_rate,projected_az_rate"
    )?;
    for i in 0..q.len() {
        let c = &mesh.cells[i];
        let old = magnetic_rate(i, old_brate[i]);
        let fv = magnetic_rate(i, target[i]);
        let new = magnetic_rate(i, next_brate[i]);
        writeln!(
            file,
            "{i},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{old:.17e},{fv:.17e},{new:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
            c.centroid[0],
            c.centroid[1],
            c.volume,
            q[i].magnetic[0],
            q[i].magnetic[1],
            energy[i],
            energy[i] - old,
            energy[i] - fv,
            energy[i] - new,
            baseline[i],
            projection.rate[i]
        )?;
    }
    let target_norm = curl.norm(&target);
    let before = curl.norm(&subtract(&old_brate, &target)) / target_norm;
    let after = curl.norm(&subtract(&next_brate, &target)) / target_norm;
    println!(
        "{nx},{jitter},{},{:.17e},{before:.17e},{after:.17e},{agreement:.17e},{:.6}",
        projection.iterations,
        projection.normal_relative_residual,
        started.elapsed().as_secs_f64()
    );
    Ok(())
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let path = std::env::args()
        .nth(1)
        .ok_or("usage: shock-compatibility NEW_OUTPUT_DIR")?;
    let output = Path::new(&path);
    fs::create_dir(output)?;
    println!(
        "nx,jitter,iterations,normal_relative_residual,baseline_relative_mismatch,projected_relative_mismatch,baseline_assembly_relative_error,seconds"
    );
    for nx in [64, 128, 256] {
        for jitter in [0., 0.15] {
            probe(nx, jitter, output)?;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn weighted_transpose_matches_actual_derivative() {
        for jitter in [0., 0.15] {
            let mesh = Mesh::lattice(64, 4, [2., 0.125], jitter).unwrap();
            let c = Curl::new(&mesh).unwrap();
            let a: Vec<_> = (0..mesh.cells.len())
                .map(|i| (i as f64 * 1.37).sin())
                .collect();
            let b: Vec<_> = (0..mesh.cells.len())
                .map(|i| [(i as f64 * 0.83).cos(), (i as f64 * 0.43).sin()])
                .collect();
            let left: f64 = c
                .apply(&a)
                .unwrap()
                .iter()
                .zip(&b)
                .zip(&mesh.cells)
                .map(|((a, b), cell)| cell.volume * (a[0] * b[0] + a[1] * b[1]))
                .sum();
            let right = dot(&a, &c.transpose(&b));
            assert!((left - right).abs() < 1e-12 * (1. + left.abs()));
        }
    }
    #[test]
    fn recovers_a_known_compatible_rate_without_fixing_a_gauge() {
        for jitter in [0., 0.15] {
            let mesh = Mesh::lattice(64, 4, [2., 0.125], jitter).unwrap();
            let c = Curl::new(&mesh).unwrap();
            let a: Vec<_> = (0..mesh.cells.len())
                .map(|i| (i as f64 * 1.37).sin())
                .collect();
            let target = c.apply(&a).unwrap();
            let p = project(&c, &vec![0.; a.len()], &target).unwrap();
            assert!(
                c.norm(&subtract(&c.apply(&p.rate).unwrap(), &target)) / c.norm(&target) < 1e-8
            );
        }
    }
    #[test]
    fn incompatible_target_leaves_an_orthogonal_residual() {
        let mesh = Mesh::lattice(64, 4, [2., 0.125], 0.15).unwrap();
        let c = Curl::new(&mesh).unwrap();
        let b: Vec<_> = (0..mesh.cells.len())
            .map(|i| [(i as f64 * 0.83).cos(), (i as f64 * 0.43).sin()])
            .collect();
        let p = project(&c, &vec![0.; b.len()], &b).unwrap();
        let residual = subtract(&c.apply(&p.rate).unwrap(), &b);
        assert!(c.norm(&residual) / c.norm(&b) > 1e-3);
        let normal = c.transpose(&residual);
        let rhs = c.transpose(&b);
        assert!(dot(&normal, &normal).sqrt() / dot(&rhs, &rhs).sqrt() < 1e-9);
    }
}
