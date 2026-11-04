//! Separate 1D conservative-induction comparison. Shares only EOS/Riemann kernels;
//! no Voronoi, Az, curl, or planar potential update is used.
use mhd_core::{IdealGas, Primitive, riemann};
use std::{
    env,
    fs::File,
    io::{BufWriter, Write},
};

type State = [f64; 6]; // rho, momenta(3), energy, By ; Bx=.75, Bz=0

fn recover(eos: IdealGas, u: State) -> Result<Primitive, String> {
    eos.recover([u[0], u[1], u[2], u[3], u[4]], [0.75, u[5], 0.0])
}

fn rate(eos: IdealGas, states: &[State], dx: f64) -> Result<(Vec<State>, f64), String> {
    let n = states.len();
    let q: Vec<_> = states
        .iter()
        .map(|u| recover(eos, *u))
        .collect::<Result<_, _>>()?;
    let mut result = vec![[0.0; 6]; n];
    let mut max_speed: f64 = 0.0;
    for i in 0..n {
        let j = (i + 1) % n;
        let flux = riemann(eos, q[i], q[j], [1.0, 0.0, 0.0], [0.0; 3])?;
        max_speed = max_speed.max(flux.max_speed);
        let f = [
            flux.fluid[0],
            flux.fluid[1],
            flux.fluid[2],
            flux.fluid[3],
            flux.fluid[4],
            flux.induction[1],
        ];
        for (k, v) in f.iter().enumerate() {
            result[i][k] -= v / dx;
            result[j][k] += v / dx;
        }
    }
    Ok((result, 0.3 * dx / max_speed))
}

fn run() -> Result<(), String> {
    let args: Vec<_> = env::args().skip(1).collect();
    if args.len() != 3 {
        return Err("usage: brio-reference N TIME OUTPUT.csv".into());
    }
    let n: usize = args[0].parse().map_err(|_| "invalid N")?;
    let target: f64 = args[1].parse().map_err(|_| "invalid time")?;
    if !(16..=65536).contains(&n)
        || n % 2 != 0
        || !target.is_finite()
        || !(0.0..=0.1).contains(&target)
    {
        return Err("require even N in [16,65536] and finite time in [0,.1]".into());
    }
    let eos = IdealGas::new(2.0)?;
    let dx = 2.0 / n as f64;
    let mut states: Vec<State> = (0..n)
        .map(|i| {
            let (density, pressure, by) = if i < n / 2 {
                (1.0, 1.0, 1.0)
            } else {
                (0.125, 0.1, -1.0)
            };
            let u = eos
                .conservative(Primitive {
                    density,
                    pressure,
                    velocity: [0.0; 3],
                    magnetic: [0.75, by, 0.0],
                })
                .unwrap();
            [u[0], u[1], u[2], u[3], u[4], by]
        })
        .collect();
    let initial: State = std::array::from_fn(|k| states.iter().map(|s| s[k] * dx).sum());
    let mut time = 0.0;
    let mut steps = 0;
    while time < target {
        let (r0, bound) = rate(eos, &states, dx)?;
        let dt = bound.min(target - time);
        let stage: Vec<State> = states
            .iter()
            .zip(&r0)
            .map(|(u, r)| std::array::from_fn(|k| u[k] + dt * r[k]))
            .collect();
        let (r1, _) = rate(eos, &stage, dx)?;
        for i in 0..n {
            for k in 0..6 {
                states[i][k] += 0.5 * dt * (r0[i][k] + r1[i][k]);
            }
        }
        for u in &states {
            recover(eos, *u)?;
        }
        time = (time + dt).min(target);
        steps += 1;
    }
    let final_totals: State = std::array::from_fn(|k| states.iter().map(|s| s[k] * dx).sum());
    let budget = (0..6)
        .map(|k| (final_totals[k] - initial[k]).abs() / initial[k].abs().max(initial[0]))
        .fold(0.0, f64::max);
    if budget > 1e-10 {
        return Err(format!("reference conservation failure: {budget}"));
    }
    let mut output = BufWriter::new(File::create(&args[2]).map_err(|e| e.to_string())?);
    writeln!(output, "x,rho,vx,vy,p,bx,by").map_err(|e| e.to_string())?;
    for (i, u) in states.iter().enumerate() {
        let q = recover(eos, *u)?;
        writeln!(
            output,
            "{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},7.5e-1,{:.17e}",
            (i as f64 + 0.5) * dx,
            q.density,
            q.velocity[0],
            q.velocity[1],
            q.pressure,
            q.magnetic[1]
        )
        .map_err(|e| e.to_string())?;
    }
    output.flush().map_err(|e| e.to_string())?;
    println!("n,time,steps,budget_error\n{n},{time:.17e},{steps},{budget:.17e}");
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("brio-reference: {e}");
        std::process::exit(1);
    }
}
