//! Continuous minimum-change projection of quadratic face reconstructions.
//! The metric and prospective experiment are specified in M1_COMPLETION_PLAN.md.
use crate::{Reconstruction, Vec2};
use std::f64::consts::SQRT_2;

pub type Coefficients = [f64; 5];

/// Half-space `normal dot value <= bound`; zero must be feasible.
#[derive(Clone, Copy, Debug)]
pub struct HalfSpace {
    pub normal: Coefficients,
    pub bound: f64,
}

#[derive(Clone, Debug)]
pub struct Projection {
    pub value: Coefficients,
    /// Nonnegative KKT multipliers in the original constraint normalization.
    pub multipliers: Vec<f64>,
    pub iterations: usize,
}

fn dot(a: Coefficients, b: Coefficients) -> f64 {
    a.iter().zip(b).map(|(a, b)| a * b).sum()
}
fn norm(a: Coefficients) -> f64 {
    a.into_iter().fold(0., f64::hypot)
}
const ROUND: f64 = 256. * f64::EPSILON;

/// Euclidean projection, using a feasible primal active set in at most five dimensions.
/// Working rows are independent; the complete set of tight constraints need not be.
/// Failure is explicit rather than substituting another limiter.
pub fn project(raw: Coefficients, constraints: &[HalfSpace]) -> Result<Projection, String> {
    if !raw.iter().all(|x| x.is_finite())
        || constraints.iter().any(|c| {
            !c.bound.is_finite() || c.bound < 0. || !c.normal.iter().all(|x| x.is_finite())
        })
    {
        return Err("projection requires finite coefficients and zero-feasible bounds".into());
    }
    let norms: Vec<_> = constraints.iter().map(|c| norm(c.normal)).collect();
    if norms.iter().any(|n| !n.is_finite() || *n == 0.) {
        return Err("projection requires nonzero finite constraint normals".into());
    }
    let scale = raw.iter().map(|v| v.abs()).fold(0., f64::max);
    if scale == 0. {
        return Ok(Projection {
            value: raw,
            multipliers: vec![0.; constraints.len()],
            iterations: 0,
        });
    }
    let target = raw.map(|v| v / scale);
    let rows: Vec<_> = constraints
        .iter()
        .zip(&norms)
        .map(|(c, n)| c.normal.map(|v| v / n))
        .collect();
    // A positive overflow here is an inactive, very distant bound, not an invalid input.
    let bounds: Vec<_> = constraints
        .iter()
        .zip(&norms)
        .map(|(c, n)| (c.bound / n.max(scale)) / n.min(scale))
        .collect();
    if rows.iter().zip(&bounds).all(|(&r, &b)| dot(r, target) <= b) {
        return Ok(Projection {
            value: raw,
            multipliers: vec![0.; constraints.len()],
            iterations: 0,
        });
    }
    let tolerance = ROUND * (1. + norm(target));
    let mut x = [0.; 5];
    let mut active: Vec<usize> = Vec::new();
    for iteration in 0..256 {
        let mut basis: Vec<Coefficients> = Vec::new();
        let mut lower = [[0.; 5]; 5];
        for (i, &index) in active.iter().enumerate() {
            let mut row = rows[index];
            for _ in 0..2 {
                for (j, &q) in basis.iter().enumerate() {
                    let amount = dot(row, q);
                    lower[i][j] += amount;
                    for k in 0..5 {
                        row[k] -= amount * q[k];
                    }
                }
            }
            let diagonal = norm(row);
            if diagonal <= ROUND || !diagonal.is_finite() {
                return Err("projection working constraints are numerically dependent".into());
            }
            lower[i][i] = diagonal;
            basis.push(row.map(|v| v / diagonal));
        }
        let residual: Coefficients = std::array::from_fn(|k| target[k] - x[k]);
        let mut direction = residual;
        for _ in 0..2 {
            for &q in &basis {
                let amount = dot(direction, q);
                for k in 0..5 {
                    direction[k] -= amount * q[k];
                }
            }
        }
        if norm(direction) <= tolerance {
            let mut lambda = vec![0.; active.len()];
            for i in (0..active.len()).rev() {
                lambda[i] = (dot(basis[i], residual)
                    - ((i + 1)..active.len())
                        .map(|j| lower[j][i] * lambda[j])
                        .sum::<f64>())
                    / lower[i][i];
            }
            // Bland-style index selection on negative multipliers avoids arbitrary tie choices.
            if let Some(remove) = (0..active.len())
                .filter(|&i| lambda[i] < -tolerance)
                .min_by_key(|&i| active[i])
            {
                active.remove(remove);
                continue;
            }
            let mut stationarity: Coefficients = std::array::from_fn(|k| x[k] - target[k]);
            for (&index, &l) in active.iter().zip(&lambda) {
                for (value, coefficient) in stationarity.iter_mut().zip(rows[index]) {
                    *value += l * coefficient;
                }
            }
            let multiplier_scale = 1. + lambda.iter().map(|l| l.abs()).sum::<f64>();
            if !x.iter().chain(&lambda).all(|v| v.is_finite())
                || norm(stationarity) > tolerance * multiplier_scale
                || rows
                    .iter()
                    .zip(&bounds)
                    .any(|(&r, &b)| dot(r, x) - b > tolerance)
                || active
                    .iter()
                    .any(|&i| (dot(rows[i], x) - bounds[i]).abs() > tolerance)
            {
                return Err("projection KKT residual exceeds f64 tolerance".into());
            }
            let mut multipliers = vec![0.; constraints.len()];
            for (&index, l) in active.iter().zip(lambda) {
                multipliers[index] = l.max(0.) * scale / norms[index];
            }
            let value = x.map(|v| v * scale);
            if !value.iter().chain(&multipliers).all(|v| v.is_finite()) {
                return Err("projection output overflow".into());
            }
            return Ok(Projection {
                value,
                multipliers,
                iterations: iteration + 1,
            });
        }
        let direction_norm = norm(direction);
        let mut step = 1_f64;
        let mut blocking = None;
        for (i, (&row, &bound)) in rows.iter().zip(&bounds).enumerate() {
            if active.contains(&i) {
                continue;
            }
            let speed = dot(row, direction);
            if speed <= ROUND * direction_norm {
                continue;
            }
            let slack = bound - dot(row, x);
            if slack < -tolerance {
                return Err("projection lost primal feasibility".into());
            }
            let candidate = slack.max(0.) / speed;
            if candidate < step {
                step = candidate;
                blocking = Some(i);
            }
        }
        for k in 0..5 {
            x[k] += step * direction[k];
        }
        if let Some(index) = blocking {
            if active.len() == 5 {
                return Err("projection exceeded working-set dimension".into());
            }
            active.push(index);
        }
    }
    Err("projection active-set iteration limit".into())
}

