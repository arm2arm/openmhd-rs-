//! Endpoint geometry and independently derived orientation, winding and motion controls.
use galaxy_types::{CellId, EntityId};
use moving_mesh::three_d::*;
use std::collections::BTreeMap;

type Velocities = BTreeMap<CellId, Vec3>;
const ZERO: Vec3 = [0.0; 3];

fn site(i: usize, position: Vec3) -> Generator3 {
    Generator3 {
        id: CellId::new(EntityId::new(8, i as u64)),
        position,
        winding: Image3::ZERO,
    }
}
fn domain(boundary: Boundary3) -> Domain3 {
    Domain3 {
        anchor: ZERO,
        width: [1.0; 3],
        boundary,
    }
}
fn flow(g: &ValidatedGeometry3, value: Vec3) -> Velocities {
    g.cells().iter().map(|c| (c.generator.id, value)).collect()
}
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
    std::array::from_fn(|k| a[k] - b[k])
}
fn close(a: f64, b: f64, tol: f64) {
    assert!(
        (a - b).abs() <= tol,
        "actual={a:.17e} expected={b:.17e} tol={tol:.4e}"
    );
}
fn near_vec(a: Vec3, b: Vec3, tol: f64) {
    for (x, y) in a.into_iter().zip(b) {
        close(x, y, tol);
    }
}

// Recompute area from oriented triangles and cell volume from signed tetrahedra.
// No reduction below uses the candidate's cached orientation/closure diagnostics.
fn audit(g: &ValidatedGeometry3) {
    let mut counts = vec![[0_u8; 2]; g.faces().len()];
    for (i, c) in g.cells().iter().enumerate() {
        let mut volume = 0.0;
        let mut closure = ZERO;
        for f in g.oriented_faces(g.cell_ref(i).unwrap()).unwrap() {
            let shared = g.face(f.handle).unwrap();
            assert!(std::ptr::eq(shared, f.shared));
            let positive = f.incidence.sign == 1;
            assert_eq!(f.incidence.sign, if positive { 1 } else { -1 });
            assert_eq!(
                Some(i as u32),
                if positive {
                    Some(shared.left)
                } else {
                    shared.right
                }
            );
            counts[f.handle.index() as usize][usize::from(!positive)] += 1;
            let normal = f.outward_normal();
            let vertices = f.vertices().collect::<Vec<_>>();
            let mut area = 0.0;
            let mut centroid = ZERO;
            for pair in vertices[1..].windows(2) {
                let vector = cross(sub(pair[0], vertices[0]), sub(pair[1], vertices[0]));
                let a = 0.5 * dot(vector, normal);
                assert!(a > 0.0, "reversed or collapsed triangle {a}");
                area += a;
                volume += dot(vertices[0], cross(pair[0], pair[1])) / 6.0;
                for k in 0..3 {
                    centroid[k] += a * (vertices[0][k] + pair[0][k] + pair[1][k]) / 3.0;
                    closure[k] += 0.5 * vector[k];
                }
            }
            close(area, shared.area, 1e-10 * shared.area);
            near_vec(centroid.map(|v| v / area), f.centroid_offset(), 1e-10);
        }
        near_vec(closure, ZERO, 1e-10 * c.surface_area);
        close(volume, c.volume, 1e-10 * c.volume);
    }
    for (c, f) in counts.into_iter().zip(g.faces()) {
        assert_eq!(c, [1, u8::from(f.right.is_some())]);
    }
    let expected: f64 = g.domain().width.iter().product();
    close(
        g.cells().iter().map(|c| c.volume).sum(),
        expected,
        1e-10 * expected,
    );
}

