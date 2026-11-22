//! Small periodic 2D Voronoi reference: independent half-plane clipping in f64.
//! All 3x3 image planes remain eligible; ordered bounding-tree pruning skips only
//! the existing circle-test no-ops. An all-pairs comparator is retained. Optional deterministic threading, no FFI.

use std::collections::BTreeMap;
mod cache;
pub mod checkpoint;
pub mod projection;
pub mod quadratic_jet;

pub mod parallel;
mod quadratic;
pub mod three_d;
pub mod timing;
pub use quadratic::QuadraticHessians;
mod positive_laplacian;
pub use positive_laplacian::PositiveLaplacian;

pub type Vec2 = [f64; 2];
pub fn dot(a: Vec2, b: Vec2) -> f64 {
    a[0] * b[0] + a[1] * b[1]
}
fn sub(a: Vec2, b: Vec2) -> Vec2 {
    [a[0] - b[0], a[1] - b[1]]
}

#[derive(Clone, Debug)]
pub struct Cell {
    pub volume: f64,
    /// Unwrapped near the cell's generator; periodic image offsets remain explicit.
    pub centroid: Vec2,
    pub faces: Vec<(usize, f64)>,
}

#[derive(Clone, Debug)]
pub struct Face {
    pub left: usize,
    pub right: usize,
    pub image: [i32; 2],
    pub centroid: Vec2,
    pub normal: Vec2,
    pub area: f64,
}

#[derive(Clone, Debug)]
pub struct Mesh {
    pub lengths: Vec2,
    pub generators: Vec<Vec2>,
    pub cells: Vec<Cell>,
    pub faces: Vec<Face>,
}

#[derive(Clone, Copy, Debug)]
struct Vertex {
    point: Vec2,
    incoming: (usize, i32, i32),
}

/// Reference half-plane clip. `Polygon::clip` below performs the same
/// operations in the same order; this form is kept to test that claim.
#[cfg(test)]
fn clip(polygon: &[Vertex], delta: Vec2, tag: (usize, i32, i32)) -> Vec<Vertex> {
    let boundary = 0.5 * dot(delta, delta);
    // A plane beyond the polygon's enclosing circle cannot intersect it.
    let radius2 = polygon
        .iter()
        .map(|v| dot(v.point, v.point))
        .fold(0.0, f64::max);
    if dot(delta, delta) > 4.0 * radius2 * (1.0 + 1e-13) {
        return polygon.to_vec();
    }
    let mut result = Vec::with_capacity(polygon.len() + 1);
    for k in 0..polygon.len() {
        let a = polygon[k];
        let b = polygon[(k + 1) % polygon.len()];
        let da = dot(a.point, delta) - boundary;
        let db = dot(b.point, delta) - boundary;
        let inside_a = da <= 0.0;
        let inside_b = db <= 0.0;
        if inside_a != inside_b {
            let t = da / (da - db);
            result.push(Vertex {
                point: [
                    a.point[0] + t * (b.point[0] - a.point[0]),
                    a.point[1] + t * (b.point[1] - a.point[1]),
                ],
                incoming: if inside_a { b.incoming } else { tag },
            });
        }
        if inside_b {
            result.push(b);
        }
    }
    result
}

/// A cell polygon under successive half-plane clips. Every generator of the
/// mesh is offered to every cell in a fixed order, far ones first, so a build
/// is dominated by planes that change the polygon little or not at all. This
/// type keeps the squared radius of every vertex, evaluates the side of each
/// vertex once per plane, copies unbroken runs of kept vertices as blocks and
/// allocates nothing per plane. The vertices, their order and every
/// floating-point operation that produces them are those of `clip`.
struct Polygon {
    vertices: Vec<Vertex>,
    /// `dot(point, point)` of every vertex, in the same order.
    norm2: Vec<f64>,
    /// Largest `norm2`: the squared radius of the enclosing circle.
    radius2: f64,
    // Reused buffers: the next polygon, and the side of the plane of each vertex.
    next: Vec<Vertex>,
    next_norm2: Vec<f64>,
    side: Vec<f64>,
}
impl Polygon {
    fn new(vertices: Vec<Vertex>) -> Self {
        let norm2: Vec<f64> = vertices.iter().map(|v| dot(v.point, v.point)).collect();
        Self {
            radius2: Self::largest(&norm2),
            next: Vec::with_capacity(vertices.len() + 8),
            next_norm2: Vec::with_capacity(vertices.len() + 8),
            side: Vec::with_capacity(vertices.len() + 8),
            vertices,
            norm2,
        }
    }
    /// A maximum does not depend on the order of the vertices.
    fn largest(norm2: &[f64]) -> f64 {
        norm2.iter().copied().fold(0.0, f64::max)
    }
    fn clip(&mut self, delta: Vec2, tag: (usize, i32, i32)) {
        let boundary = 0.5 * dot(delta, delta);
        // A plane beyond the polygon's enclosing circle cannot intersect it.
        if dot(delta, delta) > 4.0 * self.radius2 * (1.0 + 1e-13) {
            return;
        }
        let count = self.vertices.len();
        if count == 0 {
            return;
        }
        // The reference evaluates this for a vertex as the end of one edge
        // and again as the start of the next: the same value both times.
        self.side.clear();
        self.side
            .extend(self.vertices.iter().map(|v| dot(v.point, delta) - boundary));
        // With every vertex inside, the reference loop emits each successor in
        // turn: the same polygon starting one vertex later. That start decides
        // the order of the area and centroid sums, so it is reproduced.
        if self.side.iter().all(|d| *d <= 0.0) {
            self.vertices.rotate_left(1);
            self.norm2.rotate_left(1);
            return;
        }
        self.next.clear();
        self.next_norm2.clear();
        let mut k = 0;
        while k < count {
            let end = if k + 1 == count { 0 } else { k + 1 };
            let (da, db) = (self.side[k], self.side[end]);
            let inside_a = da <= 0.0;
            let inside_b = db <= 0.0;
            if inside_a != inside_b {
                let (a, b) = (self.vertices[k], self.vertices[end]);
                let t = da / (da - db);
                let point = [
                    a.point[0] + t * (b.point[0] - a.point[0]),
                    a.point[1] + t * (b.point[1] - a.point[1]),
                ];
                self.next.push(Vertex {
                    point,
                    incoming: if inside_a { b.incoming } else { tag },
                });
                self.next_norm2.push(dot(point, point));
            }
            if inside_b && end != 0 {
                // The reference emits `end` here and, edge by edge, every
                // inside vertex that follows it without a crossing: one block.
                let mut last = end;
                while last + 1 < count && self.side[last + 1] <= 0.0 {
                    last += 1;
                }
                self.next.extend_from_slice(&self.vertices[end..=last]);
                self.next_norm2.extend_from_slice(&self.norm2[end..=last]);
                // The edge that leaves `last` has not been examined yet.
                k = last;
                continue;
            }
            if inside_b {
                self.next.push(self.vertices[0]);
                self.next_norm2.push(self.norm2[0]);
            }
            k += 1;
        }
        std::mem::swap(&mut self.vertices, &mut self.next);
        std::mem::swap(&mut self.norm2, &mut self.next_norm2);
        self.radius2 = Self::largest(&self.norm2);
    }
}

