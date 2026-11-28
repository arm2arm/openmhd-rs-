use mhd_io::{Decoder, Encoder, digest};
use mhd_parallel::{RankTeam, layout::Layout, map_indexed};
use mpi::{Count, datatype::PartitionMut, topology::SimpleCommunicator, traits::*};
use std::{cell::Cell, num::NonZeroUsize, time::Instant};

/// Reference all-gather halo transport. MPI calls stay on the MPI initialization thread.
/// The distributed kernels compute only their owned records. Each rank retains a sorted
/// compact replica for neighbour queries and deterministic floating-point reductions.
pub struct MpiLayout<'a> {
    world: &'a SimpleCommunicator,
    pub team: RankTeam,
    pub bytes_received: Cell<u64>,
    pub work: Cell<u64>,
    pub exchange_seconds: Cell<f64>,
}
impl<'a> MpiLayout<'a> {
    pub fn new(world: &'a SimpleCommunicator, team: RankTeam) -> Self {
        Self {
            world,
            team,
            bytes_received: Cell::new(0),
            work: Cell::new(0),
            exchange_seconds: Cell::new(0.),
        }
    }
    fn agree_bytes(&self, input: &[u8]) -> Result<(), String> {
        let hash = digest(&[input]);
        let mut hashes = vec![0u8; 32 * self.ranks().get()];
        self.world.all_gather_into(&hash[..], &mut hashes[..]);
        if hashes.chunks_exact(32).any(|h| h != hash) {
            return Err("MPI ranks disagree on the input generation or work ownership".into());
        }
        Ok(())
    }
    fn exchange(&self, send: &[u8]) -> Result<Vec<Vec<u8>>, String> {
        let start = Instant::now();
        let n = self.ranks().get();
        let mut sizes = vec![0u64; n];
        self.world
            .all_gather_into(&(send.len() as u64), &mut sizes[..]);
        let mut counts = Vec::with_capacity(n);
        let mut offsets = Vec::with_capacity(n);
        let mut end: Count = 0;
        for v in sizes {
            let count =
                Count::try_from(v).map_err(|_| "MPI rank message exceeds MPI_Count range")?;
            offsets.push(end);
            counts.push(count);
            end = end
                .checked_add(count)
                .ok_or("MPI exchange exceeds all-gatherv count range")?;
        }
        let mut bytes = vec![0u8; end as usize];
        {
            let mut target = PartitionMut::new(&mut bytes[..], &counts[..], &offsets[..]);
            self.world.all_gather_varcount_into(send, &mut target);
        }
        let result = offsets
            .iter()
            .zip(counts)
            .map(|(&a, n)| bytes[a as usize..(a + n) as usize].to_vec())
            .collect();
        self.bytes_received
            .set(self.bytes_received.get() + end as u64 - send.len() as u64);
        self.exchange_seconds
            .set(self.exchange_seconds.get() + start.elapsed().as_secs_f64());
        Ok(result)
    }
}
impl Layout for MpiLayout<'_> {
    fn agree(&self, input: &[u8]) -> Result<(), String> {
        self.agree_bytes(input)
    }
    fn rank(&self) -> usize {
        self.world.rank() as usize
    }
    fn ranks(&self) -> NonZeroUsize {
        NonZeroUsize::new(self.world.size() as usize).unwrap()
    }
    fn packets<F>(&self, owners: &[usize], compute: F) -> Result<Vec<Vec<u8>>, String>
    where
        F: Fn(usize) -> Result<Vec<u8>, String> + Sync + Send,
    {
        // Check the collective plan before a rank can exit early on bad ownership.
        let mut plan = Encoder::new();
        for &owner in owners {
            plan.usize(owner);
        }
        self.agree(&plan.finish())?;
        let size = self.ranks().get();
        let rank = self.rank();
        if owners.iter().any(|&r| r >= size) {
            return Err("MPI owner outside communicator".into());
        }
        let local: Vec<_> = owners
            .iter()
            .enumerate()
            .filter_map(|(i, &r)| (r == rank).then_some(i))
            .collect();
        let rows = self
            .team
            .install(|| map_indexed(local.len(), NonZeroUsize::MIN, |j| compute(local[j])));
        self.work.set(self.work.get() + rows.len() as u64);
        let mut msg = Encoder::new();
        msg.usize(rows.len());
        for (&i, row) in local.iter().zip(rows) {
            msg.usize(i);
            match row {
                Ok(body) => {
                    msg.boolean(true);
                    msg.bytes(&body);
                }
                Err(e) => {
                    msg.boolean(false);
                    msg.string(&e);
                }
            }
        }
        let messages = self.exchange(&msg.finish())?;
        let mut assembled: Vec<Option<Result<Vec<u8>, String>>> =
            (0..owners.len()).map(|_| None).collect();
        for (source, body) in messages.iter().enumerate() {
            let mut d = Decoder::new(body);
            let count = d.count(17)?;
            for _ in 0..count {
                let i = d.usize()?;
                if owners.get(i) != Some(&source) || assembled[i].is_some() {
                    return Err("duplicate or misowned MPI row".into());
                }
                let success = d.boolean()?;
                assembled[i] = Some(if success {
                    Ok(d.bytes()?.to_vec())
                } else {
                    Err(d.string()?)
                });
            }
            d.finish()?;
        }
        assembled
            .into_iter()
            .map(|row| row.ok_or_else(|| String::from("missing MPI row"))?)
            .collect()
    }
}
