//! S-CENTROID. Each named selection also runs on its own REANA workflow.
use galaxy_types::{CellId, EntityId};
use moving_mesh::three_d::*;
use std::collections::BTreeMap;

const SITES: [Vec3; 2] = [[0.25, 7.0 / 16.0, 0.375], [0.75, 9.0 / 16.0, 0.625]];
const VELOCITIES: [Vec3; 2] = [
    [0.125, 3.0 / 16.0, -1.0 / 16.0],
    [-1.0 / 16.0, -0.125, 1.0 / 16.0],
];
const ZERO: Vec3 = [0.0; 3];
type Velocities = BTreeMap<CellId, Vec3>;

fn id(index: usize) -> CellId {
    CellId::new(EntityId::new(65, index as u64))
}
fn site(index: usize, position: Vec3) -> Generator3 {
    Generator3 {
        id: id(index),
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
fn perm(v: Vec3, axes: [usize; 3]) -> Vec3 {
    axes.map(|i| v[i])
}
fn maximum(v: Vec3) -> f64 {
    v.into_iter().map(f64::abs).fold(0.0, f64::max)
}
fn close(a: f64, b: f64) {
    assert!((a - b).abs() <= 1e-10, "actual {a:.17e}, expected {b:.17e}");
}
fn close3(a: Vec3, b: Vec3) {
    for (v, w) in a.into_iter().zip(b) {
        close(v, w);
    }
}
fn oblique(axes: [usize; 3], t: f64) -> ValidatedGeometry3 {
    let sites: Vec<_> = SITES
        .iter()
        .zip(VELOCITIES)
        .enumerate()
        .map(|(i, (r, v))| {
            site(
                i,
                perm(std::array::from_fn(|k| v[k].mul_add(t, r[k])), axes),
            )
        })
        .collect();
    HalfSpaceOracle3::build(domain(Boundary3::Bounded), &sites).unwrap()
}
fn flow(axes: [usize; 3]) -> Velocities {
    VELOCITIES
        .into_iter()
        .enumerate()
        .map(|(i, w)| (id(i), perm(w, axes)))
        .collect()
}
fn centroid(c: &CellGeometry3) -> Vec3 {
    std::array::from_fn(|k| c.generator.position[k] + c.centroid_offset[k])
}
fn observed(label: &str, i: usize, t: i32, v: f64, x: Vec3) {
    let [x, y, z] = x;
    println!("M2C {label} {i} {t} {v:.17e} {x:.17e} {y:.17e} {z:.17e}");
}

fn rebuilt_difference(axes: [usize; 3], power: i32) {
    let h = 2.0_f64.powi(-power);
    let start = oblique(axes, 0.0);
    let before = oblique(axes, -h);
    let after = oblique(axes, h);
    let field = flow(axes);
    let rates = prescribed_motion_rates3(&start, &field, ZERO).unwrap();
    assert_eq!(rates.epoch(), start.epoch());
    for g in [&before, &after] {
        assert!(
            start
                .faces()
                .iter()
                .map(|f| f.key)
                .eq(g.faces().iter().map(|f| f.key))
        );
    }
    let i = start
        .faces()
        .iter()
        .position(|f| f.right.is_some())
        .unwrap();
    let face = &start.faces()[i];
    let fr = rates.face(start.face_ref(i).unwrap()).unwrap();
    let a_dot = 5.0 / 128.0;
    close(fr.volume_flux, a_dot);
    // The explicit x = F(y,z,t) boundary gives the normal speed at *each*
    // vertex independently of the candidate's face moment or bisector formula.
    for vertex in &face.polygon {
        let mut v = ZERO;
        for (k, &axis) in axes.iter().enumerate() {
            v[axis] = vertex[k] + SITES[0][axis];
        }
        let exact = (a_dot + (17.0 / 32.0) * (v[1] - 0.5) - (7.0 / 16.0) * (v[2] - 0.5)) * 4.0
            / 21_f64.sqrt();
        let wn = fr.normal_speed
            + fr.normal_speed_gradient
                .iter()
                .enumerate()
                .map(|(k, g)| g * (vertex[k] - face.centroid_offset[k]))
                .sum::<f64>();
        close(wn, exact);
    }
    let left_c = perm([53.0 / 192.0, 11.0 / 24.0, 5.0 / 12.0], axes);
    let first_rate = perm([41.0 / 1536.0, 49.0 / 768.0, -13.0 / 768.0], axes);
    let mut volume_error = 0.0_f64;
    let mut centroid_error = 0.0_f64;
    let mut generator_gap = 0.0_f64;
    let mut omitted_gap = 0.0_f64;
    for (i, c) in start.cells().iter().enumerate() {
        let sign = if i == 0 { 1.0 } else { -1.0 };
        let expect_c = if i == 0 {
            left_c
        } else {
            left_c.map(|v| 1.0 - v)
        };
        let expect_v = std::array::from_fn(|k| 2.0 * sign * (first_rate[k] - expect_c[k] * a_dot));
        let rate = rates
            .cell(start.cell_by_id(c.generator.id).unwrap())
            .unwrap();
        close(c.volume, 0.5);
        close3(centroid(c), expect_c);
        close(rate.volume_rate, sign * a_dot);
        close3(rate.centroid_velocity, expect_v);
        observed("rate", i, 0, rate.volume_rate, rate.centroid_velocity);
        let get = |g: &ValidatedGeometry3| -> (f64, Vec3) {
            let cell = g.cell(g.cell_by_id(c.generator.id).unwrap()).unwrap();
            (cell.volume, centroid(cell))
        };
        let (vm, cm) = get(&before);
        let (vp, cp) = get(&after);
        observed("sample", i, -1, vm, cm);
        observed("sample", i, 0, c.volume, centroid(c));
        observed("sample", i, 1, vp, cp);
        volume_error = volume_error.max(((vp - vm) / (2.0 * h) - rate.volume_rate).abs());
        centroid_error = centroid_error.max(maximum(std::array::from_fn(|k| {
            (cp[k] - cm[k]) / (2.0 * h) - rate.centroid_velocity[k]
        })));
        generator_gap = generator_gap.max(maximum(std::array::from_fn(|k| {
            rate.centroid_velocity[k] - field[&c.generator.id][k]
        })));
        // Stationary walls have zero central moment flux. Only the single
        // internal face can contribute this term to these cells.
        omitted_gap = omitted_gap.max(maximum(fr.central_moment_flux.map(|x| x / c.volume)));
    }
    let [mx, my, mz] = fr.central_moment_flux;
    println!("M2C moment {mx:.17e} {my:.17e} {mz:.17e}");
    println!(
        "M2C errors {volume_error:.17e} {centroid_error:.17e} {generator_gap:.17e} {omitted_gap:.17e}"
    );
    assert!(generator_gap > 1e-2 && omitted_gap > 1e-2);
    if power == 11 {
        assert!(volume_error <= 1e-7 && centroid_error <= 1e-7);
    }
}

macro_rules! oblique_ladder {
    ($name:ident,$axes:expr) => {
        mod $name {
            use super::rebuilt_difference;
            #[test]
            fn h32() {
                rebuilt_difference($axes, 5);
            }
            #[test]
            fn h64() {
                rebuilt_difference($axes, 6);
            }
            #[test]
            fn h128() {
                rebuilt_difference($axes, 7);
            }
            #[test]
            fn h256() {
                rebuilt_difference($axes, 8);
            }
            #[test]
            fn h512() {
                rebuilt_difference($axes, 9);
            }
            #[test]
            fn h1024() {
                rebuilt_difference($axes, 10);
            }
            #[test]
            fn h2048() {
                rebuilt_difference($axes, 11);
            }
        }
    };
}
oblique_ladder!(xyz, [0, 1, 2]);
oblique_ladder!(xzy, [0, 2, 1]);
oblique_ladder!(yxz, [1, 0, 2]);
oblique_ladder!(yzx, [1, 2, 0]);
oblique_ladder!(zxy, [2, 0, 1]);
oblique_ladder!(zyx, [2, 1, 0]);

#[test]
fn periodic_self_image_rigid_translation() {
    let mut d = domain(Boundary3::Periodic);
    d.width = [2.0, 0.5, 4.0];
    let mut a = site(9, [1.75, 0.0625, 1.25]);
    a.winding = Image3([329, -17, 24]);
    let g = HalfSpaceOracle3::build(d, &[a]).unwrap();
    let w = [2.0, -1.0, 0.5];
    let rates = prescribed_motion_rates3(&g, &BTreeMap::from([(a.id, w)]), ZERO).unwrap();
    let cell = rates.cell(g.cell_by_id(a.id).unwrap()).unwrap();
    close(cell.volume_rate, 0.0);
    close3(cell.centroid_velocity, w);
    assert_eq!(g.faces().len(), 3);
    assert_eq!(g.cells()[0].incidences.len(), 6);
    for (i, f) in g.faces().iter().enumerate() {
        let r = rates.face(g.face_ref(i).unwrap()).unwrap();
        close(
            r.normal_speed,
            f.normal.iter().zip(w).map(|(n, v)| n * v).sum(),
        );
        close3(r.normal_speed_gradient, ZERO);
    }
}

#[test]
fn periodic_two_owner_seam_uses_both_image_velocities() {
    let mut a = site(5, [0.875, 0.375, 0.5]);
    a.winding = Image3([12, -2, 1]);
    let mut b = site(1, [0.125, 0.375, 0.5]);
    b.winding = Image3([-8, 3, 0]);
    let g = HalfSpaceOracle3::build(domain(Boundary3::Periodic), &[a, b]).unwrap();
    let v = BTreeMap::from([(a.id, [0.25, 0.25, -0.5]), (b.id, [-0.125, 0.25, -0.5])]);
    let rates = prescribed_motion_rates3(&g, &v, ZERO).unwrap();
    let mut count = 0;
    for (i, f) in g.faces().iter().enumerate() {
        if f.right != Some(f.left) {
            count += 1;
            let r = rates.face(g.face_ref(i).unwrap()).unwrap();
            close(r.normal_speed, f.normal[0] / 16.0);
        }
    }
    assert_eq!(count, 2);
    for c in g.cells() {
        let r = rates.cell(g.cell_by_id(c.generator.id).unwrap()).unwrap();
        close(r.volume_rate, 0.0);
        close3(r.centroid_velocity, [0.0625, 0.25, -0.5]);
    }
}

#[test]
fn fixed_walls_keep_centroid_stationary_while_generator_drifts() {
    let a = site(1, [0.125, 0.25, 0.75]);
    let g = HalfSpaceOracle3::build(domain(Boundary3::Bounded), &[a]).unwrap();
    let rates =
        prescribed_motion_rates3(&g, &BTreeMap::from([(a.id, [2.0, -1.0, 0.5])]), ZERO).unwrap();
    let r = rates.cell(g.cell_ref(0).unwrap()).unwrap();
    assert_eq!(r.centroid_velocity, ZERO);
    assert_eq!(r.volume_rate, 0.0);
    for i in 0..g.faces().len() {
        let f = rates.face(g.face_ref(i).unwrap()).unwrap();
        assert_eq!(f.normal_speed, 0.0);
        assert_eq!(f.central_moment_flux, ZERO);
    }
}

#[test]
fn rigid_bounded_translation_moves_every_centroid_with_the_walls() {
    let g = oblique([0, 1, 2], 0.0);
    let b = [2.0, -1.0, 0.5];
    let v = g.cells().iter().map(|c| (c.generator.id, b)).collect();
    let rates = prescribed_motion_rates3(&g, &v, b).unwrap();
    for i in 0..g.cells().len() {
        let r = rates.cell(g.cell_ref(i).unwrap()).unwrap();
        close(r.volume_rate, 0.0);
        close3(r.centroid_velocity, b);
    }
}

#[test]
fn a_joint_boost_shifts_centroid_velocity_on_the_deforming_box() {
    let axes = [2, 0, 1];
    let g = oblique(axes, 0.0);
    let b = [2.0, -1.0, 0.5];
    let v = flow(axes);
    let boosted = v
        .iter()
        .map(|(&id, w)| (id, std::array::from_fn(|k| w[k] + b[k])))
        .collect();
    let orig = prescribed_motion_rates3(&g, &v, ZERO).unwrap();
    let new = prescribed_motion_rates3(&g, &boosted, b).unwrap();
    for i in 0..g.cells().len() {
        let h = g.cell_ref(i).unwrap();
        let (r, s) = (orig.cell(h).unwrap(), new.cell(h).unwrap());
        close(r.volume_rate, s.volume_rate);
        close3(
            s.centroid_velocity,
            std::array::from_fn(|k| r.centroid_velocity[k] + b[k]),
        );
    }
}

#[test]
fn reject_incomplete_mismatched_and_nonfinite_velocity_fields() {
    let g = oblique([0, 1, 2], 0.0);
    let mut v = flow([0, 1, 2]);
    v.remove(&id(0));
    assert_eq!(
        prescribed_motion_rates3(&g, &v, ZERO).unwrap_err(),
        MotionRateError3::VelocityCatalogMismatch
    );
    v.insert(id(99), ZERO);
    assert_eq!(
        prescribed_motion_rates3(&g, &v, ZERO).unwrap_err(),
        MotionRateError3::VelocityCatalogMismatch
    );
    let mut v = flow([0, 1, 2]);
    assert_eq!(
        prescribed_motion_rates3(&g, &v, [f64::INFINITY, 0.0, 0.0]).unwrap_err(),
        MotionRateError3::NonFiniteWallVelocity
    );
    v.insert(id(1), [0.0, f64::NAN, 0.0]);
    assert_eq!(
        prescribed_motion_rates3(&g, &v, ZERO).unwrap_err(),
        MotionRateError3::NonFiniteVelocity(id(1))
    );
}

#[test]
fn reject_unrepresentable_integrated_face_flux() {
    let mut d = domain(Boundary3::Bounded);
    d.width = [4.0; 3];
    let a = site(1, [1.0; 3]);
    let g = HalfSpaceOracle3::build(d, &[a]).unwrap();
    assert!(matches!(
        prescribed_motion_rates3(
            &g,
            &BTreeMap::from([(a.id, ZERO)]),
            [f64::MAX / 2.0, 0.0, 0.0]
        ),
        Err(MotionRateError3::Unrepresentable(_))
    ));
}

#[test]
fn reject_indices_from_a_different_geometry_epoch() {
    let g = oblique([0, 1, 2], 0.0);
    let other = oblique([0, 1, 2], 0.0);
    let rates = prescribed_motion_rates3(&g, &flow([0, 1, 2]), ZERO).unwrap();
    assert_eq!(
        rates.cell(other.cell_ref(0).unwrap()),
        Err(GeometryError3::EpochMismatch)
    );
    assert_eq!(
        rates.face(other.face_ref(0).unwrap()),
        Err(GeometryError3::EpochMismatch)
    );
}