/// Contiguous ID ranges preserve traversal order independently of geometry.
struct RangeTree {
    start: usize,
    end: usize,
    lower: Vec2,
    upper: Vec2,
    children: Option<Box<[RangeTree; 2]>>,
}
impl RangeTree {
    fn new(points: &[Vec2], start: usize, end: usize) -> Self {
        let lower = std::array::from_fn(|k| {
            points[start..end]
                .iter()
                .map(|p| p[k])
                .fold(f64::INFINITY, f64::min)
        });
        let upper = std::array::from_fn(|k| {
            points[start..end]
                .iter()
                .map(|p| p[k])
                .fold(f64::NEG_INFINITY, f64::max)
        });
        let children = if end - start > 8 {
            let middle = start + (end - start) / 2;
            Some(Box::new([
                Self::new(points, start, middle),
                Self::new(points, middle, end),
            ]))
        } else {
            None
        };
        Self {
            start,
            end,
            lower,
            upper,
            children,
        }
    }
}
struct PlaneWalk<'a> {
    points: &'a [Vec2],
    lengths: Vec2,
    scale: f64,
    i: usize,
    pass: usize,
}
impl PlaneWalk<'_> {
    fn one(&self, j: usize, polygon: &mut Polygon) -> Result<(), String> {
        if self.i == j {
            return Ok(());
        }
        let [lx, ly] = self.lengths;
        let base = sub(self.points[j], self.points[self.i]);
        let nearest = [
            -(base[0] / lx).round() as i32,
            -(base[1] / ly).round() as i32,
        ];
        let mut image = |sx: i32, sy: i32| {
            let delta = [base[0] + f64::from(sx) * lx, base[1] + f64::from(sy) * ly];
            if dot(delta, delta) < 1e-22 * self.scale * self.scale {
                return Err(format!(
                    "duplicate or nearly coincident periodic generators {},{j}",
                    self.i
                ));
            }
            polygon.clip(delta, (j, sx, sy));
            Ok(())
        };
        if self.pass == 0 {
            // The first pass clips the nearest image only, when it is one of the nine.
            let [sx, sy] = nearest;
            if (-1..=1).contains(&sx) && (-1..=1).contains(&sy) {
                image(sx, sy)?;
            }
            return Ok(());
        }
        for sx in -1..=1 {
            for sy in -1..=1 {
                if [sx, sy] != nearest {
                    image(sx, sy)?;
                }
            }
        }
        Ok(())
    }
    fn visit(&self, node: &RangeTree, polygon: &mut Polygon) -> Result<(), String> {
        let radius2 = polygon.radius2;
        // Expand the box to cover subtraction/image-addition roundoff in `one`.
        // Taking independent image minima in each axis is conservative for all 9 images.
        let margin = 64. * f64::EPSILON * self.scale;
        let distance: Vec2 = std::array::from_fn(|k| {
            (-1..=1)
                .map(|image| {
                    let shift = f64::from(image) * self.lengths[k];
                    let lower = node.lower[k] + shift - self.points[self.i][k];
                    let upper = self.points[self.i][k] - (node.upper[k] + shift);
                    (lower.max(upper) - margin).max(0.)
                })
                .fold(f64::INFINITY, f64::min)
        });
        let distance2 = dot(distance, distance);
        if distance2.is_finite() && distance2 > 4. * radius2 * (1. + 1e-13) {
            return Ok(());
        }
        if let Some(children) = &node.children {
            self.visit(&children[0], polygon)?;
            self.visit(&children[1], polygon)?;
        } else {
            for j in node.start..node.end {
                self.one(j, polygon)?;
            }
        }
        Ok(())
    }
}

impl Mesh {
    pub fn lattice(nx: usize, ny: usize, lengths: Vec2, jitter: f64) -> Result<Self, String> {
        Self::build(Self::lattice_points(nx, ny, lengths, jitter)?, lengths)
    }
    fn lattice_points(
        nx: usize,
        ny: usize,
        lengths: Vec2,
        jitter: f64,
    ) -> Result<Vec<Vec2>, String> {
        if nx < 4
            || ny < 4
            || nx.checked_mul(ny).is_none()
            || !jitter.is_finite()
            || !(0.0..=0.25).contains(&jitter)
        {
            return Err("lattice requires nx,ny >= 4 and jitter in [0,0.25]".into());
        }
        let mut points = Vec::with_capacity(nx * ny);
        for j in 0..ny {
            for i in 0..nx {
                // Deterministic trigonometric perturbation, not a random benchmark seed.
                let k = (i + nx * j) as f64;
                points.push([
                    (i as f64 + 0.5 + jitter * (1.7 * k + 0.3).sin()) * lengths[0] / nx as f64,
                    (j as f64 + 0.5 + jitter * (2.3 * k + 0.7).cos()) * lengths[1] / ny as f64,
                ]);
            }
        }
        Ok(points)
    }

    /// Nonuniform lattice whose generators are displaced along x only, by one
    /// deterministic offset per column. Every cell is a rectangle and the mesh
    /// is invariant under translation by one row, so y-invariant data keep a
    /// vanishing discrete transverse derivative. `jitter = 0` is `lattice`.
    pub fn lattice_columns(
        nx: usize,
        ny: usize,
        lengths: Vec2,
        jitter: f64,
    ) -> Result<Self, String> {
        if nx < 4
            || ny < 4
            || nx.checked_mul(ny).is_none()
            || !jitter.is_finite()
            || !(0.0..=0.25).contains(&jitter)
        {
            return Err("lattice requires nx,ny >= 4 and jitter in [0,0.25]".into());
        }
        let mut points = Vec::with_capacity(nx * ny);
        for j in 0..ny {
            for i in 0..nx {
                points.push([
                    (i as f64 + 0.5 + jitter * (1.7 * i as f64 + 0.3).sin()) * lengths[0]
                        / nx as f64,
                    (j as f64 + 0.5) * lengths[1] / ny as f64,
                ]);
            }
        }
        Self::build(points, lengths)
    }

    pub fn build(generators: Vec<Vec2>, lengths: Vec2) -> Result<Self, String> {
        Self::build_impl(generators, lengths, true)
    }

    /// Original exhaustive clipping order, retained for numerical equivalence checks.
    pub fn build_all_pairs(generators: Vec<Vec2>, lengths: Vec2) -> Result<Self, String> {
        Self::build_impl(generators, lengths, false)
    }

