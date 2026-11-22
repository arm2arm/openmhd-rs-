use mhd_vector_pot::general::{Config, Initial, Motion, Profile, Simulation};
use moving_mesh::Mesh;
use std::f64::consts::TAU;

fn smooth(profile: Profile, boost: f64) -> Simulation {
    Simulation::new(
        Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap(),
        Config {
            profile,
            motion: Motion::Rigid([boost, 0.]),
            mean_magnetic: [0.3, 0.2, 0.1],
            limited: false,
            max_dt: 0.0001,
            ..Config::default()
        },
        |x| Initial {
            density: 1. + 0.01 * (TAU * x[0]).sin(),
            pressure: 1. + 0.03 * (TAU * x[1]).cos(),
            velocity: [
                boost + 0.1 * (TAU * x[1]).sin(),
                0.1 * (TAU * x[0]).cos(),
                0.,
            ],
            potential: [
                0.001 * (TAU * x[1]).cos(),
                0.001 * (TAU * x[0]).sin(),
                0.001 * (TAU * (x[0] + x[1])).sin(),
            ],
            phi: 0.,
        },
    )
    .unwrap()
}

#[test]
fn pressure_rate_matches_temporal_finite_difference_and_joint_boost() {
    for profile in [Profile::BulkFrameHeunSplineV1] {
        let base = smooth(profile, 0.);
        let rates = base.energy_rates().unwrap();
        let boosted = smooth(profile, 2.).energy_rates().unwrap();
        for (a, b) in rates.iter().zip(boosted) {
            assert!((a.pressure_rate - b.pressure_rate).abs() < 1e-10);
        }
        let initial = base.primitives().unwrap();
        let mut errors = Vec::new();
        for dt in [1e-5, 5e-6] {
            let mut sim = base.clone();
            sim.advance_to(dt).unwrap();
            assert_eq!(sim.counters().steps, 1);
            errors.push(
                sim.primitives()
                    .unwrap()
                    .iter()
                    .zip(&initial)
                    .zip(&rates)
                    .map(|((a, b), r)| ((a.pressure - b.pressure) / dt - r.pressure_rate).abs())
                    .sum::<f64>(),
            );
        }
        assert!((1.8..2.2).contains(&(errors[0] / errors[1])), "{errors:?}");
        let total_rate: f64 = rates
            .iter()
            .zip(&base.state().mesh.cells)
            .map(|(r, c)| r.total_rate * c.volume)
            .sum();
        assert!(total_rate.abs() < 1e-12);
    }
}

#[test]
fn accepted_state_observer_and_energy_diagnostics_are_passive() {
    let mut a = smooth(Profile::BulkFrameHeunSplineV1, 0.);
    let mut b = a.clone();
    a.advance_to(0.001).unwrap();
    let mut times = Vec::new();
    b.advance_to_observed(0.001, |sim| {
        sim.energy_rates()?;
        times.push(sim.time());
        Ok(())
    })
    .unwrap();
    assert_eq!(format!("{:?}", a.state()), format!("{:?}", b.state()));
    assert_eq!(format!("{:?}", a.counters()), format!("{:?}", b.counters()));
    assert_eq!(times.len(), a.counters().steps);
    assert!(times.windows(2).all(|x| x[1] > x[0]));
}

#[test]
fn uniform_energy_rates_are_zero() {
    let sim = Simulation::new(
        Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap(),
        Config {
            profile: Profile::BulkFrameHeunSplineV1,
            mean_magnetic: [0.75, 0.3, 0.1],
            motion: Motion::Rigid([2., -1.]),
            ..Config::default()
        },
        |_| Initial {
            density: 1.,
            pressure: 0.5,
            velocity: [2.1, -0.8, 0.3],
            potential: [0.; 3],
            phi: 0.,
        },
    )
    .unwrap();
    for r in sim.energy_rates().unwrap() {
        for rate in [
            r.total_rate,
            r.kinetic_rate,
            r.magnetic_rate,
            r.magnetic_rate_fv,
            r.pressure_rate,
        ] {
            assert!(rate.abs() < 1e-10);
        }
    }
}
