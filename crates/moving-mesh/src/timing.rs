//! Coarse wall-clock phase accounting for performance diagnosis.
//! Timers and counters are observations only: nothing reads them back into a
//! numerical state, and they are reported in `timing.json`, never in a summary.
//! Scopes are meant for whole phases on the calling thread, not for the body
//! of a parallel map. Nested scopes report inclusive times.
use std::sync::Mutex;
use std::time::Instant;

static TABLE: Mutex<Vec<(&'static str, f64, u64)>> = Mutex::new(Vec::new());

fn add(name: &'static str, seconds: f64, events: u64) {
    // A poisoned table only means another thread panicked while reporting.
    let mut table = TABLE.lock().unwrap_or_else(|poison| poison.into_inner());
    if let Some(row) = table.iter_mut().find(|row| row.0 == name) {
        row.1 += seconds;
        row.2 += events;
    } else {
        table.push((name, seconds, events));
    }
}

/// Accumulates the elapsed wall time of one phase when dropped.
pub struct Scope {
    name: &'static str,
    start: Instant,
}
impl Drop for Scope {
    fn drop(&mut self) {
        add(self.name, self.start.elapsed().as_secs_f64(), 1);
    }
}

/// Time the enclosing block under `name`; bind the result to a named variable.
pub fn scope(name: &'static str) -> Scope {
    Scope {
        name,
        start: Instant::now(),
    }
}

/// Count events that have no duration, such as rejected trial steps.
pub fn count(name: &'static str, events: u64) {
    add(name, 0., events);
}

/// `(name, seconds, events)` in first-use order.
pub fn report() -> Vec<(&'static str, f64, u64)> {
    TABLE
        .lock()
        .unwrap_or_else(|poison| poison.into_inner())
        .clone()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn scopes_and_counters_accumulate_by_name() {
        {
            let _outer = scope("timing-test/outer");
            let _inner = scope("timing-test/inner");
            count("timing-test/events", 3);
        }
        {
            let _outer = scope("timing-test/outer");
        }
        count("timing-test/events", 2);
        let rows = report();
        let find = |name: &str| rows.iter().find(|row| row.0 == name).copied().unwrap();
        assert_eq!(find("timing-test/outer").2, 2);
        assert_eq!(find("timing-test/inner").2, 1);
        assert_eq!(find("timing-test/events"), ("timing-test/events", 0., 5));
        assert!(find("timing-test/outer").1 >= find("timing-test/inner").1);
        assert!(rows.iter().all(|row| row.1.is_finite() && row.1 >= 0.));
    }
}
