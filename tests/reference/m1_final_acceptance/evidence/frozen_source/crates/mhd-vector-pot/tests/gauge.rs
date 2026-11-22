use mhd_vector_pot::gauge::{Cleaning, PointSources, Vec3};
use std::f64::consts::TAU;

fn zero_sources() -> PointSources {
    PointSources {
        potential: [0.0; 3],
        fluid_velocity: [0.0; 3],
        auxiliary_velocity: [0.0; 3],
        centroid_velocity: [0.0; 3],
        magnetic: [0.0; 3],
        mean_magnetic: [0.0; 3],
        gradient_a: [[0.0; 3]; 3],
        gradient_auxiliary: [[0.0; 3]; 3],
        gradient_phi: [0.0; 3],
        current: [0.0; 3],
        resistivity: 0.0,
    }
}
fn cross(a: Vec3, b: Vec3) -> Vec3 {
    [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
}
fn close(a: f64, b: f64) {
    assert!(
        (a - b).abs() < 1e-12 * (1.0 + a.abs() + b.abs()),
        "{a} != {b}"
    );
}

fn jet() -> PointSources {
    let mut s = zero_sources();
    s.potential = [0.7, -0.2, 0.4];
    s.fluid_velocity = [1.1, 0.3, -0.8];
    s.auxiliary_velocity = [0.4, -0.5, 0.2];
    s.centroid_velocity = [-0.2, 0.1, 0.6];
    s.gradient_a = [[0.1, 0.3, -0.2], [-0.4, 0.7, 0.6], [0.8, -0.9, -0.5]];
    s.gradient_auxiliary = [[0.2, -0.3, 0.7], [0.8, -0.1, -0.4], [-0.6, 0.9, 0.5]];
    s.mean_magnetic = [0.9, -0.4, 0.3];
    let g = s.gradient_a;
    let curl = [g[2][1] - g[1][2], g[0][2] - g[2][0], g[1][0] - g[0][1]];
    s.magnetic = std::array::from_fn(|k| s.mean_magnetic[k] + curl[k]);
    s.gradient_phi = [-0.3, 0.7, 0.2];
    s.current = [0.5, -0.2, 0.9];
    s.resistivity = 0.03;
    s
}

#[test]
fn full_point_rate_matches_eulerian_product_rule_identity() {
    let s = jet();
    let rate = s.rate().unwrap().total();
    let induction = cross(s.fluid_velocity, s.magnetic);
    for k in 0..3 {
        // grad(u dot A) = sum_a [(partial_k u_a) A_a + u_a (partial_k A_a)].
        let gauge_gradient: f64 = (0..3)
            .map(|a| {
                s.gradient_auxiliary[a][k] * s.potential[a]
                    + s.auxiliary_velocity[a] * s.gradient_a[a][k]
            })
            .sum();
        let centroid_derivative: f64 = (0..3)
            .map(|b| s.centroid_velocity[b] * s.gradient_a[k][b])
            .sum();
        close(
            rate[k],
            induction[k] - gauge_gradient + centroid_derivative - s.resistivity * s.current[k]
                + s.gradient_phi[k],
        );
    }
}

#[test]
fn joint_boost_only_adds_mean_field_gauge_drift() {
    let s = jet();
    let mut boosted = s;
    let boost = [2.0, -1.0, 0.4];
    for (k, b) in boost.iter().enumerate() {
        boosted.fluid_velocity[k] += b;
        boosted.auxiliary_velocity[k] += b;
        boosted.centroid_velocity[k] += b;
    }
    let a = s.rate().unwrap().total();
    let b = boosted.rate().unwrap().total();
    let expected = cross(boost, s.mean_magnetic);
    for k in 0..3 {
        close(b[k] - a[k], expected[k]);
    }
}

#[test]
fn constant_background_has_positive_potential_drift() {
    let mut s = zero_sources();
    s.fluid_velocity = [1.0, 2.0, 3.0];
    s.auxiliary_velocity = s.fluid_velocity;
    s.centroid_velocity = s.fluid_velocity;
    s.magnetic = [0.4, -0.2, 0.7];
    s.mean_magnetic = s.magnetic;
    let expected = cross(s.fluid_velocity, s.magnetic);
    let actual = s.rate().unwrap().total();
    for k in 0..3 {
        close(actual[k], expected[k]);
    }
}

#[test]
fn distortion_shear_is_exact_and_rotation_converges_in_time() {
    let initial = [0.7, -0.2, 0.4];
    let time = 1.3;
    let integrate = |rotation: bool, n: usize| {
        let dt = time / n as f64;
        let mut a = initial;
        for _ in 0..n {
            let mut s = zero_sources();
            s.potential = a;
            s.gradient_auxiliary = if rotation {
                [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0; 3]]
            } else {
                [[0.0, 2.0, 0.0], [0.0; 3], [0.0; 3]]
            };
            let r0 = s.rate().unwrap().total();
            s.potential = std::array::from_fn(|k| a[k] + dt * r0[k]);
            let r1 = s.rate().unwrap().total();
            a = std::array::from_fn(|k| a[k] + 0.5 * dt * (r0[k] + r1[k]));
        }
        a
    };
    let shear = integrate(false, 20);
    close(shear[0], initial[0]);
    close(shear[1], initial[1] - 2.0 * time * initial[0]);
    close(shear[2], initial[2]);
    let exact = [
        time.cos() * initial[0] - time.sin() * initial[1],
        time.sin() * initial[0] + time.cos() * initial[1],
        initial[2],
    ];
    let errors: Vec<_> = [20, 40, 80]
        .iter()
        .map(|n| {
            integrate(true, *n)
                .iter()
                .zip(exact)
                .map(|(a, b)| (a - b).powi(2))
                .sum::<f64>()
                .sqrt()
        })
        .collect();
    for pair in errors.windows(2) {
        assert!((pair[0] / pair[1]).log2() > 1.8, "{errors:?}");
    }
}

