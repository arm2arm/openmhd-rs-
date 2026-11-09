use mhd_vector_pot::auxiliary::{Jet, Projection, SmoothVelocity, VelocitySample, interpolate};

fn close(a: f64, b: f64) {
    assert!(
        (a - b).abs() <= 1e-11 * (1.0 + a.abs() + b.abs()),
        "{a} != {b}"
    );
}

fn polynomial(x: f64, y: f64, dx: usize, dy: usize, k: usize) -> f64 {
    let mut value = 0.0;
    for a in dx..4 {
        for b in dy..4 {
            let coefficient = ((1 + a + 3 * b + 2 * k) as f64).sin();
            let factor_x = if dx == 0 { 1.0 } else { a as f64 };
            let factor_y = if dy == 0 { 1.0 } else { b as f64 };
            value += coefficient
                * factor_x
                * factor_y
                * x.powi((a - dx) as i32)
                * y.powi((b - dy) as i32);
        }
    }
    value
}

#[test]
fn tensor_cubic_values_and_physical_derivatives_are_exact() {
    let h = [0.3, 0.7];
    let origin = [-0.2, 0.4];
    let corners = std::array::from_fn(|j| {
        std::array::from_fn(|i| {
            let x = origin[0] + i as f64 * h[0];
            let y = origin[1] + j as f64 * h[1];
            Jet {
                value: std::array::from_fn(|k| polynomial(x, y, 0, 0, k)),
                dx: std::array::from_fn(|k| polynomial(x, y, 1, 0, k)),
                dy: std::array::from_fn(|k| polynomial(x, y, 0, 1, k)),
                dxy: std::array::from_fn(|k| polynomial(x, y, 1, 1, k)),
            }
        })
    });
    for p in [[0.0, 0.0], [1.0, 1.0], [0.31, 0.73], [0.91, 0.12]] {
        let s = interpolate(&corners, h, p).unwrap();
        let x = origin[0] + p[0] * h[0];
        let y = origin[1] + p[1] * h[1];
        for k in 0..3 {
            close(s.velocity[k], polynomial(x, y, 0, 0, k));
            close(s.jacobian[k][0], polynomial(x, y, 1, 0, k));
            close(s.jacobian[k][1], polynomial(x, y, 0, 1, k));
            assert_eq!(s.jacobian[k][2], 0.0);
        }
    }
}

fn samples(offset: f64) -> Vec<VelocitySample> {
    (0..16)
        .map(|i| VelocitySample {
            position: [(i % 4) as f64 / 4.0 + offset, (i / 4) as f64 / 4.0 + offset],
            volume: 1.0 + i as f64 / 16.0,
            velocity: [(i as f64).sin(), (0.7 * i as f64).cos(), 0.1 * i as f64],
        })
        .collect()
}

#[test]
fn periodic_interpolant_is_c1_and_preserves_constants() {
    let input = samples(0.0);
    let field = SmoothVelocity::build([1.0; 2], &input, [0.0; 2]).unwrap();
    assert_eq!(field.intervals(), 4);
    for boundary in [0.0, 0.25, 0.5, 0.75, 1.0] {
        for axis in 0..2 {
            let mut l = [0.37; 2];
            let mut r = l;
            l[axis] = boundary - 1e-14;
            r[axis] = boundary + 1e-14;
            let a = field.sample(l, 0.0).unwrap();
            let b = field.sample(r, 0.0).unwrap();
            for k in 0..3 {
                assert!((a.velocity[k] - b.velocity[k]).abs() < 1e-10);
                for j in 0..2 {
                    assert!((a.jacobian[k][j] - b.jacobian[k][j]).abs() < 1e-10);
                }
            }
        }
    }
    let input: Vec<_> = input
        .into_iter()
        .map(|mut s| {
            s.velocity = [0.4, -0.2, 0.7];
            s
        })
        .collect();
    let field = SmoothVelocity::build([1.0; 2], &input, [0.0; 2]).unwrap();
    for p in [[0.0, 0.0], [0.13, 0.79], [2.91, -1.18]] {
        let s = field.sample(p, 0.17).unwrap();
        for (k, v) in [0.4, -0.2, 0.7].iter().enumerate() {
            close(s.velocity[k], *v);
            for d in s.jacobian[k] {
                close(d, 0.0);
            }
        }
    }
}

