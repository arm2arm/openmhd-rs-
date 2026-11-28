//! Periodic Stokes curl of a shared quadratic face-average potential (F1–F4).
use super::{cross, sub};
use moving_mesh::parallel;
use moving_mesh::three_d::{
    Boundary3, Tensor3, ValidatedGeometry3, Vec3,
    fit::{FitError3, FitOrder3, ScalarJet3},
    operator_mesh::{MeshFit3, OperatorMesh3},
};
use std::collections::BTreeMap;

/// Centroid point samples of A map to volume averages of B. Covariances are
/// surface-average central second moments in physical coordinates.
pub struct SharedFaceCurl3 {
    mesh: OperatorMesh3,
    covariances: Vec<Tensor3>,
    pub(super) fits: Vec<MeshFit3>,
}

fn face_basis(d: Vec3, c: &Tensor3) -> [f64; 10] {
    let [x, y, z] = d;
    [
        1.,
        x,
        y,
        z,
        (x * x + c[0][0]) * 0.5,
        (y * y + c[1][1]) * 0.5,
        (z * z + c[2][2]) * 0.5,
        x * y + c[0][1],
        x * z + c[0][2],
        y * z + c[1][2],
    ]
}
fn evaluate(jet: &ScalarJet3, b: &[f64; 10]) -> f64 {
    // Only ten-term fits are constructed in this type.
    let h = jet.hessian.expect("quadratic face fit");
    let gradient = jet.gradient;
    [
        jet.value,
        gradient[0],
        gradient[1],
        gradient[2],
        h[0][0],
        h[1][1],
        h[2][2],
        h[0][1],
        h[0][2],
        h[1][2],
    ]
    .into_iter()
    .zip(b)
    .map(|(x, y)| x * y)
    .sum()
}
fn finite(field: &[Vec3]) -> bool {
    field.iter().flatten().all(|v| v.is_finite())
}

impl SharedFaceCurl3 {
    pub const POLICY: &'static str = "periodic-shared-face-quadratic-curl-v1";
    pub const SAMPLING: &'static str = "a-point-b-cell-average-v1";

    pub fn mesh(&self) -> &OperatorMesh3 {
        &self.mesh
    }

    pub fn from_validated(g: &ValidatedGeometry3) -> Result<Self, FitError3> {
        Self::from_metrics(
            OperatorMesh3::from_validated(g)?,
            g.faces().iter().map(|f| f.covariance).collect(),
        )
    }

    /// Construct a map on imported shared metrics. Each covariance must belong
    /// to the same polygon and canonical face order as the mesh.
    pub fn from_metrics(mesh: OperatorMesh3, covariances: Vec<Tensor3>) -> Result<Self, FitError3> {
        if mesh.domain().boundary != Boundary3::Periodic {
            return Err(FitError3::UnsupportedBoundary);
        }
        if covariances.len() != mesh.faces().len() {
            return Err(FitError3::InvalidSample);
        }
        for (cov, face) in covariances.iter().zip(mesh.faces()) {
            let scale = cov
                .iter()
                .flatten()
                .copied()
                .map(f64::abs)
                .fold(0., f64::max);
            if !finite(cov) || scale == 0. {
                return Err(FitError3::InvalidSample);
            }
            let scaled = cov.map(|row| row.map(|v| v / scale));
            for (i, row) in scaled.iter().enumerate() {
                let normal: f64 = row.iter().zip(face.normal).map(|(x, n)| x * n).sum();
                if normal.abs() > 1e-9
                    || row[i] < -1e-12
                    || row.iter().enumerate().any(|(j, &v)| {
                        (v - scaled[j][i]).abs() > 1e-12 || row[i] * scaled[j][j] - v * v < -1e-12
                    })
                {
                    return Err(FitError3::InvalidSample);
                }
            }
        }
        let fits = parallel::map_indexed(mesh.cells().len(), std::num::NonZeroUsize::MIN, |i| {
            mesh.fit(i, FitOrder3::Quadratic)
        })
        .into_iter()
        .collect::<Result<_, _>>()?;
        Ok(Self {
            mesh,
            covariances,
            fits,
        })
    }

    pub(super) fn sides(&self, face: usize) -> [(usize, [f64; 10]); 2] {
        let f = &self.mesh.faces()[face];
        let right = f.right.expect("validated periodic face");
        [
            (f.left, self.mesh.cells()[f.left].centroid),
            (right, self.mesh.lifted(right, f.right_image)),
        ]
        .map(|(i, center)| {
            (
                i,
                face_basis(sub(f.centroid, center), &self.covariances[face]),
            )
        })
    }

