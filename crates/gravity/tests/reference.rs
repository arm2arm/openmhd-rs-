//! Written, unexecuted small G1 controls. Rational expressions below are manual
//! targets, not independently evaluated high-precision endpoint references.
use gravity::diagnostics::{measure, VirialResidual, VirialUndefined};
use gravity::direct::{evaluate, DirectConfig, Evaluation};
use gravity::kdk::{timestep_ceiling, KdkSystem};
use gravity::kernel::pair;
use gravity::softening::{FixedPlummer, GravityModel, SofteningClass};
use gravity::state::{Catalog, CollisionlessKind, Particle, ParticleMetadata};
use gravity::units::{CgsQuantity, Quantity, UnitSystem};
use gravity::{CacheField, EntityId, GravityError, ParticleId, Vec3};

fn id(counter: u64) -> ParticleId { ParticleId::new(EntityId::new(1, counter)) }
fn metadata() -> ParticleMetadata {
    ParticleMetadata { kind: CollisionlessKind::DarkMatter, softening: SofteningClass::new(0), component: 0, galaxy: 0 }
}
fn particle(counter: u64, mass: f64, position: Vec3, momentum: Vec3) -> Particle {
    Particle::from_momentum(id(counter), mass, position, momentum, metadata()).unwrap()
}
fn model() -> GravityModel {
    GravityModel::new(UnitSystem::dimensionless_g1(), FixedPlummer::new(4.0, SofteningClass::new(0)).unwrap())
}
fn axis() -> Catalog {
    Catalog::new(0.0, 0, vec![particle(1, 2.0, [0.0; 3], [0.0; 3]), particle(2, 3.0, [3.0, 0.0, 0.0], [0.0; 3])]).unwrap()
}
fn evaluated(c: &Catalog) -> Evaluation { evaluate(c, &model(), &DirectConfig::default()).unwrap() }
fn close(actual: f64, expected: f64, scale: f64) {
    assert!(actual.is_finite() && expected.is_finite() && scale.is_finite() && scale >= 0.0);
    if scale == 0.0 { assert_eq!(actual, expected); }
    else { assert!((actual - expected).abs() <= 5e-13 * scale, "actual={actual:?}, expected={expected:?}, scale={scale:?}"); }
}
fn vector_close(actual: Vec3, expected: Vec3, scale: f64) {
    for (a, e) in actual.into_iter().zip(expected) { close(a, e, scale); }
}
fn changed(c: &Catalog, transform: impl Fn(&Particle) -> Particle) -> Catalog {
    Catalog::new(c.time(), c.revision(), c.particles().iter().map(transform).collect()).unwrap()
}
fn raw_equal(a: &Evaluation, b: &Evaluation) {
    assert_eq!(a.pair_count(), b.pair_count());
    assert_eq!(a.samples().len(), b.samples().len());
    assert_eq!(a.pair_energy().to_bits(), b.pair_energy().to_bits());
    for (x, y) in a.samples().iter().zip(b.samples()) {
        assert_eq!(x.force().map(f64::to_bits), y.force().map(f64::to_bits));
        assert_eq!(x.specific_potential().to_bits(), y.specific_potential().to_bits());
    }
}

#[test]
fn empty_catalog_has_no_pairs_and_no_com_or_timestep() {
    let c = Catalog::new(0.0, 0, vec![]).unwrap();
    let e = evaluated(&c);
    assert!(e.samples().is_empty());
    assert_eq!(e.pair_count(), 0);
    assert_eq!(e.pair_energy(), 0.0);
    let d = measure(&c, &model(), &DirectConfig::default(), &e).unwrap();
    assert_eq!(d.mass, 0.0);
    assert_eq!(d.center_of_mass, None);
    assert_eq!(d.virial_residual, VirialResidual::Undefined(VirialUndefined::EmptyCatalog));
    assert_eq!(timestep_ceiling(&c, &model()), Err(GravityError::EmptyTimestep));
    let mut system = KdkSystem::new(c, model(), DirectConfig::default()).unwrap();
    let checkpoint = system.checkpoint().canonical_bytes();
    let time_bits = system.catalog().time().to_bits();
    let revision = system.catalog().revision();
    assert_eq!(system.try_step(0.125).unwrap_err(), GravityError::EmptyTimestep);
    assert_eq!(system.checkpoint().canonical_bytes(), checkpoint);
    assert_eq!(system.catalog().time().to_bits(), time_bits);
    assert_eq!(system.catalog().revision(), revision);
}