fn audit_changes(old: &ValidatedGeometry3, step: &MeshStep3) {
    let new = &step.geometry;
    let mut old_count = 0;
    let mut new_count = 0;
    for (&key, &change) in &step.face_changes {
        let (from, to) = match change {
            FaceChange3::Retained { previous, current } => (Some(previous), Some(current)),
            FaceChange3::Disappeared(previous) => (Some(previous), None),
            FaceChange3::Appeared(current) => (None, Some(current)),
        };
        if let Some(h) = from {
            assert_eq!(old.face(h).unwrap().key, key);
            assert!(matches!(new.face(h), Err(GeometryError3::EpochMismatch)));
            old_count += 1;
        }
        if let Some(h) = to {
            assert_eq!(new.face(h).unwrap().key, key);
            assert!(matches!(old.face(h), Err(GeometryError3::EpochMismatch)));
            new_count += 1;
        }
    }
    assert_eq!(
        (old_count, new_count),
        (old.faces().len(), new.faces().len())
    );
}

fn grid(n: usize, boundary: Boundary3) -> ValidatedGeometry3 {
    let mut sites = Vec::new();
    for k in 0..n {
        for j in 0..n {
            for i in 0..n {
                sites.push(site(
                    sites.len(),
                    [i, j, k].map(|q| (q as f64 + 0.5) / n as f64),
                ));
            }
        }
    }
    sites.reverse();
    HalfSpaceOracle3::build(domain(boundary), &sites).unwrap()
}

fn rigid(n: usize) {
    let start = grid(n, Boundary3::Periodic);
    let velocity = [2.0, -1.0, 0.5];
    let dt = 2.75;
    let step = advance_generators3(&start, &flow(&start, velocity), dt).unwrap();
    audit_changes(&start, &step);
    let end = &step.geometry;
    audit(end);
    for (old, new) in start.cells().iter().zip(end.cells()) {
        assert_eq!(old.generator.id, new.generator.id);
        let lift = std::array::from_fn::<_, 3, _>(|a| old.generator.position[a] + dt * velocity[a]);
        assert_eq!(new.generator.winding.0, lift.map(|x| x.floor() as i64));
        assert_eq!(new.generator.position, lift.map(|x| x - x.floor()));
        close(new.volume, old.volume, 1e-10 * old.volume);
        near_vec(old.centroid_offset, new.centroid_offset, 1e-10);
    }
    for change in step.face_changes.values() {
        let FaceChange3::Retained { previous, current } = *change else {
            panic!("translation changed neighbours")
        };
        let a = start.face(previous).unwrap();
        let b = end.face(current).unwrap();
        close(a.area, b.area, 1e-10 * a.area);
        near_vec(a.normal, b.normal, 1e-10);
    }
    println!(
        "RIGID n={n} cells={} faces={} volume_closure={:.17e}",
        end.cells().len(),
        end.faces().len(),
        end.quality().relative_volume_closure
    );
}
#[test]
#[ignore = "release-scale M01 REANA case"]
fn rigid_4_cubed_multiple_wraps() {
    rigid(4);
}
#[test]
#[ignore = "release-scale M01 REANA case"]
fn rigid_8_cubed_multiple_wraps() {
    rigid(8);
}

