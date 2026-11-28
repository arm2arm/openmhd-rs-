//! Coupled ideal MHD on smooth prescribed periodic 3D Voronoi trajectories.
//! The finite-step reference supports a rigid translation or a non-crossing
//! product of moving planes. General deforming topology needs an event controller.
mod projection;
mod stage;
use crate::operators3::{MovingSharedFaceCurl3, SharedFaceCurl3};
use mhd_core::{Conservative, IdealGas, cross, dot};
use moving_mesh::three_d::{operator_mesh::CellId, sweeps::SharedSweeps3, *};
use projection::ScreenedCurl;
use stage::{CellFits, Closure};
use std::collections::BTreeMap;

pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;
fn axpy<const N: usize>(a: [f64; N], s: f64, b: [f64; N]) -> [f64; N] {
    std::array::from_fn(|k| a[k] + s * b[k])
}
fn add<const N: usize>(a: [f64; N], b: [f64; N]) -> [f64; N] {
    axpy(a, 1., b)
}
fn sub<const N: usize>(a: [f64; N], b: [f64; N]) -> [f64; N] {
    axpy(a, -1., b)
}

#[derive(Clone, Copy, Debug)]
pub struct Model3 {
    pub eos: IdealGas,
    pub mean_field: Vec3,
    pub reference_velocity: Vec3,
    /// Fixed positive initial magnetic scale for the 1e-9 configured-mean check.
    pub field_scale: f64,
}
#[derive(Clone, Copy, Debug)]
pub struct CellState3 {
    pub conserved: Conservative,
    pub potential: Vec3,
    pub phi: f64,
}
#[derive(Clone, Copy, Debug)]
pub struct SolveReport {
    pub iterations: usize,
    pub rhs_norm: f64,
    /// Relative for an active solve, absolute when the RHS is at or below 1e-30.
    pub true_residual: f64,
}
#[derive(Debug)]
pub struct StageReport3 {
    pub solve: SolveReport,
    pub max_gcl_residual: f64,
    pub auxiliary_intervals: usize,
    pub mean_field: Vec3,
    pub min_pressure: f64,
    pub min_density: f64,
    /// Cellwise S21: geometry, raw potential, screened correction. Code energy units.
    pub magnetic_transfers: Vec<[f64; 3]>,
    /// S14 finite-volume induction target on the rebuilt cells (separate from curl B).
    pub target_field: Vec<Vec3>,
    /// Corrected, time-integrated gas (5) and completed induction (3) exchanges.
    pub exchanges: BTreeMap<FaceKey3, [f64; 8]>,
}
#[derive(Debug)]
pub struct StepReport3 {
    pub predictor: StageReport3,
    pub corrector: StageReport3,
}

struct Epoch {
    support: SupportedGeometry3,
    rates: PrescribedPolygonRates3,
    op: MovingSharedFaceCurl3,
    screen: ScreenedCurl,
    fits: Vec<CellFits>,
}
impl Epoch {
    fn new(
        domain: Domain3,
        sites: &[Generator3],
        velocity: &BTreeMap<CellId, Vec3>,
    ) -> Result<Self> {
        let support = match HalfSpaceOracle3::try_supported_product(domain, sites)? {
            Some(product) => product,
            None => HalfSpaceOracle3::build_supported_periodic(domain, sites)?,
        };
        let rates = PrescribedPolygonRates3::build(&support, velocity)?;
        let op = MovingSharedFaceCurl3::assemble(&support, &rates)?;
        let screen = ScreenedCurl::new(op.field())?;
        let mesh = op.field().mesh();
        let fits = (0..mesh.cells().len())
            .map(|i| CellFits::build(mesh, i))
            .collect::<Result<_>>()?;
        Ok(Self {
            support,
            rates,
            op,
            screen,
            fits,
        })
    }
}
fn totals(state: &[CellState3]) -> Conservative {
    state.iter().fold([0.; 5], |sum, c| add(sum, c.conserved))
}

struct Rates {
    raw: Vec<Vec3>,
    chi: Vec<f64>,
    defect: Vec<Vec3>,
    face_flux: BTreeMap<FaceKey3, [f64; 8]>,
    averages: BTreeMap<CellId, [f64; 8]>,
    timestep_limit: f64,
}

