//! Experimental weighted projection of a magnetic rate onto the planar curl range.
//! See docs/M1_SHOCK_INVESTIGATION.md: this is a nonlocal engineering comparator,
//! not the paper algorithm or a positivity guarantee. It changes A rates only.
//! C = (Dy Az, -Dx Az, Dx Ay-Dy Ax); solve C^T V C delta = C^T V(target-C rate).
//! Opt-in screening kappa > 0 solves (C^T V C + kappa D) delta = rhs, with D the
//! Jacobi diagonal: a damped, more local correction, no longer the exact
//! least-squares projection. kappa = 0 is the original algorithm.
use faer::{
    Mat, Side,
    linalg::solvers::Solve,
    sparse::{SparseColMat, Triplet, linalg::solvers::Llt},
};
use mhd_core::{Vec3, dot};
use moving_mesh::{Derivatives, Mesh, Vec2};
use std::{borrow::Cow, collections::BTreeMap};

const PRECONDITIONER_SHIFT: f64 = 1e-8;

/// Optional cached factorization of H+sigma*D, used only to precondition H.
/// Original normal equations, residual criteria and Jacobi-gauge metric remain.
#[derive(Debug)]
pub(crate) struct Preconditioner {
    factor: Llt<usize, f64>,
    cells: usize,
    /// Actual coefficient of D in the factored matrix, for execution provenance.
    pub(crate) shift: f64,
    // The same immutable geometry metric as the cached factorization. Rebuilding
    // its sparse rows at every Heun stage does not change these coefficients.
    diagonal: Vec<Vec3>,
}
impl Preconditioner {
    fn matrix(
        mesh: &Mesh,
        derivative: &Derivatives,
        shift: f64,
    ) -> Result<SparseColMat<usize, f64>, String> {
        let n = mesh.cells.len();
        let mut entries = Vec::new();
        for (i, samples) in derivative.samples.iter().enumerate() {
            let mut row: BTreeMap<usize, Vec2> = BTreeMap::new();
            for s in samples {
                for k in 0..2 {
                    row.entry(s.index).or_default()[k] += s.weight[k];
                    row.entry(samples[0].index).or_default()[k] -= s.weight[k];
                }
            }
            let x: Vec<_> = row.iter().map(|(&j, d)| (3 * j + 2, d[1])).collect();
            let y: Vec<_> = row.iter().map(|(&j, d)| (3 * j + 2, -d[0])).collect();
            let z: Vec<_> = row
                .iter()
                .flat_map(|(&j, d)| [(3 * j, -d[1]), (3 * j + 1, d[0])])
                .collect();
            for component in [x, y, z] {
                for &(j, a) in &component {
                    for &(k, b) in &component {
                        if j >= k && a != 0. && b != 0. {
                            entries.push(Triplet::new(j, k, mesh.cells[i].volume * a * b));
                        }
                    }
                }
            }
        }
        for (i, d) in (Curl { mesh, derivative }).diagonal().iter().enumerate() {
            for (k, &d) in d.iter().enumerate() {
                if !d.is_finite() || d <= 0. {
                    return Err("invalid cached projection diagonal".into());
                }
                entries.push(Triplet::new(3 * i + k, 3 * i + k, shift * d));
            }
        }
        SparseColMat::try_new_from_triplets(3 * n, 3 * n, &entries)
            .map_err(|e| format!("projection matrix: {e:?}"))
    }
    /// `screening = 0` factors the original H + 1e-8 D preconditioner. A positive
    /// screening factors the screened operator H + screening D itself.
    pub fn build(mesh: &Mesh, derivative: &Derivatives, screening: f64) -> Result<Self, String> {
        if !screening.is_finite() || screening < 0. {
            return Err("projection screening must be finite and nonnegative".into());
        }
        let shift = if screening > 0. {
            screening
        } else {
            PRECONDITIONER_SHIFT
        };
        let matrix = Self::matrix(mesh, derivative, shift)?;
        // faer's rayon feature is disabled: no nested worker pool or FFI.
        let factor = matrix
            .sp_cholesky(Side::Lower)
            .map_err(|e| format!("projection preconditioner: {e:?}"))?;
        Ok(Self {
            factor,
            cells: mesh.cells.len(),
            shift,
            diagonal: (Curl { mesh, derivative }).diagonal(),
        })
    }
    fn apply(&self, r: &[Vec3]) -> Result<Vec<Vec3>, String> {
        if r.len() != self.cells {
            return Err("cached projection size mismatch".into());
        }
        let rhs = Mat::from_fn(3 * r.len(), 1, |i, _| r[i / 3][i % 3]);
        let solved = self.factor.solve(&rhs);
        let result: Vec<Vec3> = (0..r.len())
            .map(|i| std::array::from_fn(|k| solved[(3 * i + k, 0)]))
            .collect();
        if result.iter().flatten().any(|v| !v.is_finite()) {
            return Err("nonfinite projection preconditioner solve".into());
        }
        Ok(result)
    }
}

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
#[cfg(test)]
pub(crate) fn project(
    mesh: &Mesh,
    derivative: &Derivatives,
    initial: &[Vec3],
    target: &[Vec3],
) -> Result<Vec<Vec3>, String> {
    project_with_preconditioner(mesh, derivative, initial, target, None, 0.)
}

