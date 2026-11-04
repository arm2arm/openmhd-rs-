use std::env;
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::process::ExitCode;

use mhd_vector_pot::{Case, Grid, Reconstruction, Simulation, Snapshot, Vec2};

const HELP: &str = "Kinematic 2D reference; prescribed velocity, no coupled MHD fluid update.
Usage: field-loop [options]
  --case loop|smooth          default: loop
  --n N                       square periodic grid, N >= 4 (default: 64)
  --mesh fixed|comoving        default: fixed
  --vx V --vy V                fluid velocity (default: 2, 1)
  --time T                     final time (default: 1)
  --cfl C                      in (0,0.5], default: 0.4
  --limiter mc|unlimited       default: mc for loop, unlimited for smooth
  --output PATH                optional final cell CSV, with provenance comments
  --help                       print this help
Stdout contains one CSV header and one diagnostics row.
";

struct Options {
    case: Case,
    n: usize,
    comoving: bool,
    velocity: Vec2,
    time: f64,
    cfl: f64,
    reconstruction: Reconstruction,
    output: Option<PathBuf>,
}

fn parse(args: impl Iterator<Item = String>) -> Result<Option<Options>, String> {
    let mut options = Options {
        case: Case::Loop,
        n: 64,
        comoving: false,
        velocity: [2.0, 1.0],
        time: 1.0,
        cfl: 0.4,
        reconstruction: Reconstruction::MonotonizedCentral,
        output: None,
    };
    let mut limiter = None;
    let mut args = args;
    while let Some(flag) = args.next() {
        if flag == "--help" || flag == "-h" {
            return Ok(None);
        }
        if !matches!(
            flag.as_str(),
            "--case"
                | "--n"
                | "--mesh"
                | "--vx"
                | "--vy"
                | "--time"
                | "--cfl"
                | "--limiter"
                | "--output"
        ) {
            return Err(format!("unknown option: {flag}"));
        }
        let value = args
            .next()
            .ok_or_else(|| format!("missing value for {flag}"))?;
        match flag.as_str() {
            "--case" => {
                options.case = match value.as_str() {
                    "loop" => Case::Loop,
                    "smooth" => Case::Smooth,
                    _ => return Err("--case must be loop or smooth".into()),
                }
            }
            "--n" => options.n = value.parse().map_err(|_| "--n must be an integer")?,
            "--mesh" => {
                options.comoving = match value.as_str() {
                    "fixed" => false,
                    "comoving" => true,
                    _ => return Err("--mesh must be fixed or comoving".into()),
                }
            }
            "--vx" => options.velocity[0] = number(&flag, &value)?,
            "--vy" => options.velocity[1] = number(&flag, &value)?,
            "--time" => options.time = number(&flag, &value)?,
            "--cfl" => options.cfl = number(&flag, &value)?,
            "--limiter" => {
                limiter = Some(match value.as_str() {
                    "mc" => Reconstruction::MonotonizedCentral,
                    "unlimited" => Reconstruction::Unlimited,
                    _ => return Err("--limiter must be mc or unlimited".into()),
                })
            }
            "--output" => options.output = Some(PathBuf::from(value)),
            _ => unreachable!(),
        }
    }
    options.reconstruction = limiter.unwrap_or(match options.case {
        Case::Smooth => Reconstruction::Unlimited,
        Case::Loop => Reconstruction::MonotonizedCentral,
    });
    Ok(Some(options))
}

fn number(flag: &str, value: &str) -> Result<f64, String> {
    value
        .parse()
        .map_err(|_| format!("{flag} must be a number"))
}