#[test]
fn periodic_self_faces_keep_both_charts_and_the_same_fan() {
    let mut s = site(0, [0.875, 0.125, 0.5]);
    s.winding = Image3([1_i64 << 54, -(1_i64 << 54), 3]);
    let start = HalfSpaceOracle3::build(domain(Boundary3::Periodic), &[s]).unwrap();
    let end = advance_generators3(&start, &flow(&start, [2.25, -1.25, 0.5]), 1.0).unwrap();
    audit_changes(&start, &end);
    audit(&end.geometry);
    let g = &end.geometry;
    let c = &g.cells()[0];
    assert_eq!(c.generator.position, [0.125, 0.875, 0.0]);
    assert_eq!(
        c.generator.winding.0,
        [s.winding.0[0] + 3, s.winding.0[1] - 2, 4]
    );
    for f in g.faces() {
        let pair = g
            .oriented_faces(g.cell_ref(0).unwrap())
            .unwrap()
            .filter(|v| v.shared.key == f.key)
            .collect::<Vec<_>>();
        assert_eq!(pair.len(), 2);
        let a = pair.iter().find(|v| v.incidence.sign == 1).unwrap();
        let b = pair.iter().find(|v| v.incidence.sign == -1).unwrap();
        let (id, img) = a.incidence.neighbour.unwrap();
        assert_eq!(
            b.incidence.neighbour,
            Some((id, img.checked_neg().unwrap()))
        );
        assert_eq!(a.outward_normal(), b.outward_normal().map(|v| -v));
        let left: Vec<_> = a.vertices().collect();
        for (i, v) in b.vertices().enumerate() {
            let j = (left.len() - i) % left.len();
            near_vec(sub(v, b.incidence.chart_translation), left[j], 0.0);
        }
    }
}
#[test]
fn axial_face_is_born_at_contact_and_removed_on_reversal() {
    let positions = [
        [3.0 / 16.0, 0.25, 0.0],
        [3.0 / 16.0, -0.25, 0.0],
        [-5.0 / 16.0, 0.0, 0.0],
        [0.0, 0.0, -5.0 / 16.0],
        [0.0, 0.0, 6.0 / 16.0],
    ];
    let sites: Vec<_> = positions
        .into_iter()
        .enumerate()
        .map(|(i, p)| site(i, p))
        .collect();
    let d = Domain3 {
        anchor: [-1.0; 3],
        width: [2.0; 3],
        boundary: Boundary3::Bounded,
    };
    let start = HalfSpaceOracle3::build(d, &sites).unwrap();
    let mut v = flow(&start, ZERO);
    v.insert(sites[4].id, [0.0, 0.0, -0.125]);
    let key = FaceKey3::Interior {
        lo: sites[3].id,
        hi: sites[4].id,
        hi_image: Image3::ZERO,
    };
    let contact = advance_generators3(&start, &v, 0.5).unwrap();
    assert!(!contact.face_changes.contains_key(&key));
    let opened = advance_generators3(&contact.geometry, &v, 0.5).unwrap();
    let FaceChange3::Appeared(h) = opened.face_changes[&key] else {
        panic!("positive-area face missing")
    };
    let f = opened.geometry.face(h).unwrap();
    assert_eq!(f.polygon.len(), 3);
    near_vec(f.normal, [0.0, 0.0, 1.0], 1e-12);
    close(f.area, 1.0 / 192.0, 1e-13);
    let center: Vec3 = std::array::from_fn(|k| sites[3].position[k] + f.centroid_offset[k]);
    near_vec(center, [-1.0 / 288.0, 0.0, -1.0 / 32.0], 1e-12);
    v.insert(sites[4].id, [0.0, 0.0, 0.125]);
    let closed = advance_generators3(&opened.geometry, &v, 1.0).unwrap();
    assert!(matches!(closed.face_changes[&key],FaceChange3::Disappeared(found) if found==h));
    assert!(
        closed
            .geometry
            .faces()
            .iter()
            .map(|f| f.key)
            .eq(start.faces().iter().map(|f| f.key))
    );
    for (old, step) in [
        (&start, &contact),
        (&contact.geometry, &opened),
        (&opened.geometry, &closed),
    ] {
        audit_changes(old, step);
        audit(&step.geometry);
    }
    println!(
        "FLIP area={:.17e} centroid={center:?} sides=2 vertices={}",
        f.area,
        f.polygon.len()
    );
}

