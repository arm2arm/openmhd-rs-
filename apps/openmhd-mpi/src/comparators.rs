//! Independent reference solvers using the same rank-owned periodic cell/face indices.
use crate::{MpiLayout, Result, save};
use mhd_parallel::layout::Layout;
use mhd_vector_pot::{benchmarks, ct, passive::Passive, transport::Transport};
use moving_mesh::Mesh;
use std::{io::Write, path::Path};

fn row(bytes: &mut Vec<u8>, index: usize, values: impl IntoIterator<Item = f64>) -> Result<()> {
    write!(bytes, "{index}")?;
    for v in values {
        write!(bytes, ",{v:.17e}")?;
    }
    writeln!(bytes)?;
    Ok(())
}

pub fn run(layout: &MpiLayout<'_>, args: &[String], reference: bool) -> Result<()> {
    let [problem, n, jitter, target, directory] = args else {
        return Err(
            "compare2 ct|ct-limited|planar|passive|prescribed N JITTER TIME DIRECTORY".into(),
        );
    };
    if reference && layout.ranks().get() != 1 {
        return Err("serial comparator requires one rank".into());
    }
    let (n, jitter, target) = (n.parse()?, jitter.parse()?, target.parse()?);
    let velocity = [0.5, -0.25];
    let w = [0.125, -0.0625];
    let boost = [w[0], w[1], 0.];
    let mut state = Vec::new();
    let mut faces = Vec::new();
    let steps;
    if problem == "planar" {
        let config = mhd_planar::Config {
            case: mhd_planar::Case::OrszagTang,
            nx: n,
            ny: n,
            jitter,
            mesh_velocity: w,
            boost: w,
            ..Default::default()
        };
        let mut sim = if reference {
            mhd_planar::Simulation::new(config)?
        } else {
            mhd_planar::Simulation::new_on(config, layout)?
        };
        if reference {
            sim.advance_to(target)?
        } else {
            sim.advance_on(target, layout)?
        }
        steps = sim.steps;
        writeln!(
            state,
            "cell,x,y,volume,mass,px,py,pz,energy,az,bx,by,bz,density,pressure"
        )?;
        for (i, q) in sim.primitives()?.into_iter().enumerate() {
            row(
                &mut state,
                i,
                sim.position(i)
                    .into_iter()
                    .chain([sim.mesh.cells[i].volume])
                    .chain(sim.conserved[i])
                    .chain([sim.az[i]])
                    .chain(q.magnetic)
                    .chain([q.density, q.pressure]),
            )?;
        }
    } else {
        let mesh = if reference {
            Mesh::lattice(n, n, [1.; 2], jitter)?
        } else {
            Mesh::lattice_on(n, n, [1.; 2], jitter, layout)?
        };
        match problem.as_str() {
            "ct" | "ct-limited" => {
                let config = ct::Config {
                    admissible_limiter: problem == "ct-limited",
                    mean_xy: [1., 0.],
                    mesh_velocity: w,
                    ..Default::default()
                };
                let mut sim = ct::Simulation::new(mesh, config, |x| {
                    (
                        benchmarks::alfven_initial(x, 0., boost).potential[2],
                        benchmarks::alfven_exact(x, 0., 0., boost),
                    )
                })?;
                if reference {
                    sim.advance_to(target)?
                } else {
                    sim.advance_on(target, layout)?
                }
                steps = sim.steps;
                writeln!(
                    state,
                    "cell,volume,mass,px,py,pz,energy,bz_integral,bx,by,bz,density,pressure,div_ct"
                )?;
                let divergence = sim.geometry.divergence(&sim.mesh, &sim.state.flux);
                for (i, q) in sim.recover(&sim.state)?.into_iter().enumerate() {
                    row(
                        &mut state,
                        i,
                        [sim.mesh.cells[i].volume]
                            .into_iter()
                            .chain(sim.state.fluid[i])
                            .chain([sim.state.bz_integral[i]])
                            .chain(q.magnetic)
                            .chain([q.density, q.pressure, divergence[i]]),
                    )?;
                }
                writeln!(faces, "face,left,right,oriented_flux")?;
                for (i, (f, flux)) in sim.mesh.faces.iter().zip(sim.state.flux).enumerate() {
                    writeln!(faces, "{i},{},{},{flux:.17e}", f.left, f.right)?;
                }
            }
            "passive" | "prescribed" => {
                let initial = |x| benchmarks::passive_loop(x, 0., [velocity[0], velocity[1], 0.]).0;
                writeln!(state, "cell,x,y,volume,az,bx,by")?;
                if problem == "passive" {
                    let mut sim = Passive::new(mesh, velocity, w, initial)?;
                    if reference {
                        sim.advance_to(target)?
                    } else {
                        sim.advance_on(target, layout)?
                    }
                    steps = sim.steps();
                    let positions = sim.positions();
                    for (i, b) in sim.magnetic()?.into_iter().enumerate() {
                        row(
                            &mut state,
                            i,
                            positions[i]
                                .into_iter()
                                .chain([sim.mesh().cells[i].volume, sim.potential()[i]])
                                .chain(b),
                        )?;
                    }
                } else {
                    let mut sim = Transport::new(mesh, velocity, w, initial)?;
                    if reference {
                        sim.advance_to(target)?
                    } else {
                        sim.advance_on(target, layout)?
                    }
                    steps = sim.steps();
                    for (i, b) in sim.fields()?.magnetic.into_iter().enumerate() {
                        row(
                            &mut state,
                            i,
                            sim.position(i).into_iter().chain([
                                sim.mesh().cells[i].volume,
                                sim.potential()[i][0],
                                b[0],
                                b[1],
                            ]),
                        )?;
                    }
                }
            }
            _ => return Err("unknown planar comparator".into()),
        }
    }
    layout.agree(&state)?;
    layout.agree(&faces)?;
    let counters = format!("time,steps\n{target:.17e},{steps}\n");
    layout.agree(counters.as_bytes())?;
    if layout.rank() == 0 {
        let dir = Path::new(directory);
        std::fs::create_dir(dir)?;
        save(dir, "cells.csv", &state)?;
        save(dir, "steps.csv", counters.as_bytes())?;
        if !faces.is_empty() {
            save(dir, "faces.csv", &faces)?;
        }
    }
    Ok(())
}
