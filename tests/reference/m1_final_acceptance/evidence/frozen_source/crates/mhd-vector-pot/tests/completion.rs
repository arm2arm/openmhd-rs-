use mhd_vector_pot::general::{Config, Initial, Motion, Profile, Simulation};
use moving_mesh::Mesh;
use std::f64::consts::TAU;

#[test]
fn signal_completion_survives_cell_permutation_and_deforming_boost() {
    for jitter in [0., 0.15] {
        let mesh = Mesh::lattice(6, 8, [1.3, 0.7], jitter).unwrap();
        let order: Vec<_> = (0..48).map(|i| (i * 17 + 5) % 48).collect();
        let permuted = Mesh::build(
            order.iter().map(|&i| mesh.generators[i]).collect(),
            mesh.lengths,
        )
        .unwrap();
        let boost = [2., -1., 0.8];
        let initial = |x: [f64; 2], b: [f64; 3]| Initial {
            density: 1. + 0.01 * (TAU * x[0] / 1.3).sin(),
            pressure: 1.,
            velocity: [
                0.2 + 0.05 * (TAU * x[1] / 0.7).sin() + b[0],
                -0.1 + b[1],
                0.04 + b[2],
            ],
            potential: [
                0.001 * (TAU * x[1] / 0.7).sin(),
                0.001 * (TAU * x[0] / 1.3).cos(),
                0.001 * (TAU * x[0] / 1.3).sin() * (TAU * x[1] / 0.7).sin(),
            ],
            phi: 0.0001 * (TAU * x[0] / 1.3).cos(),
        };
        let cfg = Config {
            profile: Profile::BulkFrameSignalV1,
            motion: Motion::Fluid,
            mean_magnetic: [0.3, 0.2, 0.1],
            max_dt: 0.0005,
            ..Config::default()
        };
        let mut a = Simulation::new(mesh.clone(), cfg.clone(), |x| initial(x, [0.; 3])).unwrap();
        let mut b = Simulation::new(permuted, cfg.clone(), |x| initial(x, [0.; 3])).unwrap();
        let mut boosted = Simulation::new(mesh, cfg, |x| initial(x, boost)).unwrap();
        a.advance_to(0.01).unwrap();
        b.advance_to(0.01).unwrap();
        boosted.advance_to(0.01).unwrap();
        let qa = a.primitives().unwrap();
        let qb = b.primitives().unwrap();
        let qc = boosted.primitives().unwrap();
        for (j, &i) in order.iter().enumerate() {
            for (k, shift) in boost.iter().enumerate() {
                assert!((qa[i].magnetic[k] - qb[j].magnetic[k]).abs() < 1e-11);
                assert!((qa[i].velocity[k] - qb[j].velocity[k]).abs() < 1e-11);
                assert!((a.state().potential[i][k] - b.state().potential[j][k]).abs() < 1e-11);
                assert!((qa[i].magnetic[k] - qc[i].magnetic[k]).abs() < 1e-9);
                assert!((qa[i].velocity[k] + shift - qc[i].velocity[k]).abs() < 1e-9);
            }
            assert!((qa[i].density - qc[i].density).abs() < 1e-9);
            assert!((qa[i].pressure - qc[i].pressure).abs() < 1e-9);
        }
        for sim in [&a, &b, &boosted] {
            let d = sim.diagnostics().unwrap();
            assert!(d.min_density > 0. && d.min_pressure > 0.);
            assert!(d.normalized_budget.iter().all(|v| v.abs() < 1e-10));
        }
    }
}
