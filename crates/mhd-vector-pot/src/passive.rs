//! Prescribed constant-flow scalar A_z transport on fixed/rigid Voronoi meshes.
//! This isolates the general pointwise face-LS transport operator; no gas evolves.
use moving_mesh::{
    Derivatives, Mesh, Vec2, dot,
    quadratic::{Compact, Quadratic},
};

pub struct Passive {
    mesh: Mesh,
    potential: Vec<f64>,
    time: f64,
    steps: usize,
    velocity: Vec2,
    mesh_velocity: Vec2,
    neighbour: Derivatives,
    face: Derivatives,
    dt: f64,
    quadratic: Option<Quadratic>,
    consistent: bool,
    compact: Option<Compact>,
}
impl Passive {
    pub fn mesh(&self) -> &Mesh {
        &self.mesh
    }
    pub fn potential(&self) -> &[f64] {
        &self.potential
    }
    pub fn time(&self) -> f64 {
        self.time
    }
    pub fn steps(&self) -> usize {
        self.steps
    }

    pub fn new(
        mesh: Mesh,
        velocity: Vec2,
        mesh_velocity: Vec2,
        initial: impl Fn(Vec2) -> f64,
    ) -> Result<Self, String> {
        Self::with_quadratic(mesh, velocity, mesh_velocity, initial, false)
    }
    pub fn with_quadratic(
        mesh: Mesh,
        velocity: Vec2,
        mesh_velocity: Vec2,
        initial: impl Fn(Vec2) -> f64,
        quadratic: bool,
    ) -> Result<Self, String> {
        Self::with_reconstruction(
            mesh,
            velocity,
            mesh_velocity,
            initial,
            quadratic,
            false,
            false,
        )
    }
    pub fn with_consistent(
        mesh: Mesh,
        velocity: Vec2,
        mesh_velocity: Vec2,
        initial: impl Fn(Vec2) -> f64,
    ) -> Result<Self, String> {
        Self::with_reconstruction(mesh, velocity, mesh_velocity, initial, true, true, false)
    }
    pub fn with_compact(
        mesh: Mesh,
        velocity: Vec2,
        mesh_velocity: Vec2,
        initial: impl Fn(Vec2) -> f64,
    ) -> Result<Self, String> {
        Self::with_reconstruction(mesh, velocity, mesh_velocity, initial, true, true, true)
    }
    fn with_reconstruction(
        mesh: Mesh,
        velocity: Vec2,
        mesh_velocity: Vec2,
        initial: impl Fn(Vec2) -> f64,
        quadratic: bool,
        consistent: bool,
        compact: bool,
    ) -> Result<Self, String> {
        if !velocity.iter().chain(&mesh_velocity).all(|v| v.is_finite()) {
            return Err("nonfinite velocity".into());
        }
        let neighbour = Derivatives::build(&mesh, false)?;
        let face = Derivatives::build(&mesh, true)?;
        let b = [
            mesh_velocity[0] - velocity[0],
            mesh_velocity[1] - velocity[1],
        ];
        let rate = face
            .samples
            .iter()
            .map(|samples| samples.iter().map(|s| dot(b, s.weight).abs()).sum::<f64>())
            .fold(0., f64::max);
        let potential: Vec<_> = mesh.cells.iter().map(|c| initial(c.centroid)).collect();
        if !potential.iter().all(|v| v.is_finite()) {
            return Err("nonfinite initial potential".into());
        }
        let quadratic = if quadratic {
            Some(Quadratic::build(&mesh)?)
        } else {
            None
        };
        let compact = if compact {
            Some(Compact::build(&mesh, &neighbour)?)
        } else {
            None
        };
        Ok(Self {
            compact,
            consistent,
            quadratic,
            mesh,
            potential,
            time: 0.,
            steps: 0,
            velocity,
            mesh_velocity,
            neighbour,
            face,
            dt: 0.3 / rate,
        })
    }
    fn gradient(&self, values: &[f64]) -> Result<Vec<Vec2>, String> {
        if let Some(q) = &self.quadratic {
            Ok(self.jets(q, values)?.iter().map(|j| j.gradient).collect())
        } else {
            self.neighbour.gradient(values)
        }
    }
    fn jets(
        &self,
        q: &Quadratic,
        values: &[f64],
    ) -> Result<Vec<moving_mesh::quadratic::QuadraticJet>, String> {
        if let Some(c) = &self.compact {
            c.jets(&self.neighbour, q, values)
        } else {
            q.jets(values)
        }
    }
    fn rate(&self, a: &[f64]) -> Result<Vec<f64>, String> {
        let (gradient, curvature) = if self.consistent {
            let jets = self.jets(
                self.quadratic
                    .as_ref()
                    .ok_or("consistent transport requires quadratic fit")?,
                a,
            )?;
            let g: Vec<_> = jets.iter().map(|j| j.gradient).collect();
            let h: Vec<_> = jets.iter().map(|j| j.hessian).collect();
            let factors = self.mesh.reconstruction()?.quadratic_factors(a, &g, &h)?;
            (
                g.iter()
                    .zip(&factors)
                    .map(|(g, f)| g.map(|v| v * f))
                    .collect(),
                Some(
                    h.iter()
                        .zip(&factors)
                        .map(|(h, f)| h.map(|v| v * f))
                        .collect::<Vec<_>>(),
                ),
            )
        } else {
            (self.mesh.limit_gradients(a, &self.gradient(a)?)?, None)
        };
        let b = [
            self.mesh_velocity[0] - self.velocity[0],
            self.mesh_velocity[1] - self.velocity[1],
        ];
        Ok(self
            .face
            .samples
            .iter()
            .enumerate()
            .map(|(i, samples)| {
                samples
                    .iter()
                    .map(|s| {
                        let face = &self.mesh.faces[s.index];
                        let donor = if dot(b, self.mesh.displacement(face, i)) < 0. {
                            i
                        } else {
                            self.mesh.neighbour(face, i).0
                        };
                        let up =
                            a[donor] + dot(gradient[donor], self.mesh.displacement(face, donor));
                        let correction = if let Some(h) = &curvature {
                            moving_mesh::quadratic::term(
                                h[donor],
                                self.mesh.displacement(face, donor),
                            ) - moving_mesh::quadratic::term(h[i], self.mesh.displacement(face, i))
                        } else {
                            0.
                        };
                        dot(b, s.weight)
                            * if curvature.is_some() {
                                up - a[i] + correction
                            } else {
                                up - a[i]
                            }
                    })
                    .sum()
            })
            .collect())
    }
    pub fn advance_to(&mut self, target: f64) -> Result<(), String> {
        if !target.is_finite()
            || target < self.time
            || !self.mesh_velocity.iter().all(|v| (v * target).is_finite())
        {
            return Err("invalid target".into());
        }
        if self.velocity == self.mesh_velocity {
            self.time = target;
            return Ok(());
        }
        while self.time < target {
            let dt = self.dt.min(target - self.time);
            if !dt.is_finite() || dt <= 0. || self.time + dt == self.time {
                return Err("invalid passive timestep".into());
            }
            let r0 = self.rate(&self.potential)?;
            let predictor: Vec<_> = self
                .potential
                .iter()
                .zip(&r0)
                .map(|(a, r)| a + dt * r)
                .collect();
            let r1 = self.rate(&predictor)?;
            let next: Vec<_> = self
                .potential
                .iter()
                .zip(r0)
                .zip(r1)
                .map(|((a, r0), r1)| a + 0.5 * dt * (r0 + r1))
                .collect();
            if !next.iter().all(|v| v.is_finite()) {
                return Err("nonfinite passive state".into());
            }
            self.potential = next;
            self.time += dt;
            self.steps += 1;
        }
        Ok(())
    }
    pub fn magnetic(&self) -> Result<Vec<Vec2>, String> {
        Ok(self
            .gradient(&self.potential)?
            .iter()
            .map(|g| [g[1], -g[0]])
            .collect())
    }
    pub fn positions(&self) -> Vec<Vec2> {
        self.mesh
            .cells
            .iter()
            .map(|c| {
                std::array::from_fn(|k| {
                    (c.centroid[k] + self.mesh_velocity[k] * self.time)
                        .rem_euclid(self.mesh.lengths[k])
                })
            })
            .collect()
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn compact_passive_preserves_constant_and_comoving_states_and_refines() {
        for jitter in [0., 0.15] {
            let f = |x: Vec2| (std::f64::consts::TAU * x[0]).sin();
            let mut errors = Vec::new();
            for n in [16, 32] {
                let mesh = Mesh::lattice(n, n, [1.; 2], jitter).unwrap();
                let mut fixed =
                    Passive::with_compact(mesh.clone(), [1., -0.5], [0.; 2], f).unwrap();
                fixed.advance_to(0.1).unwrap();
                errors.push(
                    fixed
                        .positions()
                        .iter()
                        .zip(fixed.potential())
                        .zip(&mesh.cells)
                        .map(|((x, a), c)| c.volume * (a - f([x[0] - 0.1, x[1] + 0.05])).abs())
                        .sum::<f64>(),
                );
                let mut rigid =
                    Passive::with_compact(mesh.clone(), [1., -0.5], [1., -0.5], f).unwrap();
                let a = rigid.potential.clone();
                let b = rigid.magnetic().unwrap();
                rigid.advance_to(0.1).unwrap();
                assert_eq!(a, rigid.potential);
                assert_eq!(b, rigid.magnetic().unwrap());
                let mut constant =
                    Passive::with_compact(mesh, [1., -0.5], [0.; 2], |_| 0.7).unwrap();
                constant.advance_to(0.1).unwrap();
                assert!(constant.potential.iter().all(|a| *a == 0.7));
            }
            assert!(errors[1] < 0.6 * errors[0], "{jitter}: {errors:?}");
        }
    }
    #[test]
    fn consistent_passive_preserves_constant_and_comoving_states_and_refines() {
        for jitter in [0., 0.15] {
            let f = |x: Vec2| (std::f64::consts::TAU * x[0]).sin();
            let mut errors = Vec::new();
            for n in [16, 32] {
                let mesh = Mesh::lattice(n, n, [1.; 2], jitter).unwrap();
                let mut fixed =
                    Passive::with_consistent(mesh.clone(), [1., -0.5], [0.; 2], f).unwrap();
                fixed.advance_to(0.1).unwrap();
                errors.push(
                    fixed
                        .positions()
                        .iter()
                        .zip(fixed.potential())
                        .zip(&mesh.cells)
                        .map(|((x, a), c)| c.volume * (a - f([x[0] - 0.1, x[1] + 0.05])).abs())
                        .sum::<f64>(),
                );
                let mut rigid =
                    Passive::with_consistent(mesh.clone(), [1., -0.5], [1., -0.5], f).unwrap();
                let a = rigid.potential.clone();
                let b = rigid.magnetic().unwrap();
                rigid.advance_to(0.1).unwrap();
                assert_eq!(a, rigid.potential);
                assert_eq!(b, rigid.magnetic().unwrap());
                let mut constant =
                    Passive::with_consistent(mesh, [1., -0.5], [0.; 2], |_| 0.7).unwrap();
                constant.advance_to(0.1).unwrap();
                assert!(constant.potential.iter().all(|a| *a == 0.7));
            }
            assert!(errors[1] < 0.6 * errors[0], "{jitter}: {errors:?}");
        }
    }
    #[test]
    fn rigid_transport_preserves_discrete_potential_and_curl_exactly() {
        for jitter in [0., 0.15] {
            let mut sim = Passive::new(
                Mesh::lattice(12, 9, [1.; 2], jitter).unwrap(),
                [2., 1.],
                [2., 1.],
                |x| (6. * x[0]).sin() * (7. * x[1]).cos(),
            )
            .unwrap();
            let a = sim.potential.clone();
            let b = sim.magnetic().unwrap();
            sim.advance_to(0.37).unwrap();
            assert_eq!(a, sim.potential);
            assert_eq!(b, sim.magnetic().unwrap());
        }
    }
    #[test]
    fn quadratic_passive_option_uses_the_quadratic_curl_and_preserves_comoving_state() {
        let mesh = Mesh::lattice(12, 12, [1.; 2], 0.15).unwrap();
        let f = |x: Vec2| (std::f64::consts::TAU * x[0]).sin();
        let linear = Passive::new(mesh.clone(), [2., 1.], [2., 1.], f).unwrap();
        let mut quad = Passive::with_quadratic(mesh.clone(), [2., 1.], [2., 1.], f, true).unwrap();
        let expected = Quadratic::build(&mesh)
            .unwrap()
            .jets(&quad.potential)
            .unwrap();
        let b = quad.magnetic().unwrap();
        assert!(
            b.iter()
                .zip(linear.magnetic().unwrap())
                .any(|(a, b)| (a[1] - b[1]).abs() > 1e-4)
        );
        for (b, j) in b.iter().zip(expected) {
            assert_eq!(*b, [j.gradient[1], -j.gradient[0]]);
        }
        let a = quad.potential.clone();
        quad.advance_to(1.).unwrap();
        assert_eq!(a, quad.potential);
        assert_eq!(b, quad.magnetic().unwrap());
    }
    #[test]
    fn smooth_fixed_transport_converges_and_constant_is_preserved() {
        for jitter in [0., 0.15] {
            let mut errors = Vec::new();
            for n in [16, 32] {
                let mut sim = Passive::new(
                    Mesh::lattice(n, n, [1.; 2], jitter).unwrap(),
                    [1., -0.5],
                    [0.; 2],
                    |x| (std::f64::consts::TAU * x[0]).sin(),
                )
                .unwrap();
                sim.advance_to(0.1).unwrap();
                errors.push(
                    sim.positions()
                        .iter()
                        .zip(&sim.potential)
                        .zip(&sim.mesh.cells)
                        .map(|((x, a), c)| {
                            c.volume * (a - (std::f64::consts::TAU * (x[0] - 0.1)).sin()).abs()
                        })
                        .sum::<f64>(),
                );
            }
            assert!(errors[1] < 0.6 * errors[0], "{jitter}: {errors:?}");
            let mut sim = Passive::new(
                Mesh::lattice(9, 8, [1.; 2], jitter).unwrap(),
                [-1., 2.],
                [0.; 2],
                |_| 0.7,
            )
            .unwrap();
            sim.advance_to(0.2).unwrap();
            assert!(sim.potential.iter().all(|a| *a == 0.7));
        }
    }
}
