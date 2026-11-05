//! Serial periodic 2.5D coupled reference with explicitly named gauge profiles.
//! See docs/VECTOR_POTENTIAL_REFERENCE.md for sources, engineering choices and gates.
use crate::auxiliary::{SmoothVelocity, VelocitySample};
use crate::gauge::{Cleaning, CleaningStage};
use crate::operators::{
    MagneticFit, PotentialStage, PrimitiveGradient, components, face_velocity, gradients, predict,
};
use mhd_core::{
    Conservative, FaceCompletion, FaceFlux, FluxMethod, IdealGas, Primitive, Vec3, cross,
    riemann_with_completion,
};
use moving_mesh::{Derivatives, Mesh, Vec2, dot, quadratic::Quadratic};
use std::{f64::consts::PI, sync::Arc};

#[derive(Clone, Debug)]
pub enum Motion {
    Fixed,
    Rigid(Vec2),
    Fluid,
    /// Persistent cell IDs; velocities held fixed throughout each attempted step.
    Prescribed(Vec<Vec2>),
}
/// Named algorithms: the original paper profile remains the default.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Profile {
    #[default]
    PaperGlobalV2,
    /// Explicit gauge psi=u dot a with A=a+C, Cdot=Vref cross mean_B.
    BulkFrameV1,
    /// Bulk-frame gauge with continuous symmetric-fan A-face completion.
    BulkFrameHllV1,
    /// Optional quadratic A reconstruction; all other completion/stage choices retained.
    BulkFrameHllQuadraticV1,
    /// Quadratic A fit with affine-exact source and quadratic-consistent advection.
    BulkFrameHllConsistentV1,
    /// Consistent-rate profile with the same quadratic derivative for phi and A.
    BulkFrameHllMatchedV1,
}
impl Profile {
    pub fn name(self) -> &'static str {
        match self {
            Self::PaperGlobalV2 => "paper-global-v2",
            Self::BulkFrameV1 => "bulk-frame-v1",
            Self::BulkFrameHllV1 => "bulk-frame-hll-v1",
            Self::BulkFrameHllQuadraticV1 => "bulk-frame-hll-quadratic-v1",
            Self::BulkFrameHllConsistentV1 => "bulk-frame-hll-consistent-v1",
            Self::BulkFrameHllMatchedV1 => "bulk-frame-hll-matched-v1",
        }
    }
    fn quadratic(self) -> bool {
        matches!(
            self,
            Self::BulkFrameHllQuadraticV1
                | Self::BulkFrameHllConsistentV1
                | Self::BulkFrameHllMatchedV1
        )
    }
    fn consistent(self) -> bool {
        matches!(
            self,
            Self::BulkFrameHllConsistentV1 | Self::BulkFrameHllMatchedV1
        )
    }
    fn matched(self) -> bool {
        self == Self::BulkFrameHllMatchedV1
    }
    fn completion(self) -> FaceCompletion {
        match self {
            Self::BulkFrameHllV1
            | Self::BulkFrameHllQuadraticV1
            | Self::BulkFrameHllConsistentV1
            | Self::BulkFrameHllMatchedV1 => FaceCompletion::SymmetricHll,
            _ => FaceCompletion::RiemannState,
        }
    }
}
#[derive(Clone, Debug)]
pub struct Config {
    pub profile: Profile,
    pub gamma: f64,
    pub mean_magnetic: Vec3,
    pub motion: Motion,
    pub cfl: f64,
    pub max_dt: f64,
    pub limited: bool,
    /// Fixed initial field scale for dimensionless divergence diagnostics.
    pub magnetic_scale: f64,
}
impl Default for Config {
    fn default() -> Self {
        Self {
            profile: Profile::PaperGlobalV2,
            gamma: 5. / 3.,
            mean_magnetic: [0.; 3],
            motion: Motion::Fixed,
            cfl: 0.3,
            max_dt: f64::INFINITY,
            limited: true,
            magnetic_scale: 1.,
        }
    }
}
#[derive(Clone, Copy, Debug)]
pub struct Initial {
    pub density: f64,
    pub pressure: f64,
    pub velocity: Vec3,
    pub potential: Vec3,
    pub phi: f64,
}
#[derive(Clone, Debug)]
pub struct State {
    pub mesh: Mesh,
    /// Reduced a; total periodic potential is a + gauge_offset. V2 offset is zero.
    pub potential: Vec<Vec3>,
    pub gauge_offset: Vec3,
    pub phi: Vec<f64>,
    /// Cell-integrated (mass, momentum3, total energy); never a density here.
    pub conserved: Vec<Conservative>,
    pub auxiliary_origin: Vec2,
}
#[derive(Clone, Debug, Default)]
pub struct Counters {
    pub steps: usize,
    pub rejected_geometry: usize,
    pub rejected_state: usize,
    pub rejected_cfl: usize,
    /// Successful HLL face results used by accepted stages.
    pub hll_fallbacks: usize,
    /// All successful HLL results, including discarded/partially failed sweeps.
    pub hll_fallbacks_attempted: usize,
    pub auxiliary_coarsenings: usize,
    pub auxiliary_roots: Vec<usize>,
    pub min_dt: Option<f64>,
    pub max_dt: f64,
    /// Maximum x-characteristic speed in accepted old/predicted/closed cell states.
    pub max_signal_x: f64,
    /// Maximum face-rest fan bound in accepted fluid sweeps.
    pub max_face_signal: f64,
    /// Sum of accepted dt times max(cell x speed, face-rest fan speed);
    /// a seam bound for the fixed-grid Brio strip, not a general lab-frame bound.
    pub integrated_signal_travel: f64,
    /// Max accepted per-step |V1-V0-dt/2*(Vdot0+Vdot1)|/V0.
    pub geometric_conservation_max: f64,
}
#[derive(Clone, Debug)]
pub struct Simulation {
    state: State,
    // Only shared immutable state is exposed; rebuild on every deformation.
    geometry: Arc<Geometry>,
    config: Config,
    time: f64,
    reference_velocity: Vec3,
    counters: Counters,
    pub(crate) initial_totals: Conservative,
    pub(crate) budget_scales: Conservative,
    pub(crate) initial_mean: Vec3,
}
#[derive(Clone, Debug)]
struct Geometry {
    mesh: Mesh,
    neighbours: Derivatives,
    faces: Derivatives,
    quadratic: Option<Quadratic>,
}
impl Geometry {
    fn new(mesh: Mesh, quadratic: bool) -> Result<Self, String> {
        let neighbours = Derivatives::build(&mesh, false)?;
        let faces = Derivatives::build(&mesh, true)?;
        let quadratic = if quadratic {
            Some(Quadratic::build(&mesh)?)
        } else {
            None
        };
        Ok(Self {
            quadratic,
            mesh,
            neighbours,
            faces,
        })
    }
}
struct FluidRate {
    q: Vec<Conservative>,
    fluxes: Vec<FaceFlux>,
    waves: Vec<f64>,
    fallbacks: usize,
    volume_rate: Vec<f64>,
}
struct Prepared {
    geometry: Arc<Geometry>,
    primitive: Vec<Primitive>,
    gradients: Vec<PrimitiveGradient>,
    generator_velocity: Vec<Vec2>,
    auxiliary: SmoothVelocity,
    fluid: FluidRate,
    potential_rate: Vec<Vec3>,
    cleaning: Vec<CleaningStage>,
    sound: Vec<f64>,
    bound: f64,
}
#[derive(Debug)]
enum TrialError {
    Geometry(String),
    State(String),
    Cfl,
}
impl From<String> for TrialError {
    fn from(s: String) -> Self {
        Self::State(s)
    }
}
struct Accepted {
    state: State,
    geometry: Arc<Geometry>,
    fallbacks: usize,
    geometric_error: f64,
    max_signal_x: f64,
    max_face_signal: f64,
}