#[test]
fn one_source_including_zero_payload_has_no_self_force_or_energy() {
    let p = Particle::from_momentum(ParticleId::new(EntityId::new(0, 0)), 2.0, [1.0, -2.0, 3.0], [0.0; 3], metadata()).unwrap();
    let c = Catalog::new(0.0, 0, vec![p.clone()]).unwrap();
    let e = evaluated(&c);
    assert_eq!(e.pair_count(), 0);
    assert_eq!(e.pair_energy(), 0.0);
    assert_eq!(e.samples()[0].force(), [0.0; 3]);
    assert_eq!(e.samples()[0].specific_potential(), 0.0);
    assert_eq!(pair(&model(), &p, &p).unwrap_err(), GravityError::SelfPair);
    let d = measure(&c, &model(), &DirectConfig::default(), &e).unwrap();
    assert_eq!(d.virial_residual, VirialResidual::Undefined(VirialUndefined::NonpositiveScale));
}

#[test]
fn eps4_axis_force_potential_energy_and_acceleration() {
    let c = axis();
    let e = evaluated(&c);
    assert_eq!(e.pair_count(), 1);
    vector_close(e.sample(id(1)).unwrap().force(), [18.0 / 125.0, 0.0, 0.0], 18.0 / 125.0);
    assert_eq!(e.sample(id(2)).unwrap().force(), e.sample(id(1)).unwrap().force().map(|v| -v));
    close(e.sample(id(1)).unwrap().specific_potential(), -3.0 / 5.0, 3.0 / 5.0);
    close(e.sample(id(2)).unwrap().specific_potential(), -2.0 / 5.0, 2.0 / 5.0);
    close(e.pair_energy(), -6.0 / 5.0, 6.0 / 5.0);
    vector_close(e.acceleration(&c, &model(), &DirectConfig::default(), id(1)).unwrap(), [9.0 / 125.0, 0.0, 0.0], 9.0 / 125.0);
    vector_close(e.acceleration(&c, &model(), &DirectConfig::default(), id(2)).unwrap(), [-6.0 / 125.0, 0.0, 0.0], 6.0 / 125.0);
    close(e.net_force_scale(), 36.0 / 125.0, 36.0 / 125.0);
    close(e.torque_scale(), 54.0 / 125.0, 54.0 / 125.0);
    let half_mass_phi = 0.5 * c.particles().iter().map(|p| p.mass() * e.sample(p.id()).unwrap().specific_potential()).sum::<f64>();
    close(half_mass_phi, -6.0 / 5.0, 6.0 / 5.0);
}

#[test]
fn eps4_oblique_pair_raw_torques_cancel() {
    let c = Catalog::new(0.0, 0, vec![particle(1, 2.0, [-4.0, 1.0, 2.0], [0.0; 3]), particle(2, 3.0, [-3.0, 3.0, 4.0], [0.0; 3])]).unwrap();
    let e = evaluated(&c);
    vector_close(e.sample(id(1)).unwrap().force(), [6.0 / 125.0, 12.0 / 125.0, 12.0 / 125.0], 18.0 / 125.0);
    let d = measure(&c, &model(), &DirectConfig::default(), &e).unwrap();
    vector_close(d.net_force, [0.0; 3], 36.0 / 125.0);
    // Twice the largest manual individual torque component, a fixed stronger
    // small-control scale; the full G-SYMMETRY norm scale remains independent.
    vector_close(d.torque_origin, [0.0; 3], 120.0 / 125.0);
    close(e.pair_energy(), -6.0 / 5.0, 6.0 / 5.0);
}

#[test]
fn coincident_distinct_sources_keep_negative_pair_energy() {
    let c = Catalog::new(0.0, 0, vec![particle(1, 2.0, [1.0, -2.0, 3.0], [0.0; 3]), particle(2, 3.0, [1.0, -2.0, 3.0], [0.0; 3])]).unwrap();
    let e = evaluated(&c);
    assert_eq!(e.pair_count(), 1);
    assert_eq!(e.samples()[0].force(), [0.0; 3]);
    assert_eq!(e.samples()[1].force(), [0.0; 3]);
    assert_eq!(e.pair_energy(), -3.0 / 2.0);
    assert_eq!(e.samples()[0].specific_potential(), -3.0 / 4.0);
    assert_eq!(e.samples()[1].specific_potential(), -1.0 / 2.0);
    assert_eq!(e.net_force_scale(), 0.0);
}