#[test]
fn empty_bins_coarsen_globally_with_volume_weighted_mean() {
    let four: Vec<_> = (0..4)
        .map(|i| VelocitySample {
            position: [0.2 + 0.5 * (i % 2) as f64, 0.2 + 0.5 * (i / 2) as f64],
            volume: 1.0,
            velocity: [i as f64; 3],
        })
        .collect();
    let f = SmoothVelocity::build([1.0; 2], &four, [0.0; 2]).unwrap();
    assert_eq!(f.intervals(), 2);
    assert_eq!(f.coarsenings, 1);
    assert_eq!(f.counts, vec![1; 4]);
    let two = [
        VelocitySample {
            position: [0.2; 2],
            volume: 1.0,
            velocity: [1.0, 2.0, 3.0],
        },
        VelocitySample {
            position: [0.7; 2],
            volume: 3.0,
            velocity: [5.0, 6.0, 7.0],
        },
    ];
    let f = SmoothVelocity::build([1.0; 2], &two, [0.0; 2]).unwrap();
    assert_eq!(f.intervals(), 1);
    assert_eq!(f.coarsenings, 2);
    assert_eq!(f.counts, vec![2]);
    assert_eq!(f.max_cell_volumes, vec![3.0]);
    let s = f.sample([0.37, 0.81], 0.1).unwrap();
    for (k, v) in [4.0, 5.0, 6.0].iter().enumerate() {
        close(s.velocity[k], *v);
        for d in s.jacobian[k] {
            close(d, 0.0);
        }
    }
}

#[test]
fn moving_origin_preserves_half_open_ties_and_boosted_rebuilds() {
    let input = samples(0.125); // Exact corner-box boundaries.
    let shift = [0.37, -0.21];
    let boost = [2.0, -1.0, 0.7];
    let translated: Vec<_> = input
        .iter()
        .map(|s| VelocitySample {
            position: std::array::from_fn(|k| s.position[k] + shift[k]),
            volume: s.volume,
            velocity: std::array::from_fn(|k| s.velocity[k] + boost[k]),
        })
        .collect();
    let base = SmoothVelocity::build([1.0; 2], &input, [0.0; 2]).unwrap();
    let other = SmoothVelocity::build([1.0; 2], &translated, shift).unwrap();
    assert_eq!(base.counts, other.counts);
    assert_eq!(base.intervals(), other.intervals());
    for time in [0.0, 0.03, 0.17] {
        let a = base.sample([0.19, 0.71], time).unwrap();
        let b = other
            .sample(
                [
                    0.19 + shift[0] + time * boost[0],
                    0.71 + shift[1] + time * boost[1],
                ],
                time,
            )
            .unwrap();
        for (k, shift) in boost.iter().enumerate() {
            close(b.velocity[k], a.velocity[k] + shift);
            for j in 0..3 {
                close(a.jacobian[k][j], b.jacobian[k][j]);
            }
        }
    }
    // A second synchronization keeps memberships covariant only with moved origin.
    let dt = 0.07;
    let moved = base.advanced_origin(dt).unwrap();
    let moved_boost = other.advanced_origin(dt).unwrap();
    let base_samples: Vec<_> = input
        .iter()
        .map(|s| VelocitySample {
            position: std::array::from_fn(|k| s.position[k] + dt * base.mean_velocity[k]),
            ..*s
        })
        .collect();
    let boost_samples: Vec<_> = translated
        .iter()
        .map(|s| VelocitySample {
            position: std::array::from_fn(|k| s.position[k] + dt * other.mean_velocity[k]),
            ..*s
        })
        .collect();
    let a = SmoothVelocity::build([1.0; 2], &base_samples, moved).unwrap();
    let b = SmoothVelocity::build([1.0; 2], &boost_samples, moved_boost).unwrap();
    assert_eq!(a.counts, b.counts);
    for (k, shift) in boost.iter().enumerate() {
        close(b.mean_velocity[k], a.mean_velocity[k] + shift);
    }
}

