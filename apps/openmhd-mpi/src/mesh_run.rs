use super::{MpiLayout, Result, save, shared_input};
use galaxy_types::CellId;
use mhd_parallel::{
    layout::Layout,
    partition::{Partition, Site},
};
use moving_mesh::three_d::{self, Domain3, Generator3, HalfSpaceOracle3, motion_io};
use std::{collections::BTreeMap, io::Write, path::Path};

pub fn partition(
    domain: Domain3,
    sites: &[Generator3],
    weights: &BTreeMap<CellId, u64>,
    layout: &impl Layout,
) -> Result<Partition> {
    let points = sites
        .iter()
        .map(|s| Site {
            id: s.id.entity(),
            position: s.position,
            weight: weights.get(&s.id).copied().unwrap_or(1),
        })
        .collect::<Vec<_>>();
    Ok(Partition::new(
        &points,
        domain.anchor,
        domain.width,
        layout.ranks(),
    )?)
}
/// Execute each rebuild once. Clipping counts from the previous rebuild weight the
/// next Morton partition, including each successive Lloyd predictor.
struct Builder<'a, 'world> {
    layout: &'a MpiLayout<'world>,
    reference: bool,
    lloyd: bool,
    weights: BTreeMap<CellId, u64>,
    receipt: Vec<(CellId, usize, u64)>,
}
impl Builder<'_, '_> {
    fn build(
        &mut self,
        domain: Domain3,
        sites: &[Generator3],
    ) -> Result<three_d::ValidatedGeometry3> {
        if self.reference {
            return Ok(if self.lloyd {
                HalfSpaceOracle3::build(domain, sites)?
            } else {
                HalfSpaceOracle3::build_motion_epoch(domain, sites)?
            });
        }
        let assign = partition(domain, sites, &self.weights, self.layout)?;
        let (g, work) = if self.lloyd {
            HalfSpaceOracle3::build_layout(domain, sites, &assign, self.layout)?
        } else {
            HalfSpaceOracle3::build_motion_layout(domain, sites, &assign, self.layout)?
        };
        self.receipt.clear();
        for (cell, cost) in g.cells().iter().zip(work) {
            let id = cell.generator.id;
            self.weights.insert(id, cost);
            self.receipt.push((id, assign.owner(id.entity())?, cost));
        }
        Ok(g)
    }
}
pub fn run(layout: &MpiLayout<'_>, args: &[String], mode: &str) -> Result<()> {
    let [file, out, steps @ ..] = args else {
        return Err("mesh|lloyd CATALOG OUTPUT_DIRECTORY DT [DT ...]".into());
    };
    if steps.is_empty() {
        return Err("provide at least one mesh timestep".into());
    }
    let reference = mode.ends_with("-reference");
    if reference && layout.ranks().get() != 1 {
        return Err("serial mesh requires one rank".into());
    }
    let lloyd = mode.starts_with("lloyd");
    let catalog = motion_io::parse_catalog(std::str::from_utf8(&shared_input(layout, file)?)?)?;
    let mut builder = Builder {
        layout,
        reference,
        lloyd,
        weights: BTreeMap::new(),
        receipt: Vec::new(),
    };
    let mut g = builder.build(catalog.domain, &catalog.generators)?;
    let dt = steps
        .iter()
        .map(|v| v.parse::<f64>())
        .collect::<std::result::Result<Vec<_>, _>>()?;
    let prescribed = catalog
        .flow
        .iter()
        .map(|(&id, gas)| (id, gas.velocity))
        .collect();
    let root = layout.rank() == 0;
    let mut data = Vec::new();
    let mut loads = Vec::new();
    if root {
        writeln!(data, "{}", motion_io::HEADER)?;
        writeln!(loads, "step,id,owner,clipping_predicates")?;
    }
    let mut time = 0.;
    for step in 0..=dt.len() {
        if root {
            motion_io::write_epoch(&mut data, step, time, &g)?;
            for &(id, owner, cost) in &builder.receipt {
                writeln!(loads, "{step},{},{owner},{cost}", id.entity())?;
            }
        }
        if let Some(&h) = dt.get(step) {
            if !((time + h).is_finite() && time + h > time) {
                return Err("invalid mesh clock".into());
            }
            g = if lloyd && reference {
                three_d::predict_lloyd_step3(
                    &g,
                    &catalog.flow,
                    h,
                    three_d::LloydConfig3::default(),
                )?
                .geometry
            } else if lloyd {
                three_d::predict_lloyd_with(
                    &g,
                    &catalog.flow,
                    h,
                    three_d::LloydConfig3::default(),
                    |d, s| {
                        builder
                            .build(d, s)
                            .map_err(|e| three_d::LloydError3::Layout(e.to_string()))
                    },
                )?
                .geometry
            } else {
                let sites = three_d::generator_endpoints3(&g, &prescribed, h)?;
                builder.build(catalog.domain, &sites)?
            };
            time += h;
        }
    }
    if root {
        let dir = Path::new(out);
        std::fs::create_dir(dir)?;
        save(dir, "mesh.csv", &data)?;
        save(dir, "ownership.csv", &loads)?;
    }
    Ok(())
}
