//! Read-only semidiscrete rate decomposition; never used to advance the state.
use super::*;

/// Rates per unit cell volume on fixed/rigid meshes. Face groups are defined
/// by |nx| >= |ny| (x group) and its complement, not by a tensor decomposition.
/// On column meshes they are exactly the x-normal and y-normal faces.
#[derive(Clone, Debug)]
pub struct FrozenRate {
    pub fluid: Conservative,
    pub fluid_faces_x: Conservative,
    pub fluid_faces_y: Conservative,
    pub magnetic_curl: Vec3,
    /// Same rigid-frame target as the projected update, including the z frame.
    pub magnetic_fv: Vec3,
    pub magnetic_unprojected: Vec3,
    pub potential: Vec3,
    pub potential_unprojected: Vec3,
}

impl Simulation {
    /// Reevaluate the production stage from immutable state and decompose its
    /// rates. This does not advance time or update fallback/step counters.
    pub fn frozen_rates(&self) -> Result<Vec<FrozenRate>, String> {
        if !matches!(self.config.motion, Motion::Fixed | Motion::Rigid(_)) {
            return Err("frozen-rate audit requires fixed or rigid geometry".into());
        }
        let old = self.prepare(&mut 0)?;
        let mesh = &self.geometry.mesh;
        let n = mesh.cells.len();
        let fit = self.magnetic_fit()?;
        let unprojected = self.config.profile.potential_rate(PotentialStage {
            mesh,
            face_stencil: &self.geometry.faces,
            potential: &self.state.potential,
            fit: &fit,
            faces: &old.fluid.fluxes,
            auxiliary: &old.auxiliary,
            advection_velocity: &old.generator_velocity,
            mean: self.config.mean_magnetic,
            reference_velocity: self.reference_velocity,
            tau: 0.,
        })?;
        let curl = |rate: &[Vec3]| -> Result<Vec<Vec3>, String> {
            Ok(MagneticFit::with_stencil(
                mesh,
                self.geometry.magnetic_stencil(),
                rate,
                &vec![0.; n],
                [0.; 3],
                false,
            )?
            .magnetic)
        };
        let projected_curl = curl(&old.potential_rate)?;
        let original_curl = curl(&unprojected)?;
        let mut fluid_x = vec![[0.; 5]; n];
        let mut fluid_y = vec![[0.; 5]; n];
        let mut target = vec![[0.; 3]; n];
        for (face, flux) in mesh.faces.iter().zip(&old.fluid.fluxes) {
            let fluid = if face.normal[0].abs() >= face.normal[1].abs() {
                &mut fluid_x
            } else {
                &mut fluid_y
            };
            for (k, value) in flux.fluid.iter().enumerate() {
                let exchange = face.area * value;
                fluid[face.left][k] -= exchange;
                fluid[face.right][k] += exchange;
            }
            let bn = flux.magnetic[0] * face.normal[0] + flux.magnetic[1] * face.normal[1];
            for (i, sign) in [(face.left, -1.), (face.right, 1.)] {
                for k in 0..3 {
                    let w = if k < 2 {
                        old.generator_velocity[0][k]
                    } else {
                        self.reference_velocity[2]
                    };
                    target[i][k] +=
                        sign * face.area * (flux.induction[k] + bn * w) / mesh.cells[i].volume;
                }
            }
        }
        Ok((0..n)
            .map(|i| FrozenRate {
                fluid: old.fluid.q[i].map(|v| v / mesh.cells[i].volume),
                fluid_faces_x: fluid_x[i].map(|v| v / mesh.cells[i].volume),
                fluid_faces_y: fluid_y[i].map(|v| v / mesh.cells[i].volume),
                magnetic_curl: projected_curl[i],
                magnetic_fv: target[i],
                magnetic_unprojected: original_curl[i],
                potential: old.potential_rate[i],
                potential_unprojected: unprojected[i],
            })
            .collect())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn frozen_face_groups_preserve_periodic_budgets_and_sum_to_production() {
        let sim = Simulation::new(
            Mesh::lattice_columns(16, 4, [2., 0.125], 0.15).unwrap(),
            Config {
                profile: Profile::BulkFrameHeunQuadraticV1,
                gamma: 2.,
                mean_magnetic: [0.75, 0., 0.],
                accelerated_projection: true,
                projection_screening: 1.,
                ..Config::default()
            },
            |p| crate::benchmarks::brio_initial(p, [0.; 3]),
        )
        .unwrap();
        let rates = sim.frozen_rates().unwrap();
        for rate in &rates {
            for k in 0..5 {
                let sum = rate.fluid_faces_x[k] + rate.fluid_faces_y[k];
                assert!((sum - rate.fluid[k]).abs() < 1e-12 * (1. + sum.abs()));
            }
            assert!(rate.magnetic_curl.iter().all(|v| v.is_finite()));
        }
        for k in 0..5 {
            for group in [false, true] {
                let total: f64 = rates
                    .iter()
                    .zip(&sim.state.mesh.cells)
                    .map(|(r, c)| {
                        c.volume
                            * if group {
                                r.fluid_faces_x[k]
                            } else {
                                r.fluid_faces_y[k]
                            }
                    })
                    .sum();
                assert!(total.abs() < 1e-12);
            }
        }
    }

    #[test]
    fn uniform_rigid_state_has_zero_rates_in_both_face_groups() {
        let sim = Simulation::new(
            Mesh::lattice_columns(8, 4, [2., 0.125], 0.15).unwrap(),
            Config {
                profile: Profile::BulkFrameHeunQuadraticV1,
                mean_magnetic: [0.75, 0.2, 0.1],
                motion: Motion::Rigid([2., -1.]),
                accelerated_projection: true,
                projection_screening: 1.,
                ..Config::default()
            },
            |_| Initial {
                density: 1.,
                pressure: 1.,
                velocity: [2., -1., 0.],
                potential: [0.; 3],
                phi: 0.,
            },
        )
        .unwrap();
        for rate in sim.frozen_rates().unwrap() {
            assert!(
                rate.fluid
                    .iter()
                    .chain(&rate.fluid_faces_x)
                    .chain(&rate.fluid_faces_y)
                    .chain(&rate.magnetic_curl)
                    .chain(&rate.magnetic_fv)
                    .chain(&rate.magnetic_unprojected)
                    .chain(&rate.potential)
                    .chain(&rate.potential_unprojected)
                    .all(|v| v.abs() < 1e-11)
            );
        }
    }
}
