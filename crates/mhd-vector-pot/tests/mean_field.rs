//! Preregistered first-step mean-field boost mechanism, not a new invariance gate.
use mhd_core::{Vec3, cross};
use mhd_vector_pot::auxiliary::{SmoothVelocity, VelocitySample};
use mhd_vector_pot::general::{Config, Initial, Motion, Profile, Simulation};
use mhd_vector_pot::operators::MagneticFit;
use moving_mesh::Mesh;
use std::f64::consts::TAU;

fn initial(x: [f64; 2], boost: Vec3) -> Initial {
    let (x, y) = (TAU * x[0], TAU * x[1]);
    Initial {
        density: 1.,
        pressure: 1.,
        velocity: [
            0.2 + 0.05 * y.sin() + boost[0],
            -0.1 + 0.03 * x.cos() + boost[1],
            0.04 * (x + y).sin() + boost[2],
        ],
        potential: [0.001 * y.sin(), 0.001 * x.cos(), 0.001 * x.sin() * y.sin()],
        phi: 0.,
    }
}

#[test]
fn first_step_boost_residual_is_the_mixed_derivative_commutator() {
    let mean = [0.3, 0.2, 0.1];
    let boost = [2., -1., 0.];
    let c = cross(boost, mean);
    let dt = 1e-4;
    for n in [8, 16] {
        for jitter in [0., 0.15] {
            let mesh = Mesh::lattice(n, n, [1.; 2], jitter).unwrap();
            let mut base = Simulation::new(
                mesh.clone(),
                Config {
                    mean_magnetic: mean,
                    max_dt: dt,
                    ..Config::default()
                },
                |x| initial(x, [0.; 3]),
            )
            .unwrap();
            let mut boosted = Simulation::new(
                mesh.clone(),
                Config {
                    mean_magnetic: mean,
                    max_dt: dt,
                    motion: Motion::Rigid([boost[0], boost[1]]),
                    ..Config::default()
                },
                |x| initial(x, boost),
            )
            .unwrap();
            let samples: Vec<_> = base
                .primitives()
                .unwrap()
                .iter()
                .zip(&mesh.cells)
                .map(|(q, cell)| VelocitySample {
                    position: cell.centroid,
                    volume: cell.volume,
                    velocity: q.velocity,
                })
                .collect();
            let auxiliary = SmoothVelocity::build(mesh.lengths, &samples, [0.; 2]).unwrap();
            let ht_c: Vec<Vec3> = mesh
                .cells
                .iter()
                .map(|cell| {
                    let h = auxiliary.sample(cell.centroid, dt).unwrap().jacobian;
                    std::array::from_fn(|k| (0..3).map(|a| h[a][k] * c[a]).sum())
                })
                .collect();
            let commutator =
                MagneticFit::build(&mesh, &ht_c, &vec![0.; mesh.cells.len()], [0.; 3], false)
                    .unwrap()
                    .magnetic;
            base.advance_to(dt).unwrap();
            boosted.advance_to(dt).unwrap();
            assert_eq!(base.counters().steps, 1);
            assert_eq!(boosted.counters().steps, 1);
            assert_eq!(
                base.counters().auxiliary_roots,
                boosted.counters().auxiliary_roots
            );
            let qa = base.primitives().unwrap();
            let qb = boosted.primitives().unwrap();
            let mut a_difference = 0_f64;
            let mut b_difference = 0_f64;
            let mut residual = 0_f64;
            for i in 0..mesh.cells.len() {
                let qa_integral = base.state().conserved[i];
                let qb_integral = boosted.state().conserved[i];
                let mass = qb_integral[0];
                assert!((mass - qa_integral[0]).abs() < 1e-11);
                for (k, b) in boost.iter().enumerate() {
                    assert!((qb_integral[1 + k] - b * mass - qa_integral[1 + k]).abs() < 1e-11);
                }
                let transformed_energy = qb_integral[4]
                    - (0..3).map(|k| boost[k] * qb_integral[1 + k]).sum::<f64>()
                    + 0.5 * mass * boost.iter().map(|v| v * v).sum::<f64>();
                assert!((transformed_energy - qa_integral[4]).abs() < 1e-11);
                let expected_pressure = -(5. / 3. - 1.)
                    * 0.5
                    * (qb[i].magnetic.iter().map(|b| b * b).sum::<f64>()
                        - qa[i].magnetic.iter().map(|b| b * b).sum::<f64>());
                assert!((qb[i].pressure - qa[i].pressure - expected_pressure).abs() < 1e-11);
                for (k, shift) in boost.iter().enumerate().take(2) {
                    assert!((qb[i].magnetic[k] - qa[i].magnetic[k]).abs() < 1e-11);
                    let d = (boosted.state().mesh.cells[i].centroid[k]
                        - shift * dt
                        - mesh.cells[i].centroid[k]
                        + 0.5)
                        .rem_euclid(1.)
                        - 0.5;
                    assert!(d.abs() < 1e-11);
                }
                for (k, shift) in c.iter().enumerate() {
                    let a_expected = dt * shift - 0.5 * dt * dt * ht_c[i][k];
                    let b_expected = -0.5 * dt * dt * commutator[i][k];
                    a_difference = a_difference.max(
                        (boosted.state().potential[i][k]
                            - base.state().potential[i][k]
                            - a_expected)
                            .abs(),
                    );
                    b_difference = b_difference
                        .max((qb[i].magnetic[k] - qa[i].magnetic[k] - b_expected).abs());
                    residual = residual.max(b_expected.abs());
                }
            }
            eprintln!(
                "mean-field one-step N={n} jitter={jitter}: predicted B max={residual:.6e}, A identity error={a_difference:.6e}, B identity error={b_difference:.6e}"
            );
            assert!(a_difference <= 1e-11 && b_difference <= 1e-11);
            assert!(
                residual > 100. * b_difference,
                "probe must resolve a nonzero residual above arithmetic noise"
            );
        }
    }
}

