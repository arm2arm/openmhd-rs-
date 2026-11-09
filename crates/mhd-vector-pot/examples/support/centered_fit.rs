//! Diagnostic form of the optional central-value fit in paper §5.1 step vi.
use moving_mesh::{Mesh, Vec2};

fn solve(data: &[(Vec2, f64, f64)], h: f64) -> Result<Vec2, String> {
    let mut m = [0.; 3];
    let mut b = [0.; 2];
    for &(d, weight, change) in data {
        let [x, y] = d.map(|v| v / h);
        m[0] += weight * x * x;
        m[1] += weight * x * y;
        m[2] += weight * y * y;
        b[0] += weight * x * change;
        b[1] += weight * y * change;
    }
    let det = m[0] * m[2] - m[1] * m[1];
    let trace = m[0] + m[2];
    if !det.is_finite() || det <= 1e-10 * trace * trace {
        return Err("rank-deficient centered stencil".into());
    }
    let g = [
        (m[2] * b[0] - m[1] * b[1]) / (det * h),
        (m[0] * b[1] - m[1] * b[0]) / (det * h),
    ];
    if !g.iter().all(|v| v.is_finite()) {
        return Err("centered fit overflow".into());
    }
    Ok(g)
}

pub fn gradient(mesh: &Mesh, values: &[f64]) -> Result<Vec<Vec2>, String> {
    mesh.validate()?;
    if values.len() != mesh.cells.len() || !values.iter().all(|v| v.is_finite()) {
        return Err("invalid centered-fit values".into());
    }
    mesh.cells
        .iter()
        .enumerate()
        .map(|(i, cell)| {
            let perimeter: f64 = cell.faces.iter().map(|&(f, _)| mesh.faces[f].area).sum();
            let data: Vec<_> = cell
                .faces
                .iter()
                .map(|&(f, _)| {
                    let face = &mesh.faces[f];
                    let (j, d) = mesh.neighbour(face, i);
                    (d, face.area / perimeter, values[j] - values[i])
                })
                .collect();
            solve(&data, cell.volume.sqrt())
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn affine_and_constant_on_actual_periodic_stencils() {
        for jitter in [0., 0.15] {
            let mesh = Mesh::lattice(32, 4, [2., 0.125], jitter).unwrap();
            assert!(
                gradient(&mesh, &vec![7.; mesh.cells.len()])
                    .unwrap()
                    .iter()
                    .flatten()
                    .all(|v| *v == 0.)
            );
            for (i, cell) in mesh.cells.iter().enumerate() {
                let data: Vec<_> = cell
                    .faces
                    .iter()
                    .map(|&(f, _)| {
                        let (_, d) = mesh.neighbour(&mesh.faces[f], i);
                        (d, mesh.faces[f].area, 2. * d[0] - 3. * d[1])
                    })
                    .collect();
                let g = solve(&data, cell.volume.sqrt()).unwrap();
                assert!((g[0] - 2.).abs() < 1e-12 && (g[1] + 3.).abs() < 1e-12);
            }
        }
        assert!(solve(&[([1., 0.], 1., 1.), ([-1., 0.], 1., -1.)], 1.).is_err());
    }
    #[test]
    fn periodic_smooth_refinement_and_offset_invariance() {
        use std::f64::consts::TAU;
        for jitter in [0., 0.15] {
            let mut errors = Vec::new();
            for n in [8, 16, 32] {
                let mesh = Mesh::lattice(n, n, [1.; 2], jitter).unwrap();
                let values: Vec<_> = mesh
                    .cells
                    .iter()
                    .map(|c| (TAU * c.centroid[0]).sin() * (TAU * c.centroid[1]).cos())
                    .collect();
                let grad = gradient(&mesh, &values).unwrap();
                let shifted =
                    gradient(&mesh, &values.iter().map(|v| v + 4.).collect::<Vec<_>>()).unwrap();
                let error: f64 = mesh
                    .cells
                    .iter()
                    .zip(&grad)
                    .map(|(c, g)| {
                        let [x, y] = c.centroid.map(|v| TAU * v);
                        c.volume
                            * (g[0] - TAU * x.cos() * y.cos()).hypot(g[1] + TAU * x.sin() * y.sin())
                    })
                    .sum();
                errors.push(error);
                assert!(
                    grad.iter()
                        .flatten()
                        .zip(shifted.iter().flatten())
                        .all(|(a, b)| (a - b).abs() < 1e-12)
                );
            }
            assert!(errors.windows(2).all(|e| e[1] < 0.55 * e[0]), "{errors:?}");
        }
    }
}
