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

pub(crate) fn samples(mesh: &Mesh, i: usize) -> Vec<(usize, Vec2)> {
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

#[derive(Clone, Debug)]
struct HessianSample {
    index: usize,
    weight: [f64; 3],
}
struct Fit {
    gradient: Vec<DerivativeSample>,
    hessian: Vec<HessianSample>,
    condition: f64,
}
fn fit(data: &[(usize, Vec2)], h: f64) -> Result<Fit, String> {
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
    let gradient = data
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
    let hessian = data
        .iter()
        .enumerate()
        .map(|(j, &(index, _))| HessianSample {
            index,
            weight: std::array::from_fn(|k| {
                (0..6).map(|l| inverse[k + 3][l] * q[l][j]).sum::<f64>() * roots[j]
                    / (scales[k + 3] * h * h)
            }),
        })
        .collect();
    Ok(Fit {
        gradient,
        hessian,
        condition,
    })
}

/// Second derivatives [xx, yy, xy] of the same free quadratic fit.
/// Periodic images and baseline subtraction follow the first-derivative operator.
/// Its trace is NOT a negative-semidefinite diffusion operator: even a regular
/// mesh has amplifying high-frequency modes. See the Fourier-symbol test.
#[derive(Clone, Debug)]
pub struct QuadraticHessians {
    samples: Vec<Vec<HessianSample>>,
    pub worst_condition: f64,
}
impl QuadraticHessians {
    /// Upper bound on the infinity norm of the discrete Hessian trace.
    /// Includes baseline subtraction and repeated periodic samples.
    pub fn laplacian_norm_bound(&self) -> f64 {
        self.samples
            .iter()
            .map(|row| {
                2. * row
                    .iter()
                    .map(|s| (s.weight[0] + s.weight[1]).abs())
                    .sum::<f64>()
            })
            .fold(0., f64::max)
    }
    pub fn build(mesh: &Mesh) -> Result<Self, String> {
        mesh.validate()?;
        let mut result = Self {
            samples: Vec::with_capacity(mesh.cells.len()),
            worst_condition: 0.,
        };
        for (i, cell) in mesh.cells.iter().enumerate() {
            let fit =
                fit(&samples(mesh, i), cell.volume.sqrt()).map_err(|e| format!("cell {i}: {e}"))?;
            result.worst_condition = result.worst_condition.max(fit.condition);
            result.samples.push(fit.hessian);
        }
        Ok(result)
    }
    pub fn evaluate(&self, values: &[f64]) -> Result<Vec<[f64; 3]>, String> {
        if values.len() != self.samples.len() || !values.iter().all(|v| v.is_finite()) {
            return Err("Hessian requires finite cell values of matching length".into());
        }
        let result: Vec<[f64; 3]> = self
            .samples
            .iter()
            .map(|row| {
                std::array::from_fn(|k| {
                    row.iter()
                        .map(|s| s.weight[k] * (values[s.index] - values[row[0].index]))
                        .sum()
                })
            })
            .collect();
        if !result.iter().flatten().all(|v| v.is_finite()) {
            return Err("Hessian arithmetic overflow".into());
        }
        Ok(result)
    }
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
            let row =
                fit(&samples(mesh, i), cell.volume.sqrt()).map_err(|e| format!("cell {i}: {e}"))?;
            stencils.push(row.gradient);
            worst_condition = worst_condition.max(row.condition);
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
    fn trace_fourier_symbol_has_amplifying_short_modes() {
        let n = 16;
        let mesh = Mesh::lattice(n, n, [1.; 2], 0.).unwrap();
        let hessian = QuadraticHessians::build(&mesh).unwrap();
        let linear = Derivatives::build(&mesh, false).unwrap();
        // Independent symbol of the 12-point inverse-distance free fit:
        // lambda*h^2 = (2/3)*(cos(2 theta)-cos(theta)) for x-only modes.
        // It changes sign at theta=2*pi/3; consistency alone is insufficient.
        for k in [1., 6.] {
            let theta = TAU * k / n as f64;
            let lambda = (2. / 3.) * ((2. * theta).cos() - theta.cos()) * (n * n) as f64;
            let a: Vec<_> = mesh
                .cells
                .iter()
                .map(|c| (TAU * k * c.centroid[0]).sin())
                .collect();
            let lap: Vec<_> = hessian
                .evaluate(&a)
                .unwrap()
                .iter()
                .map(|h| h[0] + h[1])
                .collect();
            for (&actual, &value) in lap.iter().zip(&a) {
                assert!((actual - lambda * value).abs() < 1e-10);
                assert!(actual.abs() <= hessian.laplacian_norm_bound());
            }
            let grad = linear.gradient(&a).unwrap();
            let dr = linear.gradient(&lap).unwrap();
            let energy_rate: f64 = mesh
                .cells
                .iter()
                .zip(grad)
                .zip(dr)
                .map(|((c, g), r)| c.volume * (g[0] * r[0] + g[1] * r[1]))
                .sum();
            assert_eq!(energy_rate.is_sign_positive(), k == 6.);
        }
    }

    #[test]
    fn hessians_reproduce_polynomials_on_periodic_and_thin_stencils() {
        for (nx, ny, lengths) in [(8, 8, [1.; 2]), (64, 4, [2., 0.125])] {
            for jitter in [0., 0.15] {
                let mesh = Mesh::lattice(nx, ny, lengths, jitter).unwrap();
                let operator = QuadraticHessians::build(&mesh).unwrap();
                assert!(
                    operator
                        .evaluate(&vec![0.7; nx * ny])
                        .unwrap()
                        .iter()
                        .all(|h| *h == [0.; 3])
                );
                assert!(operator.evaluate(&[]).is_err());
                for i in 0..nx * ny {
                    let data = samples(&mesh, i);
                    let h = mesh.cells[i].volume.sqrt();
                    for monomial in 0..6 {
                        let values: Vec<_> = data
                            .iter()
                            .map(|(_, d)| basis(d.map(|x| x / h))[monomial])
                            .collect();
                        for k in 0..3 {
                            let actual: f64 = operator.samples[i]
                                .iter()
                                .zip(&values)
                                .map(|(s, v)| s.weight[k] * (v - values[0]) * h * h)
                                .sum();
                            assert!(
                                (actual - f64::from(monomial == k + 3)).abs() < 1e-11,
                                "{nx} {jitter} {i} {monomial} {k}: {actual}"
                            );
                        }
                    }
                }
            }
        }
    }

    #[test]
    fn smooth_two_dimensional_hessians_converge() {
        let mut errors = Vec::new();
        for n in [12, 24, 48] {
            let mesh = Mesh::lattice(n, n, [1.; 2], 0.15).unwrap();
            let potential: Vec<_> = mesh
                .cells
                .iter()
                .map(|c| (TAU * c.centroid[0]).sin() * (TAU * c.centroid[1]).cos())
                .collect();
            let measured = QuadraticHessians::build(&mesh)
                .unwrap()
                .evaluate(&potential)
                .unwrap();
            let error = mesh
                .cells
                .iter()
                .zip(&potential)
                .zip(&measured)
                .map(|((c, a), h)| {
                    let exact = [
                        -TAU * TAU * a,
                        -TAU * TAU * a,
                        -TAU * TAU * (TAU * c.centroid[0]).cos() * (TAU * c.centroid[1]).sin(),
                    ];
                    c.volume * (0..3).map(|k| (h[k] - exact[k]).powi(2)).sum::<f64>()
                })
                .sum::<f64>()
                .sqrt();
            errors.push(error);
        }
        eprintln!("Hessian L2 ladder: {errors:?}");
        assert!(errors.windows(2).all(|e| e[0] / e[1] > 1.8), "{errors:?}");
    }

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
