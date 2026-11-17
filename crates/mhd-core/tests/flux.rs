use mhd_core::{
    FaceCompletion, FaceFlux, FluxMethod, IdealGas, Primitive, RiemannSolver, Vec3, cross, dot,
    riemann, riemann_with_solver,
};

fn q() -> Primitive {
    Primitive {
        density: 1.3,
        pressure: 0.7,
        velocity: [0.6, -0.3, 0.2],
        magnetic: [0.8, 0.4, -0.2],
    }
}
fn close(a: f64, b: f64) {
    assert!(
        (a - b).abs() < 1e-11 * (1.0 + a.abs() + b.abs()),
        "{a} != {b}"
    );
}

fn check_analytic_flux(eos: IdealGas, q: Primitive, n: Vec3, w: Vec3, f: FaceFlux) {
    let u = eos.conservative(q).unwrap();
    let vn = dot(q.velocity, n);
    let bn = dot(q.magnetic, n);
    let wn = dot(w, n);
    let pt = q.pressure + 0.5 * dot(q.magnetic, q.magnetic);
    close(f.fluid[0], q.density * (vn - wn));
    for k in 0..3 {
        close(
            f.fluid[k + 1],
            u[k + 1] * (vn - wn) + pt * n[k] - bn * q.magnetic[k],
        );
    }
    close(
        f.fluid[4],
        (u[4] + pt) * vn - bn * dot(q.velocity, q.magnetic) - wn * u[4],
    );
    let emf = cross(q.velocity, q.magnetic);
    for (k, e) in emf.iter().enumerate() {
        close(f.electromotive[k], *e);
        close(
            f.induction[k],
            (vn - wn) * q.magnetic[k] - bn * q.velocity[k],
        );
    }
}

#[test]
fn eos_roundtrip_and_invalid_states() {
    let eos = IdealGas::new(5.0 / 3.0).unwrap();
    let prim = q();
    let u = eos.conservative(prim).unwrap();
    let back = eos.recover(u, prim.magnetic).unwrap();
    close(back.pressure, prim.pressure);
    for k in 0..3 {
        close(back.velocity[k], prim.velocity[k]);
    }
    assert!(IdealGas::new(1.0).is_err());
    assert!(IdealGas::new(f64::NAN).is_err());
    let mut bad = u;
    bad[4] = 0.0;
    assert!(eos.recover(bad, prim.magnetic).is_err());
    bad[0] = -1.0;
    assert!(eos.recover(bad, prim.magnetic).is_err());
    let mut bad = prim;
    bad.pressure = f64::NAN;
    assert!(eos.conservative(bad).is_err());
}

#[test]
fn uniform_ale_equals_analytic_and_emf() {
    let eos = IdealGas::new(5.0 / 3.0).unwrap();
    let q = q();
    let n = [0.6, 0.8, 0.0];
    let w = [0.3, -0.1, 0.7];
    for solver in [RiemannSolver::Hlld, RiemannSolver::Hll] {
        let f = riemann_with_solver(eos, q, q, n, w, FaceCompletion::Intermediate, solver).unwrap();
        check_analytic_flux(eos, q, n, w, f);
    }
}

