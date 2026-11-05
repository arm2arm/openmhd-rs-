//! Exact geometry and stencil persistence. Cached coefficients are never refitted.
use super::quadratic::{Compact, Quadratic, Sample};
use super::{Cell, DerivativeSample, Derivatives, Face, Mesh};
use mhd_io::{Decoder, Encoder};

pub struct CachedGeometry {
    pub mesh: Mesh,
    pub neighbours: Derivatives,
    pub faces: Derivatives,
    pub quadratic: Option<Quadratic>,
    pub compact: Option<Compact>,
}

pub fn mesh_bytes(mesh: &Mesh) -> Result<Vec<u8>, String> {
    mesh.validate()?;
    let mut w = Encoder::new();
    w.floats(&mesh.lengths);
    w.usize(mesh.generators.len());
    for p in &mesh.generators {
        w.floats(p);
    }
    w.usize(mesh.cells.len());
    for c in &mesh.cells {
        w.float(c.volume);
        w.floats(&c.centroid);
        w.usize(c.faces.len());
        for &(f, sign) in &c.faces {
            w.usize(f);
            w.float(sign);
        }
    }
    w.usize(mesh.faces.len());
    for f in &mesh.faces {
        w.usize(f.left);
        w.usize(f.right);
        for x in f.image {
            w.i32(x);
        }
        w.floats(&f.centroid);
        w.floats(&f.normal);
        w.float(f.area);
    }
    Ok(w.finish())
}

fn read_mesh(bytes: &[u8]) -> Result<Mesh, String> {
    let mut r = Decoder::new(bytes);
    let lengths = r.floats()?;
    let n = r.count(16)?;
    let generators = (0..n).map(|_| r.floats()).collect::<Result<_, _>>()?;
    let n = r.count(32)?;
    let mut cells = Vec::with_capacity(n);
    for _ in 0..n {
        let volume = r.float()?;
        let centroid = r.floats()?;
        let n = r.count(16)?;
        let faces = (0..n)
            .map(|_| Ok((r.usize()?, r.float()?)))
            .collect::<Result<_, String>>()?;
        cells.push(Cell {
            volume,
            centroid,
            faces,
        });
    }
    let n = r.count(64)?;
    let mut faces = Vec::with_capacity(n);
    for _ in 0..n {
        faces.push(Face {
            left: r.usize()?,
            right: r.usize()?,
            image: [r.i32()?, r.i32()?],
            centroid: r.floats()?,
            normal: r.floats()?,
            area: r.float()?,
        });
    }
    r.finish()?;
    let mesh = Mesh {
        lengths,
        generators,
        cells,
        faces,
    };
    mesh.validate()?;
    Ok(mesh)
}

