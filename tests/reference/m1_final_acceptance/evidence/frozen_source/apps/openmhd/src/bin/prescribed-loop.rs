//! Separate constant-flow Voronoi loop; no conservative fluid is evolved.
use mhd_vector_pot::{benchmarks::passive_loop, transport::Transport};
use moving_mesh::Mesh;
use std::{fmt::Write as _, fs, path::PathBuf};

fn snapshot(sim: &Transport) -> Result<String, String> {
    let fields = sim.fields()?;
    let mut csv =
        String::from("id,time,x,y,volume,az,bx,by,bz,div_b_ls,div_b_face,div_b_limited\n");
    for (i, cell) in sim.mesh().cells.iter().enumerate() {
        write!(&mut csv, "{i}").map_err(|e| e.to_string())?;
        let x = sim.position(i);
        let b = fields.magnetic[i];
        for v in [
            sim.time(),
            x[0],
            x[1],
            cell.volume,
            sim.potential()[i][0],
            b[0],
            b[1],
            b[2],
            fields.divergences[0][i],
            fields.divergences[1][i],
            fields.divergences[2][i],
        ] {
            write!(&mut csv, ",{v:.17e}").map_err(|e| e.to_string())?;
        }
        csv.push('\n');
    }
    Ok(csv)
}
fn run() -> Result<(), String> {
    let mut n = 32usize;
    let mut jitter = 0.;
    let mut time = 1.;
    let mut velocity = [2., 1.];
    let mut mesh_velocity = [0.; 2];
    let mut output = PathBuf::from("results/prescribed_loop_single");
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == "--help" {
            println!(
                "prescribed-loop --n N --jitter J --time T --vx VX --vy VY --mesh-x WX --mesh-y WY --output DIR\nConstant-flow planar Voronoi transport; f64, periodic unit square, no gas/EOS evolution."
            );
            return Ok(());
        }
        let value = args
            .next()
            .ok_or_else(|| format!("missing value for {arg}"))?;
        let number = || {
            value
                .parse::<f64>()
                .map_err(|_| format!("invalid number for {arg}"))
        };
        match arg.as_str() {
            "--n" => n = value.parse().map_err(|_| "invalid N")?,
            "--jitter" => jitter = number()?,
            "--time" => time = number()?,
            "--vx" => velocity[0] = number()?,
            "--vy" => velocity[1] = number()?,
            "--mesh-x" => mesh_velocity[0] = number()?,
            "--mesh-y" => mesh_velocity[1] = number()?,
            "--output" => output = PathBuf::from(value),
            _ => return Err(format!("unknown option {arg}")),
        }
    }
    if !time.is_finite() || time < 0. {
        return Err("invalid target time".into());
    }
    let mesh = Mesh::lattice(n, n, [1.; 2], jitter)?;
    let mut sim = Transport::new(mesh, velocity, mesh_velocity, |x| {
        passive_loop(x, 0., [velocity[0], velocity[1], 0.]).0
    })?;
    fs::create_dir_all(&output).map_err(|e| e.to_string())?;
    fs::write(output.join("initial.csv"), snapshot(&sim)?).map_err(|e| e.to_string())?;
    let failure = sim.advance_to(time).err();
    fs::write(output.join("final.csv"), snapshot(&sim)?).map_err(|e| e.to_string())?;
    let summary = format!(
        "{{\"completed\":{},\"time\":{:.17e},\"requested_time\":{time},\"steps\":{},\"n\":{n},\"jitter\":{jitter},\"velocity\":{:?},\"mesh_velocity\":{:?},\"model\":\"constant-flow-voronoi-v1\"}}\n",
        failure.is_none(),
        sim.time(),
        sim.steps(),
        velocity,
        mesh_velocity
    );
    fs::write(output.join("summary.json"), summary).map_err(|e| e.to_string())?;
    if let Some(e) = failure {
        fs::write(output.join("failure.txt"), &e).map_err(|e| e.to_string())?;
        return Err(e);
    }
    println!(
        "prescribed loop N={n}, jitter={jitter}: {} steps",
        sim.steps()
    );
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("error: {e}");
        std::process::exit(1);
    }
}
