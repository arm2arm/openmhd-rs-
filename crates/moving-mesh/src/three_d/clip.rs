use super::exact::{D, Point, det, dot};
use super::{FaceKey3, GeometryError3, Image3};
use std::cmp::Ordering;

type Result<T> = std::result::Result<T, GeometryError3>;
pub(crate) const MAX_FACES: usize = 256;
const MAX_FACE_VERTICES: usize = 256;
const MAX_SUPPORT: usize = 64;
const MAX_PREDICATES: usize = 500_000_000;

#[derive(Default)]
pub(crate) struct Budget {
    pub predicates: usize,
    pub contacts: usize,
    pub planes: usize,
}

impl Budget {
    fn tick(&mut self) -> Result<()> {
        self.predicates += 1;
        if self.predicates > MAX_PREDICATES { return Err(GeometryError3::ResourceLimit("predicate operations")); }
        Ok(())
    }
}

#[derive(Clone)]
pub(crate) struct Plane {
    pub n: [D; 3],
    pub h: D,
    pub key: FaceKey3,
    pub sign: i8,
    pub neighbour: Option<usize>,
    pub wrapped_image: Image3,
}

impl Plane {
    fn side(&self, point: &Point, budget: &mut Budget) -> Result<i8> {
        budget.tick()?;
        Ok(dot(&self.n, &point.numerator)?.sub(&self.h.mul(&point.denominator)?)?.sign())
    }
}

#[derive(Clone)]
pub(crate) struct Vertex {
    pub point: Point,
    support: Vec<usize>,
}

impl Vertex {
    fn add_support(&mut self, index: usize) -> Result<()> {
        if let Err(at) = self.support.binary_search(&index) { self.support.insert(at, index); }
        if self.support.len() > MAX_SUPPORT { return Err(GeometryError3::ResourceLimit("vertex support")); }
        Ok(())
    }
}

#[derive(Clone)]
pub(crate) struct Polygon {
    pub plane: usize,
    pub vertices: Vec<Vertex>,
}

fn intersection(indices: [usize; 3], planes: &[Plane], budget: &mut Budget) -> Result<Vertex> {
    budget.tick()?;
    let rows = indices.map(|i| planes[i].n.clone());
    let mut denominator = det(&rows)?;
    if denominator.sign() == 0 { return Err(GeometryError3::SingularIntersection); }
    let mut numerator = [D::zero(), D::zero(), D::zero()];
    for (a, value) in numerator.iter_mut().enumerate() {
        let mut replaced = rows.clone();
        for k in 0..3 { replaced[k][a] = planes[indices[k]].h.clone(); }
        *value = det(&replaced)?;
    }
    if denominator.sign() < 0 {
        denominator = denominator.neg();
        numerator = numerator.map(|v| v.neg());
    }
    let mut support = indices.to_vec();
    support.sort_unstable();
    Ok(Vertex { point: Point { numerator, denominator }, support })
}

fn crossing(a: &Vertex, b: &Vertex, new: usize, planes: &[Plane], budget: &mut Budget) -> Result<Vertex> {
    let common: Vec<_> = a.support.iter().copied().filter(|i| b.support.binary_search(i).is_ok()).collect();
    for i in 0..common.len() {
        for j in i + 1..common.len() {
            match intersection([common[i], common[j], new], planes, budget) {
                Ok(mut vertex) => {
                    for k in &common { vertex.add_support(*k)?; }
                    return Ok(vertex);
                }
                Err(GeometryError3::SingularIntersection) => {}
                Err(error) => return Err(error),
            }
        }
    }
    Err(GeometryError3::InvalidTopology("crossing edge lacks independent supports"))
}

fn orientation(a: &Point, b: &Point, c: &Point, axes: [usize; 2], budget: &mut Budget) -> Result<i8> {
    budget.tick()?;
    let row = |p: &Point| [p.numerator[axes[0]].clone(), p.numerator[axes[1]].clone(), p.denominator.clone()];
    Ok(det(&[row(a), row(b), row(c)])?.sign())
}

/// Exact projected monotone hull. Only equal or exactly collinear points are
/// removed. Cyclic projection makes its sign the selected 3D normal component.
pub(crate) fn convex_loop(vertices: Vec<Vertex>, normal: &[D; 3], budget: &mut Budget) -> Result<Vec<Vertex>> {
    let mut dominant = 0;
    for a in 1..3 {
        let magnitude = |d: &D| if d.sign() < 0 { d.neg() } else { d.clone() };
        if magnitude(&normal[a]).cmp(&magnitude(&normal[dominant]))? == Ordering::Greater { dominant = a; }
    }
    if normal[dominant].sign() == 0 { return Err(GeometryError3::InvalidTopology("zero plane normal")); }
    let axes = [(dominant + 1) % 3, (dominant + 2) % 3];
    let mut sorted: Vec<Vertex> = Vec::new();
    for vertex in vertices {
        let mut at = 0;
        while at < sorted.len() {
            budget.tick()?;
            let order = vertex.point.compare_axis(&sorted[at].point, axes[0])?
                .then(vertex.point.compare_axis(&sorted[at].point, axes[1])?);
            if order != Ordering::Greater { break; }
            at += 1;
        }
        if at < sorted.len() && vertex.point.same(&sorted[at].point)? {
            for index in vertex.support { sorted[at].add_support(index)?; }
        } else { sorted.insert(at, vertex); }
    }
    if sorted.len() > MAX_FACE_VERTICES { return Err(GeometryError3::ResourceLimit("face vertices")); }
    if sorted.len() < 3 { return Ok(Vec::new()); }
    let mut lower: Vec<Vertex> = Vec::new();
    let mut upper: Vec<Vertex> = Vec::new();
    for (chain, sequence) in [(&mut lower, sorted.clone()), (&mut upper, sorted.iter().rev().cloned().collect())] {
        for vertex in sequence {
            while chain.len() >= 2 && orientation(&chain[chain.len() - 2].point,
                &chain[chain.len() - 1].point, &vertex.point, axes, budget)? <= 0 {
                chain.pop();
            }
            chain.push(vertex);
        }
    }
    lower.pop();
    upper.pop();
    lower.extend(upper);
    if lower.len() < 3 { return Ok(Vec::new()); }
    if normal[dominant].sign() < 0 { lower.reverse(); }
    // Start at lexicographically smallest projected coordinate, either winding.
    let mut first = None;
    for (index, vertex) in lower.iter().enumerate() {
        if vertex.point.same(&sorted[0].point)? { first = Some(index); break; }
    }
    let first = first.ok_or(GeometryError3::InvalidTopology("hull lost extreme vertex"))?;
    lower.rotate_left(first);
    Ok(lower)
}

