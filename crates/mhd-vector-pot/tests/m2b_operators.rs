use mhd_vector_pot::auxiliary3::{
    AuxiliaryError3, CornerJet3, SmoothVelocity3, VelocitySample3, interpolate_cell,
};
use mhd_vector_pot::operators3::DiscreteCurl3;
use moving_mesh::three_d::{
    Boundary3, Domain3, Generator3, HalfSpaceOracle3, Image3, Vec3,
    fit::{FitOrder3, SampleKey3},
    operator_mesh::{MeshFit3, OperatorMesh3},
};
use std::collections::BTreeSet;

fn id(i: usize) -> moving_mesh::three_d::operator_mesh::CellId {
    SampleKey3::from_words(0x4f3033, i as u64, Image3::ZERO).owner
}
fn basis(exponents: [i32; 3], point: Vec3, mask: usize) -> f64 {
    exponents
        .into_iter()
        .enumerate()
        .map(|(a, n)| {
            if mask & (1 << a) == 0 {
                point[a].powi(n)
            } else if n == 0 {
                0.
            } else {
                f64::from(n) * point[a].powi(n - 1)
            }
        })
        .product()
}
fn polynomial(e: [i32; 3]) {
    let origin = [-0.75, 0.25, -0.5];
    let h = [0.5, 1.5, 2.0];
    let factors = [1.0, -2.0, 0.75];
    let corners = std::array::from_fn(|m| {
        let p = std::array::from_fn(|a| origin[a] + if m & (1 << a) == 0 { 0. } else { h[a] });
        CornerJet3 {
            derivatives: std::array::from_fn(|k| factors.map(|v| v * basis(e, p, k))),
        }
    });
    let mut worst = 0.0_f64;
    for f in [
        [0., 0., 0.],
        [1., 1., 1.],
        [0.125, 0.625, 0.75],
        [0.5, 0.25, 0.375],
        [0.25, 1., 0.125],
    ] {
        let p = std::array::from_fn(|a| origin[a] + h[a] * f[a]);
        let v = interpolate_cell(&corners, h, f).unwrap();
        for (k, &factor) in factors.iter().enumerate() {
            let val = factor * basis(e, p, 0);
            worst = worst.max((v.value[k] - val).abs() / val.abs().max(1.));
            for a in 0..3 {
                let du = factor * basis(e, p, 1 << a);
                worst = worst.max((v.jacobian[k][a] - du).abs() / du.abs().max(1.));
            }
        }
    }
    println!("metric polynomial_max_scaled {worst:.17e}");
    assert!(worst <= 1e-10);
}
macro_rules! poly {
    ($name:ident,$x:literal,$y:literal,$z:literal) => {
        #[test]
        fn $name() {
            polynomial([$x, $y, $z]);
        }
    };
}
poly!(tricubic_000, 0, 0, 0);
poly!(tricubic_001, 0, 0, 1);
poly!(tricubic_002, 0, 0, 2);
poly!(tricubic_003, 0, 0, 3);
poly!(tricubic_010, 0, 1, 0);
poly!(tricubic_011, 0, 1, 1);
poly!(tricubic_012, 0, 1, 2);
poly!(tricubic_013, 0, 1, 3);
poly!(tricubic_020, 0, 2, 0);
poly!(tricubic_021, 0, 2, 1);
poly!(tricubic_022, 0, 2, 2);
poly!(tricubic_023, 0, 2, 3);
poly!(tricubic_030, 0, 3, 0);
poly!(tricubic_031, 0, 3, 1);
poly!(tricubic_032, 0, 3, 2);
poly!(tricubic_033, 0, 3, 3);
poly!(tricubic_100, 1, 0, 0);
poly!(tricubic_101, 1, 0, 1);
poly!(tricubic_102, 1, 0, 2);
poly!(tricubic_103, 1, 0, 3);
poly!(tricubic_110, 1, 1, 0);
poly!(tricubic_111, 1, 1, 1);
poly!(tricubic_112, 1, 1, 2);
poly!(tricubic_113, 1, 1, 3);
poly!(tricubic_120, 1, 2, 0);
poly!(tricubic_121, 1, 2, 1);
poly!(tricubic_122, 1, 2, 2);
poly!(tricubic_123, 1, 2, 3);
poly!(tricubic_130, 1, 3, 0);
poly!(tricubic_131, 1, 3, 1);
poly!(tricubic_132, 1, 3, 2);
poly!(tricubic_133, 1, 3, 3);
poly!(tricubic_200, 2, 0, 0);
poly!(tricubic_201, 2, 0, 1);
poly!(tricubic_202, 2, 0, 2);
poly!(tricubic_203, 2, 0, 3);
poly!(tricubic_210, 2, 1, 0);
poly!(tricubic_211, 2, 1, 1);
poly!(tricubic_212, 2, 1, 2);
poly!(tricubic_213, 2, 1, 3);
poly!(tricubic_220, 2, 2, 0);
poly!(tricubic_221, 2, 2, 1);
poly!(tricubic_222, 2, 2, 2);
poly!(tricubic_223, 2, 2, 3);
poly!(tricubic_230, 2, 3, 0);
poly!(tricubic_231, 2, 3, 1);
poly!(tricubic_232, 2, 3, 2);
poly!(tricubic_233, 2, 3, 3);
poly!(tricubic_300, 3, 0, 0);
poly!(tricubic_301, 3, 0, 1);
poly!(tricubic_302, 3, 0, 2);
poly!(tricubic_303, 3, 0, 3);
poly!(tricubic_310, 3, 1, 0);
poly!(tricubic_311, 3, 1, 1);
poly!(tricubic_312, 3, 1, 2);
poly!(tricubic_313, 3, 1, 3);
poly!(tricubic_320, 3, 2, 0);
poly!(tricubic_321, 3, 2, 1);
poly!(tricubic_322, 3, 2, 2);
poly!(tricubic_323, 3, 2, 3);
poly!(tricubic_330, 3, 3, 0);
poly!(tricubic_331, 3, 3, 1);
poly!(tricubic_332, 3, 3, 2);
poly!(tricubic_333, 3, 3, 3);