#[test]
fn eps4_three_source_superposition_retains_colocated_pair() {
    let mut particles = axis().particles().to_vec();
    particles.push(particle(3, 5.0, [0.0; 3], [0.0; 3]));
    let c = Catalog::new(0.0, 0, particles).unwrap();
    let e = evaluated(&c);
    assert_eq!(e.pair_count(), 3);
    for (counter, force, phi) in [(1, 18.0 / 125.0, -37.0 / 20.0), (2, -63.0 / 125.0, -7.0 / 5.0), (3, 45.0 / 125.0, -11.0 / 10.0)] {
        let s = e.sample(id(counter)).unwrap();
        vector_close(s.force(), [force, 0.0, 0.0], force.abs());
        close(s.specific_potential(), phi, phi.abs());
    }
    close(e.pair_energy(), -67.0 / 10.0, 67.0 / 10.0);
    close(e.net_force_scale(), 126.0 / 125.0, 126.0 / 125.0);
    close(e.torque_scale(), 189.0 / 125.0, 189.0 / 125.0);
}

#[test]
fn equal_masses_have_equal_and_opposite_accelerations() {
    let c = Catalog::new(0.0, 0, vec![particle(1, 2.0, [0.0; 3], [0.0; 3]), particle(2, 2.0, [3.0, 0.0, 0.0], [0.0; 3])]).unwrap();
    let e = evaluated(&c);
    vector_close(e.samples()[0].force(), [12.0 / 125.0, 0.0, 0.0], 12.0 / 125.0);
    assert_eq!(e.acceleration(&c, &model(), &DirectConfig::default(), id(1)).unwrap(), e.acceleration(&c, &model(), &DirectConfig::default(), id(2)).unwrap().map(|v| -v));
}

#[test]
fn exact_rounded_mass_ratio_uses_pinned_dyadic_q() {
    let q = f64::from_bits(0x3eb0_c6f7_a0b5_ed8d);
    assert_eq!(q.to_bits(), (1e-6_f64).to_bits());
    // q = 4722366482869645 * 2^-72; not the exact rational 1/1000000.
    let c = Catalog::new(0.0, 0, vec![particle(1, 1.0, [0.0; 3], [0.0; 3]), particle(2, q, [3.0, 0.0, 0.0], [0.0; 3])]).unwrap();
    let e = evaluated(&c);
    vector_close(e.samples()[0].force(), [3.0 * q / 125.0, 0.0, 0.0], 3.0 * q / 125.0);
    assert_eq!(e.samples()[1].force(), e.samples()[0].force().map(|v| -v));
    close(e.pair_energy(), -q / 5.0, q / 5.0);
    close(e.samples()[0].specific_potential(), -q / 5.0, q / 5.0);
    close(e.samples()[1].specific_potential(), -1.0 / 5.0, 1.0 / 5.0);
    vector_close(e.acceleration(&c, &model(), &DirectConfig::default(), id(2)).unwrap(), [-3.0 / 125.0, 0.0, 0.0], 3.0 / 125.0);
}

#[test]
fn input_permutation_has_identical_sorted_state_and_evaluation() {
    let c = axis();
    let mut p = c.particles().to_vec();
    p.reverse();
    let permuted = Catalog::new(c.time(), c.revision(), p).unwrap();
    assert_eq!(c.state_identity(), permuted.state_identity());
    assert_eq!(evaluated(&c).canonical_bytes(), evaluated(&permuted).canonical_bytes());
}

#[test]
fn species_and_analysis_relabel_change_pins_without_changing_physics() {
    let c = axis();
    let relabelled = changed(&c, |p| {
        let mut tags = metadata();
        tags.kind = CollisionlessKind::Star;
        tags.component = 7;
        tags.galaxy = 9;
        Particle::from_momentum(p.id(), p.mass(), p.position(), p.momentum(), tags).unwrap()
    });
    assert_ne!(c.source_identity(), relabelled.source_identity());
    assert_ne!(c.state_identity(), relabelled.state_identity());
    raw_equal(&evaluated(&c), &evaluated(&relabelled));
}

#[test]
fn persistent_id_relabel_is_not_storage_identity() {
    let c = axis();
    let renamed = changed(&c, |p| Particle::from_momentum(ParticleId::new(EntityId::new(8, p.id().entity().counter())), p.mass(), p.position(), p.momentum(), metadata()).unwrap());
    assert_ne!(c.source_identity(), renamed.source_identity());
    raw_equal(&evaluated(&c), &evaluated(&renamed));
}

#[test]
fn isolated_translation_preserves_raw_pair_answers() {
    let c = axis();
    let moved = changed(&c, |p| {
        let x = p.position();
        Particle::from_momentum(p.id(), p.mass(), [x[0] + 8.0, x[1] - 4.0, x[2] + 2.0], p.momentum(), metadata()).unwrap()
    });
    raw_equal(&evaluated(&c), &evaluated(&moved));
    assert_ne!(c.source_identity(), moved.source_identity());
}

