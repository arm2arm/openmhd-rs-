//! Shared input and oriented polygon output for serial, thread-team and MPI motion drivers.
use super::*;
use galaxy_types::{CellId, EntityId};
use std::io::Write;
use std::{collections::BTreeMap, error::Error, fmt::Display, fs, str::FromStr};

pub struct MotionCatalog {
    pub domain: Domain3,
    pub generators: Vec<Generator3>,
    pub flow: BTreeMap<CellId, GasMotion3>,
}

fn triple<T: FromStr>(words: &[&str]) -> Result<[T; 3], String>
where
    T::Err: Display,
{
    let parse = |word: &str| {
        word.parse()
            .map_err(|err| format!("invalid number {word}: {err}"))
    };
    Ok([parse(words[0])?, parse(words[1])?, parse(words[2])?])
}

pub fn read_catalog(file: &str) -> Result<MotionCatalog, Box<dyn Error>> {
    parse_catalog(&fs::read_to_string(file)?)
}
pub fn parse_catalog(input: &str) -> Result<MotionCatalog, Box<dyn Error>> {
    let mut lines = input.lines().filter_map(|line| {
        let text = line.split('#').next()?.trim();
        (!text.is_empty()).then_some(text)
    });
    let header: Vec<_> = lines
        .next()
        .ok_or("missing domain")?
        .split_whitespace()
        .collect();
    if header.len() != 8 || header[0] != "domain" {
        return Err("expected domain MODE x0 y0 z0 Lx Ly Lz".into());
    }
    let domain = Domain3 {
        boundary: match header[1] {
            "periodic" => Boundary3::Periodic,
            "bounded" => Boundary3::Bounded,
            _ => return Err("invalid boundary".into()),
        },
        anchor: triple(&header[2..5])?,
        width: triple(&header[5..8])?,
    };
    let mut generators = Vec::new();
    let mut flow = BTreeMap::new();
    for line in lines {
        let words: Vec<_> = line.split_whitespace().collect();
        if words.len() != 12 || words[0] != "cell" {
            return Err("expected cell ID x y z ix iy iz vx vy vz sound_speed".into());
        }
        let id = CellId::new(words[1].parse::<EntityId>()?);
        let generator = Generator3 {
            id,
            position: triple(&words[2..5])?,
            winding: Image3(triple(&words[5..8])?),
        };
        let gas = GasMotion3 {
            velocity: triple(&words[8..11])?,
            sound_speed: words[11].parse()?,
        };
        if flow.insert(id, gas).is_some() {
            return Err(format!("duplicate cell ID {}", id.entity()).into());
        }
        generators.push(generator);
    }
    Ok(MotionCatalog {
        domain,
        generators,
        flow,
    })
}

pub const HEADER: &str = "step,time,owner,x,y,z,ix,iy,iz,volume,face,sign,neighbour,jx,jy,jz,wall_patch,area,nx,ny,nz,vertex,dx,dy,dz";
pub fn write_epoch(
    out: &mut impl Write,
    step: usize,
    time: f64,
    mesh: &ValidatedGeometry3,
) -> Result<(), Box<dyn Error>> {
    for (i, cell) in mesh.cells().iter().enumerate() {
        let id = cell.generator.id.entity();
        let [x, y, z] = cell.generator.position;
        let [ix, iy, iz] = cell.generator.winding.0;
        for face in mesh.oriented_faces(mesh.cell_ref(i)?)? {
            let (peer, image) = face
                .incidence
                .neighbour
                .map(|(id, image)| (id.entity().to_string(), image))
                .unwrap_or_else(|| (String::new(), Image3::ZERO));
            let patch = match face.shared.key {
                FaceKey3::Boundary { patch, .. } => patch.0.to_string(),
                FaceKey3::Interior { .. } => String::new(),
            };
            let [jx, jy, jz] = image.0;
            let [nx, ny, nz] = face.outward_normal();
            let area = face.shared.area;
            let local = face.handle.index();
            let sign = face.incidence.sign;
            let volume = cell.volume;
            for (vertex, [dx, dy, dz]) in face.vertices().enumerate() {
                writeln!(
                    out,
                    "{step},{time:.17e},{id},{x:.17e},{y:.17e},{z:.17e},{ix},{iy},{iz},{volume:.17e},{local},{sign},{peer},{jx},{jy},{jz},{patch},{area:.17e},{nx:.17e},{ny:.17e},{nz:.17e},{vertex},{dx:.17e},{dy:.17e},{dz:.17e}"
                )?;
            }
        }
    }
    Ok(())
}
