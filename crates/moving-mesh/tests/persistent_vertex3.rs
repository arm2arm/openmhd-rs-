use galaxy_types::{CellId, EntityId};
use moving_mesh::three_d::*;
use std::collections::BTreeMap;

fn cartesian(x: &[f64], yz: &[f64]) -> Vec<Generator3> {
    let mut sites = Vec::new();
    for &z in yz {
        for &y in yz {
            for &a in x {
                sites.push(Generator3 {
                    id: CellId::new(EntityId::new(9, sites.len() as u64)),
                    position: [a, y, z],
                    winding: Image3::ZERO,
                });
            }
        }
    }
    sites
}

fn periodic() -> Domain3 {
    Domain3 {
        anchor: [0.; 3],
        width: [1.; 3],
        boundary: Boundary3::Periodic,
    }
}
fn close(a: f64, b: f64) {
    assert!((a - b).abs() < 1e-13, "{a:.17e} vs {b:.17e}");
}

#[test]
fn separable_nonrigid_tensor_motion_matches_rectangular_face_moments() {
    let xs = [0.125, 0.4375, 0.8125];
    let yz = [0.25, 0.75];
    let vx = [0.0625, -0.125, 0.25];
    let sites = cartesian(&xs, &yz);
    let g = HalfSpaceOracle3::build_supported_periodic(periodic(), &sites).unwrap();
    let w = sites
        .iter()
        .enumerate()
        .map(|(i, s)| (s.id, [vx[i % 3], 0.0, 0.0]))
        .collect();
    let rates = PrescribedPolygonRates3::build(&g, &w).unwrap();
    let geom = g.geometry();
    let mut multiple = 0;
    for (i, f) in geom.faces().iter().enumerate() {
        let h = geom.face_ref(i).unwrap();
        multiple += g
            .vertex_supports(h)
            .unwrap()
            .iter()
            .filter(|s| s.len() > 3)
            .count();
        let r = rates.face(h).unwrap();
        let ix = f.left as usize % 3;
        let prev = (ix + 2) % 3;
        let next = (ix + 1) % 3;
        let axis = f.normal.iter().position(|v| v.abs() == 1.).unwrap();
        let (cx, da, covxx) = if axis == 0 {
            let peer = f.right.unwrap() as usize % 3;
            ((vx[ix] + vx[peer]) / 2., 0.0, 0.0)
        } else {
            let width =
                ((xs[next] - xs[ix]).rem_euclid(1.) + (xs[ix] - xs[prev]).rem_euclid(1.)) / 2.;
            let dw = (vx[next] - vx[prev]) / 2.;
            (
                (vx[prev] + 2. * vx[ix] + vx[next]) / 4.,
                dw / 2.,
                width * dw / 6.,
            )
        };
        close(r.centroid_velocity[0], cx);
        close(r.centroid_velocity[1], 0.0);
        close(r.centroid_velocity[2], 0.0);
        for (k, n) in f.normal.iter().enumerate() {
            close(r.area_vector_rate[k], da * n);
        }
        for (k, row) in r.covariance_rate.iter().enumerate() {
            for (j, &c) in row.iter().enumerate() {
                close(c, if k == 0 && j == 0 { covxx } else { 0.0 });
            }
        }
    }
    assert!(multiple > 0);
}

#[test]
fn registered_shear_has_incompatible_axial_and_diagonal_planes() {
    let xs = [0.125, 0.375, 0.625, 0.875];
    let sites = cartesian(&xs, &xs);
    let g = HalfSpaceOracle3::build_supported_periodic(periodic(), &sites).unwrap();
    let w: BTreeMap<_, Vec3> = sites
        .iter()
        .map(|s| {
            (
                s.id,
                std::array::from_fn(|d| {
                    0.05 * (std::f64::consts::TAU * s.position[(d + 1) % 3]).sin()
                }),
            )
        })
        .collect();
    let v = w[&sites[21].id];
    let v_x = w[&sites[22].id];
    let v_y = w[&sites[25].id];
    let v_xy = w[&sites[26].id];
    // Relative centre (.125,.125,.125). The X and Y bisectors force
    // derivatives along X and Y that violate the XY diagonal equation.
    let rhs = |velocity: Vec3, d: Vec3| {
        (0..3)
            .map(|k| (velocity[k] - v[k]) * (d[k] - 0.125))
            .sum::<f64>()
    };
    let from_xy = rhs(v_x, [0.25, 0., 0.]) + rhs(v_y, [0., 0.25, 0.]);
    let diagonal = rhs(v_xy, [0.25, 0.25, 0.]);
    println!(
        "same-vertex four-plane incompatibility: axial={from_xy:.17e}, diagonal={diagonal:.17e}"
    );
    assert!(from_xy - diagonal > 0.017);
    let left = 21;
    let mut verified = false;
    for (i, f) in g
        .geometry()
        .faces()
        .iter()
        .enumerate()
        .filter(|(_, f)| f.left == left)
    {
        let h = g.geometry().face_ref(i).unwrap();
        for (p, active) in f.polygon.iter().zip(g.vertex_supports(h).unwrap()) {
            if *p == [0.125; 3] {
                for j in [22, 25, 26] {
                    assert!(active.contains(&VertexPlane3 {
                        neighbour: j,
                        image: Image3::ZERO
                    }));
                }
                verified = true;
            }
        }
    }
    assert!(verified);
    assert!(matches!(
        PrescribedPolygonRates3::build(&g, &w),
        Err(GeometryError3::InvalidTopology(
            "non-simple moving periodic vertex"
        ))
    ));
}
