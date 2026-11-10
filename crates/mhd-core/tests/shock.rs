use mhd_core::{
    FaceCompletion, FluxMethod, IdealGas, Primitive, RiemannSolver, ShockSensor, Vec3, cross, dot,
    riemann_with_shock_sensor, riemann_with_solver,
};
fn close(a: f64, b: f64) {
    assert!(
        (a - b).abs() < 2e-11 * (1. + a.abs() + b.abs()),
        "{a} != {b}"
    );
}
fn q() -> Primitive {
    Primitive {
        density: 1.,
        pressure: 1.,
        velocity: [0.; 3],
        magnetic: [0.; 3],
    }
}

#[test]
fn inactive_sensor_is_bit_identical_and_missing_sensor_is_rejected() {
    let eos = IdealGas::new(1.4).unwrap();
    let l = q();
    let r = Primitive {
        pressure: 0.5,
        ..q()
    };
    for completion in [FaceCompletion::Intermediate, FaceCompletion::SignalWeighted] {
        let old = riemann_with_solver(
            eos,
            l,
            r,
            [1., 0., 0.],
            [0.; 3],
            completion,
            RiemannSolver::Hlld,
        )
        .unwrap();
        let new = riemann_with_shock_sensor(
            eos,
            l,
            r,
            [1., 0., 0.],
            [0.; 3],
            completion,
            ShockSensor::default(),
        )
        .unwrap();
        assert_eq!(old.fluid, new.fluid);
        assert_eq!(old.induction, new.induction);
        assert_eq!(old.electromotive, new.electromotive);
        assert_eq!(old.velocity, new.velocity);
        assert_eq!(old.magnetic, new.magnetic);
        assert_eq!(old.method, new.method);
    }
    assert!(
        riemann_with_solver(
            eos,
            l,
            r,
            [1., 0., 0.],
            [0.; 3],
            FaceCompletion::Intermediate,
            RiemannSolver::HlldShock
        )
        .is_err()
    );
}

#[test]
fn active_pressure_correction_retains_symmetric_pressure_in_energy_flux() {
    let eos = IdealGas::new(1.4).unwrap();
    let l = q();
    let r = Primitive {
        pressure: 0.5,
        ..q()
    };
    let cf = 1.4_f64.sqrt();
    let f = riemann_with_shock_sensor(
        eos,
        l,
        r,
        [1., 0., 0.],
        [0.; 3],
        FaceCompletion::Intermediate,
        ShockSensor {
            normal_difference: 0.,
            transverse_difference: -cf,
        },
    )
    .unwrap();
    assert_eq!(f.method, FluxMethod::HlldShock);
    close(f.shock_factor, 1. / 16.);
    let middle = 0.5 / (32. * cf);
    close(f.fluid[0], cf * middle / (cf + middle));
    // In this equal-density, initially stationary hydro fixture, the star
    // pressure is the arithmetic mean 3/4. The energy/mass flux ratio recovers
    // it independently; deriving Pstar from the modified left jump fails this.
    close(
        f.fluid[4] / f.fluid[0] - eos.conservative(l).unwrap()[4],
        0.75,
    );
}

#[test]
fn active_sensor_preserves_uniform_state_and_stationary_contact() {
    let eos = IdealGas::new(1.4).unwrap();
    let sensor = ShockSensor {
        normal_difference: 0.,
        transverse_difference: -1.,
    };
    for rho in [1., 0.25] {
        let l = Primitive {
            magnetic: [0.4, 0.2, 0.1],
            ..q()
        };
        let r = Primitive { density: rho, ..l };
        let f = riemann_with_shock_sensor(
            eos,
            l,
            r,
            [1., 0., 0.],
            [0.; 3],
            FaceCompletion::Intermediate,
            sensor,
        )
        .unwrap();
        assert_eq!(f.method, FluxMethod::HlldShock);
        close(f.fluid[0], 0.);
        close(f.fluid[4], 0.);
        close(f.fluid[1], 1. + 0.5 * dot(l.magnetic, l.magnetic) - 0.16);
        close(f.fluid[2], -0.08);
        close(f.fluid[3], -0.04);
        for x in f.induction {
            close(x, 0.);
        }
    }
}

#[test]
fn active_sensor_flux_has_normal_rotation_and_joint_boost_covariance() {
    let eos = IdealGas::new(1.4).unwrap();
    let l = Primitive {
        velocity: [0.1, -0.1, 0.2],
        magnetic: [0.4, 0.2, 0.1],
        ..q()
    };
    let r = Primitive {
        density: 0.8,
        pressure: 0.8,
        velocity: [-0.1, 0.1, 0.],
        magnetic: [0.4, -0.1, 0.1],
    };
    let sensor = ShockSensor {
        normal_difference: -0.05,
        transverse_difference: -0.5,
    };
    let solve = |l, r, n, w| {
        riemann_with_shock_sensor(eos, l, r, n, w, FaceCompletion::SignalWeighted, sensor).unwrap()
    };
    let n = [0.6, 0.8, 0.];
    let w = [0.02, -0.03, 0.1];
    let f = solve(l, r, n, w);
    assert_eq!(f.method, FluxMethod::HlldShock);
    let rev = solve(r, l, n.map(|v| -v), w);
    for k in 0..5 {
        close(f.fluid[k], -rev.fluid[k]);
    }
    for k in 0..3 {
        close(f.induction[k], -rev.induction[k]);
        close(f.electromotive[k], rev.electromotive[k]);
    }
    let rotate = |v: Vec3| [-v[1], v[0], v[2]];
    let rotq = |q: Primitive| Primitive {
        velocity: rotate(q.velocity),
        magnetic: rotate(q.magnetic),
        ..q
    };
    let fr = solve(rotq(l), rotq(r), rotate(n), rotate(w));
    close(f.fluid[0], fr.fluid[0]);
    close(f.fluid[4], fr.fluid[4]);
    let rm = rotate([f.fluid[1], f.fluid[2], f.fluid[3]]);
    for (k, momentum) in rm.iter().enumerate() {
        close(fr.fluid[k + 1], *momentum);
        close(fr.induction[k], rotate(f.induction)[k]);
        close(fr.electromotive[k], rotate(f.electromotive)[k]);
    }
    let boost = [2., -1., 0.7];
    let bq = |q: Primitive| Primitive {
        velocity: std::array::from_fn(|k| q.velocity[k] + boost[k]),
        ..q
    };
    let fb = solve(bq(l), bq(r), n, std::array::from_fn(|k| w[k] + boost[k]));
    close(fb.fluid[0], f.fluid[0]);
    for (k, velocity) in boost.iter().enumerate() {
        close(fb.fluid[k + 1], f.fluid[k + 1] + velocity * f.fluid[0]);
    }
    close(
        fb.fluid[4],
        f.fluid[4]
            + dot(boost, [f.fluid[1], f.fluid[2], f.fluid[3]])
            + 0.5 * dot(boost, boost) * f.fluid[0],
    );
    let bn = 0.5 * (dot(l.magnetic, n) + dot(r.magnetic, n));
    let be = cross(boost, f.magnetic);
    for (k, velocity) in boost.iter().enumerate() {
        close(fb.induction[k], f.induction[k] - bn * velocity);
        close(fb.electromotive[k], f.electromotive[k] + be[k]);
    }
}
