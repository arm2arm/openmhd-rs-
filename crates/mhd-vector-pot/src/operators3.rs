//! Static, unlimited point curl. Array indices are [field component][coordinate].
use moving_mesh::three_d::{
    Tensor3, Vec3,
    fit::{FitError3, PointFit3, ScalarJet3},
};

pub fn curl(j: Tensor3) -> Vec3 {
    [j[2][1] - j[1][2], j[0][2] - j[2][0], j[1][0] - j[0][1]]
}
pub fn trace(j: Tensor3) -> f64 {
    j[0][0] + j[1][1] + j[2][2]
}

#[derive(Debug, Clone, Copy)]
pub struct MagneticJet3 {
    pub potential: [ScalarJet3; 3],
    pub field: Vec3,
    pub div_a: f64,
    pub same_fit_jacobian: Option<Tensor3>,
}
/// Observations are ordered by fit.samples(); an image looks up the same
/// periodic owner's potential. Manufactured lifted scalar fields may instead
/// supply a different value for each image.
pub fn recover(fit: &PointFit3, values: &[Vec3], mean: Vec3) -> Result<MagneticJet3, FitError3> {
    if !mean.into_iter().all(f64::is_finite) {
        return Err(FitError3::NonFinite);
    }
    let apply = |k: usize| fit.apply(&values.iter().map(|v| v[k]).collect::<Vec<_>>());
    let potential = [apply(0)?, apply(1)?, apply(2)?];
    let j = potential.map(|s| s.gradient);
    let c = curl(j);
    let field = std::array::from_fn(|i| mean[i] + c[i]);
    let same_fit_jacobian = match potential.map(|p| p.hessian) {
        [Some(a), Some(b), Some(c)] => Some(std::array::from_fn(|k| {
            std::array::from_fn(|i| [c[1][i] - b[2][i], a[2][i] - c[0][i], b[0][i] - a[1][i]][k])
        })),
        _ => None,
    };
    let div_a = trace(j);
    if !field
        .into_iter()
        .chain([div_a])
        .chain(same_fit_jacobian.into_iter().flatten().flatten())
        .all(f64::is_finite)
    {
        return Err(FitError3::NonFinite);
    }
    Ok(MagneticJet3 {
        potential,
        field,
        div_a,
        same_fit_jacobian,
    })
}

