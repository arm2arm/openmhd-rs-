use galaxy_types::{CellId, EntityId};
use moving_mesh::three_d::*;
use std::collections::BTreeMap;

type Flow = BTreeMap<CellId, GasMotion3>;
fn id(n: u64) -> CellId {
    CellId::new(EntityId::new(23, n))
}
fn site(n: u64, position: Vec3) -> Generator3 {
    Generator3 {
        id: id(n),
        position,
        winding: Image3::ZERO,
    }
}
fn domain(boundary: Boundary3) -> Domain3 {
    Domain3 {
        anchor: [0.0; 3],
        width: [1.0; 3],
        boundary,
    }
}
fn geometry(boundary: Boundary3, sites: &[Generator3]) -> ValidatedGeometry3 {
    HalfSpaceOracle3::build(domain(boundary), sites).unwrap()
}
fn flow(rows: &[(u64, Vec3, f64)]) -> Flow {
    rows.iter()
        .map(|&(n, velocity, sound_speed)| {
            (
                id(n),
                GasMotion3 {
                    velocity,
                    sound_speed,
                },
            )
        })
        .collect()
}
fn config(iterations: usize, sound_speed_fraction: Option<f64>) -> LloydConfig3 {
    LloydConfig3 {
        iterations,
        sound_speed_fraction,
    }
}
fn close(got: f64, want: f64) {
    assert!((got - want).abs() < 2e-12, "got {got:e}, expected {want:e}");
}
fn close3(got: Vec3, want: Vec3) {
    for (a, b) in got.into_iter().zip(want) {
        close(a, b);
    }
}
fn norm(v: Vec3) -> f64 {
    v[0].hypot(v[1]).hypot(v[2])
}
fn cell(mesh: &ValidatedGeometry3, n: u64) -> &CellGeometry3 {
    mesh.cell(mesh.cell_by_id(id(n)).unwrap()).unwrap()
}

#[test]
fn bounded_cell_targets_future_centroid_from_original_position() {
    let p = [0.125, 0.375, 0.75];
    let gas = [0.25, -0.125, 0.0625];
    let mesh = geometry(Boundary3::Bounded, &[site(1, p)]);
    let f = flow(&[(1, gas, 1.0)]);
    let dt = 0.25;
    let step = predict_lloyd_step3(&mesh, &f, dt, config(1, None)).unwrap();
    close3(step.velocities[&id(1)], p.map(|x| (0.5 - x) / dt));
    close3(cell(&step.geometry, 1).generator.position, [0.5; 3]);
    close3(cell(&step.geometry, 1).centroid_offset, [0.0; 3]);
    close(cell(&step.geometry, 1).volume, 1.0);
}

#[test]
fn two_slab_iterations_are_synchronous_and_return_the_last_endpoint() {
    let sites = [site(9, [0.125, 0.5, 0.5]), site(2, [0.625, 0.5, 0.5])];
    let mesh = geometry(Boundary3::Bounded, &sites);
    let reversed = geometry(Boundary3::Bounded, &[sites[1], sites[0]]);
    let f = flow(&[(9, [0.25, 0.0, 0.0], 1.0), (2, [0.125, 0.0, 0.0], 2.0)]);
    let dt = 0.25;
    // Independent 1D slab oracle: the shared face bisects the two predicted sites.
    let mut x = [0.1875, 0.65625];
    for k in 0..=3 {
        let a = predict_lloyd_step3(&mesh, &f, dt, config(k, None)).unwrap();
        let b = predict_lloyd_step3(&reversed, &f, dt, config(k, None)).unwrap();
        assert_eq!(a.velocities, b.velocities);
        for (i, n) in [9, 2].into_iter().enumerate() {
            close3(cell(&a.geometry, n).generator.position, [x[i], 0.5, 0.5]);
            close(a.velocities[&id(n)][0], (x[i] - sites[i].position[0]) / dt);
        }
        let face = (x[0] + x[1]) / 2.0;
        x = [face / 2.0, (1.0 + face) / 2.0];
    }
}

#[test]
fn sound_speed_bounds_total_vector_correction_about_fluid_motion() {
    let p = [0.125, 0.25, 0.75];
    let v = [0.25, -0.125, 0.0];
    let dt = 0.25;
    let f = flow(&[(1, v, 0.5)]);
    let mesh = geometry(Boundary3::Bounded, &[site(1, p)]);
    let adv: Vec3 = std::array::from_fn(|a| p[a] + dt * v[a]);
    let toward = adv.map(|x| 0.5 - x);
    let limit = 0.05;
    for passes in [1, 5] {
        let s = predict_lloyd_step3(&mesh, &f, dt, config(passes, Some(0.1))).unwrap();
        let dv = std::array::from_fn(|a| s.velocities[&id(1)][a] - v[a]);
        close(norm(dv), limit);
        close3(dv, toward.map(|c| limit * c / norm(toward)));
        close3(
            cell(&s.geometry, 1).generator.position,
            std::array::from_fn(|a| adv[a] + dv[a] * dt),
        );
    }
}