#[test]
fn cleaning_stages_freeze_old_source_and_use_new_radius() {
    let c = Cleaning::default();
    let dt = 0.02;
    let stage = c.begin(0.7, 0.3, 2.0, 0.4).unwrap();
    close(stage.initial_rate(), 0.675);
    close(stage.predicted_phi(dt).unwrap(), 0.7135);
    close(stage.endpoint_rate(dt, 0.6).unwrap(), 0.84325);
    close(stage.finish_phi(dt, 0.6).unwrap(), 0.7151825);
    // Positive divergence drives positive phi; positive phi damps at div(A)=0.
    assert!(c.rate(0.0, 0.2, 1.0, 0.1).unwrap() > 0.0);
    assert!(c.rate(0.2, 0.0, 1.0, 0.1).unwrap() < 0.0);
}

#[test]
fn printed_cleaning_bounds_have_expected_scaling() {
    let c = Cleaning::default();
    let bounds = c.bounds(2.0, 0.4).unwrap();
    close(bounds.hyperbolic, 0.2);
    close(bounds.diffusive, 0.03);
    let twice_radius = c.bounds(2.0, 0.8).unwrap();
    close(twice_radius.hyperbolic, 2.0 * bounds.hyperbolic);
    close(twice_radius.diffusive, 2.0 * bounds.diffusive);
    let twice_speed = c.bounds(4.0, 0.4).unwrap();
    close(twice_speed.hyperbolic, 0.5 * bounds.hyperbolic);
    close(twice_speed.diffusive, 0.5 * bounds.diffusive);
    let alpha = Cleaning::new(2.0, 0.15).unwrap().bounds(2.0, 0.4).unwrap();
    close(alpha.hyperbolic, 0.5 * bounds.hyperbolic);
    close(alpha.diffusive, 0.5 * bounds.diffusive);
}

#[test]
fn coupled_cleaning_mode_exposes_frozen_source_temporal_order() {
    let cleaning = Cleaning::default();
    let cs = 1.0;
    let radius = 0.1;
    let time = 0.5;
    let initial = [0.01, 0.02];
    let k = TAU;
    let kappa = cleaning.beta() * cs / radius;
    let omega = (cleaning.alpha() * cs * cs * k * k - 0.25 * kappa * kappa).sqrt();
    let (sin, cos) = (omega * time).sin_cos();
    let damping = (-0.5 * kappa * time).exp();
    let exact = [
        damping * ((cos + 0.5 * kappa * sin / omega) * initial[0] + k * sin / omega * initial[1]),
        damping
            * (-cleaning.alpha() * cs * cs * k * sin / omega * initial[0]
                + (cos - 0.5 * kappa * sin / omega) * initial[1]),
    ];
    for frozen in [true, false] {
        let mut errors = Vec::new();
        for n in [40, 80, 160, 320] {
            let dt = time / n as f64;
            let mut a = initial[0];
            let mut p = initial[1];
            for _ in 0..n {
                let stage = cleaning.begin(p, -k * a, cs, radius).unwrap();
                let ps = stage.predicted_phi(dt).unwrap();
                let astar = a + dt * k * p;
                let next_p = if frozen {
                    stage.finish_phi(dt, radius).unwrap()
                } else {
                    p + 0.5
                        * dt
                        * (stage.initial_rate()
                            + cleaning.rate(ps, -k * astar, cs, radius).unwrap())
                };
                a += 0.5 * dt * k * (p + ps);
                p = next_p;
            }
            errors.push((a - exact[0]).hypot(p - exact[1]));
        }
        for pair in errors.windows(2) {
            assert!(pair[1] < pair[0], "{errors:?}");
        }
        let order = (errors[2] / errors[3]).log2();
        if frozen {
            assert!((0.8..1.2).contains(&order), "{errors:?}: {order}");
        } else {
            assert!(order > 1.8, "{errors:?}: {order}");
        }
    }
}

#[test]
fn invalid_and_overflowing_source_inputs_are_rejected() {
    let c = Cleaning::default();
    for value in [0.0, -1.0, f64::NAN, f64::INFINITY] {
        assert!(Cleaning::new(value, 0.15).is_err());
        assert!(Cleaning::new(1.0, value).is_err());
        assert!(c.bounds(1.0, value).is_err());
        assert!(c.bounds(value, 0.1).is_err());
        assert!(c.begin(0.0, 0.1, 1.0, value).is_err());
    }
    assert!(c.begin(f64::NAN, 0.0, 1.0, 0.1).is_err());
    assert!(c.begin(0.0, f64::INFINITY, 1.0, 0.1).is_err());
    let stage = c.begin(0.0, 0.1, 1.0, 0.1).unwrap();
    assert!(stage.predicted_phi(-0.1).is_err());
    assert!(stage.finish_phi(f64::NAN, 0.1).is_err());
    assert!(stage.finish_phi(0.1, 0.0).is_err());
    let mut s = zero_sources();
    s.gradient_auxiliary[0][1] = f64::NAN;
    assert!(s.rate().is_err());
    s = zero_sources();
    s.resistivity = -1.0;
    assert!(s.rate().is_err());
    s = zero_sources();
    s.current = [f64::MAX; 3];
    s.resistivity = 2.0;
    assert!(s.rate().is_err());
}
