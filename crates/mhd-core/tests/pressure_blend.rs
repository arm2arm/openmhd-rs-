use mhd_core::{
    FaceCompletion, FaceFlux, FluxMethod, IdealGas, Primitive, RiemannSolver, cross, dot,
    riemann_with_pressure_blend, riemann_with_solver,
};

fn close(a: f64, b: f64) {
    assert!(
        (a - b).abs() < 2e-12 * (1. + a.abs() + b.abs()),
        "{a} != {b}"
    );
}
fn states() -> (Primitive, Primitive) {
    (
        Primitive {
            density: 1.,
            pressure: 1.,
            velocity: [0.1, -0.1, 0.2],
            magnetic: [0.4, 0.2, 0.1],
        },
        Primitive {
            density: 0.8,
            pressure: 0.8,
            velocity: [-0.1, 0.1, 0.],
            magnetic: [0.4, -0.1, 0.1],
        },
    )
}
fn exact(a: FaceFlux, b: FaceFlux) {
    assert_eq!(a.fluid, b.fluid);
    assert_eq!(a.induction, b.induction);
    assert_eq!(a.electromotive, b.electromotive);
    assert_eq!(a.velocity, b.velocity);
    assert_eq!(a.magnetic, b.magnetic);
    assert_eq!(a.max_speed, b.max_speed);
    assert_eq!(a.method, b.method);
}

#[test]
fn pressure_blend_endpoints_retain_exact_fluxes_and_invalid_weights_are_rejected() {
    let eos = IdealGas::new(1.4).unwrap();
    let (l, r) = states();
    let n = [1., 0., 0.];
    let w = [0.; 3];
    for completion in [FaceCompletion::Intermediate, FaceCompletion::SignalWeighted] {
        for (omega, solver) in [(0., RiemannSolver::Hll), (1., RiemannSolver::Hlld)] {
            exact(
                riemann_with_pressure_blend(eos, l, r, n, w, completion, omega).unwrap(),
                riemann_with_solver(eos, l, r, n, w, completion, solver).unwrap(),
            );
        }
        for omega in [-0.1, 1.1, f64::NAN, f64::INFINITY] {
            assert!(riemann_with_pressure_blend(eos, l, r, n, w, completion, omega).is_err());
        }
        assert!(
            riemann_with_solver(eos, l, r, n, w, completion, RiemannSolver::HlldPressure).is_err()
        );
    }
}

#[test]
fn all_conservative_and_induction_components_share_one_convex_weight() {
    let eos = IdealGas::new(1.4).unwrap();
    let (l, r) = states();
    let n = [1., 0., 0.];
    let w = [0.2, -0.3, 0.1];
    for completion in [FaceCompletion::Intermediate, FaceCompletion::SignalWeighted] {
        let a = riemann_with_solver(eos, l, r, n, w, completion, RiemannSolver::Hlld).unwrap();
        let b = riemann_with_solver(eos, l, r, n, w, completion, RiemannSolver::Hll).unwrap();
        for omega in [0.125, 0.5, 0.875] {
            let c = riemann_with_pressure_blend(eos, l, r, n, w, completion, omega).unwrap();
            assert_eq!(c.method, FluxMethod::HlldPressure);
            assert_eq!(c.shock_factor, omega);
            for k in 0..5 {
                close(c.fluid[k], omega * a.fluid[k] + (1. - omega) * b.fluid[k]);
            }
            for k in 0..3 {
                close(
                    c.induction[k],
                    omega * a.induction[k] + (1. - omega) * b.induction[k],
                );
            }
            if completion == FaceCompletion::SignalWeighted {
                assert_eq!(c.velocity, a.velocity);
                assert_eq!(c.magnetic, a.magnetic);
                for k in 0..3 {
                    close(
                        c.electromotive[k],
                        omega * a.electromotive[k] + (1. - omega) * b.electromotive[k],
                    );
                }
            }
        }
    }
}

