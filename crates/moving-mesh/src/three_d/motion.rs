//! Instantaneous Reynolds rates on a smooth branch of an accepted Voronoi geometry.
use super::moments::{Sum, add, dot, norm, scale, sub};
use super::{
    CellRef3, FaceRef3, GeometryEpoch3, GeometryError3, SharedFace3, ValidatedGeometry3, Vec3,
};
use galaxy_types::CellId;
use std::collections::BTreeMap;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct FaceMotionRate3 {
    /// Canonical outward normal speed at the face's area centroid.
    pub normal_speed: f64,
    /// Tangential gradient of the affine normal speed (inverse time).
    pub normal_speed_gradient: Vec3,
    /// Integral of normal speed, positive outward from the canonical left owner.
    pub volume_flux: f64,
    /// Integral of (x - face_centroid) times normal speed over this face.
    pub central_moment_flux: Vec3,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct CellMotionRate3 {
    pub volume_rate: f64,
    /// Physical derivative of the geometric centroid in a continuous chart.
    pub centroid_velocity: Vec3,
}

/// One geometry epoch and one prescribed velocity field. Lookups require handles
/// from that geometry, including when a rebuild retained exactly the same IDs.
#[derive(Clone, Debug)]
pub struct MotionRates3 {
    epoch: GeometryEpoch3,
    faces: Vec<FaceMotionRate3>,
    cells: Vec<CellMotionRate3>,
}

impl MotionRates3 {
    pub fn epoch(&self) -> GeometryEpoch3 {
        self.epoch
    }

    pub fn face(&self, face: FaceRef3) -> Result<&FaceMotionRate3, GeometryError3> {
        if face.epoch() != self.epoch {
            return Err(GeometryError3::EpochMismatch);
        }
        self.faces
            .get(face.index() as usize)
            .ok_or(GeometryError3::InvalidLocalIndex)
    }

    pub fn cell(&self, cell: CellRef3) -> Result<&CellMotionRate3, GeometryError3> {
        if cell.epoch() != self.epoch {
            return Err(GeometryError3::EpochMismatch);
        }
        self.cells
            .get(cell.index() as usize)
            .ok_or(GeometryError3::InvalidLocalIndex)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MotionRateError3 {
    VelocityCatalogMismatch,
    NonFiniteVelocity(CellId),
    NonFiniteWallVelocity,
    Unrepresentable(&'static str),
}

impl std::fmt::Display for MotionRateError3 {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::VelocityCatalogMismatch => f.write_str("velocity and geometry cell IDs differ"),
            Self::NonFiniteVelocity(id) => write!(f, "nonfinite velocity for {}", id.entity()),
            Self::NonFiniteWallVelocity => f.write_str("nonfinite translating-wall velocity"),
            Self::Unrepresentable(q) => write!(f, "unrepresentable {q}"),
        }
    }
}

impl std::error::Error for MotionRateError3 {}

fn face_rate(
    face: &SharedFace3,
    separation: Vec3,
    velocities: &[Vec3],
    wall_velocity: Vec3,
) -> Result<FaceMotionRate3, MotionRateError3> {
    let normal = face.normal;
    let (normal_speed, gradient) = if let Some(right) = face.right {
        let left = velocities[face.left as usize];
        let right = velocities[right as usize];
        let half_distance = 0.5 * norm(separation);
        let half_difference = sub(scale(left, 0.5), scale(right, 0.5));
        let slope = half_difference.map(|x| x / half_distance);
        let average = add(scale(left, 0.5), scale(right, 0.5));
        let skew = sub(face.centroid_offset, scale(separation, 0.5));
        (
            dot(average, normal) + dot(slope, skew),
            sub(slope, scale(normal, dot(slope, normal))),
        )
    } else {
        (dot(wall_velocity, normal), [0.0; 3])
    };
    let volume_flux = face.area * normal_speed;
    let central_moment_flux = face.covariance.map(|row| face.area * dot(row, gradient));
    if ![normal_speed, volume_flux]
        .into_iter()
        .chain(gradient)
        .chain(central_moment_flux)
        .all(f64::is_finite)
    {
        return Err(MotionRateError3::Unrepresentable("face motion rate"));
    }
    Ok(FaceMotionRate3 {
        normal_speed,
        normal_speed_gradient: gradient,
        volume_flux,
        central_moment_flux,
    })
}

/// Evaluate S3–S4 at this geometry. Velocities must cover every real generator.
/// The wall argument is the shared velocity of a translating cuboid; use zero
/// for stationary walls. A periodic domain has no physical wall contributions.
pub fn prescribed_motion_rates3(
    geometry: &ValidatedGeometry3,
    velocities: &BTreeMap<CellId, Vec3>,
    wall_velocity: Vec3,
) -> Result<MotionRates3, MotionRateError3> {
    if !geometry
        .cells()
        .iter()
        .map(|c| &c.generator.id)
        .eq(velocities.keys())
    {
        return Err(MotionRateError3::VelocityCatalogMismatch);
    }
    if !wall_velocity.into_iter().all(f64::is_finite) {
        return Err(MotionRateError3::NonFiniteWallVelocity);
    }
    for (&id, velocity) in velocities {
        if !velocity.iter().copied().all(f64::is_finite) {
            return Err(MotionRateError3::NonFiniteVelocity(id));
        }
    }
    let velocities: Vec<_> = velocities.values().copied().collect();
    // The oracle already retained this lifted difference from the exact image
    // geometry, including the full box span on a periodic self-face.
    let mut separations = vec![[0.0; 3]; geometry.faces().len()];
    for cell in geometry.cells() {
        for inc in &cell.incidences {
            if inc.sign < 0 {
                separations[inc.face as usize] = scale(inc.chart_translation, -1.0);
            }
        }
    }
    let faces: Vec<_> = geometry
        .faces()
        .iter()
        .zip(separations)
        .map(|(face, d)| face_rate(face, d, &velocities, wall_velocity))
        .collect::<Result<_, _>>()?;
    let mut cells = Vec::with_capacity(geometry.cells().len());
    for cell in geometry.cells() {
        let mut volume = Sum::default();
        let mut moment = [Sum::default(); 3];
        for inc in &cell.incidences {
            let i = inc.face as usize;
            let rate = &faces[i];
            let local_face = add(geometry.faces()[i].centroid_offset, inc.chart_translation);
            let arm = sub(local_face, cell.centroid_offset);
            let sign = f64::from(inc.sign);
            volume.add(sign * rate.volume_flux);
            for (k, sum) in moment.iter_mut().enumerate() {
                sum.add(sign * (arm[k] * rate.volume_flux + rate.central_moment_flux[k]));
            }
        }
        let volume_rate = volume.get();
        let centroid_velocity = moment.map(|s| s.get() / cell.volume);
        if !volume_rate.is_finite() || !centroid_velocity.into_iter().all(f64::is_finite) {
            return Err(MotionRateError3::Unrepresentable("cell motion rate"));
        }
        cells.push(CellMotionRate3 {
            volume_rate,
            centroid_velocity,
        });
    }
    Ok(MotionRates3 {
        epoch: geometry.epoch(),
        faces,
        cells,
    })
}
