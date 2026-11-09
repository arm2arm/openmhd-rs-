//! Experimental weighted projection of a magnetic rate onto the planar curl range.
//! See docs/M1_SHOCK_INVESTIGATION.md: this is a nonlocal engineering comparator,
//! not the paper algorithm or a positivity guarantee. It changes A rates only.
//! C = (Dy Az, -Dx Az, Dx Ay-Dy Ax); solve C^T V C delta = C^T V(target-C rate).
use mhd_core::{Vec3, dot};
use moving_mesh::{Derivatives, Mesh, Vec2};
use std::collections::BTreeMap;

struct Curl<'a> {
    mesh: &'a Mesh,
    derivative: &'a Derivatives,
}
impl Curl<'_> {
    fn apply(&self, a: &[Vec3]) -> Result<Vec<Vec3>, String> {
        let gradients = (0..3)
            .map(|k| {
                self.derivative
                    .gradient(&a.iter().map(|a| a[k]).collect::<Vec<_>>())
            })
            .collect::<Result<Vec<_>, _>>()?;
        Ok((0..a.len())
            .map(|i| {
                [
                    gradients[2][i][1],
                    -gradients[2][i][0],
                    gradients[1][i][0] - gradients[0][i][1],
                ]
            })
            .collect())
    }
    fn transpose(&self, b: &[Vec3]) -> Vec<Vec3> {
        // Match Derivatives::gradient's sample-baseline subtraction exactly;
        // neglecting it would not be the transpose of the implemented operator.
        let mut result = vec![[0.; 3]; b.len()];
        for (i, samples) in self.derivative.samples.iter().enumerate() {
            for s in samples {
                let value = [
                    -s.weight[1] * b[i][2],
                    s.weight[0] * b[i][2],
                    s.weight[1] * b[i][0] - s.weight[0] * b[i][1],
                ];
                for (k, value) in value.iter().enumerate() {
                    result[s.index][k] += self.mesh.cells[i].volume * value;
                    result[samples[0].index][k] -= self.mesh.cells[i].volume * value;
                }
            }
        }
        result
    }
    fn diagonal(&self) -> Vec<Vec3> {
        let mut result = vec![[0.; 3]; self.mesh.cells.len()];
        for (i, samples) in self.derivative.samples.iter().enumerate() {
            let mut row: BTreeMap<usize, Vec2> = BTreeMap::new();
            for s in samples {
                for k in 0..2 {
                    row.entry(s.index).or_default()[k] += s.weight[k];
                    row.entry(samples[0].index).or_default()[k] -= s.weight[k];
                }
            }
            for (j, d) in row {
                for (k, value) in [d[1] * d[1], d[0] * d[0], d[0] * d[0] + d[1] * d[1]]
                    .iter()
                    .enumerate()
                {
                    result[j][k] += self.mesh.cells[i].volume * value;
                }
            }
        }
        result
    }
}
fn inner(a: &[Vec3], b: &[Vec3]) -> f64 {
    a.iter().zip(b).map(|(a, b)| dot(*a, *b)).sum()
}
fn subtract(a: &[Vec3], b: &[Vec3]) -> Vec<Vec3> {
    a.iter()
        .zip(b)
        .map(|(a, b)| std::array::from_fn(|k| a[k] - b[k]))
        .collect()
}
pub(crate) fn project(
    mesh: &Mesh,
    derivative: &Derivatives,
    initial: &[Vec3],
    target: &[Vec3],
) -> Result<Vec<Vec3>, String> {
    if initial.len() != mesh.cells.len()
        || target.len() != mesh.cells.len()
        || !initial
            .iter()
            .chain(target)
            .flatten()
            .all(|v| v.is_finite())
    {
        return Err("invalid projected-rate data".into());
    }
    let curl = Curl { mesh, derivative };
    let rhs = curl.transpose(&subtract(target, &curl.apply(initial)?));
    let rhs_norm = inner(&rhs, &rhs).sqrt();
    if rhs_norm <= 1e-30 {
        return Ok(initial.to_vec());
    }
    let diagonal = curl.diagonal();
    if diagonal
        .iter()
        .flatten()
        .any(|d| !d.is_finite() || *d <= 0.)
    {
        return Err("invalid projected-rate diagonal".into());
    }
    let precondition = |r: &[Vec3]| {
        r.iter()
            .zip(&diagonal)
            .map(|(r, d)| std::array::from_fn(|k| r[k] / d[k]))
            .collect::<Vec<Vec3>>()
    };
    let mut delta = vec![[0.; 3]; initial.len()];
    let mut r = rhs.clone();
    let mut z = precondition(&r);
    let mut direction = z.clone();
    let mut rz = inner(&r, &z);
    // There are 3N scalar unknowns. Start the correction at zero without an
    // explicit gauge constraint; stop on the magnetic-rate normal residual.
    for _ in 0..24 * initial.len() {
        let applied = curl.transpose(&curl.apply(&direction)?);
        let denominator = inner(&direction, &applied);
        if !denominator.is_finite() || denominator <= 0. {
            return Err("nonpositive projected-rate curvature".into());
        }
        let alpha = rz / denominator;
        for i in 0..r.len() {
            for k in 0..3 {
                delta[i][k] += alpha * direction[i][k];
                r[i][k] -= alpha * applied[i][k];
            }
        }
        if inner(&r, &r).sqrt() / rhs_norm < 1e-11 {
            let true_applied = curl.transpose(&curl.apply(&delta)?);
            let residual = subtract(&rhs, &true_applied);
            let relative = inner(&residual, &residual).sqrt() / rhs_norm;
            if !relative.is_finite() || relative > 1e-9 {
                return Err(format!("projected-rate residual drift: {relative}"));
            }
            return Ok(initial
                .iter()
                .zip(delta)
                .map(|(a, d)| std::array::from_fn(|k| a[k] + d[k]))
                .collect());
        }
        z = precondition(&r);
        let next = inner(&r, &z);
        for i in 0..r.len() {
            for k in 0..3 {
                direction[i][k] = z[i][k] + (next / rz) * direction[i][k];
            }
        }
        rz = next;
    }
    Err("projected-rate solve exceeded iteration limit".into())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn full_curl_transpose_and_compatible_target() {
        for jitter in [0., 0.15] {
            let mesh = Mesh::lattice(8, 8, [1.; 2], jitter).unwrap();
            let derivative = Derivatives::build(&mesh, false).unwrap();
            let c = Curl {
                mesh: &mesh,
                derivative: &derivative,
            };
            let a: Vec<Vec3> = (0..64)
                .map(|i| std::array::from_fn(|k| (i as f64 * 1.37 + k as f64).sin()))
                .collect();
            let b: Vec<Vec3> = (0..64)
                .map(|i| std::array::from_fn(|k| (i as f64 * 0.73 + k as f64).cos()))
                .collect();
            let left: f64 = c
                .apply(&a)
                .unwrap()
                .iter()
                .zip(&b)
                .zip(&mesh.cells)
                .map(|((a, b), cell)| cell.volume * dot(*a, *b))
                .sum();
            assert!((left - inner(&a, &c.transpose(&b))).abs() < 1e-12 * (1. + left.abs()));
            let target = c.apply(&a).unwrap();
            let result = project(&mesh, &derivative, &vec![[0.; 3]; 64], &target).unwrap();
            let residual = subtract(&c.apply(&result).unwrap(), &target);
            assert!(inner(&residual, &residual).sqrt() / inner(&target, &target).sqrt() < 1e-8);
        }
    }
    #[test]
    fn incompatible_target_has_stationary_residual_and_rejects_invalid_input() {
        let mesh = Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap();
        let derivative = Derivatives::build(&mesh, false).unwrap();
        let c = Curl {
            mesh: &mesh,
            derivative: &derivative,
        };
        let b: Vec<Vec3> = (0..64)
            .map(|i| std::array::from_fn(|k| (i as f64 * 0.73 + k as f64).cos()))
            .collect();
        let initial = vec![[0.; 3]; 64];
        let result = project(&mesh, &derivative, &initial, &b).unwrap();
        let residual = subtract(&c.apply(&result).unwrap(), &b);
        assert!(inner(&residual, &residual).sqrt() / inner(&b, &b).sqrt() > 1e-3);
        let normal = c.transpose(&residual);
        let rhs = c.transpose(&b);
        assert!(inner(&normal, &normal).sqrt() / inner(&rhs, &rhs).sqrt() < 1e-9);
        assert!(project(&mesh, &derivative, &initial[..63], &b).is_err());
        assert!(project(&mesh, &derivative, &initial, &vec![[f64::NAN; 3]; 64]).is_err());
    }

    #[test]
    fn quadratic_curl_transpose_and_manufactured_rate() {
        // ny=4 includes repeated cell IDs at distinct periodic images in a
        // double stencil. The transpose and diagonal must combine those entries.
        let mesh = Mesh::lattice(16, 4, [2., 0.125], 0.15).unwrap();
        let derivative = Derivatives::quadratic(&mesh).unwrap();
        let curl = Curl {
            mesh: &mesh,
            derivative: &derivative,
        };
        let a: Vec<Vec3> = (0..64)
            .map(|i| std::array::from_fn(|k| (i as f64 * 1.37 + k as f64).sin()))
            .collect();
        let b: Vec<Vec3> = (0..64)
            .map(|i| std::array::from_fn(|k| (i as f64 * 0.73 + k as f64).cos()))
            .collect();
        let target = curl.apply(&a).unwrap();
        let left: f64 = target
            .iter()
            .zip(&b)
            .zip(&mesh.cells)
            .map(|((a, b), c)| c.volume * dot(*a, *b))
            .sum();
        let right = inner(&a, &curl.transpose(&b));
        assert!((left - right).abs() < 1e-12 * (1. + left.abs()));
        let result = project(&mesh, &derivative, &vec![[0.; 3]; 64], &target).unwrap();
        let error = subtract(&curl.apply(&result).unwrap(), &target);
        assert!(inner(&error, &error).sqrt() / inner(&target, &target).sqrt() < 1e-8);
    }
}
