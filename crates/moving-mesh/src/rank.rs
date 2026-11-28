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
    mut weights: impl Iterator<Item = u64>,
    ranks: NonZeroUsize,
) -> Result<Vec<usize>, String> {
    let sites: Vec<_> = points
        .iter()
        .zip(&mut weights)
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
    if sites.len() != points.len() || weights.next().is_some() {
        return Err("expected one partition weight per cell".into());
    }
    let part = Partition::new(&sites, [0.; 3], [lengths[0], lengths[1], 1.], ranks)?;
    sites.iter().map(|s| part.owner(s.id)).collect()
}
/// Cell and face ownership for a fixed or rigid planar epoch. The Riemann solve
/// belongs to the smaller persistent generator ordinal. Self-image faces retain their index.
pub struct MeshRanks<'a> {
    pub exchange: &'a dyn Exchange,
    pub cells: Vec<usize>,
    pub faces: Vec<usize>,
}
impl<'a> MeshRanks<'a> {
    pub fn new(mesh: &super::Mesh, exchange: &'a dyn Exchange) -> Result<Self, String> {
        let cells = cell_ranks(
            &mesh.generators,
            mesh.lengths,
            mesh.cells.iter().map(|c| c.faces.len().max(1) as u64),
            exchange.rank_count(),
        )?;
        let faces = mesh
            .faces
            .iter()
            .map(|f| cells[f.left.min(f.right)])
            .collect();
        Ok(Self {
            exchange,
            cells,
            faces,
        })
    }
}
#[derive(Clone, Copy)]
pub enum Entities {
    Cells,
    Faces,
}
pub type RowResults<const N: usize> = Vec<Result<[f64; N], String>>;
/// Evaluate in parallel and retain per-index numerical errors so existing solvers
/// can account for successful fallback faces preceding a failed trial.
pub fn scheduled_rows<const N: usize>(
    count: usize,
    ranks: Option<&MeshRanks<'_>>,
    entities: Entities,
    compute: impl Fn(usize) -> Result<[f64; N], String> + Send + Sync,
) -> Result<RowResults<N>, String> {
    let Some(ranks) = ranks else {
        return Ok(mhd_parallel::map(count, compute));
    };
    let owners = match entities {
        Entities::Cells => &ranks.cells,
        Entities::Faces => &ranks.faces,
    };
    if owners.len() != count {
        return Err("row ownership belongs to a different mesh".into());
    }
    ranks
        .exchange
        .exchange(owners, &|i| {
            let mut e = Encoder::new();
            match compute(i) {
                Ok(v) => {
                    e.boolean(true);
                    e.floats(&v)
                }
                Err(reason) => {
                    e.boolean(false);
                    e.string(&reason)
                }
            }
            Ok(e.finish())
        })?
        .into_iter()
        .map(|body| {
            let mut d = Decoder::new(&body);
            let row = if d.boolean()? {
                Ok(d.floats()?)
            } else {
                Err(d.string()?)
            };
            d.finish()?;
            Ok(row)
        })
        .collect()
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
