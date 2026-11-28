use super::*;
use mhd_parallel::halo::{HaloPlan, HaloRows};
use mpi::{collective::SystemOperation, datatype::Partition};

#[derive(Default)]
pub(super) struct Traffic {
    calls: u64,
    received: u64,
    full: u64,
    seconds: f64,
}

/// MPI counts and displacements are in doubles. Check the entire displacement span.
struct Counts {
    sizes: Vec<Count>,
    offsets: Vec<Count>,
    total: usize,
}
impl Counts {
    fn new<const N: usize>(rows: &[Vec<usize>]) -> Option<Self> {
        let mut end: Count = 0;
        let mut sizes = Vec::with_capacity(rows.len());
        let mut offsets = Vec::with_capacity(rows.len());
        for peer in rows {
            let size = Count::try_from(peer.len().checked_mul(N)?).ok()?;
            offsets.push(end);
            sizes.push(size);
            end = end.checked_add(size)?;
        }
        Some(Self {
            sizes,
            offsets,
            total: end as usize,
        })
    }
}
impl MpiLayout<'_> {
    pub fn report_halos(&self) {
        for (stage, t) in self.traffic.borrow().iter() {
            eprintln!(
                "openmhd-halo rank={} stage={stage} mode={} calls={} payload_bytes={} full_bytes={} payload_seconds={:.9}",
                self.rank(),
                if self.sparse { "sparse" } else { "full" },
                t.calls,
                t.received,
                t.full,
                t.seconds
            );
        }
    }

    pub(super) fn fixed_halo<const N: usize, F>(
        &self,
        stage: &str,
        plan: &HaloPlan,
        compute: F,
    ) -> Result<HaloRows<N>, String>
    where
        F: Fn(usize) -> Result<[f64; N], String> + Sync + Send,
    {
        let rank = self.rank();
        let ranks = self.ranks().get();
        let mut identity = Encoder::new();
        identity.string(stage);
        identity.boolean(self.sparse);
        identity.usize(N);
        identity.usize(plan.owners().len());
        for (i, &owner) in plan.owners().iter().enumerate() {
            identity.usize(owner);
            identity.usize(plan.receivers(i).len());
            for &peer in plan.receivers(i) {
                identity.usize(peer);
            }
        }
        self.agree_bytes(&identity.finish())?;
        plan.validate(ranks)?;
        if N == 0 {
            return Err("halo row width must be positive".into());
        }
        let local: Vec<_> = plan
            .owners()
            .iter()
            .enumerate()
            .filter_map(|(i, &o)| (o == rank).then_some(i))
            .collect();
        let values = self
            .team
            .install(|| map_indexed(local.len(), NonZeroUsize::MIN, |j| compute(local[j])));
        self.work.set(self.work.get() + local.len() as u64);
        // Every rank observes the first failing global ordinal before any payload collective.
        let error = local
            .iter()
            .copied()
            .zip(&values)
            .find_map(|(i, v)| v.as_ref().err().map(|e| (i, e)));
        let mut first = u64::MAX;
        self.world.all_reduce_into(
            &error.map_or(u64::MAX, |(i, _)| i as u64),
            &mut first,
            SystemOperation::min(),
        );
        if first != u64::MAX {
            let messages = self.exchange(error.map_or(&[], |(_, e)| e.as_bytes()))?;
            return Err(format!(
                "{stage} row {first}: {}",
                String::from_utf8_lossy(&messages[plan.owners()[first as usize]])
            ));
        }
        let owned: HaloRows<N> = local
            .iter()
            .copied()
            .zip(values.into_iter().collect::<Result<Vec<_>, _>>()?)
            .collect();
        let mut send = vec![Vec::new(); ranks];
        let mut recv = vec![Vec::new(); ranks];
        for (i, &owner) in plan.owners().iter().enumerate() {
            if !self.sparse {
                recv[owner].push(i);
            } else if owner == rank {
                for &peer in plan.receivers(i) {
                    if peer != rank {
                        send[peer].push(i);
                    }
                }
            } else if plan.wanted(i, rank) {
                recv[owner].push(i);
            }
        }
        let outgoing = Counts::new::<N>(&send);
        let incoming = Counts::new::<N>(&recv);
        let valid = i32::from(outgoing.is_some() && incoming.is_some());
        let mut all_valid = 0;
        self.world
            .all_reduce_into(&valid, &mut all_valid, SystemOperation::min());
        if all_valid == 0 {
            return Err("halo payload exceeds MPI count range".into());
        }
        let incoming = incoming.expect("collectively checked");
        // Keep separate valid base addresses even when every peer count is zero.
        let mut buffer = vec![0.; incoming.total.max(1)];
        let mut target =
            PartitionMut::new(&mut buffer[..], &incoming.sizes[..], &incoming.offsets[..]);
        let elapsed = if self.sparse {
            let outgoing = outgoing.expect("collectively checked");
            let mut packed: Vec<_> = send.iter().flatten().flat_map(|i| owned[i]).collect();
            if packed.is_empty() {
                packed.push(0.);
            }
            let source = Partition::new(&packed[..], &outgoing.sizes[..], &outgoing.offsets[..]);
            let start = Instant::now();
            self.world.all_to_all_varcount_into(&source, &mut target);
            start.elapsed().as_secs_f64()
        } else {
            let packed: Vec<_> = owned.values().flatten().copied().collect();
            let start = Instant::now();
            self.world
                .all_gather_varcount_into(&packed[..], &mut target);
            start.elapsed().as_secs_f64()
        };
        let full = (plan.owners().len() - local.len()) as u64 * (N as u64) * 8;
        let received = if self.sparse {
            incoming.total as u64 * 8
        } else {
            full
        };
        self.bytes_received
            .set(self.bytes_received.get() + received);
        self.exchange_seconds
            .set(self.exchange_seconds.get() + elapsed);
        let mut traffic = self.traffic.borrow_mut();
        let t = traffic.entry(stage.to_owned()).or_default();
        t.calls += 1;
        t.full += full;
        t.received += received;
        t.seconds += elapsed;
        let mut result: HaloRows<N> = owned
            .into_iter()
            .filter(|(i, _)| plan.wanted(*i, rank))
            .collect();
        for (&i, words) in recv
            .iter()
            .flatten()
            .zip(buffer[..incoming.total].chunks_exact(N))
        {
            if plan.owners()[i] != rank && plan.wanted(i, rank) {
                result.insert(i, words.try_into().expect("fixed width"));
            }
        }
        Ok(result)
    }
}
