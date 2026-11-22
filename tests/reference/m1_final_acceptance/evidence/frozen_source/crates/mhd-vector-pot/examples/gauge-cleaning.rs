//! Reproducible manufactured gauge-mode audit; analytic derivatives, no gas/mesh.
use mhd_vector_pot::gauge::Cleaning;
use std::f64::consts::TAU;

fn main() -> Result<(), String> {
    let c = Cleaning::default();
    let k = TAU;
    let cs = 1.0;
    let radius = 0.1;
    let time = 0.5;
    let initial: [f64; 2] = [0.01, 0.02];
    let normalization = initial[0].hypot(initial[1]);
    let kappa = c.beta() * cs / radius;
    let omega = (c.alpha() * cs * cs * k * k - 0.25 * kappa * kappa).sqrt();
    let (sin, cos) = (omega * time).sin_cos();
    let damping = (-0.5 * kappa * time).exp();
    let exact = [
        damping * ((cos + 0.5 * kappa * sin / omega) * initial[0] + k * sin / omega * initial[1]),
        damping
            * (-c.alpha() * cs * cs * k * sin / omega * initial[0]
                + (cos - 0.5 * kappa * sin / omega) * initial[1]),
    ];
    println!("method,n,dt,time,k,cs,radius,alpha,beta,a,p,exact_a,exact_p,relative_error,order");
    for frozen in [true, false] {
        let method = if frozen {
            "paper_frozen_source"
        } else {
            "reevaluated_heun_comparator"
        };
        let mut previous: Option<f64> = None;
        for n in [40, 80, 160, 320] {
            let dt = time / n as f64;
            let mut a = initial[0];
            let mut p = initial[1];
            for _ in 0..n {
                let stage = c.begin(p, -k * a, cs, radius)?;
                let ps = stage.predicted_phi(dt)?;
                let astar = a + dt * k * p;
                let next_p = if frozen {
                    stage.finish_phi(dt, radius)?
                } else {
                    p + 0.5 * dt * (stage.initial_rate() + c.rate(ps, -k * astar, cs, radius)?)
                };
                a += 0.5 * dt * k * (p + ps);
                p = next_p;
            }
            let error = (a - exact[0]).hypot(p - exact[1]) / normalization;
            let order = previous
                .map(|prior| format!("{:.17e}", (prior / error).log2()))
                .unwrap_or_default();
            println!(
                "{method},{n},{dt:.17e},{time:.17e},{k:.17e},{cs:.17e},{radius:.17e},{:.17e},{:.17e},{a:.17e},{p:.17e},{:.17e},{:.17e},{error:.17e},{order}",
                c.alpha(),
                c.beta(),
                exact[0],
                exact[1]
            );
            previous = Some(error);
        }
    }
    Ok(())
}