    fn build_impl(mut generators: Vec<Vec2>, lengths: Vec2, prune: bool) -> Result<Self, String> {
        let _timer = timing::scope("mesh/build");
        if generators.len() < 9
            || !lengths.iter().all(|l| l.is_finite() && *l > 0.0)
            || !generators.iter().flatten().all(|x| x.is_finite())
        {
            return Err("periodic mesh requires >=9 finite points and positive box lengths".into());
        }
        for p in &mut generators {
            for k in 0..2 {
                p[k] = p[k].rem_euclid(lengths[k]);
            }
        }
        let scale = lengths[0].max(lengths[1]);
        let tree = prune.then(|| RangeTree::new(&generators, 0, generators.len()));
        let built = parallel::try_map(generators.len(), |i| {
            let ri = &generators[i];
            let mut edges = BTreeMap::new();
            let [lx, ly] = lengths;
            let mut polygon = Polygon::new(vec![
                Vertex {
                    point: [-lx / 2.0, -ly / 2.0],
                    incoming: (i, -1, 0),
                },
                Vertex {
                    point: [lx / 2.0, -ly / 2.0],
                    incoming: (i, 0, -1),
                },
                Vertex {
                    point: [lx / 2.0, ly / 2.0],
                    incoming: (i, 1, 0),
                },
                Vertex {
                    point: [-lx / 2.0, ly / 2.0],
                    incoming: (i, 0, 1),
                },
            ]);
            // Exactly the original pass/j/sx/sy order, including periodic ties.
            for pass in 0..2 {
                let walk = PlaneWalk {
                    points: &generators,
                    lengths,
                    scale,
                    i,
                    pass,
                };
                if let Some(tree) = &tree {
                    walk.visit(tree, &mut polygon)?;
                } else {
                    for j in 0..generators.len() {
                        walk.one(j, &mut polygon)?;
                    }
                }
            }
            let polygon = polygon.vertices;
            if polygon.len() < 3 {
                return Err(format!("empty Voronoi cell {i}"));
            }
            let mut twice_area = 0.0;
            let mut first_moment = [0.0; 2];
            for k in 0..polygon.len() {
                let a = polygon[k].point;
                let b = polygon[(k + 1) % polygon.len()].point;
                let det = a[0] * b[1] - a[1] * b[0];
                twice_area += det;
                for d in 0..2 {
                    first_moment[d] += (a[d] + b[d]) * det;
                }
                let distance = dot(sub(b, a), sub(b, a)).sqrt();
                if distance <= 1e-12 * scale {
                    continue;
                } // zero-length cocircular edge
                let (j, sx, sy) = polygon[(k + 1) % polygon.len()].incoming;
                if i == j {
                    return Err("self-image faces unsupported: use a well populated 2D mesh".into());
                }
                let key = (i, j, sx, sy);
                let midpoint = [ri[0] + 0.5 * (a[0] + b[0]), ri[1] + 0.5 * (a[1] + b[1])];
                if edges.insert(key, (distance, midpoint)).is_some() {
                    return Err("duplicate periodic edge".into());
                }
            }
            if twice_area <= 1e-20 * scale * scale || !twice_area.is_finite() {
                return Err(format!("degenerate Voronoi cell {i}"));
            }
            let cell = Cell {
                volume: 0.5 * twice_area,
                centroid: [
                    ri[0] + first_moment[0] / (3.0 * twice_area),
                    ri[1] + first_moment[1] / (3.0 * twice_area),
                ],
                faces: Vec::new(),
            };
            Ok((cell, edges))
        })?;
        let mut cells = Vec::with_capacity(generators.len());
        let mut edges = BTreeMap::new();
        for (cell, cell_edges) in built {
            cells.push(cell);
            edges.extend(cell_edges);
        }
        let mut faces = Vec::new();
        for (&(i, j, sx, sy), &(area, centroid)) in &edges {
            let &(other_area, other_centroid) = edges
                .get(&(j, i, -sx, -sy))
                .ok_or_else(|| format!("unpaired periodic face {i}->{j} ({sx},{sy})"))?;
            let image = [f64::from(sx) * lengths[0], f64::from(sy) * lengths[1]];
            if (area - other_area).abs() > 1e-9 * scale
                || (0..2).any(|k| (centroid[k] - other_centroid[k] - image[k]).abs() > 1e-9 * scale)
            {
                return Err("inconsistent reciprocal Voronoi face".into());
            }
            if i > j {
                continue;
            }
            let delta = [
                generators[j][0] + image[0] - generators[i][0],
                generators[j][1] + image[1] - generators[i][1],
            ];
            let d = dot(delta, delta).sqrt();
            let index = faces.len();
            faces.push(Face {
                left: i,
                right: j,
                image: [sx, sy],
                centroid,
                normal: [delta[0] / d, delta[1] / d],
                area,
            });
            cells[i].faces.push((index, 1.0));
            cells[j].faces.push((index, -1.0));
        }
        let mesh = Self {
            lengths,
            generators,
            cells,
            faces,
        };
        mesh.validate()?;
        Ok(mesh)
    }

    /// Face offset in this cell's periodic image. Requires validated connectivity
    /// and a cell incident to the supplied face (as returned by `Cell::faces`).
    pub fn displacement(&self, face: &Face, cell: usize) -> Vec2 {
        let c = self.cells[cell].centroid;
        if cell == face.left {
            sub(face.centroid, c)
        } else {
            [
                face.centroid[0] - c[0] - f64::from(face.image[0]) * self.lengths[0],
                face.centroid[1] - c[1] - f64::from(face.image[1]) * self.lengths[1],
            ]
        }
    }

    /// Counterclockwise vertices in the cell centroid's periodic image.
    /// Reconstructs each oriented edge's starting vertex from its midpoint/normal/length.
    /// Intended for overlap diagnostics; does not modify the integration geometry.
    pub fn polygon(&self, i: usize) -> Result<Vec<Vec2>, String> {
        let cell = self.cells.get(i).ok_or("invalid polygon cell")?;
        let mut points: Vec<Vec2> = cell
            .faces
            .iter()
            .map(|&(f, sign)| {
                let face = &self.faces[f];
                let d = self.displacement(face, i);
                [
                    d[0] + 0.5 * sign * face.area * face.normal[1],
                    d[1] - 0.5 * sign * face.area * face.normal[0],
                ]
            })
            .collect();
        points.sort_by(|a, b| a[1].atan2(a[0]).total_cmp(&b[1].atan2(b[0])));
        let area = 0.5
            * (0..points.len())
                .map(|k| {
                    let a = points[k];
                    let b = points[(k + 1) % points.len()];
                    a[0] * b[1] - a[1] * b[0]
                })
                .sum::<f64>();
        if !area.is_finite() || (area / cell.volume - 1.).abs() > 1e-9 {
            return Err(format!("polygon area mismatch for cell {i}"));
        }
        for p in &mut points {
            for (value, centre) in p.iter_mut().zip(cell.centroid) {
                *value += centre;
            }
        }
        Ok(points)
    }

    /// Neighbour ID and centroid offset; same incidence precondition as displacement.
    pub fn neighbour(&self, face: &Face, cell: usize) -> (usize, Vec2) {
        let (j, sign) = if cell == face.left {
            (face.right, 1.0)
        } else {
            (face.left, -1.0)
        };
        let delta = std::array::from_fn(|k| {
            self.cells[j].centroid[k] - self.cells[cell].centroid[k]
                + sign * f64::from(face.image[k]) * self.lengths[k]
        });
        (j, delta)
    }

