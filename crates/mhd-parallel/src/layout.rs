//! Rank-owned independent kernels, plus a serial/explicit-Rayon implementation.
//! MPI implementations perform communication on the calling thread, outside the compute team.
use crate::halo::{HaloPlan, HaloRows};
use std::num::NonZeroUsize;

/// The owner vector is in canonical work order. The return vector has the same ordering,
/// including zero-length inputs and ranks which own no work. Errors must reach all ranks.
pub trait Layout {
    fn agree(&self, _generation: &[u8]) -> Result<(), String> {
        Ok(())
    }
    fn rank(&self) -> usize;
    fn ranks(&self) -> NonZeroUsize;
    fn packets<F>(&self, owners: &[usize], compute: F) -> Result<Vec<Vec<u8>>, String>
    where
        F: Fn(usize) -> Result<Vec<u8>, String> + Send + Sync;

    /// Compute on producers and return only rows subscribed to by this rank.
    fn halo_rows<const N: usize, F>(
        &self,
        _stage: &str,
        plan: &HaloPlan,
        compute: F,
    ) -> Result<HaloRows<N>, String>
    where
        F: Fn(usize) -> Result<[f64; N], String> + Send + Sync,
    {
        plan.validate(self.ranks().get())?;
        Ok(self
            .rows(plan.owners(), compute)?
            .into_iter()
            .enumerate()
            .filter(|(i, _)| plan.wanted(*i, self.rank()))
            .collect())
    }
    fn rows<const N: usize, F>(&self, owners: &[usize], compute: F) -> Result<Vec<[f64; N]>, String>
    where
        F: Fn(usize) -> Result<[f64; N], String> + Send + Sync,
    {
        self.packets(owners, |i| {
            let row = compute(i)?;
            let mut bytes = Vec::with_capacity(8 * N);
            for value in row {
                bytes.extend_from_slice(&value.to_bits().to_le_bytes());
            }
            Ok(bytes)
        })?
        .into_iter()
        .map(|bytes| {
            if bytes.len() != N * 8 {
                return Err("incorrect distributed row width".into());
            }
            Ok(std::array::from_fn(|k| {
                f64::from_le_bytes(bytes[8 * k..8 * k + 8].try_into().unwrap())
            }))
        })
        .collect()
    }
}

/// Single-rank reference with the same numerical compute closures as MPI.
pub struct LocalLayout(pub NonZeroUsize);
impl Layout for LocalLayout {
    fn rank(&self) -> usize {
        0
    }
    fn ranks(&self) -> NonZeroUsize {
        NonZeroUsize::MIN
    }
    fn packets<F>(&self, owners: &[usize], compute: F) -> Result<Vec<Vec<u8>>, String>
    where
        F: Fn(usize) -> Result<Vec<u8>, String> + Send + Sync,
    {
        if owners.iter().any(|&rank| rank != 0) {
            return Err("owner outside local layout".into());
        }
        super::with_team(self.0, || {
            super::map_indexed(owners.len(), NonZeroUsize::MIN, compute)
        })?
        .into_iter()
        .collect()
    }
}

/// Borrowed object-safe view for existing solver entry points. The concrete MPI
/// communicator stays outside the scientific crates and outside worker threads.
pub trait Exchange {
    fn rank_count(&self) -> NonZeroUsize;
    fn agree_bytes(&self, bytes: &[u8]) -> Result<(), String>;
    fn exchange(
        &self,
        owners: &[usize],
        compute: &(dyn Fn(usize) -> Result<Vec<u8>, String> + Send + Sync),
    ) -> Result<Vec<Vec<u8>>, String>;
}
impl<L: Layout> Exchange for L {
    fn rank_count(&self) -> NonZeroUsize {
        self.ranks()
    }
    fn agree_bytes(&self, bytes: &[u8]) -> Result<(), String> {
        self.agree(bytes)
    }
    fn exchange(
        &self,
        owners: &[usize],
        compute: &(dyn Fn(usize) -> Result<Vec<u8>, String> + Send + Sync),
    ) -> Result<Vec<Vec<u8>>, String> {
        self.packets(owners, compute)
    }
}
