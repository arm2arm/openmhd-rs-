use mhd_vector_pot::general::{Config, Initial, Motion, Profile, Simulation};
use moving_mesh::{Mesh, parallel};
use std::f64::consts::TAU;

#[test]
fn threaded_coupled_states_diagnostics_and_counters_match_serial_bits() {
    for profile in [
        Profile::PaperGlobalV2,
        Profile::BulkFrameV1,
        Profile::BulkFrameSignalV1,
        Profile::BulkFrameHeunV1,
        Profile::BulkFrameHeunSplineV1,
    ] {
        for moving in [false, true] {
            let run = || {
                let mesh = Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap();
                let motion = if !moving {
                    Motion::Fixed
                } else if profile.is_heun() {
                    Motion::Rigid([2., -1.])
                } else {
                    Motion::Fluid
                };
                let mut sim = Simulation::new(
                    mesh,
                    Config {
                        profile,
                        motion,
                        mean_magnetic: [0.3, 0.2, 0.1],
                        max_dt: 0.0005,
                        ..Config::default()
                    },
                    |x| Initial {
                        density: 1. + 0.01 * (TAU * x[0]).sin(),
                        pressure: 1.,
                        velocity: [2. + 0.05 * (TAU * x[1]).sin(), -1., 0.3],
                        potential: [
                            0.001 * (TAU * x[1]).sin(),
                            0.001 * (TAU * x[0]).cos(),
                            0.001 * (TAU * x[0]).sin() * (TAU * x[1]).sin(),
                        ],
                        phi: 0.0001 * (TAU * x[0]).cos(),
                    },
                )
                .unwrap();
                sim.advance_to(0.004).unwrap();
                let d = sim.diagnostics().unwrap();
                assert!(d.min_density > 0. && d.min_pressure > 0.);
                assert!(d.normalized_budget.iter().all(|e| e.abs() < 1e-10));
                format!("{:?}{:?}{d:?}", sim.state(), sim.counters())
            };
            let serial = run();
            for threads in [1, 2, 4, 24] {
                assert_eq!(
                    parallel::with_threads(threads, run).unwrap(),
                    serial,
                    "profile {profile:?}, moving {moving}, threads {threads}"
                );
            }
        }
    }
}
