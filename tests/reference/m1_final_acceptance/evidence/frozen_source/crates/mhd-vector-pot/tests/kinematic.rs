use mhd_vector_pot::{Case, Grid, Reconstruction, Simulation};

fn run(n: usize, case: Case, velocity: [f64; 2], mesh: [f64; 2], time: f64) -> Simulation {
    let reconstruction = match case {
        Case::Smooth => Reconstruction::Unlimited,
        Case::Loop => Reconstruction::MonotonizedCentral,
    };
    let mut sim = Simulation::new(
        Grid::new(n, n).unwrap(),
        case,
        velocity,
        mesh,
        reconstruction,
        0.4,
    )
    .unwrap();
    sim.advance_to(time).unwrap();
    assert_eq!(sim.time(), time);
    sim
}

#[test]
fn smooth_transport_and_curl_converge_at_second_order() {
    // Predeclared order >= 1.8 in docs/KINEMATIC_2D.md. Shortened final time for CI.
    let metrics: Vec<_> = [16, 32, 64]
        .into_iter()
        .map(|n| {
            run(n, Case::Smooth, [2.0, 1.0], [0.0; 2], 0.25)
                .snapshot()
                .metrics
        })
        .collect();
    for pair in metrics.windows(2) {
        let az_order = (pair[0].az_l1 / pair[1].az_l1).log2();
        let b_order = (pair[0].b_l1 / pair[1].b_l1).log2();
        assert!(az_order >= 1.8, "Az order {az_order}");
        assert!(b_order >= 1.8, "B order {b_order}");
    }
}

#[test]
fn comoving_loop_preserves_discrete_potential_and_field_exactly() {
    let mut sim = Simulation::new(
        Grid::new(32, 32).unwrap(),
        Case::Loop,
        [2.0, 1.0],
        [2.0, 1.0],
        Reconstruction::MonotonizedCentral,
        0.4,
    )
    .unwrap();
    let initial_az = sim.az().to_vec();
    let initial = sim.snapshot();
    sim.advance_to(1.25).unwrap();
    assert_eq!(sim.az(), initial_az);
    let final_state = sim.snapshot();
    assert_eq!(initial.b, final_state.b);
    assert_eq!(final_state.metrics.magnetic_energy_ratio, 1.0);
    assert_eq!(sim.steps(), 0);
    let centre = (0.5 / 32.0 + 2.0 * 1.25_f64).rem_euclid(1.0);
    assert_eq!(sim.position(0, 0)[0], centre);
}

#[test]
fn loop_limiter_preserves_bounds_and_integral_for_signed_transport() {
    for velocity in [[2.0, 1.0], [-2.0, -1.0], [0.0, -1.0]] {
        let mut sim = Simulation::new(
            Grid::new(24, 24).unwrap(),
            Case::Loop,
            velocity,
            [0.0; 2],
            Reconstruction::MonotonizedCentral,
            0.4,
        )
        .unwrap();
        let initial_max = sim.az().iter().copied().fold(0.0, f64::max);
        sim.advance_to(0.5).unwrap();
        let metrics = sim.snapshot().metrics;
        assert!(
            metrics.az_min >= -1e-12 * initial_max,
            "min {}",
            metrics.az_min
        );
        assert!(metrics.az_max <= initial_max * (1.0 + 1e-12));
        assert!(metrics.az_integral_relative_drift.abs() <= 1e-11);
        assert!(metrics.mean_b.iter().all(|b| b.abs() < 1e-15));
    }
}

#[test]
fn adding_same_boost_to_fluid_and_mesh_preserves_kinematic_solution() {
    let base = run(24, Case::Smooth, [2.0, -1.0], [0.5, 0.25], 0.3);
    let boosted = run(24, Case::Smooth, [10.0, -5.0], [8.5, -3.75], 0.3);
    assert_eq!(base.relative_velocity(), boosted.relative_velocity());
    assert_eq!(base.az(), boosted.az());
    assert_eq!(base.snapshot().b, boosted.snapshot().b);
    // Physical positions differ by boost*t modulo the box.
    let base_position = base.position(0, 0);
    let boosted_position = boosted.position(0, 0);
    for (axis, boost) in [8.0, -4.0].into_iter().enumerate() {
        let expected = (base_position[axis] + boost * 0.3).rem_euclid(1.0);
        assert!((expected - boosted_position[axis]).abs() < 1e-14);
    }
}

#[test]
fn negative_smooth_advection_matches_analytic_translation() {
    let metrics = run(48, Case::Smooth, [-2.0, -1.0], [0.0; 2], 0.25)
        .snapshot()
        .metrics;
    assert!(metrics.az_l1 < 0.03);
    assert!(metrics.b_l1 < 0.4);
}

#[test]
fn temporal_order_against_exact_semidiscrete_fourier_mode() {
    // Independent Fourier-symbol reference removes the fixed spatial error.
    let n = 16;
    let grid = Grid::new(n, n).unwrap();
    let final_time = 0.2;
    let coefficient = |sim: &Simulation| {
        let (mut real, mut imaginary) = (0.0, 0.0);
        for j in 0..n {
            for i in 0..n {
                let phase =
                    std::f64::consts::TAU * ((i as f64 + 0.5) + 2.0 * (j as f64 + 0.5)) / n as f64;
                real += sim.az()[grid.index(i, j)] * phase.cos();
                imaginary -= sim.az()[grid.index(i, j)] * phase.sin();
            }
        }
        [real / (n * n) as f64, imaginary / (n * n) as f64]
    };
    let (mut lambda_real, mut lambda_imaginary) = (0.0, 0.0);
    for (speed, wavenumber) in [(2.0_f64, 1.0), (1.0_f64, 2.0)] {
        let theta = std::f64::consts::TAU * wavenumber / n as f64;
        lambda_real -= 0.5 * speed.abs() * n as f64 * (1.0 - theta.cos()).powi(2);
        lambda_imaginary -= speed * n as f64 * (1.5 * theta.sin() - 0.25 * (2.0 * theta).sin());
    }
    let mut errors = Vec::new();
    for cfl in [0.4, 0.2, 0.1] {
        let mut sim = Simulation::new(
            grid,
            Case::Smooth,
            [2.0, 1.0],
            [0.0; 2],
            Reconstruction::Unlimited,
            cfl,
        )
        .unwrap();
        let initial = coefficient(&sim);
        let amplitude = (lambda_real * final_time).exp();
        let (sine, cosine) = (lambda_imaginary * final_time).sin_cos();
        let exact = [
            amplitude * (initial[0] * cosine - initial[1] * sine),
            amplitude * (initial[0] * sine + initial[1] * cosine),
        ];
        sim.advance_to(final_time).unwrap();
        let actual = coefficient(&sim);
        errors.push((actual[0] - exact[0]).hypot(actual[1] - exact[1]));
    }
    for pair in errors.windows(2) {
        let order = (pair[0] / pair[1]).log2();
        assert!(order >= 1.8, "temporal order {order}");
    }
}
