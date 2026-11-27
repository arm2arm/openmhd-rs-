//! Views of one canonical face in each incident generator's local coordinates.
use super::moments::{add, scale};
use super::{
    CellRef3, FaceIncidence3, FaceRef3, GeometryError3, SharedFace3, ValidatedGeometry3, Vec3,
};

/// One owner's incidence. Both owners borrow the same canonical face and area.
#[derive(Clone, Copy)]
pub struct OrientedFace3<'a> {
    pub handle: FaceRef3,
    pub shared: &'a SharedFace3,
    pub incidence: &'a FaceIncidence3,
}

impl OrientedFace3<'_> {
    pub fn outward_normal(self) -> Vec3 {
        scale(self.shared.normal, f64::from(self.incidence.sign))
    }

    pub fn centroid_offset(self) -> Vec3 {
        add(
            self.shared.centroid_offset,
            self.incidence.chart_translation,
        )
    }

    /// Counterclockwise viewed from outside this owner. Keep the canonical fan
    /// pivot on both sides so that corresponding triangles have opposite winding.
    pub fn vertices(&self) -> impl ExactSizeIterator<Item = Vec3> + '_ {
        let polygon = &self.shared.polygon;
        (0..polygon.len()).map(move |i| {
            let j = if self.incidence.sign < 0 && i != 0 {
                polygon.len() - i
            } else {
                i
            };
            add(polygon[j], self.incidence.chart_translation)
        })
    }
}

impl ValidatedGeometry3 {
    /// An interior face appears once for each side, including both incidences
    /// of a periodic self-face. Physical wall faces have one outward incidence.
    pub fn oriented_faces(
        &self,
        owner: CellRef3,
    ) -> Result<impl ExactSizeIterator<Item = OrientedFace3<'_>>, GeometryError3> {
        let cell = self.cell(owner)?;
        Ok(cell.incidences.iter().map(move |incidence| OrientedFace3 {
            handle: FaceRef3 {
                epoch: self.epoch(),
                index: incidence.face,
            },
            shared: &self.faces()[incidence.face as usize],
            incidence,
        }))
    }
}
