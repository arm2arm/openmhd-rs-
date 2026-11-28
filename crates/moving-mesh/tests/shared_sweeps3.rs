use galaxy_types::{CellId, EntityId};
use moving_mesh::three_d::sweeps::{SharedSweeps3, SweepError3};
use moving_mesh::three_d::*;
use std::collections::BTreeMap;

type Velocity = BTreeMap<CellId, Vec3>;
fn site(i: usize, p: Vec3) -> Generator3 {
    Generator3 {
        id: CellId::new(EntityId::new(8, i as u64)),
        position: p,
        winding: Image3::ZERO,
    }
}
fn unit(boundary: Boundary3) -> Domain3 {
    Domain3 {
        anchor: [0.; 3],
        width: [1.; 3],
        boundary,
    }
}
fn smooth() -> (ValidatedGeometry3, Velocity) {
    let sites = [
        [0.15, 0.2, 0.25],
        [0.72, 0.3, 0.2],
        [0.35, 0.79, 0.4],
        [0.51, 0.41, 0.83],
        [0.8, 0.82, 0.64],
    ]
    .into_iter()
    .enumerate()
    .map(|(i, p)| site(i, p))
    .collect::<Vec<_>>();
    let speeds = [
        [0.1, -0.04, 0.03],
        [-0.06, 0.02, 0.14],
        [0.02, 0.08, -0.05],
        [0.1, 0.05, -0.09],
        [-0.08, -0.04, 0.02],
    ];
    let w = sites.iter().zip(speeds).map(|(s, v)| (s.id, v)).collect();
    (
        HalfSpaceOracle3::build(unit(Boundary3::Bounded), &sites).unwrap(),
        w,
    )
}
fn stages(
    g: &ValidatedGeometry3,
    w: &Velocity,
    dt: f64,
) -> (ValidatedGeometry3, SharedSweeps3, SharedSweeps3) {
    let h = advance_generators3(g, w, dt).unwrap().geometry;
    let a = prescribed_motion_rates3(g, w, [0.; 3]).unwrap();
    let b = prescribed_motion_rates3(&h, w, [0.; 3]).unwrap();
    let e = SharedSweeps3::euler(g, &a, &h, dt).unwrap();
    let t = SharedSweeps3::heun(g, &a, &h, &b, dt).unwrap();
    (h, e, t)
}
fn close(a: f64, b: f64, tol: f64) {
    assert!((a - b).abs() <= tol, "{a:.17e} {b:.17e} tol {tol:.3e}");
}

