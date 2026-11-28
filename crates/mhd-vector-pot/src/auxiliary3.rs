//! Static periodic tensor-Hermite velocity; all corner jets are shared.
use crate::auxiliary::spline_weights;
use moving_mesh::three_d::{Tensor3, Vec3, operator_mesh::CellId};
#[derive(Clone, Copy, Debug)]
pub struct CornerJet3 {
    /// Bit 0 differentiates x, bit 1 y, bit 2 z. Slot zero is the value.
    pub derivatives: [Vec3; 8],
}
#[derive(Clone, Copy, Debug)]
pub struct Velocity3 {
    pub value: Vec3,
    pub jacobian: Tensor3,
}
#[derive(Debug, PartialEq, Eq)]
pub enum AuxiliaryError3 {
    InvalidInput,
    DuplicateOwner,
    AuxiliaryTransitionUnresolved,
    NonFinite,
}
impl std::fmt::Display for AuxiliaryError3 {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}
impl std::error::Error for AuxiliaryError3 {}

fn basis(t: f64, h: f64) -> ([[f64; 2]; 2], [[f64; 2]; 2]) {
    let s = t * t;
    let c = s * t;
    (
        [
            [2. * c - 3. * s + 1., h * (c - 2. * s + t)],
            [-2. * c + 3. * s, h * (c - s)],
        ],
        [
            [(6. * s - 6. * t) / h, 3. * s - 4. * t + 1.],
            [(-6. * s + 6. * t) / h, 3. * s - 2. * t],
        ],
    )
}
/// Evaluate a cell polynomial. Corner indices are x + 2*y + 4*z.
pub fn interpolate_cell(
    corners: &[CornerJet3; 8],
    spacing: Vec3,
    fraction: Vec3,
) -> Result<Velocity3, AuxiliaryError3> {
    if !spacing.into_iter().all(|x| x.is_finite() && x > 0.)
        || !fraction.into_iter().all(|x| (0.0..=1.0).contains(&x))
    {
        return Err(AuxiliaryError3::InvalidInput);
    }
    let b: [_; 3] = std::array::from_fn(|i| basis(fraction[i], spacing[i]));
    let mut result = Velocity3 {
        value: [0.; 3],
        jacobian: [[0.; 3]; 3],
    };
    for (corner, jet) in corners.iter().enumerate() {
        for (mask, d) in jet.derivatives.iter().enumerate() {
            let v: Vec3 = std::array::from_fn(|i| b[i].0[(corner >> i) & 1][(mask >> i) & 1]);
            let g: Vec3 = std::array::from_fn(|i| {
                b[i].1[(corner >> i) & 1][(mask >> i) & 1] * v[(i + 1) % 3] * v[(i + 2) % 3]
            });
            for (k, &u) in d.iter().enumerate() {
                result.value[k] += v[0] * v[1] * v[2] * u;
                for (j, &dg) in g.iter().enumerate() {
                    result.jacobian[k][j] += dg * u;
                }
            }
        }
    }
    if !result
        .value
        .into_iter()
        .chain(result.jacobian.into_iter().flatten())
        .all(f64::is_finite)
    {
        return Err(AuxiliaryError3::NonFinite);
    }
    Ok(result)
}
#[derive(Clone, Copy, Debug)]
pub struct VelocitySample3 {
    pub id: CellId,
    pub position: Vec3,
    pub volume: f64,
    pub velocity: Vec3,
}
#[derive(Debug)]
pub struct Deposition3 {
    pub intervals: usize,
    pub counts: Vec<usize>,
    pub normalizers: Vec<f64>,
    pub max_cell_volumes: Vec<f64>,
}
#[derive(Debug)]
pub struct SmoothVelocity3 {
    lengths: Vec3,
    origin: Vec3,
    intervals: usize,
    corners: Vec<CornerJet3>,
    pub attempts: Vec<Deposition3>,
}
fn index(q: [usize; 3], n: usize) -> usize {
    q[0] + n * (q[1] + n * q[2])
}
fn differences(values: &[Vec3], n: usize, h: Vec3) -> Vec<CornerJet3> {
    let mut jets: Vec<_> = values
        .iter()
        .map(|&v| {
            let mut derivatives = [[0.; 3]; 8];
            derivatives[0] = v;
            CornerJet3 { derivatives }
        })
        .collect();
    for (axis, &spacing) in h.iter().enumerate() {
        let stride = n.pow(axis as u32);
        for mask in 0..(1 << axis) {
            let values = moving_mesh::parallel::map(jets.len(), |i| {
                let pos = (i / stride) % n;
                let base = i - pos * stride;
                let plus = jets[base + ((pos + 1) % n) * stride].derivatives[mask];
                let minus = jets[base + ((pos + n - 1) % n) * stride].derivatives[mask];
                std::array::from_fn(|k| (plus[k] - minus[k]) / (2. * spacing))
            });
            for (jet, value) in jets.iter_mut().zip(values) {
                jet.derivatives[mask | (1 << axis)] = value;
            }
        }
    }
    jets
}
impl SmoothVelocity3 {
    pub fn deposit(
        lengths: Vec3,
        origin: Vec3,
        samples: &[VelocitySample3],
        root: usize,
    ) -> Result<Self, AuxiliaryError3> {
        if !lengths.into_iter().all(|x| x.is_finite() && x > 0.)
            || !origin.into_iter().all(f64::is_finite)
            || ![1, 2, 4].contains(&root)
            || samples.iter().any(|s| {
                !s.volume.is_finite()
                    || s.volume <= 0.
                    || !s.velocity.into_iter().chain(s.position).all(f64::is_finite)
            })
        {
            return Err(AuxiliaryError3::InvalidInput);
        }
        let mut by_id: Vec<_> = samples.iter().collect();
        by_id.sort_by_key(|s| s.id);
        if by_id.windows(2).any(|w| w[0].id == w[1].id) {
            return Err(AuxiliaryError3::DuplicateOwner);
        }
        let total: f64 = by_id.iter().map(|s| s.volume).sum();
        if !total.is_finite() {
            return Err(AuxiliaryError3::NonFinite);
        }
        let mut attempts = Vec::new();
        for n in [4_usize, 2, 1].into_iter().filter(|n| *n <= root) {
            let bins = n.pow(3);
            let mut d = Deposition3 {
                intervals: n,
                counts: vec![0; bins],
                normalizers: vec![0.; bins],
                max_cell_volumes: vec![0.; bins],
            };
            let mut values = vec![[0.; 3]; bins];
            for s in &by_id {
                if (0..3).any(|k| !(s.position[k] - origin[k]).is_finite()) {
                    return Err(AuxiliaryError3::NonFinite);
                }
                let w: [_; 3] = std::array::from_fn(|a| {
                    spline_weights(s.position[a], origin[a], lengths[a], n)
                });
                for (z, &wz) in w[2][..n].iter().enumerate() {
                    for (y, &wy) in w[1][..n].iter().enumerate() {
                        for (x, &wx) in w[0][..n].iter().enumerate() {
                            let weight = (s.volume / total) * wx * wy * wz;
                            if weight <= 0. {
                                continue;
                            }
                            let i = index([x, y, z], n);
                            d.counts[i] += 1;
                            d.normalizers[i] += weight;
                            d.max_cell_volumes[i] = d.max_cell_volumes[i].max(s.volume);
                            for (u, &v) in values[i].iter_mut().zip(&s.velocity) {
                                *u += weight * v;
                            }
                        }
                    }
                }
            }
            let usable = d.normalizers.iter().all(|w| w.is_finite() && *w > 0.);
            if usable {
                for (v, &w) in values.iter_mut().zip(&d.normalizers) {
                    for u in v {
                        *u /= w;
                    }
                }
            }
            attempts.push(d);
            if usable {
                let corners = differences(&values, n, lengths.map(|l| l / n as f64));
                if corners
                    .iter()
                    .flat_map(|j| j.derivatives.into_iter().flatten())
                    .any(|x| !x.is_finite())
                {
                    return Err(AuxiliaryError3::NonFinite);
                }
                return Ok(Self {
                    lengths,
                    origin,
                    intervals: n,
                    corners,
                    attempts,
                });
            }
        }
        Err(AuxiliaryError3::AuxiliaryTransitionUnresolved)
    }
    pub fn intervals(&self) -> usize {
        self.intervals
    }
    pub fn sample(&self, x: Vec3) -> Result<Velocity3, AuxiliaryError3> {
        let n = self.intervals;
        let q: Vec3 = std::array::from_fn(|a| {
            ((x[a] - self.origin[a]).rem_euclid(self.lengths[a]) / self.lengths[a]) * n as f64
        });
        if !q.into_iter().all(f64::is_finite) {
            return Err(AuxiliaryError3::NonFinite);
        }
        let cell = q.map(|v| v.floor() as usize % n);
        let f = q.map(f64::fract);
        let corners = std::array::from_fn(|m| {
            self.corners[index(std::array::from_fn(|a| (cell[a] + ((m >> a) & 1)) % n), n)]
        });
        interpolate_cell(&corners, self.lengths.map(|v| v / n as f64), f)
    }
}
