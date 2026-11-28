//! Periodic Stokes curl of a shared quadratic face-average potential (F1–F4).
use super::{cross, sub};
use moving_mesh::parallel::{
    self,
    halo::{FaceHalo, HaloPlan},
};
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
fn coefficients(jet: &ScalarJet3) -> [f64; 10] {
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
}
fn evaluate(jet: &[f64; 10], b: &[f64; 10]) -> f64 {
    jet.iter().zip(b).map(|(x, y)| x * y).sum()
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
        let jets = parallel::map(self.fits.len(), |i| self.jet(i, |j| a[j]))
            .into_iter()
            .collect::<Result<Vec<_>, _>>()?;
        let values = parallel::map(self.mesh.faces().len(), |j| self.face_value(j, |i| jets[i]));
        if finite(&values) {
            Ok(values)
        } else {
            Err(FitError3::NonFinite)
        }
    }

    fn jet(&self, i: usize, value: impl Fn(usize) -> Vec3) -> Result<[[f64; 10]; 3], FitError3> {
        let f = &self.fits[i];
        let sample = |k: usize| {
            f.fit
                .apply(&f.owners.iter().map(|&j| value(j)[k]).collect::<Vec<_>>())
                .map(|s| coefficients(&s))
        };
        Ok([sample(0)?, sample(1)?, sample(2)?])
    }
    fn face_value(&self, j: usize, jet: impl Fn(usize) -> [[f64; 10]; 3]) -> Vec3 {
        let [(l, bl), (r, br)] = self.sides(j);
        let (left, right) = (jet(l), jet(r));
        std::array::from_fn(|k| 0.5 * evaluate(&left[k], &bl) + 0.5 * evaluate(&right[k], &br))
    }
    /// Owner-only jet recovery followed by one area-average A per canonical shared face.
    /// All receivers use exactly the same face value on the two opposite incidences.
    pub fn apply_on<L: parallel::layout::Layout>(
        &self,
        a: &[Vec3],
        partition: &parallel::partition::Partition,
        layout: &L,
    ) -> Result<Vec<Vec3>, String> {
        let compatible = a.len() == self.fits.len() && partition.ranks() == layout.ranks();
        layout.agree(&[u8::from(compatible)])?;
        if !compatible {
            return Err("invalid distributed curl input".into());
        }
        let owners = self.cell_owners(partition)?;
        let fits = HaloPlan::new(
            owners.clone(),
            self.fits
                .iter()
                .zip(&owners)
                .flat_map(|(fit, &rank)| fit.owners.iter().map(move |&j| (j, rank))),
        )?;
        let samples = layout.halo_rows("curl-samples", &fits, |i| {
            if a[i].iter().any(|x| !x.is_finite()) {
                return Err("nonfinite potential sample".into());
            }
            Ok(a[i])
        })?;
        let endpoints = self
            .mesh
            .faces()
            .iter()
            .map(|f| (f.left, f.right))
            .collect::<Vec<_>>();
        let routes = FaceHalo::new(owners, self.face_owners(partition)?, &endpoints)?;
        let jets = layout.halo_rows::<30, _>("curl-jets", &routes.to_faces, |i| {
            // Every image of a fit sample uses its real owner's one received row.
            let jet = self.jet(i, |j| samples[&j]).map_err(|e| format!("{e:?}"))?;
            Ok(std::array::from_fn(|k| jet[k / 10][k % 10]))
        })?;
        let fluxes = layout.halo_rows("curl-faces", &routes.to_cells, |j| {
            let f = &self.mesh.faces()[j];
            let value = self.face_value(j, |i| {
                std::array::from_fn(|c| std::array::from_fn(|k| jets[&i][10 * c + k]))
            });
            Ok(cross(f.normal.map(|n| n * f.area), value))
        })?;
        layout.rows(routes.to_faces.owners(), |i| {
            let mut out = [0.; 3];
            for &(j, forward) in &routes.incidences[i] {
                for (x, term) in out.iter_mut().zip(fluxes[&j]) {
                    if forward {
                        *x += term;
                    } else {
                        *x -= term;
                    }
                }
            }
            out = out.map(|x| x / self.mesh.cells()[i].volume);
            if !out.iter().all(|v| v.is_finite()) {
                return Err("nonfinite distributed curl".into());
            }
            Ok(out)
        })
    }
    /// Accumulate one extensive exchange on both incidences before dividing by
    /// cell volume. The prescribed harmonic mean is a separate field component.
    pub fn apply(&self, a: &[Vec3]) -> Result<Vec<Vec3>, FitError3> {
        self.accumulate(self.face_values(a)?)
    }
    fn accumulate(&self, values: Vec<Vec3>) -> Result<Vec<Vec3>, FitError3> {
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
        super::scatter::local(b.len(), self.mesh.faces().len(), |j| {
            self.transpose_face(b, j)
        })
    }
    fn transpose_face(
        &self,
        b: &[Vec3],
        j: usize,
    ) -> Result<super::scatter::Contributions, FitError3> {
        let face = &self.mesh.faces()[j];
        let l = face.left;
        let r = face.right.ok_or(FitError3::UnsupportedBoundary)?;
        if l == r {
            return Ok(Vec::new());
        }
        let delta = std::array::from_fn(|k| {
            b[l][k] / self.mesh.cells()[l].volume - b[r][k] / self.mesh.cells()[r].volume
        });
        let dual = cross(delta, face.normal.map(|n| n * face.area));
        Ok(self
            .face_weights(j)?
            .into_iter()
            .map(|(target, w)| (target, dual.map(|x| w * x)))
            .collect())
    }
    pub fn transpose_on<L: parallel::layout::Layout>(
        &self,
        b: &[Vec3],
        partition: &parallel::partition::Partition,
        layout: &L,
    ) -> Result<Vec<Vec3>, String> {
        if b.len() != self.fits.len() || !finite(b) || partition.ranks() != layout.ranks() {
            return Err("invalid distributed curl transpose input".into());
        }
        let owners = self.face_owners(partition)?;
        super::scatter::ranked(b.len(), &owners, layout, |j| self.transpose_face(b, j))
    }
    /// Block diagonal after combining all images of each real generator.
    fn gram_cell(&self, i: usize) -> Result<super::scatter::Contributions, FitError3> {
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
        let volume = self.mesh.cells()[i].volume;
        Ok(blocks
            .into_iter()
            .map(|(owner, g)| {
                (
                    owner,
                    std::array::from_fn(|k| {
                        (g[(k + 1) % 3].powi(2) + g[(k + 2) % 3].powi(2)) / volume
                    }),
                )
            })
            .collect())
    }
    pub fn gram_diagonal(&self) -> Result<Vec<Vec3>, FitError3> {
        super::scatter::local(self.fits.len(), self.fits.len(), |i| self.gram_cell(i))
    }
    pub fn gram_diagonal_on<L: parallel::layout::Layout>(
        &self,
        partition: &parallel::partition::Partition,
        layout: &L,
    ) -> Result<Vec<Vec3>, String> {
        if partition.ranks() != layout.ranks() {
            return Err("invalid Gram diagonal partition".into());
        }
        let owners = self.cell_owners(partition)?;
        super::scatter::ranked(self.fits.len(), &owners, layout, |i| self.gram_cell(i))
    }
    pub(super) fn cell_owners(
        &self,
        partition: &parallel::partition::Partition,
    ) -> Result<Vec<usize>, String> {
        self.mesh
            .cells()
            .iter()
            .map(|c| partition.owner(c.id.entity()))
            .collect()
    }
    fn face_owners(
        &self,
        partition: &parallel::partition::Partition,
    ) -> Result<Vec<usize>, String> {
        let cells = self.mesh.cells();
        self.mesh
            .faces()
            .iter()
            .map(|f| {
                partition.face_owner(
                    cells[f.left].id.entity(),
                    f.right.map(|r| cells[r].id.entity()),
                )
            })
            .collect()
    }
}
