//! Explicit local thread pools. Outside `with_threads`, all maps remain serial.
//! Only independent outputs are parallelized; no floating-point reduction changes.
use rayon::prelude::*;

pub fn with_threads<T: Send>(threads: usize, work: impl FnOnce() -> T + Send) -> Result<T, String> {
    if !(1..=24).contains(&threads) {
        return Err("threads must be between 1 and 24".into());
    }
    if threads == 1 && rayon::current_thread_index().is_none() {
        return Ok(work());
    }
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()
        .map_err(|e| format!("thread pool: {e}"))?;
    Ok(pool.install(work))
}

/// Indexed collection retains input order, including deterministic first errors.
pub fn map<T: Send>(len: usize, work: impl Fn(usize) -> T + Sync + Send) -> Vec<T> {
    if rayon::current_thread_index().is_some() && rayon::current_num_threads() > 1 {
        (0..len)
            .into_par_iter()
            .with_min_len(32)
            .map(work)
            .collect()
    } else {
        (0..len).map(work).collect()
    }
}

pub fn try_map<T: Send>(
    len: usize,
    work: impl Fn(usize) -> Result<T, String> + Sync + Send,
) -> Result<Vec<T>, String> {
    // Collect Results by index before resolving them: Rayon short-circuiting
    // alone does not promise the same first error as the serial implementation.
    map(len, work).into_iter().collect()
}