#[test]
fn blended_flux_is_covariant_under_owner_reversal_rotation_and_joint_boost() {
    let eos = IdealGas::new(1.4).unwrap();
    let (l, r) = states();
    let n = [1., 0., 0.];
    let w = [0.2, -0.3, 0.1];
    for completion in [FaceCompletion::Intermediate, FaceCompletion::SignalWeighted] {
        let solve =
            |l, r, n, w| riemann_with_pressure_blend(eos, l, r, n, w, completion, 0.4).unwrap();
        let f = solve(l, r, n, w);
        let reverse = solve(r, l, n.map(|x| -x), w);
        for k in 0..5 {
            close(reverse.fluid[k], -f.fluid[k]);
        }
        for k in 0..3 {
            close(reverse.induction[k], -f.induction[k]);
            close(reverse.electromotive[k], f.electromotive[k]);
        }
        let rotate = |v: [f64; 3]| [-v[1], v[0], v[2]];
        let rq = |q: Primitive| Primitive {
            velocity: rotate(q.velocity),
            magnetic: rotate(q.magnetic),
            ..q
        };
        let rf = solve(rq(l), rq(r), rotate(n), rotate(w));
        close(rf.fluid[0], f.fluid[0]);
        close(rf.fluid[4], f.fluid[4]);
        let momentum = rotate([f.fluid[1], f.fluid[2], f.fluid[3]]);
        for (k, value) in momentum.iter().enumerate() {
            close(rf.fluid[k + 1], *value);
            close(rf.induction[k], rotate(f.induction)[k]);
            close(rf.electromotive[k], rotate(f.electromotive)[k]);
        }
        let boost = [2., -1., 0.5];
        let bq = |q: Primitive| Primitive {
            velocity: std::array::from_fn(|k| q.velocity[k] + boost[k]),
            ..q
        };
        let bf = solve(bq(l), bq(r), n, std::array::from_fn(|k| w[k] + boost[k]));
        close(bf.fluid[0], f.fluid[0]);
        for k in 0..3 {
            close(bf.fluid[k + 1], f.fluid[k + 1] + boost[k] * f.fluid[0]);
            close(
                bf.induction[k],
                f.induction[k] - dot(l.magnetic, n) * boost[k],
            );
            close(
                bf.electromotive[k],
                f.electromotive[k] + cross(boost, f.magnetic)[k],
            );
        }
        close(
            bf.fluid[4],
            f.fluid[4]
                + dot(boost, [f.fluid[1], f.fluid[2], f.fluid[3]])
                + 0.5 * dot(boost, boost) * f.fluid[0],
        );
    }
}

#[test]
fn blend_preserves_uniform_physical_flux_and_unmodified_contact_at_unit_weight() {
    let eos = IdealGas::new(1.4).unwrap();
    let (l, _) = states();
    for omega in [0., 0.3, 1.] {
        let f = riemann_with_pressure_blend(
            eos,
            l,
            l,
            [1., 0., 0.],
            [0.; 3],
            FaceCompletion::SignalWeighted,
            omega,
        )
        .unwrap();
        let u = eos.conservative(l).unwrap();
        let pt = l.pressure + 0.5 * dot(l.magnetic, l.magnetic);
        close(f.fluid[0], u[1]);
        for k in 0..3 {
            close(
                f.fluid[k + 1],
                u[k + 1] * l.velocity[0] - l.magnetic[0] * l.magnetic[k]
                    + if k == 0 { pt } else { 0. },
            );
        }
        close(
            f.fluid[4],
            (u[4] + pt) * l.velocity[0] - l.magnetic[0] * dot(l.velocity, l.magnetic),
        );
    }
    let l = Primitive {
        velocity: [0.; 3],
        ..l
    };
    let r = Primitive { density: 0.25, ..l };
    let f = riemann_with_pressure_blend(
        eos,
        l,
        r,
        [1., 0., 0.],
        [0.; 3],
        FaceCompletion::SignalWeighted,
        1.,
    )
    .unwrap();
    assert_eq!(f.method, FluxMethod::Hlld);
    close(f.fluid[0], 0.);
    close(f.fluid[4], 0.);
}
