use mhd_core::{
    FaceCompletion, FaceFlux, IdealGas, Primitive, Vec3, cross, dot, riemann,
    riemann_with_completion,
};

fn close(a: f64, b: f64) {
    assert!(
        (a - b).abs() <= 1e-11 * (1. + a.abs() + b.abs()),
        "{a:e} != {b:e}"
    );
}
fn source(f: FaceFlux, u: Vec3) -> Vec3 {
    let ub = cross(u, f.magnetic);
    std::array::from_fn(|k| f.electromotive[k] - ub[k])
}
fn solve(eos: IdealGas, l: Primitive, r: Primitive, n: Vec3, w: Vec3) -> FaceFlux {
    riemann_with_completion(eos, l, r, n, w, FaceCompletion::SymmetricHll).unwrap()
}

#[test]
fn continuous_completion_preserves_fluxes_reversal_and_joint_boost() {
    let eos = IdealGas::new(5. / 3.).unwrap();
    let w = [0.2, -0.1, 0.3];
    let u = [0.21, -0.1, 0.04];
    let boost = [2., -1., 0.7];
    for n in [[1_f64, 0., 0.], [0., -1., 0.], [0., 0., 1.], [0.6, 0.8, 0.]] {
        let t = if n[2].abs() < 0.9 {
            cross([0., 0., 1.], n)
        } else {
            cross([0., 1., 0.], n)
        };
        let norm = dot(t, t).sqrt();
        let t = t.map(|v| v / norm);
        let z = cross(n, t);
        let from_local = |v: Vec3| std::array::from_fn(|k| v[0] * n[k] + v[1] * t[k] + v[2] * z[k]);
        for bn in [-1., -1e-6, -1e-12, -1e-18, 0., 1e-18, 1e-12, 1e-6, 1.] {
            for speed in [
                -1.,
                0.,
                1.,
                f64::from_bits(1_f64.to_bits() - 1),
                f64::from_bits(1_f64.to_bits() + 1),
            ] {
                for density in [1., 0.2, 3.] {
                    for field_jump in [0., 0.03] {
                        let make = |right: bool| {
                            let vr =
                                from_local([speed, if right { -0.0017 } else { 0.0017 }, 0.04]);
                            Primitive {
                                density: if right { density } else { 1. },
                                pressure: 0.7,
                                velocity: std::array::from_fn(|k| vr[k] + w[k]),
                                magnetic: from_local([
                                    bn,
                                    if right { field_jump } else { 0. },
                                    -0.0046,
                                ]),
                            }
                        };
                        let l = make(false);
                        let r = make(true);
                        let old = riemann(eos, l, r, n, w).unwrap();
                        let f = solve(eos, l, r, n, w);
                        assert_eq!(f.fluid, old.fluid);
                        assert_eq!(f.induction, old.induction);
                        assert_eq!(f.method, old.method);
                        assert_eq!(f.max_speed, old.max_speed);
                        let reverse = solve(eos, r, l, n.map(|x| -x), w);
                        let shifted = |mut q: Primitive| {
                            q.velocity = std::array::from_fn(|k| q.velocity[k] + boost[k]);
                            q
                        };
                        let fb = solve(
                            eos,
                            shifted(l),
                            shifted(r),
                            n,
                            std::array::from_fn(|k| w[k] + boost[k]),
                        );
                        let base_source = source(f, u);
                        let reverse_source = source(reverse, u);
                        let boost_source = source(fb, std::array::from_fn(|k| u[k] + boost[k]));
                        for k in 0..3 {
                            close(base_source[k], reverse_source[k]);
                            close(base_source[k], boost_source[k]);
                            close(f.magnetic[k], fb.magnetic[k]);
                            close(f.fluid[k + 1] + boost[k] * f.fluid[0], fb.fluid[k + 1]);
                        }
                        close(
                            f.fluid[4]
                                + dot(boost, [f.fluid[1], f.fluid[2], f.fluid[3]])
                                + 0.5 * dot(boost, boost) * f.fluid[0],
                            fb.fluid[4],
                        );
                    }
                }
            }
        }
    }
}

#[test]
fn zero_normal_field_source_has_a_continuous_limit_and_uniform_states_are_exact() {
    let eos = IdealGas::new(5. / 3.).unwrap();
    let n = [0., -1., 0.];
    let w = [0.2, -0.1, 0.];
    let u = [0.21, -0.1, 0.04];
    let fixture = |by| {
        let l = Primitive {
            density: 1.,
            pressure: 1.,
            velocity: [0.20168128073437985, -0.1, 0.04],
            magnetic: [0., by, -0.004562414995177748],
        };
        let r = Primitive {
            velocity: [0.19831871926562014, -0.1, 0.04],
            ..l
        };
        source(solve(eos, l, r, n, w), u)
    };
    let zero = fixture(0.);
    for by in [-1e-18, 1e-18] {
        for (a, b) in fixture(by).iter().zip(zero) {
            close(*a, b);
        }
    }
    close(zero[1], -4.562414995177759e-5);
    for velocity in [[0.; 3], [10., -4., 1.], [-10., 4., -1.]] {
        let q = Primitive {
            density: 1.,
            pressure: 0.7,
            velocity,
            magnetic: [0.3, 0.2, 0.1],
        };
        let f = solve(eos, q, q, n, w);
        for k in 0..3 {
            close(f.magnetic[k], q.magnetic[k]);
            close(f.velocity[k], q.velocity[k]);
            close(f.electromotive[k], cross(velocity, q.magnetic)[k]);
        }
    }
}

