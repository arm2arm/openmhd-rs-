//! Positive, quadratic-consistent Laplace stencils on cell centroids.
//! Engineering discretization following the constraints of Seibold (2008),
//! arXiv:0802.2674. Independent two-phase simplex implementation; no copied code.
use crate::{Mesh, Vec2, quadratic};

const M: usize = 5;
const TOL: f64 = 1e-12;

fn moments([x, y]: Vec2) -> [f64; M] {
    [x, y, x * x, y * y, x * y]
}

fn pivot(table: &mut [Vec<f64>], basis: &mut [usize], row: usize, column: usize) {
    let divisor = table[row][column];
    for value in &mut table[row] {
        *value /= divisor;
    }
    let pivot = table[row].clone();
    for (i, other) in table.iter_mut().enumerate() {
        if i != row {
            let scale = other[column];
            for (a, b) in other.iter_mut().zip(&pivot) {
                *a -= scale * b;
            }
            other[column] = 0.;
        }
    }
    table[row][column] = 1.;
    basis[row] = column;
}

fn minimize(table: &mut [Vec<f64>], basis: &mut [usize], entering: usize) -> Result<(), String> {
    let rhs = table[0].len() - 1;
    for _ in 0..2000 {
        // Bland's rule for degenerate moment systems on regular lattices.
        let Some(column) = (0..entering).find(|&j| table[M][j] < -TOL) else {
            return Ok(());
        };
        let mut leaving = None;
        let mut distance = f64::INFINITY;
        for i in 0..M {
            if table[i][column] > TOL {
                let ratio = table[i][rhs] / table[i][column];
                if ratio < distance - TOL
                    || ((ratio - distance).abs() <= TOL
                        && leaving.is_none_or(|j| basis[i] < basis[j]))
                {
                    distance = ratio;
                    leaving = Some(i);
                }
            }
        }
        let row = leaving.ok_or("unbounded positive stencil program")?;
        if distance < -1e-10 {
            return Err("lost positive stencil feasibility".into());
        }
        pivot(table, basis, row, column);
    }
    Err("positive stencil iteration limit".into())
}

fn weights(offsets: &[Vec2]) -> Result<(Vec<f64>, f64), String> {
    let n = offsets.len();
    if n < M {
        return Err("insufficient positive stencil samples".into());
    }
    let columns: Vec<_> = offsets.iter().copied().map(moments).collect();
    let target = [0., 0., 2., 2., 0.];
    let rhs = n + M;
    let mut table = vec![vec![0.; rhs + 1]; M + 1];
    let mut basis: Vec<_> = (n..n + M).collect();
    for i in 0..M {
        let scale = columns.iter().map(|c| c[i].abs()).fold(0., f64::max);
        if scale <= 0. || !scale.is_finite() {
            return Err("rank-deficient positive moments".into());
        }
        for (j, c) in columns.iter().enumerate() {
            table[i][j] = c[i] / scale;
        }
        table[i][n + i] = 1.;
        table[i][rhs] = target[i] / scale;
    }
    // Phase I: minimize the sum of artificial variables.
    for j in n..rhs {
        table[M][j] = 1.;
    }
    for i in 0..M {
        for j in 0..=rhs {
            table[M][j] -= table[i][j];
        }
    }
    minimize(&mut table, &mut basis, rhs)?;
    let artificial: f64 = (0..M)
        .filter(|&i| basis[i] >= n)
        .map(|i| table[i][rhs].abs())
        .sum();
    if artificial > 1e-10 {
        return Err("no feasible positive Laplace stencil".into());
    }
    for i in 0..M {
        if basis[i] >= n {
            let column = (0..n)
                .find(|j| !basis.contains(j) && table[i][*j].abs() > TOL)
                .ok_or("rank-deficient positive moment constraints")?;
            // Only artificial zeroes within the feasibility tolerance. Original
            // unscaled moments are checked again after the complete solve.
            table[i][rhs] = 0.;
            pivot(&mut table, &mut basis, i, column);
        }
    }
    // Phase II: prefer near neighbours, cost = distance cubed (p>2).
    let cost: Vec<_> = offsets.iter().map(|d| d[0].hypot(d[1]).powi(3)).collect();
    let scale = cost.iter().copied().fold(0., f64::max);
    table[M].fill(0.);
    for (j, c) in cost.iter().enumerate() {
        table[M][j] = c / scale;
    }
    for i in 0..M {
        let c = cost[basis[i]] / scale;
        for j in 0..=rhs {
            table[M][j] -= c * table[i][j];
        }
    }
    minimize(&mut table, &mut basis, n)?;
    let mut result = vec![0.; n];
    for i in 0..M {
        let value = table[i][rhs];
        if value < -1e-12 || !value.is_finite() {
            return Err("negative/nonfinite Laplace weight".into());
        }
        result[basis[i]] = value.max(0.); // roundoff only; checked against original moments below
    }
    let residual = (0..M)
        .map(|k| {
            (columns
                .iter()
                .zip(&result)
                .map(|(c, w)| c[k] * w)
                .sum::<f64>()
                - target[k])
                .abs()
        })
        .fold(0., f64::max);
    if !residual.is_finite() || residual > 5e-10 {
        return Err(format!("inaccurate positive Laplace moments: {residual}"));
    }
    Ok((result, residual))
}