use moving_mesh::three_d::operator_mesh::{MeshFit3, OperatorMesh3};
use std::collections::BTreeMap;
fn dot(a: Vec3, b: Vec3) -> f64 {
    a.into_iter().zip(b).map(|(x, y)| x * y).sum()
}
fn cross(a: Vec3, b: Vec3) -> Vec3 {
    [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
}
fn sub(a: Vec3, b: Vec3) -> Vec3 {
    std::array::from_fn(|i| a[i] - b[i])
}

/// Baseline-restored curl rows with repeated periodic owners coalesced.
pub struct DiscreteCurl3 {
    rows: Vec<(usize, BTreeMap<usize, Vec3>)>,
}
impl DiscreteCurl3 {
    pub fn assemble(fits: &[MeshFit3]) -> Result<Self, FitError3> {
        let mut rows = Vec::with_capacity(fits.len());
        for f in fits {
            let first = *f.owners.first().ok_or(FitError3::InvalidSample)?;
            if f.owners.len() != f.fit.samples().len() || f.owners.iter().any(|i| *i >= fits.len())
            {
                return Err(FitError3::InvalidSample);
            }
            let mut row = BTreeMap::new();
            for (j, &owner) in f.owners.iter().enumerate() {
                if owner == first {
                    continue;
                }
                let w = row.entry(owner).or_insert([0.; 3]);
                for (k, x) in w.iter_mut().enumerate() {
                    *x += f.fit.coefficients()[1 + k][j];
                }
            }
            rows.push((first, row));
        }
        Ok(Self { rows })
    }
    pub fn apply(&self, a: &[Vec3]) -> Result<Vec<Vec3>, FitError3> {
        if a.len() != self.rows.len() || a.iter().flatten().any(|x| !x.is_finite()) {
            return Err(FitError3::InvalidSample);
        }
        let result: Vec<_> = self
            .rows
            .iter()
            .map(|(base, row)| {
                let mut b = [0.; 3];
                for (&j, &w) in row {
                    for (x, d) in b.iter_mut().zip(cross(w, sub(a[j], a[*base]))) {
                        *x += d;
                    }
                }
                b
            })
            .collect();
        if result.iter().flatten().any(|x| !x.is_finite()) {
            return Err(FitError3::NonFinite);
        }
        Ok(result)
    }
    /// Euclidean transpose. Physical volume weights belong to the caller.
    pub fn transpose(&self, b: &[Vec3]) -> Result<Vec<Vec3>, FitError3> {
        if b.len() != self.rows.len() || b.iter().flatten().any(|x| !x.is_finite()) {
            return Err(FitError3::InvalidSample);
        }
        let mut a = vec![[0.; 3]; b.len()];
        for ((base, row), &v) in self.rows.iter().zip(b) {
            for (&j, &w) in row {
                for (k, d) in cross(v, w).into_iter().enumerate() {
                    a[j][k] += d;
                    a[*base][k] -= d;
                }
            }
        }
        if a.iter().flatten().any(|x| !x.is_finite()) {
            return Err(FitError3::NonFinite);
        }
        Ok(a)
    }
}

pub struct IndependentDivergence3 {
    pub cell_ls: Vec<f64>,
    pub face_mean: Vec<f64>,
    pub face_limited: Vec<f64>,
}
/// Compute trace of the separate linear B fit and two finite-volume divergences.
/// The limiter uses each component's neighbour extrema and one coefficient per cell.
pub fn independent_divergence(
    mesh: &OperatorMesh3,
    b: &[Vec3],
    linear: &[MeshFit3],
) -> Result<IndependentDivergence3, FitError3> {
    use moving_mesh::three_d::fit::FitOrder3;
    let n = mesh.cells().len();
    if b.len() != n || linear.len() != n || b.iter().flatten().any(|x| !x.is_finite()) {
        return Err(FitError3::InvalidSample);
    }
    let gradients = moving_mesh::parallel::map(n, |i| -> Result<_, FitError3> {
        let fit = &linear[i];
        if fit.fit.order != FitOrder3::Linear || fit.owners.iter().any(|&j| j >= n) {
            return Err(FitError3::InvalidSample);
        }
        let mut low = b[i];
        let mut high = b[i];
        let mut grad = [[0.; 3]; 3];
        let mut alpha = [1.0_f64; 3];
        for k in 0..3 {
            let y: Vec<_> = fit.owners.iter().map(|&j| b[j][k]).collect();
            grad[k] = fit.fit.apply(&y)?.gradient;
            for q in y {
                low[k] = low[k].min(q);
                high[k] = high[k].max(q);
            }
        }
        for &(fi, forward) in mesh.incidences(i) {
            let f = &mesh.faces()[fi];
            let center = if forward {
                mesh.cells()[i].centroid
            } else {
                mesh.lifted(i, f.right_image)
            };
            let dx = sub(f.centroid, center);
            for k in 0..3 {
                let v = dot(grad[k], dx);
                if v > 0. {
                    alpha[k] = alpha[k].min((high[k] - b[i][k]) / v);
                } else if v < 0. {
                    alpha[k] = alpha[k].min((low[k] - b[i][k]) / v);
                }
            }
        }
        let limited = std::array::from_fn::<_, 3, _>(|k| grad[k].map(|x| x * alpha[k]));
        Ok((trace(grad), limited))
    })
    .into_iter()
    .collect::<Result<Vec<_>, _>>()?;
    let mut mean = vec![0.; n];
    let mut limited = vec![0.; n];
    for f in mesh.faces() {
        let l = f.left;
        let r = f.right.ok_or(FitError3::UnsupportedBoundary)?;
        let dl = sub(f.centroid, mesh.cells()[l].centroid);
        let dr = sub(f.centroid, mesh.lifted(r, f.right_image));
        let midpoint = std::array::from_fn(|k| 0.5 * (b[l][k] + b[r][k]));
        let at_face = std::array::from_fn(|k| {
            midpoint[k] + 0.5 * (dot(gradients[l].1[k], dl) + dot(gradients[r].1[k], dr))
        });
        let fm = f.area * dot(f.normal, midpoint);
        let fl = f.area * dot(f.normal, at_face);
        mean[l] += fm;
        mean[r] -= fm;
        limited[l] += fl;
        limited[r] -= fl;
    }
    for (i, c) in mesh.cells().iter().enumerate() {
        mean[i] /= c.volume;
        limited[i] /= c.volume;
    }
    if mean.iter().chain(&limited).any(|v| !v.is_finite()) {
        return Err(FitError3::NonFinite);
    }
    Ok(IndependentDivergence3 {
        cell_ls: gradients.into_iter().map(|g| g.0).collect(),
        face_mean: mean,
        face_limited: limited,
    })
}
