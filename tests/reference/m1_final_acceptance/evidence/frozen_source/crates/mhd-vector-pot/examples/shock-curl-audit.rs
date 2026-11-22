//! Initial reconstruction audit only; no evolution or changes to any solver profile.
use mhd_vector_pot::{benchmarks::brio_initial, operators::MagneticFit};
use moving_mesh::{Derivatives, Mesh, dot};
use std::{f64::consts::PI, fs, io::Write, path::Path};

fn sample(field: &str, x: f64) -> (f64, f64) {
    match field {
        "brio" => (
            brio_initial([x, 0.], [0.; 3]).potential[2],
            if x.rem_euclid(2.) < 1. { -1. } else { 1. },
        ),
        "smooth" => ((PI * x).cos() / PI, -(PI * x).sin()),
        _ => unreachable!(),
    }
}

fn audit(nx: usize, jitter: f64, output: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let mesh = Mesh::lattice(nx, 4, [2., 0.125], jitter)?;
    let stencil = Derivatives::build(&mesh, false)?;
    let constants = stencil.gradient(&vec![0.4; mesh.cells.len()])?;
    let constant_error = constants
        .iter()
        .flatten()
        .map(|x| x.abs())
        .fold(0., f64::max);
    for field in ["brio", "smooth"] {
        let a: Vec<_> = mesh
            .cells
            .iter()
            .map(|c| [0., 0., sample(field, c.centroid[0]).0])
            .collect();
        let fit = MagneticFit::build(&mesh, &a, &vec![0.; a.len()], [0.75, 0., 0.], false)?;
        let mut mixed = Vec::new();
        let mut decomposition_error = 0.0_f64;
        let mut affine_error = 0.0_f64;
        let mut cells =
            fs::File::create(output.join(format!("n{nx}_j{jitter}_{field}_cells.csv")))?;
        writeln!(
            cells,
            "id,x,y,volume,bx_error,by_error,mixed_brio_slopes,predicted_bx_error"
        )?;
        for (i, cell) in mesh.cells.iter().enumerate() {
            let gx = sample(field, cell.centroid[0]).1;
            let offsets: Vec<_> = cell
                .faces
                .iter()
                .map(|&(f, _)| mesh.neighbour(&mesh.faces[f], i).1)
                .collect();
            let samples = &stencil.samples[i];
            let residual: Vec<_> = samples
                .iter()
                .zip(&offsets)
                .map(|(s, d)| a[s.index][2] - a[i][2] - gx * d[0])
                .collect();
            let predicted: f64 = samples
                .iter()
                .zip(&residual)
                .map(|(s, r)| s.weight[1] * (r - residual[0]))
                .sum();
            let measured = fit.raw[i][2][1];
            decomposition_error = decomposition_error.max((predicted - measured).abs());
            let sides: Vec<_> = samples
                .iter()
                .map(|s| mesh.cells[s.index].centroid[0].rem_euclid(2.) < 1.)
                .collect();
            mixed.push(sides.iter().any(|s| *s != sides[0]));
            let affine: Vec<_> = offsets.iter().map(|&d| 0.2 + dot([0.7, -0.3], d)).collect();
            for (k, exact) in [0.7, -0.3].iter().enumerate() {
                let derivative: f64 = samples
                    .iter()
                    .zip(&affine)
                    .map(|(s, v)| s.weight[k] * (v - affine[0]))
                    .sum();
                affine_error = affine_error.max((derivative - exact).abs());
            }
            writeln!(
                cells,
                "{i},{:.17e},{:.17e},{:.17e},{measured:.17e},{:.17e},{},{predicted:.17e}",
                cell.centroid[0],
                cell.centroid[1],
                cell.volume,
                fit.magnetic[i][1] + gx,
                usize::from(mixed[i])
            )?;
        }
        let worst = (0..a.len())
            .max_by(|&i, &j| fit.raw[i][2][1].abs().total_cmp(&fit.raw[j][2][1].abs()))
            .unwrap();
        let mut samples =
            fs::File::create(output.join(format!("n{nx}_j{jitter}_{field}_worst.csv")))?;
        writeln!(samples, "cell_id,neighbour,dx,dy,area,az,weight_x,weight_y")?;
        for (&(f, _), s) in mesh.cells[worst].faces.iter().zip(&stencil.samples[worst]) {
            let (j, d) = mesh.neighbour(&mesh.faces[f], worst);
            assert_eq!(j, s.index);
            writeln!(
                samples,
                "{worst},{j},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
                d[0], d[1], mesh.faces[f].area, a[j][2], s.weight[0], s.weight[1]
            )?;
        }
        let volume: f64 = mesh.cells.iter().map(|c| c.volume).sum();
        let l1 = fit
            .raw
            .iter()
            .zip(&mesh.cells)
            .map(|(g, c)| g[2][1].abs() * c.volume)
            .sum::<f64>()
            / volume;
        let rms = (fit
            .raw
            .iter()
            .zip(&mesh.cells)
            .map(|(g, c)| g[2][1].powi(2) * c.volume)
            .sum::<f64>()
            / volume)
            .sqrt();
        let pure = fit
            .raw
            .iter()
            .zip(&mixed)
            .filter(|(_, mixed)| !**mixed)
            .map(|(g, _)| g[2][1].abs())
            .fold(0., f64::max);
        println!(
            "{nx},{jitter},{field},{worst},{:.17e},{l1:.17e},{rms:.17e},{},{pure:.17e},{decomposition_error:.17e},{affine_error:.17e},{constant_error:.17e},{:.17e},{:.17e},{:.17e}",
            fit.raw[worst][2][1].abs(),
            mixed.iter().filter(|m| **m).count(),
            stencil.worst_condition,
            fit.raw[worst][2][0],
            fit.raw[worst][2][1]
        );
    }
    Ok(())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let path = std::env::args()
        .nth(1)
        .ok_or("usage: shock-curl-audit NEW_OUTPUT_DIR")?;
    let output = Path::new(&path);
    fs::create_dir(output)?;
    println!(
        "nx,jitter,field,worst_cell,bx_max_error,bx_L1,bx_RMS,mixed_brio_count,bx_max_unmixed,decomposition_max_error,affine_max_error,constant_max_error,worst_condition,worst_gx,worst_gy"
    );
    for nx in [256, 512, 1024] {
        for jitter in [0., 0.15] {
            audit(nx, jitter, output)?;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn audit_fields_are_periodic_and_have_the_stated_derivatives() {
        for field in ["brio", "smooth"] {
            for x in [0.13, 0.87, 1.23, 1.77] {
                let (a, gx) = sample(field, x);
                let h = 1e-6;
                assert!((a - sample(field, x + 2.).0).abs() < 1e-14);
                assert!(
                    ((sample(field, x + h).0 - sample(field, x - h).0) / (2. * h) - gx).abs()
                        < 1e-9
                );
            }
        }
    }
}
