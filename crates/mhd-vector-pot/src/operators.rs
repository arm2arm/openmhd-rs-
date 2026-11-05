//! 2.5D operators for the reviewed paper-global-v2 endpoint scheme.
//! Derivatives are [component][x/y]; physical vectors retain all three components.
use crate::auxiliary::SmoothVelocity;
use mhd_core::{FaceFlux, IdealGas, Primitive, Vec3, cross};
use moving_mesh::{Derivatives, Face, Mesh, Vec2, dot, quadratic::Quadratic};

pub type PrimitiveGradient = [Vec2; 8];

pub(crate) fn components(q: Primitive) -> [f64; 8] {
    [
        q.density,
        q.velocity[0],
        q.velocity[1],
        q.velocity[2],
        q.pressure,
        q.magnetic[0],
        q.magnetic[1],
        q.magnetic[2],
    ]
}
pub(crate) fn primitive(q: [f64; 8]) -> Result<Primitive, String> {
    let p = Primitive {
        density: q[0],
        velocity: [q[1], q[2], q[3]],
        pressure: q[4],
        magnetic: [q[5], q[6], q[7]],
    };
    p.validate()?;
    Ok(p)
}
pub(crate) fn gradients<const N: usize>(
    mesh: &Mesh,
    stencil: &Derivatives,
    values: &[[f64; N]],
    limited: bool,
) -> Result<Vec<[Vec2; N]>, String> {
    let mut result = vec![[[0.; 2]; N]; mesh.cells.len()];
    let reconstruction = if limited {
        Some(mesh.reconstruction()?)
    } else {
        None
    };
    for k in 0..N {
        let scalar: Vec<_> = values.iter().map(|v| v[k]).collect();
        let mut grad = stencil.gradient(&scalar)?;
        if let Some(reconstruction) = &reconstruction {
            grad = reconstruction.limit_gradients(&scalar, &grad)?;
        }
        for (out, g) in result.iter_mut().zip(grad) {
            out[k] = g;
        }
    }
    Ok(result)
}

#[derive(Clone, Debug)]
pub struct MagneticFit {
    pub raw: Vec<[Vec2; 3]>,
    pub limited: Vec<[Vec2; 3]>,
    pub magnetic: Vec<Vec3>,
    pub divergence_a: Vec<f64>,
    pub gradient_phi: Vec<Vec2>,
}
impl MagneticFit {
    pub fn build(
        mesh: &Mesh,
        potential: &[Vec3],
        phi: &[f64],
        mean: Vec3,
        limited: bool,
    ) -> Result<Self, String> {
        let stencil = Derivatives::build(mesh, false)?;
        Self::with_stencil(mesh, (&stencil, None), potential, phi, mean, limited)
    }
    pub(crate) fn with_stencil(
        mesh: &Mesh,
        stencils: (&Derivatives, Option<&Quadratic>),
        potential: &[Vec3],
        phi: &[f64],
        mean: Vec3,
        limited: bool,
    ) -> Result<Self, String> {
        if !mean.iter().all(|x| x.is_finite()) {
            return Err("nonfinite mean field".into());
        }
        let (stencil, quadratic) = stencils;
        let raw = if let Some(quadratic) = quadratic {
            let mut raw = vec![[[0.; 2]; 3]; mesh.cells.len()];
            for k in 0..3 {
                let values: Vec<_> = potential.iter().map(|a| a[k]).collect();
                for (g, jet) in raw.iter_mut().zip(quadratic.jets(&values)?) {
                    g[k] = jet.gradient;
                }
            }
            raw
        } else {
            gradients(mesh, stencil, potential, false)?
        };
        let extrapolation = if limited && quadratic.is_some() {
            let guard = mesh.reconstruction()?;
            let mut extrapolation = raw.clone();
            for k in 0..3 {
                let values: Vec<_> = potential.iter().map(|a| a[k]).collect();
                let gradient: Vec<_> = raw.iter().map(|g| g[k]).collect();
                for (out, g) in extrapolation
                    .iter_mut()
                    .zip(guard.limit_gradients(&values, &gradient)?)
                {
                    out[k] = g;
                }
            }
            extrapolation
        } else if limited {
            gradients(mesh, stencil, potential, true)?
        } else {
            raw.clone()
        };
        let magnetic: Vec<Vec3> = raw
            .iter()
            .map(|g| {
                [
                    mean[0] + g[2][1],
                    mean[1] - g[2][0],
                    mean[2] + g[1][0] - g[0][1],
                ]
            })
            .collect();
        let divergence_a: Vec<f64> = raw.iter().map(|g| g[0][0] + g[1][1]).collect();
        if !magnetic
            .iter()
            .flatten()
            .chain(&divergence_a)
            .all(|x| x.is_finite())
        {
            return Err("curl/divergence arithmetic overflow".into());
        }
        Ok(Self {
            raw,
            limited: extrapolation,
            magnetic,
            divergence_a,
            gradient_phi: stencil.gradient(phi)?,
        })
    }
}

