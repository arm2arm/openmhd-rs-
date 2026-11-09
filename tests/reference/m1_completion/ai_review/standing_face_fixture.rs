//! Actual N64 regular standing-wave face 461 at t=1e-4, after one common-dt
//! step (dt=1e-4) of the historical profile, fixed base / rigid boost (2,-1,0).
//! Extracted by standing_faces.rs, not a manufactured arbitrary state.
use mhd_core::{FaceCompletion, IdealGas, Primitive, Vec3, cross, riemann_with_completion};
fn q(a: [f64; 8], boost: Vec3) -> Primitive {
    Primitive {
        density: a[0],
        velocity: [a[1] + boost[0], a[2] + boost[1], a[3] + boost[2]],
        pressure: a[4],
        magnetic: [a[5], a[6], a[7]],
    }
}
fn main() {
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
            q(base[0], zero),
            q(base[1], zero),
            [1., 0., 0.],
            zero,
            completion,
        )
        .unwrap();
        let b = riemann_with_completion(
            eos,
            q(boosted_rest[0], boost),
            q(boosted_rest[1], boost),
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
        for k in 0..3 {
            fluid[k + 1] -= boost[k] * fluid[0];
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
