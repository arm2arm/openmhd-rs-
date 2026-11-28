//! Instantaneous conservative finite-volume rates on a periodic 3D geometry.
//! Each face contributes one oriented HLLD flux. The caller supplies the
//! stage cell averages and the actual prescribed generator velocities.
use mhd_core::{Conservative, IdealGas, Primitive, dot, riemann};
use moving_mesh::{
    parallel::{layout::Layout, partition::Partition},
    three_d::{Boundary3, MotionRates3, ValidatedGeometry3, Vec3},
};
pub fn conservative_rates_on<L: Layout>(
    mesh: &ValidatedGeometry3,
    motion: &MotionRates3,
    q: &[Primitive],
    velocity: &[Vec3],
    eos: IdealGas,
    owners: &Partition,
    layout: &L,
) -> Result<Vec<Conservative>, String> {
    if mesh.domain().boundary != Boundary3::Periodic
        || q.len() != mesh.cells().len()
        || q.len() != velocity.len()
        || mesh.epoch() != motion.epoch()
        || layout.ranks() != owners.ranks()
    {
        return Err("incompatible periodic ALE rate inputs".into());
    }
    let send = mesh
        .faces()
        .iter()
        .map(|f| {
            let right = f.right.ok_or("missing periodic neighbour")? as usize;
            owners.face_owner(
                mesh.cells()[f.left as usize].generator.id.entity(),
                Some(mesh.cells()[right].generator.id.entity()),
            )
        })
        .collect::<Result<Vec<_>, _>>()?;
    let fluxes = layout.rows(&send, |i| {
        let f = &mesh.faces()[i];
        let l = f.left as usize;
        let r = f.right.ok_or("missing periodic neighbour")? as usize;
        if l == r {
            return Ok([0.; 5]);
        }
        let handle = mesh.face_ref(i).map_err(|e| e.to_string())?;
        let normal_speed = motion.face(handle).map_err(|e| e.to_string())?.normal_speed;
        let mean = std::array::from_fn(|k| 0.5 * (velocity[l][k] + velocity[r][k]));
        let correction = normal_speed - dot(mean, f.normal);
        let face_velocity = std::array::from_fn(|k| mean[k] + correction * f.normal[k]);
        Ok(riemann(eos, q[l], q[r], f.normal, face_velocity)?
            .fluid
            .map(|v| f.area * v))
    })?;
    let mut rates = vec![[0.; 5]; q.len()];
    for (f, flux) in mesh.faces().iter().zip(fluxes) {
        let l = f.left as usize;
        let r = f.right.ok_or("missing periodic neighbour")? as usize;
        if l != r {
            for (k, v) in flux.into_iter().enumerate() {
                rates[l][k] -= v;
                rates[r][k] += v;
            }
        }
    }
    if rates.iter().flatten().any(|v| !v.is_finite()) {
        return Err("nonfinite extensive rate".into());
    }
    Ok(rates)
}
