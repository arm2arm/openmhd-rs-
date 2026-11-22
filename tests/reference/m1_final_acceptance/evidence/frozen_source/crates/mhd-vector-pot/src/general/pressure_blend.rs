//! Explicit Voronoi pressure-ratio stencil for the full-vector flux blend.
//! Our MHD extension, not HLLC-ADC; see docs/M1_PRESSURE_BLEND_PLAN.md.
use super::*;
use moving_mesh::Face;

const INVALID: &str = "pressure stencil requires positive finite gas pressures";

/// The stencil as defined: the smallest pressure ratio across every face of
/// the two cells. The evolution uses `cell_ratios` and `weight`, which take
/// the same minimum in two steps.
#[cfg(test)]
pub(super) fn face_weight(mesh: &Mesh, face: &Face, q: &[Primitive]) -> Result<f64, String> {
    let mut ratio = 1.0_f64;
    for i in [face.left, face.right] {
        for &(index, _) in &mesh.cells[i].faces {
            let f = &mesh.faces[index];
            let (a, b) = (q[f.left].pressure, q[f.right].pressure);
            if !a.is_finite() || !b.is_finite() || a <= 0. || b <= 0. {
                return Err(INVALID.into());
            }
            ratio = ratio.min(a.min(b) / a.max(b));
        }
    }
    // Simon & Mandal (2018) selected exponent three. Fixed, not tuned here.
    Ok(ratio.powi(3))
}

/// For every cell, the smallest pressure ratio across its own faces, capped
/// at one; `None` where one of those pressures is not positive and finite.
/// Every ratio is a positive number, so the minimum over the two cells of a
/// face is the minimum of `face_weight`, whatever the order of comparison.
pub(super) fn cell_ratios(mesh: &Mesh, q: &[Primitive]) -> Vec<Option<f64>> {
    moving_mesh::parallel::map(mesh.cells.len(), |i| {
        let mut ratio = 1.0_f64;
        for &(index, _) in &mesh.cells[i].faces {
            let f = &mesh.faces[index];
            let (a, b) = (q[f.left].pressure, q[f.right].pressure);
            if !a.is_finite() || !b.is_finite() || a <= 0. || b <= 0. {
                return None;
            }
            ratio = ratio.min(a.min(b) / a.max(b));
        }
        Some(ratio)
    })
}

/// `face_weight` from the ratios of the two cells of the face.
pub(super) fn weight(ratios: &[Option<f64>], face: &Face) -> Result<f64, String> {
    match (ratios[face.left], ratios[face.right]) {
        // Simon & Mandal (2018) selected exponent three. Fixed, not tuned here.
        (Some(left), Some(right)) => Ok(left.min(right).powi(3)),
        _ => Err(INVALID.into()),
    }
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
    fn cell_ratios_give_the_face_stencil_bit_for_bit() {
        // Lattices that other tests already build.
        for (nx, ny, lengths, jitter) in [
            (8, 8, [1.; 2], 0.),
            (8, 8, [1.; 2], 0.15),
            (16, 4, [2., 0.125], 0.15),
            (12, 10, [1., 0.8], 0.25),
            (4, 4, [1.; 2], 0.1),
        ] {
            let mesh = Mesh::lattice(nx, ny, lengths, jitter).unwrap();
            let mut state = 0x2545_f491_4f6c_dd1d_u64;
            let mut q: Vec<_> = mesh
                .cells
                .iter()
                .map(|_| {
                    state = state
                        .wrapping_mul(6364136223846793005)
                        .wrapping_add(1442695040888963407);
                    let unit = (state >> 11) as f64 / (1_u64 << 53) as f64;
                    Primitive {
                        density: 1.,
                        // Six decades, with repeated values and tiny ratios.
                        pressure: match (state >> 3) % 5 {
                            0 => 1.,
                            1 => 1e-300 * (1. + unit),
                            _ => 10_f64.powf(6. * unit - 3.),
                        },
                        velocity: [0.; 3],
                        magnetic: [0.2, 0.1, 0.],
                    }
                })
                .collect();
            for invalid in [
                None,
                Some(f64::NAN),
                Some(0.),
                Some(-1.),
                Some(f64::INFINITY),
            ] {
                if let Some(pressure) = invalid {
                    q[mesh.cells.len() / 2].pressure = pressure;
                }
                let mut failures = 0;
                for threads in [1, 3] {
                    let ratios =
                        moving_mesh::parallel::with_threads(threads, || cell_ratios(&mesh, &q))
                            .unwrap();
                    failures = 0;
                    for face in &mesh.faces {
                        let expected = face_weight(&mesh, face, &q);
                        failures += usize::from(expected.is_err());
                        assert_eq!(
                            weight(&ratios, face).map(f64::to_bits),
                            expected.map(f64::to_bits)
                        );
                    }
                }
                assert_eq!(failures > 0, invalid.is_some());
                // On the larger meshes one bad cell leaves faces that are valid.
                if mesh.cells.len() >= 64 {
                    assert!(failures < mesh.faces.len());
                }
            }
        }
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
