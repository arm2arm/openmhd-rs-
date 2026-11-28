//! Explicit local thread pools. Outside `with_threads`, all maps remain serial.
//! Only independent outputs are parallelized; no floating-point reduction changes.
pub mod layout;
pub mod partition;

use rayon::prelude::*;

pub fn with_threads<T: Send>(threads: usize, work: impl FnOnce() -> T + Send) -> Result<T, String> {
    if !(1..=24).contains(&threads) {
        return Err("threads must be between 1 and 24".into());
    }
    if threads == 1 && rayon::current_thread_index().is_none() {
        return Ok(work());
    }
    with_team(std::num::NonZeroUsize::new(threads).unwrap(), work)
}

/// Indexed collection retains input order, including deterministic first errors.
pub fn map<T: Send>(len: usize, work: impl Fn(usize) -> T + Sync + Send) -> Vec<T> {
    map_indexed(len, std::num::NonZeroUsize::new(32).unwrap(), work)
}

pub fn try_map<T: Send>(
    len: usize,
    work: impl Fn(usize) -> Result<T, String> + Sync + Send,
) -> Result<Vec<T>, String> {
    // Collect Results by index before resolving them: Rayon short-circuiting
    // alone does not promise the same first error as the serial implementation.
    map(len, work).into_iter().collect()
}

/// Active team size for scientific work. A call outside a Rayon team is serial.
pub fn team_size() -> usize {
    if rayon::current_thread_index().is_some() {
        rayon::current_num_threads()
    } else {
        1
    }
}

/// Ordered work with a caller-selected granularity. Geometry owners are much
/// more expensive than individual arithmetic operations and can use grain 1.
pub fn map_indexed<T: Send>(
    len: usize,
    min_grain: std::num::NonZeroUsize,
    work: impl Fn(usize) -> T + Sync + Send,
) -> Vec<T> {
    if team_size() > 1 {
        (0..len)
            .into_par_iter()
            .with_min_len(min_grain.get())
            .map(work)
            .collect()
    } else {
        (0..len).map(work).collect()
    }
}

/// Compute independent entries concurrently; commit in ascending ordinal
/// order with bounded temporary storage. The one-thread path streams directly.
pub fn visit_ordered<T: Send, E>(
    len: usize,
    batch: std::num::NonZeroUsize,
    min_grain: std::num::NonZeroUsize,
    compute: impl Fn(usize) -> T + Sync + Send,
    mut commit: impl FnMut(usize, T) -> Result<(), E>,
) -> Result<(), E> {
    if team_size() == 1 {
        for i in 0..len {
            commit(i, compute(i))?;
        }
    } else {
        for start in (0..len).step_by(batch.get()) {
            let n = (len - start).min(batch.get());
            let completed = map_indexed(n, min_grain, |j| compute(start + j));
            for (j, item) in completed.into_iter().enumerate() {
                commit(start + j, item)?;
            }
        }
    }
    Ok(())
}

/// Execution entry point for resource-declared jobs. The legacy CLI keeps its
/// existing 1–24 validation. This entry point accepts an explicit nonzero team.
pub fn with_team<T: Send>(
    threads: std::num::NonZeroUsize,
    work: impl FnOnce() -> T + Send,
) -> Result<T, String> {
    let active = rayon::current_thread_index().is_some();
    if (active && rayon::current_num_threads() == threads.get()) || (!active && threads.get() == 1)
    {
        return Ok(work());
    }
    if active && threads.get() > 1 {
        return Err(
            "cannot start a second multithreaded team inside an active Rayon worker".into(),
        );
    }
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads.get())
        .build()
        .map_err(|e| format!("thread pool: {e}"))?;
    Ok(pool.install(work))
}

/// A team owned by the MPI initialization thread. Reuse its workers across Krylov
/// iterations and Runge–Kutta stages. MPI calls remain on the calling thread.
pub struct RankTeam(Option<rayon::ThreadPool>);
impl RankTeam {
    pub fn new(threads: std::num::NonZeroUsize) -> Result<Self, String> {
        if rayon::current_thread_index().is_some() {
            return Err("rank teams must be created on the MPI initialization thread".into());
        }
        if threads.get() == 1 {
            return Ok(Self(None));
        }
        rayon::ThreadPoolBuilder::new()
            .num_threads(threads.get())
            .build()
            .map(|pool| Self(Some(pool)))
            .map_err(|e| e.to_string())
    }
    pub fn install<T: Send>(&self, work: impl FnOnce() -> T + Send) -> T {
        match &self.0 {
            Some(pool) => pool.install(work),
            None => work(),
        }
    }
}

/// Runs a positional scientific driver with an optional leading `--threads N`.
/// Existing commands without the option keep their serial execution.
pub fn run_cli<T: Send, E: std::fmt::Display>(
    args: &[String],
    run: impl FnOnce(&[String]) -> Result<T, E> + Send,
) -> Result<T, String> {
    let (threads, rest) = if args.first().is_some_and(|s| s == "--threads") {
        let n = args
            .get(1)
            .and_then(|s| s.parse::<std::num::NonZeroUsize>().ok())
            .ok_or("--threads requires a positive integer")?;
        (n, &args[2..])
    } else {
        (std::num::NonZeroUsize::MIN, args)
    };
    with_team(threads, || run(rest).map_err(|error| error.to_string()))?
}
