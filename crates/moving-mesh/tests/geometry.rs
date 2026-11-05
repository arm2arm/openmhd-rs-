use moving_mesh::{Derivatives, Mesh};
use std::f64::consts::PI;

#[test]
fn periodic_lattices_and_jitter_tile_and_close() {
    for jitter in [0.0, 0.2] {
        let mesh = Mesh::lattice(8, 6, [2.0, 1.0], jitter).unwrap();
        mesh.validate().unwrap();
        if jitter == 0.0 {
            assert_eq!(mesh.faces.len(), 2 * mesh.cells.len());
            for c in &mesh.cells {
                assert!((c.volume - 2.0 / 48.0).abs() < 1e-13);
            }
        } else {
            assert!(mesh.cells.iter().any(|c| c.faces.len() != 4));
        }
        Derivatives::build(&mesh, false).unwrap();
        Derivatives::build(&mesh, true).unwrap();
    }
}

#[test]
fn affine_fits_and_constant_annihilation() {
    let mesh = Mesh::lattice(10, 10, [1.0, 1.0], 0.2).unwrap();
    let d = Derivatives::build(&mesh, false).unwrap();
    let values: Vec<_> = mesh
        .cells
        .iter()
        .map(|c| 0.7 + 2.0 * c.centroid[0] - 3.0 * c.centroid[1])
        .collect();
    let g = d.gradient(&values).unwrap();
    for (i, c) in mesh.cells.iter().enumerate() {
        if c.centroid.iter().all(|x| *x > 0.2 && *x < 0.8) {
            assert!((g[i][0] - 2.0).abs() < 1e-10);
            assert!((g[i][1] + 3.0).abs() < 1e-10);
        }
    }
    for g in d.gradient(&vec![8.0; mesh.cells.len()]).unwrap() {
        assert_eq!(g, [0.0; 2]);
    }
    let faces = Derivatives::build(&mesh, true).unwrap();
    for (i, samples) in faces.samples.iter().enumerate() {
        let mut result = [0.0; 2];
        for s in samples {
            let delta = mesh.displacement(&mesh.faces[s.index], i);
            let value = 1.3 + 2.0 * delta[0] - 3.0 * delta[1];
            for (k, r) in result.iter_mut().enumerate() {
                *r += s.weight[k] * value;
            }
        }
        assert!((result[0] - 2.0).abs() < 1e-10);
        assert!((result[1] + 3.0).abs() < 1e-10);
    }
}

#[test]
fn rebuilding_after_crossing_periodic_seams_preserves_volumes() {
    let mesh = Mesh::lattice(6, 7, [1.0, 1.0], 0.15).unwrap();
    let points = mesh
        .generators
        .iter()
        .map(|p| [p[0] + 2.91, p[1] - 1.18])
        .collect();
    let rebuilt = Mesh::build(points, mesh.lengths).unwrap();
    rebuilt.validate().unwrap();
    for (a, b) in mesh.cells.iter().zip(rebuilt.cells) {
        assert!((a.volume - b.volume).abs() < 1e-12);
    }
    let mut points = mesh.generators.clone();
    points[1] = points[0];
    assert!(Mesh::build(points, mesh.lengths).is_err());
}

#[test]
fn geometry_rebuild_handles_a_local_topology_change() {
    use std::collections::BTreeSet;
    let mesh = Mesh::lattice(6, 7, [1.0, 1.0], 0.15).unwrap();
    let mut points = mesh.generators.clone();
    points[0][0] += 0.12;
    points[0][1] += 0.06;
    let rebuilt = Mesh::build(points, mesh.lengths).unwrap();
    rebuilt.validate().unwrap();
    let keys = |m: &Mesh| {
        m.faces
            .iter()
            .map(|f| (f.left, f.right, f.image))
            .collect::<BTreeSet<_>>()
    };
    assert_ne!(keys(&mesh), keys(&rebuilt));
    // Rebuilding geometry alone performs no gas/A transfer and is not a solver step.
}

