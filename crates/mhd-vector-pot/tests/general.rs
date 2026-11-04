use mhd_core::{IdealGas, cross};
use mhd_vector_pot::general::{Config, Initial, Motion, Simulation};
use mhd_vector_pot::operators::{MagneticFit, face_velocity, material_derivative, predict};
use moving_mesh::{Mesh, dot};
use std::f64::consts::TAU;
fn near(a: f64, b: f64, t: f64) {
    assert!(
        (a - b).abs() <= t * (1. + a.abs().max(b.abs())),
        "{a} != {b}"
    );
}
fn base() -> Initial {
    Initial {
        density: 1.,
        pressure: 1.,
        velocity: [0.4, -0.2, 0.3],
        potential: [0.1, -0.05, 0.03],
        phi: 0.,
    }
}
fn budgets(s: &Simulation) {
    let d = s.diagnostics().unwrap();
    assert!(d.min_density > 0. && d.min_pressure > 0.);
    assert!(d.normalized_budget.iter().all(|x| x.abs() < 1e-10));
}
#[test]
fn uniform_full_components_and_mean_field() {
    let mean = [0.3, 0.2, 0.1];
    for jitter in [0., 0.15] {
        for motion in [Motion::Fixed, Motion::Rigid([0.7, -0.8])] {
            let mesh = Mesh::lattice(6, 6, [1.; 2], jitter).unwrap();
            let mut sim = Simulation::new(
                mesh,
                Config {
                    mean_magnetic: mean,
                    motion,
                    ..Config::default()
                },
                |_| base(),
            )
            .unwrap();
            sim.advance_to(0.05).unwrap();
            let source = cross(base().velocity, mean);
            for (i, q) in sim.primitives().unwrap().iter().enumerate() {
                near(q.density, 1., 1e-10);
                near(q.pressure, 1., 1e-10);
                for k in 0..3 {
                    near(q.velocity[k], base().velocity[k], 1e-10);
                    near(q.magnetic[k], mean[k], 1e-10);
                    near(
                        sim.state().potential[i][k],
                        base().potential[k] + 0.05 * source[k],
                        1e-10,
                    );
                }
            }
            budgets(&sim);
        }
    }
}
fn smooth(x: [f64; 2], boost: [f64; 3]) -> Initial {
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
fn repeated_auxiliary_rebuilds_are_boost_covariant() {
    for jitter in [0., 0.15] {
        let mesh = Mesh::lattice(8, 8, [1.; 2], jitter).unwrap();
        let boost = [2., -1., 0.];
        let mut a =
            Simulation::new(mesh.clone(), Config::default(), |x| smooth(x, [0.; 3])).unwrap();
        let mut b = Simulation::new(
            mesh,
            Config {
                motion: Motion::Rigid([2., -1.]),
                ..Config::default()
            },
            |x| smooth(x, boost),
        )
        .unwrap();
        a.advance_to(0.02).unwrap();
        b.advance_to(0.02).unwrap();
        assert!(a.counters().steps > 2);
        assert_eq!(a.counters().auxiliary_roots, b.counters().auxiliary_roots);
        for (qa, qb) in a.primitives().unwrap().iter().zip(b.primitives().unwrap()) {
            near(qa.density, qb.density, 1e-9);
            near(qa.pressure, qb.pressure, 1e-9);
            for (k, shift) in boost.iter().enumerate() {
                near(qa.velocity[k], qb.velocity[k] - shift, 1e-9);
                near(qa.magnetic[k], qb.magnetic[k], 1e-9);
            }
            let ea = IdealGas::new(5. / 3.).unwrap().conservative(*qa).unwrap()[4];
            let eb = IdealGas::new(5. / 3.).unwrap().conservative(qb).unwrap()[4];
            let transformed = eb
                - qb.density * (boost[0] * qb.velocity[0] + boost[1] * qb.velocity[1])
                + 0.5 * qb.density * 5.;
            near(ea, transformed, 1e-9);
        }
        for (k, shift) in boost.iter().take(2).enumerate() {
            let d = (b.state().auxiliary_origin[k] - a.state().auxiliary_origin[k] - shift * 0.02
                + 0.5)
                .rem_euclid(1.)
                - 0.5;
            near(d, 0., 1e-9);
        }
        budgets(&a);
        budgets(&b);
    }
}
#[test]
fn curl_three_components_converges() {
    for jitter in [0., 0.15] {
        let mut errors = Vec::new();
        for n in [8, 16, 32] {
            let mesh = Mesh::lattice(n, n, [1.; 2], jitter).unwrap();
            let a: Vec<_> = mesh
                .cells
                .iter()
                .map(|c| smooth(c.centroid, [0.; 3]).potential)
                .collect();
            let fit = MagneticFit::build(&mesh, &a, &vec![0.; a.len()], [0.; 3], true).unwrap();
            let mut l1 = 0.;
            let mut l2 = 0.;
            for (c, b) in mesh.cells.iter().zip(&fit.magnetic) {
                let (x, y) = (TAU * c.centroid[0], TAU * c.centroid[1]);
                let exact = [
                    0.001 * TAU * x.sin() * y.cos(),
                    -0.001 * TAU * x.cos() * y.sin(),
                    -0.001 * TAU * (x.sin() + y.cos()),
                ];
                let e = (0..3)
                    .map(|k| (b[k] - exact[k]).powi(2))
                    .sum::<f64>()
                    .sqrt();
                l1 += c.volume * e;
                l2 += c.volume * e * e;
            }
            errors.push([l1, l2.sqrt()]);
        }
        eprintln!("curl jitter={jitter}: {errors:?}");
        for pair in errors.windows(2) {
            for k in 0..2 {
                assert!((pair[0][k] / pair[1][k]).log2() > if jitter == 0. { 1.8 } else { 0.7 });
            }
        }
    }
}
#[test]
fn material_predictor_and_bisector_algebra() {
    let eos = IdealGas::new(5. / 3.).unwrap();
    let q = mhd_core::Primitive {
        density: 2.,
        pressure: 3.,
        velocity: [0.4, -0.7, 0.2],
        magnetic: [0.3, -0.8, 0.5],
    };
    let g = [
        [0.2, -0.1],
        [0.3, 0.4],
        [-0.2, 0.5],
        [0.6, -0.7],
        [0.9, -0.3],
        [0.8, 0.2],
        [-0.4, 0.7],
        [0.5, -0.6],
    ];
    let rate = material_derivative(eos, q, g);
    let theta = 0.8;
    let force = cross([-0.6, -0.5, -0.6], q.magnetic);
    near(rate[0], -2. * theta, 1e-11);
    near(rate[4], -5. * theta, 1e-11);
    for k in 0..3 {
        near(
            rate[1 + k],
            (force[k] - if k < 2 { g[4][k] } else { 0. }) / 2.,
            1e-11,
        );
        near(
            rate[5 + k],
            g[1 + k][0] * 0.3 - g[1 + k][1] * 0.8 - q.magnetic[k] * theta,
            1e-11,
        );
    }
    assert!((g[5][0] + g[6][1]).abs() > 1.); // explicitly nonzero estimated div(B)
    let boost = [13., -7., 2.];
    let mut qb = q;
    for (v, b) in qb.velocity.iter_mut().zip(boost) {
        *v += b;
    }
    let dt = 0.001;
    let offset = [0.004, -0.002];
    let a = predict(eos, q, g, offset, dt).unwrap();
    let b = predict(
        eos,
        qb,
        g,
        [offset[0] + dt * boost[0], offset[1] + dt * boost[1]],
        dt,
    )
    .unwrap();
    near(a.density, b.density, 1e-11);
    near(a.pressure, b.pressure, 1e-11);
    for (k, shift) in boost.iter().enumerate() {
        near(a.velocity[k], b.velocity[k] - shift, 1e-11);
        near(a.magnetic[k], b.magnetic[k], 1e-11);
    }
    let mesh = Mesh::lattice(6, 6, [1.; 2], 0.15).unwrap();
    let w: Vec<_> = mesh
        .generators
        .iter()
        .map(|r| [r[1].sin(), r[0].cos()])
        .collect();
    for f in &mesh.faces {
        let ri = mesh.generators[f.left];
        let rj: [f64; 2] =
            std::array::from_fn(|k| mesh.generators[f.right][k] + f64::from(f.image[k]));
        let d = [rj[0] - ri[0], rj[1] - ri[1]];
        let z = [
            f.centroid[0] - 0.5 * (ri[0] + rj[0]),
            f.centroid[1] - 0.5 * (ri[1] + rj[1]),
        ];
        let wf = face_velocity(&mesh, f, &w).unwrap();
        let lhs = dot(
            [
                wf[0] - 0.5 * (w[f.left][0] + w[f.right][0]),
                wf[1] - 0.5 * (w[f.left][1] + w[f.right][1]),
            ],
            d,
        ) + dot(
            z,
            [w[f.right][0] - w[f.left][0], w[f.right][1] - w[f.left][1]],
        );
        near(lhs, 0., 1e-11);
    }
}

#[test]
fn frozen_cleaning_mode_and_irregular_contamination() {
    let n = 16;
    let t = 0.05;
    let gamma = 5. / 3.;
    let initial = |x: [f64; 2]| Initial {
        density: 1.,
        pressure: 1. / gamma,
        velocity: [0.; 3],
        potential: [0.001 * (TAU * x[0]).cos(), 0., 0.],
        phi: 0.,
    };
    let k = (TAU / n as f64).sin() * n as f64;
    let damping = 0.15 * n as f64 * std::f64::consts::PI.sqrt();
    let omega = (k * k - 0.25 * damping * damping).sqrt();
    let a = 0.001
        * (-0.5 * damping * t).exp()
        * ((omega * t).cos() + 0.5 * damping / omega * (omega * t).sin());
    let phi = -0.001 * k / omega * (-0.5 * damping * t).exp() * (omega * t).sin();
    let mut errors = Vec::new();
    for max_dt in [0.001, 0.0005, 0.00025] {
        let mut sim = Simulation::new(
            Mesh::lattice(n, n, [1.; 2], 0.).unwrap(),
            Config {
                gamma,
                max_dt,
                ..Config::default()
            },
            initial,
        )
        .unwrap();
        sim.advance_to(t).unwrap();
        let mut ea = 0.;
        let mut ep = 0.;
        for (i, c) in sim.state().mesh.cells.iter().enumerate() {
            ea +=
                c.volume * (sim.state().potential[i][0] - a * (TAU * c.centroid[0]).cos()).powi(2);
            ep += c.volume * (sim.state().phi[i] - phi * (TAU * c.centroid[0]).sin()).powi(2);
        }
        errors.push([ea.sqrt(), ep.sqrt()]);
        assert!(
            sim.primitives()
                .unwrap()
                .iter()
                .flat_map(|q| q.magnetic)
                .all(|b| b.abs() < 1e-10)
        );
        budgets(&sim);
    }
    eprintln!("gauge errors A,phi: {errors:?}");
    for k in 0..2 {
        let order = (errors[1][k] / errors[2][k]).log2();
        assert!((0.8..=1.2).contains(&order), "gauge order {order}");
    }
    let mut sim = Simulation::new(
        Mesh::lattice(n, n, [1.; 2], 0.15).unwrap(),
        Config {
            gamma,
            max_dt: 0.0005,
            ..Config::default()
        },
        initial,
    )
    .unwrap();
    let initial_b = sim.magnetic_fit().unwrap().magnetic;
    sim.advance_to(t).unwrap();
    let final_b = sim.magnetic_fit().unwrap().magnetic;
    let initial_max = initial_b
        .iter()
        .flatten()
        .map(|b| b.abs())
        .fold(0., f64::max);
    let delta = initial_b
        .iter()
        .flatten()
        .zip(final_b.iter().flatten())
        .map(|(a, b)| (a - b).abs())
        .fold(0., f64::max);
    eprintln!("irregular gauge initial |B| component max={initial_max}, final change={delta}");
    assert!(
        sim.state()
            .potential
            .iter()
            .flatten()
            .chain(&sim.state().phi)
            .all(|x| x.abs() <= 0.002)
    );
    budgets(&sim);
}

#[test]
fn deforming_geometry_converges_without_energy_repair() {
    let mut errors = Vec::new();
    for max_dt in [0.004, 0.002, 0.001] {
        let mesh = Mesh::lattice(6, 6, [1.; 2], 0.).unwrap();
        let w = mesh
            .generators
            .iter()
            .map(|x| [0.1 * (TAU * x[1]).sin(), 0.1 * (TAU * x[0]).cos()])
            .collect();
        let mut sim = Simulation::new(
            mesh,
            Config {
                mean_magnetic: [0.3, 0.2, 0.1],
                motion: Motion::Prescribed(w),
                max_dt,
                ..Config::default()
            },
            |_| Initial {
                density: 1.,
                pressure: 0.01,
                velocity: [0.; 3],
                potential: [0.; 3],
                phi: 0.,
            },
        )
        .unwrap();
        sim.advance_to(0.04).unwrap();
        let error = sim
            .primitives()
            .unwrap()
            .iter()
            .map(|q| {
                (q.density - 1.)
                    .abs()
                    .max((q.pressure - 0.01).abs())
                    .max(q.velocity.iter().map(|v| v.abs()).fold(0., f64::max))
                    .max(
                        q.magnetic
                            .iter()
                            .zip([0.3, 0.2, 0.1])
                            .map(|(a, b)| (a - b).abs())
                            .fold(0., f64::max),
                    )
            })
            .fold(0., f64::max);
        errors.push(error);
        budgets(&sim);
    }
    eprintln!(
        "deforming physical-state max errors={errors:?}, orders={:?}",
        errors
            .windows(2)
            .map(|p| (p[0] / p[1]).log2())
            .collect::<Vec<_>>()
    );
    assert!(errors[2] < errors[0]);
}

#[test]
fn invalid_initial_data_are_rejected() {
    let mesh = Mesh::lattice(4, 4, [1.; 2], 0.).unwrap();
    for config in [
        Config {
            gamma: 1.,
            ..Config::default()
        },
        Config {
            cfl: 0.4,
            ..Config::default()
        },
        Config {
            motion: Motion::Prescribed(vec![]),
            ..Config::default()
        },
        Config {
            max_dt: 0.,
            ..Config::default()
        },
    ] {
        assert!(Simulation::new(mesh.clone(), config, |_| base()).is_err());
    }
    assert!(
        Simulation::new(mesh, Config::default(), |_| Initial {
            phi: f64::NAN,
            ..base()
        })
        .is_err()
    );
}
