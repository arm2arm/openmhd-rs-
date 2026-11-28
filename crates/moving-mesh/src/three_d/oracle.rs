use super::clip::{self, Budget, Plane};
use super::exact::{D, Point, dot as exact_dot};
use super::moments::{self, FaceIntegral, Sum};
use super::*;
use std::cmp::Ordering;
use std::collections::BTreeMap;
use std::sync::atomic::{AtomicU64, Ordering as AtomicOrdering};

type Result<T> = std::result::Result<T, GeometryError3>;
static NEXT_EPOCH: AtomicU64 = AtomicU64::new(1);

/// Independent all-pairs, serial reference; no search tree or external backend.
/// Hard bounds are rejections, never a change of the geometry problem.
pub struct HalfSpaceOracle3;

struct RawFace {
    owner: usize,
    plane: Plane,
    points: Vec<Point>,
    integral: FaceIntegral,
    support: FaceVertexSupports3,
}

fn vector_sub(a: &[D; 3], b: &[D; 3]) -> Result<[D; 3]> {
    Ok([a[0].sub(&b[0])?, a[1].sub(&b[1])?, a[2].sub(&b[2])?])
}

pub(super) fn separation(
    left: Generator3,
    right: Generator3,
    image: Image3,
    width: &[D; 3],
) -> Result<[D; 3]> {
    let mut d = vector_sub(
        &left.position.map(D::from_f64),
        &right.position.map(D::from_f64),
    )?;
    for a in 0..3 {
        // This backend only constructs wrapped shifts -1,0,1, exactly encoded.
        if !(-1..=1).contains(&image.0[a]) {
            return Err(GeometryError3::ImageOverflow);
        }
        d[a] = width[a].mul(&D::from_f64(image.0[a] as f64))?.sub(&d[a])?;
    }
    Ok(d)
}

fn key(left: Generator3, right: Generator3, wrapped: Image3) -> Result<(FaceKey3, i8)> {
    let image = wrapped.trajectory(left.winding, right.winding)?;
    let positive = image.0.iter().find(|v| **v != 0).is_some_and(|v| *v > 0);
    if left.id == right.id && image == Image3::ZERO {
        return Err(GeometryError3::InvalidTopology("zero self-image"));
    }
    let forward = left.id < right.id || (left.id == right.id && positive);
    Ok(if forward {
        (
            FaceKey3::Interior {
                lo: left.id,
                hi: right.id,
                hi_image: image,
            },
            1,
        )
    } else {
        (
            FaceKey3::Interior {
                lo: right.id,
                hi: left.id,
                hi_image: image.checked_neg()?,
            },
            -1,
        )
    })
}

fn bisector(
    left: Generator3,
    right: Generator3,
    neighbour: usize,
    image: Image3,
    width: &[D; 3],
) -> Result<Plane> {
    let n = separation(left, right, image, width)?;
    let h = exact_dot(&n, &n)?.half();
    if h.sign() == 0 {
        return Err(GeometryError3::CoincidentGenerators {
            first: left.id,
            second: right.id,
        });
    }
    let (key, sign) = key(left, right, image)?;
    Ok(Plane {
        n,
        h,
        key,
        sign,
        neighbour: Some(neighbour),
        wrapped_image: image,
    })
}

