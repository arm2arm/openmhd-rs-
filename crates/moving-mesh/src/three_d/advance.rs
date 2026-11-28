//! Finite prescribed generator steps on a fixed orthorhombic domain.
use super::{
    Boundary3, Domain3, FaceKey3, FaceRef3, Generator3, GeometryError3, HalfSpaceOracle3,
    ValidatedGeometry3, Vec3,
};
use galaxy_types::CellId;
use std::collections::BTreeMap;

/// Signed count of whole box widths in a finite binary64 displacement. Integer
/// division keeps exact seam crossings and winding increments beyond 2^53.
fn whole_widths(displacement: f64, width: f64) -> Result<i128, GeometryError3> {
    if displacement.abs() < width {
        return Ok(0);
    }
    let parts = |positive: f64| {
        let bits = positive.to_bits();
        let exponent = bits >> 52;
        let fraction = bits & ((1_u64 << 52) - 1);
        let significand = if exponent == 0 {
            fraction
        } else {
            fraction | (1_u64 << 52)
        };
        (u128::from(significand), exponent.max(1))
    };
    let (n, en) = parts(displacement.abs());
    let (d, ed) = parts(width);
    let shift = en - ed;
    // A larger exponent gap moves farther than the entire signed-i64 chart range.
    if shift > 65 {
        return Err(GeometryError3::ImageOverflow);
    }
    let whole = ((n << shift) / d) as i128;
    Ok(if displacement.is_sign_negative() {
        -whole
    } else {
        whole
    })
}

fn drift(
    domain: Domain3,
    mut site: Generator3,
    velocity: Vec3,
    dt: f64,
) -> Result<Generator3, GeometryError3> {
    for (axis, speed) in velocity.into_iter().enumerate() {
        let start = site.position[axis];
        if domain.boundary == Boundary3::Bounded {
            site.position[axis] = speed.mul_add(dt, start);
            continue;
        }
        let delta = speed * dt;
        if !delta.is_finite() {
            return Err(GeometryError3::Unrepresentable("periodic drift"));
        }
        let lo = domain.anchor[axis];
        let width = domain.width[axis];
        let hi = lo + width;
        let mut turns = whole_widths(delta, width)?;
        let remainder = delta % width;
        // Reduce the displacement before adding it to the primary coordinate,
        // so even a large integer-box translation preserves the site's offset.
        let local = start - lo;
        let mut end = if remainder < 0.0 && -remainder > local {
            turns -= 1;
            hi + (local + remainder)
        } else if remainder > 0.0 && remainder >= width - local {
            turns += 1;
            lo + (remainder - (width - local))
        } else {
            start + remainder
        };
        if end == hi {
            end = lo;
            turns += 1;
        }
        site.winding.0[axis] = i64::try_from(i128::from(site.winding.0[axis]) + turns)
            .map_err(|_| GeometryError3::ImageOverflow)?;
        site.position[axis] = end;
    }
    Ok(site)
}

pub(super) fn endpoints(
    start: &ValidatedGeometry3,
    velocities: impl Iterator<Item = Vec3>,
    dt: f64,
) -> Result<Vec<Generator3>, GeometryError3> {
    if crate::parallel::team_size() == 1 {
        return start
            .cells()
            .iter()
            .zip(velocities)
            .map(|(c, w)| drift(start.domain(), c.generator, w, dt))
            .collect();
    }
    let w: Vec<_> = velocities.collect();
    crate::parallel::map(w.len().min(start.cells().len()), |i| {
        drift(start.domain(), start.cells()[i].generator, w[i], dt)
    })
    .into_iter()
    .collect()
}

/// Endpoint correspondence of a positive-area face. Handles belong to their
/// respective geometry epochs, including when both owners are the same cell.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FaceChange3 {
    Retained {
        previous: FaceRef3,
        current: FaceRef3,
    },
    Appeared(FaceRef3),
    Disappeared(FaceRef3),
}

#[derive(Debug)]
pub struct MeshStep3 {
    pub geometry: ValidatedGeometry3,
    /// Sorted by the full persistent owner/image key (or the owner and wall).
    pub face_changes: BTreeMap<FaceKey3, FaceChange3>,
}

#[derive(Clone, Debug, PartialEq)]
pub enum MeshStepError3 {
    InvalidTimestep,
    VelocityCatalogMismatch,
    NonFiniteVelocity(CellId),
    Geometry(GeometryError3),
}

impl std::fmt::Display for MeshStepError3 {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidTimestep => f.write_str("mesh timestep must be finite and positive"),
            Self::VelocityCatalogMismatch => f.write_str("mesh and velocity cell IDs differ"),
            Self::NonFiniteVelocity(id) => write!(f, "nonfinite velocity for {}", id.entity()),
            Self::Geometry(error) => error.fmt(f),
        }
    }
}

impl std::error::Error for MeshStepError3 {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Geometry(error) => Some(error),
            _ => None,
        }
    }
}

impl From<GeometryError3> for MeshStepError3 {
    fn from(error: GeometryError3) -> Self {
        Self::Geometry(error)
    }
}

/// Move every persistent generator with its prescribed constant velocity and
/// rebuild the Voronoi cells at the end of `dt`. Bounded walls stay fixed.
/// The source geometry stays valid even if drift or clipping fails.
///
/// Face changes compare the two actual epochs. A face can appear and disappear
/// between them. Sampling additional times is necessary to observe such a face;
/// endpoint correspondence alone cannot certify space-time fluxes.
pub fn advance_generators3(
    start: &ValidatedGeometry3,
    velocities: &BTreeMap<CellId, Vec3>,
    dt: f64,
) -> Result<MeshStep3, MeshStepError3> {
    let sites = generator_endpoints3(start, velocities, dt)?;
    let geometry = HalfSpaceOracle3::build_motion_epoch(start.domain(), &sites)?;
    let mut face_changes = BTreeMap::new();
    for (index, face) in start.faces().iter().enumerate() {
        face_changes.insert(face.key, FaceChange3::Disappeared(start.face_ref(index)?));
    }
    for (index, face) in geometry.faces().iter().enumerate() {
        let current = geometry.face_ref(index)?;
        let change = face_changes
            .entry(face.key)
            .or_insert(FaceChange3::Appeared(current));
        if let FaceChange3::Disappeared(previous) = *change {
            *change = FaceChange3::Retained { previous, current };
        }
    }
    Ok(MeshStep3 {
        geometry,
        face_changes,
    })
}

/// Canonical wrapped endpoints and trajectory image counters, before choosing the
/// execution layout for the new tessellation.
pub fn generator_endpoints3(
    start: &ValidatedGeometry3,
    velocities: &BTreeMap<CellId, Vec3>,
    dt: f64,
) -> Result<Vec<Generator3>, MeshStepError3> {
    if !dt.is_finite() || dt <= 0.0 {
        return Err(MeshStepError3::InvalidTimestep);
    }
    if !start
        .cells()
        .iter()
        .map(|c| &c.generator.id)
        .eq(velocities.keys())
    {
        return Err(MeshStepError3::VelocityCatalogMismatch);
    }
    for (&id, velocity) in velocities {
        if !velocity.iter().copied().all(f64::is_finite) {
            return Err(MeshStepError3::NonFiniteVelocity(id));
        }
    }
    Ok(endpoints(start, velocities.values().copied(), dt)?)
}