#[test]
fn zero_passes_zero_fraction_and_cold_gas_follow_the_fluid() {
    let p = [0.25; 3];
    let v = [0.125, -0.0625, 0.25];
    let mesh = geometry(Boundary3::Bounded, &[site(2, p)]);
    for (k, fraction, cs) in [(0, None, 2.0), (5, Some(0.0), 2.0), (5, Some(0.1), 0.0)] {
        let s = predict_lloyd_step3(&mesh, &flow(&[(2, v, cs)]), 0.5, config(k, fraction)).unwrap();
        assert_eq!(s.velocities[&id(2)], v);
        close3(
            cell(&s.geometry, 2).generator.position,
            std::array::from_fn(|a| p[a] + 0.5 * v[a]),
        );
    }
}

#[test]
fn periodic_centroid_crosses_seam_and_commutes_with_uniform_boost() {
    let common = 1_i64 << 55;
    let mut sites = [site(1, [0.03125, 0.5, 0.5]), site(2, [0.375, 0.5, 0.5])];
    for g in &mut sites {
        g.winding = Image3([common, 0, 0]);
    }
    let mesh = geometry(Boundary3::Periodic, &sites);
    let base = flow(&[(1, [0.0; 3], 1.0), (2, [0.0; 3], 1.0)]);
    // Five complete boxes in x and an additional exactly representable translation in y.
    let boost = [20.0, 0.5, -4.0];
    let boosted = flow(&[(1, boost, 1.0), (2, boost, 1.0)]);
    let dt = 0.25;
    for cap in [None, Some(0.125)] {
        let a = predict_lloyd_step3(&mesh, &base, dt, config(3, cap)).unwrap();
        let b = predict_lloyd_step3(&mesh, &boosted, dt, config(3, cap)).unwrap();
        for n in [1, 2] {
            let ga = cell(&a.geometry, n);
            let gb = cell(&b.geometry, n);
            close3(
                std::array::from_fn(|i| b.velocities[&id(n)][i] - boost[i]),
                a.velocities[&id(n)],
            );
            close3(
                gb.generator.position,
                [ga.generator.position[0], 0.625, 0.5],
            );
            close(gb.volume, ga.volume);
            assert_eq!(
                gb.generator.winding,
                Image3([ga.generator.winding.0[0] + 5, 0, -1])
            );
        }
        if cap.is_none() {
            assert_eq!(cell(&a.geometry, 1).generator.winding.0[0], common - 1);
            close(cell(&a.geometry, 1).generator.position[0], 0.953125);
        }
    }
}

#[test]
fn large_integer_box_drift_preserves_local_position_and_checked_winding() {
    let dom = Domain3 {
        anchor: [-3.0, 2.0, -0.5],
        width: [2.0, 4.0, 1.0],
        boundary: Boundary3::Periodic,
    };
    let p = [-2.5, 3.0, 0.0];
    let mut g = site(1, p);
    g.winding = Image3([5, -3, 0]);
    let mesh = HalfSpaceOracle3::build(dom, &[g]).unwrap();
    let many = 1_i64 << 54;
    let f = flow(&[(1, [2.0 * many as f64, -12.0, -0.5], 1.0)]);
    let s = predict_lloyd_step3(&mesh, &f, 1.0, config(0, None)).unwrap();
    let end = cell(&s.geometry, 1).generator;
    assert_eq!(end.position, [-2.5, 3.0, -0.5]);
    assert_eq!(end.winding, Image3([5 + many, -6, 0]));
}

#[test]
fn small_centered_cell_keeps_its_id_and_receives_no_volume_kick() {
    let mesh = geometry(
        Boundary3::Bounded,
        &[
            site(1, [0.49609375, 0.5, 0.5]),
            site(2, [0.5; 3]),
            site(3, [0.50390625, 0.5, 0.5]),
        ],
    );
    let f = flow(&[(1, [0.0; 3], 1.0), (2, [0.0; 3], 1.0), (3, [0.0; 3], 1.0)]);
    close(cell(&mesh, 2).volume, 1.0 / 256.0);
    let s = predict_lloyd_step3(&mesh, &f, 0.125, LloydConfig3::default()).unwrap();
    close3(s.velocities[&id(2)], [0.0; 3]);
    close3(cell(&s.geometry, 2).generator.position, [0.5; 3]);
    assert_eq!(s.geometry.cells().len(), 3);
    close(s.geometry.cells().iter().map(|c| c.volume).sum(), 1.0);
}

