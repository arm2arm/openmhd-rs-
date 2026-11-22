//! Manual analytic references: docs/galaxy/fixtures/geometry3_analytic_v1.json,
//! independently reviewed in BOUNDARY_MHD_DESIGN_REVIEW.md findings 11-12.
//! Written only: execute each test on its own REANA workflow after preflight.
use galaxy_types::{CellId, EntityId};
use moving_mesh::three_d::*;

const PACKET: &str = include_str!("../../../docs/galaxy/fixtures/geometry3_analytic_v1.json");
const TOL: f64 = 1e-10;

fn id(namespace: u64, counter: u64) -> CellId { CellId::new(EntityId::new(namespace, counter)) }
fn close(value: f64, expected: f64, scale: f64) {
    assert!(value.is_finite() && expected.is_finite() && scale > 0.0);
    assert!((value - expected).abs() <= TOL * scale, "actual {value:e}, expected {expected:e}, scale {scale:e}");
}
fn generator(namespace: u64, counter: u64, position: Vec3) -> Generator3 {
    Generator3 { id: id(namespace, counter), position, winding: Image3::ZERO }
}
fn periodic() -> Domain3 { Domain3 { anchor: [0.0; 3], width: [1.0; 3], boundary: Boundary3::Periodic } }

fn witness(domain: Domain3, input: &[Generator3]) {
    println!("domain {:?} anchor_bits {:?} width_bits {:?}", domain.boundary,
        domain.anchor.map(f64::to_bits), domain.width.map(f64::to_bits));
    for g in input { println!("cell {} position_bits {:?} winding {:?}", g.id.entity(), g.position.map(f64::to_bits), g.winding); }
}

/// Expected interval arithmetic is separable and independent of clipping,
/// cap ordering, tetrahedra and candidate integration.
fn tensor(namespace: u64, name: &str, axes: [&[f64]; 3], intervals: [&[[f64; 2]]; 3]) {
    assert!(PACKET.contains(name));
    let mut input = Vec::new();
    for z in axes[2] { for y in axes[1] { for x in axes[0] {
        input.push(generator(namespace, input.len() as u64 + 1, [*x, *y, *z]));
    } } }
    witness(periodic(), &input);
    let geometry = HalfSpaceOracle3::build(periodic(), &input).expect("required analytic fixture must build");
    println!("quality {:?}", geometry.quality());
    assert_eq!(geometry.cells().len(), input.len());
    assert_eq!(geometry.faces().len(), 3 * input.len());
    assert!(geometry.faces().iter().all(|f| f.right.is_some()));
    let mut total = 0.0;
    for (i, cell) in geometry.cells().iter().enumerate() {
        let index = [i % axes[0].len(), (i / axes[0].len()) % axes[1].len(), i / (axes[0].len() * axes[1].len())];
        let range: [[f64; 2]; 3] = std::array::from_fn(|a| intervals[a][index[a]]);
        let h = range.map(|r| r[1] - r[0]);
        let centroid = range.map(|r| (r[0] + r[1]) / 2.0);
        let volume = h[0] * h[1] * h[2];
        close(cell.volume, volume, volume);
        total += cell.volume;
        assert_eq!(cell.generator.id, input[i].id);
        assert_eq!(cell.incidences.len(), 6);
        for a in 0..3 {
            close(cell.centroid_offset[a], centroid[a] - input[i].position[a], 1.0);
            for b in 0..3 {
                close(cell.central_second_moment[a][b], if a == b { volume * h[a] * h[a] / 12.0 } else { 0.0 }, volume);
            }
        }
        for incidence in &cell.incidences {
            let face = &geometry.faces()[incidence.face as usize];
            let axis = (0..3).find(|a| face.normal[*a].abs() > 0.5).unwrap();
            let sign = f64::from(incidence.sign);
            let upper = sign * face.normal[axis] > 0.0;
            let expected_area = h[(axis + 1) % 3] * h[(axis + 2) % 3];
            close(face.area, expected_area, expected_area);
            for a in 0..3 {
                let actual = cell.generator.position[a] + face.centroid_offset[a] + incidence.chart_translation[a];
                let expected = if a == axis { range[a][usize::from(upper)] } else { centroid[a] };
                close(actual, expected, 1.0);
                close(sign * face.normal[a], if a == axis { if upper { 1.0 } else { -1.0 } } else { 0.0 }, 1.0);
                for b in 0..3 {
                    let expected = if a == b && a != axis { h[a] * h[a] / 12.0 } else { 0.0 };
                    close(face.covariance[a][b], expected, 1.0);
                }
            }
        }
    }
    close(total, 1.0, 1.0);
    assert!(geometry.quality().relative_volume_closure <= TOL);
    assert!(geometry.quality().maximum_normal_closure <= TOL);
    assert!(geometry.quality().maximum_affine_closure <= TOL);
}