#[test]
fn manufactured_periodic_curl_converges() {
    for jitter in [0.0, 0.15] {
        let mut errors = Vec::new();
        for n in [8, 16, 32] {
            let mesh = Mesh::lattice(n, n, [1.0, 1.0], jitter).unwrap();
            let az: Vec<_> = mesh
                .cells
                .iter()
                .map(|c| (2.0 * PI * c.centroid[0]).sin() * (2.0 * PI * c.centroid[1]).sin())
                .collect();
            let g = Derivatives::build(&mesh, false)
                .unwrap()
                .gradient(&az)
                .unwrap();
            let err: f64 = mesh
                .cells
                .iter()
                .zip(g)
                .map(|(c, g)| {
                    let [x, y] = c.centroid;
                    c.volume
                        * ((g[0] - 2.0 * PI * (2.0 * PI * x).cos() * (2.0 * PI * y).sin()).powi(2)
                            + (g[1] - 2.0 * PI * (2.0 * PI * x).sin() * (2.0 * PI * y).cos())
                                .powi(2))
                        .sqrt()
                })
                .sum();
            errors.push(err);
        }
        for pair in errors.windows(2) {
            let order = (pair[0] / pair[1]).log2();
            assert!(
                order > if jitter == 0.0 { 1.8 } else { 0.7 },
                "jitter={jitter}: {errors:?}"
            );
        }
    }
}

#[test]
fn malformed_geometry_is_rejected_without_panicking() {
    let base = Mesh::lattice(4, 4, [1.0, 1.0], 0.0).unwrap();
    let mut mesh = base.clone();
    mesh.cells[0].volume = f64::NAN;
    assert!(
        mesh.validate().is_err(),
        "NaN volume must not pass validation"
    );
    let mut mesh = base.clone();
    mesh.cells[0].faces[0].0 = mesh.faces.len();
    assert!(
        mesh.validate().is_err(),
        "invalid connectivity must not panic"
    );
}

#[test]
fn nonuniform_tensor_grid_matches_exact_periodic_rectangles_across_units() {
    let xs = [0.02, 0.19, 0.39, 0.64, 0.83];
    let ys = [0.03, 0.29, 0.51, 0.78];
    let spacings = |v: &[f64], i: usize| {
        [
            (v[i] - v[(i + v.len() - 1) % v.len()]).rem_euclid(1.0),
            (v[(i + 1) % v.len()] - v[i]).rem_euclid(1.0),
        ]
    };
    for scale in [1e-6, 1.0, 1e6] {
        let lengths = [2.0 * scale, scale];
        let points = ys
            .iter()
            .flat_map(|y| xs.iter().map(move |x| [x * lengths[0], y * lengths[1]]))
            .collect();
        let mesh = Mesh::build(points, lengths).unwrap();
        for (i, cell) in mesh.cells.iter().enumerate() {
            let gaps = [spacings(&xs, i % xs.len()), spacings(&ys, i / xs.len())];
            let widths: [f64; 2] = std::array::from_fn(|k| 0.5 * (gaps[k][0] + gaps[k][1]));
            assert!(
                (cell.volume / (lengths[0] * lengths[1]) - widths[0] * widths[1]).abs() < 1e-10
            );
            for k in 0..2 {
                let expected = mesh.generators[i][k] / lengths[k] + (gaps[k][1] - gaps[k][0]) / 4.0;
                assert!((cell.centroid[k] / lengths[k] - expected).abs() < 1e-10);
            }
            assert_eq!(cell.faces.len(), 4);
            for &(f, sign) in &cell.faces {
                let face = &mesh.faces[f];
                let axis = usize::from(face.normal[1].abs() > 0.5);
                assert!(face.normal[1 - axis].abs() < 1e-10);
                assert!((face.normal[axis].abs() - 1.0).abs() < 1e-10);
                assert!((face.area / lengths[1 - axis] - widths[1 - axis]).abs() < 1e-10);
                let d = mesh.displacement(face, i);
                assert!(
                    (d[axis] / lengths[axis] - sign * face.normal[axis] * widths[axis] / 2.0).abs()
                        < 1e-10
                );
                assert!((d[1 - axis] / lengths[1 - axis]).abs() < 1e-10);
            }
        }
    }
}

