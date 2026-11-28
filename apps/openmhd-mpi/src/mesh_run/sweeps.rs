use super::{Builder, CellId, Result, partition, three_d};
use mhd_parallel::layout::Layout;
use std::{collections::BTreeMap, io::Write};

impl Builder<'_, '_> {
    pub(super) fn sweeps(
        &self,
        start: &three_d::ValidatedGeometry3,
        end: &three_d::ValidatedGeometry3,
        velocity: &BTreeMap<CellId, [f64; 3]>,
        dt: f64,
        index: usize,
        output: &mut [Vec<u8>; 2],
    ) -> Result<()> {
        let motion = |g: &three_d::ValidatedGeometry3| {
            three_d::prescribed_motion_rates3(g, velocity, [0.; 3])
        };
        let (old, new) = if self.reference {
            (motion(start)?, motion(end)?)
        } else {
            (
                self.layout.team.install(|| motion(start))?,
                self.layout.team.install(|| motion(end))?,
            )
        };
        let points = start
            .cells()
            .iter()
            .map(|c| c.generator)
            .collect::<Vec<_>>();
        let owners = partition(start.domain(), &points, &self.weights, self.layout)?;
        for (rule, rates) in [("euler", None), ("heun", Some(&new))] {
            let sweep = if self.reference {
                match rates {
                    None => three_d::SharedSweeps3::euler(start, &old, end, dt)?,
                    Some(r) => three_d::SharedSweeps3::heun(start, &old, end, r, dt)?,
                }
            } else {
                three_d::SharedSweeps3::on_layout(
                    start,
                    &old,
                    end,
                    rates,
                    dt,
                    &owners,
                    self.layout,
                )?
            };
            if self.layout.rank() == 0 {
                let uniform = points.iter().map(|p| (p.id, [1.])).collect();
                let physical = sweep.faces().iter().map(|(&k, f)| (k, [-f.raw])).collect();
                let exchanged = sweep.exchanges(&physical, &uniform, rates.map(|_| &uniform))?;
                for (i, (&k, f)) in sweep.faces().iter().enumerate() {
                    writeln!(
                        output[0],
                        "{index},{rule},{i},\"{k:?}\",{:.17e},{:.17e},{:.17e},{:.17e}",
                        f.raw, f.correction, f.weight, exchanged.faces[&k][0]
                    )?;
                }
                for (a, b) in start.cells().iter().zip(end.cells()) {
                    let id = a.generator.id;
                    writeln!(
                        output[1],
                        "{index},{rule},{},{:.17e},{:.17e},{:.17e},{:.17e}",
                        id.entity(),
                        a.volume,
                        b.volume,
                        exchanged.cell_increments[&id][0],
                        sweep.max_corrected_relative_defect
                    )?;
                }
            }
        }
        Ok(())
    }
}