#[test]
fn rejected_step_leaves_source_epoch_and_geometry_intact() {
    let sites = [site(0, [0.25, 0.5, 0.5]), site(1, [0.75, 0.5, 0.5])];
    let start = HalfSpaceOracle3::build(domain(Boundary3::Bounded), &sites).unwrap();
    let h = start.cell_ref(0).unwrap();
    let base = flow(&start, ZERO);
    for t in [0.0, -1.0, f64::NAN, f64::INFINITY] {
        assert_eq!(
            advance_generators3(&start, &base, t).unwrap_err(),
            MeshStepError3::InvalidTimestep
        );
    }
    let mut v = base.clone();
    v.remove(&sites[1].id);
    assert_eq!(
        advance_generators3(&start, &v, 1.0).unwrap_err(),
        MeshStepError3::VelocityCatalogMismatch
    );
    v.insert(site(42, ZERO).id, ZERO);
    assert_eq!(
        advance_generators3(&start, &v, 1.0).unwrap_err(),
        MeshStepError3::VelocityCatalogMismatch
    );
    let mut v = base;
    v.insert(sites[1].id, [f64::NAN, 0.0, 0.0]);
    assert_eq!(
        advance_generators3(&start, &v, 1.0).unwrap_err(),
        MeshStepError3::NonFiniteVelocity(sites[1].id)
    );
    v.insert(sites[1].id, [-0.5, 0.0, 0.0]);
    assert!(matches!(
        advance_generators3(&start, &v, 1.0),
        Err(MeshStepError3::Geometry(
            GeometryError3::CoincidentGenerators { .. }
        ))
    ));
    v.insert(sites[1].id, [0.25, 0.0, 0.0]);
    assert!(matches!(
        advance_generators3(&start, &v, 1.0),
        Err(MeshStepError3::Geometry(
            GeometryError3::GeneratorOutside { .. }
        ))
    ));
    let mut lone = sites[0];
    lone.winding = Image3([i64::MAX, 0, 0]);
    let g = HalfSpaceOracle3::build(domain(Boundary3::Periodic), &[lone]).unwrap();
    assert!(matches!(
        advance_generators3(&g, &flow(&g, [1.0, 0.0, 0.0]), 1.0),
        Err(MeshStepError3::Geometry(GeometryError3::ImageOverflow))
    ));
    assert_eq!(start.cell(h).unwrap().generator.position, sites[0].position);
    audit(&start);
}

fn speed(axis: usize, j: usize) -> f64 {
    [0.125, 0.0625, -0.125][axis] * [0.0, 1.0, 0.0, -1.0][j]
}

// In a Cartesian product mesh the two faces in an axis are arithmetic
// midplanes, or a fixed wall. This reference does not use candidate face records.
fn exact_axis(axis: usize, j: usize, boundary: Boundary3) -> (f64, f64) {
    let w = speed(axis, j);
    let left = if boundary == Boundary3::Bounded && j == 0 {
        0.0
    } else {
        (w + speed(axis, (j + 3) % 4)) * 0.5
    };
    let right = if boundary == Boundary3::Bounded && j == 3 {
        0.0
    } else {
        (w + speed(axis, (j + 1) % 4)) * 0.5
    };
    (right - left, (right + left) * 0.5)
}

