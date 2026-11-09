//! Constant prescribed-flow planar reduction on fixed/rigid periodic Voronoi cells.
//! No gas state, EOS, force feedback or total-fluid-energy budget is evolved.
use crate::diagnostics::divergence_values;
use crate::operators::{TransportStencil, gradients};
use mhd_core::Vec3;
use moving_mesh::{Derivatives, Mesh, Vec2};
use std::f64::consts::PI;

pub struct Transport {
    mesh: Mesh,
    neighbours: Derivatives,
    faces: Derivatives,
    velocity: Vec2,
    mesh_velocity: Vec2,
    potential: Vec<[f64; 1]>,
    time: f64,
    steps: usize,
    max_dt: f64,
}
pub struct Fields {
    pub magnetic: Vec<Vec3>,
    /// Raw neighbour LS, arithmetic-face, and limited-face operators, respectively.
    pub divergences: [Vec<f64>; 3],
}
impl Transport {
    pub fn new(
        mesh: Mesh,
        velocity: Vec2,
        mesh_velocity: Vec2,
        initial: impl Fn(Vec2) -> f64,
    ) -> Result<Self, String> {
        if !velocity.iter().chain(&mesh_velocity).all(|v| v.is_finite()) {
            return Err("transport requires finite velocities".into());
        }
        let speed = (velocity[0] - mesh_velocity[0]).hypot(velocity[1] - mesh_velocity[1]);
        if !speed.is_finite() {
            return Err("transport relative speed overflow".into());
        }
        let neighbours = Derivatives::build(&mesh, false)?;
        let faces = Derivatives::build(&mesh, true)?;
        let potential: Vec<_> = mesh.cells.iter().map(|c| [initial(c.centroid)]).collect();
        if !potential.iter().flatten().all(|a| a.is_finite()) {
            return Err("nonfinite initial transport potential".into());
        }
        let max_dt = if speed == 0. {
            f64::INFINITY
        } else {
            0.3 * mesh
                .cells
                .iter()
                .map(|c| (c.volume / PI).sqrt() / speed)
                .fold(f64::INFINITY, f64::min)
        };
        Ok(Self {
            mesh,
            neighbours,
            faces,
            velocity,
            mesh_velocity,
            potential,
            time: 0.,
            steps: 0,
            max_dt,
        })
    }
    pub fn mesh(&self) -> &Mesh {
        &self.mesh
    }
    pub fn potential(&self) -> &[[f64; 1]] {
        &self.potential
    }
    pub fn time(&self) -> f64 {
        self.time
    }
    pub fn steps(&self) -> usize {
        self.steps
    }
    pub fn position(&self, i: usize) -> Vec2 {
        std::array::from_fn(|k| {
            (self.mesh.cells[i].centroid[k] + self.time * self.mesh_velocity[k])
                .rem_euclid(self.mesh.lengths[k])
        })
    }
    fn rate(&self, a: &[[f64; 1]]) -> Result<Vec<[f64; 1]>, String> {
        let limited = gradients(&self.mesh, &self.neighbours, a, true)?;
        let op = TransportStencil {
            mesh: &self.mesh,
            faces: &self.faces,
        };
        let b = std::array::from_fn(|k| self.mesh_velocity[k] - self.velocity[k]);
        let mut rate = vec![[0.]; a.len()];
        for (i, r) in rate.iter_mut().enumerate() {
            op.add_rate(a, &limited, i, b, r);
        }
        if !rate.iter().flatten().all(|r| r.is_finite()) {
            return Err("nonfinite transport rate".into());
        }
        Ok(rate)
    }
    pub fn advance_to(&mut self, target: f64) -> Result<(), String> {
        if !target.is_finite()
            || target < self.time
            || !self
                .velocity
                .iter()
                .chain(&self.mesh_velocity)
                .all(|v| (v * target).is_finite())
        {
            return Err("invalid transport target time".into());
        }
        if self.velocity == self.mesh_velocity {
            self.time = target;
            return Ok(());
        }
        while self.time < target {
            let dt = self.max_dt.min(target - self.time);
            if self.time + dt == self.time {
                return Err("transport timestep underflow".into());
            }
            let r0 = self.rate(&self.potential)?;
            let star: Vec<_> = self
                .potential
                .iter()
                .zip(&r0)
                .map(|(a, r)| [a[0] + dt * r[0]])
                .collect();
            let r1 = self.rate(&star)?;
            let next: Vec<_> = self
                .potential
                .iter()
                .zip(r0)
                .zip(r1)
                .map(|((a, r0), r1)| [a[0] + 0.5 * dt * (r0[0] + r1[0])])
                .collect();
            if !next.iter().flatten().all(|a| a.is_finite()) {
                return Err("nonfinite transport state".into());
            }
            self.potential = next;
            self.time += dt;
            self.steps += 1;
        }
        Ok(())
    }
    pub fn fields(&self) -> Result<Fields, String> {
        let raw = gradients(&self.mesh, &self.neighbours, &self.potential, false)?;
        let magnetic: Vec<_> = raw.iter().map(|g| [g[0][1], -g[0][0], 0.]).collect();
        let divergences = divergence_values(&self.mesh, &self.neighbours, &magnetic)?;
        Ok(Fields {
            magnetic,
            divergences,
        })
    }
}