/// Positive off-diagonals imply a standalone scalar maximum principle, not a
/// magnetic-energy theorem for an independently reconstructed discrete curl.
#[derive(Clone, Debug)]
pub struct PositiveLaplacian {
    rows: Vec<Vec<(usize, f64)>>,
    sums: Vec<f64>,
    pub max_moment_error: f64,
}
impl PositiveLaplacian {
    pub fn build(mesh: &Mesh) -> Result<Self, String> {
        mesh.validate()?;
        let mut rows = Vec::with_capacity(mesh.cells.len());
        let mut sums = Vec::with_capacity(mesh.cells.len());
        let mut max_moment_error: f64 = 0.;
        for (i, cell) in mesh.cells.iter().enumerate() {
            let h = cell.volume.sqrt();
            let points = quadratic::samples(mesh, i);
            let offsets: Vec<_> = points.iter().map(|(_, d)| d.map(|x| x / h)).collect();
            let (w, residual) =
                weights(&offsets).map_err(|e| format!("positive Laplace cell {i}: {e}"))?;
            let row: Vec<_> = points
                .iter()
                .zip(w)
                .filter(|(_, w)| *w > 0.)
                .map(|((j, _), w)| (*j, w / cell.volume))
                .collect();
            let sum: f64 = row.iter().map(|(_, w)| w).sum();
            if sum <= 0. || !sum.is_finite() {
                return Err("invalid positive Laplace row".into());
            }
            rows.push(row);
            sums.push(sum);
            max_moment_error = max_moment_error.max(residual);
        }
        Ok(Self {
            rows,
            sums,
            max_moment_error,
        })
    }
    pub fn row_sums(&self) -> &[f64] {
        &self.sums
    }
    pub fn apply(&self, values: &[f64]) -> Result<Vec<f64>, String> {
        if values.len() != self.rows.len() || values.iter().any(|v| !v.is_finite()) {
            return Err("positive Laplace requires finite cell values of matching length".into());
        }
        let result: Vec<_> = self
            .rows
            .iter()
            .enumerate()
            .map(|(i, row)| {
                row.iter()
                    .map(|(j, w)| w * (values[*j] - values[i]))
                    .sum::<f64>()
            })
            .collect();
        if result.iter().any(|v| !v.is_finite()) {
            return Err("positive Laplace overflow".into());
        }
        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f64::consts::TAU;
    #[test]
    fn moments_stretched_periodic_geometry_and_maximum_principle() {
        for (nx, ny, lengths) in [
            (8, 8, [1.; 2]),
            (256, 4, [2., 0.125]),
            (512, 4, [2., 0.125]),
        ] {
            for jitter in [0., 0.15] {
                let mesh = Mesh::lattice(nx, ny, lengths, jitter).unwrap();
                let lap = PositiveLaplacian::build(&mesh).unwrap();
                assert!(lap.max_moment_error < 5e-10);
                assert!(lap.rows.iter().flatten().all(|(_, w)| *w >= 0.));
                assert!(
                    lap.apply(&vec![1.; nx * ny])
                        .unwrap()
                        .iter()
                        .all(|v| *v == 0.)
                );
                let data: Vec<_> = (0..nx * ny)
                    .map(|i| ((i * 7919 % 101) as f64) / 100.)
                    .collect();
                let rate = lap.apply(&data).unwrap();
                let dt = 0.9 / lap.sums.iter().copied().fold(0., f64::max);
                for (a, r) in data.iter().zip(rate) {
                    assert!((0.0..=1.0).contains(&(a + dt * r)));
                }
                assert!(lap.apply(&[f64::NAN]).is_err());
            }
        }
    }
    #[test]
    fn smooth_consistency_and_regular_short_modes_damp() {
        for jitter in [0., 0.15] {
            let mut errors = Vec::new();
            for n in [8, 16, 32] {
                let mesh = Mesh::lattice(n, n, [1.; 2], jitter).unwrap();
                let lap = PositiveLaplacian::build(&mesh).unwrap();
                let a: Vec<_> = mesh
                    .cells
                    .iter()
                    .map(|c| (TAU * c.centroid[0]).sin() * (TAU * c.centroid[1]).cos())
                    .collect();
                let rate = lap.apply(&a).unwrap();
                errors.push(
                    mesh.cells
                        .iter()
                        .zip(&a)
                        .zip(rate)
                        .map(|((c, a), r)| c.volume * (r + 2. * TAU * TAU * a).abs())
                        .sum::<f64>(),
                );
                if jitter == 0. {
                    for k in 1..=n / 2 {
                        let a: Vec<_> = mesh
                            .cells
                            .iter()
                            .map(|c| (0.37 + TAU * k as f64 * c.centroid[0]).sin())
                            .collect();
                        let r = lap.apply(&a).unwrap();
                        assert!(a.iter().zip(r).map(|(a, r)| a * r).sum::<f64>() < 0.);
                    }
                }
            }
            assert!(errors.windows(2).all(|e| e[1] < 0.8 * e[0]), "{errors:?}");
        }
    }
    #[test]
    fn infeasible_one_sided_points_are_rejected() {
        assert!(weights(&[[1., 0.], [2., 1.], [3., -1.], [1., 2.], [1., -2.], [2., 3.]]).is_err());
    }
}