#[test]
fn orientation_and_joint_boost() {
    for solver in [RiemannSolver::Hlld, RiemannSolver::Hll] {
        let riemann = |eos, left, right, normal, velocity| {
            riemann_with_solver(
                eos,
                left,
                right,
                normal,
                velocity,
                FaceCompletion::Intermediate,
                solver,
            )
        };

        let eos = IdealGas::new(1.4).unwrap();
        let l = q();
        let mut r = q();
        r.pressure = 0.1;
        r.density = 0.4;
        r.velocity = [-0.2, 0.5, -0.4];
        r.magnetic[1] = -0.2;
        let n = [0.6, 0.8, 0.0];
        let w = [0.1, -0.2, 0.0];
        let f = riemann(eos, l, r, n, w).unwrap();
        let reverse = riemann(eos, r, l, n.map(|x| -x), w).unwrap();
        for k in 0..5 {
            close(f.fluid[k], -reverse.fluid[k]);
        }
        for k in 0..3 {
            close(f.electromotive[k], reverse.electromotive[k]);
            close(f.induction[k], -reverse.induction[k]);
            close(f.magnetic[k], reverse.magnetic[k]);
            close(f.velocity[k], reverse.velocity[k]);
        }
        let boost = [2.0, -1.0, 0.7];
        let boosted = |mut q: Primitive| {
            for (k, b) in boost.iter().enumerate() {
                q.velocity[k] += b;
            }
            q
        };
        let fb = riemann(
            eos,
            boosted(l),
            boosted(r),
            n,
            std::array::from_fn(|k| w[k] + boost[k]),
        )
        .unwrap();
        close(fb.fluid[0], f.fluid[0]);
        for (k, b) in boost.iter().enumerate() {
            close(fb.fluid[k + 1], f.fluid[k + 1] + b * f.fluid[0]);
        }
        close(
            fb.fluid[4],
            f.fluid[4]
                + dot(boost, [f.fluid[1], f.fluid[2], f.fluid[3]])
                + 0.5 * dot(boost, boost) * f.fluid[0],
        );
        let bn = 0.5 * (dot(l.magnetic, n) + dot(r.magnetic, n));
        let boost_emf = cross(boost, f.magnetic);
        for k in 0..3 {
            close(fb.induction[k], f.induction[k] - bn * boost[k]);
            close(fb.electromotive[k], f.electromotive[k] + boost_emf[k]);
            close(fb.velocity[k], f.velocity[k] + boost[k]);
            close(fb.magnetic[k], f.magnetic[k]);
        }
        close(fb.max_speed, f.max_speed);
    }
}

#[test]
fn stationary_contact_is_resolved() {
    let eos = IdealGas::new(1.4).unwrap();
    let mut l = q();
    l.velocity = [0.0; 3];
    let mut r = l;
    r.density = 0.2;
    let f = riemann(eos, l, r, [1.0, 0.0, 0.0], [0.0; 3]).unwrap();
    close(f.fluid[0], 0.0);
    close(f.fluid[4], 0.0);
    close(
        f.fluid[1],
        l.pressure + 0.5 * dot(l.magnetic, l.magnetic) - l.magnetic[0].powi(2),
    );
    assert_eq!(f.method, FluxMethod::Hlld);
}

#[test]
fn isolated_rotational_discontinuity() {
    // Right-moving Alfven discontinuity at speed +1, rho=1, Bn=1.
    let eos = IdealGas::new(5.0 / 3.0).unwrap();
    let l = Primitive {
        density: 1.0,
        pressure: 1.0,
        velocity: [0.0, 0.0, 0.0],
        magnetic: [1.0, 0.5, 0.0],
    };
    let r = Primitive {
        density: 1.0,
        pressure: 1.0,
        velocity: [0.0, 0.5, -0.5],
        magnetic: [1.0, 0.0, 0.5],
    };
    let f = riemann(eos, l, r, [1.0, 0.0, 0.0], [0.0; 3]).unwrap();
    let expected = riemann(eos, l, l, [1.0, 0.0, 0.0], [0.0; 3]).unwrap();
    for k in 0..5 {
        close(f.fluid[k], expected.fluid[k]);
    }
    for k in 0..3 {
        close(f.induction[k], expected.induction[k]);
    }
    assert_eq!(f.method, FluxMethod::Hlld);
}

#[test]
fn zero_field_and_degenerate_states() {
    let eos = IdealGas::new(1.4).unwrap();
    let mut l = q();
    l.magnetic = [0.0; 3];
    l.velocity = [0.0; 3];
    let mut r = l;
    r.pressure = 0.1;
    r.density = 0.125;
    let f = riemann(eos, l, r, [1.0, 0.0, 0.0], [0.0; 3]).unwrap();
    assert!(f.fluid.iter().all(|x| x.is_finite()));
    assert_eq!(f.method, FluxMethod::Hlld);
    l.magnetic = [1.0, 0.0, 0.0];
    l.pressure = 1e-6;
    r = l;
    let f = riemann(eos, l, r, [1.0, 0.0, 0.0], [0.0; 3]).unwrap();
    assert_eq!(f.method, FluxMethod::HllFallback);
    assert!(riemann(eos, l, r, [2.0, 0.0, 0.0], [0.0; 3]).is_err());
}