#[derive(Clone, Copy, Debug)]
pub struct LimitedJet {
    pub gradient: Vec2,
    /// [Hxx,Hyy,Hxy]
    pub hessian: [f64; 3],
}

impl Reconstruction<'_> {
    /// Project each quadratic jet onto exactly the historical target/neighbour face bounds.
    pub fn project_quadratic(
        &self,
        values: &[f64],
        gradient: &[Vec2],
        hessian: &[[f64; 3]],
    ) -> Result<Vec<LimitedJet>, String> {
        let mesh = self.mesh;
        if values.len() != mesh.cells.len()
            || gradient.len() != values.len()
            || hessian.len() != values.len()
            || !values
                .iter()
                .chain(gradient.iter().flatten())
                .chain(hessian.iter().flatten())
                .all(|v| v.is_finite())
        {
            return Err("invalid projected reconstruction input".into());
        }
        mesh.cells
            .iter()
            .enumerate()
            .map(|(i, cell)| {
                let h = cell.volume.sqrt();
                let raw = [
                    h * gradient[i][0],
                    h * gradient[i][1],
                    0.5 * cell.volume * hessian[i][0],
                    0.5 * cell.volume * hessian[i][1],
                    cell.volume * hessian[i][2] / SQRT_2,
                ];
                let mut low = values[i];
                let mut high = values[i];
                for &(f, _) in &cell.faces {
                    let q = values[mesh.neighbour(&mesh.faces[f], i).0];
                    low = low.min(q);
                    high = high.max(q);
                }
                let mut constraints = Vec::with_capacity(2 * cell.faces.len());
                for &(f, _) in &cell.faces {
                    let [x, y] = mesh.displacement(&mesh.faces[f], i).map(|v| v / h);
                    let normal = [x, y, x * x, y * y, SQRT_2 * x * y];
                    constraints.push(HalfSpace {
                        normal,
                        bound: high - values[i],
                    });
                    constraints.push(HalfSpace {
                        normal: normal.map(|v| -v),
                        bound: values[i] - low,
                    });
                }
                let result = project(raw, &constraints).map_err(|e| format!("cell {i}: {e}"))?;
                if result.iterations == 0 {
                    return Ok(LimitedJet {
                        gradient: gradient[i],
                        hessian: hessian[i],
                    });
                }
                let z = result.value;
                let limited = LimitedJet {
                    gradient: [z[0] / h, z[1] / h],
                    hessian: [
                        2. * z[2] / cell.volume,
                        2. * z[3] / cell.volume,
                        SQRT_2 * z[4] / cell.volume,
                    ],
                };
                if !limited
                    .gradient
                    .iter()
                    .chain(&limited.hessian)
                    .all(|v| v.is_finite())
                {
                    return Err("projected jet conversion overflow".into());
                }
                Ok(limited)
            })
            .collect()
    }
}
