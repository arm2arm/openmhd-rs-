//! Stream moving Voronoi cells and their outward polygon loops as CSV.
#[path = "support/motion_catalog.rs"]
mod motion_catalog;
use moving_mesh::three_d::*;
use std::collections::BTreeMap;
use std::error::Error;
use std::io::{self, Write};

fn write_epoch(
    out: &mut impl Write,
    step: usize,
    time: f64,
    mesh: &ValidatedGeometry3,
) -> Result<(), Box<dyn Error>> {
    for (i, cell) in mesh.cells().iter().enumerate() {
        let id = cell.generator.id.entity();
        let [x, y, z] = cell.generator.position;
        let [ix, iy, iz] = cell.generator.winding.0;
        for face in mesh.oriented_faces(mesh.cell_ref(i)?)? {
            let (peer, image) = face
                .incidence
                .neighbour
                .map(|(id, image)| (id.entity().to_string(), image))
                .unwrap_or_else(|| (String::new(), Image3::ZERO));
            let patch = match face.shared.key {
                FaceKey3::Boundary { patch, .. } => patch.0.to_string(),
                FaceKey3::Interior { .. } => String::new(),
            };
            let [jx, jy, jz] = image.0;
            let [nx, ny, nz] = face.outward_normal();
            let area = face.shared.area;
            let local = face.handle.index();
            let sign = face.incidence.sign;
            let volume = cell.volume;
            for (vertex, [dx, dy, dz]) in face.vertices().enumerate() {
                writeln!(
                    out,
                    "{step},{time:.17e},{id},{x:.17e},{y:.17e},{z:.17e},{ix},{iy},{iz},{volume:.17e},{local},{sign},{peer},{jx},{jy},{jz},{patch},{area:.17e},{nx:.17e},{ny:.17e},{nz:.17e},{vertex},{dx:.17e},{dy:.17e},{dz:.17e}"
                )?;
            }
        }
    }
    Ok(())
}

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    Ok(mhd_parallel::run_cli(&args, run)?)
}

fn run(args: &[String]) -> Result<(), Box<dyn Error>> {
    let [file, timesteps @ ..] = args else {
        return Err("usage: moving-voronoi3 [--threads N] CATALOG DT [DT ...]".into());
    };
    if timesteps.is_empty() {
        return Err("provide at least one positive timestep".into());
    }
    let mut steps = Vec::new();
    let mut time = 0.0;
    for arg in timesteps {
        let dt: f64 = arg.parse()?;
        let next = time + dt;
        if !dt.is_finite() || !next.is_finite() || next <= time {
            return Err("timestep must advance the finite simulation clock".into());
        }
        steps.push((next, dt));
        time = next;
    }
    let catalog = motion_catalog::read_catalog(file)?;
    let velocities: BTreeMap<_, _> = catalog
        .flow
        .into_iter()
        .map(|(id, gas)| (id, gas.velocity))
        .collect();
    let mut mesh = HalfSpaceOracle3::build_motion_epoch(catalog.domain, &catalog.generators)?;
    let mut out = io::BufWriter::new(io::stdout().lock());
    writeln!(
        out,
        "step,time,owner,x,y,z,ix,iy,iz,volume,face,sign,neighbour,jx,jy,jz,wall_patch,area,nx,ny,nz,vertex,dx,dy,dz"
    )?;
    write_epoch(&mut out, 0, 0.0, &mesh)?;
    for (i, (time, dt)) in steps.into_iter().enumerate() {
        let step = advance_generators3(&mesh, &velocities, dt)?;
        let mut kept = 0;
        let mut born = 0;
        let mut lost = 0;
        for change in step.face_changes.values() {
            match change {
                FaceChange3::Retained { .. } => kept += 1,
                FaceChange3::Appeared(_) => born += 1,
                FaceChange3::Disappeared(_) => lost += 1,
            }
        }
        mesh = step.geometry;
        write_epoch(&mut out, i + 1, time, &mesh)?;
        eprintln!(
            "step={} time={time:.17e} retained={kept} appeared={born} disappeared={lost}",
            i + 1
        );
    }
    out.flush()?;
    Ok(())
}