    pub fn validate(&self) -> Result<(), String> {
        let _timer = timing::scope("mesh/validate");
        let box_area = self.lengths[0] * self.lengths[1];
        if !self.lengths.iter().all(|l| l.is_finite() && *l > 0.0)
            || !box_area.is_finite()
            || box_area <= 0.0
            || self.cells.len() < 9
            || self.cells.len() != self.generators.len()
            || self
                .generators
                .iter()
                .any(|p| (0..2).any(|k| !p[k].is_finite() || p[k] < 0.0 || p[k] >= self.lengths[k]))
        {
            return Err("invalid box, generator coordinates or cell count".into());
        }
        let scale = self.lengths[0].max(self.lengths[1]);
        let mut face_keys = BTreeMap::new();
        for (f, face) in self.faces.iter().enumerate() {
            if face.left >= face.right
                || face.right >= self.cells.len()
                || face.image.iter().any(|s| !(-1..=1).contains(s))
                || !face.area.is_finite()
                || face.area <= 0.0
                || !face
                    .centroid
                    .iter()
                    .chain(&face.normal)
                    .all(|v| v.is_finite())
                || (dot(face.normal, face.normal) - 1.0).abs() > 1e-9
                || face_keys
                    .insert((face.left, face.right, face.image), f)
                    .is_some()
            {
                return Err(format!(
                    "face {f}: invalid geometry or duplicate connectivity"
                ));
            }
            let delta: Vec2 = std::array::from_fn(|k| {
                (self.generators[face.right][k] - self.generators[face.left][k]
                    + f64::from(face.image[k]) * self.lengths[k])
                    / scale
            });
            let distance = delta[0].hypot(delta[1]);
            let offset = std::array::from_fn(|k| {
                (face.centroid[k] - self.generators[face.left][k]) / scale - 0.5 * delta[k]
            });
            if !distance.is_finite()
                || distance <= 1e-11
                || (0..2).any(|k| (face.normal[k] - delta[k] / distance).abs() > 1e-9)
                || !dot(offset, face.normal).is_finite()
                || dot(offset, face.normal).abs() > 1e-9
            {
                return Err(format!("face {f}: generator-normal or bisector mismatch"));
            }
        }
        let mut incidences = vec![[false; 2]; self.faces.len()];
        let mut total_fraction = 0.0;
        for (i, c) in self.cells.iter().enumerate() {
            if !c.volume.is_finite()
                || c.volume <= 0.0
                || !c.centroid.iter().all(|v| v.is_finite())
                || c.faces.len() < 3
            {
                return Err(format!("cell {i}: invalid volume, centroid or face count"));
            }
            total_fraction += c.volume / box_area;
            let h = c.volume.sqrt();
            let mut closure = [0.0; 2];
            let mut perimeter = 0.0;
            let mut tensor = [[0.0; 2]; 2];
            let mut moment = [0.0; 2];
            for &(f, sign) in &c.faces {
                let face = self
                    .faces
                    .get(f)
                    .ok_or_else(|| format!("cell {i}: invalid face index"))?;
                let side = if i == face.left && sign == 1.0 {
                    0
                } else if i == face.right && sign == -1.0 {
                    1
                } else {
                    return Err(format!("cell {i}: invalid face incidence/sign"));
                };
                if incidences[f][side] {
                    return Err(format!("cell {i}: repeated face incidence"));
                }
                incidences[f][side] = true;
                let d = self.displacement(face, i).map(|v| v / h);
                let normal = face.normal.map(|x| sign * x);
                if !dot(d, normal).is_finite() || dot(d, normal) <= 0.0 {
                    return Err("face orientation or area failure".into());
                }
                let area = face.area / h;
                perimeter += area;
                for k in 0..2 {
                    closure[k] += area * normal[k];
                    moment[k] += area * dot(d, normal) * d[k] / 3.0;
                    for (l, n) in normal.iter().enumerate() {
                        tensor[k][l] += area * d[k] * n;
                    }
                }
            }
            if !perimeter.is_finite()
                || closure
                    .iter()
                    .any(|x| !x.is_finite() || x.abs() > 1e-9 * perimeter)
                || moment
                    .iter()
                    .any(|x| !x.is_finite() || x.abs() > 1e-9 * perimeter)
                || (0..2).any(|k| {
                    (0..2).any(|l| {
                        let expected = if k == l { 1.0 } else { 0.0 };
                        !tensor[k][l].is_finite() || (tensor[k][l] - expected).abs() > 1e-9
                    })
                })
            {
                return Err(format!(
                    "cell {i}: closure, volume tensor or centroid moment failure"
                ));
            }
        }
        if incidences.iter().any(|sides| *sides != [true, true]) {
            return Err("shared face lacks exactly one incidence on each side".into());
        }
        if !total_fraction.is_finite() || (total_fraction - 1.0).abs() > 1e-9 {
            return Err("Voronoi cells do not tile the periodic box".into());
        }
        Ok(())
    }

    /// Validate once and borrow this immutable mesh for multiple reconstructions.
    pub fn reconstruction(&self) -> Result<Reconstruction<'_>, String> {
        self.validate()?;
        Ok(Reconstruction { mesh: self })
    }
    /// Cell-anchored limiter. Multiple fields can share a reconstruction guard.
    pub fn limit_gradients(&self, values: &[f64], raw: &[Vec2]) -> Result<Vec<Vec2>, String> {
        self.reconstruction()?.limit_gradients(values, raw)
    }
}

/// A mesh whose invariants were checked when it was wrapped. The wrapper hands
/// out shared references only, so the check cannot go stale: reconstruction
/// guards are created from it without repeating the validation, which costs a
/// sorted map over all faces. Changing the mesh means unwrapping it and
/// validating the result again.
#[derive(Clone, Debug)]
pub struct ValidMesh(Mesh);
impl ValidMesh {
    pub fn new(mesh: Mesh) -> Result<Self, String> {
        mesh.validate()?;
        Ok(Self(mesh))
    }
    /// Same guard as `Mesh::reconstruction`, backed by the construction check.
    pub fn reconstruction(&self) -> Reconstruction<'_> {
        Reconstruction { mesh: &self.0 }
    }
    /// `Derivatives::build` without repeating the validation.
    pub fn derivatives(&self, at_faces: bool) -> Result<Derivatives, String> {
        Derivatives::build_checked(&self.0, at_faces)
    }
    /// `Derivatives::quadratic` without repeating the validation.
    pub fn quadratic_derivatives(&self) -> Result<Derivatives, String> {
        Derivatives::quadratic_checked(&self.0)
    }
    pub fn into_inner(self) -> Mesh {
        self.0
    }
}
impl std::ops::Deref for ValidMesh {
    type Target = Mesh;
    fn deref(&self) -> &Mesh {
        &self.0
    }
}

