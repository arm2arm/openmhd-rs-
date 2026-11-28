use super::{Builder, CellId, Result, partition, three_d};
use mhd_parallel::{layout::Layout, partition::Partition};
use moving_mesh::three_d::{
    FaceKey3,
    sweeps::{SharedSweeps3, SweepExchange3},
};
use std::{collections::BTreeMap, io::Write};

impl Builder<'_, '_> {
    fn exchange(
        &self,
        sweep: &SharedSweeps3,
        owners: &Partition,
        physical: &BTreeMap<FaceKey3, [f64; 1]>,
        old: &BTreeMap<CellId, [f64; 1]>,
        predicted: Option<&BTreeMap<CellId, [f64; 1]>>,
    ) -> Result<Option<SweepExchange3<1>>> {
        if self.reference {
            return Ok(Some(sweep.exchanges(physical, old, predicted)?));
        }
        Ok(sweep.exchanges_to_root_on(physical, old, predicted, owners, self.layout)?)
    }

    pub(super) fn sweeps(
        &self,
        start: &three_d::ValidatedGeometry3,
        end: &three_d::ValidatedGeometry3,
        velocity: &BTreeMap<CellId, [f64; 3]>,
        dt: f64,
        index: usize,
        output: &mut [Vec<u8>; 3],
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
                    None => SharedSweeps3::euler(start, &old, end, dt)?,
                    Some(r) => SharedSweeps3::heun(start, &old, end, r, dt)?,
                }
            } else {
                SharedSweeps3::on_layout(start, &old, end, rates, dt, &owners, self.layout)?
            };
            // Feed the distributed stage only the rows actually held by this rank.
            let cell_state = |value: fn(usize) -> f64| -> Result<BTreeMap<_, _>> {
                let mut rows = BTreeMap::new();
                for (i, p) in points.iter().enumerate() {
                    if self.reference || owners.owner(p.id.entity())? == self.layout.rank() {
                        rows.insert(p.id, [value(i)]);
                    }
                }
                Ok(rows)
            };
            let uniform = cell_state(|_| 1.)?;
            let mut physical = BTreeMap::new();
            for (&key, f) in sweep.faces() {
                let left = match key {
                    FaceKey3::Interior { lo, .. } => lo,
                    FaceKey3::Boundary { cell, .. } => cell,
                };
                if self.reference || owners.owner(left.entity())? == self.layout.rank() {
                    physical.insert(key, [-f.raw]);
                }
            }
            let uniform_exchange = self.exchange(
                &sweep,
                &owners,
                &physical,
                &uniform,
                rates.map(|_| &uniform),
            )?;
            if self.tracer {
                let old = cell_state(|i| (i + 1) as f64 * 0.125)?;
                let predicted = cell_state(|i| 2. - (i + 1) as f64 * 0.0625)?;
                if let Some(x) =
                    self.exchange(&sweep, &owners, &physical, &old, rates.map(|_| &predicted))?
                {
                    for (kind, values) in [
                        ("face", x.faces.values().collect::<Vec<_>>()),
                        ("cell", x.cell_increments.values().collect()),
                    ] {
                        for (j, v) in values.iter().enumerate() {
                            writeln!(output[2], "{index},{rule},{kind},{j},{:.17e}", v[0])?;
                        }
                    }
                }
            }
            if let Some(exchanged) = uniform_exchange {
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
