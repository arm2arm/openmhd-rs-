use gravity::{
    EntityId, ParticleId,
    direct::{DirectConfig, evaluate},
    kdk::KdkSystem,
    softening::{FixedPlummer, GravityModel, SofteningClass},
    state::{Catalog, CollisionlessKind, Particle, ParticleMetadata},
    units::UnitSystem,
};
use std::num::NonZeroUsize;

#[test]
fn unique_pairs_and_kdk_restart_are_bitwise_layout_invariant() {
    let count = 129;
    let class = SofteningClass::new(0);
    let particles = (0..count)
        .rev()
        .map(|i| {
            let x = [i % 7, (i / 7) % 5, i / 35].map(|n| 0.125 * n as f64);
            let p = [
                0.0001 * (i % 3) as f64,
                0.0002 * (i % 5) as f64,
                -0.0001 * (i % 7) as f64,
            ];
            Particle::from_momentum(
                ParticleId::new(EntityId::new(9, i)),
                0.0125,
                x,
                p,
                ParticleMetadata {
                    kind: CollisionlessKind::DarkMatter,
                    softening: class,
                    component: 0,
                    galaxy: 0,
                },
            )
            .unwrap()
        })
        .collect();
    let initial = Catalog::new(0.0, 0, particles).unwrap();
    let model = GravityModel::new(
        UnitSystem::dimensionless_g1(),
        FixedPlummer::new(0.1875, class).unwrap(),
    );
    let cfg = DirectConfig::default();
    let advance = || {
        let f = evaluate(&initial, &model, &cfg).unwrap();
        assert_eq!(f.pair_count(), count * (count - 1) / 2);
        let mut system = KdkSystem::new(initial.clone(), model.clone(), cfg.clone()).unwrap();
        system.try_step(0.0001).unwrap();
        let mut resumed = KdkSystem::restore(&system.checkpoint()).unwrap();
        system.try_step(0.0001).unwrap();
        resumed.try_step(0.0001).unwrap();
        assert_eq!(
            system.checkpoint().canonical_bytes(),
            resumed.checkpoint().canonical_bytes()
        );
        (
            f.canonical_bytes(),
            system.checkpoint().canonical_bytes(),
            system.forces().canonical_bytes(),
        )
    };
    let n: NonZeroUsize = std::env::var("OPENMHD_TEST_THREADS")
        .unwrap_or("2".into())
        .parse()
        .unwrap();
    assert_eq!(advance(), mhd_parallel::with_team(n, advance).unwrap());
}

#[test]
fn portable_restart_validates_the_saved_force_generation_and_model() {
    let cfg = DirectConfig::default();
    let class = SofteningClass::new(1);
    let model = |eps| {
        GravityModel::new(
            UnitSystem::dimensionless_g1(),
            FixedPlummer::new(eps, class).unwrap(),
        )
    };
    let particles = (0..4)
        .map(|i| {
            Particle::from_velocity(
                ParticleId::new(EntityId::new(7, i)),
                0.125,
                [i as f64, 0.25, 0.],
                [0., 0.125, 0.],
                ParticleMetadata {
                    kind: CollisionlessKind::Star,
                    softening: class,
                    component: 2,
                    galaxy: 1,
                },
            )
            .unwrap()
        })
        .collect();
    let n = std::env::var("OPENMHD_TEST_THREADS")
        .unwrap_or("2".into())
        .parse()
        .unwrap();
    let layout = mhd_parallel::layout::LocalLayout(n);
    let mut serial = KdkSystem::new(
        Catalog::new(0., 0, particles).unwrap(),
        model(0.25),
        cfg.clone(),
    )
    .unwrap();
    serial.try_step(0.001).unwrap();
    let data = gravity::restart::encode(&serial);
    let mut resumed =
        gravity::restart::decode_on(&data, model(0.25), cfg.clone(), &layout).unwrap();
    serial.try_step(0.001).unwrap();
    resumed.try_step_on(0.001, &layout).unwrap();
    assert_eq!(
        gravity::restart::encode(&serial),
        gravity::restart::encode(&resumed)
    );
    assert!(gravity::restart::decode_on(&data, model(0.125), cfg.clone(), &layout).is_err());
    let mut damaged = data;
    damaged[20] ^= 1;
    assert!(gravity::restart::decode_on(&damaged, model(0.25), cfg, &layout).is_err());
}
