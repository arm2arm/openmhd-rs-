use moving_mesh::{Mesh, parallel};

#[test]
fn threaded_geometry_and_operators_match_serial_bits() {
    for jitter in [0., 0.15] {
        let original = Mesh::lattice(8, 8, [1.3, 0.7], jitter).unwrap();
        let points: Vec<_> = (0..64)
            .map(|i| original.generators[(17 * i + 5) % 64])
            .collect();
        let build = || {
            let mesh = Mesh::build(points.clone(), [1.3, 0.7]).unwrap();
            let values: Vec<_> = mesh
                .cells
                .iter()
                .map(|c| (c.centroid[0] * 5.).sin())
                .collect();
            let stencil = moving_mesh::Derivatives::build(&mesh, false).unwrap();
            let gradients = stencil.gradient(&values).unwrap();
            let limited = mesh.limit_gradients(&values, &gradients).unwrap();
            // f64 Debug preserves the exact round-trippable finite value, including -0.
            format!("{mesh:?}{gradients:?}{limited:?}")
        };
        let serial = build();
        for threads in [1, 2, 4, 24] {
            assert_eq!(parallel::with_threads(threads, build).unwrap(), serial);
        }
    }
}

#[test]
fn threaded_error_selection_and_explicit_thread_limits() {
    for threads in [1, 2, 4, 24] {
        let result = parallel::with_threads(threads, || {
            parallel::try_map(256, |i| {
                if i == 33 || i == 192 {
                    Err(format!("bad {i}"))
                } else {
                    Ok(i)
                }
            })
        })
        .unwrap();
        assert_eq!(result.unwrap_err(), "bad 33");
    }
    for threads in [0, 25] {
        assert!(parallel::with_threads(threads, || ()).is_err());
    }
    parallel::with_threads(4, || {
        parallel::with_threads(1, || {
            assert_eq!(rayon::current_num_threads(), 1);
        })
        .unwrap()
    })
    .unwrap();
}
