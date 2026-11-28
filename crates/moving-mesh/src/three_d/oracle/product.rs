//! Periodic Voronoi geometry for a complete product of coordinate planes.
//! Squared distance separates by axis. Each endpoint of a 1D Voronoi
//! interval has exactly two nearest images, giving eight sites per vertex.
use super::*;
use std::array;

#[derive(Clone, Copy)]
struct Interval {
    lo: f64,
    hi: f64,
}

impl Interval {
    fn length(self) -> f64 {
        self.hi - self.lo
    }
    fn center(self) -> f64 {
        0.5 * (self.lo + self.hi)
    }
    fn end(self, side: i8) -> f64 {
        if side > 0 { self.hi } else { self.lo }
    }
}

fn intervals(planes: &[f64], width: f64) -> Result<Vec<Interval>> {
    let mut forward = Vec::with_capacity(planes.len());
    for (i, &x) in planes.iter().enumerate() {
        let next = (i + 1) % planes.len();
        let mut gap = D::from_f64(planes[next]).sub(&D::from_f64(x))?;
        if next == 0 {
            gap = gap.add(&D::from_f64(width))?;
        }
        if gap.sign() <= 0 {
            return Err(GeometryError3::InvalidTopology("nonpositive periodic gap"));
        }
        forward.push(gap.half().ratio(&D::one())?);
    }
    Ok((0..planes.len())
        .map(|i| Interval {
            lo: -forward[(i + planes.len() - 1) % planes.len()],
            hi: forward[i],
        })
        .collect())
}

struct Product {
    intervals: [Vec<Interval>; 3],
    // Grid address -> persistent-ID-sorted cell index, and its inverse.
    owners: Vec<usize>,
    addresses: Vec<[usize; 3]>,
}

impl Product {
    fn identify(domain: Domain3, sites: &[Generator3]) -> Result<Option<Self>> {
        let planes: [Vec<f64>; 3] = array::from_fn(|axis| {
            let mut p: Vec<_> = sites.iter().map(|s| s.position[axis] + 0.0).collect();
            p.sort_unstable_by(f64::total_cmp);
            p.dedup();
            p
        });
        let dims = planes.each_ref().map(Vec::len);
        if dims.into_iter().try_fold(1usize, usize::checked_mul) != Some(sites.len()) {
            return Ok(None);
        }
        // checked_inputs already excluded duplicate sites. Equal cardinality
        // therefore proves every combination is represented exactly once.
        let mut owners = vec![0; sites.len()];
        let mut addresses = Vec::with_capacity(sites.len());
        for (owner, site) in sites.iter().enumerate() {
            let mut addr = [0; 3];
            for (k, a) in addr.iter_mut().enumerate() {
                *a = planes[k]
                    .binary_search_by(|p| p.total_cmp(&(site.position[k] + 0.0)))
                    .map_err(|_| GeometryError3::InvalidTopology("unregistered product plane"))?;
            }
            owners[(addr[2] * dims[1] + addr[1]) * dims[0] + addr[0]] = owner;
            addresses.push(addr);
        }
        let intervals = [
            intervals(&planes[0], domain.width[0])?,
            intervals(&planes[1], domain.width[1])?,
            intervals(&planes[2], domain.width[2])?,
        ];
        Ok(Some(Self {
            intervals,
            owners,
            addresses,
        }))
    }

    fn bounds(&self, owner: usize) -> [Interval; 3] {
        array::from_fn(|k| self.intervals[k][self.addresses[owner][k]])
    }

    fn neighbour(&self, owner: usize, shifts: [i8; 3]) -> (usize, Image3) {
        let mut addr = self.addresses[owner];
        let mut image = [0; 3];
        for (k, a) in addr.iter_mut().enumerate() {
            let n = self.intervals[k].len() as i64;
            let moved = *a as i64 + i64::from(shifts[k]);
            *a = moved.rem_euclid(n) as usize;
            image[k] = moved.div_euclid(n);
        }
        let index =
            (addr[2] * self.intervals[1].len() + addr[1]) * self.intervals[0].len() + addr[0];
        (self.owners[index], Image3(image))
    }

    fn vertex_support(&self, owner: usize, corner: [i8; 3]) -> Vec<VertexPlane3> {
        let mut planes = (1..8)
            .map(|mask| {
                let offset = array::from_fn(|k| if mask & (1 << k) != 0 { corner[k] } else { 0 });
                let (neighbour, image) = self.neighbour(owner, offset);
                VertexPlane3 {
                    neighbour: neighbour as u32,
                    image,
                }
            })
            .collect::<Vec<_>>();
        planes.sort_unstable();
        planes
    }

