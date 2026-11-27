//! F5–F9 on the literal 27-generator map, with direct endpoint rebuilds.
use mhd_vector_pot::operators3::{MovingSharedFaceCurl3, SharedFaceCurl3};
use moving_mesh::three_d::{
    fit::{FitOrder3, SampleKey3},
    operator_mesh::{CellId, OperatorMesh3},
    *,
};
use std::collections::BTreeMap;
fn id(i: usize) -> CellId {
    SampleKey3::from_words(0x49, i as u64, Image3::ZERO).owner
}
fn jitter() -> Vec<Vec3> {
    include_str!("fixtures/m2c_shared_jitter.bits")
        .lines()
        .map(|line| {
            let v: Vec<_> = line
                .split_whitespace()
                .map(|word| f64::from_bits(u64::from_str_radix(word, 16).unwrap()))
                .collect();
            v.try_into().unwrap()
        })
        .collect()
}
fn velocity(i: usize) -> Vec3 {
    [
        ((7 * i + 3) % 13) as f64 - 6.,
        ((5 * i + 1) % 11) as f64 - 5.,
        ((3 * i + 2) % 17) as f64 - 8.,
    ]
    .map(|v| v / 128.)
}
fn sample(i: usize) -> Vec3 {
    [
        ((13 * i * i + 3 * i + 7) % 31) as f64 - 15.,
        ((5 * i * i + 17 * i + 3) % 37) as f64 - 18.,
        ((7 * i * i + 11 * i + 5) % 41) as f64 - 20.,
    ]
    .map(|v| v / 16.)
}
fn geometry(sites: &[Vec3], t: f64) -> SupportedGeometry3 {
    let generators: Vec<_> = sites
        .iter()
        .enumerate()
        .map(|(i, p)| Generator3 {
            id: id(i),
            position: std::array::from_fn(|k| p[k] + t * velocity(i)[k]),
            winding: Image3::ZERO,
        })
        .collect();
    HalfSpaceOracle3::build_supported_periodic(
        Domain3 {
            anchor: [0.; 3],
            width: [1.; 3],
            boundary: Boundary3::Periodic,
        },
        &generators,
    )
    .unwrap()
}
fn velocities(n: usize) -> BTreeMap<CellId, Vec3> {
    (0..n).map(|i| (id(i), velocity(i))).collect()
}
fn shape_branch(s: &SupportedGeometry3) -> Vec<(FaceKey3, Vec<Vec<VertexPlane3>>)> {
    let g = s.geometry();
    g.faces()
        .iter()
        .enumerate()
        .map(|(i, f)| {
            let mut active = s.vertex_supports(g.face_ref(i).unwrap()).unwrap().to_vec();
            for v in &mut active {
                v.sort();
            }
            active.sort();
            (f.key, active)
        })
        .collect()
}
fn fit_branch(s: &SupportedGeometry3) -> Vec<(usize, Vec<SampleKey3>)> {
    let m = OperatorMesh3::from_validated(s.geometry()).unwrap();
    (0..m.cells().len())
        .map(|i| {
            let fit = m.fit(i, FitOrder3::Quadratic).unwrap();
            (
                usize::from(fit.rings),
                fit.fit.samples().iter().map(|s| s.key).collect(),
            )
        })
        .collect()
}
fn reference_face(g: &ValidatedGeometry3, j: usize) -> [Vec3; 5] {
    let f = &g.faces()[j];
    let p = g.cells()[f.left as usize].generator.position;
    [
        f.normal.map(|v| v * f.area),
        std::array::from_fn(|k| p[k] + f.centroid_offset[k]),
        f.covariance[0],
        f.covariance[1],
        f.covariance[2],
    ]
}
fn normalized_difference(h: f64, minus: &[Vec3], plus: &[Vec3], rate: &[Vec3]) -> (f64, f64) {
    let mut error = 0.0_f64;
    let mut peak = 1.0_f64;
    let mut ulp_floor = 0.0_f64;
    for ((m, p), r) in minus
        .iter()
        .flatten()
        .zip(plus.iter().flatten())
        .zip(rate.iter().flatten())
    {
        error = error.max(((p - m) / (2. * h) - r).abs());
        peak = peak.max(r.abs());
        let spacing = |x: f64| {
            let v = x.abs();
            f64::from_bits(v.to_bits() + 1) - v
        };
        ulp_floor = ulp_floor.max((spacing(*m) + spacing(*p)) / (2. * h));
    }
    (error / peak, ulp_floor / peak)
}
// A transported, smooth periodic point sample in the laboratory frame.
fn transported(g: &ValidatedGeometry3, rates: Option<&MotionRates3>) -> (Vec<Vec3>, Vec<Vec3>) {
    let tau = std::f64::consts::TAU;
    g.cells()
        .iter()
        .enumerate()
        .map(|(i, c)| {
            let x: Vec3 =
                std::array::from_fn(|k| tau * (c.generator.position[k] + c.centroid_offset[k]));
            let v = rates
                .map(|r| r.cell(g.cell_ref(i).unwrap()).unwrap().centroid_velocity)
                .unwrap_or([0.; 3]);
            let a = std::array::from_fn(|k| x[(k + 1) % 3].sin() * x[(k + 2) % 3].cos());
            let da = std::array::from_fn(|k| {
                let j = (k + 1) % 3;
                let l = (k + 2) % 3;
                tau * (x[j].cos() * x[l].cos() * v[j] - x[j].sin() * x[l].sin() * v[l])
            });
            (a, da)
        })
        .unzip()
}
fn observation(label: &str, h: f64, lo: &[Vec3], hi: &[Vec3], rate: &[Vec3]) -> (f64, f64) {
    for (i, ((m, p), r)) in lo.iter().zip(hi).zip(rate).enumerate() {
        for k in 0..3 {
            println!(
                "ENDPOINT {label} {i} {k} {:.17e} {:.17e} {:.17e}",
                m[k], p[k], r[k]
            );
        }
    }
    normalized_difference(h, lo, hi, rate)
}
fn central(power: i32) {
    let h = 2.0_f64.powi(-power);
    let sites = jitter();
    let s = geometry(&sites, 0.);
    let lo = geometry(&sites, -h);
    let hi = geometry(&sites, h);
    let base = shape_branch(&s);
    let fits = fit_branch(&s);
    let branches = [shape_branch(&lo), base, shape_branch(&hi)];
    let stencils = [fit_branch(&lo), fits, fit_branch(&hi)];
    for (side, (faces, cells)) in branches.iter().zip(&stencils).enumerate() {
        for (i, (key, vertices)) in faces.iter().enumerate() {
            println!("FACE {side} {i} {key:?} {vertices:?}");
        }
        for (i, (ring, ring_samples)) in cells.iter().enumerate() {
            println!("STENCIL {side} {i} {ring} {ring_samples:?}");
        }
    }
    if branches[1] != branches[0]
        || branches[1] != branches[2]
        || stencils[1] != stencils[0]
        || stencils[1] != stencils[2]
    {
        println!("BRANCH {power} switched");
        return;
    }
    println!("BRANCH {power} matched");
    let m = PrescribedPolygonRates3::build(&s, &velocities(sites.len())).unwrap();
    let native = MovingSharedFaceCurl3::assemble(&s, &m).unwrap();
    let a: Vec<_> = (0..sites.len()).map(sample).collect();
    let minus = SharedFaceCurl3::from_validated(lo.geometry()).unwrap();
    let plus = SharedFaceCurl3::from_validated(hi.geometry()).unwrap();
    let q = native.apply(&s, &m, &a).unwrap();
    let low = minus.apply(&a).unwrap();
    let high = plus.apply(&a).unwrap();
    let mut groups = vec![("field", observation("field", h, &low, &high, &q))];
    let (potential, dadt) = transported(s.geometry(), Some(m.cells_and_faces()));
    let fixed = native.apply(&s, &m, &potential).unwrap();
    let transported_part = native.field().apply(&dadt).unwrap();
    let total: Vec<Vec3> = fixed
        .iter()
        .zip(&transported_part)
        .map(|(x, y)| std::array::from_fn(|k| x[k] + y[k]))
        .collect();
    let moved_low = minus.apply(&transported(lo.geometry(), None).0).unwrap();
    let moved_high = plus.apply(&transported(hi.geometry(), None).0).unwrap();
    groups.push((
        "transported",
        observation("transported", h, &moved_low, &moved_high, &total),
    ));
    let sensitivity = transported_part
        .iter()
        .flatten()
        .copied()
        .map(f64::abs)
        .fold(0., f64::max);
    println!("TRANSPORT {sensitivity:.17e}");
    assert!(sensitivity > 1e-3);
    let mut endpoint_low = [const { Vec::new() }; 5];
    let mut endpoint_high = [const { Vec::new() }; 5];
    let mut prediction = [const { Vec::new() }; 5];
    let mut min_det = 1.0_f64;
    for j in 0..s.geometry().faces().len() {
        let handle = s.geometry().face_ref(j).unwrap();
        let d = m.face(handle).unwrap();
        min_det = min_det.min(d.minimum_normalized_vertex_determinant.unwrap());
        let l = reference_face(lo.geometry(), j);
        let r = reference_face(hi.geometry(), j);
        let rate = [
            d.area_vector_rate,
            d.centroid_velocity,
            d.covariance_rate[0],
            d.covariance_rate[1],
            d.covariance_rate[2],
        ];
        for k in 0..5 {
            endpoint_low[k].push(l[k]);
            endpoint_high[k].push(r[k]);
            prediction[k].push(rate[k]);
        }
    }
    for (k, label) in ["area", "center", "cov0", "cov1", "cov2"]
        .into_iter()
        .enumerate()
    {
        groups.push((
            label,
            observation(
                label,
                h,
                &endpoint_low[k],
                &endpoint_high[k],
                &prediction[k],
            ),
        ));
    }
    println!("QUALITY {min_det:.17e}");
    let largest = groups.iter().map(|s| s.1.0).fold(0., f64::max);
    for (label, (err, ulp)) in groups {
        println!("DIFF {power} {label} {err:.17e} {ulp:.17e}");
        assert!(err.is_finite() && ulp.is_finite());
    }
    if power == 13 {
        assert!(largest <= 1e-7, "finest scaled error {largest:.17e}");
    }
}
macro_rules! halves {($($name:ident:$p:literal),+) => {$(#[test] fn $name(){central($p);})+};}
halves!(h128:7,h256:8,h512:9,h1024:10,h2048:11,h4096:12,h8192:13);

#[test]
fn periodic_mean_adjoint_and_constants() {
    let sites = jitter();
    let n = sites.len();
    let s = geometry(&sites, 0.);
    let g = s.geometry();
    let m = PrescribedPolygonRates3::build(&s, &velocities(n)).unwrap();
    let tangent = MovingSharedFaceCurl3::assemble(&s, &m).unwrap();
    let a: Vec<_> = (0..n).map(sample).collect();
    let y: Vec<_> = (0..n).map(|i| sample((i + 3) % n)).collect();
    let b = tangent.field().apply(&a).unwrap();
    let bd = tangent.apply(&s, &m, &a).unwrap();
    let ct = tangent.transpose(&s, &m, &y).unwrap();
    let bilinear = |a: &[Vec3], b: &[Vec3]| {
        a.iter()
            .flatten()
            .zip(b.iter().flatten())
            .map(|(x, y)| x * y)
            .sum::<f64>()
    };
    let l = bilinear(&y, &bd);
    let r = bilinear(&ct, &a);
    let adj = (l - r).abs() / l.abs().max(r.abs()).max(1.);
    let zero = tangent
        .apply(&s, &m, &vec![[2., -3., 5.]; n])
        .unwrap()
        .iter()
        .flatten()
        .copied()
        .map(f64::abs)
        .fold(0., f64::max);
    let mut budget = [0.; 3];
    for (i, c) in g.cells().iter().enumerate() {
        let v = m
            .cells_and_faces()
            .cell(g.cell_ref(i).unwrap())
            .unwrap()
            .volume_rate;
        for (k, d) in budget.iter_mut().enumerate() {
            *d += v * b[i][k] + c.volume * bd[i][k];
        }
    }
    let flux = budget.into_iter().map(f64::abs).fold(0., f64::max);
    println!("IDENTITIES {adj:.17e} {zero:.17e} {flux:.17e}");
    assert!(adj <= 1e-12 && zero <= 1e-12 && flux <= 1e-12);
    let other = geometry(&sites, 0.);
    assert!(tangent.apply(&other, &m, &a).is_err());
}
#[test]
fn rigid_self_faces_and_degenerate_nonrigid_vertex() {
    let s = geometry(&[[0.5; 3]], 0.);
    let velocity = [0.25, -0.5, 1.];
    let w = [(id(0), velocity)].into_iter().collect();
    let m = PrescribedPolygonRates3::build(&s, &w).unwrap();
    for j in 0..s.geometry().faces().len() {
        let f = m.face(s.geometry().face_ref(j).unwrap()).unwrap();
        assert_eq!(f.centroid_velocity, velocity);
        assert_eq!(f.area_vector_rate, [0.; 3]);
        assert_eq!(f.covariance_rate, [[0.; 3]; 3]);
    }
    let native = MovingSharedFaceCurl3::assemble(&s, &m).unwrap();
    assert_eq!(native.apply(&s, &m, &[sample(0)]).unwrap(), [[0.; 3]]);
    let cube: Vec<_> = (0..8)
        .map(|i| std::array::from_fn(|k| if (i >> k) & 1 == 0 { 0.25 } else { 0.75 }))
        .collect();
    let cubic = geometry(&cube, 0.);
    assert!(matches!(
        PrescribedPolygonRates3::build(&cubic, &velocities(8)),
        Err(GeometryError3::InvalidTopology(
            "non-simple moving periodic vertex"
        ))
    ));
}
