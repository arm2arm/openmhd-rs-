//! Explicit Voronoi pressure-ratio stencil for the full-vector flux blend.
//! Our MHD extension, not HLLC-ADC; see docs/M1_PRESSURE_BLEND_PLAN.md.
use super::*;
use moving_mesh::Face;

pub(super) fn face_weight(mesh: &Mesh, face: &Face, q: &[Primitive]) -> Result<f64, String> {
    let mut ratio = 1.0_f64;
    for i in [face.left, face.right] {
        for &(index, _) in &mesh.cells[i].faces {
            let f = &mesh.faces[index];
            let (a, b) = (q[f.left].pressure, q[f.right].pressure);
            if !a.is_finite() || !b.is_finite() || a <= 0. || b <= 0. {
                return Err("pressure stencil requires positive finite gas pressures".into());
            }
            ratio = ratio.min(a.min(b) / a.max(b));
        }
    }
    // Simon & Mandal (2018) selected exponent three. Fixed, not tuned here.
    Ok(ratio.powi(3))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pressure_stencil_is_symmetric_scale_invariant_and_detects_transverse_jump() {
        let mesh = Mesh::lattice(8, 8, [1.; 2], 0.).unwrap();
        let primitive = Primitive {
            density: 1.,
            pressure: 1.,
            velocity: [0.; 3],
            magnetic: [0.2, 0.1, 0.],
        };
        let mut q = vec![primitive; mesh.cells.len()];
        let f = mesh
            .faces
            .iter()
            .find(|f| f.normal[0] == 1. && f.centroid.iter().all(|x| *x > 0.3 && *x < 0.7))
            .unwrap();
        assert_eq!(face_weight(&mesh, f, &q).unwrap(), 1.);
        let j = mesh.cells[f.left]
            .faces
            .iter()
            .find_map(|&(index, _)| {
                let g = &mesh.faces[index];
                (g.normal[1].abs() == 1.).then(|| mesh.neighbour(g, f.left).0)
            })
            .unwrap();
        q[j].pressure = 0.5;
        assert_eq!(q[f.left].pressure, q[f.right].pressure);
        assert_eq!(face_weight(&mesh, f, &q).unwrap(), 0.125);
        let mut reversed = f.clone();
        std::mem::swap(&mut reversed.left, &mut reversed.right);
        reversed.normal = reversed.normal.map(|x| -x);
        assert_eq!(face_weight(&mesh, &reversed, &q).unwrap(), 0.125);
        for cell in &mut q {
            cell.pressure *= 8.;
            cell.velocity = [2., -1., 0.];
        }
        assert_eq!(face_weight(&mesh, &reversed, &q).unwrap(), 0.125);
        q[j].pressure = f64::NAN;
        assert!(face_weight(&mesh, f, &q).is_err());
    }

    #[test]
    fn irregular_periodic_pressure_stencil_is_rotation_invariant() {
        let mesh = Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap();
        let q: Vec<_> = mesh
            .cells
            .iter()
            .map(|c| Primitive {
                density: 1.,
                pressure: 1. + 0.2 * (6. * c.centroid[0]).sin(),
                velocity: [0.; 3],
                magnetic: [0.2, 0.1, 0.],
            })
            .collect();
        let mut rotated = mesh.clone();
        for f in &mut rotated.faces {
            f.normal = [-f.normal[1], f.normal[0]];
            f.centroid = [-f.centroid[1], f.centroid[0]];
            f.image = [-f.image[1], f.image[0]];
        }
        let mut periodic = 0;
        for (i, f) in mesh.faces.iter().enumerate() {
            periodic += usize::from(f.image != [0; 2]);
            assert_eq!(
                face_weight(&mesh, f, &q).unwrap(),
                face_weight(&rotated, &rotated.faces[i], &q).unwrap()
            );
        }
        assert!(periodic > 0);
    }

    #[test]
    fn pressure_blend_audit_preserves_state_and_periodic_budgets() {
        let mut sim = Simulation::new(
            Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap(),
            Config {
                profile: Profile::BulkFrameHeunQuadraticV1,
                riemann_solver: RiemannSolver::HlldPressure,
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
        let audit = sim.frozen_shock_faces().unwrap();
        assert!(
            audit
                .iter()
                .any(|f| f.method == FluxMethod::HlldPressure && f.factor < 1.)
        );
        assert_eq!(sim.state().conserved, before);
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
