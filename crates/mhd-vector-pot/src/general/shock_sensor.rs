//! Explicit Voronoi extension of the Cartesian transverse-compression sensor.
//! See docs/M1_SHOCK_SENSOR_PLAN.md; this is not an AREPO algorithm claim.
use super::*;
use mhd_core::ShockSensor;
use moving_mesh::Face;

pub(super) fn face_sensor(
    mesh: &Mesh,
    face: &Face,
    q: &[Primitive],
) -> Result<ShockSensor, String> {
    let tangent = [-face.normal[1], face.normal[0]];
    let difference = |i: usize, j: usize| {
        [
            q[j].velocity[0] - q[i].velocity[0],
            q[j].velocity[1] - q[i].velocity[1],
        ]
    };
    let normal_difference = dot(difference(face.left, face.right), face.normal);
    let mut transverse_difference = 0.0_f64;
    for i in [face.left, face.right] {
        for &(f, _) in &mesh.cells[i].faces {
            let (j, d) = mesh.neighbour(&mesh.faces[f], i);
            let length = d[0].hypot(d[1]);
            if !length.is_finite() || length <= 0. {
                return Err("invalid shock-sensor neighbour displacement".into());
            }
            let jump = dot(difference(i, j), tangent) * dot(d, tangent) / length;
            if !jump.is_finite() {
                return Err("nonfinite shock-sensor velocity difference".into());
            }
            transverse_difference = transverse_difference.min(jump);
        }
    }
    Ok(ShockSensor {
        normal_difference,
        transverse_difference,
    })
}

#[derive(Clone, Debug)]
pub struct ShockFaceAudit {
    pub face: usize,
    pub theta: f64,
    pub method: FluxMethod,
    pub corrected: Conservative,
    /// HLLD flux on exactly the same frozen reconstructed state.
    pub historical: Conservative,
}

