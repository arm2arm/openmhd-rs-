//! Export exact effective derivative rows for an independent small SVD audit.
use moving_mesh::{Derivatives, Mesh};
use std::{collections::BTreeMap, fs, io::Write, path::Path};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let directory = std::env::args()
        .nth(1)
        .ok_or("usage: symmetry-rank-probe NEW_DIRECTORY")?;
    let path = Path::new(&directory);
    fs::create_dir(path)?;
    for nx in [16, 32, 64, 256] {
        for jitter in [0., 0.15] {
            let mesh = Mesh::lattice(nx, 4, [2., 0.125], jitter)?;
            let mut cells = fs::File::create(path.join(format!("n{nx}_j{jitter}_cells.csv")))?;
            writeln!(cells, "id,x,y,volume")?;
            for (i, c) in mesh.cells.iter().enumerate() {
                writeln!(
                    cells,
                    "{i},{:.17e},{:.17e},{:.17e}",
                    c.centroid[0], c.centroid[1], c.volume
                )?;
            }
            for (name, d) in [
                ("affine", Derivatives::build(&mesh, false)?),
                ("quadratic", Derivatives::quadratic(&mesh)?),
            ] {
                let mut output =
                    fs::File::create(path.join(format!("n{nx}_j{jitter}_{name}.csv")))?;
                writeln!(output, "row,column,dx,dy")?;
                for (i, samples) in d.samples.iter().enumerate() {
                    let mut row: BTreeMap<usize, [f64; 2]> = BTreeMap::new();
                    for s in samples {
                        for k in 0..2 {
                            row.entry(s.index).or_default()[k] += s.weight[k];
                            row.entry(samples[0].index).or_default()[k] -= s.weight[k];
                        }
                    }
                    for (j, w) in row {
                        writeln!(output, "{i},{j},{:.17e},{:.17e}", w[0], w[1])?;
                    }
                }
            }
        }
    }
    Ok(())
}
