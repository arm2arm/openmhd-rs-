//! Additional independently named static controls. All unexecuted locally.
use galaxy_types::{CellId, EntityId};
use moving_mesh::three_d::*;

fn generator(counter: u64, position: Vec3) -> Generator3 {
    Generator3 { id: CellId::new(EntityId::new(23, counter)), position, winding: Image3::ZERO }
}
fn domain(boundary: Boundary3) -> Domain3 { Domain3 { anchor: [0.0; 3], width: [1.0; 3], boundary } }
fn close(value: f64, expected: f64, scale: f64) {
    assert!(value.is_finite() && expected.is_finite() && scale.is_finite() && scale > 0.0);
    assert!((value - expected).abs() <= 1e-10 * scale, "{value:e} != {expected:e}, scale {scale:e}");
}

fn oblique_transform(permutation: [usize; 3], length: f64, translation: Vec3) {
    // R10, BOUNDARY_MHD_DESIGN_REVIEW findings 11-12; all permutations leave
    // this symmetric input unchanged but odd permutations still test winding.
    // The anisotropic cuboid control below separately distinguishes axes.
    let input = [generator(1, [0.25; 3]), generator(2, [0.75; 3])].map(|mut g| {
        g.position = std::array::from_fn(|a| length * g.position[permutation[a]] + translation[a]); g
    });
    let d = Domain3 { anchor: translation, width: [length; 3], boundary: Boundary3::Bounded };
    println!("domain bits {:?} {:?}", d.anchor.map(f64::to_bits), d.width.map(f64::to_bits));
    for g in input { println!("{} {:?}", g.id.entity(), g.position.map(f64::to_bits)); }
    let g = HalfSpaceOracle3::build(d, &input).unwrap();
    assert_eq!(g.faces().len(), 13);
    for (i, cell) in g.cells().iter().enumerate() {
        let expected_volume = length.powi(3) / 2.0;
        close(cell.volume, expected_volume, expected_volume);
        for a in 0..3 {
            let expected_c = length * if i == 0 { 35.0 / 96.0 } else { 61.0 / 96.0 } + translation[a];
            close(cell.generator.position[a] + cell.centroid_offset[a], expected_c, length);
            for b in 0..3 {
                let base = if a == b { 599.0 / 18432.0 } else { -169.0 / 18432.0 };
                close(cell.central_second_moment[a][b], length.powi(5) * base, expected_volume * length * length);
            }
        }
    }
    let shared = g.faces().iter().find(|f| f.right.is_some()).unwrap();
    let expected_area = length * length * 3.0 * 3.0_f64.sqrt() / 4.0;
    close(shared.area, expected_area, expected_area);
    for k in 1..shared.polygon.len() - 1 {
        let a = shared.polygon[0];
        let b = shared.polygon[k];
        let c = shared.polygon[k + 1];
        let u: Vec3 = std::array::from_fn(|j| b[j] - a[j]);
        let v: Vec3 = std::array::from_fn(|j| c[j] - a[j]);
        let oriented = (u[1] * v[2] - u[2] * v[1]) * shared.normal[0]
            + (u[2] * v[0] - u[0] * v[2]) * shared.normal[1]
            + (u[0] * v[1] - u[1] * v[0]) * shared.normal[2];
        assert!(oriented > 0.0);
    }
}

#[test]
fn oblique_scale_one_millionth() { oblique_transform([0, 1, 2], 1e-6, [0.0; 3]); }
#[test]
fn oblique_scale_one_million() { oblique_transform([0, 1, 2], 1e6, [0.0; 3]); }
#[test]
fn oblique_nonzero_anchor() { oblique_transform([0, 1, 2], 1.0, [0.371, -0.219, 0.443]); }

fn cuboid_permutation(p: [usize; 3]) {
    let original_anchor = [-1.0, -2.0, -3.0];
    let original_width = [2.0, 3.0, 4.0];
    let original_generator = [0.25, -1.0, 0.0];
    let original_centroid = [0.0, -0.5, -1.0];
    let original_j = [8.0, 18.0, 32.0];
    let d = Domain3 { anchor: p.map(|a| original_anchor[a]), width: p.map(|a| original_width[a]), boundary: Boundary3::Bounded };
    let input = generator(1, p.map(|a| original_generator[a]));
    let g = HalfSpaceOracle3::build(d, &[input]).unwrap();
    close(g.cells()[0].volume, 24.0, 24.0);
    for a in 0..3 {
        close(input.position[a] + g.cells()[0].centroid_offset[a], original_centroid[p[a]], 4.0);
        for b in 0..3 { close(g.cells()[0].central_second_moment[a][b], if a == b { original_j[p[a]] } else { 0.0 }, 384.0); }
    }
    assert_eq!(g.faces().len(), 6);
    for f in g.faces() {
        let FaceKey3::Boundary { patch, .. } = f.key else { panic!("bounded patch"); };
        let a = patch.0 as usize / 2;
        let expected_area = 24.0 / original_width[p[a]];
        close(f.area, expected_area, expected_area);
    }
}

