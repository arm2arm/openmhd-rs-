//! Run both static point-curl profiles on shared periodic benchmark metrics.
use mhd_vector_pot::operators3::{independent_divergence, recover, trace};
use moving_mesh::{
    parallel,
    three_d::{
        Boundary3, Domain3, Image3, Vec3,
        fit::{FitError3, FitOrder3, SampleKey3},
        operator_mesh::{MeshFit3, OperatorCell3, OperatorFace3, OperatorMesh3},
    },
};
use std::{
    error::Error,
    fs::File,
    io::{self, BufReader, BufWriter, Read, Write},
};

fn u32le(r: &mut impl Read) -> io::Result<usize> {
    let mut b = [0; 4];
    r.read_exact(&mut b)?;
    Ok(u32::from_le_bytes(b) as usize)
}
fn i32le(r: &mut impl Read) -> io::Result<i64> {
    let mut b = [0; 4];
    r.read_exact(&mut b)?;
    Ok(i32::from_le_bytes(b) as i64)
}
fn f64le(r: &mut impl Read) -> io::Result<f64> {
    let mut b = [0; 8];
    r.read_exact(&mut b)?;
    Ok(f64::from_le_bytes(b))
}
fn vec3(r: &mut impl Read) -> io::Result<Vec3> {
    Ok([f64le(r)?, f64le(r)?, f64le(r)?])
}

fn run(
    mesh: &OperatorMesh3,
    a: &[Vec3],
    mean: Vec3,
    path: &str,
) -> Result<(), Box<dyn Error + Send + Sync>> {
    let count = mesh.cells().len();
    let linear = parallel::map(count, |i| mesh.fit(i, FitOrder3::Linear))
        .into_iter()
        .collect::<Result<Vec<_>, _>>()?;
    let mut out = BufWriter::new(File::create_new(path)?);
    out.write_all(b"M2BR2v01")?;
    out.write_all(&(count as u32).to_le_bytes())?;
    for order in [FitOrder3::Linear, FitOrder3::Quadratic] {
        let jets = parallel::map(count, |i| -> Result<_, FitError3> {
            let constructed;
            let fit: &MeshFit3 = match order {
                FitOrder3::Linear => &linear[i],
                FitOrder3::Quadratic => {
                    constructed = mesh.fit(i, order)?;
                    &constructed
                }
            };
            let v: Vec<_> = fit.owners.iter().map(|&j| a[j]).collect();
            let j = recover(&fit.fit, &v, mean)?;
            let q = &fit.fit.quality;
            Ok((
                j,
                [
                    q.kappa1_r,
                    q.pivot_ratio_bounds[0],
                    q.samples as f64,
                    fit.rings as f64,
                    q.kappa1_bounds[1],
                ],
            ))
        })
        .into_iter()
        .collect::<Result<Vec<_>, _>>()?;
        let field: Vec<_> = jets.iter().map(|(j, _)| j.field).collect();
        let div = independent_divergence(mesh, &field, &linear)?;
        for (i, (j, quality)) in jets.iter().enumerate() {
            for v in j
                .field
                .into_iter()
                .chain([
                    j.div_a,
                    div.cell_ls[i],
                    div.face_mean[i],
                    div.face_limited[i],
                ])
                .chain(*quality)
                .chain(j.same_fit_jacobian.map(trace))
            {
                out.write_all(&v.to_le_bytes())?;
            }
        }
    }
    out.flush()?;
    Ok(())
}
fn main() -> Result<(), Box<dyn Error + Send + Sync>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 4 {
        return Err("input output threads".into());
    }
    let mut r = BufReader::new(File::open(&args[1])?);
    let mut tag = [0; 8];
    r.read_exact(&mut tag)?;
    if &tag != b"M2BO2v01" {
        return Err("input format".into());
    }
    let n = u32le(&mut r)?;
    let f = u32le(&mut r)?;
    if !(1..=32768).contains(&n) || f > 64 * n {
        return Err("input size".into());
    }
    let mean = vec3(&mut r)?;
    let mut cells = Vec::with_capacity(n);
    let mut a = Vec::with_capacity(n);
    for i in 0..n {
        let id = SampleKey3::from_words(0x49, i as u64, Image3::ZERO).owner;
        cells.push(OperatorCell3 {
            id,
            winding: Image3::ZERO,
            volume: f64le(&mut r)?,
            centroid: vec3(&mut r)?,
        });
        a.push(vec3(&mut r)?);
    }
    let mut faces = Vec::with_capacity(f);
    for _ in 0..f {
        faces.push(OperatorFace3 {
            left: u32le(&mut r)?,
            right: Some(u32le(&mut r)?),
            right_image: Image3([i32le(&mut r)?, i32le(&mut r)?, i32le(&mut r)?]),
            area: f64le(&mut r)?,
            normal: vec3(&mut r)?,
            centroid: vec3(&mut r)?,
        });
    }
    if r.read(&mut tag)? != 0 {
        return Err("trailing input".into());
    }
    let m = OperatorMesh3::from_metrics(
        Domain3 {
            anchor: [0.; 3],
            width: [1.; 3],
            boundary: Boundary3::Periodic,
        },
        cells,
        faces,
    )?;
    parallel::with_threads(args[3].parse()?, || run(&m, &a, mean, &args[2]))??;
    Ok(())
}
