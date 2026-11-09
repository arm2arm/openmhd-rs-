//! Prospective A-face completion invariants, including the archived collapsed fan.
use mhd_core::{
    FaceCompletion, FaceFlux, FluxMethod, IdealGas, Primitive, Vec3, cross, riemann,
    riemann_with_completion,
};

fn solve(l: Primitive, r: Primitive, n: Vec3, w: Vec3) -> FaceFlux {
    riemann_with_completion(
        IdealGas::new(5. / 3.).unwrap(),
        l,
        r,
        n,
        w,
        FaceCompletion::SignalWeighted,
    )
    .unwrap()
}
fn source(f: FaceFlux, u: Vec3) -> Vec3 {
    let ub = cross(u, f.magnetic);
    std::array::from_fn(|k| f.electromotive[k] - ub[k])
}
fn close(a: Vec3, b: Vec3) {
    for k in 0..3 {
        assert!((a[k] - b[k]).abs() <= 1e-11, "{a:?} != {b:?}");
    }
}
fn state(vx: f64, by: f64, vy: f64) -> Primitive {
    Primitive {
        density: 1.,
        pressure: 1.,
        velocity: [vx, vy, 0.04],
        magnetic: [0., by, -0.004562414995177748],
    }
}
fn rotate(v: Vec3) -> Vec3 {
    // A proper non-axis-aligned rotation, with an out-of-plane component.
    let (s, c) = 0.37_f64.sin_cos();
    [v[2], c * v[0] - s * v[1], s * v[0] + c * v[1]]
}
#[test]
fn completion_is_continuous_covariant_and_preserves_conservative_fluxes() {
    let n = [0., -1., 0.];
    let w = [0.2, -0.1, 0.];
    let aux = [0.21, -0.1, 0.04];
    let boost = [2., -1., 0.8];
    let base = source(
        solve(
            state(0.20168128073437985, 0., -0.1),
            state(0.19831871926562015, 0., -0.1),
            n,
            w,
        ),
        aux,
    );
    for bn in [-1e-8, -1e-14, -1e-18, 0., 1e-18, 1e-14, 1e-8, 0.3] {
        for vn in [-1e-8, -1e-16, 0., 1e-16, 1e-8, 0.2] {
            for contrast in [false, true] {
                let l = state(0.20168128073437985, bn, -0.1 + vn);
                let mut r = state(0.19831871926562015, bn, -0.1 + vn);
                if contrast {
                    r.density = 0.3;
                    r.pressure = 0.7;
                    r.magnetic[0] = 0.2;
                }
                let f = solve(l, r, n, w);
                let s = source(f, aux);
                let old = riemann(IdealGas::new(5. / 3.).unwrap(), l, r, n, w).unwrap();
                assert_eq!(f.fluid, old.fluid);
                assert_eq!(f.induction, old.induction);
                assert_eq!(f.method, old.method);
                assert_eq!(f.max_speed, old.max_speed);
                let reversed = solve(r, l, n.map(|v| -v), w);
                close(s, source(reversed, aux));
                close(f.magnetic, reversed.magnetic);
                for k in 0..5 {
                    assert!((f.fluid[k] + reversed.fluid[k]).abs() < 1e-11);
                }
                let boosted = |mut q: Primitive| {
                    q.velocity = std::array::from_fn(|k| q.velocity[k] + boost[k]);
                    q
                };
                close(
                    s,
                    source(
                        solve(
                            boosted(l),
                            boosted(r),
                            n,
                            std::array::from_fn(|k| w[k] + boost[k]),
                        ),
                        std::array::from_fn(|k| aux[k] + boost[k]),
                    ),
                );
                let rotated = |mut q: Primitive| {
                    q.velocity = rotate(q.velocity);
                    q.magnetic = rotate(q.magnetic);
                    q
                };
                close(
                    rotate(s),
                    source(
                        solve(rotated(l), rotated(r), rotate(n), rotate(w)),
                        rotate(aux),
                    ),
                );
                let mut ulp = l;
                ulp.velocity[1] = f64::from_bits(ulp.velocity[1].to_bits() + 1);
                ulp.magnetic[1] = f64::from_bits(ulp.magnetic[1].to_bits() + 1);
                close(s, source(solve(ulp, r, n, w), aux));
                if !contrast && bn.abs() <= 1e-14 && vn.abs() <= 1e-16 {
                    close(s, base);
                }
            }
        }
    }
}

#[test]
fn uniform_upwind_rotational_and_fallback_controls() {
    let n = [1., 0., 0.];
    let w = [0.2, -0.1, 0.3];
    for (v, b, p) in [
        ([0.2, -0.1, 0.3], [1., 0., 0.], 1e-6),
        ([4., 0.2, 0.1], [0.3, 0.2, 0.1], 1.),
        ([-4., 0.2, 0.1], [0.3, 0.2, 0.1], 1.),
        ([0.2, 0.3, -0.1], [0.3, 0.2, 0.1], 1.),
    ] {
        let q = Primitive {
            density: 1.,
            pressure: p,
            velocity: v,
            magnetic: b,
        };
        let f = solve(q, q, n, w);
        close(f.magnetic, b);
        close(f.electromotive, cross(v, b));
        close(source(f, v), [0.; 3]);
        if p == 1e-6 {
            assert_eq!(f.method, FluxMethod::HllFallback);
        }
    }
    // Finite normal field rotational discontinuity: numerical tangential EMF
    // is retained, even though the signal completion is a different state.
    let l = Primitive {
        density: 1.,
        pressure: 0.1,
        velocity: [0., 0.1, 0.],
        magnetic: [1., 0.1, 0.],
    };
    let r = Primitive {
        velocity: [0., 0., 0.1],
        magnetic: [1., 0., 0.1],
        ..l
    };
    let old = riemann(IdealGas::new(5. / 3.).unwrap(), l, r, n, [0.; 3]).unwrap();
    let new = solve(l, r, n, [0.; 3]);
    assert_eq!(new.fluid, old.fluid);
    assert_eq!(new.induction, old.induction);
    for k in 1..3 {
        assert_eq!(new.electromotive[k], old.electromotive[k]);
    }
}