#[test]
fn right_angle_rotation_covaries_raw_force() {
    let c = axis();
    let rotated = changed(&c, |p| {
        let x = p.position();
        Particle::from_momentum(p.id(), p.mass(), [-x[1], x[0], x[2]], p.momentum(), metadata()).unwrap()
    });
    let e = evaluated(&rotated);
    vector_close(e.samples()[0].force(), [0.0, 18.0 / 125.0, 0.0], 18.0 / 125.0);
    close(e.pair_energy(), -6.0 / 5.0, 6.0 / 5.0);
}

#[test]
fn invalid_particle_data_and_duplicate_ids_are_rejected() {
    for mass in [0.0, -1.0, f64::NAN, f64::INFINITY] {
        assert!(Particle::from_momentum(id(1), mass, [0.0; 3], [0.0; 3], metadata()).is_err());
    }
    assert!(Particle::from_momentum(id(1), 1.0, [f64::NAN, 0.0, 0.0], [0.0; 3], metadata()).is_err());
    assert!(Particle::from_momentum(id(1), 1.0, [0.0; 3], [f64::INFINITY, 0.0, 0.0], metadata()).is_err());
    assert!(Particle::from_momentum(id(1), f64::MIN_POSITIVE, [0.0; 3], [f64::MAX, 0.0, 0.0], metadata()).is_err());
    let p = particle(1, 1.0, [0.0; 3], [0.0; 3]);
    assert_eq!(Catalog::new(0.0, 0, vec![p.clone(), p]).unwrap_err(), GravityError::DuplicateId(id(1)));
    assert!(Catalog::new(f64::NAN, 0, vec![]).is_err());
}

#[test]
fn invalid_model_and_unrepresentable_scales_are_rejected() {
    for epsilon in [0.0, -1.0, f64::NAN, f64::INFINITY, f64::MAX, f64::from_bits(1)] {
        assert!(FixedPlummer::new(epsilon, SofteningClass::new(0)).is_err());
    }
    for bad in [0.0, -1.0, f64::NAN, f64::INFINITY] {
        assert!(UnitSystem::si(bad, 1.0, 1.0, 1.0, 1.0, "synthetic-SI").is_err());
        assert!(UnitSystem::si(1.0, bad, 1.0, 1.0, 1.0, "synthetic-SI").is_err());
        assert!(UnitSystem::si(1.0, 1.0, bad, 1.0, 1.0, "synthetic-SI").is_err());
        assert!(UnitSystem::si(1.0, 1.0, 1.0, bad, 1.0, "synthetic-SI").is_err());
        assert!(UnitSystem::si(1.0, 1.0, 1.0, 1.0, bad, "synthetic-SI").is_err());
    }
    assert!(UnitSystem::si(1.0, 1.0, 1.0, 1.0, 1.0, " ").is_err());
    assert!(UnitSystem::si(f64::MAX, 1.0, 1.0, 1.0, 1.0, "overflow").is_err());
}

#[test]
fn wrong_common_softening_class_is_rejected_even_with_one_source() {
    let mut tags = metadata();
    tags.softening = SofteningClass::new(1);
    let p = Particle::from_momentum(id(1), 1.0, [0.0; 3], [0.0; 3], tags).unwrap();
    let c = Catalog::new(0.0, 0, vec![p]).unwrap();
    assert_eq!(evaluate(&c, &model(), &DirectConfig::default()).unwrap_err(), GravityError::UnsupportedSofteningClass);
}

#[test]
fn nonrepresentable_displacement_or_pair_energy_fails_closed() {
    let c = Catalog::new(0.0, 0, vec![particle(1, 1.0, [-f64::MAX, 0.0, 0.0], [0.0; 3]), particle(2, 1.0, [f64::MAX, 0.0, 0.0], [0.0; 3])]).unwrap();
    assert!(evaluate(&c, &model(), &DirectConfig::default()).is_err());
    let c = Catalog::new(0.0, 0, vec![particle(1, f64::MAX, [0.0; 3], [0.0; 3]), particle(2, 2.0, [0.0; 3], [0.0; 3])]).unwrap();
    assert!(evaluate(&c, &model(), &DirectConfig::default()).is_err());
}

