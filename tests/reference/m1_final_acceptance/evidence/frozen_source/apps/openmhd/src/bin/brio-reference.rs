//! Separate 1D conservative-induction comparison. Shares only EOS/Riemann kernels;
//! no Voronoi, Az, curl, or planar potential update is used.
use mhd_core::{FluxMethod, IdealGas, Primitive, riemann};
use std::{
    env,
    fs::File,
    io::{BufWriter, Write},
};

type State = [f64; 6]; // rho, momenta(3), energy, By ; Bx=.75, Bz=0
const CFL: f64 = 0.3;

fn recover(eos: IdealGas, u: State) -> Result<Primitive, String> {
    eos.recover([u[0], u[1], u[2], u[3], u[4]], [0.75, u[5], 0.0])
}

struct Rate {
    values: Vec<State>,
    max_speed: f64,
    fallback_faces: usize,
}

fn rate(eos: IdealGas, states: &[State], dx: f64, boost: f64) -> Result<Rate, String> {
    let n = states.len();
    let q: Vec<_> = states
        .iter()
        .map(|u| recover(eos, *u))
        .collect::<Result<_, _>>()?;
    let mut result = Rate {
        values: vec![[0.0; 6]; n],
        max_speed: 0.0,
        fallback_faces: 0,
    };
    for i in 0..n {
        let j = (i + 1) % n;
        let flux = riemann(eos, q[i], q[j], [1.0, 0.0, 0.0], [boost, 0.0, 0.0])?;
        result.max_speed = result.max_speed.max(flux.max_speed);
        result.fallback_faces += usize::from(flux.method == FluxMethod::HllFallback);
        let f = [
            flux.fluid[0],
            flux.fluid[1],
            flux.fluid[2],
            flux.fluid[3],
            flux.fluid[4],
            flux.induction[1],
        ];
        for (k, v) in f.iter().enumerate() {
            result.values[i][k] -= v / dx;
            result.values[j][k] += v / dx;
        }
    }
    Ok(result)
}

fn minima(eos: IdealGas, states: &[State]) -> Result<[f64; 2], String> {
    let mut result = [f64::INFINITY; 2];
    for u in states {
        let q = recover(eos, *u)?;
        result[0] = result[0].min(q.density);
        result[1] = result[1].min(q.pressure);
    }
    Ok(result)
}

struct Trial {
    states: Vec<State>,
    max_speed: f64,
    fallback_faces: usize,
    minima: [f64; 2],
}

#[derive(Debug)]
enum TrialError {
    Cfl,
    Invalid(String),
}

impl From<String> for TrialError {
    fn from(message: String) -> Self {
        Self::Invalid(message)
    }
}

// Old states are borrowed: a failed trial cannot modify the accepted solution.
fn trial(
    eos: IdealGas,
    states: &[State],
    r0: &Rate,
    dx: f64,
    dt: f64,
    boost: f64,
) -> Result<Trial, TrialError> {
    let stage: Vec<State> = states
        .iter()
        .zip(&r0.values)
        .map(|(u, r)| std::array::from_fn(|k| u[k] + dt * r[k]))
        .collect();
    let r1 = rate(eos, &stage, dx, boost)?;
    let max_speed = r0.max_speed.max(r1.max_speed);
    if dt > (CFL * dx / max_speed) * (1.0 + 1e-12) {
        return Err(TrialError::Cfl);
    }
    let updated: Vec<State> = states
        .iter()
        .enumerate()
        .map(|(i, u)| {
            std::array::from_fn(|k| u[k] + 0.5 * dt * (r0.values[i][k] + r1.values[i][k]))
        })
        .collect();
    let m0 = minima(eos, &stage)?;
    let m1 = minima(eos, &updated)?;
    Ok(Trial {
        states: updated,
        max_speed,
        fallback_faces: r0.fallback_faces + r1.fallback_faces,
        minima: [m0[0].min(m1[0]), m0[1].min(m1[1])],
    })
}

