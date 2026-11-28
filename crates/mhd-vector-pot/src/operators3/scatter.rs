//! Ordered accumulation of sparse vector contributions from independent cells or faces.
use mhd_io::{Decoder, Encoder};
use moving_mesh::{
    parallel::{self, layout::Layout},
    three_d::{Vec3, fit::FitError3},
};
use std::num::NonZeroUsize;

pub(super) type Contributions = Vec<(usize, Vec3)>;

fn commit(out: &mut [Vec3], entries: Contributions) -> Result<(), FitError3> {
    for (j, value) in entries {
        let target = out.get_mut(j).ok_or(FitError3::InvalidSample)?;
        for (sum, term) in target.iter_mut().zip(value) {
            *sum += term;
        }
    }
    Ok(())
}

fn finish(out: Vec<Vec3>) -> Result<Vec<Vec3>, FitError3> {
    if out.iter().flatten().all(|v| v.is_finite()) {
        Ok(out)
    } else {
        Err(FitError3::NonFinite)
    }
}

pub(super) fn local(
    n: usize,
    jobs: usize,
    compute: impl Fn(usize) -> Result<Contributions, FitError3> + Sync + Send,
) -> Result<Vec<Vec3>, FitError3> {
    let mut out = vec![[0.; 3]; n];
    parallel::visit_ordered(
        jobs,
        NonZeroUsize::new(64).unwrap(),
        NonZeroUsize::MIN,
        compute,
        |_, result| commit(&mut out, result?),
    )?;
    finish(out)
}

pub(super) fn ranked<L: Layout>(
    n: usize,
    owners: &[usize],
    layout: &L,
    compute: impl Fn(usize) -> Result<Contributions, FitError3> + Sync + Send,
) -> Result<Vec<Vec3>, String> {
    let mut out = vec![[0.; 3]; n];
    for (window, ranks) in owners.chunks(64).enumerate() {
        let packets = layout.packets(ranks, |j| {
            let entries = compute(64 * window + j).map_err(|e| e.to_string())?;
            let mut e = Encoder::new();
            e.usize(entries.len());
            for (cell, v) in entries {
                e.usize(cell);
                e.floats(&v);
            }
            Ok(e.finish())
        })?;
        for packet in packets {
            let mut d = Decoder::new(&packet);
            let n = d.count(32)?;
            let mut entries = Vec::with_capacity(n);
            for _ in 0..n {
                entries.push((d.usize()?, d.floats()?));
            }
            d.finish()?;
            commit(&mut out, entries).map_err(|e| e.to_string())?;
        }
    }
    finish(out).map_err(|e| e.to_string())
}