fn face_continuity(axis: usize) {
    let n = 4;
    let h = [0.75, 0.25, 1.25];
    let jets: Vec<_> = (0..64)
        .map(|i| CornerJet3 {
            derivatives: std::array::from_fn(|m| {
                std::array::from_fn(|k| (((17 * i + 7 * m + 3 * k + 1) % 31) as f64 - 15.) / 8.)
            }),
        })
        .collect();
    let cube = |at: [usize; 3]| {
        std::array::from_fn(|m| {
            let c: [_; 3] = std::array::from_fn(|a| (at[a] + ((m >> a) & 1)) % n);
            jets[c[0] + 4 * (c[1] + 4 * c[2])]
        })
    };
    let mut worst = 0.0_f64;
    for x in 0..n {
        for y in 0..n {
            for z in 0..n {
                let at = [x, y, z];
                let mut next = at;
                next[axis] = (next[axis] + 1) % n;
                for (u, v) in [(0., 0.), (1., 1.), (0.125, 0.75), (0.375, 0.625)] {
                    let mut a = [0.; 3];
                    a[axis] = 1.;
                    a[(axis + 1) % 3] = u;
                    a[(axis + 2) % 3] = v;
                    let mut b = a;
                    b[axis] = 0.;
                    let l = interpolate_cell(&cube(at), h, a).unwrap();
                    let r = interpolate_cell(&cube(next), h, b).unwrap();
                    for (i, j) in l
                        .value
                        .into_iter()
                        .chain(l.jacobian.into_iter().flatten())
                        .zip(r.value.into_iter().chain(r.jacobian.into_iter().flatten()))
                    {
                        worst = worst.max((i - j).abs());
                    }
                }
            }
        }
    }
    println!("metric shared_face_max_absolute {worst:.17e}");
    assert!(worst <= 1e-12);
}
#[test]
fn tricubic_all_faces_and_seams_x() {
    face_continuity(0);
}
#[test]
fn tricubic_all_faces_and_seams_y() {
    face_continuity(1);
}
#[test]
fn tricubic_all_faces_and_seams_z() {
    face_continuity(2);
}
fn actual_fits(order: FitOrder3) -> Vec<MeshFit3> {
    let input: Vec<_> = (0..64)
        .map(|i| Generator3 {
            id: id(i),
            position: [i / 16, i / 4 % 4, i % 4].map(|a| (a as f64 + 0.5) / 4.),
            winding: Image3([(i % 3) as i64 - 1, 0, (i % 2) as i64]),
        })
        .collect();
    let geometry = HalfSpaceOracle3::build(
        Domain3 {
            anchor: [0.; 3],
            width: [1.; 3],
            boundary: Boundary3::Periodic,
        },
        &input,
    )
    .unwrap();
    let mesh = OperatorMesh3::from_validated(&geometry).unwrap();
    (0..64).map(|i| mesh.fit(i, order).unwrap()).collect()
}
fn adjoint(order: FitOrder3) {
    let fits = actual_fits(order);
    if order == FitOrder3::Quadratic {
        assert!(fits[0].owners.iter().collect::<BTreeSet<_>>().len() < fits[0].owners.len());
    }
    let c = DiscreteCurl3::assemble(&fits).unwrap();
    let mut seed = 20261122u64;
    let mut field = || {
        (0..64)
            .map(|_| {
                std::array::from_fn(|_| {
                    seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
                    ((seed >> 32) % 33) as f64 - 16.
                })
            })
            .collect::<Vec<_>>()
    };
    let a = field();
    let b = field();
    let ca = c.apply(&a).unwrap();
    let ct = c.transpose(&b).unwrap();
    let dot = |x: &[Vec3], y: &[Vec3]| {
        x.iter()
            .flatten()
            .zip(y.iter().flatten())
            .map(|(s, t)| s * t)
            .sum::<f64>()
    };
    let l = dot(&ca, &b);
    let r = dot(&a, &ct);
    let scale = l.abs().max(r.abs());
    assert!(scale > 1.0);
    let error = (l - r).abs() / scale;
    println!("metric adjoint_relative {error:.17e}");
    assert!(error <= 1e-12);
}
fn gauge(order: FitOrder3) {
    let fits = actual_fits(order);
    let c = DiscreteCurl3::assemble(&fits).unwrap();
    let v = c.apply(&[[1e14, -13.75, 0.03125]; 64]).unwrap();
    let e = v.into_iter().flatten().map(f64::abs).fold(0., f64::max);
    println!("metric constant_curl_max {e:.17e}");
    assert_eq!(e, 0.);
}
#[test]
fn linear_curl_transpose() {
    adjoint(FitOrder3::Linear);
}
#[test]
fn quadratic_curl_transpose() {
    adjoint(FitOrder3::Quadratic);
}
#[test]
fn linear_gauge_constant() {
    gauge(FitOrder3::Linear);
}
#[test]
fn quadratic_gauge_constant() {
    gauge(FitOrder3::Quadratic);
}
fn sample(i: usize, x: Vec3, v: Vec3, volume: f64) -> VelocitySample3 {
    VelocitySample3 {
        id: id(i),
        position: x,
        velocity: v,
        volume,
    }
}
#[test]
fn deposition_aliases_and_empty_root() {
    let input = [sample(0, [0.; 3], [1., 2., 3.], 1.)];
    let aux = SmoothVelocity3::deposit([1.; 3], [0.; 3], &input, 4).unwrap();
    assert_eq!(aux.intervals(), 2);
    assert_eq!(aux.attempts.len(), 2);
    assert!(aux.attempts[0].counts.contains(&0));
    assert_eq!(aux.attempts[1].counts, vec![1; 8]);
    let e = (aux.attempts[1].normalizers.iter().sum::<f64>() - 1.).abs();
    assert!(e < 1e-15);
    let v = aux.sample([0.125, 0.625, -1.75]).unwrap();
    assert!(
        v.value
            .into_iter()
            .zip([1., 2., 3.])
            .all(|(a, b)| (a - b).abs() < 1e-12)
    );
    assert_eq!(
        SmoothVelocity3::deposit([1.; 3], [0.; 3], &[], 4).unwrap_err(),
        AuxiliaryError3::AuxiliaryTransitionUnresolved
    );
    println!("metric alias_mass_error {e:.17e}");
}
#[test]
fn one_root_volume_weighted_mean() {
    let v = [
        sample(0, [0.125, 0.25, 0.75], [1., 4., -3.], 1.),
        sample(1, [0.625, 0.125, 0.875], [5., 0., 1.], 3.),
    ];
    let aux = SmoothVelocity3::deposit([1.; 3], [0.; 3], &v, 1).unwrap();
    let s = aux.sample([0.371, -2.125, 1.75]).unwrap();
    assert_eq!(aux.attempts[0].counts, [2]);
    let e = s
        .value
        .into_iter()
        .zip([4., 1., 0.])
        .map(|(a, b)| (a - b).abs())
        .chain(s.jacobian.into_iter().flatten().map(f64::abs))
        .fold(0., f64::max);
    println!("metric volume_mean_max {e:.17e}");
    assert!(e < 1e-12);
}
#[test]
fn deposition_order_and_translated_origin() {
    let mut samples: Vec<_> = (0..64)
        .map(|i| {
            let a = [i / 16, i / 4 % 4, i % 4].map(|v| (v as f64 + 0.375) / 4.);
            sample(i, a, [a[0] - a[2], a[1] * 2., -a[0]], 1. + (i % 5) as f64)
        })
        .collect();
    let a = SmoothVelocity3::deposit([1.; 3], [0.; 3], &samples, 4).unwrap();
    samples.reverse();
    let shift = [1.25, -2.5, 0.375];
    for s in &mut samples {
        for (x, dx) in s.position.iter_mut().zip(shift) {
            *x += dx;
        }
    }
    let b = SmoothVelocity3::deposit([1.; 3], shift, &samples, 4).unwrap();
    assert_eq!(a.intervals(), 4);
    assert_eq!(a.attempts[0].normalizers, b.attempts[0].normalizers);
    let x = [0.125, 0.375, 0.625];
    let l = a.sample(x).unwrap();
    let r = b.sample(std::array::from_fn(|k| x[k] + shift[k])).unwrap();
    assert_eq!(l.value, r.value);
    assert_eq!(l.jacobian, r.jacobian);
    println!("metric translated_jet_difference 0");
}