struct Run {
    states: Vec<State>,
    time: f64,
    steps: usize,
    budget_errors: State,
    minima: [f64; 2],
    signal_distance: f64,
    fallback_faces: usize,
    rejected_steps: usize,
    rejected_cfl: usize,
    rejected_states: usize,
}

fn simulate(n: usize, target: f64, boost: f64) -> Result<Run, String> {
    if !(16..=65536).contains(&n)
        || n % 2 != 0
        || !target.is_finite()
        || !(0.0..=0.1).contains(&target)
        || !boost.is_finite()
    {
        return Err("require even N in [16,65536], finite time in [0,.1] and finite boost".into());
    }
    let eos = IdealGas::new(2.0)?;
    let dx = 2.0 / n as f64;
    let states: Vec<State> = (0..n)
        .map(|i| {
            let (density, pressure, by) = if i < n / 2 {
                (1.0, 1.0, 1.0)
            } else {
                (0.125, 0.1, -1.0)
            };
            let u = eos.conservative(Primitive {
                density,
                pressure,
                velocity: [boost, 0.0, 0.0],
                magnetic: [0.75, by, 0.0],
            })?;
            Ok([u[0], u[1], u[2], u[3], u[4], by])
        })
        .collect::<Result<_, String>>()?;
    let initial: State = std::array::from_fn(|k| states.iter().map(|s| s[k] * dx).sum());
    let mut run = Run {
        minima: minima(eos, &states)?,
        states,
        time: 0.0,
        steps: 0,
        budget_errors: [0.0; 6],
        signal_distance: 0.0,
        fallback_faces: 0,
        rejected_steps: 0,
        rejected_cfl: 0,
        rejected_states: 0,
    };
    while run.time < target {
        let r0 = rate(eos, &run.states, dx, boost)?;
        let mut dt = (CFL * dx / r0.max_speed).min(target - run.time);
        let mut accepted = None;
        for attempt in 0..=16 {
            if !dt.is_finite() || dt <= 0.0 || run.time + dt == run.time {
                return Err("timestep cannot advance time".into());
            }
            match trial(eos, &run.states, &r0, dx, dt, boost) {
                Ok(result) => {
                    accepted = Some(result);
                    break;
                }
                Err(e) => {
                    run.rejected_steps += 1;
                    let reason = match e {
                        TrialError::Cfl => {
                            run.rejected_cfl += 1;
                            "predictor endpoint CFL bound exceeded".to_string()
                        }
                        TrialError::Invalid(message) => {
                            run.rejected_states += 1;
                            message
                        }
                    };
                    if attempt == 16 {
                        return Err(format!("step failed after 16 halvings: {reason}"));
                    }
                    dt *= 0.5;
                }
            }
        }
        let result = accepted.ok_or("no accepted trial")?;
        run.states = result.states;
        run.signal_distance += dt * result.max_speed;
        run.fallback_faces += result.fallback_faces;
        for k in 0..2 {
            run.minima[k] = run.minima[k].min(result.minima[k]);
        }
        run.time = (run.time + dt).min(target);
        run.steps += 1;
    }
    let final_totals: State = std::array::from_fn(|k| run.states.iter().map(|s| s[k] * dx).sum());
    run.budget_errors = std::array::from_fn(|k| {
        (final_totals[k] - initial[k]).abs() / initial[k].abs().max(initial[0])
    });
    if run
        .budget_errors
        .iter()
        .any(|e| !e.is_finite() || *e > 1e-10)
    {
        return Err(format!(
            "reference conservation failure: {:?}",
            run.budget_errors
        ));
    }
    Ok(run)
}

