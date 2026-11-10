//! Uniform-state response of the actual semidiscrete A/fluid operator (#24).
//! No evolution, no changed production operator. Unlimited Fourier blocks are
//! interpretable only when the measured leakage and amplitude dependence vanish.
use mhd_core::dot;
use mhd_vector_pot::general::{Config, Initial, Profile, Simulation};
use moving_mesh::Mesh;
use std::f64::consts::TAU;

const LENGTH: f64 = 0.125;
const FIELDS: [&str; 12] = [
    "rho",
    "vx",
    "vy",
    "p",
    "scaled_az",
    "by_curl",
    "by_fv",
    "scaled_az_raw",
    "p_raw",
    "by_raw",
    "vx_faces_x",
    "vx_faces_y",
];

fn shape(position: [f64; 2], wave: usize, transverse: usize) -> [f64; 2] {
    let row = (position[1] / (LENGTH / 4.)).floor() as usize;
    let sign = if transverse == 2 && row % 2 == 1 {
        -1.
    } else {
        1.
    };
    let phase = TAU * wave as f64 * position[0] / LENGTH;
    [sign * phase.cos(), sign * phase.sin()]
}

fn project(values: &[f64], basis: &[[f64; 2]], weights: &[f64]) -> ([f64; 2], f64) {
    let mut gram = [[0.; 2]; 2];
    let mut rhs = [0.; 2];
    for ((&value, b), &w) in values.iter().zip(basis).zip(weights) {
        for j in 0..2 {
            rhs[j] += w * b[j] * value;
            for k in 0..2 {
                gram[j][k] += w * b[j] * b[k];
            }
        }
    }
    let det = gram[0][0] * gram[1][1] - gram[0][1] * gram[1][0];
    let coefficients = [
        (gram[1][1] * rhs[0] - gram[0][1] * rhs[1]) / det,
        (gram[0][0] * rhs[1] - gram[1][0] * rhs[0]) / det,
    ];
    let residual = values
        .iter()
        .zip(basis)
        .zip(weights)
        .map(|((&v, b), &w)| w * (v - coefficients[0] * b[0] - coefficients[1] * b[1]).powi(2))
        .sum::<f64>()
        .sqrt();
    (coefficients, residual)
}

fn response(sim: &Simulation, scale: f64) -> Result<Vec<[f64; 12]>, String> {
    let primitive = sim.primitives()?;
    let rates = sim.frozen_rates()?;
    Ok(primitive
        .iter()
        .zip(rates)
        .map(|(q, r)| {
            let kinetic = dot(q.velocity, [r.fluid[1], r.fluid[2], r.fluid[3]])
                - 0.5 * dot(q.velocity, q.velocity) * r.fluid[0];
            [
                r.fluid[0],
                (r.fluid[1] - q.velocity[0] * r.fluid[0]) / q.density,
                (r.fluid[2] - q.velocity[1] * r.fluid[0]) / q.density,
                (sim.config().gamma - 1.)
                    * (r.fluid[4] - kinetic - dot(q.magnetic, r.magnetic_curl)),
                scale * r.potential[2],
                r.magnetic_curl[1],
                r.magnetic_fv[1],
                scale * r.potential_unprojected[2],
                (sim.config().gamma - 1.)
                    * (r.fluid[4] - kinetic - dot(q.magnetic, r.magnetic_unprojected)),
                r.magnetic_unprojected[1],
                (r.fluid_faces_x[1] - q.velocity[0] * r.fluid_faces_x[0]) / q.density,
                (r.fluid_faces_y[1] - q.velocity[0] * r.fluid_faces_y[0]) / q.density,
            ]
        })
        .collect())
}

