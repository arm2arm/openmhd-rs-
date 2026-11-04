//! Periodic bicubic reduction of paper Eq. (68), with the explicit v2 origin rule.
use crate::gauge::{Jacobian, Vec3};
use moving_mesh::Vec2;

#[derive(Clone, Copy, Debug, Default)]
pub struct Jet {
    pub value: Vec3,
    pub dx: Vec3,
    pub dy: Vec3,
    pub dxy: Vec3,
}

#[derive(Clone, Copy, Debug)]
pub struct Sample {
    pub velocity: Vec3,
    pub jacobian: Jacobian,
}

/// Tensor Hermite polynomial on a single element; coordinates are in [0,1]^2.
/// Corner layout is [y][x]; derivative jets are in physical length units.
pub fn interpolate(
    corners: &[[Jet; 2]; 2],
    spacing: Vec2,
    coordinate: Vec2,
) -> Result<Sample, String> {
    if !spacing.iter().all(|h| h.is_finite() && *h > 0.0)
        || !coordinate
            .iter()
            .all(|s| s.is_finite() && (0.0..=1.0).contains(s))
        || corners.iter().flatten().any(|j| {
            [j.value, j.dx, j.dy, j.dxy]
                .iter()
                .flatten()
                .any(|v| !v.is_finite())
        })
    {
        return Err("invalid Hermite element or coordinate".into());
    }
    let basis = |s: f64| {
        [
            [
                2.0 * s * s * s - 3.0 * s * s + 1.0,
                s * s * s - 2.0 * s * s + s,
            ],
            [-2.0 * s * s * s + 3.0 * s * s, s * s * s - s * s],
        ]
    };
    let derivative = |s: f64| {
        [
            [6.0 * s * s - 6.0 * s, 3.0 * s * s - 4.0 * s + 1.0],
            [-6.0 * s * s + 6.0 * s, 3.0 * s * s - 2.0 * s],
        ]
    };
    let bx = basis(coordinate[0]);
    let by = basis(coordinate[1]);
    let dx = derivative(coordinate[0]);
    let dy = derivative(coordinate[1]);
    let mut result = Sample {
        velocity: [0.0; 3],
        jacobian: [[0.0; 3]; 3],
    };
    for (y, row) in corners.iter().enumerate() {
        for (x, jet) in row.iter().enumerate() {
            for (px, py, values) in [
                (0, 0, jet.value),
                (1, 0, jet.dx),
                (0, 1, jet.dy),
                (1, 1, jet.dxy),
            ] {
                let scale = (if px == 0 { 1.0 } else { spacing[0] })
                    * (if py == 0 { 1.0 } else { spacing[1] });
                for (k, v) in values.iter().enumerate() {
                    result.velocity[k] += v * scale * bx[x][px] * by[y][py];
                    result.jacobian[k][0] += v * scale * dx[x][px] * by[y][py] / spacing[0];
                    result.jacobian[k][1] += v * scale * bx[x][px] * dy[y][py] / spacing[1];
                }
            }
        }
    }
    if !result
        .velocity
        .iter()
        .chain(result.jacobian.iter().flatten())
        .all(|v| v.is_finite())
    {
        return Err("Hermite evaluation overflow".into());
    }
    Ok(result)
}

#[derive(Clone, Copy, Debug)]
pub struct VelocitySample {
    pub position: Vec2,
    pub volume: f64,
    pub velocity: Vec3,
}

#[derive(Clone, Debug)]
pub struct SmoothVelocity {
    lengths: Vec2,
    origin: Vec2,
    corners: Vec<Jet>,
    intervals: usize,
    pub counts: Vec<usize>,
    pub max_cell_volumes: Vec<f64>,
    pub coarsenings: usize,
    pub mean_velocity: Vec3,
}

fn bin(position: f64, origin: f64, length: f64, intervals: usize) -> usize {
    let mut q = (position - origin).rem_euclid(length) / length * intervals as f64 + 0.5;
    let nearest = q.round();
    if (q - nearest).abs() <= 32.0 * f64::EPSILON * (1.0 + q.abs()) {
        q = nearest;
    }
    (q.floor() as usize) % intervals
}

fn jets(values: &[Vec3], n: usize, spacing: Vec2) -> Vec<Jet> {
    let index = |x: usize, y: usize| (x % n) + n * (y % n);
    let dx: Vec<Vec3> = (0..n * n)
        .map(|i| {
            let x = i % n;
            let y = i / n;
            std::array::from_fn(|k| {
                (values[index(x + 1, y)][k] - values[index(x + n - 1, y)][k]) / (2.0 * spacing[0])
            })
        })
        .collect();
    (0..n * n)
        .map(|i| {
            let x = i % n;
            let y = i / n;
            Jet {
                value: values[i],
                dx: dx[i],
                dy: std::array::from_fn(|k| {
                    (values[index(x, y + 1)][k] - values[index(x, y + n - 1)][k])
                        / (2.0 * spacing[1])
                }),
                dxy: std::array::from_fn(|k| {
                    (dx[index(x, y + 1)][k] - dx[index(x, y + n - 1)][k]) / (2.0 * spacing[1])
                }),
            }
        })
        .collect()
}

