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
    let g = d.gradient(&values);
    for (i, c) in mesh.cells.iter().enumerate() {
        if c.centroid.iter().all(|x| *x > 0.2 && *x < 0.8) {
            assert!((g[i][0] - 2.0).abs() < 1e-10);
            assert!((g[i][1] + 3.0).abs() < 1e-10);
        }
    }
    for g in d.gradient(&vec![8.0; mesh.cells.len()]) {
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
            let g = Derivatives::build(&mesh, false).unwrap().gradient(&az);
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
