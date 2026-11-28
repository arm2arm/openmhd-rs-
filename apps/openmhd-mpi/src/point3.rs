//! Cell-owned point reconstruction and independent diagnostics on one periodic epoch.
use crate::{MpiLayout, Result};
use mhd_io::{Decoder, Encoder};
use mhd_parallel::layout::Layout;
use mhd_vector_pot::operators3::{
    MovingPointCurl3, curvature_corrected_field, independent_divergence, recover,
    skew_face_divergence, trace,
};
use moving_mesh::three_d::{
    MotionRates3, ValidatedGeometry3, Vec3,
    fit::{FitError3, FitOrder3},
    operator_mesh::{MeshFit3, OperatorMesh3},
};
use std::{io::Write, num::NonZeroUsize};

fn reconstruct(
    mesh: &OperatorMesh3,
    linear: &MeshFit3,
    i: usize,
    a: &[Vec3],
    mean: Vec3,
) -> std::result::Result<[f64; 12], FitError3> {
    let samples = |fit: &MeshFit3| fit.owners.iter().map(|&j| a[j]).collect::<Vec<_>>();
    let linear_values = samples(linear);
    let low = recover(&linear.fit, &linear_values, mean)?;
    let fit = mesh.fit(i, FitOrder3::Quadratic)?;
    let high = recover(&fit.fit, &samples(&fit), mean)?;
    let corrected = curvature_corrected_field(&linear.fit, &linear_values, &high, mean)?;
    let div_curl = trace(high.same_fit_jacobian.ok_or(FitError3::InvalidSample)?);
    let [lx, ly, lz] = low.field;
    let [qx, qy, qz] = high.field;
    let [cx, cy, cz] = corrected;
    Ok([
        lx, ly, lz, low.div_a, qx, qy, qz, high.div_a, div_curl, cx, cy, cz,
    ])
}

/// Each operation owns its ordered accumulation. Exchanging finished columns
/// lets the existing library supply exactly the same stencils and signed sums.
fn operations<const N: usize>(
    layout: &MpiLayout<'_>,
    reference: bool,
    count: usize,
    cells: usize,
    evaluate: impl Fn(usize) -> std::result::Result<Vec<[f64; N]>, FitError3> + Send + Sync,
) -> Result<Vec<Vec<[f64; N]>>> {
    if reference {
        return Ok((0..count)
            .map(evaluate)
            .collect::<std::result::Result<_, _>>()?);
    }
    let owners: Vec<_> = (0..count).map(|i| i % layout.ranks().get()).collect();
    let packets = layout.packets(&owners, |i| {
        let rows = evaluate(i).map_err(|e| e.to_string())?;
        let mut e = Encoder::new();
        e.usize(rows.len());
        for row in rows {
            e.floats(&row);
        }
        Ok(e.finish())
    })?;
    let mut profiles = Vec::with_capacity(count);
    for packet in packets {
        let mut d = Decoder::new(&packet);
        if d.count(8 * N)? != cells {
            return Err("point operator returned a different cell count".into());
        }
        let rows = (0..cells)
            .map(|_| d.floats())
            .collect::<std::result::Result<_, _>>()?;
        d.finish()?;
        profiles.push(rows);
    }
    Ok(profiles)
}

pub struct PointFields<'a> {
    pub geometry: &'a ValidatedGeometry3,
    pub motion: &'a MotionRates3,
    pub owners: &'a [usize],
    pub potential: &'a [Vec3],
    pub mean: Vec3,
}

impl PointFields<'_> {
    pub fn record(&self, layout: &MpiLayout<'_>, reference: bool) -> Result<Vec<u8>> {
        let mesh = OperatorMesh3::from_validated(self.geometry)?;
        let n = mesh.cells().len();
        let linear = layout
            .team
            .install(|| {
                moving_mesh::parallel::map_indexed(n, NonZeroUsize::MIN, |i| {
                    mesh.fit(i, FitOrder3::Linear)
                })
            })
            .into_iter()
            .collect::<std::result::Result<Vec<_>, _>>()?;
        let point = |i: usize| reconstruct(&mesh, &linear[i], i, self.potential, self.mean);
        let jets: Vec<_> = if reference {
            (0..n).map(point).collect::<std::result::Result<_, _>>()?
        } else {
            layout.rows(self.owners, |i| point(i).map_err(|e| e.to_string()))?
        };

        let divergences = operations(layout, reference, 3, n, |profile| {
            let offset = [0, 4, 9][profile];
            let field: Vec<Vec3> = jets
                .iter()
                .map(|r| [r[offset], r[offset + 1], r[offset + 2]])
                .collect();
            let div = independent_divergence(&mesh, &field, &linear)?;
            let skew = skew_face_divergence(&mesh, &field, &linear)?;
            Ok((0..n)
                .map(|i| {
                    [
                        div.cell_ls[i],
                        div.face_mean[i],
                        div.face_limited[i],
                        skew[i],
                    ]
                })
                .collect())
        })?;
        let moving = layout
            .team
            .install(|| MovingPointCurl3::assemble(self.geometry, self.motion))?;
        let (curl, tangent) = moving.operators(self.geometry, self.motion)?;
        let volumes: Vec<_> = mesh.cells().iter().map(|c| c.volume).collect();
        let dual: Vec<Vec3> = (0..n)
            .map(|i| std::array::from_fn(|k| (((7 * i + 11 * k + 1) % 23) as f64 - 11.) / 16.))
            .collect();
        let maps = operations(layout, reference, 6, n, |task| {
            let op = [curl, tangent][task / 3];
            match task % 3 {
                0 => op.apply(self.potential),
                1 => op.transpose(&dual),
                _ => op.gram_diagonal(&volumes),
            }
        })?;

        let mut bytes = Vec::new();
        if layout.rank() == 0 {
            write!(
                bytes,
                "id,linear_bx,linear_by,linear_bz,linear_div_a,quadratic_bx,quadratic_by,quadratic_bz,quadratic_div_a,same_fit_div_b,corrected_bx,corrected_by,corrected_bz"
            )?;
            for profile in ["linear", "quadratic", "corrected"] {
                for method in ["cell_ls", "face_mean", "face_limited", "skew"] {
                    write!(bytes, ",{profile}_{method}")?;
                }
            }
            for v in ["a", "u", "ca", "ctu", "gram", "cda", "cdtu", "dgram"] {
                for k in ["x", "y", "z"] {
                    write!(bytes, ",{v}{k}")?;
                }
            }
            writeln!(bytes)?;
            for (i, c) in mesh.cells().iter().enumerate() {
                write!(bytes, "{}", c.id.entity())?;
                for x in jets[i]
                    .into_iter()
                    .chain(divergences.iter().flat_map(|d| d[i]))
                    .chain(self.potential[i])
                    .chain(dual[i])
                    .chain(maps.iter().flat_map(|v| v[i]))
                {
                    write!(bytes, ",{x:.17e}")?;
                }
                writeln!(bytes)?;
            }
        }
        Ok(bytes)
    }
}
