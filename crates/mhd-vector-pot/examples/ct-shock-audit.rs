//! Diagnostic of the bounded CT failure, not an acceptance test or new method.
use mhd_core::Primitive;
use mhd_vector_pot::{
    benchmarks::brio_initial,
    ct::{Config, Simulation},
};
use moving_mesh::Mesh;
use std::{
    fs::File,
    io::{BufWriter, Write},
    path::Path,
};

fn save(sim: &Simulation, output: &Path, stage: &str) -> Result<(), Box<dyn std::error::Error>> {
    let q = sim.recover(&sim.state)?;
    let rates = sim.energy_rates()?;
    let mut cells = BufWriter::new(File::create(output.join(format!("{stage}_cells.csv")))?);
    writeln!(cells, "id,time,x,y,volume,bx,by,p,dE,dK,dM,dp")?;
    for (i, ((c, q), r)) in sim.mesh.cells.iter().zip(q).zip(rates).enumerate() {
        writeln!(
            cells,
            "{i},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
            sim.time,
            c.centroid[0],
            c.centroid[1],
            c.volume,
            q.magnetic[0],
            q.magnetic[1],
            q.pressure,
            r[0],
            r[1],
            r[2],
            r[3]
        )?;
    }
    let mut faces = BufWriter::new(File::create(output.join(format!("{stage}_faces.csv")))?);
    writeln!(
        faces,
        "id,left,right,length,nx,ny,flux,dlx,dly,drx,dry,minus,plus"
    )?;
    for (i, f) in sim.mesh.faces.iter().enumerate() {
        let l = sim.mesh.displacement(f, f.left);
        let r = sim.mesh.displacement(f, f.right);
        let [minus, plus] = sim.geometry.endpoints[i];
        writeln!(
            faces,
            "{i},{},{},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{minus},{plus}",
            f.left,
            f.right,
            f.area,
            f.normal[0],
            f.normal[1],
            sim.state.flux[i],
            l[0],
            l[1],
            r[0],
            r[1]
        )?;
    }
    Ok(())
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let output = std::env::args().nth(1).ok_or("output directory required")?;
    let output = Path::new(&output);
    std::fs::create_dir_all(output)?;
    let mut sim = Simulation::new(
        Mesh::lattice(256, 4, [2., 0.125], 0.15)?,
        Config {
            gamma: 2.,
            mean_xy: [0.75, 0.],
            ..Config::default()
        },
        |x| {
            let a = brio_initial(x, [0.; 3]);
            (
                a.potential[2],
                Primitive {
                    density: a.density,
                    pressure: a.pressure,
                    velocity: a.velocity,
                    magnetic: [0.; 3],
                },
            )
        },
    )?;
    save(&sim, output, "initial")?;
    while sim.time < 0.02 {
        let old = sim.state.clone();
        let time = sim.time;
        if let Err(e) = sim.step(0.02) {
            let unchanged = old.fluid == sim.state.fluid
                && old.flux == sim.state.flux
                && old.bz_integral == sim.state.bz_integral
                && time == sim.time;
            std::fs::write(
                output.join("failure.json"),
                format!("{{\"error\":{e:?},\"rejected_state_unchanged\":{unchanged}}}\n"),
            )?;
            break;
        }
    }
    save(&sim, output, "last")?;
    Ok(())
}
