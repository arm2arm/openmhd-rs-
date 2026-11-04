use mhd_core::{FluxMethod, IdealGas, Primitive, cross, dot, riemann};

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
    let u = eos.conservative(q).unwrap();
    let f = riemann(eos, q, q, n, w).unwrap();
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
fn orientation_and_joint_boost() {
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
