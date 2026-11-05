//! Isolated Voronoi loop advection; does not evolve the gas or cleaning field.
use mhd_vector_pot::{benchmarks::passive_loop, passive::Passive};
use moving_mesh::Mesh;
use std::{fmt::Write as _, fs, path::PathBuf};
fn snapshot(sim: &Passive) -> Result<String, String> {
    let mut csv = String::from("id,time,x,y,volume,az,bx,by,bz\n");
    let b = sim.magnetic()?;
    for (i, p) in sim.positions().iter().enumerate() {
        writeln!(
            &mut csv,
            "{i},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},0",
            sim.time(),
            p[0],
            p[1],
            sim.mesh().cells[i].volume,
            sim.potential()[i],
            b[i][0],
            b[i][1]
        )
        .map_err(|e| e.to_string())?;
    }
    Ok(csv)
}
fn run() -> Result<(), String> {
    let mut mesh_cache: Option<PathBuf> = None;
    let mut n = 32;
    let mut jitter = 0.;
    let mut comoving = false;
    let mut output = PathBuf::from("results/passive_voronoi");
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == "--comoving" {
            comoving = true;
            continue;
        }
        let value = args.next().ok_or("missing value")?;
        match arg.as_str() {
            "--mesh-cache" => mesh_cache = Some(PathBuf::from(value)),
            "--n" => n = value.parse().map_err(|_| "invalid n")?,
            "--jitter" => jitter = value.parse().map_err(|_| "invalid jitter")?,
            "--output" => output = PathBuf::from(value),
            _ => return Err("unknown option".into()),
        }
    }
    let v = [2., 1.];
    let w = if comoving { v } else { [0.; 2] };
    let mesh = if let Some(path) = mesh_cache {
        Mesh::decode_lattice(
            &fs::read_to_string(path).map_err(|e| e.to_string())?,
            n,
            n,
            [1.; 2],
            jitter,
        )?
    } else {
        Mesh::lattice(n, n, [1.; 2], jitter)?
    };
    let mut sim = Passive::new(mesh, v, w, |x| passive_loop(x, 0., [2., 1., 0.]).0)?;
    fs::create_dir_all(&output).map_err(|e| e.to_string())?;
    fs::write(output.join("initial.csv"), snapshot(&sim)?).map_err(|e| e.to_string())?;
    sim.advance_to(1.)?;
    fs::write(output.join("final.csv"), snapshot(&sim)?).map_err(|e| e.to_string())?;
    fs::write(output.join("summary.json"),format!("{{\"case\":\"passive_loop\",\"operator\":\"voronoi-face-ls-heun-v1\",\"n\":{n},\"jitter\":{jitter},\"comoving\":{comoving},\"time\":{},\"steps\":{},\"velocity\":[2,1],\"precision\":\"f64\",\"boundary\":\"periodic unit square\",\"gas_evolved\":false}}\n",sim.time(),sim.steps())).map_err(|e|e.to_string())?;
    println!(
        "passive n={n} jitter={jitter} comoving={comoving}, steps={}",
        sim.steps()
    );
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("error: {error}");
        std::process::exit(1);
    }
}