#[test]
fn fast_speed_exact_limits_across_scales() {
    let eos = IdealGas::new(2.0).unwrap();
    for pressure in [1e-200_f64, 1.0, 1e200] {
        let sound = 2.0_f64.sqrt() * pressure.sqrt();
        for (magnetic, expected) in [
            ([0.0; 3], sound),
            ([2.0 * sound, 0.0, 0.0], 2.0 * sound),
            ([0.5 * sound, 0.0, 0.0], sound),
            ([0.0, 2.0 * sound, 0.0], 5.0_f64.sqrt() * sound),
        ] {
            let prim = Primitive {
                density: 1.0,
                pressure,
                velocity: [0.0; 3],
                magnetic,
            };
            let measured = eos.fast_speed(prim, [1.0, 0.0, 0.0]);
            assert!(
                (measured / expected - 1.0).abs() <= 1e-12,
                "p={pressure}, B={magnetic:?}: {measured} != {expected}"
            );
        }
    }
}

#[test]
fn common_normal_field_preserves_face_pressure_but_cell_energy_is_fixed() {
    let eos = IdealGas::new(1.4).unwrap();
    let mut l = q();
    l.magnetic[0] = 1.0;
    let mut r = l;
    r.magnetic[0] = 3.0;
    let mut common = l;
    common.magnetic[0] = 2.0;
    let n = [1.0, 0.0, 0.0];
    let w = [0.2, -0.1, 0.3];
    check_analytic_flux(eos, common, n, w, riemann(eos, l, r, n, w).unwrap());

    let u = eos.conservative(l).unwrap();
    let recovered = eos.recover(u, common.magnetic).unwrap();
    close(recovered.pressure, l.pressure - (eos.gamma() - 1.0) * 1.5);
    // The same cell E cannot support the larger magnetic energy; no reset/floor.
    assert!(eos.recover(u, r.magnetic).is_err());
    assert_eq!(u, eos.conservative(l).unwrap());
}

#[test]
fn both_supersonic_branches_use_analytic_donor_flux() {
    let eos = IdealGas::new(1.4).unwrap();
    let n = [1.0, 0.0, 0.0];
    let w = [0.3, -0.2, 0.1];
    for sign in [-1.0, 1.0] {
        let mut l = q();
        l.velocity[0] = sign * 8.0;
        let mut r = l;
        r.density = 0.5;
        r.pressure = 0.2;
        r.velocity[0] = sign * 7.0;
        r.magnetic[1] = -0.3;
        let f = riemann(eos, l, r, n, w).unwrap();
        assert_eq!(f.method, FluxMethod::Upwind);
        check_analytic_flux(eos, if sign > 0.0 { l } else { r }, n, w, f);
    }
}

