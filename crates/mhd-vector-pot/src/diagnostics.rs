//! Three distinct magnetic-divergence operators; none is assumed identically zero.
use crate::general::Simulation;
use mhd_core::{Conservative, Vec3, dot as dot3};
use moving_mesh::{Derivatives, Mesh, dot};
use std::f64::consts::PI;

#[derive(Clone, Copy, Debug)]
pub struct Norms {
    pub mean: f64,
    pub rms: f64,
    pub max: f64,
}
#[derive(Clone, Debug)]
pub struct Divergence {
    pub values: Vec<f64>,
    pub dimensional: Norms,
    pub dimensionless: Norms,
}
#[derive(Clone, Debug)]
pub struct Diagnostics {
    pub neighbour_condition: f64,
    pub face_condition: f64,
    pub totals: Conservative,
    pub normalized_budget: Conservative,
    pub budget_scales: Conservative,
    pub min_density: f64,
    pub min_pressure: f64,
    pub max_density: f64,
    pub max_pressure: f64,
    pub magnetic_energy: f64,
    pub mean_magnetic: Vec3,
    pub mean_magnetic_drift: Vec3,
    pub divergence_ls: Divergence,
    pub divergence_face: Divergence,
    pub divergence_limited_face: Divergence,
    pub divergence_a: Norms,
    pub phi: Norms,
}
impl Simulation {
    pub fn diagnostics(&self) -> Result<Diagnostics, String> {
        let state = self.state();
        let mesh = &state.mesh;
        let q = self.primitives()?;
        let fit = self.magnetic_fit()?;
        let stencil = Derivatives::build(mesh, false)?;
        let magnetic: Vec<_> = q.iter().map(|q| q.magnetic).collect();
        let [ls, face_sum, limited_sum] = divergence_values(mesh, &stencil, &magnetic)?;
        let volume: f64 = mesh.cells.iter().map(|c| c.volume).sum();
        let norms = |v: &[f64]| Norms {
            mean: v
                .iter()
                .zip(&mesh.cells)
                .map(|(v, c)| v * c.volume)
                .sum::<f64>()
                / volume,
            rms: (v
                .iter()
                .zip(&mesh.cells)
                .map(|(v, c)| v * v * c.volume)
                .sum::<f64>()
                / volume)
                .sqrt(),
            max: v.iter().map(|v| v.abs()).fold(0., f64::max),
        };
        let divergence = |values: Vec<f64>| {
            let scaled: Vec<_> = values
                .iter()
                .enumerate()
                .map(|(i, d)| {
                    let b = q[i].magnetic;
                    (mesh.cells[i].volume / PI).sqrt() * d
                        / (b[0].hypot(b[1]).hypot(b[2]) + 1e-12 * self.config().magnetic_scale)
                })
                .collect();
            Divergence {
                dimensional: norms(&values),
                dimensionless: norms(&scaled),
                values,
            }
        };
        let totals: Conservative =
            std::array::from_fn(|k| state.conserved.iter().map(|q| q[k]).sum());
        let mean_magnetic: Vec3 = std::array::from_fn(|k| {
            q.iter()
                .zip(&mesh.cells)
                .map(|(q, c)| q.magnetic[k] * c.volume)
                .sum::<f64>()
                / volume
        });
        let result = Diagnostics {
            neighbour_condition: stencil.worst_condition,
            face_condition: Derivatives::build(mesh, true)?.worst_condition,
            totals,
            normalized_budget: std::array::from_fn(|k| {
                (totals[k] - self.initial_totals[k]) / self.budget_scales[k]
            }),
            budget_scales: self.budget_scales,
            min_density: q.iter().map(|q| q.density).fold(f64::INFINITY, f64::min),
            min_pressure: q.iter().map(|q| q.pressure).fold(f64::INFINITY, f64::min),
            max_density: q.iter().map(|q| q.density).fold(0., f64::max),
            max_pressure: q.iter().map(|q| q.pressure).fold(0., f64::max),
            magnetic_energy: q
                .iter()
                .zip(&mesh.cells)
                .map(|(q, c)| 0.5 * c.volume * dot3(q.magnetic, q.magnetic))
                .sum(),
            mean_magnetic,
            mean_magnetic_drift: std::array::from_fn(|k| mean_magnetic[k] - self.initial_mean[k]),
            divergence_ls: divergence(ls),
            divergence_face: divergence(face_sum),
            divergence_limited_face: divergence(limited_sum),
            divergence_a: norms(&fit.divergence_a),
            phi: norms(&state.phi),
        };
        let scalar = [
            result.neighbour_condition,
            result.face_condition,
            result.min_density,
            result.min_pressure,
            result.max_density,
            result.max_pressure,
            result.magnetic_energy,
            result.divergence_a.mean,
            result.divergence_a.rms,
            result.divergence_a.max,
            result.phi.mean,
            result.phi.rms,
            result.phi.max,
        ];
        if !scalar
            .iter()
            .chain(&result.totals)
            .chain(&result.normalized_budget)
            .chain(&result.budget_scales)
            .chain(&result.mean_magnetic)
            .chain(&result.mean_magnetic_drift)
            .all(|x| x.is_finite())
        {
            return Err("nonfinite diagnostics".into());
        }
        for d in [
            &result.divergence_ls,
            &result.divergence_face,
            &result.divergence_limited_face,
        ] {
            if ![
                d.dimensional.mean,
                d.dimensional.rms,
                d.dimensional.max,
                d.dimensionless.mean,
                d.dimensionless.rms,
                d.dimensionless.max,
            ]
            .iter()
            .chain(&d.values)
            .all(|x| x.is_finite())
            {
                return Err("nonfinite divergence diagnostic".into());
            }
        }
        Ok(result)
    }
}

/// Raw neighbour LS, arithmetic shared-face and limited shared-face divergences.
/// The supplied stencil must be the neighbour-centre stencil for this mesh.
pub(crate) fn divergence_values(
    mesh: &Mesh,
    stencil: &Derivatives,
    magnetic: &[Vec3],
) -> Result<[Vec<f64>; 3], String> {
    let bx: Vec<_> = magnetic.iter().map(|b| b[0]).collect();
    let by: Vec<_> = magnetic.iter().map(|b| b[1]).collect();
    let gx = stencil.gradient(&bx)?;
    let gy = stencil.gradient(&by)?;
    let lx = mesh.limit_gradients(&bx, &gx)?;
    let ly = mesh.limit_gradients(&by, &gy)?;
    let ls = (0..magnetic.len()).map(|i| gx[i][0] + gy[i][1]).collect();
    let mut face_sum = vec![0.; magnetic.len()];
    let mut limited_sum = vec![0.; magnetic.len()];
    for f in &mesh.faces {
        let bn = 0.5
            * ((bx[f.left] + bx[f.right]) * f.normal[0] + (by[f.left] + by[f.right]) * f.normal[1]);
        let dl = mesh.displacement(f, f.left);
        let dr = mesh.displacement(f, f.right);
        let bl = bn
            + 0.5
                * (f.normal[0] * (dot(lx[f.left], dl) + dot(lx[f.right], dr))
                    + f.normal[1] * (dot(ly[f.left], dl) + dot(ly[f.right], dr)));
        for (i, sign) in [(f.left, 1.), (f.right, -1.)] {
            face_sum[i] += sign * f.area * bn / mesh.cells[i].volume;
            limited_sum[i] += sign * f.area * bl / mesh.cells[i].volume;
        }
    }
    Ok([ls, face_sum, limited_sum])
}
