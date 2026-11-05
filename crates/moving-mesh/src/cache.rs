//! Exact initial-mesh serialization for repeated benchmark configurations.
//! All f64 values are stored as integer IEEE-754 bit patterns, not rounded text.
use super::{Cell, Face, Mesh, Vec2};
use std::{
    fmt::Write as _,
    str::{FromStr, SplitWhitespace},
};
struct Reader<'a> {
    tokens: SplitWhitespace<'a>,
    remaining: usize,
}
impl Reader<'_> {
    fn take<T: FromStr>(&mut self) -> Result<T, String> {
        self.remaining = self
            .remaining
            .checked_sub(1)
            .ok_or("truncated mesh cache")?;
        self.tokens
            .next()
            .ok_or("truncated mesh cache")?
            .parse()
            .map_err(|_| "invalid mesh cache token".into())
    }
    fn float(&mut self) -> Result<f64, String> {
        Ok(f64::from_bits(self.take()?))
    }
    fn count(&mut self) -> Result<usize, String> {
        let n = self.take()?;
        if n > self.remaining {
            Err("invalid mesh cache count".into())
        } else {
            Ok(n)
        }
    }
}
impl Mesh {
    pub fn encode(&self) -> Result<String, String> {
        self.validate()?;
        let mut out = String::from("openmhd-mesh-bits-v1\n");
        writeln!(
            &mut out,
            "{} {} {} {}",
            self.lengths[0].to_bits(),
            self.lengths[1].to_bits(),
            self.cells.len(),
            self.faces.len()
        )
        .unwrap();
        for p in &self.generators {
            writeln!(&mut out, "{} {}", p[0].to_bits(), p[1].to_bits()).unwrap();
        }
        for c in &self.cells {
            writeln!(
                &mut out,
                "{} {} {} {}",
                c.volume.to_bits(),
                c.centroid[0].to_bits(),
                c.centroid[1].to_bits(),
                c.faces.len()
            )
            .unwrap();
            for (f, s) in &c.faces {
                writeln!(&mut out, "{f} {}", s.to_bits()).unwrap();
            }
        }
        for f in &self.faces {
            writeln!(
                &mut out,
                "{} {} {} {} {} {} {} {} {}",
                f.left,
                f.right,
                f.image[0],
                f.image[1],
                f.centroid[0].to_bits(),
                f.centroid[1].to_bits(),
                f.normal[0].to_bits(),
                f.normal[1].to_bits(),
                f.area.to_bits()
            )
            .unwrap();
        }
        Ok(out)
    }
    pub fn decode_lattice(
        input: &str,
        nx: usize,
        ny: usize,
        lengths: Vec2,
        jitter: f64,
    ) -> Result<Self, String> {
        let mut r = Reader {
            tokens: input.split_whitespace(),
            remaining: input.split_whitespace().count(),
        };
        if r.take::<String>()? != "openmhd-mesh-bits-v1" {
            return Err("unknown mesh cache format".into());
        }
        let stored = [r.float()?, r.float()?];
        let nc = r.count()?;
        let nf = r.count()?;
        if stored != lengths || nx.checked_mul(ny) != Some(nc) {
            return Err("mesh cache dimensions differ from request".into());
        }
        let generators = (0..nc)
            .map(|_| Ok([r.float()?, r.float()?]))
            .collect::<Result<Vec<_>, String>>()?;
        if generators != Self::lattice_points(nx, ny, lengths, jitter)? {
            return Err("mesh cache generators differ from requested lattice".into());
        }
        let mut cells = Vec::with_capacity(nc);
        for _ in 0..nc {
            let volume = r.float()?;
            let centroid = [r.float()?, r.float()?];
            let n = r.count()?;
            let faces = (0..n)
                .map(|_| Ok((r.take()?, r.float()?)))
                .collect::<Result<Vec<_>, String>>()?;
            cells.push(Cell {
                volume,
                centroid,
                faces,
            });
        }
        let mut faces = Vec::with_capacity(nf);
        for _ in 0..nf {
            faces.push(Face {
                left: r.take()?,
                right: r.take()?,
                image: [r.take()?, r.take()?],
                centroid: [r.float()?, r.float()?],
                normal: [r.float()?, r.float()?],
                area: r.float()?,
            });
        }
        if r.remaining != 0 {
            return Err("trailing mesh cache data".into());
        }
        let mesh = Self {
            lengths,
            generators,
            cells,
            faces,
        };
        mesh.validate()?;
        Ok(mesh)
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exact_roundtrip_and_invalid_requests() {
        for j in [0., 0.15] {
            for lengths in [[1., 1.], [1.3, 0.7]] {
                let m = Mesh::lattice(9, 7, lengths, j).unwrap();
                let encoded = m.encode().unwrap();
                let copy = Mesh::decode_lattice(&encoded, 9, 7, lengths, j).unwrap();
                assert_eq!(encoded, copy.encode().unwrap());
                assert_eq!(format!("{m:?}"), format!("{copy:?}"));
                assert!(Mesh::decode_lattice(&encoded, 8, 7, lengths, j).is_err());
                assert!(Mesh::decode_lattice(&encoded, 9, 7, lengths, 0.12).is_err());
                assert!(Mesh::decode_lattice(&(encoded.clone() + " 0"), 9, 7, lengths, j).is_err());
                assert!(
                    Mesh::decode_lattice(&encoded[..encoded.len() / 2], 9, 7, lengths, j).is_err()
                );
            }
        }
    }
}
