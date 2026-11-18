//! Optional free-intercept quadratic fit on direct and second-ring neighbours.
//! Inverse-distance weights and pivoted, twice-orthogonalized modified Gram-Schmidt.
use super::{Derivatives, Mesh, Vec2};
use std::collections::BTreeSet;
/// Quadratic Taylor term for Hessian components [xx, yy, xy].
pub fn term(h: [f64; 3], d: Vec2) -> f64 {
    0.5 * h[0] * d[0] * d[0] + h[2] * d[0] * d[1] + 0.5 * h[1] * d[1] * d[1]
}
#[derive(Clone, Debug)]
pub(crate) struct Sample {
    pub(crate) index: usize,
    pub(crate) coefficient: [f64; 6],
}
#[derive(Clone, Debug)]
pub struct Quadratic {
    pub(crate) samples: Vec<Vec<Sample>>,
    pub worst_condition: f64,
}
#[derive(Clone, Copy, Debug)]
pub struct QuadraticJet {
    pub intercept: f64,
    pub gradient: Vec2,
    pub hessian: [f64; 3],
}
/// Direct-neighbour derivative with its quadratic Taylor moment removed.
/// The Hessian still uses the two-ring fit. No general stability is implied.
#[derive(Clone, Debug)]
pub struct Compact {
    pub(crate) moments: Vec<[[f64; 3]; 2]>,
}
impl Compact {
    pub fn build(mesh: &Mesh, linear: &Derivatives) -> Result<Self, String> {
        mesh.validate()?;
        if linear.samples.len() != mesh.cells.len() {
            return Err("compact derivative shape mismatch".into());
        }
        let mut moments = Vec::with_capacity(mesh.cells.len());
        for (i, cell) in mesh.cells.iter().enumerate() {
            let samples = &linear.samples[i];
            if samples.len() != cell.faces.len() || samples.is_empty() {
                return Err("compact derivative needs face-ordered neighbour samples".into());
            }
            let basis = |d: Vec2| [0.5 * d[0] * d[0], 0.5 * d[1] * d[1], d[0] * d[1]];
            let baseline = basis(mesh.neighbour(&mesh.faces[cell.faces[0].0], i).1);
            let mut moment = [[0.; 3]; 2];
            for (sample, &(f, _)) in samples.iter().zip(&cell.faces) {
                let (j, d) = mesh.neighbour(&mesh.faces[f], i);
                if sample.index != j {
                    return Err("compact derivative sample order mismatch".into());
                }
                let q = basis(d);
                for (axis, out) in moment.iter_mut().enumerate() {
                    for k in 0..3 {
                        out[k] += sample.weight[axis] * (q[k] - baseline[k]);
                    }
                }
            }
            if !moment.iter().flatten().all(|v| v.is_finite()) {
                return Err("compact derivative moment overflow".into());
            }
            moments.push(moment);
        }
        Ok(Self { moments })
    }
    /// Keep the quadratic Hessian/intercept; replace only the gradient.
    pub fn jets(
        &self,
        linear: &Derivatives,
        quadratic: &Quadratic,
        values: &[f64],
    ) -> Result<Vec<QuadraticJet>, String> {
        let mut jets = quadratic.jets(values)?;
        let gradients = linear.gradient(values)?;
        if jets.len() != self.moments.len() || gradients.len() != jets.len() {
            return Err("compact derivative field shape mismatch".into());
        }
        for ((jet, gradient), moment) in jets.iter_mut().zip(gradients).zip(&self.moments) {
            jet.gradient = std::array::from_fn(|axis| {
                gradient[axis]
                    - (0..3)
                        .map(|k| moment[axis][k] * jet.hessian[k])
                        .sum::<f64>()
            });
            if !jet.gradient.iter().all(|v| v.is_finite()) {
                return Err("compact derivative arithmetic overflow".into());
            }
        }
        Ok(jets)
    }
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
        // Reorthogonalize against the entire existing basis, not only the most
        // recently removed column. Accumulate corrections into the same R.
        for _ in 0..2 {
            for j in 0..k {
                let correction = q.iter().map(|row| row[j] * row[k]).sum::<f64>();
                r[j][k] += correction;
                for row in &mut q {
                    row[k] -= correction * row[j];
                }
            }
        }
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
    fn compact_jets(mesh: &Mesh, values: &[f64]) -> Vec<QuadraticJet> {
        let l = Derivatives::build(mesh, false).unwrap();
        Compact::build(mesh, &l)
            .unwrap()
            .jets(&l, &Quadratic::build(mesh).unwrap(), values)
            .unwrap()
    }
    #[test]
    fn compact_rejects_malformed_geometry_and_sample_order() {
        let mesh = Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap();
        let linear = Derivatives::build(&mesh, false).unwrap();
        let mut bad = mesh.clone();
        bad.cells[0].faces[0].0 = bad.faces.len();
        assert!(Compact::build(&bad, &linear).is_err());
        let mut bad = mesh.clone();
        bad.faces[0].right = bad.cells.len();
        assert!(Compact::build(&bad, &linear).is_err());
        let mut reordered = linear.clone();
        reordered.samples[0].swap(0, 1);
        assert!(Compact::build(&mesh, &reordered).is_err());
    }
    #[test]
    fn compact_quadratics_constants_and_regular_reduction() {
        for jitter in [0., 0.15] {
            let mesh = Mesh::lattice(12, 12, [1.; 2], jitter).unwrap();
            let values: Vec<_> = mesh
                .cells
                .iter()
                .map(|c| {
                    let [x, y] = c.centroid;
                    2. + 3. * x - 4. * y + 0.7 * x * x - 0.2 * x * y + 0.9 * y * y
                })
                .collect();
            for (c, j) in mesh.cells.iter().zip(compact_jets(&mesh, &values)) {
                let [x, y] = c.centroid;
                if c.centroid.iter().all(|v| (0.25..0.75).contains(v)) {
                    assert!((j.gradient[0] - (3. + 1.4 * x - 0.2 * y)).abs() < 1e-11);
                    assert!((j.gradient[1] - (-4. - 0.2 * x + 1.8 * y)).abs() < 1e-11);
                }
            }
            assert!(
                compact_jets(&mesh, &vec![0.7; 144])
                    .iter()
                    .all(|j| j.gradient == [0.; 2] && j.hessian == [0.; 3])
            );
        }
        // Includes two periodic images with the same neighbour ID at nx=2.
        for (nx, ny) in [(2, 5), (8, 8)] {
            let points = (0..ny)
                .flat_map(|y| {
                    (0..nx)
                        .map(move |x| [(x as f64 + 0.5) / nx as f64, (y as f64 + 0.5) / ny as f64])
                })
                .collect();
            let mesh = Mesh::build(points, [1.; 2]).unwrap();
            let values: Vec<_> = mesh
                .cells
                .iter()
                .enumerate()
                .map(|(i, c)| {
                    (17. * c.centroid[0] + 31. * c.centroid[1]).sin() + 0.01 * (i as f64).cos()
                })
                .collect();
            let linear = Derivatives::build(&mesh, false)
                .unwrap()
                .gradient(&values)
                .unwrap();
            for (j, g) in compact_jets(&mesh, &values).iter().zip(linear) {
                assert!(
                    (j.gradient[0] - g[0]).abs() < 1e-11 && (j.gradient[1] - g[1]).abs() < 1e-11
                );
            }
        }
    }
    #[test]
    fn compact_periodic_images_and_id_permutation() {
        let mesh = Mesh::lattice(9, 7, [1.3, 0.7], 0.15).unwrap();
        let other = Mesh::build(
            mesh.generators.iter().rev().copied().collect(),
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
        let a = compact_jets(&mesh, &field(&mesh));
        let b = compact_jets(&other, &field(&other));
        for (x, y) in a.iter().zip(b.iter().rev()) {
            for (x, y) in x
                .gradient
                .iter()
                .chain(&x.hessian)
                .zip(y.gradient.iter().chain(&y.hessian))
            {
                assert!((x - y).abs() < 1e-10 * (1. + x.abs() + y.abs()));
            }
        }
    }
    #[test]
    fn compact_smooth_periodic_gradient_refines() {
        let mut errors = Vec::new();
        for n in [12, 24, 48] {
            let mesh = Mesh::lattice(n, n, [1.; 2], 0.15).unwrap();
            let k = std::f64::consts::TAU;
            let values: Vec<_> = mesh
                .cells
                .iter()
                .map(|c| (k * c.centroid[0]).sin() * (k * c.centroid[1]).cos())
                .collect();
            let err = mesh
                .cells
                .iter()
                .zip(compact_jets(&mesh, &values))
                .map(|(c, j)| {
                    let [x, y] = c.centroid;
                    c.volume
                        * (j.gradient[0] - k * (k * x).cos() * (k * y).cos())
                            .hypot(j.gradient[1] + k * (k * x).sin() * (k * y).sin())
                })
                .sum::<f64>();
            errors.push(err);
        }
        assert!(
            errors[2] < 0.3 * errors[1] && errors[1] < 0.3 * errors[0],
            "{errors:?}"
        );
    }
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
    fn accepted_nearly_collinear_polynomial_retains_condition_scaled_accuracy() {
        let data: Vec<Vec<f64>> = include_str!("../tests/data/quadratic_ill_conditioned.txt")
            .lines()
            .map(|line| {
                line.split_whitespace()
                    .map(|v| v.parse().unwrap())
                    .collect()
            })
            .collect();
        let rows: Vec<[f64; 6]> = data.iter().map(|r| r[..6].try_into().unwrap()).collect();
        let values: Vec<_> = data.iter().map(|r| r[6]).collect();
        let (weights, condition) = factor(&rows).unwrap();
        assert!(condition > 1e8 && condition < 1e9);
        let expected = [0.2, 0.3, -0.4, 0.7, 0.9, -0.2];
        for (k, want) in expected.iter().enumerate() {
            let value = weights
                .iter()
                .zip(&values)
                .map(|(row, v)| row[k] * (v - values[0]))
                .sum::<f64>()
                + if k == 0 { values[0] } else { 0. };
            assert!(
                (value - want).abs() < 4. * condition * f64::EPSILON * (1. + want.abs()),
                "k={k}, got={value:e}, expected={want:e}, indicator={condition:e}"
            );
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
