//! Vector-potential references: a Cartesian kinematic pilot and periodic 2.5D MHD.
//!
//! `general` implements paper-global-v2 with the source/auxiliary/diagnostic
//! modules. See docs/VECTOR_POTENTIAL_REFERENCE.md for acceptance boundaries,
//! including the unresolved nonuniform mean-field boost discrepancy.
//! The original Grid/Simulation types below remain the separate scalar Az
//! transport pilot; see docs/KINEMATIC_2D.md.

pub mod auxiliary;
pub mod diagnostics;
pub mod gauge;
pub mod general;
pub mod operators;

use std::f64::consts::{PI, TAU};

pub type Vec2 = [f64; 2];

#[derive(Clone, Copy, Debug)]
pub struct Grid {
    nx: usize,
    ny: usize,
}

impl Grid {
    pub fn new(nx: usize, ny: usize) -> Result<Self, String> {
        if nx < 4 || ny < 4 || nx.checked_mul(ny).is_none() {
            return Err(
                "grid dimensions must be at least 4 and their product must fit usize".into(),
            );
        }
        Ok(Self { nx, ny })
    }

    pub fn nx(self) -> usize {
        self.nx
    }

    pub fn ny(self) -> usize {
        self.ny
    }

    pub fn dx(self) -> f64 {
        1.0 / self.nx as f64
    }

    pub fn dy(self) -> f64 {
        1.0 / self.ny as f64
    }

    pub fn index(self, i: usize, j: usize) -> usize {
        assert!(i < self.nx && j < self.ny);
        j * self.nx + i
    }

    fn len(self) -> usize {
        self.nx * self.ny
    }

    fn neighbours(self, i: usize, j: usize) -> [usize; 4] {
        [
            self.index((i + self.nx - 1) % self.nx, j),
            self.index((i + 1) % self.nx, j),
            self.index(i, (j + self.ny - 1) % self.ny),
            self.index(i, (j + 1) % self.ny),
        ]
    }

