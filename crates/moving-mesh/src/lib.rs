//! Small periodic 2D Voronoi reference: independent half-plane clipping in f64.
//! All 3x3 image planes remain eligible; ordered bounding-tree pruning skips only
//! the existing circle-test no-ops. An all-pairs comparator is retained. Serial, no FFI.

use std::collections::BTreeMap;

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
    fn one(&self, j: usize, polygon: &mut Vec<Vertex>) -> Result<(), String> {
        if self.i == j {
            return Ok(());
        }
        let [lx, ly] = self.lengths;
        let base = sub(self.points[j], self.points[self.i]);
        let nearest = [
            -(base[0] / lx).round() as i32,
            -(base[1] / ly).round() as i32,
        ];
        for sx in -1..=1 {
            for sy in -1..=1 {
                if (self.pass == 0) != ([sx, sy] == nearest) {
                    continue;
                }
                let delta = [base[0] + f64::from(sx) * lx, base[1] + f64::from(sy) * ly];
                if dot(delta, delta) < 1e-22 * self.scale * self.scale {
                    return Err(format!(
                        "duplicate or nearly coincident periodic generators {},{j}",
                        self.i
                    ));
                }
                *polygon = clip(polygon, delta, (j, sx, sy));
            }
        }
        Ok(())
    }
    fn visit(&self, node: &RangeTree, polygon: &mut Vec<Vertex>) -> Result<(), String> {
        let radius2 = polygon
            .iter()
            .map(|v| dot(v.point, v.point))
            .fold(0., f64::max);
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
        let mut cells = Vec::with_capacity(generators.len());
        let mut edges = BTreeMap::new();
        for (i, ri) in generators.iter().enumerate() {
            let [lx, ly] = lengths;
            let mut polygon = vec![
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
            ];
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
            cells.push(Cell {
                volume: 0.5 * twice_area,
                centroid: [
                    ri[0] + first_moment[0] / (3.0 * twice_area),
                    ri[1] + first_moment[1] / (3.0 * twice_area),
                ],
                faces: Vec::new(),
            });
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

/// A checked, immutable mesh borrow. Public Mesh fields cannot be mutated while
/// this guard exists; state-dependent extrema are still recomputed on every call.
pub struct Reconstruction<'a> {
    mesh: &'a Mesh,
}
impl Reconstruction<'_> {
    pub fn limit_gradients(&self, values: &[f64], raw: &[Vec2]) -> Result<Vec<Vec2>, String> {
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

    /// Values are indexed by cells or faces according to the construction mode.
    pub fn gradient(&self, values: &[f64]) -> Result<Vec<Vec2>, String> {
        if values.len() != self.input_len || !values.iter().all(|v| v.is_finite()) {
            return Err("gradient requires finite values of the stencil's input length".into());
        }
        self.samples
            .iter()
            .map(|samples| {
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
            .collect()
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
}
