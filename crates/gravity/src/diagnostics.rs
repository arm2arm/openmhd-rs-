//! GP-6 raw laboratory ledgers and separately labelled internal diagnostics.
use crate::checked::{Sum, VectorSum, add, cross, div, dot, mul, scale, sub};
use crate::direct::{DirectConfig, Evaluation};
use crate::softening::GravityModel;
use crate::state::Catalog;
use crate::{GravityError, Vec3};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum VirialUndefined {
    EmptyCatalog,
    NonpositiveScale,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum VirialResidual {
    Defined(f64),
    Undefined(VirialUndefined),
}

#[derive(Clone, Debug)]
pub struct RawDiagnostics {
    pub mass: f64,
    pub momentum: Vec3,
    pub center_of_mass: Option<Vec3>,
    pub center_velocity: Option<Vec3>,
    pub angular_momentum_origin: Vec3,
    pub angular_momentum_internal: Option<Vec3>,
    pub kinetic_lab: f64,
    pub kinetic_internal: Option<f64>,
    pub pair_energy: f64,
    pub hamiltonian_lab: f64,
    pub net_force: Vec3,
    pub torque_origin: Vec3,
    pub virial_work: Option<f64>,
    pub inertia_internal: Option<f64>,
    pub virial_residual: VirialResidual,
}

pub fn measure(
    catalog: &Catalog,
    model: &GravityModel,
    config: &DirectConfig,
    forces: &Evaluation,
) -> Result<RawDiagnostics, GravityError> {
    forces.validate_for(catalog, model, config)?;
    let mut mass = Sum::default();
    let mut momentum = VectorSum::default();
    let mut weighted_position = VectorSum::default();
    let mut angular = VectorSum::default();
    let mut kinetic = Sum::default();
    let mut net_force = VectorSum::default();
    let mut torque = VectorSum::default();
    let count = catalog.particles().len();
    let batch = std::num::NonZeroUsize::new(512).unwrap();
    let grain = std::num::NonZeroUsize::new(16).unwrap();
    // Keep all compensated accumulators in persistent particle order. Workers
    // evaluate terms independently; the commit still checks each operation in order.
    mhd_parallel::visit_ordered(
        count,
        batch,
        grain,
        |i| {
            let p = &catalog.particles()[i];
            let f = forces.samples()[i].force();
            (
                scale(p.position(), p.mass()),
                cross(p.position(), p.momentum()),
                dot(p.momentum(), p.velocity()).and_then(|v| mul(0.5, v, "lab kinetic energy")),
                cross(p.position(), f),
            )
        },
        |i, (position, angular_term, kinetic_term, torque_term)| {
            let p = &catalog.particles()[i];
            mass.add(p.mass())?;
            momentum.add(p.momentum())?;
            weighted_position.add(position?)?;
            angular.add(angular_term?)?;
            kinetic.add(kinetic_term?)?;
            net_force.add(forces.samples()[i].force())?;
            torque.add(torque_term?)
        },
    )?;
    let mass = mass.value()?;
    let momentum = momentum.value()?;
    let kinetic_lab = kinetic.value()?;
    let mut result = RawDiagnostics {
        mass,
        momentum,
        center_of_mass: None,
        center_velocity: None,
        angular_momentum_origin: angular.value()?,
        angular_momentum_internal: None,
        kinetic_lab,
        kinetic_internal: None,
        pair_energy: forces.pair_energy(),
        hamiltonian_lab: add(kinetic_lab, forces.pair_energy(), "lab Hamiltonian")?,
        net_force: net_force.value()?,
        torque_origin: torque.value()?,
        virial_work: None,
        inertia_internal: None,
        virial_residual: VirialResidual::Undefined(VirialUndefined::EmptyCatalog),
    };
    if catalog.particles().is_empty() {
        return Ok(result);
    }
    let weighted_position = weighted_position.value()?;
    let center = [
        div(weighted_position[0], mass, "COM")?,
        div(weighted_position[1], mass, "COM")?,
        div(weighted_position[2], mass, "COM")?,
    ];
    let velocity = [
        div(momentum[0], mass, "COM velocity")?,
        div(momentum[1], mass, "COM velocity")?,
        div(momentum[2], mass, "COM velocity")?,
    ];
    let mut internal_kinetic = Sum::default();
    let mut internal_angular = VectorSum::default();
    let mut work = Sum::default();
    let mut inertia = Sum::default();
    mhd_parallel::visit_ordered(
        count,
        batch,
        grain,
        |i| {
            let p = &catalog.particles()[i];
            let r = sub(p.position(), center)?;
            let w = sub(p.velocity(), velocity)?;
            let relative_momentum = sub(p.momentum(), scale(velocity, p.mass())?)?;
            let kinetic = mul(0.5, p.mass(), "half mass")
                .and_then(|half| dot(w, w).and_then(|v| mul(half, v, "internal kinetic")));
            Ok::<_, GravityError>((
                kinetic,
                cross(r, relative_momentum),
                dot(r, forces.samples()[i].force()),
                dot(r, r).and_then(|v| mul(p.mass(), v, "internal inertia")),
            ))
        },
        |_, terms| {
            let (k, l, w, i) = terms?;
            internal_kinetic.add(k?)?;
            internal_angular.add(l?)?;
            work.add(w?)?;
            inertia.add(i?)
        },
    )?;
    let k = internal_kinetic.value()?;
    let w = work.value()?;
    let twice_k = mul(2.0, k, "twice internal kinetic")?;
    let denominator = add(twice_k, w.abs(), "virial scale")?;
    result.center_of_mass = Some(center);
    result.center_velocity = Some(velocity);
    result.kinetic_internal = Some(k);
    result.angular_momentum_internal = Some(internal_angular.value()?);
    result.virial_work = Some(w);
    result.inertia_internal = Some(inertia.value()?);
    result.virial_residual = if denominator > 0.0 {
        VirialResidual::Defined(div(
            add(twice_k, w, "virial numerator")?.abs(),
            denominator,
            "virial residual",
        )?)
    } else {
        VirialResidual::Undefined(VirialUndefined::NonpositiveScale)
    };
    Ok(result)
}
