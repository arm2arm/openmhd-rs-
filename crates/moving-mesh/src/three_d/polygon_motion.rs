//! Smooth periodic polygon derivatives with exact Voronoi vertex identities.
use super::moments::{Sum, add, cross, dot, norm, scale, sub};
use super::{
    FaceRef3, GeometryEpoch3, GeometryError3, MotionRates3, SupportedGeometry3, Tensor3, Vec3,
    VertexPlane3, prescribed_motion_rates3,
};
use galaxy_types::CellId;
use std::collections::BTreeMap;

#[derive(Clone, Copy, Debug, Default)]
pub struct PolygonMotion3 {
    pub area_vector_rate: Vec3,
    pub centroid_velocity: Vec3,
    pub covariance_rate: Tensor3,
    pub minimum_normalized_vertex_determinant: Option<f64>,
}
pub struct PrescribedPolygonRates3 {
    rates: MotionRates3,
    faces: Vec<PolygonMotion3>,
}
impl PrescribedPolygonRates3 {
    pub fn cells_and_faces(&self) -> &MotionRates3 {
        &self.rates
    }
    pub fn epoch(&self) -> GeometryEpoch3 {
        self.rates.epoch()
    }
    pub fn face(&self, handle: FaceRef3) -> Result<&PolygonMotion3, GeometryError3> {
        self.rates.face(handle)?;
        Ok(&self.faces[handle.index() as usize])
    }
    pub fn build(
        s: &SupportedGeometry3,
        w: &BTreeMap<CellId, Vec3>,
    ) -> Result<Self, GeometryError3> {
        let g = s.geometry();
        let rates = prescribed_motion_rates3(g, w, [0.; 3])
            .map_err(|_| GeometryError3::InvalidTopology("prescribed polygon velocities"))?;
        let velocity: Vec<_> = g.cells().iter().map(|c| w[&c.generator.id]).collect();
        let rigid = velocity.iter().all(|v| *v == velocity[0]);
        let mut faces = Vec::with_capacity(g.faces().len());
        for (i, f) in g.faces().iter().enumerate() {
            let left = f.left as usize;
            if rigid {
                faces.push(PolygonMotion3 {
                    centroid_velocity: velocity[0],
                    ..PolygonMotion3::default()
                });
                continue;
            }
            let plane_data = |p: VertexPlane3| {
                let other = p.neighbour as usize;
                let d = std::array::from_fn(|k| {
                    (g.cells()[other].generator.position[k] - g.cells()[left].generator.position[k])
                        + p.image.0[k] as f64 * g.domain().width[k]
                });
                (d, sub(velocity[other], velocity[left]))
            };
            let mut velocities = Vec::with_capacity(f.polygon.len());
            let mut det_min = 1.0_f64;
            for (vertex, active) in f.polygon.iter().zip(&s.support[i]) {
                let triple = super::persistent_vertex::basis(g, &velocity, left, active)?;
                let equations = triple.map(plane_data);
                // In the translating left chart, d.x=|d|²/2 and d.x'=d'.(d-x).
                let rows = equations.map(|(d, _)| scale(d, 1. / norm(d)));
                let rhs = equations.map(|(d, dv)| dot(dv, sub(d, *vertex)) / norm(d));
                let reciprocal = [
                    cross(rows[1], rows[2]),
                    cross(rows[2], rows[0]),
                    cross(rows[0], rows[1]),
                ];
                let determinant = dot(rows[0], reciprocal[0]);
                if !determinant.is_finite() || determinant.abs() <= 1e-10 {
                    return Err(GeometryError3::SingularIntersection);
                }
                det_min = det_min.min(determinant.abs());
                let v = std::array::from_fn(|k| {
                    rhs.iter()
                        .zip(reciprocal)
                        .map(|(b, r)| b * r[k])
                        .sum::<f64>()
                        / determinant
                });
                if rows
                    .into_iter()
                    .zip(rhs)
                    .any(|(r, b)| (dot(r, v) - b).abs() > 1e-12 * norm(v).max(b.abs()).max(1.))
                {
                    return Err(GeometryError3::Unrepresentable("moving vertex residual"));
                }
                velocities.push(v);
            }
            let x: Vec<_> = f
                .polygon
                .iter()
                .map(|p| sub(*p, f.centroid_offset))
                .collect();
            let mut area_vector = [Sum::default(); 3];
            let mut area_rate = Sum::default();
            let mut first = [Sum::default(); 3];
            let mut second = [[Sum::default(); 3]; 3];
            for k in 1..x.len() - 1 {
                let p = [x[0], x[k], x[k + 1]];
                let v = [velocities[0], velocities[k], velocities[k + 1]];
                let u = sub(p[1], p[0]);
                let l = sub(p[2], p[0]);
                let ds = scale(
                    add(cross(sub(v[1], v[0]), l), cross(u, sub(v[2], v[0]))),
                    0.5,
                );
                let q = 0.5 * dot(cross(u, l), f.normal);
                let dq = dot(ds, f.normal);
                if !(q.is_finite() && q > 0.) {
                    return Err(GeometryError3::Unrepresentable("moving face fan area"));
                }
                area_rate.add(dq);
                let z = add(add(p[0], p[1]), p[2]);
                let dz = add(add(v[0], v[1]), v[2]);
                for (j, area) in area_vector.iter_mut().enumerate() {
                    area.add(ds[j]);
                    first[j].add((dq * z[j] + q * dz[j]) / 3.);
                    for (k, acc) in second[j].iter_mut().enumerate() {
                        let moment = z[j] * z[k] + p.iter().map(|x| x[j] * x[k]).sum::<f64>();
                        let deriv = dz[j] * z[k]
                            + z[j] * dz[k]
                            + p.iter()
                                .zip(v)
                                .map(|(x, b)| b[j] * x[k] + x[j] * b[k])
                                .sum::<f64>();
                        acc.add((dq * moment + q * deriv) / 12.);
                    }
                }
            }
            let area_vector_rate = area_vector.map(Sum::get);
            let centroid_velocity = add(velocity[left], first.map(|x| x.get() / f.area));
            let covariance_rate: Tensor3 = std::array::from_fn(|i| {
                std::array::from_fn(|j| {
                    (second[i][j].get() - area_rate.get() * f.covariance[i][j]) / f.area
                })
            });
            if !area_vector_rate
                .iter()
                .chain(&centroid_velocity)
                .chain(covariance_rate.iter().flatten())
                .all(|v| v.is_finite())
            {
                return Err(GeometryError3::Unrepresentable("moving face moments"));
            }
            faces.push(PolygonMotion3 {
                area_vector_rate,
                centroid_velocity,
                covariance_rate,
                minimum_normalized_vertex_determinant: Some(det_min),
            });
        }
        Ok(Self { rates, faces })
    }
}