fn run() -> Result<(), String> {
    let args: Vec<_> = env::args().skip(1).collect();
    if !(3..=4).contains(&args.len()) {
        return Err("usage: brio-reference N TIME OUTPUT.csv [BOOST_X]".into());
    }
    let n: usize = args[0].parse().map_err(|_| "invalid N")?;
    let target: f64 = args[1].parse().map_err(|_| "invalid time")?;
    let boost: f64 = args
        .get(3)
        .map_or(Ok(0.0), |s| s.parse())
        .map_err(|_| "invalid boost")?;
    let result = simulate(n, target, boost)?;
    let eos = IdealGas::new(2.0)?;
    let dx = 2.0 / n as f64;
    let mut output = BufWriter::new(File::create(&args[2]).map_err(|e| e.to_string())?);
    writeln!(output, "x,rho,vx,vy,p,bx,by,energy,x_comoving").map_err(|e| e.to_string())?;
    for (i, u) in result.states.iter().enumerate() {
        let q = recover(eos, *u)?;
        let x_comoving = (i as f64 + 0.5) * dx;
        writeln!(
            output,
            "{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},7.5e-1,{:.17e},{:.17e},{:.17e}",
            (x_comoving + boost * result.time).rem_euclid(2.0),
            q.density,
            q.velocity[0],
            q.velocity[1],
            q.pressure,
            q.magnetic[1],
            u[4],
            x_comoving,
        )
        .map_err(|e| e.to_string())?;
    }
    output.flush().map_err(|e| e.to_string())?;
    let budget = result.budget_errors.iter().copied().fold(0.0, f64::max);
    println!(
        "n,time,steps,budget_error,min_rho,min_p,signal_distance,fallback_faces,rejected_steps,boost,budget_mass,budget_px,budget_py,budget_pz,budget_energy,budget_by,rejected_cfl,rejected_states"
    );
    println!(
        "{n},{:.17e},{},{budget:.17e},{:.17e},{:.17e},{:.17e},{},{},{boost:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{},{}",
        result.time,
        result.steps,
        result.minima[0],
        result.minima[1],
        result.signal_distance,
        result.fallback_faces,
        result.rejected_steps,
        result.budget_errors[0],
        result.budget_errors[1],
        result.budget_errors[2],
        result.budget_errors[3],
        result.budget_errors[4],
        result.budget_errors[5],
        result.rejected_cfl,
        result.rejected_states,
    );
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("brio-reference: {e}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn periodic_brio_is_positive_conservative_and_boost_invariant() {
        let base = simulate(64, 0.02, 0.0).unwrap();
        let boosted = simulate(64, 0.02, 2.0).unwrap();
        assert!(base.minima.iter().chain(&boosted.minima).all(|v| *v > 0.0));
        for (u, b) in base.states.iter().zip(&boosted.states) {
            let expected = [
                u[0],
                u[1] + 2.0 * u[0],
                u[2],
                u[3],
                u[4] + 2.0 * u[1] + 2.0 * u[0],
                u[5],
            ];
            for k in 0..6 {
                assert!((expected[k] - b[k]).abs() < 1e-11);
            }
        }
        assert!(
            base.budget_errors
                .iter()
                .chain(&boosted.budget_errors)
                .all(|e| *e < 1e-12)
        );
    }

    #[test]
    fn rejected_trial_leaves_states_unchanged_and_shorter_step_succeeds() {
        let initial = simulate(64, 0.0, 0.0).unwrap();
        let before = initial.states.clone();
        let eos = IdealGas::new(2.0).unwrap();
        let dx = 2.0 / 64.0;
        let r0 = rate(eos, &initial.states, dx, 0.0).unwrap();
        assert!(
            trial(
                eos,
                &initial.states,
                &r0,
                dx,
                100.0 * dx / r0.max_speed,
                0.0
            )
            .is_err()
        );
        assert_eq!(initial.states, before);
        let accepted = trial(eos, &initial.states, &r0, dx, 0.1 * dx / r0.max_speed, 0.0).unwrap();
        assert!(accepted.minima.iter().all(|v| *v > 0.0));
        for k in 0..6 {
            let change: f64 = accepted
                .states
                .iter()
                .zip(&before)
                .map(|(a, b)| a[k] - b[k])
                .sum();
            assert!(change.abs() < 1e-12);
        }
    }
}