/// Solenoidal material predictor (U1): deliberately omits v * estimated div(B).
/// This local algebra assumes validated q/gradients; predictor outputs are checked.
pub fn material_derivative(eos: IdealGas, q: Primitive, g: PrimitiveGradient) -> [f64; 8] {
    let theta = g[1][0] + g[2][1];
    let current = [g[7][1], -g[7][0], g[6][0] - g[5][1]];
    let force = cross(current, q.magnetic);
    let mut rate = [0.; 8];
    rate[0] = -q.density * theta;
    rate[4] = -eos.gamma() * q.pressure * theta;
    for k in 0..3 {
        rate[1 + k] = (force[k] - if k < 2 { g[4][k] } else { 0. }) / q.density;
        rate[5 + k] =
            g[1 + k][0] * q.magnetic[0] + g[1 + k][1] * q.magnetic[1] - q.magnetic[k] * theta;
    }
    rate
}

/// Offset is the *unwrapped* new evaluation point minus the old cell centroid.
pub fn predict(
    eos: IdealGas,
    q: Primitive,
    g: PrimitiveGradient,
    offset: Vec2,
    dt: f64,
) -> Result<Primitive, String> {
    if !dt.is_finite()
        || dt < 0.
        || !offset
            .iter()
            .chain(g.iter().flatten())
            .all(|x| x.is_finite())
    {
        return Err("invalid predictor data".into());
    }
    q.validate()?;
    let material = material_derivative(eos, q, g);
    let displacement = [
        offset[0] - dt * q.velocity[0],
        offset[1] - dt * q.velocity[1],
    ];
    let old = components(q);
    primitive(std::array::from_fn(|k| {
        old[k] + dot(g[k], displacement) + dt * material[k]
    }))
}

/// Differentiated Voronoi bisector speed; mesh must be validated and face incident.
pub fn face_velocity(
    mesh: &Mesh,
    face: &Face,
    generators_velocity: &[Vec2],
) -> Result<Vec3, String> {
    if generators_velocity.len() != mesh.cells.len() {
        return Err("generator velocity length".into());
    }
    let ri = mesh.generators[face.left];
    let rj: Vec2 = std::array::from_fn(|k| {
        mesh.generators[face.right][k] + f64::from(face.image[k]) * mesh.lengths[k]
    });
    let d: Vec2 = std::array::from_fn(|k| rj[k] - ri[k]);
    let f: Vec2 = std::array::from_fn(|k| face.centroid[k] - 0.5 * (ri[k] + rj[k]));
    let wi = generators_velocity[face.left];
    let wj = generators_velocity[face.right];
    let correction = dot([wi[0] - wj[0], wi[1] - wj[1]], f) / dot(d, d);
    let result = [
        0.5 * (wi[0] + wj[0]) + d[0] * correction,
        0.5 * (wi[1] + wj[1]) + d[1] * correction,
        0.,
    ];
    if !result.iter().all(|x| x.is_finite()) {
        return Err("invalid moving bisector velocity".into());
    }
    Ok(result)
}

