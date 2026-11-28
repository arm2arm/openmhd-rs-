use mhd_core::{IdealGas, Primitive};
use mhd_vector_pot::moving3::*;
use moving_mesh::three_d::{fit::SampleKey3, operator_mesh::CellId, *};
use std::collections::BTreeMap;

fn sites() -> Vec<Generator3> {
    (0..27)
        .map(|j| Generator3 {
            id: SampleKey3::from_words(7, j as u64, Image3::ZERO).owner,
            position: [j % 3, (j / 3) % 3, j / 9].map(|k| [0.125, 0.4375, 0.8125][k]),
            winding: Image3::ZERO,
        })
        .collect()
}
fn domain() -> Domain3 {
    Domain3 {
        anchor: [0.; 3],
        width: [1.; 3],
        boundary: Boundary3::Periodic,
    }
}
fn model() -> Model3 {
    Model3 {
        eos: IdealGas::new(5. / 3.).unwrap(),
        mean_field: [0.25, -0.125, 0.5],
        reference_velocity: [0.5, -0.25, 0.125],
        field_scale: 1.,
    }
}
fn flow(s: &[Generator3]) -> BTreeMap<CellId, Vec3> {
    s.iter()
        .map(|g| (g.id, g.position.map(|x| x - 0.5)))
        .collect()
}
fn init(c: &CellGeometry3) -> Result<CellState3> {
    let m = model();
    let q = m.eos.conservative(Primitive {
        density: 1.,
        pressure: 1.,
        velocity: m.reference_velocity,
        magnetic: m.mean_field,
    })?;
    Ok(CellState3 {
        conserved: q.map(|x| x * c.volume),
        potential: [0.; 3],
        phi: 0.,
    })
}
#[test]
fn finite_step_preserves_uniform_gas_and_advances_constant_gauge() {
    let s = sites();
    let mut sim = PeriodicMhd3::new(domain(), &s, flow(&s), model(), init).unwrap();
    let before: Vec<_> = sim.geometry().cells().iter().map(|c| c.volume).collect();
    let dt = 1. / 256.;
    let report = sim.step(dt).unwrap();
    assert!(
        before
            .iter()
            .zip(sim.geometry().cells())
            .any(|(&v, c)| (v - c.volume).abs() > 1e-5)
    );
    for (state, &b) in sim.primitives().iter().zip(sim.field()) {
        assert!((state.density - 1.).abs() < 1e-11 && (state.pressure - 1.).abs() < 1e-11);
        for (k, component) in b.into_iter().enumerate() {
            assert!(
                (state.velocity[k] - model().reference_velocity[k]).abs() < 1e-11
                    && (component - model().mean_field[k]).abs() < 1e-11
            );
        }
    }
    for s in [report.predictor, report.corrector] {
        assert!(s.max_gcl_residual < 1e-12);
        assert_eq!(s.exchanges.len(), sim.geometry().faces().len());
        assert!(s.solve.true_residual < 1e-9);
    }
    assert_eq!(
        sim.gauge_offset(),
        mhd_core::cross(model().reference_velocity, model().mean_field).map(|v| v * dt)
    );
    assert_eq!(sim.origin().winding.0, [0, -1, 0]);
}
#[test]
fn rejected_timestep_preserves_state_origin_gauge_and_geometry() {
    let sites = sites();
    let mut sim = PeriodicMhd3::new(domain(), &sites, flow(&sites), model(), init).unwrap();
    let epoch = sim.geometry().epoch();
    let q = sim.cells().to_vec();
    let field = sim.field().to_vec();
    for dt in [f64::NAN, 0., -1., 2. * sim.timestep_limit()] {
        assert!(sim.step(dt).is_err());
        assert_eq!(sim.geometry().epoch(), epoch);
        assert_eq!(sim.time(), 0.);
        assert_eq!(sim.origin().position, domain().anchor);
        assert_eq!(sim.origin().winding, Image3::ZERO);
        assert_eq!(sim.gauge_offset(), [0.; 3]);
        assert_eq!(sim.field(), &field);
        for (a, b) in sim.cells().iter().zip(&q) {
            assert_eq!(a.potential, b.potential);
            assert_eq!(a.conserved, b.conserved);
            assert_eq!(a.phi, b.phi);
        }
    }
}
#[test]
fn unproved_irregular_deformation_keeps_the_accepted_epoch() {
    let coords = include_str!("fixtures/m2c_shared_jitter.bits");
    let s: Vec<_> = coords
        .lines()
        .enumerate()
        .map(|(i, row)| {
            let coords: Vec<_> = row
                .split_whitespace()
                .map(|v| f64::from_bits(u64::from_str_radix(v, 16).unwrap()))
                .collect();
            let site = sites()[i];
            Generator3 {
                position: coords.try_into().unwrap(),
                ..site
            }
        })
        .collect();
    let mut sim = PeriodicMhd3::new(domain(), &s, flow(&s), model(), init).unwrap();
    let epoch = sim.geometry().epoch();
    let error = sim.step(1. / 1024.).unwrap_err();
    assert!(error.to_string().contains("event resolution"), "{error}");
    assert_eq!(sim.geometry().epoch(), epoch);
    assert_eq!(sim.time(), 0.);
}
#[test]
fn nonpositive_thermal_energy_is_rejected_at_initialization() {
    let s = sites();
    let err = PeriodicMhd3::new(domain(), &s, flow(&s), model(), |c| {
        let mut q = init(c)?;
        q.conserved[4] = 0.;
        Ok(q)
    });
    assert!(matches!(err,Err(e) if e.to_string().contains("pressure")));
}
