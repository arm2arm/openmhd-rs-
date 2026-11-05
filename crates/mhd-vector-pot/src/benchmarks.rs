//! Deterministic M0-packet initial states and analytic *physical* references.
//! A(t)/phi(t) are gauge dependent; only the initial Alfven potential is prescribed.
use crate::general::Initial;
use mhd_core::{Primitive, Vec3};
use moving_mesh::Vec2;
use std::f64::consts::{PI, TAU};

pub const ALFVEN_AMPLITUDE: f64 = 0.1;
pub fn loop_amplitude() -> f64 {
    0.001 / (4. * PI).sqrt()
}

/// Corrected R1 potential at t=0, not the inconsistent printed potential.
/// Caller supplies finite positions, parallel velocity and boost.
/// Requires Config::mean_magnetic=[1,0,0]; physical units and EOS follow the M1 packet.
pub fn alfven_initial(position: Vec2, parallel: f64, boost: Vec3) -> Initial {
    let q = alfven_exact(position, 0., parallel, boost);
    let phase = TAU * position[0];
    Initial {
        density: q.density,
        pressure: q.pressure,
        velocity: q.velocity,
        potential: [
            0.,
            ALFVEN_AMPLITUDE / TAU * phase.sin(),
            ALFVEN_AMPLITUDE / TAU * phase.cos(),
        ],
        phi: 0.,
    }
}
/// Analytic travelling/standing circularly polarized wave; no exact A/phi claim.
pub fn alfven_exact(position: Vec2, time: f64, parallel: f64, boost: Vec3) -> Primitive {
    let phase = TAU * (position[0] + (1. - parallel - boost[0]) * time);
    let transverse = [
        ALFVEN_AMPLITUDE * phase.sin(),
        ALFVEN_AMPLITUDE * phase.cos(),
    ];
    Primitive {
        density: 1.,
        pressure: 0.1,
        velocity: [
            parallel + boost[0],
            transverse[0] + boost[1],
            transverse[1] + boost[2],
        ],
        magnetic: [1., transverse[0], transverse[1]],
    }
}
/// Prescribed-flow loop transport reference, not an exact coupled MHD solution.
/// At the cusp r=0 and edge r=.3 the analytic derivative is undefined.
/// Returns zero B there as a placeholder; exclude those points from B error norms.
pub fn passive_loop(position: Vec2, time: f64, velocity: Vec3) -> (f64, Vec3) {
    let d: Vec2 = std::array::from_fn(|k| (position[k] - velocity[k] * time).rem_euclid(1.) - 0.5);
    let r = d[0].hypot(d[1]);
    let amplitude = loop_amplitude();
    let a = amplitude * (0.3 - r).max(0.);
    let b = if r > 0. && r < 0.3 {
        [-amplitude * d[1] / r, amplitude * d[0] / r, 0.]
    } else {
        [0.; 3]
    };
    (a, b)
}
pub fn loop_initial(position: Vec2, boost: Vec3) -> Initial {
    let velocity = [2. + boost[0], 1. + boost[1], boost[2]];
    Initial {
        density: 1.,
        pressure: 1.,
        velocity,
        potential: [0., 0., passive_loop(position, 0., velocity).0],
        phi: 0.,
    }
}

/// Periodic Brio-Wu strip: gamma=2, L=(2,.125), mean B=(.75,0,0).
/// The second discontinuity is at the periodic boundary, outside the comparison window.
pub fn brio_initial(position: Vec2, boost: Vec3) -> Initial {
    let x = position[0].rem_euclid(2.);
    let left = x < 1.;
    Initial {
        density: if left { 1. } else { 0.125 },
        pressure: if left { 1. } else { 0.1 },
        velocity: boost,
        potential: [0., 0., if left { -x } else { x - 2. }],
        phi: 0.,
    }
}
/// Orszag-Tang packet in a periodic unit square, gamma=5/3, mean B=0.
pub fn vortex_initial(position: Vec2, boost: Vec3) -> Initial {
    let [x, y] = position.map(|x| TAU * x);
    Initial {
        density: 25. / (36. * PI),
        pressure: 5. / (12. * PI),
        velocity: [-y.sin() + boost[0], x.sin() + boost[1], boost[2]],
        potential: [
            0.,
            0.,
            (y.cos() / TAU + (2. * x).cos() / (2. * TAU)) / (4. * PI).sqrt(),
        ],
        phi: 0.,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn wave_reference_sign_period_and_joint_boost() {
        for parallel in [0., 1.] {
            for x in [0., 0.137, 0.5] {
                let q = alfven_exact([x, 0.3], 0., parallel, [0.; 3]);
                let same = alfven_exact([x, 0.3], 1., parallel, [0.; 3]);
                for k in 0..3 {
                    assert!((q.magnetic[k] - same.magnetic[k]).abs() < 1e-14);
                }
                let t = 0.13;
                let b = [2., -1., 0.8];
                let a = alfven_exact([x, 0.3], t, parallel, [0.; 3]);
                let boosted = alfven_exact([x + b[0] * t, 0.3 + b[1] * t], t, parallel, b);
                for (k, shift) in b.iter().enumerate() {
                    assert!((a.velocity[k] - boosted.velocity[k] + shift).abs() < 1e-14);
                    assert!((a.magnetic[k] - boosted.magnetic[k]).abs() < 1e-14);
                }
                // Independent central differences of initial A verify B_y=-Dx A_z, B_z=Dx A_y.
                let h = 1e-6;
                let l = alfven_initial([x - h, 0.3], parallel, [0.; 3]);
                let r = alfven_initial([x + h, 0.3], parallel, [0.; 3]);
                assert!(
                    (-(r.potential[2] - l.potential[2]) / (2. * h) - q.magnetic[1]).abs() < 1e-10
                );
                assert!(
                    ((r.potential[1] - l.potential[1]) / (2. * h) - q.magnetic[2]).abs() < 1e-10
                );
            }
        }
    }
    #[test]
    fn loop_reference_sign_support_and_periodic_translation() {
        let v = [2., 1., 0.];
        let a = loop_amplitude();
        let (az, b) = passive_loop([0.6, 0.5], 0., v);
        assert!((az - 0.2 * a).abs() < 1e-16);
        assert!((b[1] - a).abs() < 1e-16);
        assert_eq!(b[0], 0.);
        assert_eq!(passive_loop([0.9, 0.5], 0., v), (0., [0.; 3]));
        let moved = passive_loop([0.6 + v[0] * 0.7, 0.5 + v[1] * 0.7], 0.7, v);
        assert!((moved.0 - az).abs() < 1e-16);
        for (value, expected) in moved.1.iter().zip(b) {
            assert!((value - expected).abs() < 1e-16);
        }
        let centre = passive_loop([0.5, 0.5], 0., v);
        assert!(centre.0.is_finite());
        assert_eq!(centre.1, [0.; 3]);
    }
}
