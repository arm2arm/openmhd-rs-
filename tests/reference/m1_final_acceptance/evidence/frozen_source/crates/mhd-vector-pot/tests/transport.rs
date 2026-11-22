use mhd_vector_pot::{benchmarks::passive_loop, transport::Transport};
use moving_mesh::Mesh;
use std::f64::consts::TAU;

#[test]
fn comoving_loop_preserves_discrete_a_b_on_irregular_cells() {
    for jitter in [0., 0.15] {
        let mesh = Mesh::lattice(12, 16, [1.; 2], jitter).unwrap();
        let mut sim = Transport::new(mesh, [2., 1.], [2., 1.], |x| {
            passive_loop(x, 0., [2., 1., 0.]).0
        })
        .unwrap();
        let a = sim.potential().to_vec();
        let b = sim.fields().unwrap().magnetic;
        sim.advance_to(1.).unwrap();
        assert_eq!(sim.potential(), a);
        assert_eq!(sim.fields().unwrap().magnetic, b);
        assert_eq!(sim.steps(), 0);
    }
}
#[test]
fn fixed_transport_is_boost_covariant_and_converges_for_both_signs() {
    for velocity in [[2., 1.], [-2., -1.]] {
        let mut errors = Vec::new();
        for n in [8, 16, 32] {
            let mesh = Mesh::lattice(n, n, [1.; 2], 0.15).unwrap();
            let initial = |x: [f64; 2]| (TAU * x[0]).sin() * (TAU * x[1]).sin();
            let mut a = Transport::new(mesh.clone(), velocity, [0.; 2], initial).unwrap();
            let mut b = Transport::new(
                mesh,
                [velocity[0] + 2., velocity[1] - 1.],
                [2., -1.],
                initial,
            )
            .unwrap();
            a.advance_to(0.07).unwrap();
            b.advance_to(0.07).unwrap();
            assert_eq!(a.potential(), b.potential());
            assert_eq!(a.steps(), b.steps());
            let error: f64 = a
                .mesh()
                .cells
                .iter()
                .zip(a.potential())
                .map(|(c, a)| {
                    c.volume
                        * (a[0]
                            - initial([
                                c.centroid[0] - velocity[0] * 0.07,
                                c.centroid[1] - velocity[1] * 0.07,
                            ]))
                        .abs()
                })
                .sum();
            errors.push(error);
        }
        assert!(errors.windows(2).all(|p| p[1] < p[0] / 2.));
    }
}
#[test]
fn constant_transport_and_invalid_inputs() {
    let mesh = Mesh::lattice(6, 6, [1.; 2], 0.15).unwrap();
    let mut sim = Transport::new(mesh.clone(), [2., 1.], [0.; 2], |_| 3.).unwrap();
    sim.advance_to(0.1).unwrap();
    assert!(sim.potential().iter().all(|a| a[0] == 3.));
    assert!(sim.advance_to(0.).is_err());
    assert!(sim.advance_to(f64::NAN).is_err());
    assert!(Transport::new(mesh.clone(), [f64::INFINITY, 0.], [0.; 2], |_| 0.).is_err());
    assert!(Transport::new(mesh, [0.; 2], [0.; 2], |_| f64::NAN).is_err());
}