#[test]
fn completion_is_continuous_at_both_outer_wave_boundaries() {
    let eos = IdealGas::new(5. / 3.).unwrap();
    let n = [1., 0., 0.];
    for density in [1., 0.3] {
        let mut l = Primitive {
            density: 1.,
            pressure: 1.,
            velocity: [0., 0.2, 0.1],
            magnetic: [0.5, 0.3, 0.1],
        };
        let mut r = Primitive {
            density,
            pressure: 1.,
            velocity: [0., -0.2, 0.05],
            magnetic: [0.5, -0.4, 0.2],
        };
        let cf = eos.fast_speed(l, n).max(eos.fast_speed(r, n));
        for sign in [-1., 1.] {
            l.velocity[0] = sign * cf;
            r.velocity[0] = sign * cf;
            let aux = [sign * cf, 0., 0.];
            let f = solve(l, r, n, [0.; 3]);
            for delta in [-1e-12, -1e-15, 0., 1e-15, 1e-12] {
                let mut ll = l;
                let mut rr = r;
                ll.velocity[0] += delta;
                rr.velocity[0] += delta;
                let near = solve(ll, rr, n, [0.; 3]);
                close(f.magnetic, near.magnetic);
                close(f.velocity, near.velocity);
                close(source(f, aux), source(near, aux));
                close(
                    source(near, aux),
                    source(solve(rr, ll, n.map(|v| -v), [0.; 3]), aux),
                );
                let boost = [100., -1., 0.8];
                for (k, shift) in boost.iter().enumerate() {
                    ll.velocity[k] += shift;
                    rr.velocity[k] += shift;
                }
                close(
                    source(near, aux),
                    source(
                        solve(ll, rr, n, boost),
                        std::array::from_fn(|k| aux[k] + boost[k]),
                    ),
                );
            }
        }
    }
}

// Actual N64 regular standing-wave face 461 at t=1e-4, after one common-dt
// step (dt=1e-4) of the historical profile, fixed base / rigid boost (2,-1,0).
// Extracted by standing_faces.rs, not a manufactured arbitrary state.
fn standing_face_state(a: [f64; 8], boost: Vec3) -> Primitive {
    Primitive {
        density: a[0],
        velocity: [a[1] + boost[0], a[2] + boost[1], a[3] + boost[2]],
        pressure: a[4],
        magnetic: [a[5], a[6], a[7]],
    }
}
#[test]
fn actual_standing_wave_face_retains_roundoff_boost_covariance() {
    let zero = [0.; 3];
    let boost = [2., -1., 0.];
    let base = [
        [
            1.,
            1.,
            0.06350625752299743,
            0.07740138009023803,
            0.10000000025068476,
            1.,
            0.06340432826110308,
            0.07727706899584699,
        ],
        [
            1.,
            1.,
            0.06352452178566724,
            0.07738639102809391,
            0.10000000025068446,
            1.,
            0.06342256319030858,
            0.07726210399155542,
        ],
    ];
    // Rest-frame values obtained by subtracting boost from the second run.
    let boosted_rest = [
        [
            1.,
            1.,
            0.06350625752299743,
            0.07740138009023803,
            0.10000000025068387,
            1.,
            0.06340432826110308,
            0.07727706899584699,
        ],
        [
            1.,
            1.,
            0.06352452178566725,
            0.07738639102809391,
            0.10000000025068505,
            1.,
            0.06342256319030858,
            0.07726210399155542,
        ],
    ];
    let aux = [0.999999999999999, 0.04536842978175854, 0.066417915451059];
    let aux_boosted = [3., -0.9546315702182406, 0.06641791545105902];
    let eos = IdealGas::new(5. / 3.).unwrap();
    for completion in [FaceCompletion::Intermediate, FaceCompletion::SignalWeighted] {
        let a = riemann_with_completion(
            eos,
            standing_face_state(base[0], zero),
            standing_face_state(base[1], zero),
            [1., 0., 0.],
            zero,
            completion,
        )
        .unwrap();
        let b = riemann_with_completion(
            eos,
            standing_face_state(boosted_rest[0], boost),
            standing_face_state(boosted_rest[1], boost),
            [1., 0., 0.],
            boost,
            completion,
        )
        .unwrap();
        let sa: Vec3 = std::array::from_fn(|k| a.electromotive[k] - cross(aux, a.magnetic)[k]);
        let sb: Vec3 =
            std::array::from_fn(|k| b.electromotive[k] - cross(aux_boosted, b.magnetic)[k]);
        let source = (0..3).map(|k| (sa[k] - sb[k]).abs()).fold(0., f64::max);
        let mut fluid = b.fluid;
        for (k, shift) in boost.iter().enumerate() {
            fluid[k + 1] -= shift * fluid[0];
        }
        fluid[4] =
            b.fluid[4] - (0..3).map(|k| boost[k] * b.fluid[k + 1]).sum::<f64>() + 2.5 * fluid[0];
        let flux = (0..5)
            .map(|k| (a.fluid[k] - fluid[k]).abs())
            .fold(0., f64::max);
        println!(
            "completion={completion:?} source_max={source:.17e} transformed_fluid_max={flux:.17e}"
        );
        assert!(flux < 1e-12);
        match completion {
            FaceCompletion::Intermediate => assert!(source > 1e-6),
            FaceCompletion::SignalWeighted => assert!(source < 1e-12),
        }
    }
}