pub(crate) struct PotentialStage<'a> {
    pub mesh: &'a Mesh,
    pub face_stencil: &'a Derivatives,
    pub potential: &'a [Vec3],
    pub fit: &'a MagneticFit,
    pub faces: &'a [FaceFlux],
    pub auxiliary: &'a SmoothVelocity,
    pub advection_velocity: &'a [Vec2],
    pub mean: Vec3,
    pub reference_velocity: Vec3,
    pub tau: f64,
}
impl PotentialStage<'_> {
    /// Paper (69)-(72),(76); numerical EMF must not be replaced by a state product.
    pub fn rate(&self) -> Result<Vec<Vec3>, String> {
        self.mesh
            .cells
            .iter()
            .enumerate()
            .map(|(i, cell)| {
                let aux = self.auxiliary.sample(cell.centroid, self.tau)?;
                let b = [
                    self.advection_velocity[i][0] - aux.velocity[0],
                    self.advection_velocity[i][1] - aux.velocity[1],
                ];
                let perimeter: f64 = cell
                    .faces
                    .iter()
                    .map(|(f, _)| self.mesh.faces[*f].area)
                    .sum();
                // BulkFrameV1 changes the gauge, not the lab-frame fluid fluxes.
                // Substituting A=a+C into the original gauge alone would leave
                // -H^T C; its deliberate omission is documented in the profile.
                let mean_source = cross(
                    std::array::from_fn(|k| aux.velocity[k] - self.reference_velocity[k]),
                    self.mean,
                );
                let mut result: Vec3 = std::array::from_fn(|k| {
                    mean_source[k]
                        - (0..3)
                            .map(|a| aux.jacobian[a][k] * self.potential[i][a])
                            .sum::<f64>()
                        + if k < 2 {
                            self.fit.gradient_phi[i][k]
                        } else {
                            0.
                        }
                });
                for &(f, _) in &cell.faces {
                    let face = &self.faces[f];
                    let ux_b = cross(aux.velocity, face.magnetic);
                    for k in 0..3 {
                        result[k] +=
                            self.mesh.faces[f].area / perimeter * (face.electromotive[k] - ux_b[k]);
                    }
                }
                for sample in &self.face_stencil.samples[i] {
                    let face = &self.mesh.faces[sample.index];
                    let displacement = self.mesh.displacement(face, i);
                    let donor = if dot(b, displacement) < 0. {
                        i
                    } else {
                        self.mesh.neighbour(face, i).0
                    };
                    let donor_offset = self.mesh.displacement(face, donor);
                    for (k, r) in result.iter_mut().enumerate() {
                        let up = self.potential[donor][k]
                            + dot(self.fit.limited[donor][k], donor_offset);
                        *r += dot(b, sample.weight) * (up - self.potential[i][k]);
                    }
                }
                if !result.iter().all(|x| x.is_finite()) {
                    return Err("nonfinite potential rate".into());
                }
                Ok(result)
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::auxiliary::VelocitySample;
    use mhd_core::FluxMethod;
    #[test]
    fn upwind_donors_and_numerical_emf_use_all_components() {
        let mesh = Mesh::lattice(6, 6, [1.; 2], 0.).unwrap();
        let i = 14; // interior (x index 2, y index 2)
        let mut potential = vec![[0.; 3]; 36];
        for (index, value) in [(i, 0.2), (i - 1, -0.1), (i + 1, 0.9)] {
            potential[index] = [value, 2. * value, -3. * value];
        }
        let mut fit = MagneticFit::build(&mesh, &potential, &vec![0.; 36], [0.; 3], false).unwrap();
        fit.limited.fill([[0.; 2]; 3]); // controlled donor fixture, discontinuous data
        fit.gradient_phi.fill([0.13, -0.12]);
        let u = [0.4, -0.2, 0.3];
        let bfield = [0.2, 0.3, 0.4];
        let mean = [0.3, -0.2, 0.1];
        let emf = [0.03, 0.07, 0.09]; // deliberately different from the face state product
        let flux = FaceFlux {
            fluid: [0.; 5],
            induction: [0.; 3],
            electromotive: emf,
            velocity: [0.; 3],
            magnetic: bfield,
            max_speed: 1.,
            method: FluxMethod::HllFallback,
        };
        let fluxes = vec![flux; mesh.faces.len()];
        let samples: Vec<_> = mesh
            .cells
            .iter()
            .map(|c| VelocitySample {
                position: c.centroid,
                volume: c.volume,
                velocity: u,
            })
            .collect();
        let aux = SmoothVelocity::build([1.; 2], &samples, [0.; 2]).unwrap();
        let faces = Derivatives::build(&mesh, true).unwrap();
        for (speed, delta) in [(0.7, 0.9 - 0.2), (-0.6, 0.2 - (-0.1))] {
            let w = vec![[u[0] + speed, u[1]]; 36];
            let result = PotentialStage {
                mesh: &mesh,
                face_stencil: &faces,
                potential: &potential,
                fit: &fit,
                faces: &fluxes,
                auxiliary: &aux,
                advection_velocity: &w,
                mean,
                reference_velocity: [0.; 3],
                tau: 0.,
            }
            .rate()
            .unwrap();
            let ux_b = cross(u, bfield);
            let ux_mean = cross(u, mean);
            for (k, multiplier) in [1., 2., -3.].iter().enumerate() {
                let exact = emf[k] - ux_b[k]
                    + ux_mean[k]
                    + if k < 2 { fit.gradient_phi[i][k] } else { 0. }
                    + speed * 6. * delta * multiplier;
                assert!(
                    (result[i][k] - exact).abs() < 1e-11,
                    "{} != {exact}",
                    result[i][k]
                );
            }
        }
    }
    #[test]
    fn live_distortion_transposes_the_full_auxiliary_jacobian() {
        let mesh = Mesh::lattice(8, 8, [1.; 2], 0.15).unwrap();
        let a = [0.2, -0.4, 0.7];
        let potential = vec![a; mesh.cells.len()];
        let fit = MagneticFit::build(&mesh, &potential, &vec![0.; potential.len()], [0.; 3], true)
            .unwrap();
        let samples: Vec<_> = mesh
            .cells
            .iter()
            .map(|c| {
                let x = std::f64::consts::TAU * c.centroid[0];
                let y = std::f64::consts::TAU * c.centroid[1];
                VelocitySample {
                    position: c.centroid,
                    volume: c.volume,
                    velocity: [
                        0.1 * x.sin() + 0.02 * y.cos(),
                        0.2 * x.cos() + 0.03 * y.sin(),
                        0.07 * x.sin() - 0.04 * y.cos(),
                    ],
                }
            })
            .collect();
        let aux = SmoothVelocity::build(mesh.lengths, &samples, [0.; 2]).unwrap();
        let sampled: Vec<_> = mesh
            .cells
            .iter()
            .map(|c| aux.sample(c.centroid, 0.).unwrap())
            .collect();
        let w: Vec<_> = sampled
            .iter()
            .map(|u| [u.velocity[0], u.velocity[1]])
            .collect();
        let fluxes = vec![
            FaceFlux {
                fluid: [0.; 5],
                induction: [0.; 3],
                electromotive: [0.; 3],
                velocity: [0.; 3],
                magnetic: [0.; 3],
                max_speed: 1.,
                method: FluxMethod::HllFallback
            };
            mesh.faces.len()
        ];
        let stencil = Derivatives::build(&mesh, true).unwrap();
        let rate = PotentialStage {
            mesh: &mesh,
            face_stencil: &stencil,
            potential: &potential,
            fit: &fit,
            faces: &fluxes,
            auxiliary: &aux,
            advection_velocity: &w,
            mean: [0.; 3],
            reference_velocity: [0.; 3],
            tau: 0.,
        }
        .rate()
        .unwrap();
        let mut z_coupling = 0_f64;
        for (r, u) in rate.iter().zip(sampled) {
            let h = u.jacobian;
            let exact = [
                -0.2 * h[0][0] + 0.4 * h[1][0] - 0.7 * h[2][0],
                -0.2 * h[0][1] + 0.4 * h[1][1] - 0.7 * h[2][1],
                0.,
            ];
            for k in 0..3 {
                assert!((r[k] - exact[k]).abs() < 1e-11);
            }
            z_coupling = z_coupling.max(h[2][0].abs()).max(h[2][1].abs());
        }
        assert!(z_coupling > 0.1);
    }
}
