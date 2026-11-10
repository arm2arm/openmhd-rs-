use mhd_vector_pot::general::{Config, Initial, Motion, Profile, Simulation};
use moving_mesh::Mesh;
use std::f64::consts::TAU;

fn config(profile: Profile, dt: f64) -> Config {
    Config {
        profile,
        mean_magnetic: [0.3, 0.2, 0.1],
        max_dt: dt,
        ..Config::default()
    }
}
fn smooth(x: [f64; 2], boost: [f64; 3]) -> Initial {
    let (x, y) = (TAU * x[0], TAU * x[1]);
    Initial {
        density: 1. + 0.01 * x.sin(),
        pressure: 1. + 0.01 * y.cos(),
        velocity: [
            0.2 + 0.05 * y.sin() + boost[0],
            -0.1 + 0.03 * x.cos() + boost[1],
            0.04 * (x + y).sin() + boost[2],
        ],
        potential: [
            0.001 * (x + y).sin(),
            0.001 * x.cos(),
            0.001 * x.sin() * y.sin(),
        ],
        phi: 0.0001 * (x - y).cos(),
    }
}
fn budgets(sim: &Simulation) {
    let d = sim.diagnostics().unwrap();
    assert!(d.min_density > 0. && d.min_pressure > 0.);
    assert!(d.normalized_budget.iter().all(|v| v.abs() < 1e-10));
    for div in [
        &d.divergence_ls,
        &d.divergence_face,
        &d.divergence_limited_face,
    ] {
        assert!(div.dimensional.rms.is_finite() && div.dimensionless.max.is_finite());
    }
    assert_eq!(
        sim.counters().endpoint_auxiliary_roots.len(),
        sim.counters().steps
    );
}

fn heun_rejects_deforming_motion(profile: Profile) {
    for motion in [Motion::Fluid, Motion::Prescribed(vec![[0.; 2]; 64])] {
        let result = Simulation::new(
            Mesh::lattice(8, 8, [1.; 2], 0.).unwrap(),
            Config {
                motion,
                ..config(profile, 0.001)
            },
            |x| smooth(x, [0.; 3]),
        );
        assert!(result.unwrap_err().contains("only fixed or rigid"));
    }
}

fn heun_uniform_state_fixed_and_rigid(profile: Profile) {
    for motion in [Motion::Fixed, Motion::Rigid([0.7, -0.4])] {
        let init = Initial {
            density: 1.,
            pressure: 0.5,
            velocity: [0.2, -0.1, 0.3],
            potential: [0.1, -0.2, 0.4],
            phi: 0.,
        };
        let mut sim = Simulation::new(
            Mesh::lattice(6, 6, [1.; 2], 0.15).unwrap(),
            Config {
                motion,
                ..config(profile, 0.001)
            },
            |_| init,
        )
        .unwrap();
        sim.advance_to(0.01).unwrap();
        for (i, q) in sim.primitives().unwrap().iter().enumerate() {
            assert!((q.density - init.density).abs() < 1e-12);
            assert!((q.pressure - init.pressure).abs() < 1e-12);
            for k in 0..3 {
                assert!((q.velocity[k] - init.velocity[k]).abs() < 1e-12);
                assert!((q.magnetic[k] - sim.config().mean_magnetic[k]).abs() < 1e-12);
                assert!((sim.state().potential[i][k] - init.potential[k]).abs() < 1e-12);
            }
        }
        budgets(&sim);
    }
}

fn heun_smooth_semidiscrete_time_order(profile: Profile) {
    let mut states = Vec::new();
    for dt in [0.001, 0.0005, 0.00025, 0.000125] {
        let mut sim = Simulation::new(
            Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap(),
            Config {
                limited: false,
                ..config(profile, dt)
            },
            |x| smooth(x, [0.; 3]),
        )
        .unwrap();
        sim.advance_to(0.02).unwrap();
        let c = sim.counters();
        assert_eq!(c.rejected_cfl + c.rejected_state + c.rejected_geometry, 0);
        assert_eq!(c.max_dt, dt);
        assert!(c.auxiliary_roots.iter().all(|r| *r == 4));
        assert!(c.endpoint_auxiliary_roots.iter().all(|r| *r == 4));
        budgets(&sim);
        states.push(vec![
            sim.state()
                .conserved
                .iter()
                .flatten()
                .copied()
                .collect::<Vec<_>>(),
            sim.state().potential.iter().flatten().copied().collect(),
            sim.state().phi.clone(),
            sim.magnetic_fit()
                .unwrap()
                .magnetic
                .iter()
                .flatten()
                .copied()
                .collect(),
        ]);
    }
    for (k, name) in ["Q", "A", "phi", "B"].iter().enumerate() {
        let differences: Vec<f64> = states
            .windows(2)
            .map(|s| {
                s[0][k]
                    .iter()
                    .zip(&s[1][k])
                    .map(|(a, b)| (a - b).powi(2))
                    .sum::<f64>()
                    .sqrt()
            })
            .collect();
        for pair in differences.windows(2) {
            let ratio = pair[0] / pair[1];
            println!("{name} self-difference ratio {ratio:.9}");
            assert!((3.4..4.6).contains(&ratio), "{name}: {differences:?}");
        }
    }
}

