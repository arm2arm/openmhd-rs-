//! Experimental double-neighbour quadratic derivative; no change to default LS.
//! See the prospective contract in docs/M1_SHOCK_INVESTIGATION.md.
use super::{DerivativeSample, Derivatives, Mesh, Vec2};
use std::collections::BTreeSet;

fn neighbours(mesh: &Mesh, i: usize) -> Vec<(usize, [i32; 2])> {
    mesh.cells[i]
        .faces
        .iter()
        .map(|&(f, _)| {
            let face = &mesh.faces[f];
            if face.left == i {
                (face.right, face.image)
            } else {
                (face.left, face.image.map(|v| -v))
            }
        })
        .collect()
}

fn samples(mesh: &Mesh, i: usize) -> Vec<(usize, Vec2)> {
    let mut images = BTreeSet::new();
    for (j, image) in neighbours(mesh, i) {
        images.insert((j, image));
        for (k, next) in neighbours(mesh, j) {
            images.insert((k, [image[0] + next[0], image[1] + next[1]]));
        }
    }
    images.remove(&(i, [0; 2]));
    images
        .into_iter()
        .map(|(j, image)| {
            (
                j,
                std::array::from_fn(|k| {
                    mesh.cells[j].centroid[k] + f64::from(image[k]) * mesh.lengths[k]
                        - mesh.cells[i].centroid[k]
                }),
            )
        })
        .collect()
}

fn basis(d: Vec2) -> [f64; 6] {
    let [x, y] = d;
    [1., x, y, 0.5 * x * x, 0.5 * y * y, x * y]
}

fn fit(data: &[(usize, Vec2)], h: f64) -> Result<(Vec<DerivativeSample>, f64), String> {
    if data.len() < 6 || !h.is_finite() || h <= 0. {
        return Err("insufficient quadratic derivative samples/scale".into());
    }
    let roots = data
        .iter()
        .map(|(_, d)| 1. / d[0].hypot(d[1]).sqrt())
        .collect::<Vec<_>>();
    let design = data
        .iter()
        .zip(&roots)
        .map(|((_, d), w)| basis(d.map(|x| x / h)).map(|x| x * w))
        .collect::<Vec<_>>();
    let scales: [f64; 6] =
        std::array::from_fn(|k| design.iter().map(|r| r[k] * r[k]).sum::<f64>().sqrt());
    if scales.iter().any(|s| !s.is_finite() || *s <= 0.) {
        return Err("invalid quadratic design matrix".into());
    }
    let mut q: Vec<Vec<f64>> = Vec::new();
    let mut r = [[0.; 6]; 6];
    for k in 0..6 {
        let mut column = design
            .iter()
            .map(|row| row[k] / scales[k])
            .collect::<Vec<_>>();
        // Reorthogonalization avoids squaring the conditioning in normal equations.
        for _ in 0..2 {
            for j in 0..k {
                let product: f64 = column.iter().zip(&q[j]).map(|(x, y)| x * y).sum();
                r[j][k] += product;
                for (value, previous) in column.iter_mut().zip(&q[j]) {
                    *value -= product * previous;
                }
            }
        }
        r[k][k] = column.iter().map(|v| v * v).sum::<f64>().sqrt();
        if !r[k][k].is_finite() || r[k][k] < 1e-10 {
            return Err("rank-deficient quadratic derivative stencil".into());
        }
        q.push(column.iter().map(|v| v / r[k][k]).collect());
    }
    let mut inverse = [[0.; 6]; 6];
    for column in 0..6 {
        for i in (0..6).rev() {
            let rhs = f64::from(i == column)
                - ((i + 1)..6)
                    .map(|j| r[i][j] * inverse[j][column])
                    .sum::<f64>();
            inverse[i][column] = rhs / r[i][i];
        }
    }
    let norm = |a: &[[f64; 6]; 6]| {
        (0..6)
            .map(|j| a.iter().map(|row| row[j].abs()).sum::<f64>())
            .fold(0., f64::max)
    };
    let condition = norm(&r) * norm(&inverse);
    if !condition.is_finite() || condition > 1e8 {
        return Err("ill-conditioned quadratic derivative stencil".into());
    }
    let result = data
        .iter()
        .enumerate()
        .map(|(j, &(index, _))| DerivativeSample {
            index,
            weight: std::array::from_fn(|k| {
                (0..6).map(|l| inverse[k + 1][l] * q[l][j]).sum::<f64>() * roots[j]
                    / (scales[k + 1] * h)
            }),
        })
        .collect();
    Ok((result, condition))
}