    fn centre(self, i: usize, j: usize) -> Vec2 {
        [(i as f64 + 0.5) * self.dx(), (j as f64 + 0.5) * self.dy()]
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Case {
    /// Smooth manufactured potential with unequal x/y wavenumbers.
    Smooth,
    /// Compact, weak field loop from paper Eq. (103), with prescribed flow.
    Loop,
}

impl Case {
    pub fn name(self) -> &'static str {
        match self {
            Self::Smooth => "smooth",
            Self::Loop => "loop",
        }
    }

    pub fn sample(self, position: Vec2) -> (f64, Vec2) {
        let [x, y] = position.map(|q| q.rem_euclid(1.0));
        match self {
            Self::Smooth => {
                let (sx, cx) = (TAU * x).sin_cos();
                let (sy, cy) = (2.0 * TAU * y).sin_cos();
                (sx * sy, [2.0 * TAU * sx * cy, -TAU * cx * sy])
            }
            Self::Loop => {
                let dx = x - 0.5;
                let dy = y - 0.5;
                let radius = dx.hypot(dy);
                let amplitude = 0.001 / (4.0 * PI).sqrt();
                let az = amplitude * (0.3 - radius).max(0.0);
                let b = if radius > 0.0 && radius < 0.3 {
                    [-amplitude * dy / radius, amplitude * dx / radius]
                } else {
                    [0.0; 2]
                };
                (az, b)
            }
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Reconstruction {
    Unlimited,
    MonotonizedCentral,
}

impl Reconstruction {
    pub fn name(self) -> &'static str {
        match self {
            Self::Unlimited => "unlimited",
            Self::MonotonizedCentral => "mc",
        }
    }

    // Returns slope times cell spacing, not the physical derivative.
    fn slope(self, left: f64, centre: f64, right: f64) -> f64 {
        let dl = centre - left;
        let dr = right - centre;
        match self {
            Self::Unlimited => 0.5 * (right - left),
            Self::MonotonizedCentral => {
                let candidates = [2.0 * dl, 0.5 * (dl + dr), 2.0 * dr];
                if candidates.iter().all(|x| *x > 0.0) {
                    candidates.into_iter().fold(f64::INFINITY, f64::min)
                } else if candidates.iter().all(|x| *x < 0.0) {
                    candidates.into_iter().fold(f64::NEG_INFINITY, f64::max)
                } else {
                    0.0
                }
            }
        }
    }
}

/// No mass, momentum or gas energy is evolved in this kinematic problem.
pub struct Simulation {
    grid: Grid,
    case: Case,
    velocity: Vec2,
    mesh_velocity: Vec2,
    reconstruction: Reconstruction,
    cfl: f64,
    az: Vec<f64>,
    initial_az: Vec<f64>,
    time: f64,
    steps: usize,
}

impl Simulation {
    pub fn new(
        grid: Grid,
        case: Case,
        velocity: Vec2,
        mesh_velocity: Vec2,
        reconstruction: Reconstruction,
        cfl: f64,
    ) -> Result<Self, String> {
        if !velocity.iter().chain(&mesh_velocity).all(|v| v.is_finite()) {
            return Err("fluid and mesh velocities must be finite".into());
        }
        if !cfl.is_finite() || cfl <= 0.0 || cfl > 0.5 {
            return Err("CFL must be finite and in (0, 0.5]".into());
        }
        let relative = [
            velocity[0] - mesh_velocity[0],
            velocity[1] - mesh_velocity[1],
        ];
        let rate = relative[0].abs() / grid.dx() + relative[1].abs() / grid.dy();
        if !rate.is_finite() {
            return Err("relative velocity / grid spacing overflows".into());
        }
        let mut az = Vec::with_capacity(grid.len());
        for j in 0..grid.ny {
            for i in 0..grid.nx {
                az.push(case.sample(grid.centre(i, j)).0);
            }
        }
        Ok(Self {
            grid,
            case,
            velocity,
            mesh_velocity,
            reconstruction,
            cfl,
            initial_az: az.clone(),
            az,
            time: 0.0,
            steps: 0,
        })
    }

    pub fn grid(&self) -> Grid {
        self.grid
    }

    pub fn az(&self) -> &[f64] {
        &self.az
    }

    pub fn time(&self) -> f64 {
        self.time
    }

    pub fn steps(&self) -> usize {
        self.steps
    }

    pub fn relative_velocity(&self) -> Vec2 {
        [
            self.velocity[0] - self.mesh_velocity[0],
            self.velocity[1] - self.mesh_velocity[1],
        ]
    }

    /// Physical, wrapped positions; storage indices move rigidly with the grid.
    pub fn position(&self, i: usize, j: usize) -> Vec2 {
        let centre = self.grid.centre(i, j);
        [0, 1].map(|a| (centre[a] + self.mesh_velocity[a] * self.time).rem_euclid(1.0))
    }

    pub fn exact(&self, i: usize, j: usize) -> (f64, Vec2) {
        let centre = self.grid.centre(i, j);
        let relative = self.relative_velocity();
        self.case
            .sample([0, 1].map(|a| centre[a] - relative[a] * self.time))
    }

    pub fn advance_to(&mut self, final_time: f64) -> Result<(), String> {
        if !final_time.is_finite() || final_time < self.time {
            return Err("final time must be finite and no earlier than current time".into());
        }
        if !self
            .velocity
            .iter()
            .chain(&self.mesh_velocity)
            .all(|v| (v * final_time).is_finite())
        {
            return Err("velocity times final time overflows".into());
        }
        let relative = self.relative_velocity();
        let rate = relative[0].abs() / self.grid.dx() + relative[1].abs() / self.grid.dy();
        if rate == 0.0 {
            self.time = final_time;
            return Ok(());
        }
        let dt_max = self.cfl / rate;
        while self.time < final_time {
            let dt = dt_max.min(final_time - self.time);
            if self.time + dt == self.time {
                return Err("timestep is too small to advance floating-point time".into());
            }
            let r0 = transport_rate(self.grid, &self.az, relative, self.reconstruction);
            let predictor: Vec<_> = self.az.iter().zip(&r0).map(|(a, r)| a + dt * r).collect();
            let r1 = transport_rate(self.grid, &predictor, relative, self.reconstruction);
            for ((a, r0), r1) in self.az.iter_mut().zip(r0).zip(r1) {
                *a += 0.5 * dt * (r0 + r1);
            }
            if !self.az.iter().all(|a| a.is_finite()) {
                return Err("non-finite vector potential during time integration".into());
            }
            self.time += dt;
            self.steps += 1;
        }
        Ok(())
    }

    pub fn snapshot(&self) -> Snapshot {
        let b = reconstruct_b(self.grid, &self.az);
        let (div_central, div_face_mc) = divergences(self.grid, &b);
        let initial_b = reconstruct_b(self.grid, &self.initial_az);
        let initial_energy = mean(initial_b.iter().map(|b| 0.5 * (b[0] * b[0] + b[1] * b[1])));
        let magnetic_energy = mean(b.iter().map(|b| 0.5 * (b[0] * b[0] + b[1] * b[1])));
        let mut az_error = 0.0;
        let mut b_error = 0.0;
        for j in 0..self.grid.ny {
            for i in 0..self.grid.nx {
                let index = self.grid.index(i, j);
                let (exact_az, exact_b) = self.exact(i, j);
                az_error += (self.az[index] - exact_az).abs();
                b_error += (b[index][0] - exact_b[0]).hypot(b[index][1] - exact_b[1]);
            }
        }
        let az_integral = mean(self.az.iter().copied());
        let az_integral_drift = az_integral - mean(self.initial_az.iter().copied());
        let initial_scale = mean(self.initial_az.iter().map(|a| a.abs()));
        let metrics = Metrics {
            az_l1: az_error / self.grid.len() as f64,
            b_l1: b_error / self.grid.len() as f64,
            az_integral,
            az_integral_drift,
            az_integral_relative_drift: az_integral_drift / initial_scale,
            az_min: self.az.iter().copied().fold(f64::INFINITY, f64::min),
            az_max: self.az.iter().copied().fold(f64::NEG_INFINITY, f64::max),
            mean_b: [mean(b.iter().map(|b| b[0])), mean(b.iter().map(|b| b[1]))],
            magnetic_energy,
            magnetic_energy_ratio: magnetic_energy / initial_energy,
            div_central_rms: mean(div_central.iter().map(|d| d * d)).sqrt(),
            div_central_max: div_central.iter().map(|d| d.abs()).fold(0.0, f64::max),
            div_face_mc_rms: mean(div_face_mc.iter().map(|d| d * d)).sqrt(),
            div_face_mc_max: div_face_mc.iter().map(|d| d.abs()).fold(0.0, f64::max),
        };
        Snapshot {
            b,
            div_central,
            div_face_mc,
            metrics,
        }
    }
}

#[derive(Debug)]
pub struct Metrics {
    pub az_l1: f64,
    pub b_l1: f64,
    pub az_integral: f64,
    pub az_integral_drift: f64,
    pub az_integral_relative_drift: f64,
    pub az_min: f64,
    pub az_max: f64,
    pub mean_b: Vec2,
    pub magnetic_energy: f64,
    pub magnetic_energy_ratio: f64,
    pub div_central_rms: f64,
    pub div_central_max: f64,
    pub div_face_mc_rms: f64,
    pub div_face_mc_max: f64,
}

pub struct Snapshot {
    pub b: Vec<Vec2>,
    pub div_central: Vec<f64>,
    pub div_face_mc: Vec<f64>,
    pub metrics: Metrics,
}

fn mean(values: impl Iterator<Item = f64>) -> f64 {
    // Compensated accumulation keeps diagnostic summation noise small.
    let (mut sum, mut correction, mut count) = (0.0, 0.0, 0_usize);
    for value in values {
        let adjusted = value - correction;
        let next = sum + adjusted;
        correction = (next - sum) - adjusted;
        sum = next;
        count += 1;
    }
    sum / count as f64
}

fn slopes(grid: Grid, values: &[f64], reconstruction: Reconstruction) -> Vec<Vec2> {
    let mut result = vec![[0.0; 2]; grid.len()];
    for j in 0..grid.ny {
        for i in 0..grid.nx {
            let k = grid.index(i, j);
            let [xm, xp, ym, yp] = grid.neighbours(i, j);
            result[k] = [
                reconstruction.slope(values[xm], values[k], values[xp]),
                reconstruction.slope(values[ym], values[k], values[yp]),
            ];
        }
    }
    result
}

fn transport_rate(
    grid: Grid,
    az: &[f64],
    velocity: Vec2,
    reconstruction: Reconstruction,
) -> Vec<f64> {
    let slopes = slopes(grid, az, reconstruction);
    let mut rate = vec![0.0; grid.len()];
    for j in 0..grid.ny {
        for i in 0..grid.nx {
            let k = grid.index(i, j);
            let [_, xp, _, yp] = grid.neighbours(i, j);
            for (axis, other, spacing) in [(0, xp, grid.dx()), (1, yp, grid.dy())] {
                let donor = if velocity[axis] >= 0.0 {
                    az[k] + 0.5 * slopes[k][axis]
                } else {
                    az[other] - 0.5 * slopes[other][axis]
                };
                let contribution = velocity[axis] * donor / spacing;
                rate[k] -= contribution;
                rate[other] += contribution;
            }
        }
    }
    rate
}

fn reconstruct_b(grid: Grid, az: &[f64]) -> Vec<Vec2> {
    let mut b = vec![[0.0; 2]; grid.len()];
    for j in 0..grid.ny {
        for i in 0..grid.nx {
            let [xm, xp, ym, yp] = grid.neighbours(i, j);
            b[grid.index(i, j)] = [
                (az[yp] - az[ym]) / (2.0 * grid.dy()),
                -(az[xp] - az[xm]) / (2.0 * grid.dx()),
            ];
        }
    }
    b
}

fn divergences(grid: Grid, b: &[Vec2]) -> (Vec<f64>, Vec<f64>) {
    let mut central = vec![0.0; grid.len()];
    let mut face = vec![0.0; grid.len()];
    let bx: Vec<_> = b.iter().map(|b| b[0]).collect();
    let by: Vec<_> = b.iter().map(|b| b[1]).collect();
    let sx = slopes(grid, &bx, Reconstruction::MonotonizedCentral);
    let sy = slopes(grid, &by, Reconstruction::MonotonizedCentral);
    for j in 0..grid.ny {
        for i in 0..grid.nx {
            let k = grid.index(i, j);
            let [xm, xp, ym, yp] = grid.neighbours(i, j);
            central[k] = (b[xp][0] - b[xm][0]) / (2.0 * grid.dx())
                + (b[yp][1] - b[ym][1]) / (2.0 * grid.dy());
            // A single reconstructed normal field is shared by each face pair.
            let bx_face = 0.5 * (bx[k] + 0.5 * sx[k][0] + bx[xp] - 0.5 * sx[xp][0]);
            let by_face = 0.5 * (by[k] + 0.5 * sy[k][1] + by[yp] - 0.5 * sy[yp][1]);
            face[k] += bx_face / grid.dx() + by_face / grid.dy();
            face[xp] -= bx_face / grid.dx();
            face[yp] -= by_face / grid.dy();
        }
    }
    (central, face)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn affine_potential_has_correct_curl_interior() {
        let grid = Grid::new(8, 12).unwrap();
        let az: Vec<_> = (0..grid.ny)
            .flat_map(|j| {
                (0..grid.nx).map(move |i| {
                    let [x, y] = grid.centre(i, j);
                    1.0 + 2.0 * x - 3.0 * y
                })
            })
            .collect();
        let b = reconstruct_b(grid, &az);
        // An affine potential is not periodic; only interior points are valid.
        for j in 1..grid.ny - 1 {
            for i in 1..grid.nx - 1 {
                let value = b[grid.index(i, j)];
                assert!((value[0] + 3.0).abs() < 1e-13);
                assert!((value[1] + 2.0).abs() < 1e-13);
            }
        }
    }

    #[test]
    fn constant_potential_has_zero_curl_and_transport() {
        let grid = Grid::new(8, 12).unwrap();
        let az = vec![2.0; grid.len()];
        assert!(reconstruct_b(grid, &az).iter().all(|b| *b == [0.0; 2]));
        for reconstruction in [
            Reconstruction::Unlimited,
            Reconstruction::MonotonizedCentral,
        ] {
            let rhs = transport_rate(grid, &az, [-2.0, 1.0], reconstruction);
            assert!(rhs.iter().all(|r| *r == 0.0));
        }
    }

    #[test]
    fn periodic_face_rates_sum_to_zero_for_both_velocity_signs() {
        let grid = Grid::new(9, 12).unwrap();
        let az: Vec<_> = (0..grid.len()).map(|k| (k as f64).sin()).collect();
        for velocity in [[2.0, -1.0], [-2.0, 1.0]] {
            let rhs = transport_rate(grid, &az, velocity, Reconstruction::MonotonizedCentral);
            assert!(mean(rhs.iter().copied()).abs() < 1e-13);
        }
    }

    #[test]
    fn curl_and_independent_divergence_are_distinct_operators() {
        let sim = Simulation::new(
            Grid::new(32, 48).unwrap(),
            Case::Smooth,
            [2.0, 1.0],
            [0.0; 2],
            Reconstruction::Unlimited,
            0.4,
        )
        .unwrap();
        let snapshot = sim.snapshot();
        assert!(snapshot.metrics.div_central_max < 1e-10);
        assert!(snapshot.metrics.div_face_mc_rms > 1e-4);
    }

    #[test]
    fn invalid_inputs_are_rejected() {
        assert!(Grid::new(3, 8).is_err());
        assert!(Grid::new(usize::MAX, 8).is_err());
        let grid = Grid::new(8, 8).unwrap();
        for cfl in [0.0, -0.1, 0.51, f64::NAN] {
            assert!(
                Simulation::new(
                    grid,
                    Case::Loop,
                    [1.0; 2],
                    [0.0; 2],
                    Reconstruction::MonotonizedCentral,
                    cfl
                )
                .is_err()
            );
        }
        assert!(
            Simulation::new(
                grid,
                Case::Loop,
                [f64::INFINITY, 1.0],
                [0.0; 2],
                Reconstruction::Unlimited,
                0.4
            )
            .is_err()
        );
        let mut sim = Simulation::new(
            grid,
            Case::Loop,
            [1.0; 2],
            [0.0; 2],
            Reconstruction::MonotonizedCentral,
            0.4,
        )
        .unwrap();
        assert!(sim.advance_to(-1.0).is_err());
        assert!(sim.advance_to(f64::NAN).is_err());
    }
}