#[test]
fn invalid_geometry_fields_and_connectivity_are_explicit_errors() {
    let base = Mesh::lattice(4, 4, [1.0, 1.0], 0.0).unwrap();
    for case in 0..18 {
        let mut mesh = base.clone();
        match case {
            0 => mesh.lengths[0] = f64::NAN,
            1 => mesh.lengths[1] = 0.0,
            2 => mesh.generators[0][0] = f64::INFINITY,
            3 => mesh.generators[0][0] = -0.1,
            4 => mesh.cells[0].volume = -1.0,
            5 => mesh.cells[0].centroid[0] = f64::NAN,
            6 => mesh.faces[0].area = f64::NAN,
            7 => mesh.faces[0].area = -1.0,
            8 => mesh.faces[0].normal[0] = f64::NAN,
            9 => mesh.faces[0].normal = [0.0; 2],
            10 => mesh.faces[0].right = mesh.cells.len(),
            11 => mesh.cells[0].faces[0].1 = 0.0,
            12 => {
                let duplicate = mesh.cells[0].faces[0];
                mesh.cells[0].faces.push(duplicate);
            }
            13 => {
                mesh.cells[0].faces.pop();
            }
            14 => {
                mesh.cells.pop();
            }
            15 => mesh.faces[0].centroid[0] += 0.05,
            16 => mesh.cells[0].centroid[0] += 0.01,
            _ => mesh.faces.push(mesh.faces[0].clone()),
        }
        assert!(mesh.validate().is_err(), "case {case}");
        assert!(Derivatives::build(&mesh, false).is_err(), "case {case}");
    }
    for lengths in [[0.0, 1.0], [f64::NAN, 1.0], [f64::MAX; 2], [1e-300; 2]] {
        assert!(Mesh::build(base.generators.clone(), lengths).is_err());
    }
    let mut points = base.generators.clone();
    points[1] = [points[0][0] + 1.0, points[0][1]];
    assert!(Mesh::build(points, base.lengths).is_err());
}

#[test]
fn ill_conditioned_stencils_and_invalid_values_are_rejected() {
    // Extreme anisotropy is rejected by clipping/reciprocity before reconstruction.
    assert!(Mesh::lattice(4, 4, [1.0, 8e-11], 0.0).is_err());
    let mesh = Mesh::lattice(4, 4, [1.0; 2], 0.1).unwrap();
    for at_faces in [false, true] {
        let d = Derivatives::build(&mesh, at_faces).unwrap();
        let count = if at_faces {
            mesh.faces.len()
        } else {
            mesh.cells.len()
        };
        assert!(d.gradient(&vec![1.0; count - 1]).is_err());
        let mut values = vec![1.0; count];
        values[0] = f64::NAN;
        assert!(d.gradient(&values).is_err());
        for g in d.gradient(&vec![8.0; count]).unwrap() {
            assert_eq!(g, [0.0; 2]);
        }
    }
    let raw = vec![[0.0; 2]; mesh.cells.len()];
    assert!(mesh.limit_gradients(&[], &raw).is_err());
    assert!(
        mesh.limit_gradients(&vec![f64::NAN; mesh.cells.len()], &raw)
            .is_err()
    );
    assert!(
        mesh.limit_gradients(
            &vec![1.0; mesh.cells.len()],
            &vec![[f64::INFINITY; 2]; mesh.cells.len()]
        )
        .is_err()
    );
}

