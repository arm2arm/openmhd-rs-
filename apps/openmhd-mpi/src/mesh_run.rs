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
pub fn run(layout: &MpiLayout<'_>, args: &[String]) -> Result<()> {
    let [file, out, steps @ ..] = args else {
        return Err("mesh CATALOG OUTPUT_DIRECTORY DT [DT ...]".into());
    };
    if steps.is_empty() {
        return Err("provide at least one mesh timestep".into());
    }
    let catalog = motion_io::parse_catalog(std::str::from_utf8(&shared_input(layout, file)?)?)?;
    let mut sites = catalog.generators;
    let dt = steps
        .iter()
        .map(|v| v.parse::<f64>())
        .collect::<std::result::Result<Vec<_>, _>>()?;
    let w: BTreeMap<_, _> = catalog
        .flow
        .into_iter()
        .map(|(id, gas)| (id, gas.velocity))
        .collect();
    let root = layout.rank() == 0;
    let mut data = Vec::new();
    let mut loads = Vec::new();
    let mut weights = BTreeMap::new();
    if root {
        writeln!(data, "{}", motion_io::HEADER)?;
        writeln!(loads, "step,id,owner,clipping_predicates")?;
    }
    let mut time = 0.;
    for step in 0..=dt.len() {
        let assignment = partition(catalog.domain, &sites, &weights, layout)?;
        let (g, effort) =
            HalfSpaceOracle3::build_motion_layout(catalog.domain, &sites, &assignment, layout)?;
        if root {
            motion_io::write_epoch(&mut data, step, time, &g)?;
        }
        for (cell, cost) in g.cells().iter().zip(effort) {
            let id = cell.generator.id;
            weights.insert(id, cost);
            if root {
                writeln!(
                    loads,
                    "{step},{},{},{cost}",
                    id.entity(),
                    assignment.owner(id.entity())?
                )?;
            }
        }
        if let Some(&h) = dt.get(step) {
            sites = three_d::generator_endpoints3(&g, &w, h)?;
            if !((time + h).is_finite() && time + h > time) {
                return Err("invalid mesh clock".into());
            }
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