fn constraints(
    owner: usize,
    generators: &[Generator3],
    domain: Domain3,
    width: &[D; 3],
) -> Result<Vec<Plane>> {
    let generator = generators[owner];
    let position = generator.position.map(D::from_f64);
    let anchor = domain.anchor.map(D::from_f64);
    let mut planes = Vec::new();
    // Six starting planes in axis/side order; periodic ones are real self planes.
    for axis in 0..3 {
        for side in 0..2 {
            if domain.boundary == Boundary3::Periodic {
                let mut image = [0; 3];
                image[axis] = if side == 0 { -1 } else { 1 };
                let mut plane = bisector(generator, generator, owner, Image3(image), width)?;
                plane.n = [D::zero(), D::zero(), D::zero()];
                plane.n[axis] = D::from_f64(if side == 0 { -1.0 } else { 1.0 });
                plane.h = width[axis].half();
                planes.push(plane);
            } else {
                let mut n = [D::zero(), D::zero(), D::zero()];
                n[axis] = D::from_f64(if side == 0 { -1.0 } else { 1.0 });
                let h = if side == 0 {
                    position[axis].sub(&anchor[axis])?
                } else {
                    anchor[axis].add(&width[axis])?.sub(&position[axis])?
                };
                planes.push(Plane {
                    n,
                    h,
                    key: FaceKey3::Boundary {
                        cell: generator.id,
                        patch: BoundaryPatch3((2 * axis + side) as u8),
                    },
                    sign: 1,
                    neighbour: None,
                    wrapped_image: Image3::ZERO,
                });
            }
        }
    }
    for (neighbour, other) in generators.iter().copied().enumerate() {
        if domain.boundary == Boundary3::Bounded {
            if owner != neighbour {
                planes.push(bisector(generator, other, neighbour, Image3::ZERO, width)?);
            }
        } else {
            for x in -1_i64..=1 {
                for y in -1_i64..=1 {
                    for z in -1_i64..=1 {
                        let image = Image3([x, y, z]);
                        let nonzero = image.0.iter().filter(|v| **v != 0).count();
                        if owner == neighbour && nonzero <= 1 {
                            continue;
                        } // already six initial self planes
                        planes.push(bisector(generator, other, neighbour, image, width)?);
                    }
                }
            }
        }
    }
    Ok(planes)
}

// Axis-aligned bisectors can bound the cell even for a partially aligned cloud.
// A strictly distant bisector cannot touch this bounding box.
fn exclude_distant_planes(planes: Vec<Plane>) -> Result<Vec<Plane>> {
    let mut bounds: [D; 6] = std::array::from_fn(|index| planes[index].h.clone());
    let mut tightened = false;
    for p in &planes[6..] {
        let mut nonzero =
            p.n.iter()
                .enumerate()
                .filter(|(_, value)| value.sign() != 0);
        let Some((axis, component)) = nonzero.next() else {
            continue;
        };
        if nonzero.next().is_some() {
            continue;
        }
        // A generator bisector has normal d and offset |d|²/2.
        let positive = component.sign() > 0;
        let index = 2 * axis + usize::from(positive);
        let distance = if positive {
            component.half()
        } else {
            component.neg().half()
        };
        if distance.cmp(&bounds[index])? == Ordering::Less {
            bounds[index] = distance;
            tightened = true;
        }
    }
    if !tightened {
        return Ok(planes);
    }
    let mut radius_squared = D::zero();
    for pair in bounds.chunks_exact(2) {
        let max = if pair[0].cmp(&pair[1])? == Ordering::Greater {
            &pair[0]
        } else {
            &pair[1]
        };
        radius_squared = radius_squared.add(&max.mul(max)?)?;
    }
    // Inside this box, |x|² <= R². A bisector at distance |d|/2 strictly
    // beyond R cannot cut or touch the final cell. Equality is retained.
    let twice_radius_squared = radius_squared.add(&radius_squared)?;
    let mut kept = Vec::with_capacity(planes.len());
    for (index, p) in planes.into_iter().enumerate() {
        if index < 6 || p.h.cmp(&twice_radius_squared)? != Ordering::Greater {
            kept.push(p);
        }
    }
    Ok(kept)
}