/// If the sites are a Cartesian product and each plane has one axial speed,
/// squared-distance minimization separates into three cyclic 1D problems.
/// A lower bound on every adjacent spacing excludes interior face events.
fn smooth_path(g: &ValidatedGeometry3, w: &BTreeMap<CellId, Vec3>, dt: f64) -> Result<()> {
    if w.values().all(|v| v == w.first_key_value().unwrap().1) {
        return Ok(());
    }
    let mut product = 1_usize;
    for axis in 0..3 {
        let mut planes: Vec<_> = g
            .cells()
            .iter()
            .map(|c| (c.generator.position[axis], w[&c.generator.id][axis]))
            .collect();
        planes.sort_by(|a, b| a.0.total_cmp(&b.0));
        if planes
            .windows(2)
            .any(|p| p[0].0 == p[1].0 && p[0].1 != p[1].1)
        {
            return Err("nonseparable mesh motion requires event resolution".into());
        }
        planes.dedup_by(|a, b| a.0 == b.0);
        product = product
            .checked_mul(planes.len())
            .ok_or("plane count overflow")?;
        let width = g.domain().width[axis];
        for (i, &(x, u)) in planes.iter().enumerate() {
            let (y, v) = planes[(i + 1) % planes.len()];
            let gap = if i + 1 == planes.len() {
                (g.domain().anchor[axis] + width - x) + (y - g.domain().anchor[axis])
            } else {
                y - x
            };
            let shift = dt * (v - u);
            let margin =
                64. * f64::EPSILON * (width + x.abs() + y.abs() + dt * (u.abs() + v.abs()));
            if !shift.is_finite() || gap.min(gap + shift) <= margin {
                return Err("moving planes can meet inside timestep".into());
            }
        }
    }
    if product != g.cells().len() {
        return Err("irregular deformation requires event resolution".into());
    }
    Ok(())
}

/// The auxiliary grid uses a wrapped origin and a separate checked winding.
/// A trial moving it a full box along an axis must be subdivided.
#[derive(Clone, Copy, Debug)]
pub struct AuxiliaryOrigin3 {
    pub position: Vec3,
    pub winding: Image3,
}
impl AuxiliaryOrigin3 {
    fn shifted(self, domain: Domain3, velocity: Vec3, dt: f64) -> Result<Self> {
        let mut next = self;
        for (k, v) in velocity.into_iter().enumerate() {
            let width = domain.width[k];
            let lo = domain.anchor[k];
            let hi = lo + width;
            let d = v * dt;
            let x = self.position[k];
            if !d.is_finite() || d.abs() >= width {
                return Err("auxiliary shift requires a smaller timestep".into());
            }
            let (mut y, mut turns) = if d < 0. && -d > x - lo {
                (hi + ((x - lo) + d), -1_i64)
            } else if d > 0. && d >= hi - x {
                (lo + (d - (hi - x)), 1)
            } else {
                (x + d, 0)
            };
            if y == hi {
                y = lo;
                turns += 1;
            }
            next.position[k] = y;
            next.winding.0[k] = self.winding.0[k]
                .checked_add(turns)
                .ok_or("auxiliary origin winding overflow")?;
        }
        Ok(next)
    }
}

pub struct PeriodicMhd3 {
    model: Model3,
    epoch: Epoch,
    velocity: BTreeMap<CellId, Vec3>,
    state: Vec<CellState3>,
    closure: Closure,
    staged: Rates,
    initial_totals: Conservative,
    budget_scales: Conservative,
    time: f64,
    origin: AuxiliaryOrigin3,
    gauge_offset: Vec3,
}
impl PeriodicMhd3 {
    pub fn new(
        domain: Domain3,
        sites: &[Generator3],
        velocity: BTreeMap<CellId, Vec3>,
        model: Model3,
        initial: impl Fn(&CellGeometry3) -> Result<CellState3>,
    ) -> Result<Self> {
        if !model.field_scale.is_finite()
            || model.field_scale <= 0.
            || domain.boundary != Boundary3::Periodic
            || !model
                .mean_field
                .iter()
                .chain(&model.reference_velocity)
                .all(|x| x.is_finite())
        {
            return Err("periodic geometry and finite frame/mean are required".into());
        }
        let epoch = Epoch::new(domain, sites, &velocity)?;
        let state = epoch
            .support
            .geometry()
            .cells()
            .iter()
            .map(initial)
            .collect::<Result<Vec<_>>>()?;
        let origin = AuxiliaryOrigin3 {
            position: domain.anchor,
            winding: Image3::ZERO,
        };
        let closure = epoch.close(&model, &state, origin.position)?;
        let staged = epoch.rates(&state, &closure, &model, &velocity)?;
        let initial_totals = totals(&state);
        let momentum_scale =
            initial_totals[0] * (2. * initial_totals[4] / initial_totals[0]).sqrt();
        let budget_scales = [
            initial_totals[0],
            momentum_scale,
            momentum_scale,
            momentum_scale,
            initial_totals[4],
        ];
        if !budget_scales.iter().all(|x| x.is_finite() && *x > 0.) {
            return Err("invalid initial conservation scales".into());
        }
        Ok(Self {
            model,
            epoch,
            velocity,
            state,
            closure,
            staged,
            initial_totals,
            budget_scales,
            time: 0.,
            origin,
            gauge_offset: [0.; 3],
        })
    }
    pub fn geometry(&self) -> &ValidatedGeometry3 {
        self.epoch.support.geometry()
    }
    pub fn cells(&self) -> &[CellState3] {
        &self.state
    }
    pub fn field(&self) -> &[Vec3] {
        &self.closure.b
    }
    pub fn primitives(&self) -> &[mhd_core::Primitive] {
        &self.closure.gas
    }
    pub fn timestep_limit(&self) -> f64 {
        self.staged.timestep_limit
    }
    pub fn time(&self) -> f64 {
        self.time
    }
    pub fn origin(&self) -> AuxiliaryOrigin3 {
        self.origin
    }
    pub fn gauge_offset(&self) -> Vec3 {
        self.gauge_offset
    }

