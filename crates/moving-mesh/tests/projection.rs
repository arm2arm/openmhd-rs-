use moving_mesh::projection::{Coefficients, HalfSpace, project};
use moving_mesh::{
    Derivatives, Mesh,
    quadratic::{Compact, Quadratic},
};
use std::f64::consts::{SQRT_2, TAU};
fn dot(a: Coefficients, b: Coefficients) -> f64 {
    a.iter().zip(b).map(|(a, b)| a * b).sum()
}
fn close(a: Coefficients, b: Coefficients, tol: f64) {
    for (a, b) in a.iter().zip(b) {
        assert!((a - b).abs() <= tol, "{a} != {b}");
    }
}
fn face(x: f64, y: f64) -> Coefficients {
    [x, y, x * x, y * y, SQRT_2 * x * y]
}
fn bounds(points: &[[f64; 2]], low: f64, high: f64) -> Vec<HalfSpace> {
    points
        .iter()
        .flat_map(|&[x, y]| {
            let r = face(x, y);
            [
                HalfSpace {
                    normal: r,
                    bound: high,
                },
                HalfSpace {
                    normal: r.map(|v| -v),
                    bound: -low,
                },
            ]
        })
        .collect()
}

#[test]
fn analytical_projection_handles_opposite_duplicate_and_zero_width_constraints() {
    let c = vec![
        HalfSpace {
            normal: [1., 0., 0., 0., 0.],
            bound: 0.,
        },
        HalfSpace {
            normal: [-1., 0., 0., 0., 0.],
            bound: 0.,
        },
        HalfSpace {
            normal: [2., 0., 0., 0., 0.],
            bound: 0.,
        },
        HalfSpace {
            normal: [0., 1., 0., 0., 0.],
            bound: 0.5,
        },
    ];
    for sign in [-1., 1.] {
        let p = project([sign * 2., 3., 4., 5., 6.], &c).unwrap();
        close(p.value, [0., 0.5, 4., 5., 6.], 1e-13);
    }
    let raw = [0., 0.1, 0., 0., 0.];
    assert_eq!(project(raw, &c).unwrap().value, raw);
    let same = bounds(&[[0.5, 0.], [-0.5, 0.], [0., 0.5], [0., -0.5]], 0., 0.);
    close(
        project([1., 2., 3., 4., 5.], &same).unwrap().value,
        [0., 0., 0., 0., 5.],
        1e-12,
    );
}

#[test]
fn transverse_limit_is_continuous_and_preserves_valid_longitudinal_curvature() {
    let c = bounds(&[[0.5, 0.], [-0.5, 0.], [0., 0.5], [0., -0.5]], -1., 0.);
    for e in [0., 1e-5, 1e-10, 1e-15, 1e-100, -1e-10] {
        let raw = [0., 0., -1., e, 0.];
        let p = project(raw, &c).unwrap();
        assert!((p.value[2] + 1.).abs() < 1e-13);
        assert!((p.value[3] - e.min(0.)).abs() < 1e-13);
        for b in &c {
            assert!(dot(b.normal, p.value) <= b.bound + 1e-13);
        }
    }
}

fn rotate(z: Coefficients, angle: f64) -> Coefficients {
    let (s, c) = angle.sin_cos();
    let a = z[2];
    let b = z[3];
    let d = z[4] / SQRT_2;
    [
        c * z[0] - s * z[1],
        s * z[0] + c * z[1],
        c * c * a + s * s * b - 2. * c * s * d,
        s * s * a + c * c * b + 2. * c * s * d,
        SQRT_2 * (c * s * (a - b) + (c * c - s * s) * d),
    ]
}
#[test]
fn invariant_metric_rotates_and_ignores_constraint_permutations() {
    let points = [
        [0.5, 0.1],
        [0.2, 0.6],
        [-0.4, 0.3],
        [-0.6, -0.2],
        [-0.1, -0.4],
        [0.4, -0.3],
    ];
    let raw = [0.3, -0.7, 1.2, -0.9, 0.5];
    let c = bounds(&points, -0.03, 0.04);
    let p = project(raw, &c).unwrap();
    for angle in [0.1, 0.7, 1.3] {
        let (s, co) = f64::sin_cos(angle);
        let r = points.map(|[x, y]| [co * x - s * y, s * x + co * y]);
        let q = project(rotate(raw, angle), &bounds(&r, -0.03, 0.04)).unwrap();
        close(q.value, rotate(p.value, angle), 2e-12);
    }
    let mut reverse = c.clone();
    reverse.reverse();
    close(project(raw, &reverse).unwrap().value, p.value, 2e-12);
    for scale in [1e-12, 1e12] {
        let cc: Vec<_> = c
            .iter()
            .map(|c| HalfSpace {
                normal: c.normal,
                bound: c.bound * scale,
            })
            .collect();
        close(
            project(raw.map(|v| v * scale), &cc)
                .unwrap()
                .value
                .map(|v| v / scale),
            p.value,
            2e-12,
        );
    }
}

