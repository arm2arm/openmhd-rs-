//! Single-node or inter-node MPI processes with explicitly sized within-rank Rayon teams.
mod field3;
mod gravity_run;
mod mesh_run;
mod mhd2;
mod transport;
use mhd_parallel::layout::Layout;
use mpi::{Threading, traits::*};
use std::{error::Error, num::NonZeroUsize, path::Path, time::Instant};
use transport::MpiLayout;
type Result<T> = std::result::Result<T, Box<dyn Error>>;

fn shared_input(layout: &MpiLayout<'_>, file: &str) -> Result<Vec<u8>> {
    Ok(layout
        .packets(&[0], |_| {
            std::fs::read(file).map_err(|e| format!("read {file}: {e}"))
        })?
        .pop()
        .ok_or("empty input broadcast")?)
}
fn options(layout: &MpiLayout<'_>, args: &[String]) -> Result<()> {
    let (mode, parts) = args
        .split_first()
        .ok_or("specify mesh, gravity or gravity-restart")?;
    match mode.as_str() {
        "mhd2" | "mhd2-restart" | "mhd2-reference" => mhd2::run(layout, parts, mode),
        "field3" | "field3-reference" => field3::run(layout, parts, mode == "field3-reference"),
        "mesh" | "mesh-reference" | "lloyd" | "lloyd-reference" => {
            mesh_run::run(layout, parts, mode)
        }
        "gravity" | "gravity-reference" | "gravity-restart" => {
            gravity_run::run(layout, parts, mode)
        }
        _ => Err(format!("unknown MPI driver {mode}").into()),
    }
}
fn save(directory: &Path, name: &str, bytes: &[u8]) -> Result<()> {
    mhd_io::write_atomic(&directory.join(name), bytes)?;
    Ok(())
}
fn main() {
    let Some((universe, support)) = mpi::initialize_with_threading(Threading::Funneled) else {
        eprintln!("MPI could not initialize");
        std::process::exit(2);
    };
    let world = universe.world();
    if support < Threading::Funneled {
        eprintln!("MPI does not supply MPI_THREAD_FUNNELED");
        world.abort(2);
    }
    let start = Instant::now();
    let args: Vec<String> = std::env::args().skip(1).collect();
    let Some((threads, rest)) = args
        .split_first()
        .and_then(|(n, args)| n.parse::<NonZeroUsize>().ok().map(|n| (n, args)))
    else {
        if world.rank() == 0 {
            eprintln!("usage: openmhd-mpi THREADS_PER_RANK mesh|gravity|gravity-restart ...");
        }
        world.abort(2)
    };
    let team = mhd_parallel::RankTeam::new(threads).unwrap_or_else(|e| {
        eprintln!("rank {} could not start its thread pool: {e}", world.rank());
        world.abort(2)
    });
    let layout = MpiLayout::new(&world, team);
    let mut command = mhd_io::Encoder::new();
    for arg in &args {
        command.string(arg);
    }
    let result = layout
        .agree(&command.finish())
        .map_err(Into::into)
        .and_then(|()| options(&layout, rest));
    if let Err(e) = result {
        eprintln!("rank {}: {e}", world.rank());
        world.abort(1);
    }
    let line = format!(
        "openmhd-mpi rank={} ranks={} threads={} work_items={} halo_bytes_received={} exchange_seconds={:.9} total_seconds={:.9}",
        world.rank(),
        world.size(),
        threads,
        layout.work.get(),
        layout.bytes_received.get(),
        layout.exchange_seconds.get(),
        start.elapsed().as_secs_f64()
    );
    // Hydra and other launchers can interleave writes from different ranks.
    // Emit one complete record per process, after the measured scientific work.
    for rank in 0..world.size() {
        if world.rank() == rank {
            eprintln!("{line}");
        }
        world.barrier();
    }
}