pub(crate) fn project_with_preconditioner(
    mesh: &Mesh,
    derivative: &Derivatives,
    initial: &[Vec3],
    target: &[Vec3],
    cached: Option<&Preconditioner>,
    screening: f64,
) -> Result<Vec<Vec3>, String> {
    if !screening.is_finite() || screening < 0. {
        return Err("projection screening must be finite and nonnegative".into());
    }
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
    let diagonal: Cow<'_, [Vec3]> = if let Some(p) = cached {
        Cow::Borrowed(&p.diagonal)
    } else {
        Cow::Owned(curl.diagonal())
    };
    if diagonal
        .iter()
        .flatten()
        .any(|d| !d.is_finite() || *d <= 0.)
    {
        return Err("invalid projected-rate diagonal".into());
    }
    let precondition = |r: &[Vec3]| -> Result<Vec<Vec3>, String> {
        if let Some(p) = cached {
            return p.apply(r);
        }
        Ok(r.iter()
            .zip(diagonal.iter())
            .map(|(r, d)| std::array::from_fn(|k| r[k] / d[k]))
            .collect::<Vec<Vec3>>())
    };
    // Screened normal operator; the unscreened branch is the original arithmetic.
    let normal = |x: &[Vec3]| -> Result<Vec<Vec3>, String> {
        let mut y = curl.transpose(&curl.apply(x)?);
        if screening > 0. {
            for i in 0..y.len() {
                for k in 0..3 {
                    y[i][k] += screening * diagonal[i][k] * x[i][k];
                }
            }
        }
        Ok(y)
    };
    let mut delta = vec![[0.; 3]; initial.len()];
    let mut r = rhs.clone();
    let mut z = precondition(&r)?;
    let mut direction = z.clone();
    let mut rz = inner(&r, &z);
    // There are 3N scalar unknowns. Start the correction at zero without an
    // explicit gauge constraint; stop on the magnetic-rate normal residual.
    for _ in 0..24 * initial.len() {
        let applied = normal(&direction)?;
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
            let true_applied = normal(&delta)?;
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
        z = precondition(&r)?;
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
    fn cached_matrix_and_projection_preserve_original_equations_and_gauge_metric() {
        for jitter in [0., 0.15] {
            let mesh = Mesh::lattice(8, 8, [1.; 2], jitter).unwrap();
            for quadratic in [false, true] {
                let derivative = if quadratic {
                    Derivatives::quadratic(&mesh).unwrap()
                } else {
                    Derivatives::build(&mesh, false).unwrap()
                };
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
                let matrix = Preconditioner::matrix(&mesh, &derivative, PRECONDITIONER_SHIFT)
                    .unwrap()
                    .to_dense();
                let exact = curl.transpose(&curl.apply(&a).unwrap());
                let diagonal = curl.diagonal();
                for i in 0..192 {
                    let measured: f64 = (0..192)
                        .map(|j| matrix[(i.max(j), i.min(j))] * a[j / 3][j % 3])
                        .sum();
                    let expected = exact[i / 3][i % 3]
                        + PRECONDITIONER_SHIFT * diagonal[i / 3][i % 3] * a[i / 3][i % 3];
                    assert!((measured - expected).abs() < 2e-11 * (1. + expected.abs()));
                }
                let cached = Preconditioner::build(&mesh, &derivative, 0.).unwrap();
                assert_eq!(cached.diagonal, diagonal);
                for target in [curl.apply(&b).unwrap(), b.clone()] {
                    let old = project(&mesh, &derivative, &a, &target).unwrap();
                    let new = project_with_preconditioner(
                        &mesh,
                        &derivative,
                        &a,
                        &target,
                        Some(&cached),
                        0.,
                    )
                    .unwrap();
                    let error = subtract(&new, &old);
                    // In D-scaled coordinates both zero-start Krylov spaces
                    // exclude the same nullspace. Check A, not just curl(A).
                    let relative = (inner(&error, &error) / (1. + inner(&old, &old))).sqrt();
                    assert!(relative < 1e-6, "gauge-sensitive A difference {relative}");
                    let magnetic = curl.apply(&error).unwrap();
                    assert!(
                        (inner(&magnetic, &magnetic) / (1. + inner(&target, &target))).sqrt()
                            < 1e-8
                    );
                }
                assert!(cached.apply(&a[..63]).is_err());
            }
        }
    }
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
    fn screening_solves_the_damped_system_and_shrinks_the_correction() {
        let mesh = Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap();
        let derivative = Derivatives::build(&mesh, false).unwrap();
        let curl = Curl {
            mesh: &mesh,
            derivative: &derivative,
        };
        let zero = vec![[0.; 3]; 64];
        // Not in the curl range: an incompatible magnetic-rate target.
        let target: Vec<Vec3> = mesh
            .cells
            .iter()
            .map(|c| {
                let (x, y) = (
                    std::f64::consts::TAU * c.centroid[0],
                    std::f64::consts::TAU * c.centroid[1],
                );
                [y.sin() + 0.3 * x.cos(), (x + y).cos(), 0.2 * x.sin()]
            })
            .collect();
        let rhs = curl.transpose(&target);
        let diagonal = curl.diagonal();
        let norm = |v: &[Vec3]| inner(v, v).sqrt();
        let exact = project(&mesh, &derivative, &zero, &target).unwrap();
        let same = project_with_preconditioner(&mesh, &derivative, &zero, &target, None, 0.);
        assert_eq!(exact, same.unwrap());
        let mut previous = norm(&exact);
        for kappa in [0.1, 1.] {
            let jacobi =
                project_with_preconditioner(&mesh, &derivative, &zero, &target, None, kappa)
                    .unwrap();
            let mut applied = curl.transpose(&curl.apply(&jacobi).unwrap());
            for i in 0..64 {
                for k in 0..3 {
                    applied[i][k] += kappa * diagonal[i][k] * jacobi[i][k];
                }
            }
            assert!(norm(&subtract(&applied, &rhs)) < 1e-9 * norm(&rhs));
            let cached = Preconditioner::build(&mesh, &derivative, kappa).unwrap();
            assert_eq!(cached.diagonal, diagonal);
            let direct = project_with_preconditioner(
                &mesh,
                &derivative,
                &zero,
                &target,
                Some(&cached),
                kappa,
            )
            .unwrap();
            assert!(norm(&subtract(&direct, &jacobi)) < 1e-8 * norm(&jacobi));
            // Stronger screening gives a strictly smaller correction.
            assert!(norm(&jacobi) < previous);
            previous = norm(&jacobi);
        }
        for bad in [-1., f64::NAN] {
            assert!(
                project_with_preconditioner(&mesh, &derivative, &zero, &target, None, bad).is_err()
            );
            assert!(Preconditioner::build(&mesh, &derivative, bad).is_err());
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