#[test]
fn physical_units_have_one_checked_si_owner_and_explicit_cgs_boundary() {
    // Deliberately simple synthetic SI constants, not an astronomical profile.
    let u = UnitSystem::si(2.0, 8.0, 4.0, 2.0, 1.0, "synthetic-SI-v1").unwrap();
    assert_eq!(u.g_code(), 0.5);
    for (q, expected) in [(Quantity::Time, 0.5), (Quantity::Density, 1.0), (Quantity::Pressure, 16.0), (Quantity::Energy, 128.0), (Quantity::Momentum, 32.0), (Quantity::AngularMomentum, 64.0), (Quantity::Acceleration, 8.0), (Quantity::SpecificPotential, 16.0), (Quantity::Force, 64.0), (Quantity::MagneticField, 4.0), (Quantity::VectorPotential, 8.0), (Quantity::Power, 256.0), (Quantity::VolumetricPower, 32.0)] {
        assert_eq!(u.scale(q).unwrap(), expected);
        assert_eq!(u.from_si(q, u.to_si(q, 2.0).unwrap()).unwrap(), 2.0);
    }
    close(u.to_cgs(CgsQuantity::Density, 1.0).unwrap(), 1e-3, 1e-3);
    assert_eq!(u.to_cgs(CgsQuantity::SpecificEnergy, 1.0).unwrap(), 160000.0);
    assert_eq!(u.to_cgs(CgsQuantity::Pressure, 1.0).unwrap(), 160.0);
    assert_eq!(u.to_cgs(CgsQuantity::VolumetricPower, 1.0).unwrap(), 320.0);
    for q in [CgsQuantity::Density, CgsQuantity::SpecificEnergy, CgsQuantity::Pressure, CgsQuantity::VolumetricPower] {
        close(u.from_cgs(q, u.to_cgs(q, 2.0).unwrap()).unwrap(), 2.0, 2.0);
    }
    assert!(u.to_si(Quantity::Length, f64::NAN).is_err());
    assert!(u.to_si(Quantity::Energy, f64::MAX).is_err());
}

#[test]
fn dimensionless_fixture_cannot_silently_convert_to_si() {
    let u = UnitSystem::dimensionless_g1();
    assert_eq!(u.g_code(), 1.0);
    assert!(!u.is_physical());
    assert_eq!(u.to_si(Quantity::Mass, 1.0), Err(GravityError::PhysicalUnitsRequired));
    let physical_g1 = UnitSystem::si(1.0, 1.0, 1.0, 1.0, 1.0, "synthetic-SI").unwrap();
    assert_ne!(u.identity(), physical_g1.identity());
}

#[test]
fn synthetic_si_rescaling_preserves_force_potential_and_energy_units() {
    let a = UnitSystem::si(1.0, 1.0, 1.0, 1.0, 1.0, "synthetic-SI-A").unwrap();
    let b = UnitSystem::si(2.0, 8.0, 4.0, 1.0, 1.0, "synthetic-SI-B").unwrap();
    let mut outputs = Vec::new();
    for u in [&a, &b] {
        let p = |counter, mass, x| particle(counter, u.from_si(Quantity::Mass, mass).unwrap(), [u.from_si(Quantity::Length, x).unwrap(), 0.0, 0.0], [0.0; 3]);
        let c = Catalog::new(0.0, 0, vec![p(1, 2.0, 0.0), p(2, 3.0, 3.0)]).unwrap();
        let m = GravityModel::new(u.clone(), FixedPlummer::new(u.from_si(Quantity::Length, 4.0).unwrap(), SofteningClass::new(0)).unwrap());
        let e = evaluate(&c, &m, &DirectConfig::default()).unwrap();
        outputs.push([
            u.to_si(Quantity::Force, e.samples()[0].force()[0]).unwrap(),
            u.to_si(Quantity::SpecificPotential, e.samples()[0].specific_potential()).unwrap(),
            u.to_si(Quantity::Energy, e.pair_energy()).unwrap(),
        ]);
    }
    for o in outputs {
        close(o[0], 18.0 / 125.0, 18.0 / 125.0);
        close(o[1], -3.0 / 5.0, 3.0 / 5.0);
        close(o[2], -6.0 / 5.0, 6.0 / 5.0);
    }
    assert_ne!(a.identity(), b.identity());
}