#[test]
fn commutator_negative_controls_have_no_magnetic_boost_residual() {
    let dt = 1e-4;
    for (mean, boost, uniform_velocity) in [
        ([0.; 3], [2., -1., 0.], false),
        ([0.3, 0.2, 0.1], [0.6, 0.4, 0.2], false),
        ([0.3, 0.2, 0.1], [2., -1., 0.], true),
    ] {
        let mesh = Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap();
        let state = |x, b: Vec3| {
            let mut q = initial(x, b);
            if uniform_velocity {
                q.velocity = [0.2 + b[0], -0.1 + b[1], 0.04 + b[2]];
            }
            q
        };
        let mut a = Simulation::new(
            mesh.clone(),
            Config {
                mean_magnetic: mean,
                max_dt: dt,
                ..Config::default()
            },
            |x| state(x, [0.; 3]),
        )
        .unwrap();
        let mut b = Simulation::new(
            mesh,
            Config {
                mean_magnetic: mean,
                max_dt: dt,
                motion: Motion::Rigid([boost[0], boost[1]]),
                ..Config::default()
            },
            |x| state(x, boost),
        )
        .unwrap();
        a.advance_to(dt).unwrap();
        b.advance_to(dt).unwrap();
        assert_eq!(a.counters().steps, 1);
        assert_eq!(b.counters().steps, 1);
        for (qa, qb) in a.primitives().unwrap().iter().zip(b.primitives().unwrap()) {
            for k in 0..3 {
                assert!((qa.magnetic[k] - qb.magnetic[k]).abs() < 1e-11);
            }
        }
    }
}

#[test]
fn bulk_frame_mean_field_boost_survives_deformation_and_cleaning() {
    check_mean_field_profile(Profile::BulkFrameV1);
}
#[test]
fn symmetric_completion_boost_survives_deformation_and_cleaning() {
    check_mean_field_profile(Profile::BulkFrameHllV1);
}
#[test]
fn quadratic_completion_boost_survives_deformation_and_cleaning() {
    check_mean_field_profile(Profile::BulkFrameHllQuadraticV1);
}

#[test]
fn consistent_completion_boost_survives_deformation_and_cleaning() {
    check_mean_field_profile(Profile::BulkFrameHllConsistentV1);
}