/// A checked, immutable mesh borrow. Public Mesh fields cannot be mutated while
/// this guard exists; state-dependent extrema are still recomputed on every call.
pub struct Reconstruction<'a> {
    mesh: &'a Mesh,
}
impl Reconstruction<'_> {
    /// One common factor bounds the complete quadratic face increment.
    pub fn quadratic_factors(
        &self,
        values: &[f64],
        gradient: &[Vec2],
        hessian: &[[f64; 3]],
    ) -> Result<Vec<f64>, String> {
        let n = self.mesh.cells.len();
        if values.len() != n
            || gradient.len() != n
            || hessian.len() != n
            || !values
                .iter()
                .chain(gradient.iter().flatten())
                .chain(hessian.iter().flatten())
                .all(|v| v.is_finite())
        {
            return Err("invalid quadratic limiter inputs".into());
        }
        self.mesh
            .cells
            .iter()
            .enumerate()
            .map(|(i, c)| {
                let mut low = values[i];
                let mut high = values[i];
                for &(f, _) in &c.faces {
                    let (j, _) = self.mesh.neighbour(&self.mesh.faces[f], i);
                    low = low.min(values[j]);
                    high = high.max(values[j]);
                }
                let mut factor: f64 = 1.;
                for &(f, _) in &c.faces {
                    let d = self.mesh.displacement(&self.mesh.faces[f], i);
                    let change = dot(gradient[i], d) + quadratic_jet::term(hessian[i], d);
                    if !change.is_finite()
                        || !(high - values[i]).is_finite()
                        || !(low - values[i]).is_finite()
                    {
                        return Err("quadratic limiter overflow".into());
                    }
                    if change > 0. {
                        factor = factor.min((high - values[i]) / change);
                    }
                    if change < 0. {
                        factor = factor.min((low - values[i]) / change);
                    }
                }
                Ok(factor.clamp(0., 1.))
            })
            .collect()
    }

    pub fn limit_gradients(&self, values: &[f64], raw: &[Vec2]) -> Result<Vec<Vec2>, String> {
        let _timer = timing::scope("limiter/neighbour-extrema");
        if values.len() != self.mesh.cells.len()
            || raw.len() != self.mesh.cells.len()
            || !values
                .iter()
                .chain(raw.iter().flatten())
                .all(|v| v.is_finite())
        {
            return Err(
                "limiter requires finite cell values and gradients of matching length".into(),
            );
        }
        parallel::try_map(self.mesh.cells.len(), |i| {
            let c = &self.mesh.cells[i];
            let mut low = values[i];
            let mut high = values[i];
            for &(f, _) in &c.faces {
                let (j, _) = self.mesh.neighbour(&self.mesh.faces[f], i);
                low = low.min(values[j]);
                high = high.max(values[j]);
            }
            let mut factor: f64 = 1.0;
            for &(f, _) in &c.faces {
                let change = dot(raw[i], self.mesh.displacement(&self.mesh.faces[f], i));
                if !change.is_finite()
                    || !(high - values[i]).is_finite()
                    || !(low - values[i]).is_finite()
                {
                    return Err(format!("cell {i}: limiter arithmetic overflow"));
                }
                if change > 0.0 {
                    factor = factor.min((high - values[i]) / change);
                }
                if change < 0.0 {
                    factor = factor.min((low - values[i]) / change);
                }
            }
            Ok(raw[i].map(|x| x * factor.clamp(0.0, 1.0)))
        })
    }

    /// Opt-in engineering variant of `limit_gradients`; see
    /// docs/M1_STANDING_WAVE_PLAN.md. The neighbour-extrema bounds are widened
    /// by a curvature that two cells confirm independently. For neighbours
    /// i, j with centroid offset d, `q_j-q_i-G_i.d` and `G_j.d-(q_j-q_i)` both
    /// equal `d^T H d/2` for a quadratic. Equal signs admit the smaller
    /// magnitude on that side only; otherwise the bounds are unchanged.
    /// `raw` must hold the unlimited gradients of all cells. Not TVD: a
    /// curvature-confirmed extremum, including a two-cell one, is retained.
    pub fn limit_gradients_smooth_extrema(
        &self,
        values: &[f64],
        raw: &[Vec2],
    ) -> Result<Vec<Vec2>, String> {
        let _timer = timing::scope("limiter/smooth-extrema");
        if values.len() != self.mesh.cells.len()
            || raw.len() != self.mesh.cells.len()
            || !values
                .iter()
                .chain(raw.iter().flatten())
                .all(|v| v.is_finite())
        {
            return Err(
                "limiter requires finite cell values and gradients of matching length".into(),
            );
        }
        parallel::try_map(self.mesh.cells.len(), |i| {
            let c = &self.mesh.cells[i];
            let mut low = values[i];
            let mut high = values[i];
            let mut concave: f64 = 0.0;
            let mut convex: f64 = 0.0;
            for &(f, _) in &c.faces {
                let (j, d) = self.mesh.neighbour(&self.mesh.faces[f], i);
                low = low.min(values[j]);
                high = high.max(values[j]);
                let jump = values[j] - values[i];
                let here = jump - dot(raw[i], d);
                let there = dot(raw[j], d) - jump;
                if !here.is_finite() || !there.is_finite() {
                    return Err(format!("cell {i}: limiter arithmetic overflow"));
                }
                if here < 0.0 && there < 0.0 {
                    concave = concave.max((-here).min(-there));
                } else if here > 0.0 && there > 0.0 {
                    convex = convex.max(here.min(there));
                }
            }
            let upper = high - values[i] + concave;
            let lower = low - values[i] - convex;
            let mut factor: f64 = 1.0;
            for &(f, _) in &c.faces {
                let change = dot(raw[i], self.mesh.displacement(&self.mesh.faces[f], i));
                if !change.is_finite() || !upper.is_finite() || !lower.is_finite() {
                    return Err(format!("cell {i}: limiter arithmetic overflow"));
                }
                if change > 0.0 {
                    factor = factor.min(upper / change);
                }
                if change < 0.0 {
                    factor = factor.min(lower / change);
                }
            }
            Ok(raw[i].map(|x| x * factor.clamp(0.0, 1.0)))
        })
    }
}

impl Reconstruction<'_> {
    /// `limit_gradients` of all N components in one parallel pass. For each
    /// component and cell the bounds, the factor and every comparison are
    /// those of `limit_gradients`; the faces are walked once for all
    /// components. `None` where `limit_gradients` of some component would
    /// return an error: the caller then takes the scalar path and its error.
    pub fn limit_all<const N: usize>(
        &self,
        values: &[[f64; N]],
        raw: &[[Vec2; N]],
    ) -> Option<Vec<[Vec2; N]>> {
        let _timer = timing::scope("limiter/neighbour-extrema/all");
        let cells = self.mesh.cells.len();
        if values.len() != cells
            || raw.len() != cells
            || !values
                .iter()
                .flatten()
                .chain(raw.iter().flatten().flatten())
                .all(|v| v.is_finite())
        {
            return None;
        }
        parallel::map(cells, |i| {
            let c = &self.mesh.cells[i];
            let mut low = values[i];
            let mut high = values[i];
            for &(f, _) in &c.faces {
                let (j, _) = self.mesh.neighbour(&self.mesh.faces[f], i);
                for k in 0..N {
                    low[k] = low[k].min(values[j][k]);
                    high[k] = high[k].max(values[j][k]);
                }
            }
            let mut factor = [1.0_f64; N];
            for &(f, _) in &c.faces {
                let d = self.mesh.displacement(&self.mesh.faces[f], i);
                for k in 0..N {
                    let change = dot(raw[i][k], d);
                    let (up, down) = (high[k] - values[i][k], low[k] - values[i][k]);
                    if !change.is_finite() || !up.is_finite() || !down.is_finite() {
                        return None;
                    }
                    if change > 0.0 {
                        factor[k] = factor[k].min(up / change);
                    }
                    if change < 0.0 {
                        factor[k] = factor[k].min(down / change);
                    }
                }
            }
            Some(std::array::from_fn(|k| {
                raw[i][k].map(|x| x * factor[k].clamp(0.0, 1.0))
            }))
        })
        .into_iter()
        .collect()
    }

    /// `limit_gradients_smooth_extrema` of all N components in one parallel
    /// pass, like `limit_all`. `None` where the scalar limiter would fail.
    pub fn limit_smooth_extrema_all<const N: usize>(
        &self,
        values: &[[f64; N]],
        raw: &[[Vec2; N]],
    ) -> Option<Vec<[Vec2; N]>> {
        let _timer = timing::scope("limiter/smooth-extrema/all");
        let cells = self.mesh.cells.len();
        if values.len() != cells
            || raw.len() != cells
            || !values
                .iter()
                .flatten()
                .chain(raw.iter().flatten().flatten())
                .all(|v| v.is_finite())
        {
            return None;
        }
        parallel::map(cells, |i| {
            let c = &self.mesh.cells[i];
            let mut low = values[i];
            let mut high = values[i];
            let mut concave = [0.0_f64; N];
            let mut convex = [0.0_f64; N];
            for &(f, _) in &c.faces {
                let (j, d) = self.mesh.neighbour(&self.mesh.faces[f], i);
                for k in 0..N {
                    low[k] = low[k].min(values[j][k]);
                    high[k] = high[k].max(values[j][k]);
                    let jump = values[j][k] - values[i][k];
                    let here = jump - dot(raw[i][k], d);
                    let there = dot(raw[j][k], d) - jump;
                    if !here.is_finite() || !there.is_finite() {
                        return None;
                    }
                    if here < 0.0 && there < 0.0 {
                        concave[k] = concave[k].max((-here).min(-there));
                    } else if here > 0.0 && there > 0.0 {
                        convex[k] = convex[k].max(here.min(there));
                    }
                }
            }
            let upper: [f64; N] = std::array::from_fn(|k| high[k] - values[i][k] + concave[k]);
            let lower: [f64; N] = std::array::from_fn(|k| low[k] - values[i][k] - convex[k]);
            let mut factor = [1.0_f64; N];
            for &(f, _) in &c.faces {
                let d = self.mesh.displacement(&self.mesh.faces[f], i);
                for k in 0..N {
                    let change = dot(raw[i][k], d);
                    if !change.is_finite() || !upper[k].is_finite() || !lower[k].is_finite() {
                        return None;
                    }
                    if change > 0.0 {
                        factor[k] = factor[k].min(upper[k] / change);
                    }
                    if change < 0.0 {
                        factor[k] = factor[k].min(lower[k] / change);
                    }
                }
            }
            Some(std::array::from_fn(|k| {
                raw[i][k].map(|x| x * factor[k].clamp(0.0, 1.0))
            }))
        })
        .into_iter()
        .collect()
    }
}