fn inputs(domain: Domain3, input: &[Generator3]) -> Result<Vec<Generator3>> {
    if !domain.anchor.iter().all(|v| v.is_finite())
        || !domain.width.iter().all(|v| v.is_finite() && *v > 0.0)
    {
        return Err(GeometryError3::InvalidDomain);
    }
    for a in 0..3 {
        if !(domain.anchor[a] + domain.width[a]).is_finite()
            || domain.anchor[a] + domain.width[a] <= domain.anchor[a]
        {
            return Err(GeometryError3::InvalidDomain);
        }
    }
    if input.is_empty() {
        return Err(GeometryError3::EmptyCatalog);
    }
    if input.len() > 512 {
        return Err(GeometryError3::TooManyGenerators {
            count: input.len(),
            limit: 512,
        });
    }
    let mut sorted = input.to_vec();
    sorted.sort_by_key(|g| g.id);
    for (i, generator) in sorted.iter().enumerate() {
        if i != 0 && sorted[i - 1].id == generator.id {
            return Err(GeometryError3::DuplicateId { id: generator.id });
        }
        if !generator.position.iter().all(|v| v.is_finite()) {
            return Err(GeometryError3::NonFiniteGenerator { id: generator.id });
        }
        if domain.boundary == Boundary3::Bounded && generator.winding != Image3::ZERO {
            return Err(GeometryError3::BoundedWinding { id: generator.id });
        }
        for a in 0..3 {
            let position = D::from_f64(generator.position[a]);
            let low = D::from_f64(domain.anchor[a]);
            let high = low.add(&D::from_f64(domain.width[a]))?;
            let lower = position.cmp(&low)?;
            let upper = position.cmp(&high)?;
            if lower == Ordering::Less
                || upper != Ordering::Less
                || (domain.boundary == Boundary3::Bounded && lower == Ordering::Equal)
            {
                return Err(GeometryError3::GeneratorOutside { id: generator.id });
            }
        }
        for other in &sorted[..i] {
            if (0..3).all(|a| generator.position[a] == other.position[a]) {
                return Err(GeometryError3::CoincidentGenerators {
                    first: other.id,
                    second: generator.id,
                });
            }
        }
    }
    Ok(sorted)
}

fn paired(left: &RawFace, right: &RawFace, displacement: &[D; 3], length: f64) -> Result<()> {
    let fail = || GeometryError3::FaceMismatch {
        key: left.plane.key,
    };
    // Independent owner clips must trace the same directed edges in reverse
    // after lifting to the left chart. Convex hulls may start at different vertices.
    let n = left.points.len();
    if n < 3 || n != right.points.len() {
        return Err(fail());
    }
    let first = right.points[0].translated(displacement)?;
    let mut pivot = None;
    for (index, vertex) in left.points.iter().enumerate() {
        if vertex.same(&first)? {
            pivot = Some(index);
            break;
        }
    }
    let pivot = pivot.ok_or_else(fail)?;
    for (j, vertex) in right.points.iter().enumerate().skip(1) {
        if !left.points[(pivot + n - j) % n].same(&vertex.translated(displacement)?)? {
            return Err(fail());
        }
    }
    let l = &left.integral;
    let r = &right.integral;
    let d = Point {
        numerator: displacement.clone(),
        denominator: D::one(),
    }
    .scaled_f64(&D::one())?;
    if (l.area / r.area - 1.0).abs() > 1e-10
        || moments::norm(moments::add(l.normal, r.normal)) > 1e-10
        || moments::norm(moments::sub(l.centroid, moments::add(r.centroid, d))) / length > 1e-10
    {
        return Err(fail());
    }
    for a in 0..3 {
        for b in 0..3 {
            if (l.covariance[a][b] - r.covariance[a][b]).abs() / (length * length) > 1e-10 {
                return Err(fail());
            }
        }
    }
    Ok(())
}

