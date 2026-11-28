//! Advance one 3D gas-generator step from a text catalog and emit CSV.
use moving_mesh::three_d::motion_io as motion_catalog;
use moving_mesh::three_d::*;
use std::error::Error;

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<_> = std::env::args().collect();
    let [_, file, dt, iterations, fraction] = args.as_slice() else {
        return Err("usage: lloyd3-step CATALOG DT ITERATIONS FRACTION|none".into());
    };
    let config = LloydConfig3 {
        iterations: iterations.parse()?,
        sound_speed_fraction: if fraction == "none" {
            None
        } else {
            Some(fraction.parse()?)
        },
    };
    let catalog = motion_catalog::read_catalog(file)?;
    let mesh = HalfSpaceOracle3::build(catalog.domain, &catalog.generators)?;
    let step = predict_lloyd_step3(&mesh, &catalog.flow, dt.parse()?, config)?;
    println!("id,x,y,z,ix,iy,iz,wx,wy,wz,volume,centroid_dx,centroid_dy,centroid_dz");
    for cell in step.geometry.cells() {
        let Generator3 {
            id,
            position: [x, y, z],
            winding: Image3([ix, iy, iz]),
        } = cell.generator;
        let [wx, wy, wz] = step.velocities[&id];
        let [dx, dy, dz] = cell.centroid_offset;
        println!(
            "{},{x:.17e},{y:.17e},{z:.17e},{ix},{iy},{iz},{wx:.17e},{wy:.17e},{wz:.17e},{:.17e},{dx:.17e},{dy:.17e},{dz:.17e}",
            id.entity(),
            cell.volume
        );
    }
    Ok(())
}
