use galaxy_types::CellId;

pub type Vec3 = [f64; 3];
pub type Tensor3 = [[f64; 3]; 3];

/// Static orthorhombic geometry only. Walls do not supply physical MHD states.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Domain3 {
    pub anchor: Vec3,
    pub width: Vec3,
    pub boundary: Boundary3,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Boundary3 {
    Periodic,
    Bounded,
}

/// Image of a real owner, never another persistent entity.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Image3(pub [i64; 3]);

impl Image3 {
    pub const ZERO: Self = Self([0; 3]);

    pub fn checked_neg(self) -> Result<Self, GeometryError3> {
        let mut result = [0; 3];
        for (a, value) in result.iter_mut().enumerate() {
            *value = self.0[a].checked_neg().ok_or(GeometryError3::ImageOverflow)?;
        }
        Ok(Self(result))
    }

    pub(crate) fn trajectory(self, left: Self, right: Self) -> Result<Self, GeometryError3> {
        let mut result = [0; 3];
        for (a, value) in result.iter_mut().enumerate() {
            let wide = i128::from(self.0[a]) + i128::from(left.0[a]) - i128::from(right.0[a]);
            *value = i64::try_from(wide).map_err(|_| GeometryError3::ImageOverflow)?;
        }
        Ok(Self(result))
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Generator3 {
    pub id: CellId,
    /// Primary-box position; periodic inputs must already be wrapped.
    pub position: Vec3,
    /// Static chart label; no trajectory is inferred by this builder.
    pub winding: Image3,
}

/// x_min,x_max,y_min,y_max,z_min,z_max, respectively.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct BoundaryPatch3(pub u8);

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum FaceKey3 {
    Interior { lo: CellId, hi: CellId, hi_image: Image3 },
    Boundary { cell: CellId, patch: BoundaryPatch3 },
}

/// Allocated monotonically in this process after validation; cannot be forged.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct GeometryEpoch3(pub(crate) u64);

impl GeometryEpoch3 {
    pub const fn value(self) -> u64 { self.0 }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CellRef3 {
    pub(crate) epoch: GeometryEpoch3,
    pub(crate) index: u32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FaceRef3 {
    pub(crate) epoch: GeometryEpoch3,
    pub(crate) index: u32,
}

impl CellRef3 {
    pub const fn epoch(self) -> GeometryEpoch3 { self.epoch }
    pub const fn index(self) -> u32 { self.index }
}

impl FaceRef3 {
    pub const fn epoch(self) -> GeometryEpoch3 { self.epoch }
    pub const fn index(self) -> u32 { self.index }
}

#[derive(Clone, Debug)]
pub struct FaceIncidence3 {
    pub face: u32,
    /// +1 for canonical left, -1 for canonical right (including self-images).
    pub sign: i8,
    /// Trajectory image in this owner's chart, not just the neighbour ID.
    pub neighbour: Option<(CellId, Image3)>,
    /// Translation from canonical left-relative polygon to this owner chart.
    pub chart_translation: Vec3,
}

#[derive(Clone, Debug)]
pub struct CellGeometry3 {
    pub generator: Generator3,
    pub volume: f64,
    pub centroid_offset: Vec3,
    /// Volume-integrated central second moment, not covariance J/V.
    pub central_second_moment: Tensor3,
    pub surface_area: f64,
    pub bounding_radius: f64,
    pub minimum_generator_face_distance: f64,
    pub incidences: Vec<FaceIncidence3>,
}

#[derive(Clone, Debug)]
pub struct SharedFace3 {
    pub key: FaceKey3,
    pub left: u32,
    pub right: Option<u32>,
    /// Wrapped neighbour image; FaceKey3 separately retains trajectory image.
    pub right_wrapped_image: Image3,
    pub area: f64,
    pub normal: Vec3,
    pub centroid_offset: Vec3,
    pub plane_distance: f64,
    /// Counterclockwise viewed from outside left, relative to left generator.
    /// Fan triangles are (0,k,k+1), k=1..len-2.
    pub polygon: Vec<Vec3>,
    /// Surface-average central second moment, units length squared.
    pub covariance: Tensor3,
}

#[derive(Clone, Debug)]
pub struct GeometryQuality3 {
    pub relative_volume_closure: f64,
    pub maximum_normal_closure: f64,
    pub maximum_affine_closure: f64,
    pub maximum_centroid_closure: f64,
    pub certified_contact_planes: usize,
    pub clipping_planes: usize,
    pub predicate_operations: usize,
}

/// Only the oracle/validator can construct this immutable view.
#[derive(Clone, Debug)]
pub struct ValidatedGeometry3 {
    pub(crate) epoch: GeometryEpoch3,
    pub(crate) domain: Domain3,
    pub(crate) cells: Vec<CellGeometry3>,
    pub(crate) faces: Vec<SharedFace3>,
    pub(crate) quality: GeometryQuality3,
}

impl ValidatedGeometry3 {
    pub fn epoch(&self) -> GeometryEpoch3 { self.epoch }
    pub fn domain(&self) -> Domain3 { self.domain }
    pub fn cells(&self) -> &[CellGeometry3] { &self.cells }
    pub fn faces(&self) -> &[SharedFace3] { &self.faces }
    pub fn quality(&self) -> &GeometryQuality3 { &self.quality }

    pub fn cell_by_id(&self, id: CellId) -> Option<CellRef3> {
        self.cells.binary_search_by_key(&id, |cell| cell.generator.id).ok()
            .map(|index| CellRef3 { epoch: self.epoch, index: index as u32 })
    }

    pub fn cell_ref(&self, index: usize) -> Result<CellRef3, GeometryError3> {
        if index >= self.cells.len() { return Err(GeometryError3::InvalidLocalIndex); }
        Ok(CellRef3 { epoch: self.epoch, index: index as u32 })
    }

    pub fn face_ref(&self, index: usize) -> Result<FaceRef3, GeometryError3> {
        if index >= self.faces.len() { return Err(GeometryError3::InvalidLocalIndex); }
        Ok(FaceRef3 { epoch: self.epoch, index: index as u32 })
    }

    pub fn cell(&self, reference: CellRef3) -> Result<&CellGeometry3, GeometryError3> {
        if reference.epoch != self.epoch { return Err(GeometryError3::EpochMismatch); }
        self.cells.get(reference.index as usize).ok_or(GeometryError3::InvalidLocalIndex)
    }

    pub fn face(&self, reference: FaceRef3) -> Result<&SharedFace3, GeometryError3> {
        if reference.epoch != self.epoch { return Err(GeometryError3::EpochMismatch); }
        self.faces.get(reference.index as usize).ok_or(GeometryError3::InvalidLocalIndex)
    }
}

#[derive(Clone, Debug, PartialEq)]
pub enum GeometryError3 {
    InvalidDomain,
    EmptyCatalog,
    TooManyGenerators { count: usize, limit: usize },
    NonFiniteGenerator { id: CellId },
    GeneratorOutside { id: CellId },
    DuplicateId { id: CellId },
    CoincidentGenerators { first: CellId, second: CellId },
    BoundedWinding { id: CellId },
    ImageOverflow,
    ResourceLimit(&'static str),
    SingularIntersection,
    InvalidTopology(&'static str),
    Unrepresentable(&'static str),
    UncertainMetric { quantity: &'static str, value: f64, separation_bound: f64 },
    NumericalValidation { quantity: &'static str, residual: f64 },
    FaceMismatch { key: FaceKey3 },
    EpochExhausted,
    EpochMismatch,
    InvalidLocalIndex,
}

impl std::fmt::Display for GeometryError3 {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "3D geometry rejected: {self:?}")
    }
}

impl std::error::Error for GeometryError3 {}