#[test]
fn cuboid_permutation_xyz() { cuboid_permutation([0, 1, 2]); }
#[test]
fn cuboid_permutation_xzy() { cuboid_permutation([0, 2, 1]); }
#[test]
fn cuboid_permutation_yxz() { cuboid_permutation([1, 0, 2]); }
#[test]
fn cuboid_permutation_yzx() { cuboid_permutation([1, 2, 0]); }
#[test]
fn cuboid_permutation_zxy() { cuboid_permutation([2, 0, 1]); }
#[test]
fn cuboid_permutation_zyx() { cuboid_permutation([2, 1, 0]); }

#[test]
fn input_permutation_is_canonical() {
    let input = [generator(9, [0.25; 3]), generator(2, [0.75; 3])];
    let a = HalfSpaceOracle3::build(domain(Boundary3::Bounded), &input).unwrap();
    let b = HalfSpaceOracle3::build(domain(Boundary3::Bounded), &[input[1], input[0]]).unwrap();
    assert_ne!(a.epoch(), b.epoch());
    for (x, y) in a.cells().iter().zip(b.cells()) {
        assert_eq!(x.generator, y.generator);
        assert_eq!(x.volume.to_bits(), y.volume.to_bits());
        assert_eq!(x.centroid_offset.map(f64::to_bits), y.centroid_offset.map(f64::to_bits));
        assert_eq!(x.central_second_moment.map(|r| r.map(f64::to_bits)), y.central_second_moment.map(|r| r.map(f64::to_bits)));
    }
    for (x, y) in a.faces().iter().zip(b.faces()) {
        assert_eq!(x.key, y.key);
        assert_eq!(x.polygon, y.polygon);
        assert_eq!(x.area.to_bits(), y.area.to_bits());
    }
}

#[test]
fn periodic_owner_image_reciprocity_and_unequal_windings() {
    let mut input = Vec::new();
    for z in [0.25, 0.75] { for y in [0.25, 0.75] { for x in [0.25, 0.75] {
        let mut g = generator(input.len() as u64, [x, y, z]);
        g.winding = Image3([3 * input.len() as i64 - 8, -7, 11]);
        input.push(g);
    } } }
    let g = HalfSpaceOracle3::build(domain(Boundary3::Periodic), &input).unwrap();
    assert_eq!(g.faces().len(), 24);
    for (index, face) in g.faces().iter().enumerate() {
        let FaceKey3::Interior { lo, hi, hi_image } = face.key else { panic!("periodic key"); };
        let left = &g.cells()[face.left as usize];
        let right = &g.cells()[face.right.unwrap() as usize];
        assert_eq!(left.generator.id, lo);
        assert_eq!(right.generator.id, hi);
        let a = left.incidences.iter().find(|i| i.face as usize == index && i.sign == 1).unwrap();
        let b = right.incidences.iter().find(|i| i.face as usize == index && i.sign == -1).unwrap();
        assert_eq!(a.neighbour, Some((hi, hi_image)));
        assert_eq!(b.neighbour, Some((lo, hi_image.checked_neg().unwrap())));
        for axis in 0..3 {
            assert_eq!(hi_image.0[axis], face.right_wrapped_image.0[axis] + left.generator.winding.0[axis] - right.generator.winding.0[axis]);
            let d = right.generator.position[axis] + face.right_wrapped_image.0[axis] as f64 - left.generator.position[axis];
            close(b.chart_translation[axis], -d, 1.0);
        }
    }
    // Three neighbour IDs, six full image incidences, not three merged faces.
    for cell in g.cells() {
        let ids: std::collections::BTreeSet<_> = cell.incidences.iter().map(|i| i.neighbour.unwrap().0).collect();
        let images: std::collections::BTreeSet<_> = cell.incidences.iter().map(|i| i.neighbour.unwrap()).collect();
        assert_eq!(ids.len(), 3);
        assert_eq!(images.len(), 6);
    }
}

#[test]
fn epoch_handles_reject_cross_geometry_use() {
    let input = [generator(1, [0.25; 3])];
    let a = HalfSpaceOracle3::build(domain(Boundary3::Periodic), &input).unwrap();
    let b = HalfSpaceOracle3::build(domain(Boundary3::Periodic), &input).unwrap();
    assert!(a.cell(a.cell_ref(0).unwrap()).is_ok());
    assert!(a.face(a.face_ref(0).unwrap()).is_ok());
    assert_eq!(a.cell_by_id(input[0].id), Some(a.cell_ref(0).unwrap()));
    assert_eq!(a.cell_by_id(generator(2, [0.25; 3]).id), None);
    assert_eq!(b.cell(a.cell_ref(0).unwrap()).unwrap_err(), GeometryError3::EpochMismatch);
    assert_eq!(b.face(a.face_ref(0).unwrap()).unwrap_err(), GeometryError3::EpochMismatch);
    assert_eq!(a.cell_ref(1).unwrap_err(), GeometryError3::InvalidLocalIndex);
    assert_eq!(a.face_ref(3).unwrap_err(), GeometryError3::InvalidLocalIndex);
}