#[test]
fn shared_limiter_bounds_discontinuities_and_preserves_affine_fits() {
    for jitter in [0.0, 0.2] {
        let mesh = Mesh::lattice(10, 10, [1.0; 2], jitter).unwrap();
        let d = Derivatives::build(&mesh, false).unwrap();
        let values: Vec<_> = mesh
            .cells
            .iter()
            .map(|c| if c.centroid[0] < 0.5 { 1.0 } else { -2.0 })
            .collect();
        let raw = d.gradient(&values).unwrap();
        let limited = mesh.limit_gradients(&values, &raw).unwrap();
        assert!(raw.iter().zip(&limited).any(|(a, b)| a != b));
        for (i, c) in mesh.cells.iter().enumerate() {
            let mut bounds = [values[i]; 2];
            for &(f, _) in &c.faces {
                let (j, _) = mesh.neighbour(&mesh.faces[f], i);
                bounds[0] = bounds[0].min(values[j]);
                bounds[1] = bounds[1].max(values[j]);
            }
            for &(f, _) in &c.faces {
                let q =
                    values[i] + moving_mesh::dot(limited[i], mesh.displacement(&mesh.faces[f], i));
                assert!(q >= bounds[0] - 1e-12 && q <= bounds[1] + 1e-12);
            }
        }
        let constant = vec![7.0; mesh.cells.len()];
        assert!(
            mesh.limit_gradients(&constant, &d.gradient(&constant).unwrap())
                .unwrap()
                .iter()
                .all(|g| *g == [0.0; 2])
        );
        let affine: Vec<_> = mesh
            .cells
            .iter()
            .map(|c| 0.7 + 2.0 * c.centroid[0] - 3.0 * c.centroid[1])
            .collect();
        let limited = mesh
            .limit_gradients(&affine, &d.gradient(&affine).unwrap())
            .unwrap();
        let mut checked = 0;
        for (i, c) in mesh.cells.iter().enumerate() {
            if c.centroid.iter().all(|x| *x > 0.25 && *x < 0.75) {
                assert!((limited[i][0] - 2.0).abs() < 1e-10);
                assert!((limited[i][1] + 3.0).abs() < 1e-10);
                checked += 1;
            }
        }
        assert!(checked >= 16);
    }
}

fn check_local_affine_stencils(mesh: &Mesh) {
    for at_faces in [false, true] {
        let d = Derivatives::build(mesh, at_faces).unwrap();
        for (i, samples) in d.samples.iter().enumerate() {
            let mut g = [0.0; 2];
            for s in samples {
                let displacement = if at_faces {
                    mesh.displacement(&mesh.faces[s.index], i)
                } else {
                    let face = mesh.cells[i]
                        .faces
                        .iter()
                        .map(|(f, _)| &mesh.faces[*f])
                        .find(|f| mesh.neighbour(f, i).0 == s.index)
                        .unwrap();
                    mesh.neighbour(face, i).1
                };
                for (k, value) in g.iter_mut().enumerate() {
                    *value += s.weight[k] * (1.3 + 2.0 * displacement[0] - 3.0 * displacement[1]);
                }
            }
            assert!((g[0] - 2.0).abs() < 1e-10);
            assert!((g[1] + 3.0).abs() < 1e-10);
        }
    }
}

#[test]
fn rebuilt_stencils_and_generator_permutation_preserve_reconstruction() {
    let mesh = Mesh::lattice(6, 7, [1.0; 2], 0.15).unwrap();
    let shift = [2.91, -1.18];
    let points = mesh
        .generators
        .iter()
        .map(|p| [p[0] + shift[0], p[1] + shift[1]])
        .collect();
    let shifted = Mesh::build(points, mesh.lengths).unwrap();
    check_local_affine_stencils(&shifted);
    let values: Vec<_> = mesh
        .cells
        .iter()
        .map(|c| (2.0 * PI * c.centroid[0]).sin())
        .collect();
    let g = Derivatives::build(&mesh, false)
        .unwrap()
        .gradient(&values)
        .unwrap();
    let shifted_g = Derivatives::build(&shifted, false)
        .unwrap()
        .gradient(&values)
        .unwrap();
    let reversed = Mesh::build(
        mesh.generators.iter().rev().copied().collect(),
        mesh.lengths,
    )
    .unwrap();
    let reversed_g = Derivatives::build(&reversed, false)
        .unwrap()
        .gradient(&values.iter().rev().copied().collect::<Vec<_>>())
        .unwrap();
    for i in 0..mesh.cells.len() {
        let j = mesh.cells.len() - 1 - i;
        assert!((mesh.cells[i].volume - reversed.cells[j].volume).abs() < 1e-10);
        for k in 0..2 {
            assert!((g[i][k] - shifted_g[i][k]).abs() < 1e-10);
            assert!((g[i][k] - reversed_g[j][k]).abs() < 1e-10);
        }
    }
    let mut points = mesh.generators.clone();
    points[0][0] += 0.12;
    points[0][1] += 0.06;
    check_local_affine_stencils(&Mesh::build(points, mesh.lengths).unwrap());
}

