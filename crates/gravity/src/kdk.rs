//! GP-4 synchronized fixed-mass KDK. Trial state is private until full success.
use crate::GravityError;
use crate::checked::{Sum, add, div, mul, positive};
use crate::diagnostics::{RawDiagnostics, measure};
use crate::direct::{CachePins, DirectConfig, Evaluation, evaluate};
use crate::identity::sized_bytes;
use crate::softening::GravityModel;
use crate::state::Catalog;

/// Registered conservative ceiling, not an error estimate or orbit gate.
pub fn timestep_ceiling(catalog: &Catalog, model: &GravityModel) -> Result<f64, GravityError> {
    if catalog.particles().is_empty() {
        return Err(GravityError::EmptyTimestep);
    }
    let mut mass = Sum::default();
    for p in catalog.particles() {
        if p.softening() != model.softening().class() {
            return Err(GravityError::UnsupportedSofteningClass);
        }
        mass.add(p.mass())?;
    }
    let epsilon = model.softening().epsilon();
    let epsilon3 = mul(
        mul(epsilon, epsilon, "ceiling epsilon squared")?,
        epsilon,
        "ceiling epsilon cubed",
    )?;
    let gm = mul(model.g(), mass.value()?, "ceiling GM")?;
    positive(
        mul(
            0.05,
            div(epsilon3, gm, "ceiling radicand")?.sqrt(),
            "timestep ceiling",
        )?,
        "timestep ceiling",
    )
}

#[derive(Clone, Debug)]
pub struct StepReport {
    pub dt: f64,
    pub start_pins: CachePins,
    pub before: RawDiagnostics,
    pub after: RawDiagnostics,
    /// Actual rounded post-drift positions and half-kick momenta, not ideal rationals.
    pub drift_endpoint: Catalog,
    pub drift_forces: Evaluation,
    pub endpoint_forces: Evaluation,
}

#[derive(Clone, Debug)]
pub struct KdkCheckpoint {
    catalog: Catalog,
    model: GravityModel,
    config: DirectConfig,
    forces: Evaluation,
}

impl KdkCheckpoint {
    /// Lossless versioned identity bytes for this in-memory checkpoint.
    /// A durable file decoder, transaction and allocator/RNG restore are deferred.
    pub fn canonical_bytes(&self) -> Vec<u8> {
        let mut bytes = b"gravity-kdk-checkpoint-v1\0".to_vec();
        for part in [
            self.catalog.state_identity().bytes(),
            self.model.identity().bytes(),
            self.model.units().identity().bytes(),
            self.config.identity().bytes(),
        ] {
            sized_bytes(&mut bytes, part);
        }
        sized_bytes(&mut bytes, &self.forces.canonical_bytes());
        bytes
    }
}

#[derive(Clone, Debug)]
pub struct KdkSystem {
    catalog: Catalog,
    model: GravityModel,
    config: DirectConfig,
    forces: Evaluation,
}

impl KdkSystem {
    pub fn new(
        catalog: Catalog,
        model: GravityModel,
        config: DirectConfig,
    ) -> Result<Self, GravityError> {
        Self::with_evaluator(catalog, model, config, evaluate)
    }
    pub fn new_on<L: mhd_parallel::layout::Layout>(
        catalog: Catalog,
        model: GravityModel,
        config: DirectConfig,
        layout: &L,
    ) -> Result<Self, GravityError> {
        Self::with_evaluator(catalog, model, config, |c, m, d| {
            crate::direct::evaluate_on(c, m, d, layout)
        })
    }
    fn with_evaluator(
        catalog: Catalog,
        model: GravityModel,
        config: DirectConfig,
        eval: impl FnOnce(&Catalog, &GravityModel, &DirectConfig) -> Result<Evaluation, GravityError>,
    ) -> Result<Self, GravityError> {
        let forces = eval(&catalog, &model, &config)?;
        measure(&catalog, &model, &config, &forces)?;
        Ok(Self {
            catalog,
            model,
            config,
            forces,
        })
    }

    pub fn catalog(&self) -> &Catalog {
        &self.catalog
    }
    pub fn model(&self) -> &GravityModel {
        &self.model
    }
    pub fn config(&self) -> &DirectConfig {
        &self.config
    }
    pub fn forces(&self) -> &Evaluation {
        &self.forces
    }

    pub fn checkpoint(&self) -> KdkCheckpoint {
        KdkCheckpoint {
            catalog: self.catalog.clone(),
            model: self.model.clone(),
            config: self.config.clone(),
            forces: self.forces.clone(),
        }
    }