    fn cell(&self, i: usize, generator: Generator3) -> Result<CellGeometry3> {
        let bounds = self.bounds(i);
        let h = bounds.map(Interval::length);
        let volume = h.iter().product::<f64>();
        let diagonal = h.map(|d| volume * d * d / 12.0);
        if !std::iter::once(&volume)
            .chain(diagonal.iter())
            .all(|v| v.is_finite() && *v > 0.)
        {
            return Err(GeometryError3::Unrepresentable("product cell moments"));
        }
        Ok(CellGeometry3 {
            generator,
            volume,
            centroid_offset: bounds.map(Interval::center),
            central_second_moment: array::from_fn(|a| {
                array::from_fn(|b| if a == b { diagonal[a] } else { 0. })
            }),
            // The shared-face validator computes these from the exported polygons.
            surface_area: 0.,
            bounding_radius: 0.,
            minimum_generator_face_distance: 0.,
            incidences: Vec::with_capacity(6),
        })
    }

    fn positive_face(
        &self,
        i: usize,
        axis: usize,
        sites: &[Generator3],
    ) -> Result<(SharedFace3, FaceVertexSupports3)> {
        let mut step = [0; 3];
        step[axis] = 1;
        let (j, wrap) = self.neighbour(i, step);
        let (key, side) = key(sites[i], sites[j], wrap)?;
        let (left, right, image) = if side > 0 {
            (i, j, wrap)
        } else {
            (j, i, wrap.checked_neg()?)
        };
        let bounds = self.bounds(left);
        let b = (axis + 1) % 3;
        let c = (axis + 2) % 3;
        let mut normal = [0.; 3];
        normal[axis] = f64::from(side);
        let mut center = bounds.map(Interval::center);
        center[axis] = bounds[axis].end(side);
        let mut polygon = Vec::with_capacity(4);
        let mut support = Vec::with_capacity(4);
        for (sb, sc) in [(-1, -1), (1, -1), (1, 1), (-1, 1)] {
            let mut corner = [0; 3];
            corner[axis] = side;
            corner[b] = sb;
            corner[c] = sc * side;
            polygon.push(array::from_fn(|k| bounds[k].end(corner[k])));
            support.push(self.vertex_support(left, corner));
        }
        let mut covariance = [[0.; 3]; 3];
        for k in [b, c] {
            covariance[k][k] = bounds[k].length().powi(2) / 12.;
        }
        let area = bounds[b].length() * bounds[c].length();
        if ![area, covariance[b][b], covariance[c][c]]
            .iter()
            .all(|v| v.is_finite() && *v > 0.)
        {
            return Err(GeometryError3::Unrepresentable("product face moments"));
        }
        Ok((
            SharedFace3 {
                key,
                left: left as u32,
                right: Some(right as u32),
                right_wrapped_image: image,
                area,
                normal,
                centroid_offset: center,
                plane_distance: center[axis].abs(),
                polygon,
                covariance,
            },
            support,
        ))
    }
}

impl HalfSpaceOracle3 {
    /// Return supported periodic geometry when the sites fill a Cartesian product.
    /// For other clouds the caller can use the independent all-pairs oracle.
    pub fn try_supported_product(
        domain: Domain3,
        sites: &[Generator3],
    ) -> Result<Option<SupportedGeometry3>> {
        if domain.boundary != Boundary3::Periodic {
            return Err(GeometryError3::InvalidDomain);
        }
        let sites = checked_inputs(domain, sites, 32 * 32 * 32)?;
        let Some(grid) = Product::identify(domain, &sites)? else {
            return Ok(None);
        };
        let mut cells = sites
            .iter()
            .enumerate()
            .map(|(i, &s)| grid.cell(i, s))
            .collect::<Result<Vec<_>>>()?;
        let mut rows = Vec::with_capacity(3 * sites.len());
        for i in 0..sites.len() {
            for axis in 0..3 {
                rows.push(grid.positive_face(i, axis, &sites)?);
            }
        }
        rows.sort_unstable_by_key(|(f, _)| f.key);
        let mut faces = Vec::<SharedFace3>::with_capacity(rows.len());
        let mut support = Vec::with_capacity(rows.len());
        for (f, active) in rows {
            if faces.last().is_some_and(|last| last.key == f.key) {
                return Err(GeometryError3::InvalidTopology("duplicate product face"));
            }
            let FaceKey3::Interior { lo, hi, hi_image } = f.key else {
                return Err(GeometryError3::InvalidTopology("bounded product face"));
            };
            let index = faces.len() as u32;
            cells[f.left as usize].incidences.push(FaceIncidence3 {
                face: index,
                sign: 1,
                neighbour: Some((hi, hi_image)),
                chart_translation: [0.; 3],
            });
            cells[f.right.unwrap() as usize]
                .incidences
                .push(FaceIncidence3 {
                    face: index,
                    sign: -1,
                    neighbour: Some((lo, hi_image.checked_neg()?)),
                    chart_translation: f.normal.map(|n| -n * (2. * f.plane_distance)),
                });
            faces.push(f);
            support.push(active);
        }
        let length = domain.width.into_iter().fold(0.0, f64::max);
        let geometry = publish_geometry(domain, cells, faces, length, GeometryQuality3::default())?;
        Ok(Some(SupportedGeometry3 {
            geometry,
            support,
            cartesian_product: true,
        }))
    }
}
