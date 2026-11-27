//! Predictive Lloyd mesh motion with prescribed cell fluid velocities (Mocz et al. 2015).
use super::{
    GeometryError3, HalfSpaceOracle3, ValidatedGeometry3, Vec3, advance::endpoints, moments::norm,
};
use galaxy_types::CellId;
use std::collections::BTreeMap;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct GasMotion3 {
    pub velocity: Vec3,
    pub sound_speed: f64,
}

/// Requested number of simultaneous corrections and optional maximum |w-v|/c_s.
/// The default applies only when the caller explicitly selects Lloyd motion.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct LloydConfig3 {
    pub iterations: usize,
    pub sound_speed_fraction: Option<f64>,
}

impl Default for LloydConfig3 {
    fn default() -> Self {
        Self {
            iterations: 5,
            sound_speed_fraction: Some(0.1),
        }
    }
}

#[derive(Debug)]
pub struct LloydStep3 {
    pub velocities: BTreeMap<CellId, Vec3>,
    pub geometry: ValidatedGeometry3,
}

#[derive(Clone, Debug, PartialEq)]
pub enum LloydError3 {
    InvalidTimestep,
    InvalidSoundSpeedFraction,
    FlowCatalogMismatch,
    InvalidFlow(CellId),
    Geometry(GeometryError3),
}

impl From<GeometryError3> for LloydError3 {
    fn from(error: GeometryError3) -> Self {
        Self::Geometry(error)
    }
}

impl std::fmt::Display for LloydError3 {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidTimestep => f.write_str("Lloyd timestep must be finite and positive"),
            Self::InvalidSoundSpeedFraction => {
                f.write_str("Lloyd sound-speed fraction must be in [0, 1]")
            }
            Self::FlowCatalogMismatch => f.write_str("gas and mesh cell IDs differ"),
            Self::InvalidFlow(id) => {
                write!(f, "invalid gas velocity or sound speed for {}", id.entity())
            }
            Self::Geometry(error) => error.fmt(f),
        }
    }
}

impl std::error::Error for LloydError3 {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Geometry(error) => Some(error),
            _ => None,
        }
    }
}

/// Advance mesh generators through one interval of prescribed gas motion.
/// Every iteration rebuilds the Voronoi mesh at the previous predicted endpoints.
/// Zero iterations gives pure gas advection. A failed prediction leaves the
/// supplied geometry and flow untouched. The returned geometry corresponds to
/// the final velocities, including the last correction.
pub fn predict_lloyd_step3(
    start: &ValidatedGeometry3,
    flow: &BTreeMap<CellId, GasMotion3>,
    dt: f64,
    config: LloydConfig3,
) -> Result<LloydStep3, LloydError3> {
    if !dt.is_finite() || dt <= 0.0 {
        return Err(LloydError3::InvalidTimestep);
    }
    if config
        .sound_speed_fraction
        .is_some_and(|f| !(0.0..=1.0).contains(&f))
    {
        return Err(LloydError3::InvalidSoundSpeedFraction);
    }
    if !start
        .cells()
        .iter()
        .map(|c| &c.generator.id)
        .eq(flow.keys())
    {
        return Err(LloydError3::FlowCatalogMismatch);
    }
    for (&id, gas) in flow {
        if gas.velocity.iter().any(|v| !v.is_finite())
            || !gas.sound_speed.is_finite()
            || gas.sound_speed < 0.0
        {
            return Err(LloydError3::InvalidFlow(id));
        }
    }
    let mut velocities: Vec<_> = flow.values().map(|g| g.velocity).collect();
    let advected = endpoints(start, velocities.iter().copied(), dt)?;
    let domain = start.domain();
    let mut geometry = HalfSpaceOracle3::build(domain, &advected)?;
    for _ in 0..config.iterations {
        let mut changed = false;
        for (((cell, adv), gas), velocity) in geometry
            .cells()
            .iter()
            .zip(&advected)
            .zip(flow.values())
            .zip(&mut velocities)
        {
            // Target the predicted centroid in the continuous chart of the
            // *fluid-advected* site. Subtract integer windings before conversion.
            let mut correction: Vec3 = std::array::from_fn(|axis| {
                let wraps =
                    i128::from(cell.generator.winding.0[axis]) - i128::from(adv.winding.0[axis]);
                (wraps as f64).mul_add(
                    domain.width[axis],
                    cell.generator.position[axis] - adv.position[axis],
                ) + cell.centroid_offset[axis]
            });
            let length = norm(correction);
            if !length.is_finite() {
                return Err(GeometryError3::Unrepresentable("Lloyd centroid displacement").into());
            }
            if let Some(fraction) = config.sound_speed_fraction {
                let limit = (fraction * gas.sound_speed) * dt;
                if length > limit {
                    correction = correction.map(|c| (c / length) * limit);
                }
            }
            let previous = *velocity;
            for (axis, c) in correction.into_iter().enumerate() {
                velocity[axis] = gas.velocity[axis] + c / dt;
                if !velocity[axis].is_finite() {
                    return Err(GeometryError3::Unrepresentable("Lloyd mesh velocity").into());
                }
            }
            changed |= *velocity != previous;
        }
        if !changed {
            break;
        }
        let sites = endpoints(start, velocities.iter().copied(), dt)?;
        geometry = HalfSpaceOracle3::build(domain, &sites)?;
    }
    Ok(LloydStep3 {
        velocities: flow.keys().copied().zip(velocities).collect(),
        geometry,
    })
}