    /// S11–S14 on rebuilt endpoint geometry. All trial data are private until
    /// positive predictor/final closure and both screened solves succeed.
    pub fn step(&mut self, dt: f64) -> Result<StepReport3> {
        let end_time = self.time + dt;
        if !dt.is_finite() || !end_time.is_finite() || end_time <= self.time {
            return Err("invalid timestep".into());
        }
        let g = self.geometry();
        if dt > self.staged.timestep_limit {
            return Err("old-stage CFL exceeded".into());
        }
        let domain = g.domain();
        smooth_path(g, &self.velocity, dt)?;
        let sites = generator_endpoints3(g, &self.velocity, dt)?;
        let end = Epoch::new(domain, &sites, &self.velocity)?;
        if !g
            .faces()
            .iter()
            .map(|f| f.key)
            .eq(end.support.geometry().faces().iter().map(|f| f.key))
        {
            return Err("face keys changed on smooth path".into());
        }
        let old_fits = &self.epoch.op.field().fits;
        let end_fits = &end.op.field().fits;
        if !old_fits.iter().zip(end_fits).all(|(a, b)| {
            a.rings == b.rings
                && a.fit
                    .samples()
                    .iter()
                    .map(|s| s.key)
                    .eq(b.fit.samples().iter().map(|s| s.key))
        }) {
            return Err("quadratic fit support changed on smooth path".into());
        }
        let old = &self.staged;
        let old_motion = self.epoch.rates.cells_and_faces();
        let end_g = end.support.geometry();
        let predictor_sweep = SharedSweeps3::euler(g, old_motion, end_g, dt)?;
        let (zp, solve_p) = self.epoch.screen.correction(&old.defect, dt)?;
        let op1 = end.op.field();
        let ga: Vec<_> = self.state.iter().map(|s| s.potential).collect();
        let bg: Vec<_> = op1
            .apply(&ga)?
            .into_iter()
            .map(|v| add(v, self.model.mean_field))
            .collect();
        let advance = |new: Option<&Rates>,
                       sweep: SharedSweeps3,
                       correction: &[Vec3],
                       solve: SolveReport,
                       origin: AuxiliaryOrigin3|
         -> Result<_> {
            let integrated = old
                .face_flux
                .iter()
                .map(|(&k, &v)| {
                    let f = if let Some(next) = new {
                        add(v, next.face_flux[&k]).map(|x| 0.5 * x)
                    } else {
                        v
                    };
                    (k, f.map(|x| dt * x))
                })
                .collect();
            let exchange = sweep.exchanges(&integrated, &old.averages, new.map(|r| &r.averages))?;
            let mut trial = Vec::with_capacity(self.state.len());
            let mut raw_a = Vec::new();
            let mut target_field = Vec::new();
            for (i, (s, c)) in self.state.iter().zip(end_g.cells()).enumerate() {
                let delta = exchange.cell_increments[&c.generator.id];
                let (r, chi) = if let Some(next) = new {
                    (
                        add(old.raw[i], next.raw[i]).map(|x| 0.5 * x),
                        0.5 * (old.chi[i] + next.chi[i]),
                    )
                } else {
                    (old.raw[i], old.chi[i])
                };
                let raw = axpy(s.potential, dt, r);
                raw_a.push(raw);
                trial.push(CellState3 {
                    conserved: std::array::from_fn(|k| s.conserved[k] + delta[k]),
                    potential: add(raw, correction[i]),
                    phi: s.phi + dt * chi,
                });
                target_field.push(std::array::from_fn(|k| {
                    (g.cells()[i].volume * self.field()[i][k] + delta[k + 5]) / c.volume
                }));
            }
            let closed = end.close(&self.model, &trial, origin.position)?;
            if closed.auxiliary.intervals() != self.closure.auxiliary.intervals() {
                return Err("auxiliary root changed on smooth step".into());
            }
            if totals(&trial)
                .iter()
                .zip(self.initial_totals)
                .zip(self.budget_scales)
                .any(|((&v, initial), scale)| !v.is_finite() || (v - initial).abs() > 1e-10 * scale)
            {
                return Err("periodic gas budget exceeded".into());
            }
            let braw = op1.apply(&raw_a)?;
            let mut mean = [0.; 3];
            let mut vol = 0.;
            let transfers = end_g
                .cells()
                .iter()
                .enumerate()
                .map(|(i, c)| {
                    let eb = |b: Vec3| 0.5 * dot(b, b);
                    let raw = add(braw[i], self.model.mean_field);
                    mean = axpy(mean, c.volume, closed.b[i]);
                    vol += c.volume;
                    [
                        c.volume * eb(bg[i]) - g.cells()[i].volume * eb(self.field()[i]),
                        c.volume * (eb(raw) - eb(bg[i])),
                        c.volume * (eb(closed.b[i]) - eb(raw)),
                    ]
                })
                .collect::<Vec<_>>();
            if !transfers
                .iter()
                .flatten()
                .chain(target_field.iter().flatten())
                .chain(&mean)
                .all(|x| x.is_finite())
            {
                return Err("nonfinite field ledger".into());
            }
            let report = StageReport3 {
                solve,
                max_gcl_residual: sweep.max_corrected_relative_defect,
                auxiliary_intervals: closed.auxiliary.intervals(),
                mean_field: mean.map(|x| x / vol),
                min_pressure: closed
                    .gas
                    .iter()
                    .map(|q| q.pressure)
                    .fold(f64::INFINITY, f64::min),
                min_density: closed
                    .gas
                    .iter()
                    .map(|q| q.density)
                    .fold(f64::INFINITY, f64::min),
                magnetic_transfers: transfers,
                target_field,
                exchanges: exchange.faces,
            };
            Ok((trial, closed, report))
        };
        let op = self.origin.shifted(domain, self.closure.bulk, dt)?;
        let (trial, closure_p, predictor) = advance(None, predictor_sweep, &zp, solve_p, op)?;
        let predicted = end.rates(&trial, &closure_p, &self.model, &self.velocity)?;
        if dt > predicted.timestep_limit {
            return Err("predictor CFL exceeded".into());
        }
        let heun_sweep =
            SharedSweeps3::heun(g, old_motion, end_g, end.rates.cells_and_faces(), dt)?;
        let (mut zh, solve_h) = end.screen.correction(&predicted.defect, 0.5 * dt)?;
        for (v, p) in zh.iter_mut().zip(zp) {
            *v = axpy(*v, 0.5, p);
        }
        let origin = self.origin.shifted(
            domain,
            add(self.closure.bulk, closure_p.bulk).map(|x| 0.5 * x),
            dt,
        )?;
        let (state, closure, corrector) =
            advance(Some(&predicted), heun_sweep, &zh, solve_h, origin)?;
        let offset = axpy(
            self.gauge_offset,
            dt,
            cross(self.model.reference_velocity, self.model.mean_field),
        );
        if !offset.iter().all(|x| x.is_finite()) {
            return Err("nonfinite constant gauge offset".into());
        }
        let staged = end.rates(&state, &closure, &self.model, &self.velocity)?;
        if dt > staged.timestep_limit {
            return Err("corrector CFL exceeded".into());
        }
        self.staged = staged;
        self.time = end_time;
        self.epoch = end;
        self.state = state;
        self.closure = closure;
        self.origin = origin;
        self.gauge_offset = offset;
        Ok(StepReport3 {
            predictor,
            corrector,
        })
    }
}