#[derive(Clone, Copy, Debug)]
pub struct DerivativeSample {
    pub index: usize,
    pub weight: Vec2,
}

/// Face-area-weighted, free-intercept fits; the centre is NOT an observation.
#[derive(Clone, Debug)]
pub struct Derivatives {
    pub samples: Vec<Vec<DerivativeSample>>,
    pub worst_condition: f64,
    input_len: usize,
}

impl Derivatives {
    pub fn build(mesh: &Mesh, at_faces: bool) -> Result<Self, String> {
        mesh.validate()?;
        Self::build_checked(mesh, at_faces)
    }

    /// The mesh must already be validated.
    fn build_checked(mesh: &Mesh, at_faces: bool) -> Result<Self, String> {
        let _timer = timing::scope("derivatives/build");
        let mut samples: Vec<Vec<DerivativeSample>> = Vec::with_capacity(mesh.cells.len());
        let mut worst_condition: f64 = 0.0;
        for (i, cell) in mesh.cells.iter().enumerate() {
            let h = cell.volume.sqrt();
            let total_weight: f64 = cell.faces.iter().map(|(f, _)| mesh.faces[*f].area).sum();
            let data: Vec<_> = cell
                .faces
                .iter()
                .map(|(f, _)| {
                    let face = &mesh.faces[*f];
                    let (index, d) = if at_faces {
                        (*f, mesh.displacement(face, i))
                    } else {
                        mesh.neighbour(face, i)
                    };
                    (index, d.map(|x| x / h), face.area / total_weight)
                })
                .collect();
            let (stencil, condition) =
                fit_derivatives(&data, h).map_err(|e| format!("cell {i}: {e}"))?;
            worst_condition = worst_condition.max(condition);
            samples.push(stencil);
        }
        Ok(Self {
            samples,
            worst_condition,
            input_len: if at_faces {
                mesh.faces.len()
            } else {
                mesh.cells.len()
            },
        })
    }

    /// Number of values `gradient` expects: cells or faces, by construction mode.
    pub fn input_len(&self) -> usize {
        self.input_len
    }

    /// `gradient` of all N components in one parallel pass. For each
    /// component and cell the baseline and the sums are those of `gradient`.
    /// `None` where `gradient` of some component would return an error: the
    /// caller then takes the scalar path and its error.
    pub fn gradients<const N: usize>(&self, values: &[[f64; N]]) -> Option<Vec<[Vec2; N]>> {
        let _timer = timing::scope("derivatives/gradients");
        if values.len() != self.input_len || !values.iter().flatten().all(|v| v.is_finite()) {
            return None;
        }
        parallel::map(self.samples.len(), |i| {
            let samples = &self.samples[i];
            if samples.is_empty() || samples.iter().any(|s| s.index >= values.len()) {
                return None;
            }
            let base = values[samples[0].index];
            let mut result = [[0.0; 2]; N];
            for k in 0..N {
                let baseline = base[k];
                let gradient: Vec2 = std::array::from_fn(|c| {
                    samples
                        .iter()
                        .map(|s| s.weight[c] * (values[s.index][k] - baseline))
                        .sum()
                });
                if !gradient.iter().all(|v| v.is_finite()) {
                    return None;
                }
                result[k] = gradient;
            }
            Some(result)
        })
        .into_iter()
        .collect()
    }

    /// Values are indexed by cells or faces according to the construction mode.
    pub fn gradient(&self, values: &[f64]) -> Result<Vec<Vec2>, String> {
        let _timer = timing::scope("derivatives/gradient");
        if values.len() != self.input_len || !values.iter().all(|v| v.is_finite()) {
            return Err("gradient requires finite values of the stencil's input length".into());
        }
        parallel::try_map(self.samples.len(), |i| {
            let samples = &self.samples[i];
            if samples.is_empty() || samples.iter().any(|s| s.index >= values.len()) {
                return Err("invalid derivative sample index or empty stencil".into());
            }
            // Any constant baseline has zero derivative; use an actual sample
            // in both modes, never interpret a cell ID as a face-value index.
            let baseline = values[samples[0].index];
            let gradient: Vec2 = std::array::from_fn(|k| {
                samples
                    .iter()
                    .map(|s| s.weight[k] * (values[s.index] - baseline))
                    .sum()
            });
            if !gradient.iter().all(|v| v.is_finite()) {
                return Err("gradient arithmetic overflow or invalid coefficients".into());
            }
            Ok(gradient)
        })
    }
}