/// Validate the actually exported single shared metrics, not just the two
/// independently integrated owner-side precursors. No pair averaging/repair.
fn validate_shared(
    cells: &mut [CellGeometry3],
    faces: &[SharedFace3],
    length: f64,
    quality: &mut GeometryQuality3,
) -> Result<()> {
    for cell in cells {
        let mut surface = Sum::default();
        let mut normal = [Sum::default(); 3];
        let mut affine = [[Sum::default(); 3]; 3];
        let mut centred = [Sum::default(); 3];
        let mut divergence_volume = Sum::default();
        let centroid = moments::scale(cell.centroid_offset, 1.0 / length);
        let volume = cell.volume / (length * length * length);
        let mut radius = 0.0_f64;
        let mut minimum_distance = f64::INFINITY;
        for incidence in &cell.incidences {
            let face = &faces[incidence.face as usize];
            let area = face.area / (length * length);
            let n = moments::scale(face.normal, f64::from(incidence.sign));
            let f = moments::scale(
                moments::add(face.centroid_offset, incidence.chart_translation),
                1.0 / length,
            );
            let y = moments::sub(f, centroid);
            let distance = moments::dot(f, n);
            if !distance.is_finite() || distance <= 0.0 || moments::dot(y, n) < -1e-12 {
                return Err(GeometryError3::InvalidTopology(
                    "shared chart/centroid containment",
                ));
            }
            minimum_distance = minimum_distance.min(distance);
            for p in &face.polygon {
                radius = radius.max(moments::norm(moments::scale(
                    moments::add(*p, incidence.chart_translation),
                    1.0 / length,
                )));
            }
            surface.add(area);
            divergence_volume.add(area * distance / 3.0);
            for a in 0..3 {
                normal[a].add(area * n[a]);
                centred[a].add(area * moments::dot(y, n) * y[a]);
                for (b, &normal_component) in n.iter().enumerate() {
                    affine[a][b].add(area * y[a] * normal_component);
                }
            }
        }
        let normal_residual = moments::norm(normal.map(Sum::get)) / surface.get();
        let centroid_residual = moments::norm(centred.map(Sum::get)) / volume;
        let mut affine_residual = 0.0_f64;
        for (a, row) in affine.iter().enumerate() {
            for (b, value) in row.iter().enumerate() {
                affine_residual = affine_residual
                    .max((value.get() / volume - if a == b { 1.0 } else { 0.0 }).abs());
            }
        }
        for (quantity, residual) in [
            ("shared normal closure", normal_residual),
            ("shared affine closure", affine_residual),
            ("shared centroid closure", centroid_residual),
            (
                "shared divergence volume",
                (divergence_volume.get() / volume - 1.0).abs(),
            ),
        ] {
            if !residual.is_finite() || residual > 1e-10 {
                return Err(GeometryError3::NumericalValidation { quantity, residual });
            }
        }
        quality.maximum_normal_closure = quality.maximum_normal_closure.max(normal_residual);
        quality.maximum_affine_closure = quality.maximum_affine_closure.max(affine_residual);
        quality.maximum_centroid_closure = quality.maximum_centroid_closure.max(centroid_residual);
        cell.surface_area = surface.get() * length * length;
        cell.bounding_radius = radius * length;
        cell.minimum_generator_face_distance = minimum_distance * length;
    }
    Ok(())
}

impl HalfSpaceOracle3 {
    pub const MAX_GENERATORS: usize = 512;
    pub const BACKEND: &'static str = "independent-all-pairs-dyadic-halfspace-v1";

    /// Pure static rebuild. No input/state mutation; failed builds publish no
    /// geometry. Epochs are process-local capability labels, not restart IDs.
    pub fn build(domain: Domain3, input: &[Generator3]) -> Result<ValidatedGeometry3> {
        Self::build_inner(domain, input, None, false)
    }

    /// Rebuild a motion epoch. Axis-aligned bisectors can certify a tighter
    /// bounding box before clipping. Only strictly disjoint planes are omitted.
    pub fn build_motion_epoch(domain: Domain3, input: &[Generator3]) -> Result<ValidatedGeometry3> {
        Self::build_inner(domain, input, None, true)
    }

    pub fn build_supported_periodic(
        domain: Domain3,
        input: &[Generator3],
    ) -> Result<SupportedGeometry3> {
        if domain.boundary != Boundary3::Periodic {
            return Err(GeometryError3::InvalidDomain);
        }
        let mut support = Vec::new();
        let geometry = Self::build_inner(domain, input, Some(&mut support), false)?;
        Ok(SupportedGeometry3 { geometry, support })
    }

