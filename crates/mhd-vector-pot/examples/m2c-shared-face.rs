//! Reproducible static shared-face maps and cell-average Fourier fields.
use mhd_io::{Decoder, Encoder};
use mhd_vector_pot::operators3::{SharedFaceCurl3, independent_divergence};
use moving_mesh::{
    parallel,
    three_d::{
        fit::{FitOrder3, SampleKey3},
        operator_mesh::{MeshFit3, OperatorCell3, OperatorFace3, OperatorMesh3},
        *,
    },
};
use std::{error::Error, fs, io::Write};

type Result<T> = std::result::Result<T, Box<dyn Error + Send + Sync>>;

fn unit() -> Domain3 {
    Domain3 {
        anchor: [0.; 3],
        width: [1.; 3],
        boundary: Boundary3::Periodic,
    }
}
fn key(i: usize) -> SampleKey3 {
    SampleKey3::from_words(0x49, i as u64, Image3::ZERO)
}

fn write_map(r: &mut Decoder<'_>, n: usize, out: &mut Encoder) -> Result<()> {
    if n > 32 {
        return Err("dense map limited to 32 owners".into());
    }
    let sites = (0..n)
        .map(|i| {
            Ok(Generator3 {
                id: key(i).owner,
                position: r.floats()?,
                winding: Image3::ZERO,
            })
        })
        .collect::<Result<Vec<_>>>()?;
    let a = (0..n)
        .map(|_| r.floats())
        .collect::<std::result::Result<Vec<Vec3>, _>>()?;
    let g = HalfSpaceOracle3::build(unit(), &sites)?;
    let mesh = OperatorMesh3::from_validated(&g)?;
    let op = SharedFaceCurl3::from_validated(&g)?;
    out.usize(g.faces().len());
    for (i, c) in g.cells().iter().enumerate() {
        let f = mesh.fit(i, FitOrder3::Quadratic)?;
        out.float(c.volume);
        out.floats(&mesh.cells()[i].centroid);
        out.usize(f.owners.len());
        for (&owner, row) in f.owners.iter().zip(f.fit.samples()) {
            out.usize(owner);
            out.floats(&row.displacement);
            for k in row.key.image.0 {
                out.u64(k as u64);
            }
        }
    }
    let face_values = op.face_values(&a)?;
    for (f, v) in g.faces().iter().zip(face_values) {
        out.usize(f.left as usize);
        out.usize(f.right.ok_or("periodic face")? as usize);
        for k in f.right_wrapped_image.0 {
            out.u64(k as u64);
        }
        out.float(f.area);
        out.floats(&f.normal);
        out.usize(f.polygon.len());
        for &v in &f.polygon {
            out.floats(&std::array::from_fn::<_, 3, _>(|k| {
                sites[f.left as usize].position[k] + v[k]
            }));
        }
        out.floats(&v);
    }
    for values in [op.apply(&a)?, op.transpose(&a)?, op.gram_diagonal()?] {
        for row in values {
            out.floats(&row);
        }
    }
    for j in 0..n {
        for k in 0..3 {
            let mut e = vec![[0.; 3]; n];
            e[j][k] = 1.;
            for v in op.apply(&e)? {
                out.floats(&v);
            }
        }
    }
    Ok(())
}

fn write_fields(r: &mut Decoder<'_>, n: usize, out: &mut Encoder) -> Result<()> {
    let nf = r.usize()?;
    if nf > 64 * n || nf == 0 {
        return Err("face count".into());
    }
    let mean: Vec3 = r.floats()?;
    if !mean.iter().all(|x| x.is_finite()) {
        return Err("harmonic field".into());
    }
    let mut cells = Vec::with_capacity(n);
    let mut a = Vec::with_capacity(n);
    for i in 0..n {
        cells.push(OperatorCell3 {
            id: key(i).owner,
            winding: Image3::ZERO,
            volume: r.float()?,
            centroid: r.floats()?,
        });
        a.push(r.floats()?);
    }
    let mut faces = Vec::with_capacity(nf);
    let mut cov = Vec::with_capacity(nf);
    for _ in 0..nf {
        faces.push(OperatorFace3 {
            left: r.usize()?,
            right: Some(r.usize()?),
            right_image: Image3([r.i32()?.into(), r.i32()?.into(), r.i32()?.into()]),
            area: r.float()?,
            normal: r.floats()?,
            centroid: r.floats()?,
        });
        cov.push([r.floats()?, r.floats()?, r.floats()?]);
    }
    let mesh = OperatorMesh3::from_metrics(unit(), cells, faces)?;
    let linear: Vec<MeshFit3> = parallel::try_map(n, |i| mesh.fit(i, FitOrder3::Linear))?;
    let op = SharedFaceCurl3::from_metrics(mesh, cov)?;
    let mut b = op.apply(&a)?;
    for v in &mut b {
        for (x, m) in v.iter_mut().zip(mean) {
            *x += m;
        }
    }
    let div = independent_divergence(op.mesh(), &b, &linear)?;
    for (i, row) in b.iter().enumerate() {
        out.floats(row);
        out.floats(&[div.cell_ls[i], div.face_mean[i], div.face_limited[i]]);
    }
    Ok(())
}

fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 4 {
        return Err("input output threads".into());
    }
    let input = fs::read(&args[1])?;
    let mut r = Decoder::new(&input);
    let kind = r.take(8)?;
    let n = r.usize()?;
    if !(1..=32768).contains(&n) {
        return Err("cell count".into());
    }
    let mut out = Encoder::new();
    out.string(SharedFaceCurl3::POLICY);
    out.string(SharedFaceCurl3::SAMPLING);
    out.usize(n);
    parallel::with_threads(args[3].parse()?, || match kind {
        b"M2CFMAP1" => write_map(&mut r, n, &mut out),
        b"M2CFFLD1" => write_fields(&mut r, n, &mut out),
        _ => Err("unknown input schema".into()),
    })??;
    r.finish()?;
    let mut file = fs::File::create_new(&args[2])?;
    file.write_all(&out.finish())?;
    file.sync_all()?;
    Ok(())
}
