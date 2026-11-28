//! Fixed/rigid 2.5D rank ownership. A generator's stable ordinal is its
//! persistent trajectory identity in the existing 2D mesh/checkpoint format.
use mhd_core::{FaceFlux, FluxMethod, Vec3};
use mhd_io::{Decoder, Encoder};
use moving_mesh::{Mesh, parallel::layout::Exchange};

type FaceSample = Result<(f64, FaceFlux, f64), String>;

pub(crate) struct StageLayout<'a> {
    pub(crate) exchange: &'a dyn Exchange,
    pub(crate) cells: Vec<usize>,
    faces: Vec<usize>,
}
impl<'a> StageLayout<'a> {
    pub(crate) fn new(mesh: &Mesh, exchange: &'a dyn Exchange) -> Result<Self, String> {
        let cells = moving_mesh::rank::cell_ranks(
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
    pub(crate) fn state_halo(&self, state: &super::State) -> Result<super::State, String> {
        let mut frame = Encoder::new();
        frame.floats(&state.auxiliary_origin);
        frame.floats(&state.gauge_offset);
        self.exchange.agree_bytes(&frame.finish())?;
        let rows = self.exchange.exchange(&self.cells, &|i| {
            let mut e = Encoder::new();
            e.floats(&state.mesh.generators[i]);
            e.floats(&state.conserved[i]);
            e.floats(&state.potential[i]);
            e.float(state.phi[i]);
            Ok(e.finish())
        })?;
        let mut halo = state.clone();
        for (i, row) in rows.iter().enumerate() {
            let mut d = Decoder::new(row);
            if d.floats::<2>()?.map(f64::to_bits) != state.mesh.generators[i].map(f64::to_bits) {
                return Err("gas halo is from a different generator epoch".into());
            }
            halo.conserved[i] = d.floats()?;
            halo.potential[i] = d.floats()?;
            halo.phi[i] = d.float()?;
            d.finish()?;
        }
        Ok(halo)
    }
    pub(crate) fn vectors(
        &self,
        compute: impl Fn(usize) -> Result<Vec3, String> + Sync + Send,
    ) -> Result<Vec<Vec3>, String> {
        self.exchange
            .exchange(&self.cells, &|i| {
                let mut e = Encoder::new();
                e.floats(&compute(i)?);
                Ok(e.finish())
            })?
            .iter()
            .map(|b| {
                let mut d = Decoder::new(b);
                let v = d.floats()?;
                d.finish()?;
                Ok(v)
            })
            .collect()
    }
    pub(super) fn fluxes(
        &self,
        compute: impl Fn(usize) -> FaceSample + Sync + Send,
    ) -> Result<Vec<FaceSample>, String> {
        // Keep scientific failures in their original face positions. The caller
        // still commits the successful prefix and records its HLL fallback count.
        let rows = self.exchange.exchange(&self.faces, &|i| {
            let mut e = Encoder::new();
            match compute(i) {
                Err(error) => {
                    e.boolean(false);
                    e.string(&error);
                }
                Ok((volume, f, speed)) => {
                    e.boolean(true);
                    e.float(volume);
                    e.float(speed);
                    e.floats(&f.fluid);
                    for v in [f.induction, f.electromotive, f.velocity, f.magnetic] {
                        e.floats(&v);
                    }
                    e.float(f.max_speed);
                    e.float(f.shock_factor);
                    let method = match f.method {
                        FluxMethod::Upwind => 0,
                        FluxMethod::Hlld => 1,
                        FluxMethod::HllFallback => 2,
                        FluxMethod::Hll => 3,
                        FluxMethod::HlldShock => 4,
                        FluxMethod::HlldPressure => 5,
                        FluxMethod::Rusanov => 6,
                    };
                    e.u64(method);
                }
            }
            Ok(e.finish())
        })?;
        rows.iter()
            .map(|b| {
                let mut d = Decoder::new(b);
                let row = if d.boolean()? {
                    let volume = d.float()?;
                    let signal = d.float()?;
                    let f = FaceFlux {
                        fluid: d.floats()?,
                        induction: d.floats()?,
                        electromotive: d.floats()?,
                        velocity: d.floats()?,
                        magnetic: d.floats()?,
                        max_speed: d.float()?,
                        shock_factor: d.float()?,
                        method: match d.u64()? {
                            0 => FluxMethod::Upwind,
                            1 => FluxMethod::Hlld,
                            2 => FluxMethod::HllFallback,
                            3 => FluxMethod::Hll,
                            4 => FluxMethod::HlldShock,
                            5 => FluxMethod::HlldPressure,
                            6 => FluxMethod::Rusanov,
                            _ => return Err("unknown Riemann flux method".into()),
                        },
                    };
                    Ok((volume, f, signal))
                } else {
                    Err(d.string()?)
                };
                d.finish()?;
                Ok(row)
            })
            .collect()
    }
}