// Coordinates are divided by h and positive weights sum to one.
fn fit_derivatives(
    data: &[(usize, Vec2, f64)],
    h: f64,
) -> Result<(Vec<DerivativeSample>, f64), String> {
    let mean: Vec2 = std::array::from_fn(|k| data.iter().map(|(_, d, w)| w * d[k]).sum());
    let mut cov = [0.0; 3];
    for (_, d, w) in data {
        let x = d[0] - mean[0];
        let y = d[1] - mean[1];
        cov[0] += w * x * x;
        cov[1] += w * x * y;
        cov[2] += w * y * y;
    }
    let det = cov[0] * cov[2] - cov[1] * cov[1];
    let trace = cov[0] + cov[2];
    if !det.is_finite() || det <= 1e-10 * trace * trace {
        return Err("rank-deficient/ill-conditioned derivative stencil".into());
    }
    let samples: Vec<_> = data
        .iter()
        .map(|(index, d, w)| DerivativeSample {
            index: *index,
            weight: [
                w * (cov[2] * (d[0] - mean[0]) - cov[1] * (d[1] - mean[1])) / (det * h),
                w * (cov[0] * (d[1] - mean[1]) - cov[1] * (d[0] - mean[0])) / (det * h),
            ],
        })
        .collect();
    if samples
        .iter()
        .any(|s| !s.weight.iter().all(|w| w.is_finite()))
    {
        return Err("unrepresentable derivative coefficients".into());
    }
    Ok((samples, trace * trace / det))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn incremental_polygon_repeats_the_reference_clip_bit_for_bit() {
        // Deterministic pseudo-random planes: far ones (no change), ones inside
        // the enclosing circle that miss the polygon (same polygon, next start
        // vertex) and ones that cut it. All three must occur and agree exactly.
        let mut state = 0x2545_F491_4F6C_DD1D_u64;
        let mut uniform = || {
            state = state
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            (state >> 11) as f64 / (1u64 << 53) as f64
        };
        let square = || {
            vec![
                Vertex {
                    point: [-0.5, -0.5],
                    incoming: (0, -1, 0),
                },
                Vertex {
                    point: [0.5, -0.5],
                    incoming: (0, 0, -1),
                },
                Vertex {
                    point: [0.5, 0.5],
                    incoming: (0, 1, 0),
                },
                Vertex {
                    point: [-0.5, 0.5],
                    incoming: (0, 0, 1),
                },
            ]
        };
        let same = |a: &[Vertex], b: &[Vertex]| {
            a.len() == b.len()
                && a.iter().zip(b).all(|(x, y)| {
                    x.point.map(f64::to_bits) == y.point.map(f64::to_bits)
                        && x.incoming == y.incoming
                })
        };
        // The radius as the reference computes it, from the vertices in order.
        let radius2 = |polygon: &[Vertex]| {
            polygon
                .iter()
                .map(|v| dot(v.point, v.point))
                .fold(0.0, f64::max)
        };
        let mut kinds = [0usize; 3];
        for trial in 0..200 {
            let mut reference = square();
            let mut fast = Polygon::new(square());
            for plane in 0..60 {
                let scale = [3.0, 1.2, 0.6, 0.2][(plane + trial) % 4];
                let delta = [
                    scale * (2.0 * uniform() - 1.0),
                    scale * (2.0 * uniform() - 1.0),
                ];
                if dot(delta, delta) < 1e-6 {
                    continue;
                }
                let before = reference.clone();
                reference = clip(&reference, delta, (plane + 1, 0, 0));
                fast.clip(delta, (plane + 1, 0, 0));
                assert!(
                    same(&fast.vertices, &reference),
                    "trial {trial} plane {plane}"
                );
                assert_eq!(fast.radius2.to_bits(), radius2(&reference).to_bits());
                let mut rotated = before.clone();
                rotated.rotate_left(1);
                kinds[if same(&reference, &before) {
                    0
                } else if same(&reference, &rotated) {
                    1
                } else {
                    2
                }] += 1;
            }
            assert!(reference.len() >= 3);
        }
        assert!(kinds.iter().all(|count| *count > 0), "{kinds:?}");
        // One explicit plane of each kind on the unit square (radius^2 = 0.5).
        for (delta, kind) in [([3.0, 0.0], 0), ([1.2, 0.0], 1), ([0.6, 0.0], 2)] {
            let reference = clip(&square(), delta, (9, 0, 0));
            let mut fast = Polygon::new(square());
            fast.clip(delta, (9, 0, 0));
            assert!(same(&fast.vertices, &reference));
            let mut rotated = square();
            rotated.rotate_left(1);
            let expected = [
                same(&reference, &square()),
                same(&reference, &rotated),
                reference.len() == 4 && reference.iter().any(|v| v.incoming == (9, 0, 0)),
            ];
            assert!(expected[kind], "plane {delta:?} should be of kind {kind}");
        }
        // A polygon that has lost every vertex stays empty, as in the reference.
        let mut empty = Polygon::new(Vec::new());
        empty.clip([0.1, 0.0], (1, 0, 0));
        assert!(empty.vertices.is_empty() && clip(&[], [0.1, 0.0], (1, 0, 0)).is_empty());

        // Many vertices, as while a build works inwards from far generators:
        // planes tangent to one circle leave a vertex each, and later planes
        // keep long runs of them. A star is not convex, so one plane crosses
        // it several times.
        let star = || -> Vec<Vertex> {
            (0..40)
                .map(|k| {
                    let angle = std::f64::consts::TAU * k as f64 / 40.0;
                    let radius = if k % 2 == 0 { 1.0 } else { 0.45 };
                    Vertex {
                        point: [radius * angle.cos(), radius * angle.sin()],
                        incoming: (k, 0, 1),
                    }
                })
                .collect()
        };
        let (mut largest, mut crossings) = (0, 0);
        for trial in 0..60 {
            let convex = trial % 2 == 0;
            let mut reference = if convex { square() } else { star() };
            let mut fast = Polygon::new(reference.clone());
            for plane in 0..120 {
                let angle = std::f64::consts::TAU * uniform();
                let length = if convex && plane < 60 {
                    0.9
                } else {
                    [0.9, 1.3, 0.7, 2.4][plane % 4] * (0.6 + 0.8 * uniform())
                };
                let delta = [length * angle.cos(), length * angle.sin()];
                let before = reference.len();
                reference = clip(&reference, delta, (plane + 1, 1, -1));
                fast.clip(delta, (plane + 1, 1, -1));
                assert!(
                    same(&fast.vertices, &reference),
                    "trial {trial} plane {plane}"
                );
                assert_eq!(fast.radius2.to_bits(), radius2(&reference).to_bits());
                assert_eq!(fast.norm2.len(), reference.len());
                largest = largest.max(reference.len());
                // Each crossing pair adds one vertex more than it removes at most.
                crossings += usize::from(reference.len() > before + 1);
            }
        }
        assert!(largest >= 30, "{largest}");
        assert!(crossings > 0);
    }

    /// Deterministic fields with smooth parts, extrema, exact ties and noise.
    fn fused_field<const N: usize>(mesh: &Mesh, seed: u64) -> Vec<[f64; N]> {
        let mut state = 0x9e37_79b9_7f4a_7c15_u64 ^ seed;
        mesh.cells
            .iter()
            .map(|c| {
                std::array::from_fn(|k| {
                    state = state
                        .wrapping_mul(6_364_136_223_846_793_005)
                        .wrapping_add(1_442_695_040_888_963_407);
                    let unit = (state >> 11) as f64 / (1u64 << 53) as f64 - 0.5;
                    let smooth = (std::f64::consts::TAU * (c.centroid[0] + 0.3 * k as f64)).sin()
                        * (2.0 * std::f64::consts::TAU * c.centroid[1]).cos();
                    match (state >> 7) % 6 {
                        0 => 0.5,
                        1 => smooth,
                        _ => smooth + 0.1 * unit,
                    }
                })
            })
            .collect()
    }

    #[test]
    fn fused_gradients_and_limiters_repeat_the_scalar_ones_bit_for_bit() {
        let bits = |v: &[Vec2]| v.iter().map(|g| g.map(f64::to_bits)).collect::<Vec<_>>();
        let component = |v: &[[Vec2; 5]], k: usize| v.iter().map(|g| g[k]).collect::<Vec<_>>();
        let (mut limited_cells, mut smooth_cells) = (0, 0);
        for (nx, ny, lengths, jitter) in [
            (8, 8, [1.0; 2], 0.0),
            (8, 8, [1.0; 2], 0.15),
            (16, 4, [2.0, 0.125], 0.15),
            (12, 10, [1.0, 0.8], 0.25),
        ] {
            let mesh = Mesh::lattice(nx, ny, lengths, jitter).unwrap();
            let guard = mesh.reconstruction().unwrap();
            for stencil in [
                Derivatives::build(&mesh, false).unwrap(),
                Derivatives::quadratic(&mesh).unwrap(),
            ] {
                for seed in 0..3 {
                    let values: Vec<[f64; 5]> = fused_field(&mesh, seed);
                    for threads in [1, 3] {
                        let (raw, limited, smooth) = parallel::with_threads(threads, || {
                            let raw = stencil.gradients(&values).unwrap();
                            let limited = guard.limit_all(&values, &raw).unwrap();
                            let smooth = guard.limit_smooth_extrema_all(&values, &raw).unwrap();
                            (raw, limited, smooth)
                        })
                        .unwrap();
                        for k in 0..5 {
                            let scalar: Vec<f64> = values.iter().map(|v| v[k]).collect();
                            let expected = stencil.gradient(&scalar).unwrap();
                            assert_eq!(bits(&component(&raw, k)), bits(&expected));
                            let clipped = guard.limit_gradients(&scalar, &expected).unwrap();
                            assert_eq!(bits(&component(&limited, k)), bits(&clipped));
                            let relaxed = guard
                                .limit_gradients_smooth_extrema(&scalar, &expected)
                                .unwrap();
                            assert_eq!(bits(&component(&smooth, k)), bits(&relaxed));
                            limited_cells += clipped
                                .iter()
                                .zip(&expected)
                                .filter(|(a, b)| a != b)
                                .count();
                            smooth_cells +=
                                relaxed.iter().zip(&clipped).filter(|(a, b)| a != b).count();
                        }
                    }
                }
            }
        }
        // Both limiters act, and the curvature-confirmed one differs somewhere.
        assert!(limited_cells > 0 && smooth_cells > 0);
    }

    #[test]
    fn fused_passes_decline_exactly_where_a_scalar_component_fails() {
        let mesh = Mesh::lattice(8, 8, [1.0; 2], 0.15).unwrap();
        let guard = mesh.reconstruction().unwrap();
        let stencil = Derivatives::quadratic(&mesh).unwrap();
        let values: Vec<[f64; 3]> = fused_field(&mesh, 9);
        let raw = stencil.gradients(&values).unwrap();
        // Values: a non-finite entry, values that overflow the sums, a wrong length.
        let mut nan = values.clone();
        nan[17][2] = f64::NAN;
        let huge: Vec<[f64; 3]> = (0..64)
            .map(|i| [0.0, if i % 2 == 0 { 1.7e308 } else { -1.7e308 }, 0.0])
            .collect();
        for bad in [&nan, &huge, &values[..63].to_vec()] {
            assert!(stencil.gradients(bad).is_none());
            assert!((0..3).any(|k| {
                stencil
                    .gradient(&bad.iter().map(|v| v[k]).collect::<Vec<_>>())
                    .is_err()
            }));
        }
        // A face-indexed stencil does not take cell values.
        let faces = Derivatives::build(&mesh, true).unwrap();
        assert!(faces.gradients(&values).is_none());
        assert!(faces.gradient(&vec![0.0; 64]).is_err());
        // Limiters: a non-finite gradient, and neighbouring values of opposite
        // sign whose bounds `high - value` overflow (the changes cannot: the
        // displacements are about 0.06 here).
        let mut infinite = raw.clone();
        infinite[5][1] = [f64::INFINITY, 0.0];
        for (values, raw) in [(&values, &infinite), (&huge, &raw)] {
            assert!(guard.limit_all(values, raw).is_none());
            assert!(guard.limit_smooth_extrema_all(values, raw).is_none());
            let scalar: Vec<f64> = values.iter().map(|v| v[1]).collect();
            let component: Vec<Vec2> = raw.iter().map(|g| g[1]).collect();
            assert!(guard.limit_gradients(&scalar, &component).is_err());
            assert!(
                guard
                    .limit_gradients_smooth_extrema(&scalar, &component)
                    .is_err()
            );
        }
        assert!(guard.limit_all(&values[..63], &raw[..63]).is_none());
    }

    #[test]
    fn collinear_and_nearly_collinear_samples_fail_conditioning_gate() {
        for eps in [0.0, 1e-6] {
            let data = [
                (0, [-1.0, -eps], 0.25),
                (1, [1.0, -eps], 0.25),
                (2, [1.0, eps], 0.25),
                (3, [-1.0, eps], 0.25),
            ];
            assert!(
                fit_derivatives(&data, 1.0)
                    .unwrap_err()
                    .contains("ill-conditioned")
            );
        }
        let data = [
            (0, [-1.0, -1.0], 0.25),
            (1, [1.0, -1.0], 0.25),
            (2, [1.0, 1.0], 0.25),
            (3, [-1.0, 1.0], 0.25),
        ];
        let (samples, condition) = fit_derivatives(&data, 1.0).unwrap();
        assert_eq!(condition, 4.0);
        let g: Vec2 = std::array::from_fn(|k| {
            samples
                .iter()
                .map(|s| s.weight[k] * (2.0 * data[s.index].1[0] - 3.0 * data[s.index].1[1]))
                .sum()
        });
        assert_eq!(g, [2.0, -3.0]);
    }

    #[test]
    fn column_lattice_keeps_transverse_symmetry_that_planar_jitter_breaks() {
        let lengths = [2.0, 0.125];
        let kink = |mesh: &Mesh| -> f64 {
            // Periodic x-only sample with slope changes at x=1 and the seam.
            let values: Vec<f64> = mesh
                .cells
                .iter()
                .map(|c| (c.centroid[0] - 1.0).abs())
                .collect();
            Derivatives::build(mesh, false)
                .unwrap()
                .gradient(&values)
                .unwrap()
                .iter()
                .fold(0.0, |m, g| m.max(g[1].abs()))
        };
        let columns = Mesh::lattice_columns(32, 4, lengths, 0.15).unwrap();
        columns.validate().unwrap();
        assert!(
            columns
                .faces
                .iter()
                .all(|f| (f.normal[0] * f.normal[1]).abs() < 1e-12)
        );
        let widths: Vec<f64> = columns.cells[..32].iter().map(|c| c.volume).collect();
        let spread = widths.iter().fold(0.0_f64, |m, v| m.max(*v))
            / widths.iter().fold(f64::INFINITY, |m, v| m.min(*v));
        assert!(spread > 1.2, "columns must be genuinely nonuniform");
        assert!(kink(&columns) < 1e-12);
        // The registered planar jitter invents a transverse slope from the
        // very same x-only samples; this is the #21 representation conflict.
        assert!(kink(&Mesh::lattice(32, 4, lengths, 0.15).unwrap()) > 1e-2);
        assert_eq!(
            Mesh::lattice_columns(8, 4, lengths, 0.).unwrap().generators,
            Mesh::lattice(8, 4, lengths, 0.).unwrap().generators
        );
        assert!(Mesh::lattice_columns(8, 4, lengths, 0.3).is_err());
    }
}
