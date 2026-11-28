//! The registered fixed/rigid iterative 2.5D solver, with selectable spatial execution.
use crate::{MpiLayout, Result, save, shared_input};
use mhd_core::RiemannSolver;
use mhd_parallel::layout::Layout;
use mhd_vector_pot::{
    benchmarks,
    general::{Config, Motion, Profile, Simulation},
    operators::PotentialLimiter,
};
use moving_mesh::Mesh;
use std::{io::Write, path::Path};

pub fn run(layout: &MpiLayout<'_>, args: &[String], mode: &str) -> Result<()> {
    let reference = mode.ends_with("-reference");
    if reference && layout.ranks().get() != 1 {
        return Err("the serial reference runs on one rank".into());
    }
    let (mut sim, target, out) = if mode == "mhd2-restart" {
        let [file, t, out] = args else {
            return Err("mhd2-restart CHECKPOINT FINAL_TIME DIRECTORY".into());
        };
        let bytes = shared_input(layout, file)?;
        let (sim, format) = Simulation::from_parallel_checkpoint(&bytes)?;
        if format != b"openmhd-mpi-mhd2-v1" {
            return Err("different MHD checkpoint identity".into());
        }
        (sim, t, out)
    } else {
        let [problem, nx, ny, jitter, t, out, boost @ ..] = args else {
            return Err(
                "mhd2 PROBLEM NX NY JITTER FINAL_TIME DIRECTORY [BOOST_X BOOST_Y BOOST_Z]".into(),
            );
        };
        let boost = match boost {
            [] => [0.; 3],
            [x, y, z] => [x.parse()?, y.parse()?, z.parse()?],
            _ => return Err("expected three boost components".into()),
        };
        let (lengths, mean, gamma) = match problem.as_str() {
            "alfven" => ([1., 1.], [1., 0., 0.], 5. / 3.),
            "loop" | "vortex" => ([1., 1.], [0.; 3], 5. / 3.),
            "brio" => ([2., 0.125], [0.75, 0., 0.], 2.),
            _ => return Err("expected alfven, loop, brio or vortex".into()),
        };
        let (nx, ny, jitter) = (nx.parse()?, ny.parse()?, jitter.parse()?);
        let mesh = if reference {
            Mesh::lattice(nx, ny, lengths, jitter)?
        } else {
            Mesh::lattice_on(nx, ny, lengths, jitter, layout)?
        };
        let config = if mode.starts_with("mhd2-deform") {
            let tau = std::f64::consts::TAU;
            let velocities = mesh
                .generators
                .iter()
                .map(|p| {
                    [
                        boost[0] + 0.1 * (tau * p[1] / lengths[1]).sin(),
                        boost[1] + 0.1 * (tau * p[0] / lengths[0]).cos(),
                    ]
                })
                .collect();
            Config {
                profile: Profile::BulkFrameV1,
                gamma,
                mean_magnetic: mean,
                motion: Motion::Prescribed(velocities),
                max_dt: 0.0005,
                ..Config::default()
            }
        } else {
            Config {
                profile: Profile::BulkFrameHeunQuadraticV1,
                riemann_solver: RiemannSolver::HlldPressure,
                gamma,
                mean_magnetic: mean,
                motion: Motion::Rigid([boost[0], boost[1]]),
                potential_limiter: Some(PotentialLimiter::SmoothExtrema),
                projection_screening: 1.,
                track_signal_travel: true,
                ..Config::default()
            }
        };
        let simulation = Simulation::new(mesh, config, |p| match problem.as_str() {
            "alfven" => benchmarks::alfven_initial(p, 0., boost),
            "loop" => benchmarks::loop_initial(p, boost),
            "brio" => benchmarks::brio_initial(p, boost),
            _ => benchmarks::vortex_initial(p, boost),
        })?;
        (simulation, t, out)
    };
    for time in target.split(',') {
        let time = time.parse::<f64>()?;
        if reference {
            sim.advance_to(time)?;
        } else {
            sim.advance_on(time, layout)?;
        }
    }
    let checkpoint = sim.parallel_checkpoint_bytes(b"openmhd-mpi-mhd2-v1")?;
    layout.agree(&checkpoint)?;
    if layout.rank() == 0 {
        let dir = Path::new(out);
        std::fs::create_dir(dir)?;
        let state = sim.state();
        let field = sim.magnetic_fit()?;
        let mut data = Vec::new();
        writeln!(
            data,
            "cell,x,y,volume,mass,px,py,pz,energy,ax,ay,az,phi,bx,by,bz"
        )?;
        for (i, c) in state.mesh.cells.iter().enumerate() {
            write!(data, "{i}")?;
            for v in state.mesh.generators[i]
                .into_iter()
                .chain([c.volume])
                .chain(state.conserved[i])
                .chain(state.potential[i])
                .chain([state.phi[i]])
                .chain(field.magnetic[i])
            {
                write!(data, ",{v:.17e}")?;
            }
            writeln!(data)?;
        }
        save(dir, "cells.csv", &data)?;
        save(dir, "checkpoint.bin", &checkpoint)?;
    }
    Ok(())
}
