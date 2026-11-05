//! Optional free-intercept quadratic fit on direct and second-ring neighbours.
//! Inverse-distance weights and pivoted, twice-orthogonalized modified Gram-Schmidt.
use super::{Mesh, Vec2};
use std::collections::BTreeSet;
#[derive(Clone, Debug)]
struct Sample {
    index: usize,
    coefficient: [f64; 6],
}
#[derive(Clone, Debug)]
pub struct Quadratic {
    samples: Vec<Vec<Sample>>,
    pub worst_condition: f64,
}
#[derive(Clone, Copy, Debug)]
pub struct QuadraticJet {
    pub intercept: f64,
    pub gradient: Vec2,
    pub hessian: [f64; 3],
}
impl Quadratic {
    pub fn build(mesh: &Mesh) -> Result<Self, String> {
        mesh.validate()?;
        let mut samples = Vec::with_capacity(mesh.cells.len());
        let mut worst_condition: f64 = 0.;
        for (i, c) in mesh.cells.iter().enumerate() {
            let mut ids = BTreeSet::new();
            for &(f, _) in &c.faces {
                let face = &mesh.faces[f];
                let (j, _) = mesh.neighbour(face, i);
                let sign = if face.left == i { 1 } else { -1 };
                let image = face.image.map(|x| sign * x);
                ids.insert((j, image));
                for &(g, _) in &mesh.cells[j].faces {
                    let other = &mesh.faces[g];
                    let (k, _) = mesh.neighbour(other, j);
                    let s = if other.left == j { 1 } else { -1 };
                    ids.insert((
                        k,
                        [image[0] + s * other.image[0], image[1] + s * other.image[1]],
                    ));
                }
            }
            ids.remove(&(i, [0, 0]));
            let h = c.volume.sqrt();
            let mut rows = Vec::new();
            let mut sqrt_weights = Vec::new();
            let mut indices = Vec::new();
            for (j, image) in ids {
                let d: Vec2 = std::array::from_fn(|k| {
                    (mesh.cells[j].centroid[k] - c.centroid[k]
                        + f64::from(image[k]) * mesh.lengths[k])
                        / h
                });
                let radius = d[0].hypot(d[1]);
                if !radius.is_finite() || radius <= 1e-12 {
                    return Err(format!("quadratic cell {i}: degenerate sample distance"));
                }
                let root = (1. / radius).sqrt();
                let [x, y] = d;
                rows.push([1., x, y, 0.5 * x * x, 0.5 * y * y, x * y].map(|v| root * v));
                sqrt_weights.push(root);
                indices.push(j);
            }
            let (coefficients, condition) = factor(&rows)?;
            worst_condition = worst_condition.max(condition);
            samples.push(
                coefficients
                    .into_iter()
                    .zip(indices)
                    .zip(sqrt_weights)
                    .map(|((mut coefficient, index), root)| {
                        for (k, v) in coefficient.iter_mut().enumerate() {
                            *v *= root
                                / if k == 0 {
                                    1.
                                } else if k < 3 {
                                    h
                                } else {
                                    h * h
                                };
                        }
                        Sample { index, coefficient }
                    })
                    .collect(),
            );
        }
        Ok(Self {
            samples,
            worst_condition,
        })
    }
    pub fn jets(&self, values: &[f64]) -> Result<Vec<QuadraticJet>, String> {
        if values.len() != self.samples.len() || !values.iter().all(|x| x.is_finite()) {
            return Err("invalid quadratic sample field".into());
        }
        self.samples
            .iter()
            .map(|samples| {
                let baseline = values[samples[0].index];
                let coefficients: [f64; 6] = std::array::from_fn(|k| {
                    samples
                        .iter()
                        .map(|s| s.coefficient[k] * (values[s.index] - baseline))
                        .sum()
                });
                if !coefficients.iter().all(|x| x.is_finite())
                    || !(coefficients[0] + baseline).is_finite()
                {
                    return Err("quadratic arithmetic overflow".into());
                }
                Ok(QuadraticJet {
                    intercept: baseline + coefficients[0],
                    gradient: [coefficients[1], coefficients[2]],
                    hessian: [coefficients[3], coefficients[4], coefficients[5]],
                })
            })
            .collect()
    }
}
fn factor(rows: &[[f64; 6]]) -> Result<(Vec<[f64; 6]>, f64), String> {
    if rows.len() < 6 || !rows.iter().flatten().all(|x| x.is_finite()) {
        return Err("quadratic stencil needs six finite samples".into());
    }
    let mut q = rows.to_vec();
    let mut r = [[0.; 6]; 6];
    let mut permutation = [0, 1, 2, 3, 4, 5];
    let mut largest: f64 = 0.;
    let mut smallest = f64::INFINITY;
    for k in 0..6 {
        let pivot = (k..6)
            .max_by(|&a, &b| {
                q.iter()
                    .map(|row| row[a] * row[a])
                    .sum::<f64>()
                    .total_cmp(&q.iter().map(|row| row[b] * row[b]).sum::<f64>())
            })
            .unwrap();
        for row in &mut q {
            row.swap(k, pivot);
        }
        for row in r.iter_mut().take(k) {
            row.swap(k, pivot);
        }
        permutation.swap(k, pivot);
        let norm = q.iter().map(|row| row[k] * row[k]).sum::<f64>().sqrt();
        largest = largest.max(norm);
        smallest = smallest.min(norm);
        if !norm.is_finite() || norm <= 1e-10 * largest {
            return Err("rank-deficient or ill-conditioned quadratic stencil".into());
        }
        r[k][k] = norm;
        for row in &mut q {
            row[k] /= norm;
        }
        for j in k + 1..6 {
            for _ in 0..2 {
                let projection = q.iter().map(|row| row[k] * row[j]).sum::<f64>();
                r[k][j] += projection;
                for row in &mut q {
                    row[j] -= projection * row[k];
                }
            }
        }
    }
    let coefficients = q
        .iter()
        .map(|row| {
            let mut solved = [0.; 6];
            for k in (0..6).rev() {
                solved[k] =
                    (row[k] - (k + 1..6).map(|j| r[k][j] * solved[j]).sum::<f64>()) / r[k][k];
            }
            let mut result = [0.; 6];
            for k in 0..6 {
                result[permutation[k]] = solved[k];
            }
            result
        })
        .collect();
    Ok((coefficients, largest / smallest))
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn quadratic_reproduction_constants_and_rank_rejection() {
        for jitter in [0., 0.15] {
            let mesh = Mesh::lattice(12, 12, [1.; 2], jitter).unwrap();
            let stencil = Quadratic::build(&mesh).unwrap();
            let values: Vec<_> = mesh
                .cells
                .iter()
                .map(|c| {
                    let [x, y] = c.centroid;
                    2. + 3. * x - 4. * y + 0.7 * x * x - 0.2 * x * y + 0.9 * y * y
                })
                .collect();
            for (c, j) in mesh.cells.iter().zip(stencil.jets(&values).unwrap()) {
                let [x, y] = c.centroid;
                if !(0.25..=0.75).contains(&x) || !(0.25..=0.75).contains(&y) {
                    continue;
                }
                for (a, b) in j.gradient.into_iter().chain(j.hessian).zip([
                    3. + 1.4 * x - 0.2 * y,
                    -4. - 0.2 * x + 1.8 * y,
                    1.4,
                    1.8,
                    -0.2,
                ]) {
                    assert!((a - b).abs() < 1e-10, "{a} {b}");
                }
            }
            assert!(
                stencil
                    .jets(&vec![0.7; 144])
                    .unwrap()
                    .iter()
                    .all(|j| j.gradient == [0.; 2] && j.hessian == [0.; 3])
            );
        }
        assert!(factor(&[[1., 0., 0., 0., 0., 0.]; 8]).is_err());
    }
    #[test]
    fn periodic_images_and_reversed_ids_preserve_jets() {
        let mesh = Mesh::lattice(9, 7, [1.3, 0.7], 0.15).unwrap();
        let perm: Vec<_> = (0..mesh.cells.len()).rev().collect();
        let other = Mesh::build(
            perm.iter().map(|&i| mesh.generators[i]).collect(),
            mesh.lengths,
        )
        .unwrap();
        let field = |m: &Mesh| {
            m.cells
                .iter()
                .map(|c| {
                    (std::f64::consts::TAU * c.centroid[0] / 1.3).sin()
                        * (std::f64::consts::TAU * c.centroid[1] / 0.7).cos()
                })
                .collect::<Vec<_>>()
        };
        let a = Quadratic::build(&mesh)
            .unwrap()
            .jets(&field(&mesh))
            .unwrap();
        let b = Quadratic::build(&other)
            .unwrap()
            .jets(&field(&other))
            .unwrap();
        for (j, &i) in perm.iter().enumerate() {
            for (x, y) in a[i]
                .gradient
                .iter()
                .chain(&a[i].hessian)
                .zip(b[j].gradient.iter().chain(&b[j].hessian))
            {
                assert!((x - y).abs() < 1e-10 * (1. + x.abs() + y.abs()));
            }
        }
    }
    #[test]
    fn smooth_periodic_gradient_converges_on_irregular_cells() {
        let mut errors = Vec::new();
        for n in [12, 24, 48] {
            let mesh = Mesh::lattice(n, n, [1.; 2], 0.15).unwrap();
            let stencil = Quadratic::build(&mesh).unwrap();
            let k = std::f64::consts::TAU;
            let values: Vec<_> = mesh
                .cells
                .iter()
                .map(|c| (k * c.centroid[0]).sin())
                .collect();
            errors.push(
                mesh.cells
                    .iter()
                    .zip(stencil.jets(&values).unwrap())
                    .map(|(c, j)| {
                        c.volume
                            * ((j.gradient[0] - k * (k * c.centroid[0]).cos()).hypot(j.gradient[1]))
                    })
                    .sum::<f64>(),
            );
        }
        assert!(
            errors[2] < 0.3 * errors[1] && errors[1] < 0.3 * errors[0],
            "{errors:?}"
        );
    }
}
