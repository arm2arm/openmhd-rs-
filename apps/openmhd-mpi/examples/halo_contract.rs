//! Collective regression controls. Run each selector under a real MPI launcher.
use mhd_parallel::{RankTeam, halo::HaloPlan, layout::Layout};
use mpi::{Threading, traits::*};
use openmhd_mpi::transport::MpiLayout;
use std::num::NonZeroUsize;

fn check(layout: &MpiLayout<'_>, selector: &str) -> Result<(), String> {
    let rank = layout.rank();
    let size = layout.ranks().get();
    if size < 4 {
        return Err("contract fixture requires at least four ranks".into());
    }
    // Rank 3 has no producers; row 3 has no consumers. Duplicate needs model images.
    let mut needs = vec![(0, 0), (0, 3), (0, 3), (1, 2), (2, 1), (2, 2)];
    if selector == "mismatch" && rank == 1 {
        needs.push((2, 3));
    }
    if selector == "range" {
        needs.push((0, size));
    }
    let owners = vec![2, 0, 1, 0];
    let plan = HaloPlan::new(owners.clone(), needs)?;
    let rows = layout.halo_rows("contract", &plan, |i| {
        if owners[i] != rank {
            return Err("wrong producer".into());
        }
        if selector == "producer-error" && (i == 1 || i == 2) {
            return Err(format!("failed owner {rank}"));
        }
        Ok([
            f64::from_bits(0x8000_0000_0000_0000),
            (i * 13 + rank) as f64,
        ])
    });
    let expected_error = match selector {
        "mismatch" => Some("MPI ranks disagree"),
        "range" => Some("outside communicator"),
        "producer-error" => Some("contract row 1: failed owner 0"),
        "routing" => None,
        _ => return Err("unknown contract selector".into()),
    };
    if let Some(expected) = expected_error {
        return match rows {
            Err(err) if err.contains(expected) => Ok(()),
            other => Err(format!("expected {expected}, got {other:?}")),
        };
    }
    let expected: &[usize] = match rank {
        0 => &[0],
        1 => &[2],
        2 => &[1, 2],
        3 => &[0],
        _ => &[],
    };
    let rows = rows?;
    if !rows.keys().copied().eq(expected.iter().copied()) {
        return Err("incorrect delivered keys".into());
    }
    for &i in expected {
        if rows[&i].map(f64::to_bits)
            != [(-0.0f64).to_bits(), ((i * 13 + owners[i]) as f64).to_bits()]
        {
            return Err("incorrect delivered words".into());
        }
    }
    let empty = HaloPlan::new(Vec::new(), [])?;
    if !layout
        .halo_rows::<1, _>("empty", &empty, |_| Err("empty producer ran".into()))?
        .is_empty()
    {
        return Err("empty exchange returned data".into());
    }
    Ok(())
}

fn main() {
    let (universe, support) =
        mpi::initialize_with_threading(Threading::Funneled).expect("MPI init");
    let world = universe.world();
    if support < Threading::Funneled {
        world.abort(2);
    }
    let args: Vec<_> = std::env::args().skip(1).collect();
    let [mode, selector] = args.as_slice() else {
        world.abort(2)
    };
    let layout = MpiLayout::new(
        &world,
        RankTeam::new(NonZeroUsize::MIN).expect("rank team"),
        mode == "sparse",
    );
    if let Err(e) = check(&layout, selector) {
        eprintln!("{e}");
        world.abort(1);
    }
    for r in 0..world.size() {
        if r == world.rank() {
            println!("verified {selector} {mode} rank={r}");
            layout.report_halos();
        }
        world.barrier();
    }
}