fn run() -> Result<(), String> {
    let mut args = std::env::args().skip(1);
    let nx: usize = args.next().ok_or("nx")?.parse().map_err(|_| "nx")?;
    let wave: usize = args.next().ok_or("x mode")?.parse().map_err(|_| "x mode")?;
    let transverse: usize = args.next().ok_or("y mode")?.parse().map_err(|_| "y mode")?;
    let epsilon: f64 = args
        .next()
        .ok_or("epsilon")?
        .parse()
        .map_err(|_| "epsilon")?;
    let background = args.next().ok_or("background")?;
    if args.next().is_some()
        || !(8..=64).contains(&nx)
        || wave == 0
        || wave >= nx / 2
        || ![0, 2].contains(&transverse)
        || !epsilon.is_finite()
        || epsilon <= 0.
        || epsilon > 1e-4
    {
        return Err("Require nx 8..64, 0 < wave < nx/2, y mode 0 or 2, epsilon in (0,1e-4]".into());
    }
    // Explicit manufactured positive states: downstream is representative,
    // rounded, not an exact Brio reference solution.
    let (rho, pressure, velocity, magnetic) = match background.as_str() {
        "downstream" => (0.235, 0.512, [0.592, -1.579, 0.], [0.75, -0.535, 0.]),
        "rest" => (0.235, 0.512, [0.; 3], [0.75, -0.535, 0.]),
        "hydro" => (1., 1., [0.592, -1.579, 0.], [0.; 3]),
        _ => return Err("background must be downstream, rest or hydro".into()),
    };
    let mesh = Mesh::lattice(nx, 4, [LENGTH; 2], 0.)?;
    let basis: Vec<_> = mesh
        .cells
        .iter()
        .map(|c| shape(c.centroid, wave, transverse))
        .collect();
    let weights: Vec<_> = mesh.cells.iter().map(|c| c.volume).collect();
    let scale = TAU * wave as f64 / LENGTH;
    let make = |input: usize, phase: usize, amplitude: f64| {
        Simulation::new(
            mesh.clone(),
            Config {
                profile: Profile::BulkFrameHeunQuadraticV1,
                gamma: 2.,
                mean_magnetic: magnetic,
                accelerated_projection: true,
                projection_screening: 1.,
                limited: false,
                ..Config::default()
            },
            |p| {
                let delta = amplitude * shape(p, wave, transverse)[phase];
                let mut q = Initial {
                    density: rho,
                    pressure,
                    velocity,
                    potential: [0.; 3],
                    phi: 0.,
                };
                match input {
                    0 => q.density += delta,
                    1 => q.velocity[0] += delta,
                    2 => q.velocity[1] += delta,
                    3 => q.pressure += delta,
                    4 => q.potential[2] = delta / scale,
                    _ => unreachable!(),
                }
                q
            },
        )
    };
    let reference = response(&make(0, 0, 0.)?, scale)?;
    let reference_max = reference
        .iter()
        .flatten()
        .map(|v| v.abs())
        .fold(0., f64::max);
    println!(
        "nx,x_mode,y_mode,epsilon,background,input,input_phase,output,output_phase,derivative,leakage_l2,reference_rate_max"
    );
    for (input, name) in FIELDS.iter().enumerate().take(5) {
        for phase in 0..2 {
            let plus = response(&make(input, phase, epsilon)?, scale)?;
            let minus = response(&make(input, phase, -epsilon)?, scale)?;
            for (output, field) in FIELDS.iter().enumerate() {
                let diff: Vec<_> = plus
                    .iter()
                    .zip(&minus)
                    .map(|(a, b)| (a[output] - b[output]) / (2. * epsilon))
                    .collect();
                let (coeff, leakage) = project(&diff, &basis, &weights);
                if !coeff
                    .iter()
                    .chain([leakage, reference_max].iter())
                    .all(|v| v.is_finite())
                {
                    return Err("Nonfinite modal response".into());
                }
                for (out_phase, value) in coeff.into_iter().enumerate() {
                    println!(
                        "{nx},{wave},{transverse},{epsilon:.17e},{background},{name},{phase},{field},{out_phase},{value:.17e},{leakage:.17e},{reference_max:.17e}"
                    );
                }
            }
        }
    }
    Ok(())
}

fn main() -> Result<(), String> {
    moving_mesh::parallel::with_threads(1, run)?
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn weighted_projection_separates_retained_and_orthogonal_modes() {
        let basis: Vec<_> = (0..32)
            .map(|i| {
                shape(
                    [
                        ((i % 8) as f64 + 0.5) * LENGTH / 8.,
                        (i / 8) as f64 * LENGTH / 4. + LENGTH / 8.,
                    ],
                    1,
                    2,
                )
            })
            .collect();
        let weights = vec![LENGTH * LENGTH / 32.; 32];
        let values: Vec<_> = basis.iter().map(|b| 3. * b[0] - 2. * b[1] + 5.).collect();
        let (coeff, residual) = project(&values, &basis, &weights);
        assert!((coeff[0] - 3.).abs() < 1e-12 && (coeff[1] + 2.).abs() < 1e-12);
        assert!((residual - 5. * LENGTH).abs() < 1e-12);
    }
}
