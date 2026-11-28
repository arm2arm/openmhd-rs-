//! Rayon dispatch for the same C force tiles used by the OpenMP benchmark.
use rayon::prelude::*;

unsafe extern "C" {
    fn gravity_tile(tile: i32);
}

#[unsafe(no_mangle)]
pub extern "C" fn rayon_team_init(threads: i32) -> i32 {
    if threads <= 0
        || rayon::ThreadPoolBuilder::new()
            .num_threads(threads as usize)
            .build_global()
            .is_err()
    {
        return 0;
    }
    rayon::broadcast(|_| ()).len() as i32
}

#[unsafe(no_mangle)]
pub extern "C" fn rayon_force_tiles(tiles: i32) {
    (0..tiles).into_par_iter().for_each(|tile| {
        // The catalogue is read-only. Each tile owns a disjoint output slice,
        // and this call joins all tiles before the MPI gather starts.
        unsafe { gravity_tile(tile) };
    });
}
