//! Frozen Eq. (77) probe with a separately specified positive Laplacian.
use mhd_core::dot;
use mhd_vector_pot::{
    benchmarks::brio_initial,
    general::{Config, Profile, Simulation},
    operators::MagneticFit,
};
use moving_mesh::{Mesh, PositiveLaplacian};
use std::f64::consts::{PI, TAU};

fn main() -> Result<(), String> {
    println!(
        "case,n,jitter,mode,magnetic_energy_rate,target,original_pressure_rate,added_pressure_rate,moment_error"
    );
    for n in [256, 512] {
        for jitter in [0., 0.15] {
            let mesh = Mesh::lattice(n, 4, [2., 0.125], jitter)?;
            let sim = Simulation::new(
                mesh.clone(),
                Config {
                    profile: Profile::PaperStateEmfV1,
                    gamma: 2.,
                    mean_magnetic: [0.75, 0., 0.],
                    ..Config::default()
                },
                |x| brio_initial(x, [0.; 3]),
            )?;
            let q = sim.primitives()?;
            let a = &sim.state().potential;
            let lap = PositiveLaplacian::build(&mesh)?;
            let scalar: Vec<_> = a.iter().map(|a| a[2]).collect();
            let raw = lap.apply(&scalar)?;
            let rate: Vec<_> = raw
                .iter()
                .enumerate()
                .map(|(i, r)| {
                    [
                        0.,
                        0.,
                        0.2 * (dot(q[i].magnetic, q[i].magnetic) / q[i].density).sqrt()
                            * (mesh.cells[i].volume / PI).sqrt()
                            * r,
                    ]
                })
                .collect();
            let db =
                MagneticFit::build(&mesh, &rate, &vec![0.; rate.len()], [0.; 3], false)?.magnetic;
            let dm: Vec<_> = q.iter().zip(db).map(|(q, b)| dot(q.magnetic, b)).collect();
            let global: f64 = mesh.cells.iter().zip(&dm).map(|(c, m)| c.volume * m).sum();
            let target = if n == 256 { 253 } else { 510 };
            println!(
                "brio,{n},{jitter},0,{global:.17e},{target},{:.17e},{:.17e},{:.17e}",
                sim.energy_rates()?[target].pressure_rate,
                -dm[target],
                lap.max_moment_error
            );
            if global >= 0. {
                return Err("positive Laplacian fails frozen shock magnetic-energy check".into());
            }
        }
    }
    for jitter in [0., 0.15] {
        let mesh = Mesh::lattice(16, 16, [1.; 2], jitter)?;
        let lap = PositiveLaplacian::build(&mesh)?;
        for k in 1..=8 {
            let a: Vec<_> = mesh
                .cells
                .iter()
                .map(|c| [0., 0., (0.37 + TAU * k as f64 * c.centroid[0]).sin()])
                .collect();
            let scalar: Vec<_> = a.iter().map(|a| a[2]).collect();
            let rate: Vec<_> = lap
                .apply(&scalar)?
                .into_iter()
                .map(|r| [0., 0., r])
                .collect();
            let b = MagneticFit::build(&mesh, &a, &vec![0.; a.len()], [0.; 3], false)?.magnetic;
            let db = MagneticFit::build(&mesh, &rate, &vec![0.; a.len()], [0.; 3], false)?.magnetic;
            let energy: f64 = mesh
                .cells
                .iter()
                .zip(b)
                .zip(db)
                .map(|((c, b), db)| c.volume * dot(b, db))
                .sum();
            println!(
                "mode,16,{jitter},{k},{energy:.17e},0,0,0,{:.17e}",
                lap.max_moment_error
            );
            if k < 8 && energy >= 0. {
                return Err("positive Laplacian fails frozen modal magnetic-energy check".into());
            }
        }
    }
    Ok(())
}