#[test]
fn two_site_plane_sweeps_analytic_signed_volume() {
    let sites = [site(0, [0.25, 0.5, 0.5]), site(1, [0.75, 0.5, 0.5])];
    let g = HalfSpaceOracle3::build(unit(Boundary3::Bounded), &sites).unwrap();
    let w = BTreeMap::from([(sites[0].id, [0.125, 0.0, 0.0]), (sites[1].id, [0.0; 3])]);
    let (h, e, t) = stages(&g, &w, 0.5);
    close(h.cells()[0].volume - g.cells()[0].volume, 1.0 / 32.0, 1e-15);
    for x in [e, t] {
        for (key, f) in x.faces() {
            close(f.correction, 0.0, 1e-15);
            close(
                f.raw,
                if matches!(key, FaceKey3::Interior { .. }) {
                    1.0 / 32.0
                } else {
                    0.0
                },
                1e-15,
            );
        }
        assert_eq!(x.components.len(), 1);
        close(x.components[0].grounded_condition_inf, 1.0, 1e-14);
    }
}
#[test]
fn periodic_self_image_keeps_metric_and_commits_zero_net_exchange() {
    let s = site(0, [0.75, 0.5, 0.5]);
    let g = HalfSpaceOracle3::build(unit(Boundary3::Periodic), &[s]).unwrap();
    let (h, _, t) = stages(&g, &BTreeMap::from([(s.id, [0.5, 0.0, 0.0])]), 1.0);
    assert_eq!(h.cells()[0].generator.winding.0[0], 1);
    assert_eq!(t.faces().len(), 3);
    assert!(t.faces().values().any(|s| s.raw.abs() > 0.4));
    assert!(t.faces().values().all(|s| s.correction == 0.0));
    let f = t.faces().keys().map(|&k| (k, [1.0e30, 3.5])).collect();
    let q = BTreeMap::from([(s.id, [1.25, -4.5])]);
    let ex = t.exchanges(&f, &q, Some(&q)).unwrap();
    assert_eq!(ex.faces, f);
    assert_eq!(ex.cell_increments[&s.id], [0.0; 2]);
}
#[test]
fn fixed_wall_keeps_prescribed_exchange_and_rejects_wall_motion() {
    let (g, w) = smooth();
    let (h, _, t) = stages(&g, &w, 0.03125);
    let q = g.cells().iter().map(|c| (c.generator.id, [3.0])).collect();
    let f = t
        .faces()
        .keys()
        .map(|&k| {
            (
                k,
                [if matches!(k, FaceKey3::Boundary { .. }) {
                    0.25
                } else {
                    0.0
                }],
            )
        })
        .collect();
    let ex = t.exchanges(&f, &q, Some(&q)).unwrap();
    let wall_sum: f64 = f
        .iter()
        .filter(|(k, _)| matches!(k, FaceKey3::Boundary { .. }))
        .map(|(_, v)| v[0])
        .sum();
    close(
        ex.cell_increments.values().map(|x| x[0]).sum(),
        -wall_sum,
        2e-13,
    );
    let moving = prescribed_motion_rates3(&g, &w, [0.25, 0., 0.]).unwrap();
    assert!(matches!(
        SharedSweeps3::euler(&g, &moving, &h, 0.03125),
        Err(SweepError3::MovingWall)
    ));
}
#[test]
fn constant_state_uses_rebuilt_volumes_for_predictor_and_corrector() {
    let (g, w) = smooth();
    let (h, e, t) = stages(&g, &w, 0.125);
    let u = [1.0, -2.0, 0.25, 3.0, 0.125];
    let q = g.cells().iter().map(|c| (c.generator.id, u)).collect();
    for (s, pred) in [(&e, None), (&t, Some(&q))] {
        let physical = s
            .faces()
            .iter()
            .map(|(&key, face)| (key, u.map(|x| -x * face.raw)))
            .collect();
        let actual = s.exchanges(&physical, &q, pred).unwrap();
        for (old, new) in g.cells().iter().zip(h.cells()) {
            for (k, x) in u.into_iter().enumerate() {
                close(
                    x * old.volume + actual.cell_increments[&old.generator.id][k],
                    x * new.volume,
                    3e-13 * new.volume,
                );
            }
        }
        assert!(s.max_raw_relative_defect > 1e-11);
        assert!(s.max_corrected_relative_defect < 1e-12);
    }
}
#[test]
fn smooth_shared_correction_has_euler_and_heun_orders() {
    let (g, w) = smooth();
    let mut history = Vec::new();
    for dt in [0.0625, 0.03125, 0.015625, 0.0078125] {
        let (_, e, t) = stages(&g, &w, dt);
        let norm = |s: &SharedSweeps3| {
            s.faces()
                .values()
                .map(|f| f.correction.abs())
                .fold(0.0, f64::max)
        };
        history.push([norm(&e), norm(&t)]);
    }
    println!("max |delta_S| by timestep: {history:?}");
    for pair in history.windows(2) {
        let e = (pair[0][0] / pair[1][0]).log2();
        let t = (pair[0][1] / pair[1][1]).log2();
        assert!(
            (1.8..2.2).contains(&e) && (2.8..3.2).contains(&t),
            "{e} {t} {history:?}"
        );
    }
}
#[test]
fn nonuniform_correction_uses_four_owner_samples_and_one_face() {
    let (g, w) = smooth();
    let (_, _, s) = stages(&g, &w, 0.125);
    let density = |base: f64| {
        g.cells()
            .iter()
            .enumerate()
            .map(|(i, c)| (c.generator.id, [base + i as f64]))
            .collect::<BTreeMap<_, _>>()
    };
    let old = density(1.0);
    let pred = density(7.0);
    let fs = s.faces().keys().map(|&k| (k, [0.35])).collect();
    let x = s.exchanges(&fs, &old, Some(&pred)).unwrap();
    let mut nonzero = false;
    for (k, f) in s.faces() {
        if let FaceKey3::Interior { lo, hi, .. } = k {
            let average = (old[lo][0] + old[hi][0] + pred[lo][0] + pred[hi][0]) / 4.0;
            close(x.faces[k][0], 0.35 - average * f.correction, 1e-16);
            nonzero |= f.correction.abs() > 1e-10;
        }
    }
    assert!(nonzero);
}
#[test]
fn endpoint_union_keeps_new_face_with_zero_predictor_weight() {
    let sites = [
        [0.1875, 0.25, 0.],
        [0.1875, -0.25, 0.],
        [-0.3125, 0., 0.],
        [0., 0., -0.3125],
        [0., 0., 0.375],
    ]
    .into_iter()
    .enumerate()
    .map(|(i, p)| site(i, p))
    .collect::<Vec<_>>();
    let d = Domain3 {
        anchor: [-1.; 3],
        width: [2.; 3],
        boundary: Boundary3::Bounded,
    };
    let g = HalfSpaceOracle3::build(d, &sites).unwrap();
    let mut w: Velocity = sites.iter().map(|s| (s.id, [0.; 3])).collect();
    w.insert(sites[4].id, [0., 0., -0.125]);
    let (_, e, t) = stages(&g, &w, 1.0);
    let k = FaceKey3::Interior {
        lo: sites[3].id,
        hi: sites[4].id,
        hi_image: Image3::ZERO,
    };
    assert_eq!(e.faces()[&k].weight, 0.0);
    assert_eq!(e.faces()[&k].raw, 0.0);
    assert_eq!(e.faces()[&k].correction, 0.0);
    assert!(t.faces()[&k].weight > 0.0);
    assert!(t.max_corrected_relative_defect <= 1e-12);
}
#[test]
fn changed_epoch_or_trajectory_does_not_reuse_sweep() {
    let (g, w) = smooth();
    let dt = 0.125;
    let h = advance_generators3(&g, &w, dt).unwrap().geometry;
    let a = prescribed_motion_rates3(&g, &w, [0.; 3]).unwrap();
    let mut other = w.clone();
    other.values_mut().next().unwrap()[0] += 0.125;
    let b = prescribed_motion_rates3(&h, &other, [0.; 3]).unwrap();
    assert!(matches!(
        SharedSweeps3::heun(&g, &a, &h, &a, dt),
        Err(SweepError3::Geometry(GeometryError3::EpochMismatch))
    ));
    assert!(matches!(
        SharedSweeps3::heun(&g, &a, &h, &b, dt),
        Err(SweepError3::ChangedTrajectory)
    ));
}
#[test]
fn exchange_requires_exact_face_owner_and_stage_catalogs() {
    let (g, w) = smooth();
    let (_, e, t) = stages(&g, &w, 0.25);
    let all: BTreeMap<_, _> = e.faces().keys().map(|&k| (k, [1.0])).collect();
    let q: BTreeMap<_, _> = g.cells().iter().map(|c| (c.generator.id, [2.0])).collect();
    assert!(e.exchanges(&all, &q, Some(&q)).is_err());
    assert!(t.exchanges(&all, &q, None).is_err());
    let mut bad = all.clone();
    bad.pop_first();
    assert!(t.exchanges(&bad, &q, Some(&q)).is_err());
    let mut nonfinite = q.clone();
    nonfinite.values_mut().next().unwrap()[0] = f64::NAN;
    assert!(e.exchanges(&all, &nonfinite, None).is_err());
    let mut missing = q.clone();
    missing.pop_last();
    assert!(e.exchanges(&all, &missing, None).is_err());
}
