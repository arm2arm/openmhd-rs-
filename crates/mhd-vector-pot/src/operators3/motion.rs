//! The fixed-sample partial derivative on a smooth periodic geometry branch.
use super::{DiscreteCurl3, coalesce, sub};
use moving_mesh::three_d::{
    Boundary3, GeometryEpoch3, MotionRates3, ValidatedGeometry3,
    fit::{FitError3, FitOrder3},
    operator_mesh::OperatorMesh3,
};

/// The accepted periodic quadratic point curl and its derivative for one
/// geometry and prescribed generator trajectory. Rebuild after a geometry
/// change or change of velocities. Wall constraints use a different fit.
pub struct MovingPointCurl3 {
    epoch: GeometryEpoch3,
    trajectory: [u8; 32],
    curl: DiscreteCurl3,
    tangent: DiscreteCurl3,
    max_condition: f64,
    max_inverse_r_norm: f64,
}

impl MovingPointCurl3 {
    pub const FIT_POLICY: &'static str = "periodic-ls-quadratic-point-curl-v1";

    pub fn assemble(g: &ValidatedGeometry3, motion: &MotionRates3) -> Result<Self, FitError3> {
        if g.domain().boundary != Boundary3::Periodic {
            return Err(FitError3::UnsupportedBoundary);
        }
        if motion.epoch() != g.epoch() {
            return Err(FitError3::MotionMismatch);
        }
        let mesh = OperatorMesh3::from_validated(g)?;
        let count = mesh.cells().len();
        let cells = (0..count)
            .map(|i| {
                let handle = g.cell_ref(i).map_err(|_| FitError3::InvalidSample)?;
                motion
                    .cell(handle)
                    .copied()
                    .map_err(|_| FitError3::MotionMismatch)
            })
            .collect::<Result<Vec<_>, _>>()?;
        let mut fits = Vec::with_capacity(count);
        let mut rows = Vec::with_capacity(count);
        let mut max_condition = 0.0_f64;
        let mut max_inverse_r_norm = 0.0_f64;
        let local = moving_mesh::parallel::map_indexed(count, std::num::NonZeroUsize::MIN, |i| {
            let cell = &cells[i];
            let fit = mesh.fit(i, FitOrder3::Quadratic)?;
            let velocities: Vec<_> = fit
                .owners
                .iter()
                .map(|&owner| sub(cells[owner].centroid_velocity, cell.centroid_velocity))
                .collect();
            let weights = fit
                .fit
                .quadratic_gradient_rate(&velocities, cell.volume_rate / mesh.cells()[i].volume)?;
            let row = coalesce(&fit.owners, weights.into_iter(), count)?;
            Ok::<_, FitError3>((fit, row))
        });
        for result in local {
            let (fit, row) = result?;
            rows.push(row);
            max_condition = max_condition.max(fit.fit.quality.kappa1_r);
            max_inverse_r_norm = max_inverse_r_norm.max(fit.fit.quality.inverse_r_norm1);
            fits.push(fit);
        }
        Ok(Self {
            epoch: g.epoch(),
            trajectory: motion.trajectory_digest(),
            curl: DiscreteCurl3::assemble(&fits)?,
            tangent: DiscreteCurl3 { rows },
            max_condition,
            max_inverse_r_norm,
        })
    }

    pub fn operators(
        &self,
        g: &ValidatedGeometry3,
        motion: &MotionRates3,
    ) -> Result<(&DiscreteCurl3, &DiscreteCurl3), FitError3> {
        if g.epoch() != self.epoch
            || motion.epoch() != self.epoch
            || motion.trajectory_digest() != self.trajectory
        {
            return Err(FitError3::MotionMismatch);
        }
        Ok((&self.curl, &self.tangent))
    }

    /// Largest local estimates of κ₁(R) and ||R⁻¹||₁ for the scaled polynomial fits.
    pub fn fit_sensitivity(&self) -> (f64, f64) {
        (self.max_condition, self.max_inverse_r_norm)
    }
}
