//! Deterministic ownership of persistent entities in an orthorhombic box.
pub use galaxy_types::EntityId;
use std::{collections::BTreeMap, num::NonZeroUsize};

#[derive(Clone, Copy, Debug)]
pub struct Site {
    pub id: EntityId,
    pub position: [f64; 3],
    /// Positive measured work from the previous geometry epoch, or 1 at startup.
    pub weight: u64,
}

#[derive(Clone, Debug)]
pub struct Partition {
    ranks: NonZeroUsize,
    owners: BTreeMap<EntityId, usize>,
}

fn morton(position: [f64; 3], origin: [f64; 3], width: [f64; 3]) -> Result<u64, String> {
    let mut key = 0u64;
    for axis in 0..3 {
        let u = (position[axis] - origin[axis]) / width[axis];
        // Inputs are wrapped by the geometry/trajectory owner. Include the
        // upper endpoint for isolated gravity boxes and final-bit rounding.
        if !position[axis].is_finite() || !(0.0..=1.0).contains(&u) {
            return Err("partition site outside its finite box".into());
        }
        let q = ((u * (1u64 << 21) as f64) as u64).min((1 << 21) - 1);
        for bit in 0..21 {
            key |= ((q >> bit) & 1) << (3 * bit + axis);
        }
    }
    Ok(key)
}

impl Partition {
    pub fn new(
        sites: &[Site],
        origin: [f64; 3],
        width: [f64; 3],
        ranks: NonZeroUsize,
    ) -> Result<Self, String> {
        if origin.iter().any(|v| !v.is_finite())
            || width.iter().any(|v| !v.is_finite() || *v <= 0.0)
        {
            return Err("invalid partition box".into());
        }
        let mut order = Vec::with_capacity(sites.len());
        let mut total = 0u128;
        for s in sites {
            if s.weight == 0 {
                return Err("zero partition weight".into());
            }
            total += u128::from(s.weight);
            order.push((morton(s.position, origin, width)?, s.id, s.weight));
        }
        order.sort_unstable();
        let mut owners = BTreeMap::new();
        let mut before = 0u128;
        for (_, id, weight) in order {
            // Midpoint of the work interval in Morton order. Use checked integers
            // so the ownership map is independent of reduction and input order.
            let half = before
                .checked_mul(2)
                .and_then(|x| x.checked_add(u128::from(weight)))
                .ok_or("partition weight overflow")?;
            let rank = half
                .checked_mul(ranks.get() as u128)
                .ok_or("partition weight overflow")?
                / total.checked_mul(2).ok_or("partition weight overflow")?;
            if owners.insert(id, rank as usize).is_some() {
                return Err(format!("duplicate partition ID {id}"));
            }
            before += u128::from(weight);
        }
        Ok(Self { ranks, owners })
    }
    pub fn ranks(&self) -> NonZeroUsize {
        self.ranks
    }
    pub fn owner(&self, id: EntityId) -> Result<usize, String> {
        self.owners
            .get(&id)
            .copied()
            .ok_or_else(|| format!("unknown partition ID {id}"))
    }
    /// The image label distinguishes parallel/self faces in the geometry.
    /// Each canonical face index has precisely one writer, even for self images.
    pub fn face_owner(&self, left: EntityId, right: Option<EntityId>) -> Result<usize, String> {
        if let Some(right) = right {
            self.owner(right)?;
            self.owner(left)?;
            self.owner(left.min(right))
        } else {
            self.owner(left)
        }
    }
}
