//! Geometry needed by the static centroid operators. Face coordinates live
//! in the left owner's chart; winding labels and wrapped images are distinct.
use super::fit::{FitError3, FitOrder3, PointFit3, SampleKey3, StencilSample3};
use super::{Boundary3, Domain3, Image3, ValidatedGeometry3, Vec3};
use galaxy_types::CellId;
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, Copy)]
pub struct OperatorCell3 {
    pub id: CellId,
    pub winding: Image3,
    pub centroid: Vec3,
    pub volume: f64,
}
#[derive(Debug, Clone, Copy)]
pub struct OperatorFace3 {
    pub left: usize,
    pub right: Option<usize>,
    pub right_image: Image3,
    pub area: f64,
    pub normal: Vec3,
    pub centroid: Vec3,
}
#[derive(Debug, Clone)]
pub struct OperatorMesh3 {
    domain: Domain3,
    cells: Vec<OperatorCell3>,
    faces: Vec<OperatorFace3>,
    adjacent: Vec<Vec<(usize, bool)>>,
}
#[derive(Debug, Clone)]
pub struct MeshFit3 {
    pub fit: PointFit3,
    /// Real cell for each sorted stencil row, including repeated owners.
    pub owners: Vec<usize>,
    pub rings: u8,
    pub rejected_supports: Vec<(u8, FitError3)>,
}
fn image_sum(a: Image3, b: Image3) -> Result<Image3, FitError3> {
    let mut v = [0; 3];
    for (i, x) in v.iter_mut().enumerate() {
        *x = a.0[i].checked_add(b.0[i]).ok_or(FitError3::ImageOverflow)?;
    }
    Ok(Image3(v))
}
impl OperatorMesh3 {
    pub fn from_validated(g: &ValidatedGeometry3) -> Result<Self, FitError3> {
        let cells = g
            .cells()
            .iter()
            .map(|c| OperatorCell3 {
                id: c.generator.id,
                volume: c.volume,
                winding: c.generator.winding,
                centroid: std::array::from_fn(|a| c.generator.position[a] + c.centroid_offset[a]),
            })
            .collect();
        let faces = g
            .faces()
            .iter()
            .map(|f| OperatorFace3 {
                left: f.left as usize,
                right: f.right.map(|i| i as usize),
                right_image: f.right_wrapped_image,
                area: f.area,
                normal: f.normal,
                centroid: std::array::from_fn(|a| {
                    g.cells()[f.left as usize].generator.position[a] + f.centroid_offset[a]
                }),
            })
            .collect();
        Self::from_metrics(g.domain(), cells, faces)
    }
    /// A shared-face metric view, including checked incidence and closure.
    /// Imported metrics need their own geometric provenance.
    pub fn from_metrics(
        domain: Domain3,
        cells: Vec<OperatorCell3>,
        faces: Vec<OperatorFace3>,
    ) -> Result<Self, FitError3> {
        let good = |v: Vec3| v.into_iter().all(f64::is_finite);
        if !good(domain.anchor)
            || !domain.width.into_iter().all(|x| x.is_finite() && x > 0.)
            || cells.is_empty()
            || cells.windows(2).any(|w| w[0].id >= w[1].id)
            || cells
                .iter()
                .any(|c| !good(c.centroid) || !c.volume.is_finite() || c.volume <= 0.)
        {
            return Err(FitError3::InvalidSample);
        }
        let n = cells.len();
        let mut adjacent = vec![Vec::new(); n];
        let mut closure = vec![[0.; 3]; n];
        let mut areas = vec![0.; n];
        for (k, f) in faces.iter().enumerate() {
            let n2: f64 = f.normal.iter().map(|x| x * x).sum();
            if f.left >= n
                || f.right.is_some_and(|r| r >= n)
                || !good(f.normal)
                || !good(f.centroid)
                || !f.area.is_finite()
                || f.area <= 0.
                || (n2 - 1.).abs() > 2e-10
                || f.right == Some(f.left) && f.right_image == Image3::ZERO
                || f.right.is_none() && domain.boundary == Boundary3::Periodic
                || domain.boundary == Boundary3::Bounded && f.right_image != Image3::ZERO
            {
                return Err(FitError3::InvalidSample);
            }
            for (i, forward) in [(Some(f.left), true), (f.right, false)] {
                if let Some(i) = i {
                    adjacent[i].push((k, forward));
                    areas[i] += f.area;
                    for (v, &normal) in closure[i].iter_mut().zip(&f.normal) {
                        *v += if forward {
                            f.area * normal
                        } else {
                            -f.area * normal
                        };
                    }
                }
            }
        }
        if adjacent.iter().any(|r| r.len() < 4)
            || closure
                .iter()
                .zip(areas)
                .any(|(v, area)| v.iter().any(|x| x.abs() > 1e-9 * area))
        {
            return Err(FitError3::InvalidSample);
        }
        let v: f64 = cells.iter().map(|c| c.volume).sum();
        let box_v: f64 = domain.width.iter().product();
        if !box_v.is_finite() || (v - box_v).abs() > 1e-9 * box_v {
            return Err(FitError3::InvalidVolume);
        }
        Ok(Self {
            domain,
            cells,
            faces,
            adjacent,
        })
    }
    pub fn domain(&self) -> Domain3 {
        self.domain
    }
    pub fn cells(&self) -> &[OperatorCell3] {
        &self.cells
    }
    pub fn faces(&self) -> &[OperatorFace3] {
        &self.faces
    }
    pub fn incidences(&self, i: usize) -> &[(usize, bool)] {
        &self.adjacent[i]
    }
    pub fn lifted(&self, cell: usize, image: Image3) -> Vec3 {
        std::array::from_fn(|k| {
            self.cells[cell].centroid[k] + image.0[k] as f64 * self.domain.width[k]
        })
    }
    pub fn fit(&self, owner: usize, order: FitOrder3) -> Result<MeshFit3, FitError3> {
        let center = self.cells.get(owner).ok_or(FitError3::MissingNeighbour)?;
        let mut frontier = vec![(owner, Image3::ZERO)];
        let mut seen = BTreeSet::from([(owner, Image3::ZERO)]);
        let mut rows = BTreeMap::new();
        let mut rejected = Vec::new();
        for ring in 1..=3 {
            let mut next = BTreeSet::new();
            for (from, shift) in frontier {
                for &(fi, forward) in &self.adjacent[from] {
                    let f = &self.faces[fi];
                    let right = f.right.ok_or(FitError3::UnsupportedBoundary)?;
                    let (index, step) = if forward {
                        (right, f.right_image)
                    } else {
                        (
                            f.left,
                            f.right_image
                                .checked_neg()
                                .map_err(|_| FitError3::ImageOverflow)?,
                        )
                    };
                    let wrapped = image_sum(shift, step)?;
                    if !seen.insert((index, wrapped)) {
                        continue;
                    }
                    next.insert((index, wrapped));
                    let c = self.cells[index];
                    let traj = wrapped
                        .trajectory(center.winding, c.winding)
                        .map_err(|_| FitError3::ImageOverflow)?;
                    let key = SampleKey3 {
                        owner: c.id,
                        image: traj,
                    };
                    let d = std::array::from_fn(|k| {
                        (c.centroid[k] - center.centroid[k])
                            + wrapped.0[k] as f64 * self.domain.width[k]
                    });
                    rows.insert(
                        key,
                        (
                            index,
                            StencilSample3 {
                                key,
                                displacement: d,
                                face_area: (ring == 1).then_some(f.area),
                            },
                        ),
                    );
                }
            }
            if rows.len() > 256 {
                return Err(FitError3::SampleLimit);
            }
            // The linear area weight is defined only for actual shared faces.
            if order == FitOrder3::Linear || ring >= 2 {
                match PointFit3::build(
                    order,
                    center.volume,
                    rows.values().map(|(_, s)| *s).collect(),
                ) {
                    Ok(fit) => {
                        return Ok(MeshFit3 {
                            fit,
                            owners: rows.values().map(|(i, _)| *i).collect(),
                            rings: ring,
                            rejected_supports: rejected,
                        });
                    }
                    Err(
                        e @ (FitError3::RankDeficient
                        | FitError3::IllConditioned
                        | FitError3::InsufficientSamples
                        | FitError3::PeriodicFitDecisionUnresolved),
                    ) if order == FitOrder3::Quadratic && ring < 3 => rejected.push((ring, e)),
                    Err(e) => return Err(e),
                }
            }
            frontier = next.into_iter().collect();
        }
        Err(FitError3::InsufficientSamples)
    }
}
