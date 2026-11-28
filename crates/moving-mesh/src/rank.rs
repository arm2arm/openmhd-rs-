//! Spatial ownership and transport for periodic 2D Voronoi clipping.
use super::{Cell, Vec2};
use mhd_io::{Decoder, Encoder};
use mhd_parallel::{
    layout::Exchange,
    partition::{EntityId, Partition, Site},
};
use std::{collections::BTreeMap, num::NonZeroUsize};
pub fn cell_ranks(
    points: &[Vec2],
    lengths: Vec2,
    weights: impl Iterator<Item = u64>,
    ranks: NonZeroUsize,
) -> Result<Vec<usize>, String> {
    let sites: Vec<_> = points
        .iter()
        .zip(weights)
        .enumerate()
        .map(|(i, (p, weight))| Site {
            id: EntityId::new(0, i as u64),
            position: [
                p[0].rem_euclid(lengths[0]),
                p[1].rem_euclid(lengths[1]),
                0.5,
            ],
            weight,
        })
        .collect();
    if sites.len() != points.len() {
        return Err("missing partition weights".into());
    }
    let part = Partition::new(&sites, [0.; 3], [lengths[0], lengths[1], 1.], ranks)?;
    sites.iter().map(|s| part.owner(s.id)).collect()
}
type Edges = BTreeMap<(usize, usize, i32, i32), (f64, Vec2)>;
pub(super) fn clips(
    ranks: &dyn Exchange,
    owners: &[usize],
    compute: impl Fn(usize) -> Result<(Cell, Edges), String> + Sync + Send,
) -> Result<Vec<(Cell, Edges)>, String> {
    let buf = ranks.exchange(owners, &|i| {
        let (cell, edges) = compute(i)?;
        let mut e = Encoder::new();
        e.float(cell.volume);
        e.floats(&cell.centroid);
        e.usize(edges.len());
        for ((owner, other, x, y), (area, center)) in edges {
            if owner != i {
                return Err("incorrect clipped owner".into());
            }
            e.usize(other);
            e.i32(x);
            e.i32(y);
            e.float(area);
            e.floats(&center);
        }
        Ok(e.finish())
    })?;
    buf.iter()
        .enumerate()
        .map(|(i, b)| {
            let mut d = Decoder::new(b);
            let cell = Cell {
                volume: d.float()?,
                centroid: d.floats()?,
                faces: Vec::new(),
            };
            let count = d.count(40)?;
            let mut edges = Edges::new();
            for _ in 0..count {
                let j = d.usize()?;
                let x = d.i32()?;
                let y = d.i32()?;
                if j >= owners.len() || j == i || !(-1..=1).contains(&x) || !(-1..=1).contains(&y) {
                    return Err("invalid remote edge owner or image".into());
                }
                if edges
                    .insert((i, j, x, y), (d.float()?, d.floats()?))
                    .is_some()
                {
                    return Err("duplicate remote edge".into());
                }
            }
            d.finish()?;
            Ok((cell, edges))
        })
        .collect()
}
