use mhd_core::Primitive;
use mhd_vector_pot::{
    benchmarks,
    ct::{Config, Geometry, Simulation},
};
use moving_mesh::Mesh;
use std::f64::consts::TAU;

#[test]
fn periodic_incidence_constant_field_and_faraday_sign() {
    for jitter in [0., 0.15] {
        for lengths in [[1., 1.], [2., 0.125]] {
            let mesh = Mesh::lattice(16, 4, lengths, jitter).unwrap();
            let geometry = Geometry::new(&mesh).unwrap();
            let mean = [0.75, -0.23];
            let flux = geometry.fluxes(&mesh, |_| 0., mean);
            for b in geometry.field(&flux) {
                for k in 0..2 {
                    assert!((b[k] - mean[k]).abs() < 2e-12);
                }
            }
            assert!(
                geometry
                    .divergence(&mesh, &flux)
                    .iter()
                    .all(|d| d.abs() < 2e-10)
            );
            let az =
                |p: [f64; 2]| (TAU * p[0] / lengths[0]).sin() * (TAU * p[1] / lengths[1]).cos();
            let potential_flux = geometry.fluxes(&mesh, az, mean);
            assert!(
                geometry
                    .divergence(&mesh, &potential_flux)
                    .iter()
                    .all(|d| d.abs() < 2e-9)
            );
            // Arbitrary EMFs must cancel around every cell, including seam faces.
            let emf: Vec<_> = mesh
                .faces
                .iter()
                .enumerate()
                .map(|(i, _)| (i as f64 * 1.23).sin())
                .collect();
            let rate = geometry.flux_rate(&emf);
            assert!(
                geometry
                    .divergence(&mesh, &rate)
                    .iter()
                    .all(|d| d.abs() < 2e-9)
            );
        }
    }
    // Regular grid: affine EMF=y implies dBx=+1, dBy=0 away from the periodic seam.
    let mesh = Mesh::lattice(8, 8, [1., 1.], 0.).unwrap();
    let geometry = Geometry::new(&mesh).unwrap();
    let emf: Vec<_> = mesh
        .faces
        .iter()
        .map(|f| f.centroid[1].rem_euclid(1.))
        .collect();
    let db = geometry.field(&geometry.flux_rate(&emf));
    for (i, c) in mesh.cells.iter().enumerate() {
        if c.centroid[1] > 0.25 && c.centroid[1] < 0.75 {
            assert!((db[i][0] - 1.).abs() < 1e-12, "{:?}", db[i]);
            assert!(db[i][1].abs() < 1e-12);
        }
    }
}

#[test]
fn uniform_fixed_and_rigid_states_preserved() {
    for jitter in [0., 0.15] {
        for w in [[0., 0.], [2., -1.]] {
            let q = Primitive {
                density: 1.,
                pressure: 0.6,
                velocity: [0.4, -0.2, 0.3],
                magnetic: [0.7, -0.2, 0.5],
            };
            let mut sim = Simulation::new(
                Mesh::lattice(6, 6, [1., 1.], jitter).unwrap(),
                Config {
                    mean_xy: [q.magnetic[0], q.magnetic[1]],
                    mesh_velocity: w,
                    ..Config::default()
                },
                |_| (0., q),
            )
            .unwrap();
            sim.advance_to(0.02).unwrap();
            for p in sim.recover(&sim.state).unwrap() {
                assert!((p.density - q.density).abs() < 2e-12);
                assert!((p.pressure - q.pressure).abs() < 2e-12);
                for k in 0..3 {
                    assert!((p.magnetic[k] - q.magnetic[k]).abs() < 2e-12);
                    assert!((p.velocity[k] - q.velocity[k]).abs() < 2e-12);
                }
            }
            assert!(sim.diagnostics().unwrap().budget_max < 2e-13);
        }
    }
}

