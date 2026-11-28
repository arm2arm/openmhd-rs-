use super::{domain, flow, sites};
use moving_mesh::three_d::{fit::SampleKey3, sweeps::SharedSweeps3, *};
use std::collections::BTreeMap;

fn close(a: f64, b: f64) {
    assert!(
        (a - b).abs() <= 2e-12 * (1. + a.abs().max(b.abs())),
        "{a:.17e} vs {b:.17e}"
    );
}

fn compare(sites: &[Generator3]) {
    let reference = HalfSpaceOracle3::build_supported_periodic(domain(), sites).unwrap();
    let product = HalfSpaceOracle3::try_supported_product(domain(), sites)
        .unwrap()
        .unwrap();
    let (a, b) = (reference.geometry(), product.geometry());
    let velocity = flow(sites);
    let p = PrescribedPolygonRates3::build(&reference, &velocity).unwrap();
    let q = PrescribedPolygonRates3::build(&product, &velocity).unwrap();
    assert_eq!(a.cells().len(), b.cells().len());
    assert_eq!(a.faces().len(), b.faces().len());
    for (i, (x, y)) in a.cells().iter().zip(b.cells()).enumerate() {
        assert_eq!(x.generator, y.generator);
        close(x.volume, y.volume);
        close(x.surface_area, y.surface_area);
        close(x.bounding_radius, y.bounding_radius);
        close(
            x.minimum_generator_face_distance,
            y.minimum_generator_face_distance,
        );
        assert_eq!(x.incidences.len(), y.incidences.len());
        for (l, r) in x.incidences.iter().zip(&y.incidences) {
            assert_eq!((l.face, l.sign, l.neighbour), (r.face, r.sign, r.neighbour));
            for (s, t) in l.chart_translation.into_iter().zip(r.chart_translation) {
                close(s, t);
            }
        }
        let ca = p.cells_and_faces().cell(a.cell_ref(i).unwrap()).unwrap();
        let cb = q.cells_and_faces().cell(b.cell_ref(i).unwrap()).unwrap();
        close(ca.volume_rate, cb.volume_rate);
        for k in 0..3 {
            close(x.centroid_offset[k], y.centroid_offset[k]);
            close(ca.centroid_velocity[k], cb.centroid_velocity[k]);
            for j in 0..3 {
                close(x.central_second_moment[k][j], y.central_second_moment[k][j]);
            }
        }
    }
    for (i, (x, y)) in a.faces().iter().zip(b.faces()).enumerate() {
        assert_eq!(
            (x.key, x.left, x.right, x.right_wrapped_image),
            (y.key, y.left, y.right, y.right_wrapped_image)
        );
        close(x.area, y.area);
        close(x.plane_distance, y.plane_distance);
        assert_eq!(x.polygon.len(), 4);
        assert_eq!(y.polygon.len(), 4);
        let ha = a.face_ref(i).unwrap();
        let hb = b.face_ref(i).unwrap();
        let (sa, sb) = (
            reference.vertex_supports(ha).unwrap(),
            product.vertex_supports(hb).unwrap(),
        );
        let start = y
            .polygon
            .iter()
            .position(|v| *v == x.polygon[0])
            .expect("same first vertex");
        for (j, v) in x.polygon.iter().enumerate() {
            let k = (j + start) % 4;
            assert_eq!(*v, y.polygon[k]);
            assert_eq!(sa[j].len(), 7);
            assert_eq!(sa[j], sb[k]);
        }
        let (fa, fb) = (p.face(ha).unwrap(), q.face(hb).unwrap());
        for k in 0..3 {
            close(x.normal[k], y.normal[k]);
            close(x.centroid_offset[k], y.centroid_offset[k]);
            close(fa.centroid_velocity[k], fb.centroid_velocity[k]);
            close(fa.area_vector_rate[k], fb.area_vector_rate[k]);
            for j in 0..3 {
                close(x.covariance[k][j], y.covariance[k][j]);
                close(fa.covariance_rate[k][j], fb.covariance_rate[k][j]);
            }
        }
    }
}

#[test]
fn product_matches_all_pairs_oriented_support_and_motion_across_seams() {
    let mut s = sites();
    for (i, p) in s.iter_mut().enumerate() {
        p.id = SampleKey3::from_words(93, ((i * 11) % 27) as u64, Image3::ZERO).owner;
        p.winding = Image3(p.position.map(|x| if x == 0.125 { 2 } else { -1 }));
    }
    s.reverse();
    compare(&s);
}

