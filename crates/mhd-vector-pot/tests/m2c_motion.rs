//! Fixed-sample periodic point-curl derivative and separate transported sample checks.
use mhd_vector_pot::operators3::{DiscreteCurl3, MovingPointCurl3};
use moving_mesh::three_d::{
    fit::*,
    operator_mesh::{CellId, MeshFit3, OperatorMesh3},
    *,
};
use std::collections::BTreeMap;

const ZERO: Vec3 = [0.; 3];
fn id(i: usize) -> CellId {
    SampleKey3::from_words(27, i as u64, Image3::ZERO).owner
}
fn q(j: usize) -> f64 {
    (j % 3) as f64 - 1.
}
fn coord(i: usize) -> [usize; 3] {
    [i % 3, (i / 3) % 3, i / 9]
}
fn velocity(i: usize) -> Vec3 {
    std::array::from_fn(|k| q(coord(i)[k] + k) / 16.)
}
fn geometry(t: f64, boundary: Boundary3) -> ValidatedGeometry3 {
    let sites: Vec<_> = (0..27)
        .map(|i| {
            let pos = std::array::from_fn(|k| {
                (coord(i)[k] as f64 + 0.5) / 3. + q(coord(i)[k] + 2 * k) / 64. + t * velocity(i)[k]
            });
            Generator3 {
                id: id(i),
                position: pos,
                winding: Image3::ZERO,
            }
        })
        .collect();
    HalfSpaceOracle3::build(
        Domain3 {
            anchor: ZERO,
            width: [1.; 3],
            boundary,
        },
        &sites,
    )
    .unwrap()
}
fn velocities() -> BTreeMap<CellId, Vec3> {
    (0..27).map(|i| (id(i), velocity(i))).collect()
}
fn field(i: usize) -> Vec3 {
    [
        ((13 * i * i + 3 * i + 7) % 31) as f64 - 15.,
        ((5 * i * i + 17 * i + 3) % 37) as f64 - 18.,
        ((7 * i * i + 11 * i + 5) % 41) as f64 - 20.,
    ]
    .map(|x| x / 16.)
}
fn fits(g: &ValidatedGeometry3) -> Vec<MeshFit3> {
    let m = OperatorMesh3::from_validated(g).unwrap();
    (0..m.cells().len())
        .map(|i| m.fit(i, FitOrder3::Quadratic).unwrap())
        .collect()
}
fn close(x: f64, y: f64) {
    assert!(
        (x - y).abs() <= 1e-12 * x.abs().max(y.abs()).max(1.),
        "{x:.17e} {y:.17e}"
    )
}
fn sample_difference(power: i32) {
    let h = 2.0_f64.powi(-power);
    let g = geometry(0., Boundary3::Periodic);
    let a: Vec<_> = (0..27).map(field).collect();
    let motion = prescribed_motion_rates3(&g, &velocities(), ZERO).unwrap();
    let plan = MovingPointCurl3::assemble(&g, &motion).unwrap();
    let (_, tangent) = plan.operators(&g, &motion).unwrap();
    let analytic = tangent.apply(&a).unwrap();
    let base = fits(&g);
    let rebuilt = |t: f64| {
        let other = geometry(t, Boundary3::Periodic);
        assert!(
            other
                .faces()
                .iter()
                .map(|f| f.key)
                .eq(g.faces().iter().map(|f| f.key))
        );
        let new = fits(&other);
        for (u, v) in base.iter().zip(&new) {
            assert_eq!(u.rings, v.rings);
            assert!(
                u.fit
                    .samples()
                    .iter()
                    .map(|r| r.key)
                    .eq(v.fit.samples().iter().map(|r| r.key))
            );
        }
        DiscreteCurl3::assemble(&new).unwrap().apply(&a).unwrap()
    };
    let minus = rebuilt(-h);
    let plus = rebuilt(h);
    let mut largest = 0_f64;
    let mut scale = 1_f64;
    for (i, ((m, p), d)) in minus.iter().zip(&plus).zip(&analytic).enumerate() {
        for (k, ((&lo, &hi), &rate)) in m.iter().zip(p).zip(d).enumerate() {
            println!("CDOT {power} {i} {k} {lo:.17e} {hi:.17e} {rate:.17e}");
            largest = largest.max(((hi - lo) / (2. * h) - rate).abs());
            scale = scale.max(rate.abs());
        }
    }
    let (cond, inverse) = plan.fit_sensitivity();
    println!("QUALITY {cond:.17e} {inverse:.17e}");
    assert!(
        cond.is_finite()
            && inverse.is_finite()
            && analytic.iter().flatten().any(|v| v.abs() > 1e-4)
            && largest.is_finite()
    );
    if power == 10 {
        assert!(
            largest / scale <= 1e-7,
            "scaled error {:.17e}",
            largest / scale
        );
    }
}
macro_rules! difference_tests {($($name:ident:$power:literal),+) => {$(#[test] fn $name(){sample_difference($power);})+};}
difference_tests!(h16:4,h32:5,h64:6,h128:7,h256:8,h512:9,h1024:10);

#[test]
fn moving_polynomial_chain_rule() {
    let mut samples = Vec::new();
    for i in 0..27 {
        if i == 13 {
            continue;
        }
        let d = coord(i).map(|v| q(v) / 3.);
        samples.push(StencilSample3 {
            key: SampleKey3::from_words(91, i as u64, Image3::ZERO),
            displacement: d,
            face_area: Some(1.),
        });
    }
    let l = [
        [0.25, -0.125, 0.5],
        [0.0625, 0.375, -0.25],
        [-0.5, 0.125, -0.125],
    ];
    let fit = PointFit3::build(FitOrder3::Quadratic, 1. / 27., samples).unwrap();
    let dot = |v: Vec3, w: Vec3| v.into_iter().zip(w).map(|(a, b)| a * b).sum::<f64>();
    let velocities: Vec<_> = fit
        .samples()
        .iter()
        .map(|s| l.map(|r| dot(r, s.displacement)))
        .collect();
    let derivatives = fit
        .quadratic_gradient_rate(&velocities, l[0][0] + l[1][1] + l[2][2])
        .unwrap();
    for (i, j) in [
        (3, 3),
        (0, 3),
        (1, 3),
        (2, 3),
        (0, 0),
        (1, 1),
        (2, 2),
        (0, 1),
        (0, 2),
        (1, 2),
    ] {
        let mut y = Vec::new();
        let mut dy = Vec::new();
        for (s, v) in fit.samples().iter().zip(&velocities) {
            let [x, y1, z] = s.displacement;
            let u = [x, y1, z, 1.];
            let du = [v[0], v[1], v[2], 0.];
            y.push(u[i] * u[j]);
            dy.push(du[i] * u[j] + u[i] * du[j]);
        }
        let transported = fit.apply(&dy).unwrap().gradient;
        for (k, &transport) in transported.iter().enumerate() {
            let frozen: f64 = derivatives
                .iter()
                .zip(&y)
                .map(|(r, v)| r[k] * (v - y[0]))
                .sum();
            let expected = if j == 3 && i < 3 { -l[i][k] } else { 0. };
            close(frozen, expected);
            close(frozen + transport, 0.);
        }
    }
    assert!(fit.quadratic_gradient_rate(&[], 1.).is_err());
    assert!(fit.quadratic_gradient_rate(&velocities, f64::NAN).is_err());
    let linear = PointFit3::build(FitOrder3::Linear, 1., fit.samples().to_vec()).unwrap();
    assert!(linear.quadratic_gradient_rate(&velocities, 0.).is_err());
}

#[test]
fn coalesced_transpose_diagonal_and_constants() {
    let g = geometry(0., Boundary3::Periodic);
    let motion = prescribed_motion_rates3(&g, &velocities(), ZERO).unwrap();
    let plan = MovingPointCurl3::assemble(&g, &motion).unwrap();
    let (c, d) = plan.operators(&g, &motion).unwrap();
    let fs = fits(&g);
    assert!(fs.iter().any(|r| {
        let mut ids = r.owners.clone();
        ids.sort();
        ids.dedup();
        ids.len() < r.owners.len()
    }));
    let v: Vec<_> = g.cells().iter().map(|c| c.volume).collect();
    let b: Vec<_> = (0..27).map(|i| field((i + 9) % 27)).collect();
    for op in [c, d] {
        let diag = op.gram_diagonal(&v).unwrap();
        let trans = op.transpose(&b).unwrap();
        let constant = op.apply(&[[3., -2., 5.]; 27]).unwrap();
        assert!(constant.iter().all(|x| *x == ZERO));
        for j in 0..27 {
            for k in 0..3 {
                let mut unit = [[0.; 3]; 27];
                unit[j][k] = 1.;
                let column = op.apply(&unit).unwrap();
                let gram: f64 = column
                    .iter()
                    .zip(&v)
                    .map(|(r, v)| v * r.iter().map(|x| x * x).sum::<f64>())
                    .sum();
                let adjoint: f64 = column
                    .iter()
                    .flatten()
                    .zip(b.iter().flatten())
                    .map(|(x, y)| x * y)
                    .sum();
                close(diag[j][k], gram);
                close(trans[j][k], adjoint);
            }
        }
        assert!(op.gram_diagonal(&[-1.; 27]).is_err());
    }
}

#[test]
fn rigid_and_stale_motion() {
    let g = geometry(0., Boundary3::Periodic);
    let uniform = (0..27).map(|i| (id(i), [1., -0.5, 0.25])).collect();
    let motion = prescribed_motion_rates3(&g, &uniform, ZERO).unwrap();
    let plan = MovingPointCurl3::assemble(&g, &motion).unwrap();
    let a: Vec<_> = (0..27).map(field).collect();
    let (_, d) = plan.operators(&g, &motion).unwrap();
    for v in d.apply(&a).unwrap().iter().flatten() {
        close(*v, 0.);
    }
    let another = prescribed_motion_rates3(&g, &velocities(), ZERO).unwrap();
    assert!(matches!(
        plan.operators(&g, &another),
        Err(FitError3::MotionMismatch)
    ));
    let wall = prescribed_motion_rates3(&g, &uniform, [1., 0., 0.]).unwrap();
    assert!(matches!(
        plan.operators(&g, &wall),
        Err(FitError3::MotionMismatch)
    ));
    let other = geometry(0., Boundary3::Periodic);
    assert!(matches!(
        MovingPointCurl3::assemble(&other, &motion),
        Err(FitError3::MotionMismatch)
    ));
    let bounded = geometry(0., Boundary3::Bounded);
    let rates = prescribed_motion_rates3(&bounded, &uniform, ZERO).unwrap();
    assert!(matches!(
        MovingPointCurl3::assemble(&bounded, &rates),
        Err(FitError3::UnsupportedBoundary)
    ));
}
