//! Fixed-sample derivative of the shared-face cell-average curl (F5–F9).
use super::{SharedFaceCurl3, cross, sub};
use moving_mesh::three_d::{
    GeometryEpoch3, PrescribedPolygonRates3, SupportedGeometry3, Tensor3, Vec3, fit::FitError3,
};
use std::collections::BTreeMap;

fn basis_rate(d: Vec3, v: Vec3, c: &Tensor3) -> [f64; 10] {
    let [x, y, z] = d;
    let [u, v, w] = v;
    [
        0.,
        u,
        v,
        w,
        x * u + 0.5 * c[0][0],
        y * v + 0.5 * c[1][1],
        z * w + 0.5 * c[2][2],
        u * y + x * v + c[0][1],
        u * z + x * w + c[0][2],
        v * z + y * w + c[1][2],
    ]
}

pub struct MovingSharedFaceCurl3 {
    epoch: GeometryEpoch3,
    trajectory: [u8; 32],
    field: SharedFaceCurl3,
    rows: Vec<BTreeMap<usize, Vec3>>,
}
impl MovingSharedFaceCurl3 {
    pub fn assemble(
        s: &SupportedGeometry3,
        motion: &PrescribedPolygonRates3,
    ) -> Result<Self, FitError3> {
        let g = s.geometry();
        let rates = motion.cells_and_faces();
        if motion.epoch() != g.epoch() {
            return Err(FitError3::MotionMismatch);
        }
        let field = SharedFaceCurl3::from_validated(g)?;
        let mesh = field.mesh();
        let cells = (0..mesh.cells().len())
            .map(|i| {
                let h = g.cell_ref(i).map_err(|_| FitError3::InvalidSample)?;
                rates
                    .cell(h)
                    .copied()
                    .map_err(|_| FitError3::MotionMismatch)
            })
            .collect::<Result<Vec<_>, _>>()?;
        let mut rows = vec![BTreeMap::<usize, Vec3>::new(); cells.len()];
        let relative: Vec<Vec<Vec3>> = field
            .fits
            .iter()
            .enumerate()
            .map(|(i, f)| {
                f.owners
                    .iter()
                    .map(|&owner| sub(cells[owner].centroid_velocity, cells[i].centroid_velocity))
                    .collect()
            })
            .collect();
        for (j, f) in mesh.faces().iter().enumerate() {
            let l = f.left;
            let r = f.right.ok_or(FitError3::UnsupportedBoundary)?;
            if l == r {
                continue;
            }
            let h = g.face_ref(j).map_err(|_| FitError3::InvalidSample)?;
            let rate = motion.face(h).map_err(|_| FitError3::MotionMismatch)?;
            let weights = field.face_weights(j)?;
            let mut wdot = BTreeMap::<usize, f64>::new();
            for ((i, b), center) in field
                .sides(j)
                .into_iter()
                .zip([mesh.cells()[l].centroid, mesh.lifted(r, f.right_image)])
            {
                let fit = &field.fits[i];
                let db = basis_rate(
                    sub(f.centroid, center),
                    sub(rate.centroid_velocity, cells[i].centroid_velocity),
                    &rate.covariance_rate,
                );
                let dw = fit.fit.quadratic_evaluation_weight_rate(
                    &relative[i],
                    cells[i].volume_rate / mesh.cells()[i].volume,
                    b,
                    db,
                )?;
                let base = fit.owners[0];
                for (&owner, v) in fit.owners.iter().zip(dw) {
                    if base != owner {
                        *wdot.entry(owner).or_default() += 0.5 * v;
                        *wdot.entry(base).or_default() -= 0.5 * v;
                    }
                }
            }
            for (&owner, w) in &weights {
                let dw = wdot.get(&owner).copied().unwrap_or(0.);
                for (target, sign) in [(l, 1.), (r, -1.)] {
                    let vol = mesh.cells()[target].volume;
                    let dilation = cells[target].volume_rate / vol;
                    let row = rows[target].entry(owner).or_default();
                    for (k, b) in row.iter_mut().enumerate() {
                        *b += sign / vol
                            * (rate.area_vector_rate[k] * w
                                + f.area * f.normal[k] * (dw - dilation * w));
                    }
                }
            }
        }
        if rows
            .iter()
            .flat_map(|r| r.values().flatten())
            .any(|v| !v.is_finite())
        {
            return Err(FitError3::NonFinite);
        }
        Ok(Self {
            epoch: g.epoch(),
            trajectory: rates.trajectory_digest(),
            field,
            rows,
        })
    }
    fn check(&self, g: &SupportedGeometry3, m: &PrescribedPolygonRates3) -> Result<(), FitError3> {
        if self.epoch != g.geometry().epoch()
            || m.epoch() != self.epoch
            || self.trajectory != m.cells_and_faces().trajectory_digest()
        {
            return Err(FitError3::MotionMismatch);
        }
        Ok(())
    }
    pub fn field(&self) -> &SharedFaceCurl3 {
        &self.field
    }
    pub fn apply(
        &self,
        g: &SupportedGeometry3,
        m: &PrescribedPolygonRates3,
        a: &[Vec3],
    ) -> Result<Vec<Vec3>, FitError3> {
        self.check(g, m)?;
        self.map(a, false)
    }
    pub fn transpose(
        &self,
        g: &SupportedGeometry3,
        m: &PrescribedPolygonRates3,
        b: &[Vec3],
    ) -> Result<Vec<Vec3>, FitError3> {
        self.check(g, m)?;
        self.map(b, true)
    }
    fn map(&self, input: &[Vec3], transpose: bool) -> Result<Vec<Vec3>, FitError3> {
        if input.len() != self.rows.len() || !input.iter().flatten().all(|x| x.is_finite()) {
            return Err(FitError3::InvalidSample);
        }
        let mut out = vec![[0.; 3]; input.len()];
        for (target, row) in self.rows.iter().enumerate() {
            for (&source, &g) in row {
                let (dest, v) = if transpose {
                    (source, cross(input[target], g))
                } else {
                    (target, cross(g, input[source]))
                };
                for (sum, add) in out[dest].iter_mut().zip(v) {
                    *sum += add;
                }
            }
        }
        if out.iter().flatten().all(|v| v.is_finite()) {
            Ok(out)
        } else {
            Err(FitError3::NonFinite)
        }
    }
}
