//! Bounded comparison of initial derivatives. No state evolution or changed gates.
use moving_mesh::{Derivatives, Mesh};
use std::f64::consts::{PI, TAU};

fn probe(nx: usize, ny: usize, jitter: f64, field: &str) -> Result<(), String> {
    let lengths = if ny == 4 { [2., 0.125] } else { [1.; 2] };
    let mesh = Mesh::lattice(nx, ny, lengths, jitter)?;
    let data: Vec<_> = mesh
        .cells
        .iter()
        .map(|c| {
            let [x, y] = c.centroid;
            match field {
                "brio" => {
                    if x.rem_euclid(2.) < 1. {
                        (-x, [-1., 0.])
                    } else {
                        (x - 2., [1., 0.])
                    }
                }
                "smooth-1d" => ((PI * x).cos() / PI, [-(PI * x).sin(), 0.]),
                "smooth-2d" => (
                    (TAU * x).sin() * (TAU * y).cos() / TAU,
                    [
                        (TAU * x).cos() * (TAU * y).cos(),
                        -(TAU * x).sin() * (TAU * y).sin(),
                    ],
                ),
                _ => unreachable!(),
            }
        })
        .collect();
    let values: Vec<_> = data.iter().map(|d| d.0).collect();
    for (name, derivative) in [
        ("affine", Derivatives::build(&mesh, false)?),
        ("quadratic", Derivatives::quadratic(&mesh)?),
    ] {
        let result = derivative.gradient(&values)?;
        let volume = lengths[0] * lengths[1];
        let mut maximum = 0.0_f64;
        let mut l1 = 0.;
        let mut squared = 0.;
        for ((c, g), (_, exact)) in mesh.cells.iter().zip(result).zip(&data) {
            let error = [g[0] - exact[0], g[1] - exact[1]];
            maximum = maximum.max(error[1].abs());
            l1 += c.volume * error[1].abs() / volume;
            squared += c.volume * (error[0] * error[0] + error[1] * error[1]) / volume;
        }
        println!(
            "{nx},{ny},{jitter},{field},{name},{maximum:.17e},{l1:.17e},{:.17e},{:.17e}",
            squared.sqrt(),
            derivative.worst_condition
        );
    }
    Ok(())
}

fn main() -> Result<(), String> {
    println!(
        "nx,ny,jitter,field,stencil,transverse_max_error,transverse_L1,gradient_L2,condition_indicator"
    );
    for nx in [256, 512, 1024] {
        for jitter in [0., 0.15] {
            for field in ["brio", "smooth-1d"] {
                probe(nx, 4, jitter, field)?;
            }
        }
    }
    for n in [12, 24, 48] {
        for jitter in [0., 0.15] {
            probe(n, n, jitter, "smooth-2d")?;
        }
    }
    Ok(())
}