    fn build_inner(
        domain: Domain3,
        input: &[Generator3],
        mut catalog: Option<&mut Vec<FaceVertexSupports3>>,
        use_motion_bounds: bool,
    ) -> Result<ValidatedGeometry3> {
        let generators = inputs(domain, input)?;
        let width = domain.width.map(D::from_f64);
        let length = domain.width.into_iter().fold(0.0_f64, f64::max);
        let mut budget = Budget::default();
        let mut cells = Vec::new();
        let mut raw = BTreeMap::<FaceKey3, Vec<RawFace>>::new();
        let mut retained_raw_vertices = 0_usize;
        let mut quality = GeometryQuality3 {
            relative_volume_closure: 0.0,
            maximum_normal_closure: 0.0,
            maximum_affine_closure: 0.0,
            maximum_centroid_closure: 0.0,
            certified_contact_planes: 0,
            clipping_planes: 0,
            predicate_operations: 0,
        };
        for (owner, generator) in generators.iter().copied().enumerate() {
            let mut planes = constraints(owner, &generators, domain, &width)?;
            if use_motion_bounds {
                planes = exclude_distant_planes(planes)?;
            }
            let mut polygons = clip::initial_box(&planes, &mut budget)?;
            for new in 6..planes.len() {
                clip::clip(&mut polygons, new, &planes, &mut budget)?;
            }
            polygons.sort_by_key(|p| (planes[p.plane].key, planes[p.plane].sign));
            clip::validate(&polygons, &planes, &mut budget)?;
            let integrals = moments::integrate(&polygons, &planes, length)?;
            quality.maximum_normal_closure =
                quality.maximum_normal_closure.max(integrals.normal_closure);
            quality.maximum_affine_closure =
                quality.maximum_affine_closure.max(integrals.affine_closure);
            quality.maximum_centroid_closure = quality
                .maximum_centroid_closure
                .max(integrals.centroid_closure);
            cells.push(CellGeometry3 {
                generator,
                volume: integrals.volume,
                centroid_offset: integrals.centroid,
                central_second_moment: integrals.moment,
                surface_area: integrals.surface,
                bounding_radius: integrals.radius,
                minimum_generator_face_distance: integrals.minimum_distance,
                incidences: Vec::new(),
            });
            for (polygon, integral) in polygons.into_iter().zip(integrals.faces) {
                if polygon.plane != integral.plane {
                    return Err(GeometryError3::InvalidTopology("face integration order"));
                }
                retained_raw_vertices += polygon.vertices.len();
                if retained_raw_vertices > 65_536 {
                    return Err(GeometryError3::ResourceLimit("retained raw vertices"));
                }
                let plane = planes[polygon.plane].clone();
                let entry = raw.entry(plane.key).or_default();
                let mut support = Vec::new();
                if catalog.is_some() && plane.sign == 1 {
                    for v in &polygon.vertices {
                        let mut active = Vec::new();
                        for p in &planes {
                            if p.side(&v.point, &mut budget)? == 0 {
                                let neighbour =
                                    p.neighbour.ok_or(GeometryError3::InvalidDomain)? as u32;
                                active.push(VertexPlane3 {
                                    neighbour,
                                    image: p.wrapped_image,
                                });
                            }
                        }
                        active.sort_unstable();
                        support.push(active);
                    }
                }
                entry.push(RawFace {
                    owner,
                    plane,
                    points: polygon.vertices.into_iter().map(|v| v.point).collect(),
                    integral,
                    support,
                });
                if entry.len() > 2 {
                    return Err(GeometryError3::InvalidTopology("duplicate canonical face"));
                }
            }
        }
        let mut faces = Vec::new();
        for (key, mut rows) in raw {
            rows.sort_by_key(|r| -r.plane.sign);
            let left = &rows[0];
            let fail = || GeometryError3::FaceMismatch { key };
            let mut displacement = [D::zero(), D::zero(), D::zero()];
            let right_owner = match key {
                FaceKey3::Boundary { .. } => {
                    if rows.len() != 1 || left.plane.sign != 1 || left.plane.neighbour.is_some() {
                        return Err(fail());
                    }
                    None
                }
                FaceKey3::Interior { lo, hi, .. } => {
                    if rows.len() != 2 || left.plane.sign != 1 || rows[1].plane.sign != -1 {
                        return Err(fail());
                    }
                    let right = &rows[1];
                    if generators[left.owner].id != lo
                        || generators[right.owner].id != hi
                        || left.plane.neighbour != Some(right.owner)
                        || right.plane.neighbour != Some(left.owner)
                        || right.plane.wrapped_image != left.plane.wrapped_image.checked_neg()?
                    {
                        return Err(fail());
                    }
                    displacement = separation(
                        generators[left.owner],
                        generators[right.owner],
                        left.plane.wrapped_image,
                        &width,
                    )?;
                    paired(left, right, &displacement, length)?;
                    Some(right.owner)
                }
            };
            let face_index = u32::try_from(faces.len())
                .map_err(|_| GeometryError3::ResourceLimit("face index"))?;
            let neighbour = match key {
                FaceKey3::Interior { hi, hi_image, .. } => Some((hi, hi_image)),
                _ => None,
            };
            cells[left.owner].incidences.push(FaceIncidence3 {
                face: face_index,
                sign: 1,
                neighbour,
                chart_translation: [0.0; 3],
            });
            if let Some(owner) = right_owner {
                let translation = Point {
                    numerator: displacement.map(|v| v.neg()),
                    denominator: D::one(),
                }
                .scaled_f64(&D::one())?;
                let neighbour = match key {
                    FaceKey3::Interior { lo, hi_image, .. } => Some((lo, hi_image.checked_neg()?)),
                    _ => return Err(fail()),
                };
                cells[owner].incidences.push(FaceIncidence3 {
                    face: face_index,
                    sign: -1,
                    neighbour,
                    chart_translation: translation,
                });
            }
            let integral = &left.integral;
            if let Some(output) = catalog.as_mut() {
                output.push(left.support.clone());
            }
            faces.push(SharedFace3 {
                key,
                left: left.owner as u32,
                right: right_owner.map(|i| i as u32),
                right_wrapped_image: left.plane.wrapped_image,
                area: integral.area,
                normal: integral.normal,
                centroid_offset: integral.centroid,
                plane_distance: integral.distance,
                polygon: integral.polygon.clone(),
                covariance: integral.covariance,
            });
        }
        validate_shared(&mut cells, &faces, length, &mut quality)?;
        let mut total = Sum::default();
        for cell in &cells {
            total.add(cell.volume);
        }
        let expected = domain.width[0] * domain.width[1] * domain.width[2];
        quality.relative_volume_closure = (total.get() / expected - 1.0).abs();
        if !expected.is_finite()
            || expected <= 0.0
            || !quality.relative_volume_closure.is_finite()
            || quality.relative_volume_closure > 1e-10
        {
            return Err(GeometryError3::NumericalValidation {
                quantity: "domain volume closure",
                residual: quality.relative_volume_closure,
            });
        }
        if domain.boundary == Boundary3::Bounded {
            let mut patch_area = [Sum::default(); 6];
            for face in &faces {
                if let FaceKey3::Boundary { patch, .. } = face.key {
                    patch_area[patch.0 as usize].add(face.area);
                }
            }
            for (p, area) in patch_area.into_iter().enumerate() {
                let axis = p / 2;
                let expected = domain.width[(axis + 1) % 3] * domain.width[(axis + 2) % 3];
                let residual = (area.get() / expected - 1.0).abs();
                if !residual.is_finite() || residual > 1e-10 {
                    return Err(GeometryError3::NumericalValidation {
                        quantity: "boundary patch closure",
                        residual,
                    });
                }
            }
        }
        quality.certified_contact_planes = budget.contacts;
        quality.clipping_planes = budget.planes;
        quality.predicate_operations = budget.predicates;
        let epoch = NEXT_EPOCH
            .fetch_update(AtomicOrdering::SeqCst, AtomicOrdering::SeqCst, |v| {
                v.checked_add(1)
            })
            .map_err(|_| GeometryError3::EpochExhausted)?;
        Ok(ValidatedGeometry3 {
            epoch: GeometryEpoch3(epoch),
            domain,
            cells,
            faces,
            quality,
        })
    }
}