fn write_cells(
    options: &Options,
    simulation: &Simulation,
    snapshot: &Snapshot,
) -> Result<(), String> {
    let Some(path) = &options.output else {
        return Ok(());
    };
    let file = File::create(path).map_err(|e| format!("{}: {e}", path.display()))?;
    let mut output = BufWriter::new(file);
    let mut write = || -> std::io::Result<()> {
        writeln!(
            output,
            "# model=kinematic_cartesian_2d; precision=f64; units=nondimensional; boundary=periodic"
        )?;
        writeln!(
            output,
            "# case={}; n={}; v={:?}; mesh={}; time={:.17e}; cfl={}; limiter={}",
            options.case.name(),
            options.n,
            options.velocity,
            if options.comoving {
                "comoving"
            } else {
                "fixed"
            },
            simulation.time(),
            options.cfl,
            options.reconstruction.name()
        )?;
        writeln!(
            output,
            "# package_version={}; no_gas_update=true; mean_B=0; phi=0; resistivity=0",
            env!("CARGO_PKG_VERSION")
        )?;
        writeln!(
            output,
            "x,y,az,bx,by,az_exact,bx_exact,by_exact,div_central,div_face_mc"
        )?;
        let grid = simulation.grid();
        for j in 0..grid.ny() {
            for i in 0..grid.nx() {
                let k = grid.index(i, j);
                let [x, y] = simulation.position(i, j);
                let (az_exact, [bx_exact, by_exact]) = simulation.exact(i, j);
                writeln!(
                    output,
                    "{x:.17e},{y:.17e},{:.17e},{:.17e},{:.17e},{az_exact:.17e},{bx_exact:.17e},{by_exact:.17e},{:.17e},{:.17e}",
                    simulation.az()[k],
                    snapshot.b[k][0],
                    snapshot.b[k][1],
                    snapshot.div_central[k],
                    snapshot.div_face_mc[k]
                )?;
            }
        }
        output.flush()
    };
    write().map_err(|e| format!("{}: {e}", path.display()))
}

fn run(options: Options) -> Result<(), String> {
    let mesh_velocity = if options.comoving {
        options.velocity
    } else {
        [0.0; 2]
    };
    let mut simulation = Simulation::new(
        Grid::new(options.n, options.n)?,
        options.case,
        options.velocity,
        mesh_velocity,
        options.reconstruction,
        options.cfl,
    )?;
    simulation.advance_to(options.time)?;
    let snapshot = simulation.snapshot();
    write_cells(&options, &simulation, &snapshot)?;
    let m = &snapshot.metrics;
    println!(
        "case,n,mesh,vx,vy,time,cfl,limiter,steps,az_l1,b_l1,az_integral,az_integral_relative_drift,az_min,az_max,mean_bx,mean_by,magnetic_energy,magnetic_energy_ratio,div_central_rms,div_central_max,div_face_mc_rms,div_face_mc_max"
    );
    println!(
        "{},{},{},{:.17e},{:.17e},{:.17e},{},{},{},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
        options.case.name(),
        options.n,
        if options.comoving {
            "comoving"
        } else {
            "fixed"
        },
        options.velocity[0],
        options.velocity[1],
        simulation.time(),
        options.cfl,
        options.reconstruction.name(),
        simulation.steps(),
        m.az_l1,
        m.b_l1,
        m.az_integral,
        m.az_integral_relative_drift,
        m.az_min,
        m.az_max,
        m.mean_b[0],
        m.mean_b[1],
        m.magnetic_energy,
        m.magnetic_energy_ratio,
        m.div_central_rms,
        m.div_central_max,
        m.div_face_mc_rms,
        m.div_face_mc_max
    );
    Ok(())
}

fn main() -> ExitCode {
    let result = match parse(env::args().skip(1)) {
        Ok(Some(options)) => run(options),
        Ok(None) => {
            print!("{HELP}");
            return ExitCode::SUCCESS;
        }
        Err(error) => Err(error),
    };
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("field-loop: {error}\nUse --help for usage.");
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_unknown_or_missing_options() {
        for args in [vec!["--typo"], vec!["--n"], vec!["--case", "other"]] {
            assert!(parse(args.into_iter().map(String::from)).is_err());
        }
    }

    #[test]
    fn case_selects_default_limiter_and_explicit_override_wins() {
        let args = ["--case", "smooth", "--vx", "-2"];
        let options = parse(args.into_iter().map(String::from)).unwrap().unwrap();
        assert_eq!(options.reconstruction, Reconstruction::Unlimited);
        assert_eq!(options.velocity[0], -2.0);
        let args = ["--limiter", "mc", "--case", "smooth"];
        let options = parse(args.into_iter().map(String::from)).unwrap().unwrap();
        assert_eq!(options.reconstruction, Reconstruction::MonotonizedCentral);
    }
}
