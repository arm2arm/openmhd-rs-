use mhd_planar::{Case, Config, Simulation};

#[test]
fn magnetic_pressure_accelerates_initially_stationary_gas() {
    // Initial gas pressure is uniform: acceleration must come from B.
    // B_y=a*k*sin(kx), so dv_x/dt=-a^2*k^3*sin(kx)*cos(kx).
    use std::f64::consts::PI;
    let mut errors = Vec::new();
    for n in [16, 32, 64] {
        let mut sim = Simulation::new(Config {
            case: Case::MagneticPressure,
            nx: n,
            ny: 4,
            ..Config::default()
        })
        .unwrap();
        sim.advance_to(1e-4).unwrap();
        let q = sim.primitives().unwrap();
        let k = 2.0 * PI;
        let mut error = 0.0;
        for (i, q) in q.iter().enumerate() {
            let x = sim.mesh.cells[i].centroid[0];
            let expected = -0.02_f64.powi(2) * k.powi(3) * (k * x).sin() * (k * x).cos();
            error += sim.mesh.cells[i].volume * (q.velocity[0] / sim.time - expected).abs();
        }
        errors.push(error);
        assert!(sim.diagnostics().unwrap().relative_budget_error < 1e-10);
    }
    assert!(
        errors[2] < 0.005 && errors[2] < errors[1] && errors[1] < errors[0],
        "{errors:?}"
    );
}

#[test]
fn coupled_uniform_state_on_regular_and_irregular_mesh() {
    for jitter in [0.0, 0.15] {
        let mut sim = Simulation::new(Config {
            case: Case::Uniform,
            nx: 6,
            ny: 6,
            jitter,
            mesh_velocity: [0.7, -0.8],
            ..Config::default()
        })
        .unwrap();
        let initial = sim.primitives().unwrap();
        sim.advance_to(0.1).unwrap();
        for (a, b) in sim.primitives().unwrap().iter().zip(initial) {
            for (x, y) in [a.density, a.pressure, a.magnetic[0], a.magnetic[1]]
                .iter()
                .zip([b.density, b.pressure, b.magnetic[0], b.magnetic[1]])
            {
                assert!((x - y).abs() < 1e-10, "{x} != {y}");
            }
        }
        assert!(sim.diagnostics().unwrap().relative_budget_error < 1e-10);
    }
}

#[test]
fn smooth_entropy_wave_errors_decrease() {
    let mut errors = Vec::new();
    for n in [8, 16, 32] {
        let mut sim = Simulation::new(Config {
            case: Case::Smooth,
            nx: n,
            ny: 4,
            ..Config::default()
        })
        .unwrap();
        sim.advance_to(0.2).unwrap();
        let d = sim.diagnostics().unwrap();
        assert!(d.relative_budget_error < 1e-10);
        errors.push(d.smooth_l1);
    }
    assert!(errors[1] < errors[0] && errors[2] < errors[1], "{errors:?}");
}

#[test]
fn vortex_feedback_and_galilean_boost() {
    let config = Config {
        nx: 8,
        ny: 8,
        ..Config::default()
    };
    let mut base = Simulation::new(config.clone()).unwrap();
    let initial = base.primitives().unwrap();
    let mut boosted = Simulation::new(Config {
        boost: [2.0, -1.0],
        mesh_velocity: [2.0, -1.0],
        ..config
    })
    .unwrap();
    base.advance_to(0.025).unwrap();
    boosted.advance_to(0.025).unwrap();
    let d = base.diagnostics().unwrap();
    assert!(d.min_density > 0.0 && d.min_pressure > 0.0 && d.relative_budget_error < 1e-10);
    let qb = base.primitives().unwrap();
    let qg = boosted.primitives().unwrap();
    assert!(
        qb.iter()
            .zip(initial)
            .any(|(q, p)| (q.density - p.density).abs() > 1e-5)
    );
    for (b, g) in qb.iter().zip(qg) {
        for (x, y) in [b.density, b.pressure, b.magnetic[0], b.magnetic[1]]
            .iter()
            .zip([g.density, g.pressure, g.magnetic[0], g.magnetic[1]])
        {
            assert!((x - y).abs() < 1e-9, "boost discrepancy {x} != {y}");
        }
    }
}

#[test]
fn brio_wu_remains_physical_and_conservative() {
    let mut sim = Simulation::new(Config {
        case: Case::BrioWu,
        nx: 24,
        ny: 4,
        ..Config::default()
    })
    .unwrap();
    sim.advance_to(0.02).unwrap();
    let d = sim.diagnostics().unwrap();
    assert!(d.min_density > 0.0 && d.min_pressure > 0.0);
    assert!(d.relative_budget_error < 1e-10);
    assert!(d.div_face_rms.is_finite() && d.div_ls_rms.is_finite());
}