fn radius(volume: f64) -> f64 {
    (volume / PI).sqrt()
}
fn sound(eos: IdealGas, q: Primitive) -> f64 {
    (eos.gamma() * q.pressure / q.density).sqrt()
}
fn recover(eos: IdealGas, state: &State, fit: &MagneticFit) -> Result<Vec<Primitive>, String> {
    state
        .conserved
        .iter()
        .zip(&state.mesh.cells)
        .zip(&fit.magnetic)
        .map(|((q, c), &b)| eos.recover(q.map(|x| x / c.volume), b))
        .collect()
}
fn fluid_rate(
    physics: (IdealGas, FaceCompletion),
    geometry: &Geometry,
    primitive_data: (&[Primitive], &[PrimitiveGradient]),
    generator_velocity: &[Vec2],
    cell_paths: &[Vec2],
    dt: f64,
    attempted_fallbacks: &mut usize,
) -> Result<FluidRate, String> {
    let (eos, completion) = physics;
    let (old, grad) = primitive_data;
    let mesh = &geometry.mesh;
    let mut q = vec![[0.; 5]; mesh.cells.len()];
    let mut waves = vec![0.; mesh.cells.len()];
    let mut volume_rate = vec![0.; mesh.cells.len()];
    let mut fluxes = Vec::with_capacity(mesh.faces.len());
    let mut fallbacks = 0;
    for face in &mesh.faces {
        let reconstruct = |i| {
            let d = mesh.displacement(face, i);
            predict(
                eos,
                old[i],
                grad[i],
                [cell_paths[i][0] + d[0], cell_paths[i][1] + d[1]],
                dt,
            )
        };
        let wf = face_velocity(mesh, face, generator_velocity)?;
        let volume_flux = face.area * (wf[0] * face.normal[0] + wf[1] * face.normal[1]);
        volume_rate[face.left] += volume_flux;
        volume_rate[face.right] -= volume_flux;
        let flux = riemann_with_completion(
            eos,
            reconstruct(face.left)?,
            reconstruct(face.right)?,
            [face.normal[0], face.normal[1], 0.],
            wf,
            completion,
        )?;
        for k in 0..5 {
            let exchange = face.area * flux.fluid[k];
            q[face.left][k] -= exchange;
            q[face.right][k] += exchange;
        }
        for i in [face.left, face.right] {
            waves[i] += face.area * flux.max_speed;
        }
        let fallback = usize::from(flux.method == FluxMethod::HllFallback);
        fallbacks += fallback;
        *attempted_fallbacks += fallback;
        fluxes.push(flux);
    }
    if !q
        .iter()
        .flatten()
        .chain(&waves)
        .chain(&volume_rate)
        .all(|x| x.is_finite())
    {
        return Err("fluid rate overflow".into());
    }
    Ok(FluidRate {
        q,
        fluxes,
        waves,
        fallbacks,
        volume_rate,
    })
}

