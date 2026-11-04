//! Small periodic 2D Voronoi reference: independent half-plane clipping in f64.
//! All generator images in a 3x3 tiling are considered. O(N^2), serial, no FFI.

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

    pub fn build(mut generators: Vec<Vec2>, lengths: Vec2) -> Result<Self, String> {
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
            // Process nearest images first: quickly shrink the clipping polygon.
            for pass in 0..2 {
                for (j, rj) in generators.iter().enumerate() {
                    let base = sub(*rj, *ri);
                    let nearest = [
                        -(base[0] / lx).round() as i32,
                        -(base[1] / ly).round() as i32,
                    ];
                    for sx in -1..=1 {
                        for sy in -1..=1 {
                            if i == j {
                                continue;
                            }
                            let is_nearest = [sx, sy] == nearest;
                            if (pass == 0) != is_nearest {
                                continue;
                            }
                            let delta =
                                [base[0] + f64::from(sx) * lx, base[1] + f64::from(sy) * ly];
                            if dot(delta, delta) < 1e-22 * scale * scale {
                                return Err(format!(
                                    "duplicate or nearly coincident periodic generators {i},{j}"
                                ));
                            }
                            polygon = clip(&polygon, delta, (j, sx, sy));
                        }
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
        let total: f64 = self.cells.iter().map(|c| c.volume).sum();
        if (total - self.lengths[0] * self.lengths[1]).abs()
            > 1e-9 * self.lengths[0] * self.lengths[1]
        {
            return Err("Voronoi cells do not tile the periodic box".into());
        }
        for (i, c) in self.cells.iter().enumerate() {
            let mut closure = [0.0; 2];
            let mut area_identity = 0.0;
            for &(f, sign) in &c.faces {
                let face = &self.faces[f];
                let d = self.displacement(face, i);
                let normal = face.normal.map(|x| sign * x);
                if dot(d, normal) <= 0.0 || face.area <= 0.0 {
                    return Err("face orientation or area failure".into());
                }
                for k in 0..2 {
                    closure[k] += face.area * normal[k];
                }
                area_identity += 0.5 * face.area * dot(d, normal);
            }
            let scale = self.lengths[0].max(self.lengths[1]);
            if closure.iter().any(|x| x.abs() > 1e-9 * scale)
                || (area_identity - c.volume).abs() > 1e-9 * c.volume
            {
                return Err(format!("cell {i}: face closure/area identity failure"));
            }
        }
        Ok(())
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
}

impl Derivatives {
    pub fn build(mesh: &Mesh, at_faces: bool) -> Result<Self, String> {
        let mut samples = Vec::with_capacity(mesh.cells.len());
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
            let mean: Vec2 = std::array::from_fn(|k| data.iter().map(|(_, d, w)| w * d[k]).sum());
            let mut cov = [0.0; 3];
            for (_, d, w) in &data {
                let x = d[0] - mean[0];
                let y = d[1] - mean[1];
                cov[0] += w * x * x;
                cov[1] += w * x * y;
                cov[2] += w * y * y;
            }
            let det = cov[0] * cov[2] - cov[1] * cov[1];
            let trace = cov[0] + cov[2];
            if !det.is_finite() || det <= 1e-10 * trace * trace {
                return Err(format!(
                    "rank-deficient/ill-conditioned derivative stencil in cell {i}"
                ));
            }
            let condition = trace * trace / det;
            worst_condition = worst_condition.max(condition);
            samples.push(
                data.iter()
                    .map(|(index, d, w)| DerivativeSample {
                        index: *index,
                        weight: [
                            w * (cov[2] * (d[0] - mean[0]) - cov[1] * (d[1] - mean[1])) / (det * h),
                            w * (cov[0] * (d[1] - mean[1]) - cov[1] * (d[0] - mean[0])) / (det * h),
                        ],
                    })
                    .collect(),
            );
        }
        Ok(Self {
            samples,
            worst_condition,
        })
    }

    pub fn gradient(&self, values: &[f64]) -> Vec<Vec2> {
        self.samples
            .iter()
            .enumerate()
            .map(|(i, samples)| {
                let baseline = values[i];
                std::array::from_fn(|k| {
                    samples
                        .iter()
                        .map(|s| s.weight[k] * (values[s.index] - baseline))
                        .sum()
                })
            })
            .collect()
    }
}