impl Derivatives {
    /// Experimental first derivatives of a free quadratic double-stencil fit.
    /// Inverse-distance weights; worst_condition is cond_1(R) of column-scaled QR.
    /// Periodic images are distinct samples even when they share a cell index.
    pub fn quadratic(mesh: &Mesh) -> Result<Self, String> {
        mesh.validate()?;
        let mut stencils = Vec::with_capacity(mesh.cells.len());
        let mut worst_condition = 0.0_f64;
        for (i, cell) in mesh.cells.iter().enumerate() {
            let (row, condition) =
                fit(&samples(mesh, i), cell.volume.sqrt()).map_err(|e| format!("cell {i}: {e}"))?;
            stencils.push(row);
            worst_condition = worst_condition.max(condition);
        }
        Ok(Self {
            samples: stencils,
            worst_condition,
            input_len: mesh.cells.len(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f64::consts::TAU;

    #[test]
    fn polynomial_reproduction_including_periodic_images_and_thin_mesh() {
        for (nx, ny, lengths) in [(8, 8, [1.; 2]), (64, 4, [2., 0.125])] {
            for jitter in [0., 0.15] {
                let mesh = Mesh::lattice(nx, ny, lengths, jitter).unwrap();
                let operator = Derivatives::quadratic(&mesh).unwrap();
                assert!(
                    operator
                        .gradient(&vec![0.7; nx * ny])
                        .unwrap()
                        .iter()
                        .all(|g| *g == [0.; 2])
                );
                for i in 0..nx * ny {
                    let data = samples(&mesh, i);
                    let h = mesh.cells[i].volume.sqrt();
                    for monomial in 0..6 {
                        let values = data
                            .iter()
                            .map(|(_, d)| basis(d.map(|x| x / h))[monomial])
                            .collect::<Vec<_>>();
                        for k in 0..2 {
                            let actual: f64 = operator.samples[i]
                                .iter()
                                .zip(&values)
                                .map(|(s, value)| s.weight[k] * (value - values[0]) * h)
                                .sum();
                            let expected = f64::from(monomial == k + 1);
                            assert!(
                                (actual - expected).abs() < 1e-11,
                                "cell {i}, basis {monomial}, derivative {k}: {actual}"
                            );
                        }
                    }
                }
            }
        }
        let collinear: Vec<_> = (0..8).map(|i| (i, [i as f64 + 1., 0.])).collect();
        assert!(fit(&collinear, 1.).is_err());
    }

    #[test]
    fn smooth_periodic_two_dimensional_gradient_converges() {
        let mut errors = Vec::new();
        for n in [12, 24, 48] {
            let mesh = Mesh::lattice(n, n, [1.; 2], 0.15).unwrap();
            let operator = Derivatives::quadratic(&mesh).unwrap();
            let values: Vec<_> = mesh
                .cells
                .iter()
                .map(|c| (TAU * c.centroid[0]).sin() * (TAU * c.centroid[1]).cos())
                .collect();
            let result = operator.gradient(&values).unwrap();
            let error: f64 = mesh
                .cells
                .iter()
                .zip(result)
                .map(|(c, g)| {
                    let [x, y] = c.centroid.map(|v| TAU * v);
                    c.volume
                        * ((g[0] - TAU * x.cos() * y.cos()).powi(2)
                            + (g[1] + TAU * x.sin() * y.sin()).powi(2))
                })
                .sum::<f64>()
                .sqrt();
            errors.push(error);
        }
        for e in errors.windows(2) {
            assert!(e[0] / e[1] > 3.3, "{errors:?}");
        }
    }
}
