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
        let batch =
            std::num::NonZeroUsize::new(moving_mesh::parallel::team_size().saturating_mul(4))
                .unwrap();
        moving_mesh::parallel::visit_ordered(
            mesh.faces().len(),
            batch,
            std::num::NonZeroUsize::MIN,
            |j| {
                let f = &mesh.faces()[j];
                let l = f.left;
                let r = f.right.ok_or(FitError3::UnsupportedBoundary)?;
                if l == r {
                    return Ok(None);
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
                Ok::<_, FitError3>(Some((weights, wdot, rate.area_vector_rate)))
            },
            |j, computed| {
                let Some((weights, wdot, area_vector_rate)) = computed? else {
                    return Ok(());
                };
                let f = &mesh.faces()[j];
                let l = f.left;
                let r = f.right.expect("validated periodic face");
                for (&owner, w) in &weights {
                    let dw = wdot.get(&owner).copied().unwrap_or(0.);
                    for (target, sign) in [(l, 1.), (r, -1.)] {
                        let vol = mesh.cells()[target].volume;
                        let dilation = cells[target].volume_rate / vol;
                        let row = rows[target].entry(owner).or_default();
                        for (k, b) in row.iter_mut().enumerate() {
                            *b += sign / vol
                                * (area_vector_rate[k] * w
                                    + f.area * f.normal[k] * (dw - dilation * w));
                        }
                    }
                }
                Ok::<(), FitError3>(())
            },
        )?;
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
    fn check_values(&self, input: &[Vec3]) -> Result<(), FitError3> {
        if input.len() != self.rows.len() || input.iter().flatten().any(|x| !x.is_finite()) {
            Err(FitError3::InvalidSample)
        } else {
            Ok(())
        }
    }
    fn apply_row(&self, i: usize, input: &[Vec3]) -> Result<Vec3, FitError3> {
        let mut value = [0.; 3];
        for (&j, &g) in &self.rows[i] {
            for (sum, term) in value.iter_mut().zip(cross(g, input[j])) {
                *sum += term;
            }
        }
        if value.iter().all(|v| v.is_finite()) {
            Ok(value)
        } else {
            Err(FitError3::NonFinite)
        }
    }
    fn transpose_row(&self, i: usize, input: &[Vec3]) -> super::scatter::Contributions {
        self.rows[i]
            .iter()
            .map(|(&j, &g)| (j, cross(input[i], g)))
            .collect()
    }
    fn map(&self, input: &[Vec3], transpose: bool) -> Result<Vec<Vec3>, FitError3> {
        self.check_values(input)?;
        if transpose {
            super::scatter::local(input.len(), input.len(), |i| {
                Ok(self.transpose_row(i, input))
            })
        } else {
            moving_mesh::parallel::map(input.len(), |i| self.apply_row(i, input))
                .into_iter()
                .collect()
        }
    }
    pub fn apply_on<L: moving_mesh::parallel::layout::Layout>(
        &self,
        g: &SupportedGeometry3,
        m: &PrescribedPolygonRates3,
        input: &[Vec3],
        partition: &moving_mesh::parallel::partition::Partition,
        layout: &L,
    ) -> Result<Vec<Vec3>, String> {
        self.check(g, m)
            .and_then(|()| self.check_values(input))
            .map_err(|e| e.to_string())?;
        if partition.ranks() != layout.ranks() {
            return Err("different moving curl partition".into());
        }
        let owners = self.field.cell_owners(partition)?;
        layout.rows(&owners, |i| {
            self.apply_row(i, input).map_err(|e| e.to_string())
        })
    }
    pub fn transpose_on<L: moving_mesh::parallel::layout::Layout>(
        &self,
        g: &SupportedGeometry3,
        m: &PrescribedPolygonRates3,
        input: &[Vec3],
        partition: &moving_mesh::parallel::partition::Partition,
        layout: &L,
    ) -> Result<Vec<Vec3>, String> {
        self.check(g, m)
            .and_then(|()| self.check_values(input))
            .map_err(|e| e.to_string())?;
        if partition.ranks() != layout.ranks() {
            return Err("different moving curl partition".into());
        }
        let owners = self.field.cell_owners(partition)?;
        super::scatter::ranked(input.len(), &owners, layout, |i| {
            Ok(self.transpose_row(i, input))
        })
    }
}