fn check_mean_field_profile(profile: Profile) {
    let mean = [0.3, 0.2, 0.1];
    let boost = [2., -1., 0.8];
    let time = 0.01;
    for fluid in [false, true] {
        for limited in [false, true] {
            let mesh = Mesh::lattice(6, 8, [1.3, 0.7], 0.15).unwrap();
            let w: Vec<_> = mesh
                .generators
                .iter()
                .map(|x| {
                    [
                        0.1 * (TAU * x[1] / 0.7).sin(),
                        0.1 * (TAU * x[0] / 1.3).cos(),
                    ]
                })
                .collect();
            let wb = w
                .iter()
                .map(|v| [v[0] + boost[0], v[1] + boost[1]])
                .collect();
            let start = |x: [f64; 2], b| {
                let p = [x[0] / 1.3, x[1] / 0.7];
                let mut q = initial(p, b);
                q.density = 1. + 0.01 * (TAU * p[0]).sin();
                q.pressure = 1. + 0.01 * (TAU * p[1]).cos();
                q.phi = 0.0001 * (TAU * (p[0] + p[1])).cos();
                q
            };
            let cfg = Config {
                profile,
                mean_magnetic: mean,
                max_dt: 0.0005,
                limited,
                motion: if fluid {
                    Motion::Fluid
                } else {
                    Motion::Prescribed(w)
                },
                ..Config::default()
            };
            let mut a = Simulation::new(mesh.clone(), cfg.clone(), |x| start(x, [0.; 3])).unwrap();
            let mut b = Simulation::new(
                mesh,
                Config {
                    motion: if fluid {
                        Motion::Fluid
                    } else {
                        Motion::Prescribed(wb)
                    },
                    ..cfg
                },
                |x| start(x, boost),
            )
            .unwrap();
            a.advance_to(time).unwrap();
            b.advance_to(time).unwrap();
            assert_eq!(a.counters().auxiliary_roots, b.counters().auxiliary_roots);
            let mut max_error = 0_f64;
            let b_cross_mean = cross(boost, mean);
            for (i, (qa, qb)) in a
                .primitives()
                .unwrap()
                .iter()
                .zip(b.primitives().unwrap())
                .enumerate()
            {
                max_error = max_error
                    .max((qa.density - qb.density).abs())
                    .max((qa.pressure - qb.pressure).abs());
                for k in 0..3 {
                    max_error = max_error
                        .max((qa.velocity[k] - qb.velocity[k] + boost[k]).abs())
                        .max((qa.magnetic[k] - qb.magnetic[k]).abs());
                    assert!((b.state().potential[i][k] - a.state().potential[i][k]).abs() < 1e-9);
                    assert!(
                        (b.state().gauge_offset[k]
                            - a.state().gauge_offset[k]
                            - time * b_cross_mean[k])
                            .abs()
                            < 1e-11
                    );
                }
                assert!((b.state().phi[i] - a.state().phi[i]).abs() < 1e-9);
                let qa_integral = a.state().conserved[i];
                let qb_integral = b.state().conserved[i];
                let eb = qb_integral[4]
                    - (0..3).map(|k| boost[k] * qb_integral[1 + k]).sum::<f64>()
                    + 0.5 * qb_integral[0] * boost.iter().map(|v| v * v).sum::<f64>();
                max_error =
                    max_error.max((eb - qa_integral[4]).abs() / a.state().mesh.cells[i].volume);
            }
            eprintln!(
                "{profile:?} rectangular fluid={fluid} limited={limited}: transformed max={max_error:.6e}"
            );
            assert!(max_error <= 1e-9);
            for sim in [&a, &b] {
                let d = sim.diagnostics().unwrap();
                assert!(d.min_density > 0. && d.min_pressure > 0.);
                assert!(d.normalized_budget.iter().all(|v| v.abs() < 1e-10));
            }
        }
    }
}

#[test]
fn bulk_frame_preserves_uniform_total_potential_drift_and_mean_zero_cleaning() {
    let mean = [0.3, 0.2, 0.1];
    let v = [0.4, -0.2, 0.3];
    let drift = cross(v, mean);
    for jitter in [0., 0.15] {
        for motion in [Motion::Fixed, Motion::Rigid([0.7, -0.8])] {
            let mesh = Mesh::lattice(6, 6, [1.; 2], jitter).unwrap();
            let mut sim = Simulation::new(
                mesh,
                Config {
                    profile: Profile::BulkFrameV1,
                    mean_magnetic: mean,
                    motion,
                    ..Config::default()
                },
                |_| Initial {
                    density: 1.,
                    pressure: 1.,
                    velocity: v,
                    potential: [0.1, -0.05, 0.03],
                    phi: 0.,
                },
            )
            .unwrap();
            sim.advance_to(0.05).unwrap();
            for (a, q) in sim.total_potential().iter().zip(sim.primitives().unwrap()) {
                for k in 0..3 {
                    assert!((a[k] - [0.1, -0.05, 0.03][k] - 0.05 * drift[k]).abs() < 1e-10);
                    assert!((q.magnetic[k] - mean[k]).abs() < 1e-10);
                }
                assert!((q.density - 1.).abs() < 1e-10 && (q.pressure - 1.).abs() < 1e-10);
            }
        }
    }
    let mesh = Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap();
    let start = |x: [f64; 2]| Initial {
        density: 1.,
        pressure: 0.6,
        velocity: [0.; 3],
        potential: [0.001 * (TAU * x[0]).cos(), 0., 0.],
        phi: 0.,
    };
    let mut a = Simulation::new(
        mesh.clone(),
        Config {
            max_dt: 0.0005,
            ..Config::default()
        },
        start,
    )
    .unwrap();
    let mut b = Simulation::new(
        mesh,
        Config {
            profile: Profile::BulkFrameV1,
            max_dt: 0.0005,
            ..Config::default()
        },
        start,
    )
    .unwrap();
    a.advance_to(0.05).unwrap();
    b.advance_to(0.05).unwrap();
    assert_eq!(a.state().potential, b.state().potential);
    assert_eq!(a.state().phi, b.state().phi);
    assert_eq!(a.state().conserved, b.state().conserved);
    assert_eq!(b.state().gauge_offset, [0.; 3]);
}

#[test]
fn matched_cleaning_boost_survives_deformation() {
    check_mean_field_profile(Profile::BulkFrameHllMatchedV1);
}