pub(crate) fn initial_box(planes: &[Plane], budget: &mut Budget) -> Result<Vec<Polygon>> {
    let mut corners = Vec::new();
    for z in 0..2 { for y in 0..2 { for x in 0..2 {
        corners.push(intersection([x, 2 + y, 4 + z], planes, budget)?);
    } } }
    let mut faces = Vec::new();
    for p in 0..6 {
        let points = corners.iter().filter(|v| v.support.contains(&p)).cloned().collect();
        faces.push(Polygon { plane: p, vertices: convex_loop(points, &planes[p].n, budget)? });
    }
    Ok(faces)
}

pub(crate) fn clip(faces: &mut Vec<Polygon>, new: usize, planes: &[Plane], budget: &mut Budget) -> Result<()> {
    budget.planes += 1;
    let plane = &planes[new];
    let mut outside = false;
    let mut contact = false;
    for face in faces.iter_mut() {
        for vertex in &mut face.vertices {
            match plane.side(&vertex.point, budget)? {
                1 => outside = true,
                0 => { vertex.add_support(new)?; contact = true; }
                _ => {}
            }
        }
    }
    if !outside {
        if contact { budget.contacts += 1; }
        return Ok(());
    }
    let mut result = Vec::new();
    let mut cap = Vec::new();
    for face in faces.iter() {
        let mut kept = Vec::new();
        for a in 0..face.vertices.len() {
            let left = &face.vertices[a];
            let right = &face.vertices[(a + 1) % face.vertices.len()];
            let sl = plane.side(&left.point, budget)?;
            let sr = plane.side(&right.point, budget)?;
            if sl <= 0 {
                kept.push(left.clone());
                if sl == 0 { cap.push(left.clone()); }
            }
            if sl * sr < 0 {
                let vertex = crossing(left, right, new, planes, budget)?;
                cap.push(vertex.clone());
                kept.push(vertex);
            }
        }
        let vertices = convex_loop(kept, &planes[face.plane].n, budget)?;
        if !vertices.is_empty() { result.push(Polygon { plane: face.plane, vertices }); }
    }
    let vertices = convex_loop(cap, &plane.n, budget)?;
    if vertices.is_empty() { return Err(GeometryError3::InvalidTopology("strict cut without positive cap")); }
    result.push(Polygon { plane: new, vertices });
    if result.len() > MAX_FACES { return Err(GeometryError3::ResourceLimit("cell faces")); }
    if result.iter().map(|p| p.vertices.len()).sum::<usize>() > 4096 {
        return Err(GeometryError3::ResourceLimit("cell polygon incidences"));
    }
    if result.len() < 4 { return Err(GeometryError3::InvalidTopology("empty/lower-dimensional cell")); }
    *faces = result;
    Ok(())
}

/// Exact edge-manifold, plane-containment and positive-generator checks. Faces
/// have independent vertex copies; compare rational coordinates, not f64 bits.
pub(crate) fn validate(faces: &[Polygon], planes: &[Plane], budget: &mut Budget) -> Result<()> {
    let mut points: Vec<Point> = Vec::new();
    let mut edges = std::collections::BTreeMap::<(usize, usize), (usize, i32)>::new();
    for face in faces {
        if planes[face.plane].h.sign() <= 0 { return Err(GeometryError3::InvalidTopology("generator not strictly interior")); }
        let mut loop_ids = Vec::new();
        for vertex in &face.vertices {
            if planes[face.plane].side(&vertex.point, budget)? != 0 {
                return Err(GeometryError3::InvalidTopology("vertex off supporting plane"));
            }
            let mut id = None;
            for (i, point) in points.iter().enumerate() {
                if vertex.point.same(point)? { id = Some(i); break; }
            }
            let id = id.unwrap_or_else(|| { points.push(vertex.point.clone()); points.len() - 1 });
            loop_ids.push(id);
        }
        for k in 0..loop_ids.len() {
            let a = loop_ids[k];
            let b = loop_ids[(k + 1) % loop_ids.len()];
            if a == b { return Err(GeometryError3::InvalidTopology("zero edge")); }
            let row = edges.entry((a.min(b), a.max(b))).or_default();
            row.0 += 1;
            row.1 += if a < b { 1 } else { -1 };
        }
    }
    if edges.values().any(|v| *v != (2, 0)) || points.len() + faces.len() != edges.len() + 2 {
        return Err(GeometryError3::InvalidTopology("edge manifold/Euler closure"));
    }
    // Every final vertex is inside every original constraint, not just its face.
    for point in &points {
        for plane in planes {
            if plane.side(point, budget)? > 0 { return Err(GeometryError3::InvalidTopology("constraint violation")); }
        }
    }
    Ok(())
}
