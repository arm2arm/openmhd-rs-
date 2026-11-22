use mhd_core::IdealGas;
use mhd_vector_pot::general::{Config, Initial, Motion, Profile, Simulation};
use moving_mesh::Mesh;

#[test]
fn accepted_signal_travel_matches_uniform_characteristics_and_is_passive() {
    for profile in [Profile::PaperGlobalV2, Profile::BulkFrameHeunSplineV1] {
        for boost in [0., 2.] {
            let base = Config {
                profile,
                mean_magnetic: [0.75, 0.3, 0.1],
                motion: Motion::Rigid([boost, 0.]),
                max_dt: 0.001,
                ..Config::default()
            };
            let mesh = Mesh::lattice(8, 4, [2., 0.125], 0.).unwrap();
            let initial = |_| Initial {
                density: 1.,
                pressure: 0.5,
                velocity: [0.2 + boost, -0.1, 0.3],
                potential: [0.; 3],
                phi: 0.,
            };
            let mut a = Simulation::new(mesh.clone(), base.clone(), initial).unwrap();
            let mut b = Simulation::new(
                mesh,
                Config {
                    track_signal_travel: true,
                    ..base
                },
                initial,
            )
            .unwrap();
            let q = b.primitives().unwrap()[0];
            let expected = 0.01
                * ((q.velocity[0] - boost).abs()
                    + IdealGas::new(5. / 3.).unwrap().fast_speed(q, [1., 0., 0.]));
            a.advance_to(0.01).unwrap();
            b.advance_to(0.01).unwrap();
            assert_eq!(format!("{:?}", a.state()), format!("{:?}", b.state()));
            assert_eq!(a.counters().signal_travel_x, 0.);
            assert!((b.counters().signal_travel_x - expected).abs() < 1e-12);
            assert_eq!(a.counters().steps, b.counters().steps);
        }
    }
}