#[test]
fn cache_rejects_real_changed_epoch_sources_momentum_and_backend() {
    let c = axis();
    let e = evaluated(&c);
    let cfg = DirectConfig::default();
    let later = Catalog::new(1.0, 0, c.particles().to_vec()).unwrap();
    assert_eq!(e.validate_for(&later, &model(), &cfg), Err(GravityError::CacheMismatch(CacheField::Time)));
    let revision = Catalog::new(0.0, 1, c.particles().to_vec()).unwrap();
    assert_eq!(e.validate_for(&revision, &model(), &cfg), Err(GravityError::CacheMismatch(CacheField::StateRevision)));
    let moved = changed(&c, |p| Particle::from_momentum(p.id(), p.mass(), [p.position()[0] + 1.0, 0.0, 0.0], p.momentum(), metadata()).unwrap());
    assert_eq!(e.validate_for(&moved, &model(), &cfg), Err(GravityError::CacheMismatch(CacheField::Sources)));
    let kicked = changed(&c, |p| Particle::from_momentum(p.id(), p.mass(), p.position(), [1.0, 0.0, 0.0], metadata()).unwrap());
    assert_eq!(e.validate_for(&kicked, &model(), &cfg), Err(GravityError::CacheMismatch(CacheField::State)));
    let retagged = changed(&c, |p| {
        let mut tags = metadata();
        tags.component = 1;
        Particle::from_momentum(p.id(), p.mass(), p.position(), p.momentum(), tags).unwrap()
    });
    assert_eq!(c.source_identity(), retagged.source_identity());
    assert_eq!(e.validate_for(&retagged, &model(), &cfg), Err(GravityError::CacheMismatch(CacheField::State)));
    assert_eq!(e.validate_for(&c, &model(), &DirectConfig::new(1)), Err(GravityError::CacheMismatch(CacheField::Backend)));
    let different_g = GravityModel::new(UnitSystem::si(1.0, 1.0, 1.0, 2.0, 1.0, "synthetic").unwrap(), FixedPlummer::new(4.0, SofteningClass::new(0)).unwrap());
    assert_eq!(e.validate_for(&c, &different_g, &cfg), Err(GravityError::CacheMismatch(CacheField::GravitationalConstant)));
    let different_epsilon = GravityModel::new(UnitSystem::dimensionless_g1(), FixedPlummer::new(2.0, SofteningClass::new(0)).unwrap());
    assert_eq!(e.validate_for(&c, &different_epsilon, &cfg), Err(GravityError::CacheMismatch(CacheField::Softening)));
    let different_class_table = GravityModel::new(UnitSystem::dimensionless_g1(), FixedPlummer::new(4.0, SofteningClass::new(1)).unwrap());
    assert_eq!(e.validate_for(&c, &different_class_table, &cfg), Err(GravityError::CacheMismatch(CacheField::Model)));
    let physical_g1 = GravityModel::new(UnitSystem::si(1.0, 1.0, 1.0, 1.0, 1.0, "synthetic").unwrap(), FixedPlummer::new(4.0, SofteningClass::new(0)).unwrap());
    assert_eq!(e.validate_for(&c, &physical_g1, &cfg), Err(GravityError::CacheMismatch(CacheField::Units)));
}

#[test]
fn free_kdk_exact_manual_drift_and_undefined_internal_virial() {
    let c = Catalog::new(0.0, 0, vec![particle(1, 2.0, [1.0, -2.0, 3.0], [2.0, -4.0, 6.0])]).unwrap();
    let mut system = KdkSystem::new(c, model(), DirectConfig::default()).unwrap();
    let report = system.try_step(1.0 / 8.0).unwrap();
    assert_eq!(system.catalog().particles()[0].position(), [9.0 / 8.0, -9.0 / 4.0, 27.0 / 8.0]);
    assert_eq!(system.catalog().particles()[0].momentum(), [2.0, -4.0, 6.0]);
    assert_eq!(report.after.kinetic_lab, 14.0);
    assert_eq!(report.after.hamiltonian_lab, 14.0);
    assert_eq!(report.after.kinetic_internal, Some(0.0));
    assert_eq!(report.after.virial_residual, VirialResidual::Undefined(VirialUndefined::NonpositiveScale));
    system.forces().validate_for(system.catalog(), system.model(), system.config()).unwrap();
}

#[test]
fn pair_kdk_retains_actual_rounded_drift_and_full_endpoint_cache() {
    let mut system = KdkSystem::new(axis(), model(), DirectConfig::default()).unwrap();
    let report = system.try_step(1.0 / 8.0).unwrap();
    // Ideal symbolic positions only; a future independent endpoint oracle must
    // evaluate at the retained actual binary64 report.drift_endpoint positions.
    close(report.drift_endpoint.particle(id(1)).unwrap().position()[0], 9.0 / 16000.0, 9.0 / 16000.0);
    close(report.drift_endpoint.particle(id(2)).unwrap().position()[0], 23997.0 / 8000.0, 3.0);
    assert_eq!(system.catalog().time(), 1.0 / 8.0);
    assert_eq!(system.catalog().revision(), 1);
    assert_eq!(report.drift_endpoint.source_identity(), system.catalog().source_identity());
    assert_ne!(report.drift_endpoint.state_identity(), system.catalog().state_identity());
    assert_eq!(report.drift_forces.validate_for(system.catalog(), system.model(), system.config()), Err(GravityError::CacheMismatch(CacheField::State)));
    system.forces().validate_for(system.catalog(), system.model(), system.config()).unwrap();
    assert_eq!(report.drift_forces.samples()[0].force(), system.forces().samples()[0].force());
    vector_close(report.after.momentum, [0.0; 3], 1.0);
}

