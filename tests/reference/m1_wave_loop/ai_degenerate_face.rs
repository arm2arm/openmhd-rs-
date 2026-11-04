//! Standalone AI-review observation. No solver fix or pass threshold is asserted.
//! A stationary tangential shear with nearly zero normal B has stable conservative
//! fluxes but a discontinuous selected HLLD state/normal-EMF completion at Bn=0.
use mhd_core::{IdealGas, Primitive, cross, riemann};
fn main() {
    let eos = IdealGas::new(5.0 / 3.0).unwrap();
    let normal = [0.0, -1.0, 0.0];
    let wf = [0.2, -0.1, 0.0];
    let aux = [0.21, -0.1, 0.04];
    for by in [-1e-12, -1e-18, 0.0, 1e-18, 1e-12] {
        let left = Primitive {
            density: 1.0,
            pressure: 1.0,
            velocity: [0.20168128073437985, -0.1, 0.04],
            magnetic: [0.0, by, -0.004562414995177748],
        };
        let right = Primitive {
            velocity: [0.19831871926562014, -0.1, 0.04],
            ..left
        };
        let f = riemann(eos, left, right, normal, wf).unwrap();
        let rev = riemann(eos, right, left, normal.map(|n| -n), wf).unwrap();
        let du = cross(aux, rev.magnetic);
        let source_reverse: [f64; 3] = std::array::from_fn(|k| rev.electromotive[k] - du[k]);
        let ux_b = cross(aux, f.magnetic);
        let a_face: [f64; 3] = std::array::from_fn(|k| f.electromotive[k] - ux_b[k]);
        println!("reversed orientation source={source_reverse:?}");
        println!(
            "By={by:.1e} Bn={:.1e} method={:?}\n  state_v={:?}\n  state_B={:?}\n  fluid_flux={:?}\n  numerical_EMF={:?}\n  EMF_minus_u_cross_B={a_face:?}",
            -by, f.method, f.velocity, f.magnetic, f.fluid, f.electromotive
        );
    }
}