#[test]
fn immutable_reconstruction_guard_matches_individual_calls_and_rejects_corruption() {
    for jitter in [0., 0.15] {
        let mesh = Mesh::lattice(8, 6, [1.3, 0.7], jitter).unwrap();
        let stencil = Derivatives::build(&mesh, false).unwrap();
        let guard = mesh.reconstruction().unwrap();
        for frequency in [1., 3.] {
            let values: Vec<_> = mesh
                .cells
                .iter()
                .map(|c| (2. * PI * frequency * c.centroid[0] / mesh.lengths[0]).sin())
                .collect();
            let g = stencil.gradient(&values).unwrap();
            assert_eq!(
                guard.limit_gradients(&values, &g).unwrap(),
                mesh.limit_gradients(&values, &g).unwrap()
            );
        }
    }
    let mut corrupt = Mesh::lattice(4, 4, [1.; 2], 0.).unwrap();
    corrupt.cells[0].volume *= 2.;
    assert!(corrupt.reconstruction().is_err());
}

#[test]
fn ordered_pruning_is_bit_identical_to_all_pairs_clipping() {
    for lengths in [[1.; 2], [1.3, 0.7], [1e-3, 2e-3], [1300., 700.]] {
        for jitter in [0., 0.15, 0.25] {
            let initial = Mesh::lattice(8, 6, lengths, jitter).unwrap();
            for variant in 0..4 {
                let mut points = initial.generators.clone();
                match variant {
                    1 => points.reverse(),
                    2 => {
                        for p in &mut points {
                            p[0] += 2.91 * lengths[0];
                            p[1] -= 1.18 * lengths[1];
                        }
                    }
                    3 => {
                        points[0][0] += 0.12 * lengths[0];
                        points[0][1] += 0.06 * lengths[1];
                    }
                    _ => {}
                }
                let fast = Mesh::build(points.clone(), lengths).unwrap();
                let original = Mesh::build_all_pairs(points, lengths).unwrap();
                assert_eq!(format!("{fast:?}"), format!("{original:?}"));
            }
            let mut points = initial.generators.clone();
            points[1] = points[0];
            assert!(Mesh::build(points.clone(), lengths).is_err());
            assert!(Mesh::build_all_pairs(points, lengths).is_err());
        }
    }
}

#[test]
fn diagnostic_polygons_reproduce_cell_area_and_centroid() {
    for lengths in [[1., 1.], [2., 0.125]] {
        for jitter in [0., 0.15] {
            let mesh = Mesh::lattice(13, 7, lengths, jitter).unwrap();
            for (i, cell) in mesh.cells.iter().enumerate() {
                let p = mesh.polygon(i).unwrap();
                let mut area = 0.;
                let mut centre = [0.; 2];
                for k in 0..p.len() {
                    let a = p[k];
                    let b = p[(k + 1) % p.len()];
                    let a = [a[0] - cell.centroid[0], a[1] - cell.centroid[1]];
                    let b = [b[0] - cell.centroid[0], b[1] - cell.centroid[1]];
                    let cross = a[0] * b[1] - a[1] * b[0];
                    area += 0.5 * cross;
                    for j in 0..2 {
                        centre[j] += (a[j] + b[j]) * cross / 6.;
                    }
                }
                assert!((area / cell.volume - 1.).abs() < 1e-10);
                assert!(centre.iter().all(|x| (x / area).abs() < 1e-10));
            }
        }
    }
}