struct Bound<'a> {
    geometry: &'a Geometry,
    auxiliary: &'a SmoothVelocity,
    generator_velocity: &'a [Vec2],
    advection_velocity: &'a [Vec2],
    waves: &'a [f64],
    sound: &'a [f64],
    tau: f64,
}
impl Bound<'_> {
    fn value(&self, cfl: f64) -> Result<f64, String> {
        let mut bound = f64::INFINITY;
        let mesh = &self.geometry.mesh;
        for (i, cell) in mesh.cells.iter().enumerate() {
            let r = radius(cell.volume);
            let cleaning = Cleaning::default().bounds(self.sound[i], r)?;
            bound = bound.min(cleaning.hyperbolic).min(cleaning.diffusive);
            if self.waves[i] > 0. {
                bound = bound.min(cell.volume / self.waves[i]);
            }
            let aux = self.auxiliary.sample(cell.centroid, self.tau)?;
            let b = [
                self.advection_velocity[i][0] - aux.velocity[0],
                self.advection_velocity[i][1] - aux.velocity[1],
            ];
            let advection: f64 = self.geometry.faces.samples[i]
                .iter()
                .map(|s| dot(b, s.weight).abs())
                .sum();
            if advection > 0. {
                bound = bound.min(1. / advection);
            }
            let distortion = (0..3)
                .map(|k| (0..3).map(|a| aux.jacobian[a][k].abs()).sum::<f64>())
                .fold(0., f64::max);
            if distortion > 0. {
                bound = bound.min(1. / distortion);
            }
            for &(f, _) in &cell.faces {
                let j = mesh.neighbour(&mesh.faces[f], i).0;
                let relative = (self.generator_velocity[i][0] - self.generator_velocity[j][0])
                    .hypot(self.generator_velocity[i][1] - self.generator_velocity[j][1]);
                if relative > 0. {
                    bound = bound.min(r / relative);
                }
            }
        }
        let result = cfl * bound;
        if !result.is_finite() || result <= 0. {
            return Err("invalid global timestep bound".into());
        }
        Ok(result)
    }
}

type Endpoint = (Arc<Geometry>, Vec<Vec2>, Vec<Vec2>);

/// Preserve winding through generator motion plus changes of centroid offsets.
fn endpoint(old: &Arc<Geometry>, w: &[Vec2], dt: f64, rigid: bool) -> Result<Endpoint, String> {
    let mesh = &old.mesh;
    if rigid {
        // Translation leaves all metric data and LS weights invariant. Translate
        // local images with the left generator and update right-image identities.
        let shift = [dt * w[0][0], dt * w[0][1]];
        if shift == [0.; 2] {
            return Ok((Arc::clone(old), vec![shift; w.len()], w.to_vec()));
        }
        let wrapped: Vec<Vec2> = mesh
            .generators
            .iter()
            .map(|g| std::array::from_fn(|k| (g[k] + shift[k]).rem_euclid(mesh.lengths[k])))
            .collect();
        let local_shift: Vec<Vec2> = wrapped
            .iter()
            .zip(&mesh.generators)
            .map(|(new, old)| [new[0] - old[0], new[1] - old[1]])
            .collect();
        let mut next = (**old).clone();
        next.mesh.generators = wrapped;
        for (cell, s) in next.mesh.cells.iter_mut().zip(&local_shift) {
            for (coordinate, shift) in cell.centroid.iter_mut().zip(s) {
                *coordinate += shift;
            }
        }
        for face in &mut next.mesh.faces {
            let s = local_shift[face.left];
            for (k, shift) in s.iter().enumerate() {
                face.centroid[k] += shift;
                let image = f64::from(face.image[k])
                    + (s[k] - local_shift[face.right][k]) / mesh.lengths[k];
                if !image.is_finite() || image.round().abs() > 1. {
                    return Err("invalid translated periodic image".into());
                }
                face.image[k] = image.round() as i32;
            }
        }
        next.mesh.validate()?;
        return Ok((Arc::new(next), vec![shift; w.len()], w.to_vec()));
    }
    let points = mesh
        .generators
        .iter()
        .zip(w)
        .map(|(g, w)| [g[0] + dt * w[0], g[1] + dt * w[1]])
        .collect();
    let next = Geometry::new(Mesh::build(points, mesh.lengths)?, old.quadratic.is_some())?;
    let mut paths = Vec::with_capacity(w.len());
    let mut what = Vec::with_capacity(w.len());
    for (i, wi) in w.iter().enumerate() {
        let delta: Vec2 = std::array::from_fn(|k| {
            (next.mesh.cells[i].centroid[k] - next.mesh.generators[i][k])
                - (mesh.cells[i].centroid[k] - mesh.generators[i][k])
        });
        paths.push(std::array::from_fn(|k| dt * wi[k] + delta[k]));
        what.push(std::array::from_fn(|k| wi[k] + 2. * delta[k] / dt));
    }
    Ok((Arc::new(next), paths, what))
}