#[test]
fn invalid_domains_and_empty_catalog_reject() {
    let input = [generator(1, [0.25; 3])];
    for width in [[0.0, 1.0, 1.0], [-1.0, 1.0, 1.0], [f64::NAN, 1.0, 1.0], [1.0, f64::INFINITY, 1.0]] {
        assert_eq!(HalfSpaceOracle3::build(Domain3 { width, ..domain(Boundary3::Periodic) }, &input).unwrap_err(), GeometryError3::InvalidDomain);
    }
    assert_eq!(HalfSpaceOracle3::build(domain(Boundary3::Periodic), &[]).unwrap_err(), GeometryError3::EmptyCatalog);
    let too_many = vec![input[0]; 513];
    assert_eq!(HalfSpaceOracle3::build(domain(Boundary3::Periodic), &too_many).unwrap_err(), GeometryError3::TooManyGenerators { count: 513, limit: 512 });
}

#[test]
fn invalid_catalog_identity_finiteness_and_domain_reject() {
    let d = domain(Boundary3::Periodic);
    let input = generator(0, [0.25; 3]); // zero payload counter is representable
    let zero = Generator3 { id: CellId::new(EntityId::new(0, 0)), ..input };
    assert!(HalfSpaceOracle3::build(d, &[zero]).is_ok());
    assert!(HalfSpaceOracle3::build(d, &[input]).is_ok());
    assert_eq!(HalfSpaceOracle3::build(d, &[input, input]).unwrap_err(), GeometryError3::DuplicateId { id: input.id });
    let coincident = generator(1, input.position);
    assert_eq!(HalfSpaceOracle3::build(d, &[input, coincident]).unwrap_err(), GeometryError3::CoincidentGenerators { first: input.id, second: coincident.id });
    let bad = generator(1, [f64::NAN, 0.25, 0.25]);
    assert_eq!(HalfSpaceOracle3::build(d, &[bad]).unwrap_err(), GeometryError3::NonFiniteGenerator { id: bad.id });
    for x in [-0.25, 1.0] {
        let bad = generator(1, [x, 0.25, 0.25]);
        assert_eq!(HalfSpaceOracle3::build(d, &[bad]).unwrap_err(), GeometryError3::GeneratorOutside { id: bad.id });
    }
    let wall = generator(1, [0.0, 0.25, 0.25]);
    assert_eq!(HalfSpaceOracle3::build(domain(Boundary3::Bounded), &[wall]).unwrap_err(), GeometryError3::GeneratorOutside { id: wall.id });
    let mut winding = generator(1, [0.25; 3]);
    winding.winding = Image3([1, 0, 0]);
    assert_eq!(HalfSpaceOracle3::build(domain(Boundary3::Bounded), &[winding]).unwrap_err(), GeometryError3::BoundedWinding { id: winding.id });
}

#[test]
fn image_overflow_rejects_without_partial_geometry() {
    let mut a = generator(1, [0.25; 3]);
    let mut b = generator(2, [0.75; 3]);
    a.winding = Image3([i64::MAX, 0, 0]);
    b.winding = Image3([i64::MIN, 0, 0]);
    assert_eq!(HalfSpaceOracle3::build(domain(Boundary3::Periodic), &[a, b]).unwrap_err(), GeometryError3::ImageOverflow);
    assert_eq!(Image3([i64::MIN, 0, 0]).checked_neg().unwrap_err(), GeometryError3::ImageOverflow);
}

#[test]
fn equal_extreme_windings_do_not_overflow_intermediate_arithmetic() {
    let mut input = generator(1, [0.25; 3]);
    input.winding = Image3([i64::MAX, i64::MIN, i64::MAX]);
    let g = HalfSpaceOracle3::build(domain(Boundary3::Periodic), &[input]).unwrap();
    assert_eq!(g.faces().len(), 3);
    assert_eq!(g.cells()[0].incidences.len(), 6);
}

#[test]
fn unrepresentable_physical_moment_scale_rejects() {
    let d = Domain3 { width: [1e100; 3], ..domain(Boundary3::Periodic) };
    let input = [generator(1, [2.5e99; 3])];
    assert_eq!(HalfSpaceOracle3::build(d, &input).unwrap_err(), GeometryError3::Unrepresentable("physical moment scales"));
}
