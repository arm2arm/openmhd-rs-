use mhd_core::cross;
use mhd_vector_pot::general::{Config, Initial, Motion, Profile, Simulation};
use moving_mesh::Mesh;

#[test]
fn paper_state_source_preserves_uniform_state_and_mean_field_drift() {
    let profile = Profile::PaperStateEmfV1;
    assert!(!profile.is_heun());
    assert_eq!(profile.name(), "paper-state-emf-v1");
    let mean = [0.3, 0.2, -0.1];
    for jitter in [0., 0.15] {
        for motion in [Motion::Fixed, Motion::Rigid([0.7, -0.4])] {
            let initial = Initial {
                density: 1.,
                pressure: 0.7,
                velocity: [0.2, -0.1, 0.3],
                potential: [0.03, -0.04, 0.05],
                phi: 0.,
            };
            let mut sim = Simulation::new(
                Mesh::lattice(8, 8, [1.; 2], jitter).unwrap(),
                Config {
                    profile,
                    mean_magnetic: mean,
                    motion,
                    max_dt: 0.0005,
                    ..Config::default()
                },
                |_| initial,
            )
            .unwrap();
            sim.advance_to(0.005).unwrap();
            let expected_rate = cross(initial.velocity, mean);
            for (i, q) in sim.primitives().unwrap().iter().enumerate() {
                assert!((q.density - initial.density).abs() < 1e-11);
                assert!((q.pressure - initial.pressure).abs() < 1e-11);
                for k in 0..3 {
                    assert!((q.magnetic[k] - mean[k]).abs() < 1e-11);
                    assert!((q.velocity[k] - initial.velocity[k]).abs() < 1e-11);
                    assert!(
                        (sim.state().potential[i][k]
                            - initial.potential[k]
                            - sim.time() * expected_rate[k])
                            .abs()
                            < 1e-11
                    );
                }
            }
            assert!(
                sim.diagnostics()
                    .unwrap()
                    .normalized_budget
                    .iter()
                    .all(|x| x.abs() < 1e-11)
            );
            assert_eq!(sim.counters().rejected_state, 0);
        }
    }
}
