//! Derivative of the physical gradient weights on a fixed quadratic stencil.
use super::{FitError3, FitOrder3, PointFit3, Vec3, basis, length};

type Basis = [f64; 10];

fn inner(a: &Basis, b: &Basis) -> f64 {
    a.iter().zip(b).map(|(a, b)| a * b).sum()
}

struct SampleRate {
    x: Basis,
    dx: Basis,
    w: f64,
    dw: f64,
}

impl PointFit3 {
    // Solve XᵀWX z = rhs through the existing scaled, pivoted QR. The
    // returned vector and rhs both belong to the unnormalized polynomial basis.
    fn solve_quadratic_dual(&self, rhs: Basis) -> Basis {
        let p = &self.quality.permutation;
        let scales = &self.quality.scales;
        let r = &self.triangular;
        let mut v = [0.; 10];
        for (k, &column) in p.iter().enumerate() {
            let previous: f64 = v[..k].iter().zip(r).map(|(v, row)| v * row[k]).sum();
            v[k] = (rhs[column] / scales[column] - previous) / r[k][k];
        }
        let mut out = [0.; 10];
        for (k, &column) in p.iter().enumerate().rev() {
            let upper: f64 = r[k][k + 1..]
                .iter()
                .zip(&v[k + 1..])
                .map(|(r, v)| r * v)
                .sum();
            v[k] = (v[k] - upper) / r[k][k];
            out[column] = v[k] / scales[column];
        }
        out
    }

    /// For each sorted owner/image sample, return the time derivative of its
    /// three physical gradient coefficients, acting on sample-minus-baseline
    /// values. Supply centroid-relative velocities and Vdot/V at this epoch.
    pub fn quadratic_gradient_rate(
        &self,
        relative_velocities: &[Vec3],
        relative_volume_rate: f64,
    ) -> Result<Vec<Vec3>, FitError3> {
        if self.order != FitOrder3::Quadratic
            || relative_velocities.len() != self.samples.len()
            || !relative_volume_rate.is_finite()
            || !relative_velocities.iter().flatten().all(|v| v.is_finite())
        {
            return Err(FitError3::InvalidSample);
        }
        let h = self.quality.h;
        let dilation = relative_volume_rate / 3.;
        let rows: Vec<_> = self
            .samples
            .iter()
            .zip(relative_velocities)
            .zip(&self.weights)
            .map(|((s, v), sw)| {
                let d = s.displacement;
                let radius = length(&d);
                let u = d.map(|d| d / h);
                let [x, y, z] = u;
                let [vx, vy, vz] = std::array::from_fn(|k| v[k] / h - u[k] * dilation);
                let w = sw * sw;
                let log_weight_rate: f64 = d
                    .iter()
                    .zip(v)
                    .map(|(d, v)| -(d / radius) * (v / radius))
                    .sum();
                SampleRate {
                    x: basis(u),
                    dx: [
                        0.,
                        vx,
                        vy,
                        vz,
                        x * vx,
                        y * vy,
                        z * vz,
                        vx * y + x * vy,
                        vx * z + x * vz,
                        vy * z + y * vz,
                    ],
                    w,
                    dw: w * log_weight_rate,
                }
            })
            .collect();
        let mut result = vec![[0.; 3]; rows.len()];
        for axis in 0..3 {
            let mut select = [0.; 10];
            select[1 + axis] = 1.;
            let z = self.solve_quadratic_dual(select);
            // N z' = -N' z. Apply both X' terms as well as W' directly
            // to z, including the residual contribution for non-polynomial data.
            let mut rhs = [0.; 10];
            for r in &rows {
                let xz = inner(&r.x, &z);
                let factor = r.dw * xz + r.w * inner(&r.dx, &z);
                for (j, v) in rhs.iter_mut().enumerate() {
                    *v -= r.dx[j] * r.w * xz + r.x[j] * factor;
                }
            }
            let dz = self.solve_quadratic_dual(rhs);
            for (j, (r, gradient)) in rows.iter().zip(&mut result).enumerate() {
                let derivative =
                    r.dw * inner(&r.x, &z) + r.w * (inner(&r.dx, &z) + inner(&r.x, &dz));
                gradient[axis] = derivative / h - dilation * self.map[axis + 1][j];
            }
        }
        if result.iter().flatten().all(|v| v.is_finite()) {
            Ok(result)
        } else {
            Err(FitError3::NonFinite)
        }
    }
}