#[test]
fn deterministic_polyhedra_satisfy_independent_kkt_residuals() {
    let mut state = 431_u64;
    let mut rand = || {
        state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
        ((state >> 11) as f64) / (1_u64 << 53) as f64
    };
    for case in 0..1000 {
        let raw = std::array::from_fn(|_| 2. * rand() - 1.);
        let mut c = Vec::new();
        for _ in 0..6 {
            let row = std::array::from_fn(|_| 2. * rand() - 1.);
            let b = if case % 4 == 0 { 0. } else { rand() * 0.3 };
            c.push(HalfSpace {
                normal: row,
                bound: b,
            });
            c.push(HalfSpace {
                normal: row.map(|v| -v),
                bound: b,
            });
        }
        let p = project(raw, &c).unwrap_or_else(|e| panic!("case {case}: {e}"));
        let mut residual: Coefficients = std::array::from_fn(|k| p.value[k] - raw[k]);
        for (c, l) in c.iter().zip(&p.multipliers) {
            let slack = c.bound - dot(c.normal, p.value);
            assert!(slack >= -2e-11, "case {case}: {slack}");
            assert!(*l >= 0.);
            assert!((l * slack).abs() < 2e-11);
            for (r, coefficient) in residual.iter_mut().zip(c.normal) {
                *r += l * coefficient;
            }
        }
        close(residual, [0.; 5], 2e-11);
    }
}

#[test]
fn actual_cosine_and_irregular_jets_obey_bounds_and_field_symmetries() {
    for jitter in [0., 0.15] {
        let mesh = Mesh::lattice(16, 16, [1.; 2], jitter).unwrap();
        let d = Derivatives::build(&mesh, false).unwrap();
        let q = Quadratic::build(&mesh).unwrap();
        let c = Compact::build(&mesh, &d).unwrap();
        let values: Vec<_> = mesh
            .cells
            .iter()
            .map(|cell| (TAU * (cell.centroid[0] - mesh.cells[0].centroid[0])).cos())
            .collect();
        let jets = c.jets(&d, &q, &values).unwrap();
        let g: Vec<_> = jets.iter().map(|j| j.gradient).collect();
        let h: Vec<_> = jets.iter().map(|j| j.hessian).collect();
        let guard = mesh.reconstruction().unwrap();
        let limited = guard.project_quadratic(&values, &g, &h).unwrap();
        if jitter == 0. {
            assert!(h[0][1] > 0.1);
            assert!((limited[0].hessian[0] - h[0][0]).abs() < 1e-10);
            assert!(limited[0].hessian[1].abs() < 1e-10);
            assert_eq!(guard.quadratic_factors(&values, &g, &h).unwrap()[0], 0.);
        }
        for (i, j) in limited.iter().enumerate() {
            let mut lo = values[i];
            let mut hi = lo;
            for &(f, _) in &mesh.cells[i].faces {
                let v = values[mesh.neighbour(&mesh.faces[f], i).0];
                lo = lo.min(v);
                hi = hi.max(v);
            }
            for &(f, _) in &mesh.cells[i].faces {
                let r = mesh.displacement(&mesh.faces[f], i);
                let v = values[i]
                    + moving_mesh::dot(j.gradient, r)
                    + moving_mesh::quadratic::term(j.hessian, r);
                assert!(v >= lo - 1e-12 && v <= hi + 1e-12);
            }
        }
        for sign in [-2., 0.5] {
            let v: Vec<_> = values.iter().map(|v| 3. + sign * v).collect();
            let gg: Vec<_> = g.iter().map(|g| g.map(|x| sign * x)).collect();
            let hh: Vec<_> = h.iter().map(|h| h.map(|x| sign * x)).collect();
            let other = guard.project_quadratic(&v, &gg, &hh).unwrap();
            for (a, b) in limited.iter().zip(other) {
                for (x, y) in a
                    .gradient
                    .iter()
                    .chain(&a.hessian)
                    .zip(b.gradient.iter().chain(&b.hessian))
                {
                    assert!((x * sign - y).abs() < 1e-9);
                }
            }
        }
    }
}

#[test]
fn invalid_inputs_are_rejected() {
    assert!(project([f64::NAN; 5], &[]).is_err());
    assert!(
        project(
            [0.; 5],
            &[HalfSpace {
                normal: [0.; 5],
                bound: 1.
            }]
        )
        .is_err()
    );
    assert!(
        project(
            [0.; 5],
            &[HalfSpace {
                normal: [1.; 5],
                bound: -1.
            }]
        )
        .is_err()
    );
}

#[test]
fn feasibility_is_decided_without_underflowing_constraint_products() {
    let plane = HalfSpace {
        normal: [1e-200, 0., 0., 0., 0.],
        bound: 0.,
    };
    let result = project([1e-200, 0., 0., 0., 0.], &[plane]).unwrap();
    assert_eq!(result.value, [0.; 5]);
    assert!((result.multipliers[0] - 1.).abs() < 1e-14);
    let plane = HalfSpace {
        normal: [1e-100, 0., 0., 0., 0.],
        bound: 1e200,
    };
    let result = project([2e300, 0., 0., 0., 0.], &[plane]);
    // The primal answer is representable but its original multiplier is not.
    assert!(result.is_err());
}