#[test]
fn rejected_dt_and_revision_leave_complete_accepted_state_unchanged() {
    let mut s = KdkSystem::new(axis(), model(), DirectConfig::default()).unwrap();
    let initial = s.checkpoint().canonical_bytes();
    for dt in [0.0, -0.125, f64::NAN, f64::INFINITY, 1.0] {
        assert!(s.try_step(dt).is_err());
        assert_eq!(s.checkpoint().canonical_bytes(), initial);
    }
    let c = Catalog::new(0.0, u64::MAX, axis().particles().to_vec()).unwrap();
    let mut s = KdkSystem::new(c, model(), DirectConfig::default()).unwrap();
    let initial = s.checkpoint().canonical_bytes();
    assert_eq!(s.try_step(0.125).unwrap_err(), GravityError::RevisionOverflow);
    assert_eq!(s.checkpoint().canonical_bytes(), initial);

    // G1_ORBIT_CAMPAIGN_AMENDMENT: std arithmetic is only a guard-branch
    // input, not an independent high-precision period/orbit reference.
    // Resting momenta suffice: the ceiling depends on total mass/epsilon,
    // not the missing, independently rounded circular-orbit momenta.
    let epsilon = 0.1_f64;
    let orbit_model = GravityModel::new(
        UnitSystem::dimensionless_g1(),
        FixedPlummer::new(epsilon, SofteningClass::new(0)).unwrap(),
    );
    let orbit_catalog = Catalog::new(
        2.0,
        7,
        vec![
            particle(1, 1.0, [0.0; 3], [0.0; 3]),
            particle(2, 2.0, [1.0, 0.0, 0.0], [0.0; 3]),
        ],
    ).unwrap();
    let guard_period = 2.0 * std::f64::consts::PI
        * (1.0 + epsilon * epsilon).powf(0.75)
        / (orbit_model.g() * 3.0).sqrt();
    assert!(guard_period.is_finite() && guard_period > 0.0);
    let ceiling = timestep_ceiling(&orbit_catalog, &orbit_model).unwrap();
    let mut orbit = KdkSystem::new(orbit_catalog, orbit_model, DirectConfig::default()).unwrap();
    let checkpoint = orbit.checkpoint().canonical_bytes();
    let time_bits = orbit.catalog().time().to_bits();
    let revision = orbit.catalog().revision();
    for divisor in [128.0, 256.0, 512.0, 1024.0] {
        let dt = guard_period / divisor;
        assert!(dt > ceiling, "original divisor={divisor}");
        assert_eq!(orbit.try_step(dt).unwrap_err(), GravityError::StepAboveCeiling);
        assert_eq!(orbit.checkpoint().canonical_bytes(), checkpoint);
        assert_eq!(orbit.catalog().time().to_bits(), time_bits);
        assert_eq!(orbit.catalog().revision(), revision);
    }
}

#[test]
fn rounded_nonadvancing_time_is_atomic() {
    let c = Catalog::new(1e20, 0, axis().particles().to_vec()).unwrap();
    let mut s = KdkSystem::new(c, model(), DirectConfig::default()).unwrap();
    let initial = s.checkpoint().canonical_bytes();
    assert_eq!(s.try_step(0.125).unwrap_err(), GravityError::TimeNotAdvanced);
    assert_eq!(s.checkpoint().canonical_bytes(), initial);
}

#[test]
fn failed_trial_evaluation_leaves_catalog_and_force_cache_unchanged() {
    // Exact dyadics: x=3*2^510, v=2^511. For h=1/2 the co-located
    // sources drift to x=2^512, whose squared norm overflows. Initial
    // x^2=9*2^1020 and v^2=2^1022 are finite. No reference is evaluated here.
    let x = f64::from_bits(0x5fe8_0000_0000_0000);
    let v = f64::from_bits(0x5fe0_0000_0000_0000);
    let c = Catalog::new(0.0, 0, vec![particle(1, 1.0, [x, 0.0, 0.0], [v, 0.0, 0.0]), particle(2, 1.0, [x, 0.0, 0.0], [v, 0.0, 0.0])]).unwrap();
    let m = GravityModel::new(UnitSystem::dimensionless_g1(), FixedPlummer::new(8.0, SofteningClass::new(0)).unwrap());
    let mut s = KdkSystem::new(c, m, DirectConfig::default()).unwrap();
    let initial = s.checkpoint().canonical_bytes();
    assert!(matches!(s.try_step(0.5), Err(GravityError::Nonrepresentable("dot product"))));
    assert_eq!(s.checkpoint().canonical_bytes(), initial);
}