fn write_derivatives(w: &mut Encoder, d: &Derivatives) {
    w.usize(d.input_len);
    w.float(d.worst_condition);
    w.usize(d.samples.len());
    for row in &d.samples {
        w.usize(row.len());
        for s in row {
            w.usize(s.index);
            w.floats(&s.weight);
        }
    }
}
fn read_derivatives(r: &mut Decoder<'_>) -> Result<Derivatives, String> {
    let input_len = r.usize()?;
    let worst_condition = r.float()?;
    let n = r.count(8)?;
    let mut samples = Vec::with_capacity(n);
    for _ in 0..n {
        let n = r.count(24)?;
        samples.push(
            (0..n)
                .map(|_| {
                    Ok(DerivativeSample {
                        index: r.usize()?,
                        weight: r.floats()?,
                    })
                })
                .collect::<Result<_, String>>()?,
        );
    }
    Ok(Derivatives {
        input_len,
        worst_condition,
        samples,
    })
}
fn validate(
    mesh: &Mesh,
    neighbours: &Derivatives,
    faces: &Derivatives,
    quadratic: Option<&Quadratic>,
    compact: Option<&Compact>,
) -> Result<(), String> {
    mesh.validate()?;
    let n = mesh.cells.len();
    for (d, at_faces) in [(neighbours, false), (faces, true)] {
        if d.input_len != if at_faces { mesh.faces.len() } else { n }
            || d.samples.len() != n
            || !d.worst_condition.is_finite()
            || d.worst_condition <= 0.
        {
            return Err("invalid derivative cache shape/condition".into());
        }
        for (i, (row, cell)) in d.samples.iter().zip(&mesh.cells).enumerate() {
            if row.len() != cell.faces.len() {
                return Err("invalid derivative cache row".into());
            }
            for (s, &(f, _)) in row.iter().zip(&cell.faces) {
                let expected = if at_faces {
                    f
                } else {
                    mesh.neighbour(&mesh.faces[f], i).0
                };
                if s.index != expected || !s.weight.iter().all(|x| x.is_finite()) {
                    return Err("invalid derivative cache sample".into());
                }
            }
        }
    }
    if let Some(q) = quadratic {
        if q.samples.len() != n
            || !q.worst_condition.is_finite()
            || q.worst_condition <= 0.
            || q.samples.iter().any(|row| {
                row.len() < 6
                    || row
                        .iter()
                        .any(|s| s.index >= n || !s.coefficient.iter().all(|x| x.is_finite()))
            })
        {
            return Err("invalid quadratic cache".into());
        }
    }
    if let Some(c) = compact {
        if quadratic.is_none()
            || c.moments.len() != n
            || !c.moments.iter().flatten().flatten().all(|x| x.is_finite())
        {
            return Err("invalid compact cache".into());
        }
    }
    Ok(())
}
pub fn encode(
    mesh: &Mesh,
    neighbours: &Derivatives,
    faces: &Derivatives,
    quadratic: Option<&Quadratic>,
    compact: Option<&Compact>,
) -> Result<Vec<u8>, String> {
    validate(mesh, neighbours, faces, quadratic, compact)?;
    let mut w = Encoder::new();
    w.bytes(&mesh_bytes(mesh)?);
    write_derivatives(&mut w, neighbours);
    write_derivatives(&mut w, faces);
    w.boolean(quadratic.is_some());
    if let Some(q) = quadratic {
        w.float(q.worst_condition);
        w.usize(q.samples.len());
        for row in &q.samples {
            w.usize(row.len());
            for s in row {
                w.usize(s.index);
                w.floats(&s.coefficient);
            }
        }
    }
    w.boolean(compact.is_some());
    if let Some(c) = compact {
        w.usize(c.moments.len());
        for row in &c.moments {
            for axis in row {
                w.floats(axis);
            }
        }
    }
    Ok(w.finish())
}
pub fn decode(bytes: &[u8]) -> Result<CachedGeometry, String> {
    let mut r = Decoder::new(bytes);
    let mesh = read_mesh(r.bytes()?)?;
    let neighbours = read_derivatives(&mut r)?;
    let faces = read_derivatives(&mut r)?;
    let quadratic = if r.boolean()? {
        let worst_condition = r.float()?;
        let n = r.count(8)?;
        let mut samples = Vec::with_capacity(n);
        for _ in 0..n {
            let n = r.count(56)?;
            samples.push(
                (0..n)
                    .map(|_| {
                        Ok(Sample {
                            index: r.usize()?,
                            coefficient: r.floats()?,
                        })
                    })
                    .collect::<Result<_, String>>()?,
            );
        }
        Some(Quadratic {
            worst_condition,
            samples,
        })
    } else {
        None
    };
    let compact = if r.boolean()? {
        let n = r.count(48)?;
        let moments = (0..n)
            .map(|_| Ok([r.floats()?, r.floats()?]))
            .collect::<Result<_, String>>()?;
        Some(Compact { moments })
    } else {
        None
    };
    r.finish()?;
    validate(
        &mesh,
        &neighbours,
        &faces,
        quadratic.as_ref(),
        compact.as_ref(),
    )?;
    Ok(CachedGeometry {
        mesh,
        neighbours,
        faces,
        quadratic,
        compact,
    })
}
