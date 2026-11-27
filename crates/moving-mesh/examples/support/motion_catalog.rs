use galaxy_types::{CellId, EntityId};
use moving_mesh::three_d::*;
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
    let input = fs::read_to_string(file)?;
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