fn wave(boost: [f64; 3]) -> Simulation {
    Simulation::new(
        Mesh::lattice(8, 8, [1., 1.], 0.15).unwrap(),
        Config {
            mean_xy: [1., 0.],
            mesh_velocity: [boost[0], boost[1]],
            max_dt: 0.00025,
            ..Config::default()
        },
        |x| {
            (
                benchmarks::alfven_initial(x, 0., boost).potential[2],
                benchmarks::alfven_exact(x, 0., 0., boost),
            )
        },
    )
    .unwrap()
}

#[test]
fn nonuniform_boost_budget_and_ct_divergence() {
    let mut a = wave([0.; 3]);
    let mut b = wave([2., -1., 0.]);
    a.advance_to(0.002).unwrap();
    b.advance_to(0.002).unwrap();
    let qa = a.recover(&a.state).unwrap();
    let qb = b.recover(&b.state).unwrap();
    for (a, b) in qa.iter().zip(qb) {
        assert!((a.density - b.density).abs() < 1e-11);
        assert!((a.pressure - b.pressure).abs() < 1e-11);
        for (k, shift) in [2., -1., 0.].into_iter().enumerate() {
            assert!((a.magnetic[k] - b.magnetic[k]).abs() < 1e-11);
            assert!((a.velocity[k] + shift - b.velocity[k]).abs() < 1e-11);
        }
    }
    for s in [&a, &b] {
        let d = s.diagnostics().unwrap();
        assert!(d.budget_max < 1e-12);
        assert!(d.div_ct_max < 1e-10);
    }
}

#[test]
fn frozen_pressure_rate_matches_finite_difference() {
    let mut sim = wave([0.; 3]);
    let before = sim.recover(&sim.state).unwrap();
    let rates = sim.energy_rates().unwrap();
    sim.advance_to(1e-7).unwrap();
    let after = sim.recover(&sim.state).unwrap();
    for ((a, b), r) in before.iter().zip(after).zip(rates) {
        assert!(((b.pressure - a.pressure) / 1e-7 - r[3]).abs() < 1e-6);
    }
}

#[test]
fn rejected_invalid_state_or_target_does_not_mutate_solution() {
    let mut sim = wave([0.; 3]);
    let old = sim.state.clone();
    assert!(sim.step(f64::NAN).is_err());
    assert_eq!(sim.state.fluid, old.fluid);
    sim.state.fluid[3][4] = -1.;
    let old = sim.state.clone();
    assert!(sim.step(0.01).is_err());
    assert_eq!(sim.state.fluid, old.fluid);
    assert_eq!(sim.state.flux, old.flux);
    assert_eq!(sim.state.bz_integral, old.bz_integral);
    assert_eq!(sim.time, 0.);
}

#[test]
fn admissible_profile_inactive_on_smooth_wave_and_covariant_under_boost() {
    let mut original = wave([0.; 3]);
    let mut limited = wave([0.; 3]);
    limited.config.admissible_limiter = true;
    let mut boosted = wave([2., -1., 0.]);
    boosted.config.admissible_limiter = true;
    for s in [&mut original, &mut limited, &mut boosted] {
        s.advance_to(0.002).unwrap();
    }
    assert_eq!(limited.limited_stages, 0);
    assert_eq!(limited.state.fluid, original.state.fluid);
    assert_eq!(limited.state.flux, original.state.flux);
    assert_eq!(limited.state.bz_integral, original.state.bz_integral);
    let a = limited.recover(&limited.state).unwrap();
    let b = boosted.recover(&boosted.state).unwrap();
    for (a, b) in a.iter().zip(b) {
        assert!((a.pressure - b.pressure).abs() < 1e-11);
        for (k, shift) in [2., -1., 0.].into_iter().enumerate() {
            assert!((a.velocity[k] + shift - b.velocity[k]).abs() < 1e-11);
            assert!((a.magnetic[k] - b.magnetic[k]).abs() < 1e-11);
        }
    }
}
