//! Single-threaded comparison on identical generator words. Coordinates in a unit box.
use galaxy_types::{CellId, EntityId};
use glam::DVec3;
use meshless_voronoi::{Dimensionality, VoronoiIntegrator, integrals::VolumeCentroidIntegral};
use moving_mesh::three_d::*;
use std::{collections::BTreeMap, fmt::Write, time::Instant};

#[derive(Clone)]
struct Fixture {
    sites: Vec<Generator3>,
    boundary: Boundary3,
}

fn fixture(name: &str) -> Result<Fixture, String> {
    let n = match name {
        "one" => 1,
        "cube2" | "seam-before" | "seam-after" => 2,
        "jitter" | "jitter-next" | "bounded" | "close-pair" => 3,
        "cube4" | "registered-shear4" => 4,
        "cube8" => 8,
        _ => return Err(format!("unknown fixture {name}")),
    };
    let mut sites = Vec::new();
    for i in 0..n * n * n {
        let ijk = [i % n, i / n % n, i / (n * n)];
        let mut position = [0.0; 3];
        let mut winding = [0_i64; 3];
        for k in 0..3 {
            let mut x = (ijk[k] as f64 + 0.5) / n as f64;
            if matches!(name, "jitter" | "jitter-next" | "bounded" | "close-pair") {
                // Fixed integer mixing preserves the same per-ID cloud in both backends.
                let mut z = ((i * 3 + k + 1) as u64).wrapping_mul(0x9e3779b97f4a7c15);
                z = (z ^ (z >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
                z = (z ^ (z >> 27)).wrapping_mul(0x94d049bb133111eb);
                let j = ((z ^ (z >> 31)) >> 52) as f64 - 2048.0;
                x += j / (16384.0 * n as f64);
                if name == "jitter-next" {
                    x += ((i * 13 + k * 29) % 37) as f64 / 4096.0;
                }
            }
            if k == 0 && matches!(name, "seam-before" | "seam-after") {
                x += if name == "seam-before" { 0.125 } else { 0.375 };
                winding[k] = x.floor() as i64;
                x -= winding[k] as f64;
            }
            position[k] = x;
        }
        sites.push(Generator3 {
            id: CellId::new(EntityId::new(8, i as u64)),
            position,
            winding: Image3(winding),
        });
    }
    if name == "close-pair" {
        sites[1].position = sites[0].position;
        sites[1].position[0] += 2.0_f64.powi(-32);
    }
    Ok(Fixture {
        sites,
        boundary: if name == "bounded" {
            Boundary3::Bounded
        } else {
            Boundary3::Periodic
        },
    })
}

fn vec_words(out: &mut String, v: DVec3) {
    for x in v.to_array() {
        write!(out, " {x:.17e}").unwrap();
    }
}

fn cell(out: &mut String, i: usize, volume: f64, centroid: DVec3) {
    write!(out, "C {i} {volume:.17e}").unwrap();
    vec_words(out, centroid);
    out.push('\n');
}

enum Opposite {
    Site(usize, [i64; 3]),
    Wall(u8),
}

fn face(out: &mut String, owner: usize, opposite: Opposite, normal: DVec3, vertices: &[DVec3]) {
    write!(out, "F {owner}").unwrap();
    match opposite {
        Opposite::Site(j, m) => write!(out, " I {j} {} {} {}", m[0], m[1], m[2]).unwrap(),
        Opposite::Wall(p) => write!(out, " W {p}").unwrap(),
    }
    vec_words(out, normal);
    for &v in vertices {
        vec_words(out, v);
    }
    out.push('\n');
}

fn project(f: &Fixture, accelerated: bool, out: &mut String) -> Result<f64, String> {
    let domain = Domain3 {
        anchor: [0.0; 3],
        width: [1.0; 3],
        boundary: f.boundary,
    };
    let index: BTreeMap<_, _> = f.sites.iter().enumerate().map(|(i, g)| (g.id, i)).collect();
    let started = Instant::now();
    let build = if accelerated {
        HalfSpaceOracle3::build_motion_epoch
    } else {
        HalfSpaceOracle3::build
    };
    let g = build(domain, &f.sites).map_err(|e| format!("{e:?}"))?;
    let seconds = started.elapsed().as_secs_f64();
    for (ci, c) in g.cells().iter().enumerate() {
        let i = index[&c.generator.id];
        cell(out, i, c.volume, DVec3::from_array(c.centroid_offset));
        for a in g
            .oriented_faces(g.cell_ref(ci).map_err(|e| format!("{e:?}"))?)
            .map_err(|e| format!("{e:?}"))?
        {
            let opposite = match (a.incidence.neighbour, a.shared.key) {
                (Some((id, m)), _) => Opposite::Site(index[&id], m.0),
                (None, FaceKey3::Boundary { patch, .. }) => Opposite::Wall(patch.0),
                _ => return Err("interior face missing owner".into()),
            };
            let vertices: Vec<_> = a.vertices().map(DVec3::from_array).collect();
            face(
                out,
                i,
                opposite,
                DVec3::from_array(a.outward_normal()),
                &vertices,
            );
        }
    }
    Ok(seconds)
}

fn external(f: &Fixture, out: &mut String) -> Result<f64, String> {
    let xyz: Vec<_> = f
        .sites
        .iter()
        .map(|s| DVec3::from_array(s.position))
        .collect();
    let started = Instant::now();
    let mesh = VoronoiIntegrator::build(
        &xyz,
        None,
        DVec3::ZERO,
        DVec3::ONE,
        Dimensionality::ThreeD,
        f.boundary == Boundary3::Periodic,
    )
    .with_faces();
    let integrals = mesh.compute_cell_integrals::<VolumeCentroidIntegral>();
    let seconds = started.elapsed().as_secs_f64();
    if integrals.len() != xyz.len() {
        return Err("missing volume integrals".into());
    }
    for (i, m) in integrals.iter().enumerate() {
        cell(out, i, m.volume, m.centroid - xyz[i]);
        let c = mesh.get_cell_at(i).ok_or("missing convex cell")?;
        for k in 0..c.face_count() {
            let normal = -c.clipping_plane(k).n.normalize();
            let opposite = if let Some(j) = c.neighbour(k) {
                let shift = c.shift(k).unwrap_or(DVec3::ZERO).to_array();
                if shift
                    .iter()
                    .any(|s| !s.is_finite() || s.fract() != 0.0 || s.abs() > 1.0)
                {
                    return Err("invalid periodic image in unit box".into());
                }
                Opposite::Site(
                    j,
                    std::array::from_fn(|d| {
                        shift[d] as i64 + f.sites[i].winding.0[d] - f.sites[j].winding.0[d]
                    }),
                )
            } else {
                let axis = normal
                    .to_array()
                    .iter()
                    .position(|a| a.abs() == 1.0)
                    .ok_or("nonaxial wall")?;
                Opposite::Wall((2 * axis + usize::from(normal[axis] > 0.0)) as u8)
            };
            let vs: Vec<_> = c
                .face_vertices(k)
                .iter()
                .map(|&j| c.vertices[j].loc - xyz[i])
                .collect();
            face(out, i, opposite, normal, &vs);
        }
    }
    Ok(seconds)
}

fn run() -> Result<(), String> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 3 {
        return Err("usage: m2-backend-benchmark BACKEND FIXTURE".into());
    }
    let f = fixture(&args[2])?;
    let mut rows = String::new();
    for (i, s) in f.sites.iter().enumerate() {
        writeln!(
            rows,
            "P {i} {:016x} {:016x} {:016x} {} {} {}",
            s.position[0].to_bits(),
            s.position[1].to_bits(),
            s.position[2].to_bits(),
            s.winding.0[0],
            s.winding.0[1],
            s.winding.0[2]
        )
        .unwrap();
    }
    let all = Instant::now();
    let seconds = match args[1].as_str() {
        "oracle" => project(&f, false, &mut rows)?,
        "motion" => project(&f, true, &mut rows)?,
        "meshless" => external(&f, &mut rows)?,
        "rates" if args[2] == "registered-shear4" => {
            let g = HalfSpaceOracle3::build_supported_periodic(
                Domain3 {
                    anchor: [0.0; 3],
                    width: [1.0; 3],
                    boundary: Boundary3::Periodic,
                },
                &f.sites,
            )
            .map_err(|e| format!("{e:?}"))?;
            let w = f
                .sites
                .iter()
                .map(|s| {
                    (
                        s.id,
                        std::array::from_fn(|k| {
                            0.05 * (std::f64::consts::TAU * s.position[(k + 1) % 3]).sin()
                        }),
                    )
                })
                .collect();
            let count = (0..g.geometry().faces().len())
                .map(|i| {
                    g.vertex_supports(g.geometry().face_ref(i).unwrap())
                        .unwrap()
                        .iter()
                        .filter(|s| s.len() != 3)
                        .count()
                })
                .sum::<usize>();
            eprintln!(
                "registered start: {} cells; {count} face-vertex incidences with other than three supporting planes",
                f.sites.len()
            );
            PrescribedPolygonRates3::build(&g, &w)
                .map_err(|e| format!("registered time-zero polygon rates: {e:?}"))?;
            all.elapsed().as_secs_f64()
        }
        _ => return Err("unknown backend or rates fixture".into()),
    };
    println!(
        "T {} {} {:.9} {:.9}",
        args[1],
        args[2],
        seconds,
        all.elapsed().as_secs_f64()
    );
    print!("{rows}");
    Ok(())
}
fn main() -> std::process::ExitCode {
    match run() {
        Ok(()) => std::process::ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("{e}");
            std::process::ExitCode::FAILURE
        }
    }
}