#[test]
fn in_memory_restart_preserves_short_fixed_step_history_exactly() {
    let mut original = KdkSystem::new(axis(), model(), DirectConfig::default()).unwrap();
    original.try_step(1.0 / 32.0).unwrap();
    let checkpoint = original.checkpoint();
    let mut restarted = KdkSystem::restore(&checkpoint).unwrap();
    for dt in [1.0 / 32.0, 1.0 / 64.0, 1.0 / 32.0] {
        original.try_step(dt).unwrap();
        restarted.try_step(dt).unwrap();
        assert_eq!(original.checkpoint().canonical_bytes(), restarted.checkpoint().canonical_bytes());
    }
}

#[test]
fn boost_keeps_internal_diagnostics_and_raw_lab_energy_transform() {
    let c = axis();
    let boost = [2.0, -1.0, 0.5];
    let boosted = changed(&c, |p| Particle::from_velocity(p.id(), p.mass(), p.position(), boost, metadata()).unwrap());
    let base = measure(&c, &model(), &DirectConfig::default(), &evaluated(&c)).unwrap();
    let b = measure(&boosted, &model(), &DirectConfig::default(), &evaluated(&boosted)).unwrap();
    assert_eq!(b.momentum, [10.0, -5.0, 2.5]);
    assert_eq!(b.kinetic_internal, base.kinetic_internal);
    assert_eq!(b.virial_work, base.virial_work);
    assert_eq!(b.virial_residual, base.virial_residual);
    close(b.kinetic_lab, 105.0 / 8.0, 105.0 / 8.0);
    close(b.hamiltonian_lab - base.hamiltonian_lab, 105.0 / 8.0, 105.0 / 8.0);
    raw_equal(&evaluated(&c), &evaluated(&boosted));
    let mut base_system = KdkSystem::new(c, model(), DirectConfig::default()).unwrap();
    let mut boost_system = KdkSystem::new(boosted, model(), DirectConfig::default()).unwrap();
    for dt in [1.0 / 32.0, 1.0 / 64.0] {
        let original = base_system.try_step(dt).unwrap();
        let shifted = boost_system.try_step(dt).unwrap();
        let t = boost_system.catalog().time();
        for (p, q) in base_system.catalog().particles().iter().zip(boost_system.catalog().particles()) {
            let expected_x = [p.position()[0] + 2.0 * t, p.position()[1] - t, p.position()[2] + 0.5 * t];
            let expected_p = [p.momentum()[0] + 2.0 * p.mass(), p.momentum()[1] - p.mass(), p.momentum()[2] + 0.5 * p.mass()];
            vector_close(q.position(), expected_x, 3.0);
            vector_close(q.momentum(), expected_p, 10.0);
        }
        let dot_boost_p = 2.0 * original.after.momentum[0] - original.after.momentum[1] + 0.5 * original.after.momentum[2];
        close(shifted.after.hamiltonian_lab - original.after.hamiltonian_lab, dot_boost_p + 105.0 / 8.0, 105.0 / 8.0);
    }
}

#[test]
fn raw_diagnostics_keep_nonzero_lab_momentum_and_angular_momentum() {
    let c = Catalog::new(0.0, 0, vec![particle(1, 2.0, [-4.0, 1.0, 2.0], [1.0, 2.0, 3.0])]).unwrap();
    let d = measure(&c, &model(), &DirectConfig::default(), &evaluated(&c)).unwrap();
    assert_eq!(d.momentum, [1.0, 2.0, 3.0]);
    assert_eq!(d.angular_momentum_origin, [-1.0, 14.0, -9.0]);
    assert_eq!(d.kinetic_lab, 7.0 / 2.0);
    assert_eq!(d.kinetic_internal, Some(0.0));
    assert_eq!(d.hamiltonian_lab, 7.0 / 2.0);
}

#[test]
fn short_fixed_list_velocity_reversal_keeps_raw_residuals() {
    let initial = axis();
    let mut s = KdkSystem::new(initial.clone(), model(), DirectConfig::default()).unwrap();
    for dt in [1.0 / 64.0, 1.0 / 32.0] { s.try_step(dt).unwrap(); }
    let reversed = changed(s.catalog(), |p| Particle::from_momentum(p.id(), p.mass(), p.position(), p.momentum().map(|v| -v), metadata()).unwrap());
    let mut backward = KdkSystem::new(reversed, model(), DirectConfig::default()).unwrap();
    for dt in [1.0 / 32.0, 1.0 / 64.0] { backward.try_step(dt).unwrap(); }
    for (p, old) in backward.catalog().particles().iter().zip(initial.particles()) {
        vector_close(p.position(), old.position(), 3.0);
        vector_close(p.momentum(), old.momentum().map(|v| -v), 1.0);
    }
    // Positive-time velocity reversal is a short algebra check, not G-KDK's
    // preregistered 100-period fixed-list reversal/temporal-order acceptance.
}
