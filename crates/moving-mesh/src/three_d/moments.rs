use super::clip::{Plane, Polygon};
use super::exact::D;
use super::{GeometryError3, Tensor3, Vec3};

pub(crate) fn add(a: Vec3, b: Vec3) -> Vec3 {
    std::array::from_fn(|k| a[k] + b[k])
}
pub(crate) fn sub(a: Vec3, b: Vec3) -> Vec3 {
    std::array::from_fn(|k| a[k] - b[k])
}
pub(crate) fn scale(a: Vec3, b: f64) -> Vec3 {
    a.map(|v| v * b)
}
pub(crate) fn dot(a: Vec3, b: Vec3) -> f64 {
    a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
}
pub(crate) fn cross(a: Vec3, b: Vec3) -> Vec3 {
    [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
}
pub(crate) fn norm(a: Vec3) -> f64 {
    a[0].hypot(a[1]).hypot(a[2])
}

/// Neumaier accumulation in deterministic plane/triangle/component order.
#[derive(Clone, Copy, Default)]
pub(crate) struct Sum {
    value: f64,
    correction: f64,
}
impl Sum {
    pub fn add(&mut self, x: f64) {
        let next = self.value + x;
        self.correction += if self.value.abs() >= x.abs() {
            (self.value - next) + x
        } else {
            (x - next) + self.value
        };
        self.value = next;
    }
    pub fn get(self) -> f64 {
        self.value + self.correction
    }
}

#[derive(Clone)]
pub(crate) struct FaceIntegral {
    pub plane: usize,
    pub polygon: Vec<Vec3>,
    pub normal: Vec3,
    pub area: f64,
    pub centroid: Vec3,
    pub covariance: Tensor3,
    pub distance: f64,
}

pub(crate) struct Integrals {
    pub faces: Vec<FaceIntegral>,
    pub volume: f64,
    pub centroid: Vec3,
    pub moment: Tensor3,
    pub surface: f64,
    pub radius: f64,
    pub minimum_distance: f64,
    pub normal_closure: f64,
    pub affine_closure: f64,
    pub centroid_closure: f64,
}

fn reject(quantity: &'static str, residual: f64) -> GeometryError3 {
    GeometryError3::NumericalValidation { quantity, residual }
}

pub(crate) fn integrate(
    polygons: &[Polygon],
    planes: &[Plane],
    length: f64,
) -> Result<Integrals, GeometryError3> {
    let unit = D::from_f64(length);
    let mut faces = Vec::new();
    let mut volume = Sum::default();
    let mut first = [Sum::default(); 3];
    let mut tetrahedra = Vec::new();
    let mut radius = 0.0_f64;
    for polygon in polygons {
        let plane = &planes[polygon.plane];
        let mut dominant = 0;
        for a in 1..3 {
            let magnitude = |x: &D| if x.sign() < 0 { x.neg() } else { x.clone() };
            if magnitude(&plane.n[a]).cmp(&magnitude(&plane.n[dominant]))?
                == std::cmp::Ordering::Greater
            {
                dominant = a;
            }
        }
        let nscale = if plane.n[dominant].sign() < 0 {
            plane.n[dominant].neg()
        } else {
            plane.n[dominant].clone()
        };
        let raw = [
            plane.n[0].ratio(&nscale)?,
            plane.n[1].ratio(&nscale)?,
            plane.n[2].ratio(&nscale)?,
        ];
        let normal = scale(raw, 1.0 / norm(raw));
        let vertices = polygon
            .vertices
            .iter()
            .map(|v| v.point.scaled_f64(&unit))
            .collect::<Result<Vec<_>, _>>()?;
        let mut area = Sum::default();
        let mut area_first = [Sum::default(); 3];
        let mut triangles = Vec::new();
        for k in 1..vertices.len() - 1 {
            let [a, b, c] = [vertices[0], vertices[k], vertices[k + 1]];
            let weight = dot(cross(sub(b, a), sub(c, a)), normal) * 0.5;
            let v = dot(a, cross(b, c)) / 6.0;
            if !weight.is_finite() || weight <= 0.0 || !v.is_finite() || v <= 0.0 {
                return Err(reject("positive triangle/tetrahedron", weight.min(v)));
            }
            // Explicit conservative metric-separation policy. A small positive
            // face is NEVER deleted: reject the entire mesh if this floating
            // integral cannot be separated from the local arithmetic floor.
            // This is an engineering filter, not a rigorous interval enclosure.
            let radius = norm(a).max(norm(b)).max(norm(c));
            let area_bound = 256.0 * f64::EPSILON * radius * radius;
            let volume_bound = 512.0 * f64::EPSILON * radius * radius * radius;
            if weight <= area_bound {
                return Err(GeometryError3::UncertainMetric {
                    quantity: "triangle area",
                    value: weight,
                    separation_bound: area_bound,
                });
            }
            if v <= volume_bound {
                return Err(GeometryError3::UncertainMetric {
                    quantity: "tetrahedron volume",
                    value: v,
                    separation_bound: volume_bound,
                });
            }
            let sum = add(add(a, b), c);
            area.add(weight);
            volume.add(v);
            for axis in 0..3 {
                area_first[axis].add(weight * sum[axis] / 3.0);
                first[axis].add(v * sum[axis] / 4.0);
            }
            triangles.push(([a, b, c], weight));
            tetrahedra.push(([a, b, c], v));
        }
        let area = area.get();
        let centroid = area_first.map(|v| v.get() / area);
        let mut second = [[Sum::default(); 3]; 3];
        for (triangle, weight) in triangles {
            let shifted = triangle.map(|p| sub(p, centroid));
            let sum = add(add(shifted[0], shifted[1]), shifted[2]);
            for a in 0..3 {
                for b in 0..3 {
                    let diagonal: f64 = shifted.iter().map(|p| p[a] * p[b]).sum();
                    second[a][b].add(weight * (diagonal + sum[a] * sum[b]) / 12.0);
                }
            }
        }
        let covariance = second.map(|row| row.map(|v| v.get() / area));
        let distance = dot(centroid, normal);
        if !distance.is_finite() || distance <= 0.0 {
            return Err(reject("positive face distance", distance));
        }
        for p in &vertices {
            let residual = (dot(*p, normal) - distance).abs();
            if !residual.is_finite() || residual > 1e-10 {
                return Err(reject("floating face planarity", residual));
            }
            radius = radius.max(norm(*p));
        }
        faces.push(FaceIntegral {
            plane: polygon.plane,
            polygon: vertices,
            normal,
            area,
            centroid,
            covariance,
            distance,
        });
    }
    let volume = volume.get();
    if !volume.is_finite() || volume <= 0.0 {
        return Err(reject("positive volume", volume));
    }
    let centroid = first.map(|v| v.get() / volume);
    let mut moment = [[Sum::default(); 3]; 3];
    for (triangle, weight) in tetrahedra {
        let points = [
            scale(centroid, -1.0),
            sub(triangle[0], centroid),
            sub(triangle[1], centroid),
            sub(triangle[2], centroid),
        ];
        let sum = points.iter().copied().fold([0.0; 3], add);
        for a in 0..3 {
            for b in 0..3 {
                let diagonal: f64 = points.iter().map(|p| p[a] * p[b]).sum();
                moment[a][b].add(weight * (diagonal + sum[a] * sum[b]) / 20.0);
            }
        }
    }
    let moment = moment.map(|row| row.map(Sum::get));
    let diagonal_scale = (0..3).map(|a| moment[a][a]).fold(0.0_f64, f64::max);
    if !diagonal_scale.is_finite() || diagonal_scale <= 0.0 {
        return Err(reject("central moment positivity", diagonal_scale));
    }
    let j = moment.map(|row| row.map(|v| v / diagonal_scale));
    let terms = [
        j[0][0] * j[1][1] * j[2][2],
        j[0][1] * j[1][2] * j[2][0],
        j[0][2] * j[1][0] * j[2][1],
        -j[0][2] * j[1][1] * j[2][0],
        -j[0][1] * j[1][0] * j[2][2],
        -j[0][0] * j[1][2] * j[2][1],
    ];
    let determinant: f64 = terms.iter().sum();
    let roundoff_scale: f64 = terms.iter().map(|v| v.abs()).sum();
    if (0..3).any(|a| j[a][a] <= 0.0)
        || j[0][0] * j[1][1] - j[0][1] * j[1][0] <= 0.0
        || !determinant.is_finite()
        || determinant <= 64.0 * f64::EPSILON * roundoff_scale
    {
        return Err(reject("central moment conditioning", determinant));
    }
    let mut normal_sum = [Sum::default(); 3];
    let mut affine = [[Sum::default(); 3]; 3];
    let mut centred = [Sum::default(); 3];
    let mut surface = Sum::default();
    let mut divergence_volume = Sum::default();
    let mut minimum_distance = f64::INFINITY;
    for face in &faces {
        surface.add(face.area);
        minimum_distance = minimum_distance.min(face.distance);
        divergence_volume.add(face.area * face.distance / 3.0);
        let y = sub(face.centroid, centroid);
        if dot(y, face.normal) < -1e-12 {
            return Err(reject("centroid containment", dot(y, face.normal)));
        }
        for a in 0..3 {
            normal_sum[a].add(face.area * face.normal[a]);
            centred[a].add(face.area * dot(y, face.normal) * y[a]);
            for b in 0..3 {
                affine[a][b].add(face.area * y[a] * face.normal[b]);
            }
        }
    }
    let surface = surface.get();
    let normal_closure = norm(normal_sum.map(Sum::get)) / surface;
    let mut affine_closure = 0.0_f64;
    for a in 0..3 {
        for b in 0..3 {
            affine_closure = affine_closure
                .max((affine[a][b].get() / volume - if a == b { 1.0 } else { 0.0 }).abs());
        }
    }
    let centroid_closure = norm(centred.map(Sum::get)) / volume;
    for (quantity, residual) in [
        ("normal closure", normal_closure),
        ("affine closure", affine_closure),
        ("centroid closure", centroid_closure),
        (
            "divergence volume",
            (divergence_volume.get() / volume - 1.0).abs(),
        ),
    ] {
        if !residual.is_finite() || residual > 1e-10 {
            return Err(reject(quantity, residual));
        }
    }
    let length2 = length * length;
    let length3 = length2 * length;
    let length5 = length3 * length2;
    if ![length2, length3, length5]
        .iter()
        .all(|v| v.is_finite() && *v > 0.0)
    {
        return Err(GeometryError3::Unrepresentable("physical moment scales"));
    }
    for face in &mut faces {
        face.area *= length2;
        face.centroid = scale(face.centroid, length);
        face.polygon.iter_mut().for_each(|p| *p = scale(*p, length));
        face.covariance = face.covariance.map(|row| row.map(|v| v * length2));
        face.distance *= length;
        if !face.area.is_finite()
            || face.area <= 0.0
            || !face.centroid.iter().all(|v| v.is_finite())
            || !face.covariance.iter().flatten().all(|v| v.is_finite())
        {
            return Err(GeometryError3::Unrepresentable("physical face integrals"));
        }
    }
    let result = Integrals {
        faces,
        volume: volume * length3,
        centroid: scale(centroid, length),
        moment: moment.map(|row| row.map(|v| v * length5)),
        surface: surface * length2,
        radius: radius * length,
        minimum_distance: minimum_distance * length,
        normal_closure,
        affine_closure,
        centroid_closure,
    };
    if !result.volume.is_finite()
        || result.volume <= 0.0
        || !result.surface.is_finite()
        || result.surface <= 0.0
        || !result.moment.iter().flatten().all(|v| v.is_finite())
        || (0..3).any(|a| result.moment[a][a] <= 0.0)
        || !result.centroid.iter().all(|v| v.is_finite())
        || !result.radius.is_finite()
        || result.radius <= 0.0
        || !result.minimum_distance.is_finite()
        || result.minimum_distance <= 0.0
    {
        return Err(GeometryError3::Unrepresentable("physical cell integrals"));
    }
    Ok(result)
}