    pub fn restore(checkpoint: &KdkCheckpoint) -> Result<Self, GravityError> {
        checkpoint.forces.validate_for(
            &checkpoint.catalog,
            &checkpoint.model,
            &checkpoint.config,
        )?;
        measure(
            &checkpoint.catalog,
            &checkpoint.model,
            &checkpoint.config,
            &checkpoint.forces,
        )?;
        Ok(Self {
            catalog: checkpoint.catalog.clone(),
            model: checkpoint.model.clone(),
            config: checkpoint.config.clone(),
            forces: checkpoint.forces.clone(),
        })
    }

    pub fn try_step(&mut self, dt: f64) -> Result<StepReport, GravityError> {
        self.step_using(dt, evaluate)
    }
    pub fn try_step_on<L: mhd_parallel::layout::Layout>(
        &mut self,
        dt: f64,
        layout: &L,
    ) -> Result<StepReport, GravityError> {
        layout
            .agree(&dt.to_bits().to_le_bytes())
            .map_err(GravityError::Parallel)?;
        self.step_using(dt, |c, m, d| crate::direct::evaluate_on(c, m, d, layout))
    }
    fn step_using(
        &mut self,
        dt: f64,
        mut eval: impl FnMut(&Catalog, &GravityModel, &DirectConfig) -> Result<Evaluation, GravityError>,
    ) -> Result<StepReport, GravityError> {
        positive(dt, "KDK dt")?;
        self.forces
            .validate_for(&self.catalog, &self.model, &self.config)?;
        if dt > timestep_ceiling(&self.catalog, &self.model)? {
            return Err(GravityError::StepAboveCeiling);
        }
        let half = positive(mul(0.5, dt, "KDK half dt")?, "KDK half dt")?;
        let end = add(self.catalog.time(), dt, "endpoint time")?;
        if end <= self.catalog.time() {
            return Err(GravityError::TimeNotAdvanced);
        }
        let revision = self
            .catalog
            .revision()
            .checked_add(1)
            .ok_or(GravityError::RevisionOverflow)?;
        let before = measure(&self.catalog, &self.model, &self.config, &self.forces)?;
        let drift_particles = mhd_parallel::map(self.catalog.particles().len(), |i| {
            let p = &self.catalog.particles()[i];
            let f = self.forces.sample(p.id())?.force();
            let old_p = p.momentum();
            let old_x = p.position();
            let mut half_p = [0.0; 3];
            let mut x = [0.0; 3];
            for (k, out) in half_p.iter_mut().enumerate() {
                *out = add(
                    old_p[k],
                    mul(half, f[k], "half kick")?,
                    "half-kicked momentum",
                )?;
                x[k] = add(
                    old_x[k],
                    mul(dt, div(*out, p.mass(), "drift velocity")?, "drift")?,
                    "drift position",
                )?;
            }
            p.moved(x, half_p)
        })
        .into_iter()
        .collect::<Result<Vec<_>, GravityError>>()?;
        let drift_endpoint = Catalog::new(end, revision, drift_particles)?;
        let drift_forces = eval(&drift_endpoint, &self.model, &self.config)?;
        let particles = mhd_parallel::map(drift_endpoint.particles().len(), |i| {
            let p = &drift_endpoint.particles()[i];
            let f = drift_forces.sample(p.id())?.force();
            let half_p = p.momentum();
            let mut momentum = [0.0; 3];
            for (out, (half_p, force)) in momentum.iter_mut().zip(half_p.into_iter().zip(f)) {
                *out = add(
                    half_p,
                    mul(half, force, "last half kick")?,
                    "endpoint momentum",
                )?;
            }
            p.moved(p.position(), momentum)
        })
        .into_iter()
        .collect::<Result<Vec<_>, GravityError>>()?;
        let catalog = Catalog::new(end, revision, particles)?;
        // Momenta belong to the full state pin. Re-evaluate at the same rounded
        // positions rather than silently rebinding a half-momentum cache.
        let endpoint_forces = eval(&catalog, &self.model, &self.config)?;
        let after = measure(&catalog, &self.model, &self.config, &endpoint_forces)?;
        let report = StepReport {
            dt,
            start_pins: self.forces.pins().clone(),
            before,
            after,
            drift_endpoint,
            drift_forces,
            endpoint_forces: endpoint_forces.clone(),
        };
        self.catalog = catalog;
        self.forces = endpoint_forces;
        Ok(report)
    }
}