#[test]
fn product_matches_periodic_self_and_two_plane_images() {
    let s: Vec<_> = sites()
        .into_iter()
        .filter(|p| p.position[0] == 0.125 && p.position[1] != 0.8125)
        .collect();
    compare(&s);
}

#[test]
fn incomplete_product_and_invalid_catalogs_fail_closed() {
    let mut s = sites();
    s.pop();
    assert!(
        HalfSpaceOracle3::try_supported_product(domain(), &s)
            .unwrap()
            .is_none()
    );
    let mut duplicate = s[0];
    duplicate.id = s.pop().unwrap().id;
    s.push(duplicate);
    assert!(matches!(
        HalfSpaceOracle3::try_supported_product(domain(), &s),
        Err(GeometryError3::CoincidentGenerators { .. })
    ));
    s.pop();
    s[1].position[0] = 1.;
    assert!(matches!(
        HalfSpaceOracle3::try_supported_product(domain(), &s),
        Err(GeometryError3::GeneratorOutside { .. })
    ));
}

fn grid(dims: [usize; 3]) -> Vec<Generator3> {
    (0..dims.iter().product())
        .map(|i: usize| Generator3 {
            id: SampleKey3::from_words(7, i as u64, Image3::ZERO).owner,
            position: std::array::from_fn(|k| {
                ((i / dims[..k].iter().product::<usize>() % dims[k]) as f64 + 0.5) / dims[k] as f64
            }),
            winding: Image3::ZERO,
        })
        .collect()
}

#[test]
fn large_product_retains_all_cells_faces_and_reciprocals() {
    let s = grid([12, 9, 8]);
    let product = HalfSpaceOracle3::try_supported_product(domain(), &s)
        .unwrap()
        .unwrap();
    let g = product.geometry();
    assert_eq!(g.cells().len(), 864);
    assert_eq!(g.faces().len(), 3 * s.len());
    for c in g.cells() {
        close(c.volume, 1. / 864.);
        assert_eq!(c.incidences.len(), 6);
    }
    for (i, f) in g.faces().iter().enumerate() {
        let left = &g.cells()[f.left as usize];
        let right = &g.cells()[f.right.unwrap() as usize];
        assert!(
            left.incidences
                .iter()
                .any(|v| v.face as usize == i && v.sign == 1)
        );
        assert!(
            right
                .incidences
                .iter()
                .any(|v| v.face as usize == i && v.sign == -1)
        );
        assert!(
            product
                .vertex_supports(g.face_ref(i).unwrap())
                .unwrap()
                .iter()
                .all(|p| p.len() == 7)
        );
    }
}

#[test]
fn grounded_sparse_ring_matches_exact_inverse_row_sum() {
    let n = 130;
    let s = grid([n, 1, 1]);
    let product = HalfSpaceOracle3::try_supported_product(domain(), &s)
        .unwrap()
        .unwrap();
    let g = product.geometry();
    let v: BTreeMap<_, _> = s.iter().map(|p| (p.id, [0.; 3])).collect();
    let m = prescribed_motion_rates3(g, &v, [0.; 3]).unwrap();
    let sweep = SharedSweeps3::heun(g, &m, g, &m, 1. / 256.).unwrap();
    // For the grounded periodic cycle, (L^-1 1)_i=i(n-i)/(2w), ||L||_inf=4w.
    close(
        sweep.components[0].grounded_condition_inf,
        (n * n / 2) as f64,
    );
    assert_eq!(sweep.max_corrected_relative_defect, 0.);
}

#[test]
fn sparse_grounded_correction_closes_deforming_product_cells() {
    let s = grid([8, 8, 3]);
    let start = HalfSpaceOracle3::try_supported_product(domain(), &s)
        .unwrap()
        .unwrap();
    let g = start.geometry();
    let w = flow(&s);
    let dt = 1. / 512.;
    let endpoints = generator_endpoints3(g, &w, dt).unwrap();
    let end = HalfSpaceOracle3::try_supported_product(domain(), &endpoints)
        .unwrap()
        .unwrap();
    let rates = prescribed_motion_rates3(g, &w, [0.; 3]).unwrap();
    let updated = prescribed_motion_rates3(end.geometry(), &w, [0.; 3]).unwrap();
    for sweep in [
        SharedSweeps3::euler(g, &rates, end.geometry(), dt).unwrap(),
        SharedSweeps3::heun(g, &rates, end.geometry(), &updated, dt).unwrap(),
    ] {
        assert_eq!(sweep.components.len(), 1);
        assert!(sweep.max_raw_relative_defect > 1e-11);
        assert!(sweep.max_corrected_relative_defect < 1e-12);
    }
}