#[test]
fn periodic_one_cell_self_images() {
    tensor(1, "periodic_one_cell_self_images", [&[1.0 / 4.0], &[3.0 / 8.0], &[5.0 / 8.0]],
        [&[[-1.0 / 4.0, 3.0 / 4.0]], &[[-1.0 / 8.0, 7.0 / 8.0]], &[[1.0 / 8.0, 9.0 / 8.0]]]);
    let g = HalfSpaceOracle3::build(periodic(), &[generator(1, 1, [0.25, 0.375, 0.625])]).unwrap();
    let mut images = Vec::new();
    for face in g.faces() {
        assert_eq!(face.left, 0);
        assert_eq!(face.right, Some(0));
        if let FaceKey3::Interior { lo, hi, hi_image } = face.key {
            assert_eq!(lo, hi);
            images.push(hi_image.0);
        } else { panic!("periodic boundary face"); }
    }
    images.sort();
    assert_eq!(images, vec![[0, 0, 1], [0, 1, 0], [1, 0, 0]]);
    for index in 0..3 {
        let signs: Vec<_> = g.cells()[0].incidences.iter().filter(|i| i.face as usize == index).map(|i| i.sign).collect();
        assert_eq!(signs, vec![1, -1]);
    }
}

#[test]
fn periodic_cartesian_2x2x2() {
    let axis = [0.25, 0.75];
    let intervals = [[0.0, 0.5], [0.5, 1.0]];
    tensor(2, "periodic_cartesian_2x2x2", [&axis; 3], [&intervals; 3]);
}

#[test]
fn periodic_nonuniform_3x2x2() {
    tensor(3, "periodic_nonuniform_3x2x2", [&[0.125, 0.375, 0.75], &[0.25, 0.75], &[0.25, 0.75]],
        [&[[-1.0 / 16.0, 0.25], [0.25, 9.0 / 16.0], [9.0 / 16.0, 15.0 / 16.0]],
         &[[0.0, 0.5], [0.5, 1.0]], &[[0.0, 0.5], [0.5, 1.0]]]);
}

#[test]
fn periodic_cartesian_4x4x4() {
    let axis = [0.125, 0.375, 0.625, 0.875];
    let intervals = [[0.0, 0.25], [0.25, 0.5], [0.5, 0.75], [0.75, 1.0]];
    tensor(4, "periodic_cartesian_4x4x4", [&axis; 3], [&intervals; 3]);
}

#[test]
fn periodic_nonuniform_4x4x4() {
    let axis = [1.0 / 20.0, 3.0 / 20.0, 7.0 / 20.0, 13.0 / 20.0];
    let intervals = [[-3.0 / 20.0, 1.0 / 10.0], [1.0 / 10.0, 1.0 / 4.0], [1.0 / 4.0, 1.0 / 2.0], [1.0 / 2.0, 17.0 / 20.0]];
    tensor(5, "periodic_nonuniform_4x4x4", [&axis; 3], [&intervals; 3]);
}

