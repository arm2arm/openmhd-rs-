//! Opt-in limiter of the A-advection gradients; docs/M1_STANDING_WAVE_PLAN.md.
//! The default must stay bitwise unchanged. These are operator/coupling
//! checks on small meshes, not the registered M1 convergence gate.
use mhd_core::RiemannSolver;
use mhd_vector_pot::benchmarks::alfven_initial;
use mhd_vector_pot::general::{Config, Motion, Profile, Simulation};
use mhd_vector_pot::operators::PotentialLimiter;
use moving_mesh::Mesh;

fn standing(n: usize, jitter: f64, config: Config) -> Simulation {
    Simulation::new(
        Mesh::lattice(n, n, [1.; 2], jitter).unwrap(),
        Config {
            profile: Profile::BulkFrameHeunQuadraticV1,
            riemann_solver: RiemannSolver::HlldPressure,
            accelerated_projection: true,
            projection_screening: 1.,
            mean_magnetic: [1., 0., 0.],
            motion: Motion::Fixed,
            max_dt: 0.002,
            ..config
        },
        |x| alfven_initial(x, 1., [0.; 3]),
    )
    .unwrap()
}

fn limited(limiter: Option<PotentialLimiter>) -> Config {
    Config {
        potential_limiter: limiter,
        ..Config::default()
    }
}

/// Cells whose transverse (physical wave) potential gradients are clipped.
fn clipped_transverse(sim: &Simulation) -> usize {
    let fit = sim.magnetic_fit().unwrap();
    fit.raw
        .iter()
        .zip(&fit.limited)
        .filter(|(raw, limited)| raw[1] != limited[1] || raw[2] != limited[2])
        .count()
}

fn magnetic_difference(a: &Simulation, b: &Simulation) -> f64 {
    a.primitives()
        .unwrap()
        .iter()
        .zip(b.primitives().unwrap())
        .flat_map(|(p, q)| (0..3).map(move |k| (p.magnetic[k] - q.magnetic[k]).abs()))
        .fold(0., f64::max)
}

#[test]
fn explicit_historical_choices_are_bitwise_the_defaults() {
    assert_eq!(
        Config::default().effective_potential_limiter(),
        PotentialLimiter::NeighbourExtrema
    );
    let unlimited = Config {
        limited: false,
        ..Config::default()
    };
    assert_eq!(
        unlimited.effective_potential_limiter(),
        PotentialLimiter::Unlimited
    );
    for jitter in [0., 0.15] {
        for (implicit, explicit) in [
            (
                Config::default(),
                limited(Some(PotentialLimiter::NeighbourExtrema)),
            ),
            (
                unlimited.clone(),
                Config {
                    potential_limiter: Some(PotentialLimiter::Unlimited),
                    ..unlimited.clone()
                },
            ),
        ] {
            let mut a = standing(12, jitter, implicit);
            let mut b = standing(12, jitter, explicit);
            a.advance_to(0.006).unwrap();
            b.advance_to(0.006).unwrap();
            assert!(a.counters().steps >= 3);
            assert_eq!(format!("{:?}", a.state()), format!("{:?}", b.state()));
        }
    }
}

#[test]
fn only_the_advection_gradient_copy_depends_on_the_limiter() {
    // Curl, div(A) and the unlimited gradients are identical at a common state.
    let fits: Vec<_> = [
        None,
        Some(PotentialLimiter::SmoothExtrema),
        Some(PotentialLimiter::Unlimited),
    ]
    .into_iter()
    .map(|limiter| standing(16, 0.15, limited(limiter)).magnetic_fit().unwrap())
    .collect();
    for fit in &fits[1..] {
        assert_eq!(fit.raw, fits[0].raw);
        assert_eq!(fit.magnetic, fits[0].magnetic);
        assert_eq!(fit.divergence_a, fits[0].divergence_a);
        assert_eq!(fit.gradient_phi, fits[0].gradient_phi);
    }
    assert_eq!(fits[2].limited, fits[2].raw);
    assert_ne!(fits[0].limited, fits[0].raw);
}

#[test]
fn smooth_extrema_matches_unlimited_advection_on_a_resolved_standing_wave() {
    for jitter in [0., 0.15] {
        let mut standard = standing(24, jitter, limited(None));
        let mut relaxed = standing(24, jitter, limited(Some(PotentialLimiter::SmoothExtrema)));
        let mut unlimited = standing(24, jitter, limited(Some(PotentialLimiter::Unlimited)));
        let cells = standard.state().mesh.cells.len();
        let initially_clipped = clipped_transverse(&standard);
        assert!(initially_clipped > 0);
        assert_eq!(
            clipped_transverse(&relaxed),
            0,
            "jitter {jitter}: resolved potential extrema clipped at t=0"
        );
        for sim in [&mut standard, &mut relaxed, &mut unlimited] {
            sim.advance_to(0.006).unwrap();
            assert!(sim.counters().steps >= 3 && sim.counters().rejected_state == 0);
            let d = sim.diagnostics().unwrap();
            assert!(d.min_density > 0. && d.min_pressure > 0.);
            assert!(d.normalized_budget.iter().all(|x| x.abs() < 1e-10));
        }
        let clipped = clipped_transverse(&relaxed);
        let agreement = magnetic_difference(&relaxed, &unlimited);
        let standard_effect = magnetic_difference(&standard, &unlimited);
        eprintln!(
            "jitter {jitter}: standard clips {initially_clipped}/{cells} at t=0; relaxed clips \
             {clipped} at t=.006; |B relaxed-unlimited|={agreement:e}, \
             |B standard-unlimited|={standard_effect:e}"
        );
        assert_eq!(
            clipped, 0,
            "jitter {jitter}: resolved potential extrema clipped after evolution"
        );
        // The standard limiter measurably changes the field. On the regular
        // mesh B is independent of the gauge component A_x, so an inactive
        // relaxed limiter reproduces unlimited advection to solver roundoff.
        // On the jittered mesh A_x enters the discrete curl and is not
        // constrained by this test; only a clear separation is required.
        assert!(standard_effect > 1e-8, "{standard_effect:e}");
        if jitter == 0. {
            assert!(agreement < 1e-10, "{agreement:e}");
        } else {
            assert!(agreement < 0.1 * standard_effect, "{agreement:e}");
        }
    }
}