#[test]
fn invalid_auxiliary_inputs_fail() {
    assert!(SmoothVelocity::build([1.0; 2], &[], [0.0; 2]).is_err());
    let mut s = samples(0.0);
    s[0].volume = 0.0;
    assert!(SmoothVelocity::build([1.0; 2], &s, [0.0; 2]).is_err());
    s = samples(0.0);
    s[0].velocity[2] = f64::NAN;
    assert!(SmoothVelocity::build([1.0; 2], &s, [0.0; 2]).is_err());
    let f = SmoothVelocity::build([1.0; 2], &samples(0.0), [0.0; 2]).unwrap();
    assert!(f.sample([f64::INFINITY, 0.0], 0.0).is_err());
    assert!(f.advanced_origin(-0.1).is_err());
}

#[test]
fn continuous_projection_removes_the_old_membership_jump() {
    let mut input = samples(0.);
    input.push(VelocitySample {
        position: [0.125, 0.],
        volume: 0.7,
        velocity: [4., -1., 2.],
    });
    for projection in [Projection::NearestBin, Projection::CubicSpline] {
        let eps = 1e-8;
        let a =
            SmoothVelocity::build_with_projection([1.; 2], &input, [-eps, 0.], projection).unwrap();
        let b =
            SmoothVelocity::build_with_projection([1.; 2], &input, [eps, 0.], projection).unwrap();
        assert_eq!(a.intervals(), 4);
        assert_eq!(b.intervals(), 4);
        let a = a.sample([0.17, 0.21], 0.).unwrap();
        let b = b.sample([0.17, 0.21], 0.).unwrap();
        let difference = a
            .velocity
            .iter()
            .zip(b.velocity)
            .map(|(a, b)| (a - b).abs())
            .chain(
                a.jacobian
                    .iter()
                    .flatten()
                    .zip(b.jacobian.iter().flatten())
                    .map(|(a, b)| (a - b).abs()),
            )
            .fold(0., f64::max);
        if projection == Projection::NearestBin {
            assert!(difference > 1e-3, "old jump {difference}");
        } else {
            assert!(difference < 100. * eps, "continuous change {difference}");
        }
    }
}

#[test]
fn spline_projection_preserves_constants_and_boost_covariance() {
    let input = samples(0.125);
    let shift = [0.37, -0.21];
    let boost = [2., -1., 0.7];
    let translated: Vec<_> = input
        .iter()
        .map(|s| VelocitySample {
            position: std::array::from_fn(|k| s.position[k] + shift[k]),
            velocity: std::array::from_fn(|k| s.velocity[k] + boost[k]),
            ..*s
        })
        .collect();
    let build = |samples: &[VelocitySample], origin| {
        SmoothVelocity::build_with_projection([1.; 2], samples, origin, Projection::CubicSpline)
            .unwrap()
    };
    let a = build(&input, [0.; 2]);
    let b = build(&translated, shift);
    for t in [0., 0.07] {
        let pa = a.sample([0.19, 0.71], t).unwrap();
        let pb = b
            .sample(
                [
                    0.19 + shift[0] + t * boost[0],
                    0.71 + shift[1] + t * boost[1],
                ],
                t,
            )
            .unwrap();
        for (k, boost) in boost.iter().enumerate() {
            close(pb.velocity[k], pa.velocity[k] + boost);
            for j in 0..3 {
                close(pa.jacobian[k][j], pb.jacobian[k][j]);
            }
        }
    }
    let constant = [VelocitySample {
        position: [0.; 2],
        volume: 1.,
        velocity: [0.4, -0.2, 0.7],
    }];
    let a = build(&constant, [0.; 2]);
    assert_eq!(a.intervals(), 2); // Empty fine support coarsens, periodic aliases sum.
    let p = a.sample([0.37, 0.81], 0.17).unwrap();
    for (k, value) in constant[0].velocity.iter().enumerate() {
        close(p.velocity[k], *value);
        for d in p.jacobian[k] {
            close(d, 0.);
        }
    }
    let mut invalid = constant;
    invalid[0].velocity[0] = f64::NAN;
    assert!(
        SmoothVelocity::build_with_projection([1.; 2], &invalid, [0.; 2], Projection::CubicSpline)
            .is_err()
    );
}
