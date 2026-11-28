//! Numerical records for the static and smooth-branch 3D operators.
use crate::{MpiLayout, Result};
use mhd_parallel::{layout::Layout, partition::Partition};
use mhd_vector_pot::{
    auxiliary3::{SmoothVelocity3, VelocitySample3},
    operators3::{MovingSharedFaceCurl3, SharedFaceCurl3},
};
use moving_mesh::three_d::{PrescribedPolygonRates3, SupportedGeometry3, ValidatedGeometry3, Vec3};
use std::{collections::BTreeMap, io::Write};

pub struct Fields<'a, 'w> {
    pub mesh: &'a ValidatedGeometry3,
    pub support: Option<&'a SupportedGeometry3>,
    pub partition: &'a Partition,
    pub layout: &'a MpiLayout<'w>,
    pub reference: bool,
}
impl Fields<'_, '_> {
    pub fn record(
        &self,
        op: &SharedFaceCurl3,
        a: &[Vec3],
        ca: &[Vec3],
        w: &[Vec3],
    ) -> Result<Vec<u8>> {
        let cells = self.mesh.cells();
        let test: Vec<_> = cells
            .iter()
            .enumerate()
            .map(|(i, _)| {
                [
                    ((13 * i + 3) % 23) as f64 / 16.,
                    ((7 * i + 9) % 29) as f64 / 16.,
                    ((19 * i + 2) % 31) as f64 / 16.,
                ]
            })
            .collect();
        let (adjoint, diagonal) = if self.reference {
            (op.transpose(&test)?, op.gram_diagonal()?)
        } else {
            (
                op.transpose_on(&test, self.partition, self.layout)?,
                op.gram_diagonal_on(self.partition, self.layout)?,
            )
        };
        let centers = op.mesh().cells();
        let samples: Vec<_> = centers
            .iter()
            .zip(w)
            .map(|(c, &v)| VelocitySample3 {
                id: c.id,
                position: c.centroid,
                volume: c.volume,
                velocity: v,
            })
            .collect();
        let d = self.mesh.domain();
        let auxiliary = self
            .layout
            .team
            .install(|| SmoothVelocity3::deposit(d.width, d.anchor, &samples, 4))?;
        let aux = |i: usize| -> std::result::Result<[f64; 12], String> {
            let local = auxiliary
                .sample(centers[i].centroid)
                .map_err(|e| e.to_string())?;
            Ok(std::array::from_fn(|k| {
                if k < 3 {
                    local.value[k]
                } else {
                    local.jacobian[(k - 3) / 3][(k - 3) % 3]
                }
            }))
        };
        let interpolation = if self.reference {
            (0..cells.len())
                .map(aux)
                .collect::<std::result::Result<Vec<_>, _>>()?
        } else {
            let owners = cells
                .iter()
                .map(|c| self.partition.owner(c.generator.id.entity()))
                .collect::<std::result::Result<Vec<_>, _>>()?;
            self.layout.rows(&owners, aux)?
        };
        let tangent = if let Some(s) = self.support {
            let velocity: BTreeMap<_, _> = cells
                .iter()
                .zip(w)
                .map(|(c, &v)| (c.generator.id, v))
                .collect();
            let m = self
                .layout
                .team
                .install(|| PrescribedPolygonRates3::build(s, &velocity))?;
            let derivative = self
                .layout
                .team
                .install(|| MovingSharedFaceCurl3::assemble(s, &m))?;
            let (forward, adjoint) = if self.reference {
                (
                    derivative.apply(s, &m, a)?,
                    derivative.transpose(s, &m, &test)?,
                )
            } else {
                (
                    derivative.apply_on(s, &m, a, self.partition, self.layout)?,
                    derivative.transpose_on(s, &m, &test, self.partition, self.layout)?,
                )
            };
            let vdot = (0..cells.len())
                .map(|i| {
                    Ok(m.cells_and_faces()
                        .cell(self.mesh.cell_ref(i)?)?
                        .volume_rate)
                })
                .collect::<Result<Vec<_>>>()?;
            Some((forward, adjoint, vdot))
        } else {
            None
        };
        let mut data = Vec::new();
        if self.layout.rank() == 0 {
            write!(
                data,
                "id,volume,ax,ay,az,cax,cay,caz,ux,uy,uz,ctux,ctuy,ctuz,gx,gy,gz,wx,wy,wz"
            )?;
            for i in 0..9 {
                write!(data, ",dw{i}")?;
            }
            if tangent.is_some() {
                write!(data, ",cdax,cday,cdaz,cdtux,cdtuy,cdtuz,vdot")?;
            }
            writeln!(data)?;
            for (i, c) in cells.iter().enumerate() {
                write!(data, "{},{}", c.generator.id.entity(), c.volume)?;
                for v in a[i]
                    .into_iter()
                    .chain(ca[i])
                    .chain(test[i])
                    .chain(adjoint[i])
                    .chain(diagonal[i])
                    .chain(interpolation[i])
                {
                    write!(data, ",{v:.17e}")?;
                }
                if let Some((direct, dual, dv)) = &tangent {
                    for v in direct[i].into_iter().chain(dual[i]).chain([dv[i]]) {
                        write!(data, ",{v:.17e}")?;
                    }
                }
                writeln!(data)?;
            }
        }
        Ok(data)
    }
}