#[test]
fn rotations_and_magnetic_reversal_preserve_flux_symmetry() {
    let eos = IdealGas::new(1.4).unwrap();
    let l = q();
    let mut r = q();
    r.density = 0.4;
    r.pressure = 0.1;
    r.velocity = [-0.2, 0.5, -0.4];
    r.magnetic = [-0.2, 0.5, 0.7];
    let w = [0.1, -0.2, 0.0];
    let rotate = |v: Vec3| [v[2], v[0], v[1]]; // Proper cyclic rotation.
    let rotate_q = |mut q: Primitive| {
        q.velocity = rotate(q.velocity);
        q.magnetic = rotate(q.magnetic);
        q
    };
    let negate_b = |mut q: Primitive| {
        q.magnetic = q.magnetic.map(|v| -v);
        q
    };
    // Exercise both choices of tangent basis, including a nearly z-normal face.
    for n in [[0.6, 0.8, 0.0], [0.0, 0.0, 1.0]] {
        let f = riemann(eos, l, r, n, w).unwrap();
        let rotated = riemann(eos, rotate_q(l), rotate_q(r), rotate(n), rotate(w)).unwrap();
        close(rotated.fluid[0], f.fluid[0]);
        close(rotated.fluid[4], f.fluid[4]);
        let momentum = rotate([f.fluid[1], f.fluid[2], f.fluid[3]]);
        for (k, m) in momentum.iter().enumerate() {
            close(rotated.fluid[k + 1], *m);
            close(rotated.induction[k], rotate(f.induction)[k]);
            close(rotated.electromotive[k], rotate(f.electromotive)[k]);
        }
        let reversed = riemann(eos, negate_b(l), negate_b(r), n, w).unwrap();
        for k in 0..5 {
            close(reversed.fluid[k], f.fluid[k]);
        }
        for k in 0..3 {
            close(reversed.induction[k], -f.induction[k]);
            close(reversed.electromotive[k], -f.electromotive[k]);
        }
    }
}

#[test]
fn invalid_face_and_overflow_inputs_return_errors() {
    let eos = IdealGas::new(1.4).unwrap();
    let n = [1.0, 0.0, 0.0];
    for value in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        for component in 0..8 {
            let mut bad = q();
            match component {
                0 => bad.density = value,
                1 => bad.pressure = value,
                2..=4 => bad.velocity[component - 2] = value,
                _ => bad.magnetic[component - 5] = value,
            }
            assert!(eos.conservative(bad).is_err());
            assert!(riemann(eos, bad, q(), n, [0.0; 3]).is_err());
            assert!(riemann(eos, q(), bad, n, [0.0; 3]).is_err());
        }
        assert!(riemann(eos, q(), q(), [value, 0.0, 0.0], [0.0; 3]).is_err());
        assert!(riemann(eos, q(), q(), n, [value, 0.0, 0.0]).is_err());
        let mut u = eos.conservative(q()).unwrap();
        u[4] = value;
        assert!(eos.recover(u, q().magnetic).is_err());
    }
    for value in [0.0, -1.0] {
        let mut bad = q();
        bad.pressure = value;
        assert!(riemann(eos, bad, q(), n, [0.0; 3]).is_err());
        bad = q();
        bad.density = value;
        assert!(eos.conservative(bad).is_err());
    }
    let mut overflow = q();
    overflow.velocity[0] = f64::MAX;
    assert!(eos.conservative(overflow).is_err());
    assert!(riemann(eos, overflow, q(), n, [0.0; 3]).is_err());
    assert!(riemann(eos, q(), q(), [0.0; 3], [0.0; 3]).is_err());
}

#[test]
fn explicit_hll_contact_diffusion_matches_two_wave_formula() {
    let eos = IdealGas::new(1.4).unwrap();
    let l = Primitive {
        density: 1.,
        pressure: 1.,
        velocity: [0.; 3],
        magnetic: [0.; 3],
    };
    let r = Primitive { density: 0.25, ..l };
    let cf = (1.4_f64 / 0.25).sqrt();
    let f = riemann_with_solver(
        eos,
        l,
        r,
        [1., 0., 0.],
        [0.; 3],
        FaceCompletion::Intermediate,
        RiemannSolver::Hll,
    )
    .unwrap();
    assert_eq!(f.method, FluxMethod::Hll);
    close(f.fluid[0], -0.5 * cf * (r.density - l.density));
    for (actual, expected) in f.fluid[1..].iter().zip([1., 0., 0., 0.]) {
        close(*actual, expected);
    }
    assert_eq!(f.induction, [0.; 3]);
    // Explicit HLL and fallback accounting stay distinct. Default resolves this contact.
    assert_eq!(
        riemann(eos, l, r, [1., 0., 0.], [0.; 3]).unwrap().method,
        FluxMethod::Hlld
    );
}