impl SmoothVelocity {
    pub fn build(lengths: Vec2, samples: &[VelocitySample], origin: Vec2) -> Result<Self, String> {
        if samples.is_empty()
            || !lengths.iter().all(|v| v.is_finite() && *v > 0.0)
            || !origin.iter().all(|v| v.is_finite())
            || samples.iter().any(|s| {
                !s.volume.is_finite()
                    || s.volume <= 0.0
                    || !s.position.iter().chain(&s.velocity).all(|v| v.is_finite())
                    || (0..2).any(|k| !(s.position[k] - origin[k]).is_finite())
            })
        {
            return Err("invalid auxiliary velocity samples/domain/origin".into());
        }
        let total: f64 = samples.iter().map(|s| s.volume).sum();
        if !total.is_finite() || total <= 0.0 {
            return Err("auxiliary volume overflow".into());
        }
        let mean_velocity: Vec3 = std::array::from_fn(|k| {
            samples
                .iter()
                .map(|s| s.volume / total * s.velocity[k])
                .sum()
        });
        for (coarsenings, n) in [4, 2, 1].into_iter().enumerate() {
            let mut weights = vec![0.0; n * n];
            let mut values = vec![[0.0; 3]; n * n];
            let mut counts = vec![0; n * n];
            let mut max_cell_volumes = vec![0.0_f64; n * n];
            for s in samples {
                let i = bin(s.position[0], origin[0], lengths[0], n)
                    + n * bin(s.position[1], origin[1], lengths[1], n);
                let w = s.volume / total;
                weights[i] += w;
                counts[i] += 1;
                max_cell_volumes[i] = max_cell_volumes[i].max(s.volume);
                for (k, v) in s.velocity.iter().enumerate() {
                    values[i][k] += w * v;
                }
            }
            if counts.contains(&0) {
                continue;
            }
            for (v, w) in values.iter_mut().zip(weights) {
                for component in v {
                    *component /= w;
                }
            }
            let corners = jets(&values, n, lengths.map(|l| l / n as f64));
            if !mean_velocity
                .into_iter()
                .chain(
                    corners
                        .iter()
                        .flat_map(|j| [j.value, j.dx, j.dy, j.dxy])
                        .flatten(),
                )
                .all(|v| v.is_finite())
            {
                return Err("auxiliary averages/jets overflow".into());
            }
            return Ok(Self {
                lengths,
                origin,
                corners,
                intervals: n,
                counts,
                max_cell_volumes,
                coarsenings,
                mean_velocity,
            });
        }
        Err("auxiliary root remained empty".into())
    }

    pub fn intervals(&self) -> usize {
        self.intervals
    }
    pub fn origin(&self) -> Vec2 {
        self.origin
    }

    pub fn sample(&self, position: Vec2, stage_time: f64) -> Result<Sample, String> {
        if !stage_time.is_finite() || stage_time < 0.0 {
            return Err("invalid auxiliary stage time".into());
        }
        let coordinate: Vec2 = std::array::from_fn(|k| {
            position[k] - self.origin[k] - stage_time * self.mean_velocity[k]
        });
        if !coordinate.iter().all(|v| v.is_finite()) {
            return Err("auxiliary coordinate overflow".into());
        }
        let n = self.intervals;
        let spacing = self.lengths.map(|l| l / n as f64);
        let q: Vec2 =
            std::array::from_fn(|k| coordinate[k].rem_euclid(self.lengths[k]) / spacing[k]);
        let cell = q.map(|v| v.floor() as usize);
        let local = std::array::from_fn(|k| (q[k] - cell[k] as f64).clamp(0.0, 1.0));
        let corners = std::array::from_fn(|y| {
            std::array::from_fn(|x| self.corners[(cell[0] + x) % n + n * ((cell[1] + y) % n)])
        });
        interpolate(&corners, spacing, local)
    }

    pub fn advanced_origin(&self, dt: f64) -> Result<Vec2, String> {
        if !dt.is_finite() || dt < 0.0 {
            return Err("invalid origin advance interval".into());
        }
        let origin: Vec2 = std::array::from_fn(|k| self.origin[k] + dt * self.mean_velocity[k]);
        if !origin.iter().all(|v| v.is_finite()) {
            return Err("auxiliary origin overflow".into());
        }
        Ok(std::array::from_fn(|k| {
            origin[k].rem_euclid(self.lengths[k])
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f64::consts::TAU;

    #[test]
    fn centred_jets_converge_for_periodic_smooth_data() {
        let mut errors = Vec::new();
        for n in [8, 16, 32] {
            let h = 1.0 / n as f64;
            let values: Vec<_> = (0..n * n)
                .map(|i| [(TAU * (i % n) as f64 * h).sin() * (TAU * (i / n) as f64 * h).cos(); 3])
                .collect();
            let field = SmoothVelocity {
                lengths: [1.0; 2],
                origin: [0.0; 2],
                corners: jets(&values, n, [h; 2]),
                intervals: n,
                counts: vec![1; n * n],
                max_cell_volumes: vec![h * h; n * n],
                coarsenings: 0,
                mean_velocity: [0.0; 3],
            };
            let error: f64 = (0..n * n)
                .map(|i| {
                    let p = [((i % n) as f64 + 0.37) * h, ((i / n) as f64 + 0.63) * h];
                    let g = field.sample(p, 0.0).unwrap().jacobian[0];
                    (g[0] - TAU * (TAU * p[0]).cos() * (TAU * p[1]).cos())
                        .hypot(g[1] + TAU * (TAU * p[0]).sin() * (TAU * p[1]).sin())
                })
                .sum::<f64>()
                / (n * n) as f64;
            errors.push(error);
        }
        for pair in errors.windows(2) {
            // Finite-difference jets plus interpolation: record convergence,
            // rather than assume an asymptotic order on the coarsest grid.
            assert!(pair[1] < pair[0], "{errors:?}");
        }
    }
}