impl Simulation {
    /// Immutable final-state observation, not an evolution or cumulative count.
    pub fn frozen_shock_faces(&self) -> Result<Vec<ShockFaceAudit>, String> {
        if self.config.riemann_solver != RiemannSolver::HlldShock {
            return Err("shock-face audit requires the explicit shock comparator".into());
        }
        let old = self.prepare(&mut 0)?;
        let control = fluid_rate(
            (
                IdealGas::new(self.config.gamma)?,
                self.config.profile.completion(),
                false,
                RiemannSolver::Hlld,
            ),
            &old.geometry,
            (&old.primitive, &old.gradients),
            &old.generator_velocity,
            &vec![[0.; 2]; old.primitive.len()],
            0.,
            &mut 0,
        )?;
        Ok(old
            .fluid
            .fluxes
            .iter()
            .zip(&control.fluxes)
            .enumerate()
            .map(|(face, (new, old))| ShockFaceAudit {
                face,
                theta: new.shock_factor,
                method: new.method,
                corrected: new.fluid,
                historical: old.fluid,
            })
            .collect())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn primitive(v: Vec3) -> Primitive {
        Primitive {
            density: 1.,
            pressure: 1.,
            velocity: v,
            magnetic: [0.2, 0.1, 0.],
        }
    }
    fn close(a: f64, b: f64) {
        assert!(
            (a - b).abs() < 2e-13 * (1. + a.abs() + b.abs()),
            "{a} != {b}"
        );
    }

    #[test]
    fn cartesian_affine_sensor_reduces_to_transverse_velocity_differences() {
        let mesh = Mesh::lattice(8, 6, [1.; 2], 0.).unwrap();
        let q: Vec<_> = mesh
            .cells
            .iter()
            .map(|c| {
                let [x, y] = c.centroid;
                primitive([-2. * x + 0.3 * y, 0.7 * x - 3. * y, 0.])
            })
            .collect();
        let f = mesh
            .faces
            .iter()
            .find(|f| f.normal[0] == 1. && f.centroid.iter().all(|x| *x > 0.3 && *x < 0.7))
            .unwrap();
        let s = face_sensor(&mesh, f, &q).unwrap();
        close(s.normal_difference, -2. / 8.);
        close(s.transverse_difference, -3. / 6.);
        close(s.factor(1.).unwrap(), (1.25_f64 / 1.5).powi(4));
    }

    #[test]
    fn irregular_periodic_sensor_preserves_owner_reversal_boost_and_rotation() {
        let mesh = Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap();
        let q: Vec<_> = mesh
            .cells
            .iter()
            .map(|c| primitive([(6. * c.centroid[0]).sin(), (5. * c.centroid[1]).cos(), 0.]))
            .collect();
        let boost: Vec<_> = q
            .iter()
            .map(|q| primitive([q.velocity[0] + 2., q.velocity[1] - 1., 0.7]))
            .collect();
        let rotate = |p: Vec2| [-p[1], p[0]];
        let mut rotated = mesh.clone();
        for c in &mut rotated.cells {
            c.centroid = rotate(c.centroid);
        }
        for f in &mut rotated.faces {
            f.centroid = rotate(f.centroid);
            f.normal = rotate(f.normal);
            f.image = [-f.image[1], f.image[0]];
        }
        let rq: Vec<_> = q
            .iter()
            .map(|q| primitive([-q.velocity[1], q.velocity[0], q.velocity[2]]))
            .collect();
        let mut periodic = 0;
        for (i, f) in mesh.faces.iter().enumerate() {
            if f.image != [0; 2] {
                periodic += 1;
            }
            let a = face_sensor(&mesh, f, &q).unwrap();
            let mut reversed = f.clone();
            std::mem::swap(&mut reversed.left, &mut reversed.right);
            reversed.normal = reversed.normal.map(|x| -x);
            reversed.image = reversed.image.map(|x| -x);
            for b in [
                face_sensor(&mesh, &reversed, &q).unwrap(),
                face_sensor(&mesh, f, &boost).unwrap(),
                face_sensor(&rotated, &rotated.faces[i], &rq).unwrap(),
            ] {
                close(a.normal_difference, b.normal_difference);
                close(a.transverse_difference, b.transverse_difference);
                close(a.factor(1.).unwrap(), b.factor(1.).unwrap());
            }
        }
        assert!(periodic > 0);
    }

    #[test]
    fn active_sensor_audit_preserves_state_and_periodic_conservative_exchange() {
        let mut sim = Simulation::new(
            Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap(),
            Config {
                profile: Profile::BulkFrameHeunQuadraticV1,
                riemann_solver: RiemannSolver::HlldShock,
                accelerated_projection: true,
                projection_screening: 1.,
                mean_magnetic: [0.2, 0.1, 0.],
                max_dt: 0.0001,
                ..Config::default()
            },
            |p| Initial {
                density: 1.,
                pressure: 1. + 0.1 * (6. * p[1]).cos(),
                velocity: [0.3 * (6. * p[0]).sin(), 0.1 * (6. * p[1]).cos(), 0.],
                potential: [0.; 3],
                phi: 0.,
            },
        )
        .unwrap();
        let before = sim.state().conserved.clone();
        let steps = sim.counters().steps;
        let audit = sim.frozen_shock_faces().unwrap();
        assert!(
            audit
                .iter()
                .any(|f| f.method == FluxMethod::HlldShock && f.theta < 1.)
        );
        assert_eq!(sim.state().conserved, before);
        assert_eq!(sim.counters().steps, steps);
        let rates = sim.frozen_rates().unwrap();
        for k in 0..5 {
            let sum: f64 = rates
                .iter()
                .zip(&sim.state().mesh.cells)
                .map(|(r, c)| r.fluid[k] * c.volume)
                .sum();
            assert!(sum.abs() < 1e-12);
        }
        sim.advance_to(0.0002).unwrap();
        let d = sim.diagnostics().unwrap();
        assert!(d.min_density > 0. && d.min_pressure > 0.);
        assert!(d.normalized_budget.iter().all(|x| x.abs() < 1e-12));
    }
}