fn heun_boost_and_permutation(profile: Profile) {
    let mesh = Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap();
    let order: Vec<_> = (0..64).map(|i| (i * 17 + 5) % 64).collect();
    let permuted =
        Mesh::build(order.iter().map(|&i| mesh.generators[i]).collect(), [1.; 2]).unwrap();
    let boost = [2., -1., 0.8];
    let mut a = Simulation::new(mesh.clone(), config(profile, 0.0005), |x| {
        smooth(x, [0.; 3])
    })
    .unwrap();
    let mut b = Simulation::new(permuted, config(profile, 0.0005), |x| smooth(x, [0.; 3])).unwrap();
    let mut boosted = Simulation::new(
        mesh,
        Config {
            motion: Motion::Rigid([boost[0], boost[1]]),
            ..config(profile, 0.0005)
        },
        |x| smooth(x, boost),
    )
    .unwrap();
    for sim in [&mut a, &mut b, &mut boosted] {
        sim.advance_to(0.01).unwrap();
        budgets(sim);
    }
    let (qa, qb, qc) = (
        a.primitives().unwrap(),
        b.primitives().unwrap(),
        boosted.primitives().unwrap(),
    );
    for (j, &i) in order.iter().enumerate() {
        assert!((qa[i].density - qc[i].density).abs() < 1e-10);
        assert!((qa[i].pressure - qc[i].pressure).abs() < 1e-10);
        for (k, shift) in boost.iter().enumerate() {
            assert!((qa[i].magnetic[k] - qb[j].magnetic[k]).abs() < 1e-11);
            assert!((qa[i].velocity[k] - qb[j].velocity[k]).abs() < 1e-11);
            assert!((qa[i].magnetic[k] - qc[i].magnetic[k]).abs() < 1e-10);
            assert!((qa[i].velocity[k] + shift - qc[i].velocity[k]).abs() < 1e-10);
            assert!((a.state().potential[i][k] - boosted.state().potential[i][k]).abs() < 1e-10);
        }
    }
    for (k, shift) in boost.iter().take(2).enumerate() {
        let delta = (boosted.state().auxiliary_origin[k]
            - a.state().auxiliary_origin[k]
            - shift * a.time()
            + 0.5)
            .rem_euclid(1.)
            - 0.5;
        assert!(delta.abs() < 1e-12);
    }
}

macro_rules! profile_checks {
    ($name:ident, $profile:expr) => {
        mod $name {
            use super::*;
            #[test]
            fn unsupported_motion() {
                heun_rejects_deforming_motion($profile);
            }
            #[test]
            fn uniform() {
                heun_uniform_state_fixed_and_rigid($profile);
            }
            #[test]
            fn time_order() {
                heun_smooth_semidiscrete_time_order($profile);
            }
            #[test]
            fn boost_and_permutation() {
                heun_boost_and_permutation($profile);
            }
        }
    };
}
profile_checks!(nearest_bin, Profile::BulkFrameHeunV1);
profile_checks!(cubic_spline, Profile::BulkFrameHeunSplineV1);
profile_checks!(projected, Profile::BulkFrameHeunProjectedV1);
profile_checks!(quadratic, Profile::BulkFrameHeunQuadraticV1);

#[test]
fn cached_projection_reports_the_factor_shift_actually_built() {
    for profile in [
        Profile::BulkFrameHeunProjectedV1,
        Profile::BulkFrameHeunQuadraticV1,
    ] {
        for (accelerated, screening, expected) in [
            (false, 0., None),
            (false, 1., None),
            (true, 0., Some(1e-8)),
            (true, 0.5, Some(0.5)),
            (true, 1., Some(1.)),
        ] {
            let sim = Simulation::new(
                Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap(),
                Config {
                    accelerated_projection: accelerated,
                    projection_screening: screening,
                    ..config(profile, 0.0005)
                },
                |x| smooth(x, [0.; 3]),
            )
            .unwrap();
            assert_eq!(sim.projection_preconditioner_shift(), expected);
        }
    }
}

#[test]
fn projected_single_step_thread_counts_preserve_bits() {
    let run = || {
        let mut sim = Simulation::new(
            Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap(),
            config(Profile::BulkFrameHeunProjectedV1, 0.0005),
            |x| smooth(x, [0.; 3]),
        )
        .unwrap();
        sim.advance_to(0.0005).unwrap();
        assert_eq!(sim.counters().steps, 1);
        budgets(&sim);
        format!("{:?}{:?}", sim.state(), sim.counters())
    };
    let expected = run();
    for threads in [1, 4, 24] {
        assert_eq!(
            moving_mesh::parallel::with_threads(threads, run).unwrap(),
            expected
        );
    }
}

#[test]
fn quadratic_single_step_thread_counts_preserve_bits() {
    let run = || {
        let mut sim = Simulation::new(
            Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap(),
            config(Profile::BulkFrameHeunQuadraticV1, 0.0005),
            |x| smooth(x, [0.; 3]),
        )
        .unwrap();
        sim.advance_to(0.0005).unwrap();
        assert_eq!(sim.counters().steps, 1);
        budgets(&sim);
        format!("{:?}{:?}", sim.state(), sim.counters())
    };
    let expected = run();
    for threads in [1, 4, 24] {
        assert_eq!(
            moving_mesh::parallel::with_threads(threads, run).unwrap(),
            expected
        );
    }
}
