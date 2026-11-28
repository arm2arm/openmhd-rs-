//! Exact incidence along the linear generator path at a multiple periodic vertex.
use super::exact::{self, D};
use super::moments::{cross, dot, norm, scale};
use super::oracle::separation;
use super::{GeometryError3, ValidatedGeometry3, Vec3, VertexPlane3};

type Result<T> = std::result::Result<T, GeometryError3>;
type ExactRow = [D; 3];

pub(super) fn basis(
    geometry: &ValidatedGeometry3,
    velocities: &[Vec3],
    left: usize,
    active: &[VertexPlane3],
) -> Result<[VertexPlane3; 3]> {
    if let Ok(simple) = active.try_into() {
        return Ok(simple);
    }
    let owner = geometry.cells()[left].generator;
    let width = geometry.domain().width.map(D::from_f64);
    let mut offsets = Vec::new();
    let mut slopes = Vec::new();
    let mut normals = Vec::new();
    for plane in active {
        let j = plane.neighbour as usize;
        let peer = geometry.cells()[j].generator;
        offsets.push(separation(owner, peer, plane.image, &width)?);
        let slope = |k: usize| D::from_f64(velocities[j][k]).sub(&D::from_f64(velocities[left][k]));
        slopes.push([slope(0)?, slope(1)?, slope(2)?]);
        let d = std::array::from_fn(|k| {
            (peer.position[k] - owner.position[k])
                + plane.image.0[k] as f64 * geometry.domain().width[k]
        });
        normals.push(scale(d, 1.0 / norm(d)));
    }
    let indices = (0..active.len())
        .find_map(|i| {
            (i + 1..active.len()).find_map(|j| {
                (j + 1..active.len())
                    .find(|&k| dot(normals[i], cross(normals[j], normals[k])).abs() > 1e-10)
                    .map(|k| [i, j, k])
            })
        })
        .ok_or(GeometryError3::SingularIntersection)?;
    // d(t) is affine. The augmented 4x4 determinant with rows
    // [d_x, d_y, d_z, |d|^2] has degree at most five. Six exact, distinct
    // substitutions certify the identity even when a basis is singular at a
    // nonzero sample. They do not approximate a time derivative.
    for t in 0..=5 {
        let tau = D::from_f64(f64::from(t));
        let mut rows = Vec::new();
        let mut rhs = Vec::new();
        for (d, v) in offsets.iter().zip(&slopes) {
            let component = |k: usize| d[k].add(&v[k].mul(&tau)?);
            let r: ExactRow = [component(0)?, component(1)?, component(2)?];
            rhs.push(exact::dot(&r, &r)?);
            rows.push(r);
        }
        let basis = indices.map(|i| rows[i].clone());
        let det = exact::det(&basis)?;
        if t == 0 && det.sign() == 0 {
            return Err(GeometryError3::SingularIntersection);
        }
        let numerator = |axis: usize| {
            let mut m = basis.clone();
            for (r, i) in m.iter_mut().zip(indices) {
                r[axis] = rhs[i].clone();
            }
            exact::det(&m)
        };
        let doubled_vertex = [numerator(0)?, numerator(1)?, numerator(2)?];
        for (i, r) in rows.iter().enumerate() {
            if !indices.contains(&i)
                && exact::dot(r, &doubled_vertex)?
                    .sub(&det.mul(&rhs[i])?)?
                    .sign()
                    != 0
            {
                return Err(GeometryError3::InvalidTopology(
                    "non-simple moving periodic vertex",
                ));
            }
        }
    }
    Ok(indices.map(|i| active[i]))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::three_d::{Boundary3, Domain3, Generator3, HalfSpaceOracle3, Image3};
    use galaxy_types::{CellId, EntityId};

    #[test]
    fn matching_first_derivatives_do_not_certify_persistent_incidence() {
        let sites: Vec<_> = (0..8)
            .map(|i| Generator3 {
                id: CellId::new(EntityId::new(9, i)),
                position: std::array::from_fn(|k| if (i >> k) & 1 == 0 { 0.25 } else { 0.75 }),
                winding: Image3::ZERO,
            })
            .collect();
        let s = HalfSpaceOracle3::build_supported_periodic(
            Domain3 {
                anchor: [0.; 3],
                width: [1.; 3],
                boundary: Boundary3::Periodic,
            },
            &sites,
        )
        .unwrap();
        let g = s.geometry();
        let mut w = vec![[0.0; 3]; 8];
        w[7] = [0.125, -0.125, 0.0];
        for (i, f) in g.faces().iter().enumerate().filter(|(_, f)| f.left == 0) {
            let h = g.face_ref(i).unwrap();
            for (p, active) in f.polygon.iter().zip(s.vertex_supports(h).unwrap()) {
                if *p == [0.25; 3] {
                    assert_eq!(active.len(), 7);
                    for a in active {
                        let j = a.neighbour as usize;
                        let d = std::array::from_fn(|k| {
                            sites[j].position[k] - sites[0].position[k] + a.image.0[k] as f64 - p[k]
                        });
                        assert_eq!(dot(w[j], d), 0.0);
                    }
                    assert!(matches!(
                        basis(g, &w, 0, active),
                        Err(GeometryError3::InvalidTopology(
                            "non-simple moving periodic vertex"
                        ))
                    ));
                    return;
                }
            }
        }
        panic!("no positive octant vertex");
    }
}