    /// The real-owner interpolation row H, including both restored intercepts.
    /// This includes self-image polygons, whose curl exchanges cancel.
    pub fn face_weights(&self, face: usize) -> Result<BTreeMap<usize, f64>, FitError3> {
        if face >= self.mesh.faces().len() {
            return Err(FitError3::InvalidSample);
        }
        let mut weights = BTreeMap::<usize, f64>::new();
        for (owner, basis) in self.sides(face) {
            let f = &self.fits[owner];
            let base = f.owners[0];
            *weights.entry(base).or_default() += 0.5;
            for (j, &source) in f.owners.iter().enumerate() {
                if source == base {
                    continue;
                }
                let w: f64 = f
                    .fit
                    .coefficients()
                    .iter()
                    .zip(basis)
                    .map(|(r, b)| r[j] * b)
                    .sum();
                *weights.entry(source).or_default() += 0.5 * w;
                *weights.entry(base).or_default() -= 0.5 * w;
            }
        }
        if weights.values().all(|v| v.is_finite()) {
            Ok(weights)
        } else {
            Err(FitError3::NonFinite)
        }
    }

    pub fn face_values(&self, a: &[Vec3]) -> Result<Vec<Vec3>, FitError3> {
        if a.len() != self.fits.len() || !finite(a) {
            return Err(FitError3::InvalidSample);
        }
        let jets = parallel::map(self.fits.len(), |i| {
            let f = &self.fits[i];
            let sample = |k: usize| {
                f.fit
                    .apply(&f.owners.iter().map(|&j| a[j][k]).collect::<Vec<_>>())
            };
            Ok([sample(0)?, sample(1)?, sample(2)?])
        })
        .into_iter()
        .collect::<Result<Vec<_>, FitError3>>()?;
        let values = parallel::map(self.mesh.faces().len(), |j| {
            let [(l, bl), (r, br)] = self.sides(j);
            std::array::from_fn(|k| {
                0.5 * evaluate(&jets[l][k], &bl) + 0.5 * evaluate(&jets[r][k], &br)
            })
        });
        if finite(&values) {
            Ok(values)
        } else {
            Err(FitError3::NonFinite)
        }
    }

    /// Accumulate one extensive exchange on both incidences before dividing by
    /// cell volume. The prescribed harmonic mean is a separate field component.
    pub fn apply(&self, a: &[Vec3]) -> Result<Vec<Vec3>, FitError3> {
        let values = self.face_values(a)?;
        let mut out = vec![[0.; 3]; self.fits.len()];
        for (f, value) in self.mesh.faces().iter().zip(values) {
            let r = f.right.expect("validated periodic face");
            if r == f.left {
                continue;
            }
            let flux = cross(f.normal.map(|n| n * f.area), value);
            for (k, term) in flux.into_iter().enumerate() {
                out[f.left][k] += term;
                out[r][k] -= term;
            }
        }
        for (v, c) in out.iter_mut().zip(self.mesh.cells()) {
            *v = v.map(|x| x / c.volume);
        }
        if finite(&out) {
            Ok(out)
        } else {
            Err(FitError3::NonFinite)
        }
    }

    /// Euclidean transpose. The test vector carries no implicit volume weight.
    pub fn transpose(&self, b: &[Vec3]) -> Result<Vec<Vec3>, FitError3> {
        if b.len() != self.fits.len() || !finite(b) {
            return Err(FitError3::InvalidSample);
        }
        let mut out = vec![[0.; 3]; self.fits.len()];
        for (j, f) in self.mesh.faces().iter().enumerate() {
            let r = f.right.expect("validated periodic face");
            if r == f.left {
                continue;
            }
            let l = f.left;
            let delta = std::array::from_fn(|k| {
                b[l][k] / self.mesh.cells()[l].volume - b[r][k] / self.mesh.cells()[r].volume
            });
            let dual = cross(delta, f.normal.map(|n| n * f.area));
            for (owner, w) in self.face_weights(j)? {
                for (dest, v) in out[owner].iter_mut().zip(dual) {
                    *dest += w * v;
                }
            }
        }
        if finite(&out) {
            Ok(out)
        } else {
            Err(FitError3::NonFinite)
        }
    }

    /// Diagonal of CᵀVC after summing every image, baseline and incident
    /// polygon contribution to a real input/output block.
    pub fn gram_diagonal(&self) -> Result<Vec<Vec3>, FitError3> {
        let mut out = vec![[0.; 3]; self.fits.len()];
        for (i, c) in self.mesh.cells().iter().enumerate() {
            let mut blocks = BTreeMap::<usize, Vec3>::new();
            for &(j, forward) in self.mesh.incidences(i) {
                let f = &self.mesh.faces()[j];
                if f.right == Some(f.left) {
                    continue;
                }
                let area = if forward { f.area } else { -f.area };
                for (owner, w) in self.face_weights(j)? {
                    let g = blocks.entry(owner).or_default();
                    for (x, n) in g.iter_mut().zip(f.normal) {
                        *x += area * n * w;
                    }
                }
            }
            for (owner, g) in blocks {
                for (k, x) in out[owner].iter_mut().enumerate() {
                    *x += (g[(k + 1) % 3].powi(2) + g[(k + 2) % 3].powi(2)) / c.volume;
                }
            }
        }
        if finite(&out) {
            Ok(out)
        } else {
            Err(FitError3::NonFinite)
        }
    }
}