fn smooth(boundary: Boundary3, den: u32) {
    let g = grid(4, boundary);
    let h = 1.0 / f64::from(den);
    let mut w = Velocities::new();
    for c in g.cells() {
        let j = c.generator.position.map(|p| (4.0 * p) as usize);
        w.insert(c.generator.id, std::array::from_fn(|a| speed(a, j[a])));
    }
    let backwards = w.iter().map(|(&id, &v)| (id, v.map(|e| -e))).collect();
    let minus = advance_generators3(&g, &backwards, h).unwrap();
    let plus = advance_generators3(&g, &w, h).unwrap();
    let rates = prescribed_motion_rates3(&g, &w, ZERO).unwrap();
    let mut worst: f64 = 0.0;
    let mut expected: f64 = 0.0;
    for (i, c) in g.cells().iter().enumerate() {
        let j = c.generator.position.map(|p| (4.0 * p) as usize);
        let slopes: Vec3 = std::array::from_fn(|a| exact_axis(a, j[a], boundary).0);
        let centroid_velocity: Vec3 = std::array::from_fn(|a| exact_axis(a, j[a], boundary).1);
        let rate = rates.cell(g.cell_ref(i).unwrap()).unwrap();
        let vdot = slopes.into_iter().sum::<f64>() / 16.0;
        close(rate.volume_rate, vdot, 1e-12);
        near_vec(rate.centroid_velocity, centroid_velocity, 1e-12);
        for (direction, mesh) in [(-1.0, &minus.geometry), (1.0, &plus.geometry)] {
            let end = &mesh.cells()[i];
            let exact_volume = slopes
                .into_iter()
                .map(|s| 0.25 + direction * h * s)
                .product::<f64>();
            close(end.volume, exact_volume, 1e-12);
            let measured =
                std::array::from_fn(|a| end.generator.position[a] + end.centroid_offset[a]);
            let exact = std::array::from_fn(|a| {
                c.generator.position[a] + direction * h * centroid_velocity[a]
            });
            near_vec(measured, exact, 1e-12);
        }
        let fd = (plus.geometry.cells()[i].volume - minus.geometry.cells()[i].volume) / (2.0 * h);
        worst = worst.max((fd - rate.volume_rate).abs() * 64.0);
        expected = expected.max(64.0 * h * h * slopes.into_iter().product::<f64>().abs());
    }
    for (i, face) in g.faces().iter().enumerate() {
        let normal_speed = face.right.map_or(0.0, |right| {
            let l = w[&g.cells()[face.left as usize].generator.id];
            let r = w[&g.cells()[right as usize].generator.id];
            0.5 * (dot(l, face.normal) + dot(r, face.normal))
        });
        close(
            rates.face(g.face_ref(i).unwrap()).unwrap().normal_speed,
            normal_speed,
            1e-12,
        );
    }
    for step in [&minus, &plus] {
        audit_changes(&g, step);
        audit(&step.geometry);
        assert!(
            step.face_changes
                .values()
                .all(|c| matches!(c, FaceChange3::Retained { .. }))
        );
    }
    close(worst, expected, 2e-11);
    if den == 1024 {
        assert!(worst <= 1e-7);
    }
    println!(
        "SMOOTH boundary={boundary:?} inverse_h={den} scaled_fd_error={worst:.17e} analytic={expected:.17e}"
    );
}
macro_rules! smooth_case {
    ($name:ident,$boundary:ident,$den:literal) => {
        #[test]
        #[ignore = "release-scale M01 REANA case"]
        fn $name() {
            smooth(Boundary3::$boundary, $den);
        }
    };
}
smooth_case!(bounded_h128, Bounded, 128);
smooth_case!(bounded_h256, Bounded, 256);
smooth_case!(bounded_h512, Bounded, 512);
smooth_case!(bounded_h1024, Bounded, 1024);
smooth_case!(periodic_h128, Periodic, 128);
smooth_case!(periodic_h256, Periodic, 256);
smooth_case!(periodic_h512, Periodic, 512);
smooth_case!(periodic_h1024, Periodic, 1024);

#[test]
fn irregular_periodic_deformation_is_invariant_to_input_order() {
    let points = [
        [0.125, 0.25, 0.375],
        [0.625, 0.125, 0.25],
        [0.3125, 0.6875, 0.1875],
        [0.8125, 0.75, 0.3125],
        [0.1875, 0.125, 0.6875],
        [0.75, 0.375, 0.8125],
        [0.1875, 0.8125, 0.625],
        [0.875, 0.625, 0.75],
    ];
    let mut sites: Vec<_> = points
        .into_iter()
        .enumerate()
        .map(|(i, p)| site(i, p))
        .collect();
    let v: Velocities = sites
        .iter()
        .map(|s| {
            let [x, y, z] = s.position;
            (s.id, [0.25 + y * 0.125, z * 0.0625, -x * 0.125])
        })
        .collect();
    let d = domain(Boundary3::Periodic);
    let start = HalfSpaceOracle3::build(d, &sites).unwrap();
    let a = advance_generators3(&start, &v, 0.5).unwrap();
    sites.reverse();
    let b = advance_generators3(&HalfSpaceOracle3::build(d, &sites).unwrap(), &v, 0.5).unwrap();
    audit_changes(&start, &a);
    audit(&a.geometry);
    assert!(a.face_changes.keys().eq(b.face_changes.keys()));
    assert!(
        a.geometry
            .cells()
            .iter()
            .any(|c| c.generator.winding.0[0] == 1)
    );
    for (x, y) in a.geometry.faces().iter().zip(b.geometry.faces()) {
        assert_eq!(
            (x.key, x.normal, x.area, &x.polygon),
            (y.key, y.normal, y.area, &y.polygon)
        );
    }
}
