//! Evaluate shared-face magnetic reconstruction and extensive fluid rates at one supplied epoch.
use super::{MpiLayout, Result, mesh_run::partition, save, shared_input};
use galaxy_types::EntityId;
use mhd_core::{IdealGas, Primitive};
use mhd_parallel::layout::{Layout, LocalLayout};
use mhd_vector_pot::operators3::{SharedFaceCurl3, conservative_rates_on};
use moving_mesh::three_d::{HalfSpaceOracle3, motion_io, prescribed_motion_rates3};
use std::{collections::BTreeMap, io::Write, num::NonZeroUsize, path::Path};

pub fn run(layout: &MpiLayout<'_>, args: &[String], mode: &str) -> Result<()> {
    let [catalog, field, gamma, bx, by, bz, out] = args else {
        return Err("field3 CATALOG FIELD GAMMA MEAN_BX MEAN_BY MEAN_BZ DIRECTORY".into());
    };
    let reference = mode.ends_with("-reference");
    if reference && layout.ranks().get() != 1 {
        return Err("field reference requires one rank".into());
    }
    let catalog = motion_io::parse_catalog(std::str::from_utf8(&shared_input(layout, catalog)?)?)?;
    let input = shared_input(layout, field)?;
    let mut samples = BTreeMap::new();
    for line in std::str::from_utf8(&input)?.lines() {
        let line = line.split('#').next().unwrap().trim();
        if line.is_empty() {
            continue;
        }
        let tokens: Vec<_> = line.split_whitespace().collect();
        let [id, rho, x, y, z, p, ax, ay, az, phi, dt] = tokens.as_slice() else {
            return Err("expected ID density vx vy vz pressure Ax Ay Az phi local_dt".into());
        };
        let row: [f64; 10] = [rho, x, y, z, p, ax, ay, az, phi, dt]
            .map(|v| v.parse())
            .into_iter()
            .collect::<std::result::Result<Vec<_>, _>>()?
            .try_into()
            .unwrap();
        if row.iter().any(|v| !v.is_finite())
            || row[9] <= 0.
            || samples.insert(id.parse::<EntityId>()?, row).is_some()
        {
            return Err("invalid or duplicate field sample".into());
        }
    }
    let model = IdealGas::new(gamma.parse()?)?;
    let harmonic: [f64; 3] = [bx.parse()?, by.parse()?, bz.parse()?];
    let part = partition(
        catalog.domain,
        &catalog.generators,
        &BTreeMap::new(),
        layout,
    )?;
    let regular;
    let supported;
    let (mesh, support) = if mode.contains("-tangent") {
        supported = if reference {
            HalfSpaceOracle3::build_supported_periodic(catalog.domain, &catalog.generators)?
        } else {
            HalfSpaceOracle3::build_supported_layout(
                catalog.domain,
                &catalog.generators,
                &part,
                layout,
            )?
            .0
        };
        (supported.geometry(), Some(&supported))
    } else {
        regular = if reference {
            HalfSpaceOracle3::build_motion_epoch(catalog.domain, &catalog.generators)?
        } else {
            HalfSpaceOracle3::build_motion_layout(
                catalog.domain,
                &catalog.generators,
                &part,
                layout,
            )?
            .0
        };
        (&regular, None)
    };
    if mesh.cells().len() != samples.len() {
        return Err("field catalog length".into());
    }
    let ordered = mesh
        .cells()
        .iter()
        .map(|c| {
            samples
                .get(&c.generator.id.entity())
                .copied()
                .ok_or("missing field ID")
        })
        .collect::<std::result::Result<Vec<_>, _>>()?;
    let owners = mesh
        .cells()
        .iter()
        .map(|c| part.owner(c.generator.id.entity()))
        .collect::<std::result::Result<Vec<_>, _>>()?;
    // Exchange all authoritative material variables, cleaning potential and local step by owner.
    let fields = if reference {
        ordered
    } else {
        layout.rows(&owners, |i| Ok(ordered[i]))?
    };
    let a = fields
        .iter()
        .map(|r| [r[5], r[6], r[7]])
        .collect::<Vec<_>>();
    let op = layout
        .team
        .install(|| SharedFaceCurl3::from_validated(mesh))
        .map_err(|e| format!("{e:?}"))?;
    let fluctuation = if reference {
        op.apply(&a).map_err(|e| format!("{e:?}"))?
    } else {
        op.apply_on(&a, &part, layout)?
    };
    let q = fields
        .iter()
        .zip(&fluctuation)
        .map(|(r, b)| Primitive {
            density: r[0],
            velocity: [r[1], r[2], r[3]],
            pressure: r[4],
            magnetic: std::array::from_fn(|k| harmonic[k] + b[k]),
        })
        .collect::<Vec<_>>();
    let velocities = catalog
        .flow
        .iter()
        .map(|(&id, gas)| (id, gas.velocity))
        .collect::<BTreeMap<_, _>>();
    let motion = layout
        .team
        .install(|| prescribed_motion_rates3(mesh, &velocities, [0.; 3]))?;
    let velocity = velocities.values().copied().collect::<Vec<_>>();
    let rate = if reference {
        conservative_rates_on(
            mesh,
            &motion,
            &q,
            &velocity,
            model,
            &part,
            &LocalLayout(NonZeroUsize::MIN),
        )?
    } else {
        conservative_rates_on(mesh, &motion, &q, &velocity, model, &part, layout)?
    };
    let operators = crate::field_analysis::Fields {
        mesh,
        support,
        partition: &part,
        layout,
        reference,
    }
    .record(&op, &a, &fluctuation, &velocity)?;
    let points = if mode.contains("-points") {
        Some(
            crate::point3::PointFields {
                geometry: mesh,
                motion: &motion,
                owners: &owners,
                potential: &a,
                mean: harmonic,
            }
            .record(layout, reference)?,
        )
    } else {
        None
    };
    if layout.rank() == 0 {
        let mut bytes = Vec::new();
        writeln!(bytes, "id,volume,bx,by,bz,dm,dpx,dpy,dpz,de")?;
        for ((c, q), v) in mesh.cells().iter().zip(q).zip(rate) {
            write!(bytes, "{}", c.generator.id.entity())?;
            for x in [c.volume].into_iter().chain(q.magnetic).chain(v) {
                write!(bytes, ",{x:.17e}")?;
            }
            writeln!(bytes)?;
        }
        let dir = Path::new(out);
        std::fs::create_dir(dir)?;
        save(dir, "rates.csv", &bytes)?;
        save(dir, "field-operators.csv", &operators)?;
        if let Some(points) = points {
            save(dir, "point-operators.csv", &points)?;
        }
    }
    Ok(())
}