impl Simulation {
    pub fn new(
        mesh: Mesh,
        config: Config,
        initial: impl Fn(Vec2) -> Initial,
    ) -> Result<Self, String> {
        mesh.validate()?;
        let eos = IdealGas::new(config.gamma)?;
        if !config.cfl.is_finite()
            || config.cfl <= 0.
            || config.cfl > 0.3
            || config.max_dt.is_nan()
            || config.max_dt <= 0.
            || !config.magnetic_scale.is_finite()
            || config.magnetic_scale <= 0.
            || !config.mean_magnetic.iter().all(|x| x.is_finite())
        {
            return Err("invalid general reference configuration".into());
        }
        let data: Vec<_> = mesh.cells.iter().map(|c| initial(c.centroid)).collect();
        let potential: Vec<_> = data.iter().map(|q| q.potential).collect();
        let phi: Vec<_> = data.iter().map(|q| q.phi).collect();
        let geometry = Arc::new(Geometry::new(mesh.clone(), config.profile.quadratic())?);
        let fit = MagneticFit::with_stencil(
            &mesh,
            (
                &geometry.neighbours,
                geometry.quadratic.as_ref(),
                config.profile.consistent(),
                config.profile.matched(),
            ),
            &potential,
            &phi,
            config.mean_magnetic,
            config.limited,
        )?;
        let primitive: Vec<_> = data
            .iter()
            .zip(&fit.magnetic)
            .map(|(q, &b)| Primitive {
                density: q.density,
                pressure: q.pressure,
                velocity: q.velocity,
                magnetic: b,
            })
            .collect();
        let conserved: Vec<Conservative> = primitive
            .iter()
            .zip(&mesh.cells)
            .map(|(&q, c)| eos.conservative(q).map(|v| v.map(|x| x * c.volume)))
            .collect::<Result<_, _>>()?;
        let volume: f64 = mesh.cells.iter().map(|c| c.volume).sum();
        let initial_totals: Conservative =
            std::array::from_fn(|k| conserved.iter().map(|q| q[k]).sum());
        let reference_velocity: Vec3 = match config.profile {
            Profile::PaperGlobalV2 => [0.; 3],
            Profile::BulkFrameV1
            | Profile::BulkFrameHllV1
            | Profile::BulkFrameHllQuadraticV1
            | Profile::BulkFrameHllConsistentV1
            | Profile::BulkFrameHllMatchedV1 => {
                std::array::from_fn(|k| initial_totals[k + 1] / initial_totals[0])
            }
        };
        if !reference_velocity.iter().all(|v| v.is_finite()) {
            return Err("nonfinite gauge reference velocity".into());
        }
        let rho = primitive.iter().map(|q| q.density).fold(0., f64::max);
        let speed = primitive
            .iter()
            .map(|q| {
                q.velocity[0]
                    .hypot(q.velocity[1])
                    .hypot(q.velocity[2])
                    .max(sound(eos, *q))
            })
            .fold(0., f64::max);
        let energy = conserved
            .iter()
            .zip(&mesh.cells)
            .map(|(q, c)| q[4] / c.volume)
            .fold(0., f64::max);
        let scales = [rho, rho * speed, rho * speed, rho * speed, energy];
        let budget_scales = std::array::from_fn(|k| {
            conserved
                .iter()
                .map(|q| q[k].abs())
                .sum::<f64>()
                .max(volume * scales[k])
                .max(1e-30)
        });
        let initial_mean = std::array::from_fn(|k| {
            fit.magnetic
                .iter()
                .zip(&mesh.cells)
                .map(|(b, c)| b[k] * c.volume)
                .sum::<f64>()
                / volume
        });
        let result = Self {
            geometry,
            state: State {
                mesh,
                potential,
                phi,
                conserved,
                auxiliary_origin: [0.; 2],
                gauge_offset: [0.; 3],
            },
            config,
            time: 0.,
            reference_velocity,
            counters: Counters::default(),
            initial_totals,
            budget_scales,
            initial_mean,
        };
        result.generator_velocities(&primitive)?;
        Ok(result)
    }
    pub fn state(&self) -> &State {
        &self.state
    }
    pub fn config(&self) -> &Config {
        &self.config
    }
    /// Fixed initial mass-weighted velocity, used only by the gauge comparator.
    pub fn reference_velocity(&self) -> Vec3 {
        self.reference_velocity
    }
    pub fn total_potential(&self) -> Vec<Vec3> {
        self.state
            .potential
            .iter()
            .map(|a| std::array::from_fn(|k| a[k] + self.state.gauge_offset[k]))
            .collect()
    }
    pub fn time(&self) -> f64 {
        self.time
    }
    pub fn counters(&self) -> &Counters {
        &self.counters
    }
    pub fn quadratic_condition(&self) -> Option<f64> {
        self.geometry.quadratic.as_ref().map(|q| q.worst_condition)
    }
    pub fn magnetic_fit(&self) -> Result<MagneticFit, String> {
        MagneticFit::with_stencil(
            &self.geometry.mesh,
            (
                &self.geometry.neighbours,
                self.geometry.quadratic.as_ref(),
                self.config.profile.consistent(),
                self.config.profile.matched(),
            ),
            &self.state.potential,
            &self.state.phi,
            self.config.mean_magnetic,
            self.config.limited,
        )
    }
    pub fn primitives(&self) -> Result<Vec<Primitive>, String> {
        recover(
            IdealGas::new(self.config.gamma)?,
            &self.state,
            &self.magnetic_fit()?,
        )
    }
    fn generator_velocities(&self, q: &[Primitive]) -> Result<Vec<Vec2>, String> {
        let n = self.state.mesh.cells.len();
        let w = match &self.config.motion {
            Motion::Fixed => vec![[0.; 2]; n],
            Motion::Rigid(v) => vec![*v; n],
            Motion::Fluid => q.iter().map(|q| [q.velocity[0], q.velocity[1]]).collect(),
            Motion::Prescribed(v) => v.clone(),
        };
        if w.len() != n || !w.iter().flatten().all(|x| x.is_finite()) {
            return Err("invalid generator velocities".into());
        }
        Ok(w)
    }
    fn prepare(&self, attempted: &mut usize) -> Result<Prepared, String> {
        let eos = IdealGas::new(self.config.gamma)?;
        let geometry = Arc::clone(&self.geometry);
        let fit = MagneticFit::with_stencil(
            &geometry.mesh,
            (
                &geometry.neighbours,
                geometry.quadratic.as_ref(),
                self.config.profile.consistent(),
                self.config.profile.matched(),
            ),
            &self.state.potential,
            &self.state.phi,
            self.config.mean_magnetic,
            self.config.limited,
        )?;
        let primitive = recover(eos, &self.state, &fit)?;
        let gradients = gradients(
            &geometry.mesh,
            &geometry.neighbours,
            &primitive.iter().map(|q| components(*q)).collect::<Vec<_>>(),
            self.config.limited,
        )?;
        let generator_velocity = self.generator_velocities(&primitive)?;
        let samples: Vec<_> = primitive
            .iter()
            .zip(&geometry.mesh.cells)
            .map(|(q, c)| VelocitySample {
                position: c.centroid,
                volume: c.volume,
                velocity: q.velocity,
            })
            .collect();
        let auxiliary =
            SmoothVelocity::build(geometry.mesh.lengths, &samples, self.state.auxiliary_origin)?;
        let fluid = fluid_rate(
            (eos, self.config.profile.completion()),
            &geometry,
            (&primitive, &gradients),
            &generator_velocity,
            &vec![[0.; 2]; primitive.len()],
            0.,
            attempted,
        )?;
        let potential_rate = PotentialStage {
            mesh: &geometry.mesh,
            face_stencil: &geometry.faces,
            potential: &self.state.potential,
            fit: &fit,
            faces: &fluid.fluxes,
            auxiliary: &auxiliary,
            advection_velocity: &generator_velocity,
            mean: self.config.mean_magnetic,
            reference_velocity: self.reference_velocity,
            tau: 0.,
            centered: self.config.profile.consistent(),
        }
        .rate()?;
        let sound: Vec<_> = primitive.iter().map(|&q| sound(eos, q)).collect();
        let cleaning = (0..primitive.len())
            .map(|i| {
                Cleaning::default().begin(
                    self.state.phi[i],
                    fit.divergence_a[i],
                    sound[i],
                    radius(geometry.mesh.cells[i].volume),
                )
            })
            .collect::<Result<_, _>>()?;
        let bound = Bound {
            geometry: &geometry,
            auxiliary: &auxiliary,
            generator_velocity: &generator_velocity,
            advection_velocity: &generator_velocity,
            waves: &fluid.waves,
            sound: &sound,
            tau: 0.,
        }
        .value(self.config.cfl)?;
        Ok(Prepared {
            geometry,
            primitive,
            gradients,
            generator_velocity,
            auxiliary,
            fluid,
            potential_rate,
            cleaning,
            sound,
            bound,
        })
    }
    fn trial(
        &self,
        old: &Prepared,
        dt: f64,
        attempted: &mut usize,
    ) -> Result<Accepted, TrialError> {
        let eos = IdealGas::new(self.config.gamma)?;
        let rigid = matches!(self.config.motion, Motion::Fixed | Motion::Rigid(_));
        let (geometry, paths, what) = endpoint(&old.geometry, &old.generator_velocity, dt, rigid)
            .map_err(TrialError::Geometry)?;
        let star: Vec<Vec3> = self
            .state
            .potential
            .iter()
            .zip(&old.potential_rate)
            .map(|(a, r)| std::array::from_fn(|k| a[k] + dt * r[k]))
            .collect();
        let phi_star = old
            .cleaning
            .iter()
            .map(|c| c.predicted_phi(dt))
            .collect::<Result<Vec<_>, _>>()?;
        let fit = MagneticFit::with_stencil(
            &geometry.mesh,
            (
                &geometry.neighbours,
                geometry.quadratic.as_ref(),
                self.config.profile.consistent(),
                self.config.profile.matched(),
            ),
            &star,
            &phi_star,
            self.config.mean_magnetic,
            self.config.limited,
        )
        .map_err(TrialError::State)?;
        let fluid = fluid_rate(
            (eos, self.config.profile.completion()),
            &geometry,
            (&old.primitive, &old.gradients),
            &old.generator_velocity,
            &paths,
            dt,
            attempted,
        )?;
        let rate = PotentialStage {
            mesh: &geometry.mesh,
            face_stencil: &geometry.faces,
            potential: &star,
            fit: &fit,
            faces: &fluid.fluxes,
            auxiliary: &old.auxiliary,
            advection_velocity: &what,
            mean: self.config.mean_magnetic,
            reference_velocity: self.reference_velocity,
            tau: dt,
            centered: self.config.profile.consistent(),
        }
        .rate()?;
        let predicted = old
            .primitive
            .iter()
            .enumerate()
            .map(|(i, &q)| predict(eos, q, old.gradients[i], paths[i], dt))
            .collect::<Result<Vec<_>, _>>()?;
        let mut sound_bound: Vec<_> = predicted
            .iter()
            .enumerate()
            .map(|(i, &q)| sound(eos, q).max(old.sound[i]))
            .collect();
        let bound = |cs: &[f64]| {
            Bound {
                geometry: &geometry,
                auxiliary: &old.auxiliary,
                generator_velocity: &old.generator_velocity,
                advection_velocity: &what,
                waves: &fluid.waves,
                sound: cs,
                tau: dt,
            }
            .value(self.config.cfl)
        };
        if dt > bound(&sound_bound)? * (1. + 1e-12) {
            return Err(TrialError::Cfl);
        }
        let potential = self
            .state
            .potential
            .iter()
            .enumerate()
            .map(|(i, a)| {
                std::array::from_fn(|k| a[k] + 0.5 * dt * (old.potential_rate[i][k] + rate[i][k]))
            })
            .collect();
        let phi = old
            .cleaning
            .iter()
            .enumerate()
            .map(|(i, c)| c.finish_phi(dt, radius(geometry.mesh.cells[i].volume)))
            .collect::<Result<_, _>>()?;
        let conserved = self
            .state
            .conserved
            .iter()
            .enumerate()
            .map(|(i, q)| {
                std::array::from_fn(|k| q[k] + 0.5 * dt * (old.fluid.q[i][k] + fluid.q[i][k]))
            })
            .collect();
        let offset_rate = cross(self.reference_velocity, self.config.mean_magnetic);
        let next = State {
            mesh: geometry.mesh.clone(),
            potential,
            phi,
            conserved,
            auxiliary_origin: old.auxiliary.advanced_origin(dt)?,
            gauge_offset: std::array::from_fn(|k| self.state.gauge_offset[k] + dt * offset_rate[k]),
        };
        if !next.gauge_offset.iter().all(|x| x.is_finite())
            || next
                .potential
                .iter()
                .any(|a| (0..3).any(|k| !(a[k] + next.gauge_offset[k]).is_finite()))
        {
            return Err(TrialError::State(
                "total potential/gauge offset overflow".into(),
            ));
        }
        let final_fit = MagneticFit::with_stencil(
            &next.mesh,
            (
                &geometry.neighbours,
                geometry.quadratic.as_ref(),
                self.config.profile.consistent(),
                self.config.profile.matched(),
            ),
            &next.potential,
            &next.phi,
            self.config.mean_magnetic,
            self.config.limited,
        )?;
        let closed = recover(eos, &next, &final_fit)?;
        for (i, &q) in closed.iter().enumerate() {
            sound_bound[i] = sound_bound[i].max(sound(eos, q));
        }
        if dt > bound(&sound_bound)? * (1. + 1e-12) {
            return Err(TrialError::Cfl);
        }
        let geometric_error = next
            .mesh
            .cells
            .iter()
            .enumerate()
            .map(|(i, c)| {
                let v0 = self.state.mesh.cells[i].volume;
                (c.volume - v0 - 0.5 * dt * (old.fluid.volume_rate[i] + fluid.volume_rate[i])).abs()
                    / v0
            })
            .fold(0., f64::max);
        if !geometric_error.is_finite() {
            return Err(TrialError::Geometry(
                "nonfinite geometric conservation error".into(),
            ));
        }
        let max_signal_x = old
            .primitive
            .iter()
            .chain(&predicted)
            .chain(&closed)
            .map(|&q| q.velocity[0].abs() + eos.fast_speed(q, [1., 0., 0.]))
            .fold(0., f64::max);
        let max_face_signal = old
            .fluid
            .fluxes
            .iter()
            .chain(&fluid.fluxes)
            .map(|f| f.max_speed)
            .fold(0., f64::max);
        Ok(Accepted {
            max_signal_x,
            max_face_signal,
            state: next,
            geometry,
            fallbacks: fluid.fallbacks,
            geometric_error,
        })
    }
    pub fn advance_to(&mut self, target: f64) -> Result<(), String> {
        if !target.is_finite() || target < self.time {
            return Err("invalid target time".into());
        }
        while self.time < target {
            let mut attempted = 0;
            let preparation = self.prepare(&mut attempted);
            self.counters.hll_fallbacks_attempted += attempted;
            let old = preparation?;
            let mut dt = old.bound.min(self.config.max_dt).min(target - self.time);
            let mut accepted = None;
            let mut last_error = String::new();
            for _ in 0..16 {
                if !dt.is_finite()
                    || dt <= 0.
                    || self.time + dt == self.time
                    || self.counters.steps >= 1_000_000
                {
                    return Err("timestep underflow or step limit".into());
                }
                let mut attempted = 0;
                let trial = self.trial(&old, dt, &mut attempted);
                self.counters.hll_fallbacks_attempted += attempted;
                match trial {
                    Ok(next) => {
                        accepted = Some(next);
                        break;
                    }
                    Err(e) => {
                        last_error = match e {
                            TrialError::Geometry(s) => {
                                self.counters.rejected_geometry += 1;
                                s
                            }
                            TrialError::State(s) => {
                                self.counters.rejected_state += 1;
                                s
                            }
                            TrialError::Cfl => {
                                self.counters.rejected_cfl += 1;
                                "endpoint CFL bound".into()
                            }
                        };
                        dt *= 0.5;
                    }
                }
            }
            let next =
                accepted.ok_or_else(|| format!("step failed at t={}: {last_error}", self.time))?;
            self.counters.max_signal_x = self.counters.max_signal_x.max(next.max_signal_x);
            self.counters.max_face_signal = self.counters.max_face_signal.max(next.max_face_signal);
            self.counters.integrated_signal_travel +=
                dt * next.max_signal_x.max(next.max_face_signal);
            self.state = next.state;
            self.geometry = next.geometry;
            self.time = (self.time + dt).min(target);
            self.counters.steps += 1;
            self.counters.min_dt = Some(self.counters.min_dt.map_or(dt, |d| d.min(dt)));
            self.counters.max_dt = self.counters.max_dt.max(dt);
            self.counters.geometric_conservation_max = self
                .counters
                .geometric_conservation_max
                .max(next.geometric_error);
            self.counters.hll_fallbacks += old.fluid.fallbacks + next.fallbacks;
            self.counters
                .auxiliary_roots
                .push(old.auxiliary.intervals());
            self.counters.auxiliary_coarsenings += old.auxiliary.coarsenings;
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f64::consts::TAU;
    fn initial(_: Vec2) -> Initial {
        Initial {
            density: 1.,
            pressure: 1.,
            velocity: [0.2, -0.1, 0.3],
            potential: [0.1, -0.2, 0.4],
            phi: 0.,
        }
    }
    #[test]
    fn endpoint_winding_topology_and_rejected_trial_are_consistent() {
        let mesh = Mesh::lattice(6, 6, [1.; 2], 0.).unwrap();
        let w: Vec<_> = mesh
            .generators
            .iter()
            .map(|p| [0.1 * (TAU * p[1]).sin(), 0.1 * (TAU * p[0]).cos()])
            .collect();
        let sim = Simulation::new(
            mesh.clone(),
            Config {
                motion: Motion::Prescribed(w.clone()),
                ..Config::default()
            },
            initial,
        )
        .unwrap();
        let old = sim.prepare(&mut 0).unwrap();
        let (end, _, _) = endpoint(&old.geometry, &w, 0.04, false).unwrap();
        assert_ne!(old.geometry.mesh.faces.len(), end.mesh.faces.len());
        let before = format!("{:?}", sim.state);
        let auxiliary_before = format!("{:?}", old.auxiliary);
        assert!(sim.trial(&old, 1., &mut 0).is_err());
        assert_eq!(before, format!("{:?}", sim.state));
        assert_eq!(auxiliary_before, format!("{:?}", old.auxiliary));
        // A later good trial remains possible from exactly the same old data.
        assert!(sim.trial(&old, 0.1 * old.bound, &mut 0).is_ok());
        let rigid = vec![[200., -300.]; mesh.cells.len()];
        let (end, paths, what) = endpoint(&old.geometry, &rigid, 0.017, true).unwrap();
        for i in 0..paths.len() {
            assert!((paths[i][0] - 3.4).abs() < 1e-12);
            assert!((paths[i][1] + 5.1).abs() < 1e-12);
            assert_eq!(what[i], rigid[i]);
            for k in 0..2 {
                let residual = (end.mesh.generators[i][k] - mesh.generators[i][k] - paths[i][k]
                    + 0.5)
                    .rem_euclid(1.)
                    - 0.5;
                assert!(residual.abs() < 1e-12);
            }
        }
    }
    #[test]
    fn bulk_gauge_offset_and_geometry_survive_rejected_trial() {
        let mut sim = Simulation::new(
            Mesh::lattice(6, 6, [1.; 2], 0.15).unwrap(),
            Config {
                profile: Profile::BulkFrameV1,
                mean_magnetic: [0.3, 0.2, 0.1],
                max_dt: 0.001,
                ..Config::default()
            },
            initial,
        )
        .unwrap();
        sim.advance_to(0.002).unwrap();
        assert_ne!(sim.state.gauge_offset, [0.; 3]);
        let old = sim.prepare(&mut 0).unwrap();
        let before = format!("{:?}", sim);
        assert!(sim.trial(&old, 1., &mut 0).is_err());
        assert_eq!(before, format!("{:?}", sim));
        assert!(Arc::ptr_eq(&old.geometry, &sim.geometry));
        let dt = 0.1 * old.bound;
        let accepted = sim.trial(&old, dt, &mut 0).unwrap();
        let rate = cross(sim.reference_velocity, sim.config.mean_magnetic);
        for (k, rate) in rate.iter().enumerate() {
            assert_eq!(
                accepted.state.gauge_offset[k],
                sim.state.gauge_offset[k] + dt * rate
            );
        }
    }

    #[test]
    fn cached_geometry_matches_rebuilt_clipping_evolution() {
        for jitter in [0., 0.15] {
            for motion in [
                Motion::Fixed,
                Motion::Rigid([2., -1.]),
                Motion::Rigid([0.2, -0.1]),
                Motion::Fluid,
            ] {
                let mesh = Mesh::lattice(6, 8, [1.3, 0.7], jitter).unwrap();
                let original =
                    Mesh::build_all_pairs(mesh.generators.clone(), mesh.lengths).unwrap();
                let config = Config {
                    motion: motion.clone(),
                    max_dt: 0.0005,
                    ..Config::default()
                };
                let data = |x: Vec2| Initial {
                    velocity: [0.2 + 0.03 * (TAU * x[1] / 0.7).sin(), -0.1, 0.04],
                    potential: [
                        0.001 * (TAU * x[1] / 0.7).sin(),
                        0.001 * (TAU * x[0] / 1.3).cos(),
                        0.001 * (TAU * x[0] / 1.3).sin(),
                    ],
                    phi: 0.0001 * (TAU * x[0] / 1.3).sin(),
                    ..initial(x)
                };
                let mut fast = Simulation::new(mesh, config.clone(), data).unwrap();
                let mut reference = Simulation::new(original, config, data).unwrap();
                for step in 1..=6 {
                    // Reproduce the old preparation path, rebuilding stencils every step.
                    reference.geometry =
                        Arc::new(Geometry::new(reference.state.mesh.clone(), false).unwrap());
                    let target = step as f64 * 0.0005;
                    fast.advance_to(target).unwrap();
                    reference.advance_to(target).unwrap();
                    for (a, b) in fast
                        .state
                        .conserved
                        .iter()
                        .flatten()
                        .zip(reference.state.conserved.iter().flatten())
                    {
                        assert!(
                            (a - b).abs() < 1e-11,
                            "jitter={jitter} motion={motion:?} step={step} a={a:e} b={b:e} error={:e}",
                            (a - b).abs()
                        );
                    }
                    for (a, b) in fast
                        .state
                        .potential
                        .iter()
                        .flatten()
                        .chain(&fast.state.phi)
                        .zip(
                            reference
                                .state
                                .potential
                                .iter()
                                .flatten()
                                .chain(&reference.state.phi),
                        )
                    {
                        assert!(
                            (a - b).abs() < 1e-11,
                            "jitter={jitter} motion={motion:?} step={step} a={a:e} b={b:e} error={:e}",
                            (a - b).abs()
                        );
                    }
                    for (a, b) in fast
                        .magnetic_fit()
                        .unwrap()
                        .magnetic
                        .iter()
                        .flatten()
                        .zip(reference.magnetic_fit().unwrap().magnetic.iter().flatten())
                    {
                        assert!(
                            (a - b).abs() < 1e-11,
                            "jitter={jitter} motion={motion:?} step={step} a={a:e} b={b:e} error={:e}",
                            (a - b).abs()
                        );
                    }
                }
            }
        }
    }

    #[test]
    fn face_exchanges_cancel_at_both_geometries() {
        let mesh = Mesh::lattice(6, 6, [1.; 2], 0.15).unwrap();
        let mut sim = Simulation::new(
            mesh,
            Config {
                motion: Motion::Fluid,
                ..Config::default()
            },
            |x| Initial {
                density: 1. + 0.01 * (TAU * x[0]).sin(),
                velocity: [0.2 + 0.02 * (TAU * x[1]).cos(), -0.1, 0.3],
                ..initial(x)
            },
        )
        .unwrap();
        let old = sim.prepare(&mut 0).unwrap();
        for k in 0..5 {
            assert!(old.fluid.q.iter().map(|q| q[k]).sum::<f64>().abs() < 1e-12);
        }
        let next = sim.trial(&old, 0.1 * old.bound, &mut 0).unwrap();
        for k in 0..5 {
            let a: f64 = sim.state.conserved.iter().map(|q| q[k]).sum();
            let b: f64 = next.state.conserved.iter().map(|q| q[k]).sum();
            assert!((a - b).abs() < 1e-12);
        }
        sim.advance_to(0.002).unwrap();
        assert!(
            sim.diagnostics()
                .unwrap()
                .normalized_budget
                .iter()
                .all(|x| x.abs() < 1e-12)
        );
    }
}

#[cfg(test)]
mod endpoint_cleaning_test {
    use super::*;
    use std::f64::consts::TAU;
    #[test]
    fn endpoint_uses_phi_star_but_frozen_initial_cleaning_source() {
        let mesh = Mesh::lattice(8, 8, [1.; 2], 0.).unwrap();
        let sim = Simulation::new(mesh, Config::default(), |x| Initial {
            density: 1.,
            pressure: 0.6,
            velocity: [0.; 3],
            potential: [0.; 3],
            phi: 0.001 * (TAU * x[0]).sin(),
        })
        .unwrap();
        let old = sim.prepare(&mut 0).unwrap();
        let dt = 0.001;
        let next = sim.trial(&old, dt, &mut 0).unwrap();
        let damping = 0.15 / radius(1. / 64.); // cs=1
        let keff = (TAU / 8.).sin() * 8.;
        for (i, c) in sim.state.mesh.cells.iter().enumerate() {
            let x = TAU * c.centroid[0];
            let expected_a = dt * (1. - 0.5 * dt * damping) * 0.001 * keff * x.cos();
            let expected_phi = 0.001 * x.sin() * (1. - dt * damping + 0.5 * (dt * damping).powi(2));
            assert!((next.state.potential[i][0] - expected_a).abs() < 1e-14);
            assert!((next.state.phi[i] - expected_phi).abs() < 1e-14);
        }
    }
}

#[cfg(test)]
mod fallback_accounting_test {
    use super::*;
    #[test]
    fn partial_failed_sweep_keeps_successful_hll_counts() {
        let geometry = Geometry::new(Mesh::lattice(4, 4, [1.; 2], 0.).unwrap(), false).unwrap();
        let n = geometry.mesh.cells.len();
        let first = &geometry.mesh.faces[0];
        let q = Primitive {
            density: 1.,
            pressure: 1e-6,
            velocity: [0.; 3],
            magnetic: [first.normal[0], first.normal[1], 0.],
        };
        let mut primitive = vec![q; n];
        let invalid = (0..n)
            .rev()
            .find(|&i| i != first.left && i != first.right)
            .unwrap();
        primitive[invalid].pressure = -1.;
        let mut attempted = 0;
        let result = fluid_rate(
            (IdealGas::new(1.4).unwrap(), FaceCompletion::RiemannState),
            &geometry,
            (&primitive, &vec![[[0.; 2]; 8]; n]),
            &vec![[0.; 2]; n],
            &vec![[0.; 2]; n],
            0.,
            &mut attempted,
        );
        assert!(result.is_err());
        assert!(
            attempted > 0,
            "first face is the degenerate parallel-field HLL fixture"
        );
    }
}
