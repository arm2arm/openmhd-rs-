//! Representation floor of the transverse field on a planar-jittered mesh.
//!
//! Samples a y-invariant reference potential Az(x), taken from a regular-mesh
//! snapshot, at the centroids of a jittered Brio mesh and applies the linear
//! neighbour and quadratic curls. The resulting |Bx - mean| is the error that
//! the reconstruction alone produces for that profile, with no evolution.
//! With --cells the CSV is a snapshot of the same rest-frame mesh and its az
//! column is used cell by cell.
//! Usage: bx-floor [--cells] CSV NX NY JITTER
use moving_mesh::{Derivatives, Mesh};
use std::{env, fs};

fn main() -> Result<(), String> {
    let mut args: Vec<String> = env::args().skip(1).collect();
    let cells = args.first().is_some_and(|a| a == "--cells");
    if cells {
        args.remove(0);
    }
    if args.len() != 4 {
        return Err("usage: bx-floor [--cells] CSV NX NY JITTER".into());
    }
    let text = fs::read_to_string(&args[0]).map_err(|e| e.to_string())?;
    let mut lines = text.lines();
    let header: Vec<&str> = lines.next().ok_or("empty reference")?.split(',').collect();
    let column = |name: &str| {
        header
            .iter()
            .position(|h| *h == name)
            .ok_or(format!("missing column {name}"))
    };
    let (cx, cy, ca) = (column("x")?, column("y")?, column("az")?);
    let mut rows: Vec<(f64, f64, f64)> = Vec::new();
    for line in lines {
        let v: Vec<f64> = line
            .split(',')
            .map(|s| {
                s.parse()
                    .map_err(|_| "invalid reference number".to_string())
            })
            .collect::<Result<_, _>>()?;
        rows.push((v[cx], v[cy], v[ca]));
    }
    // One row of the regular reference; reject a reference that depends on y.
    let rows_for_table: &[(f64, f64, f64)] = if cells { &[] } else { &rows };
    let y0 = rows_for_table.iter().fold(f64::INFINITY, |m, r| m.min(r.1));
    let mut table: Vec<(f64, f64)> = rows_for_table
        .iter()
        .filter(|r| (r.1 - y0).abs() < 1e-12)
        .map(|r| (r.0.rem_euclid(2.), r.2))
        .collect();
    table.sort_by(|a, b| a.0.total_cmp(&b.0));
    for r in rows_for_table {
        let nearest = table
            .iter()
            .min_by(|a, b| {
                (a.0 - r.0.rem_euclid(2.))
                    .abs()
                    .total_cmp(&(b.0 - r.0.rem_euclid(2.)).abs())
            })
            .ok_or("empty reference row")?;
        if (nearest.1 - r.2).abs() > 1e-9 {
            return Err("reference potential is not y-invariant".into());
        }
    }
    let m = table.len();
    let h = 2. / m as f64;
    if !cells
        && (m < 8
            || table
                .iter()
                .enumerate()
                .any(|(i, t)| (t.0 - (i as f64 + 0.5) * h).abs() > 1e-9))
    {
        return Err("reference must be a regular periodic lattice on [0,2]".into());
    }
    // Periodic Catmull-Rom interpolation of the reference potential.
    let az = |x: f64| {
        let s = x.rem_euclid(2.) / h - 0.5;
        let i = s.floor();
        let t = s - i;
        let p = |k: i64| table[(i as i64 + k).rem_euclid(m as i64) as usize].1;
        let (a, b, c, d) = (p(-1), p(0), p(1), p(2));
        b + 0.5 * t * (c - a + t * (2. * a - 5. * b + 4. * c - d + t * (3. * (b - c) + d - a)))
    };
    let nx: usize = args[1].parse().map_err(|_| "invalid NX")?;
    let ny: usize = args[2].parse().map_err(|_| "invalid NY")?;
    let jitter: f64 = args[3].parse().map_err(|_| "invalid JITTER")?;
    let mesh = Mesh::lattice(nx, ny, [2., 0.125], jitter)?;
    // A snapshot of the same mesh is used cell by cell (e.g. a fitted x-only
    // part or its remainder); a regular reference is interpolated in x.
    let values: Vec<f64> = if cells {
        if rows.len() != mesh.cells.len()
            || rows.iter().zip(&mesh.cells).any(|(r, c)| {
                (r.0 - c.centroid[0]).abs() > 1e-9 || (r.1 - c.centroid[1]).abs() > 1e-9
            })
        {
            return Err("snapshot cells do not match the requested rest-frame mesh".into());
        }
        rows.iter().map(|r| r.2).collect()
    } else {
        mesh.cells.iter().map(|c| az(c.centroid[0])).collect()
    };
    let volume: f64 = mesh.cells.iter().map(|c| c.volume).sum();
    println!("stencil,max_bx_error,l1_bx_error");
    for (name, stencil) in [
        ("neighbour", Derivatives::build(&mesh, false)?),
        ("quadratic", Derivatives::quadratic(&mesh)?),
    ] {
        let g = stencil.gradient(&values)?;
        let max = g.iter().fold(0.0_f64, |m, g| m.max(g[1].abs()));
        let l1 = g
            .iter()
            .zip(&mesh.cells)
            .map(|(g, c)| c.volume * g[1].abs())
            .sum::<f64>()
            / volume;
        println!("{name},{max:.6e},{l1:.6e}");
    }
    Ok(())
}