#[test]
fn bounded_one_cell_2x3x4() {
    assert!(PACKET.contains("bounded_one_cell_2x3x4"));
    let domain = Domain3 { anchor: [-1.0, -2.0, -3.0], width: [2.0, 3.0, 4.0], boundary: Boundary3::Bounded };
    let input = generator(6, 1, [0.25, -1.0, 0.0]);
    witness(domain, &[input]);
    let g = HalfSpaceOracle3::build(domain, &[input]).unwrap();
    let cell = &g.cells()[0];
    close(cell.volume, 24.0, 24.0);
    assert_eq!(g.faces().len(), 6);
    assert_eq!(cell.incidences.len(), 6);
    for a in 0..3 {
        close(input.position[a] + cell.centroid_offset[a], [0.0, -0.5, -1.0][a], 4.0);
        for b in 0..3 { close(cell.central_second_moment[a][b], if a == b { [8.0, 18.0, 32.0][a] } else { 0.0 }, 384.0); }
    }
    for face in g.faces() {
        let FaceKey3::Boundary { patch, .. } = face.key else { panic!("unexpected interior"); };
        let axis = patch.0 as usize / 2;
        let upper = patch.0 % 2 == 1;
        let expected_area = [12.0, 8.0, 6.0][axis];
        close(face.area, expected_area, expected_area);
        for a in 0..3 {
            close(face.normal[a], if a == axis { if upper { 1.0 } else { -1.0 } } else { 0.0 }, 1.0);
            let expected = if a == axis { domain.anchor[a] + if upper { domain.width[a] } else { 0.0 } }
                else { domain.anchor[a] + domain.width[a] / 2.0 };
            close(input.position[a] + face.centroid_offset[a], expected, 4.0);
        }
    }
}

#[test]
fn bounded_oblique_bisector() {
    assert!(PACKET.contains("bounded_oblique_bisector"));
    let domain = Domain3 { boundary: Boundary3::Bounded, ..periodic() };
    let input = [generator(7, 1, [0.25; 3]), generator(7, 2, [0.75; 3])];
    witness(domain, &input);
    let g = HalfSpaceOracle3::build(domain, &input).unwrap();
    assert_eq!(g.faces().len(), 13);
    assert_eq!(g.cells().iter().map(|c| c.incidences.len()).sum::<usize>(), 14);
    for (i, cell) in g.cells().iter().enumerate() {
        close(cell.volume, 0.5, 0.5);
        for a in 0..3 {
            close(cell.generator.position[a] + cell.centroid_offset[a], if i == 0 { 35.0 / 96.0 } else { 61.0 / 96.0 }, 1.0);
            for b in 0..3 {
                close(cell.central_second_moment[a][b], if a == b { 599.0 / 18432.0 } else { -169.0 / 18432.0 }, 0.5);
            }
        }
    }
    let face = g.faces().iter().find(|f| f.right.is_some()).unwrap();
    assert_eq!(face.polygon.len(), 6);
    let expected_area = 3.0 * 3.0_f64.sqrt() / 4.0;
    close(face.area, expected_area, expected_area);
    let expected_vertices = [[1.0, 0.5, 0.0], [0.5, 1.0, 0.0], [0.0, 1.0, 0.5], [0.0, 0.5, 1.0], [0.5, 0.0, 1.0], [1.0, 0.0, 0.5]];
    for point in &face.polygon {
        assert!(expected_vertices.iter().any(|v| (0..3).all(|a| (point[a] + 0.25 - v[a]).abs() <= TOL)));
    }
    for a in 0..3 {
        close(face.normal[a], 1.0 / 3.0_f64.sqrt(), 1.0);
        close(face.centroid_offset[a] + 0.25, 0.5, 1.0);
    }
    for f in g.faces().iter().filter(|f| f.right.is_none()) {
        let FaceKey3::Boundary { patch, .. } = f.key else { panic!("wall key"); };
        let lower_owner = f.left == 0;
        let min_patch = patch.0 % 2 == 0;
        let large = lower_owner == min_patch;
        let expected_area = if large { 7.0 / 8.0 } else { 1.0 / 8.0 };
        close(f.area, expected_area, expected_area);
        let tangent = match (lower_owner, min_patch) {
            (true, true) => 19.0 / 42.0, (true, false) => 1.0 / 6.0,
            (false, true) => 5.0 / 6.0, (false, false) => 23.0 / 42.0,
        };
        for a in 0..3 {
            let expected = if a == patch.0 as usize / 2 { if min_patch { 0.0 } else { 1.0 } } else { tangent };
            close(g.cells()[f.left as usize].generator.position[a] + f.centroid_offset[a], expected, 1.0);
        }
    }
}