#[test]
fn invalid_flow_catalog_timestep_and_fraction_are_rejected() {
    let mesh = geometry(Boundary3::Bounded, &[site(7, [0.5; 3])]);
    let f = flow(&[(7, [0.0; 3], 1.0)]);
    let run = |flow: &Flow, dt, cfg| predict_lloyd_step3(&mesh, flow, dt, cfg).unwrap_err();
    for dt in [0.0, -1.0, f64::NAN, f64::INFINITY] {
        assert_eq!(
            run(&f, dt, LloydConfig3::default()),
            LloydError3::InvalidTimestep
        );
    }
    for fraction in [-0.01, 1.01, f64::NAN] {
        assert_eq!(
            run(&f, 1.0, config(1, Some(fraction))),
            LloydError3::InvalidSoundSpeedFraction
        );
    }
    for bad in [
        Flow::new(),
        flow(&[(9, [0.0; 3], 1.0)]),
        flow(&[(7, [0.0; 3], 1.0), (9, [0.0; 3], 1.0)]),
    ] {
        assert_eq!(
            run(&bad, 1.0, LloydConfig3::default()),
            LloydError3::FlowCatalogMismatch
        );
    }
    for (v, cs) in [
        ([f64::INFINITY, 0.0, 0.0], 1.0),
        ([0.0; 3], -1.0),
        ([0.0; 3], f64::NAN),
    ] {
        assert_eq!(
            run(&flow(&[(7, v, cs)]), 1.0, LloydConfig3::default()),
            LloydError3::InvalidFlow(id(7))
        );
    }
}

#[test]
fn failed_predictions_preserve_inputs_and_report_the_geometry_error() {
    let mesh = geometry(
        Boundary3::Bounded,
        &[site(1, [0.25, 0.5, 0.5]), site(2, [0.75, 0.5, 0.5])],
    );
    let old = mesh.cell_by_id(id(1)).unwrap();
    let run = |vx1, vx2| {
        predict_lloyd_step3(
            &mesh,
            &flow(&[(1, [vx1, 0.0, 0.0], 1.0), (2, [vx2, 0.0, 0.0], 1.0)]),
            1.0,
            LloydConfig3::default(),
        )
        .unwrap_err()
    };
    assert!(matches!(
        run(0.25, -0.25),
        LloydError3::Geometry(GeometryError3::CoincidentGenerators { .. })
    ));
    assert_eq!(
        run(-0.25, 0.0),
        LloydError3::Geometry(GeometryError3::GeneratorOutside { id: id(1) })
    );
    assert_eq!(mesh.cell(old).unwrap().generator.position, [0.25, 0.5, 0.5]);
    let mut p = site(1, [0.5; 3]);
    p.winding = Image3([i64::MAX, 0, 0]);
    let periodic = geometry(Boundary3::Periodic, &[p]);
    assert_eq!(
        predict_lloyd_step3(
            &periodic,
            &flow(&[(1, [2.0, 0.0, 0.0], 1.0)]),
            1.0,
            config(0, None)
        )
        .unwrap_err(),
        LloydError3::Geometry(GeometryError3::ImageOverflow)
    );
}

#[test]
fn irregular_moving_cloud_improves_centering_and_closes_volume() {
    let coordinates = [
        [0.18, 0.22, 0.29],
        [0.77, 0.28, 0.21],
        [0.31, 0.71, 0.17],
        [0.82, 0.81, 0.32],
        [0.28, 0.16, 0.74],
        [0.69, 0.33, 0.84],
        [0.19, 0.78, 0.67],
        [0.74, 0.66, 0.72],
    ];
    let sites: Vec<_> = coordinates
        .iter()
        .enumerate()
        .map(|(i, &p)| site(i as u64, p))
        .collect();
    let mesh = geometry(Boundary3::Bounded, &sites);
    let f: Flow = sites
        .iter()
        .map(|g| {
            (
                g.id,
                GasMotion3 {
                    velocity: [(g.position[1] - 0.5) * 0.25, 0.0, 0.0],
                    sound_speed: 1.0,
                },
            )
        })
        .collect();
    let step = |k| predict_lloyd_step3(&mesh, &f, 0.25, config(k, Some(0.1))).unwrap();
    let rms = |m: &ValidatedGeometry3| {
        (m.cells()
            .iter()
            .map(|c| (norm(c.centroid_offset) / c.volume.cbrt()).powi(2))
            .sum::<f64>()
            / sites.len() as f64)
            .sqrt()
    };
    let a = step(0);
    let b = step(5);
    let before = rms(&a.geometry);
    let after = rms(&b.geometry);
    println!("dimensionless_rms_advected={before:.12e} dimensionless_rms_lloyd={after:.12e}");
    assert!(after < before, "{after} >= {before}");
    for s in [&a, &b] {
        close(s.geometry.cells().iter().map(|c| c.volume).sum(), 1.0);
    }
    for (&id, w) in &b.velocities {
        assert!(norm(std::array::from_fn(|i| w[i] - f[&id].velocity[i])) <= 0.1 + 2e-12);
    }
}