#[test]
fn nonuniform_hll_fallback_preserves_fluxes_and_covariance() {
    use mhd_core::FluxMethod;
    let eos = IdealGas::new(1.4).unwrap();
    let n = [1., 0., 0.];
    let w = [0.2, -0.1, 0.3];
    let u = [0.21, -0.1, 0.04];
    let boost = [2., -1., 0.7];
    let mut seed = 934578_u64;
    let mut count = 0;
    let mut random = || {
        seed = seed
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        (seed >> 11) as f64 / ((1_u64 << 53) as f64)
    };
    for i in 0..200 {
        let bn = if i % 2 == 0 { 1. } else { 0. };
        let mut make = || Primitive {
            density: 10_f64.powf(-2. + 4. * random()),
            pressure: 10_f64.powf(-8. + 10. * random()),
            velocity: [
                10. * (random() - 0.5),
                2. * (random() - 0.5),
                2. * (random() - 0.5),
            ],
            magnetic: [
                bn,
                if i % 3 == 0 {
                    0.
                } else {
                    2. * (random() - 0.5)
                },
                if i % 3 == 0 {
                    0.
                } else {
                    2. * (random() - 0.5)
                },
            ],
        };
        let l = make();
        let r = make();
        let old = riemann(eos, l, r, n, w).unwrap();
        let f = solve(eos, l, r, n, w);
        assert_eq!(f.fluid, old.fluid);
        assert_eq!(f.induction, old.induction);
        if f.method != FluxMethod::HllFallback {
            continue;
        }
        count += 1;
        let rev = solve(eos, r, l, n.map(|x| -x), w);
        let shift = |q: Primitive| Primitive {
            velocity: std::array::from_fn(|k| q.velocity[k] + boost[k]),
            ..q
        };
        let fb = solve(
            eos,
            shift(l),
            shift(r),
            n,
            std::array::from_fn(|k| w[k] + boost[k]),
        );
        for ((a, b), c) in source(f, u)
            .iter()
            .zip(source(rev, u))
            .zip(source(fb, std::array::from_fn(|k| u[k] + boost[k])))
        {
            close(*a, b);
            close(*a, c);
        }
    }
    assert!(count >= 20, "only {count} fallback faces exercised");
}

#[test]
fn finite_normal_field_stationary_rotational_waves_are_continuous() {
    let eos = IdealGas::new(5. / 3.).unwrap();
    for speed in [-1., 1.] {
        let run = |delta: f64| {
            let l = Primitive {
                density: 1.,
                pressure: 0.7,
                velocity: [speed + delta, 0.2 * speed, 0.],
                magnetic: [1., 0.2, 0.],
            };
            let r = Primitive {
                velocity: [speed + delta, 0., 0.2 * speed],
                magnetic: [1., 0., 0.2],
                ..l
            };
            solve(eos, l, r, [1., 0., 0.], [0.; 3])
        };
        let centre = run(0.);
        for delta in [-1e-12, 1e-12] {
            let f = run(delta);
            for (a, b) in source(f, [0.3, -0.2, 0.1])
                .iter()
                .zip(source(centre, [0.3, -0.2, 0.1]))
            {
                close(*a, b);
            }
            for (a, b) in f.magnetic.iter().zip(centre.magnetic) {
                close(*a, b);
            }
            for (a, b) in f.induction.iter().zip(centre.induction) {
                close(*a, b);
            }
        }
    }
}

#[test]
fn completion_rotates_with_all_physical_vectors() {
    let axis = [
        1_f64 / 14_f64.sqrt(),
        2. / 14_f64.sqrt(),
        3. / 14_f64.sqrt(),
    ];
    let angle = 0.73_f64;
    let rotate = |v: Vec3| {
        let av = cross(axis, v);
        std::array::from_fn(|k| {
            angle.cos() * v[k] + angle.sin() * av[k] + (1. - angle.cos()) * dot(axis, v) * axis[k]
        })
    };
    let eos = IdealGas::new(5. / 3.).unwrap();
    let l = Primitive {
        density: 0.7,
        pressure: 1.1,
        velocity: [0.3, -0.4, 0.7],
        magnetic: [0.8, 0.2, -0.6],
    };
    let r = Primitive {
        density: 1.2,
        pressure: 0.3,
        velocity: [-0.2, 0.1, 0.6],
        magnetic: [0.8, -0.7, 0.4],
    };
    let n = [1., 0., 0.];
    let w = [0.13, 0.2, -0.1];
    let u = [0.4, 0.1, 0.3];
    let rotq = |q: Primitive| Primitive {
        velocity: rotate(q.velocity),
        magnetic: rotate(q.magnetic),
        ..q
    };
    let f = solve(eos, l, r, n, w);
    let g = solve(eos, rotq(l), rotq(r), rotate(n), rotate(w));
    for (a, b) in rotate(f.magnetic).iter().zip(g.magnetic) {
        close(*a, b);
    }
    for (a, b) in rotate(f.induction).iter().zip(g.induction) {
        close(*a, b);
    }
    for (a, b) in rotate(source(f, u)).iter().zip(source(g, rotate(u))) {
        close(*a, b);
    }
    for (a, b) in rotate([f.fluid[1], f.fluid[2], f.fluid[3]])
        .iter()
        .zip(&g.fluid[1..4])
    {
        close(*a, *b);
    }
    close(f.fluid[0], g.fluid[0]);
    close(f.fluid[4], g.fluid[4]);
}
