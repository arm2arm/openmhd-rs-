//! Instantaneous conservative finite-volume rates on a periodic 3D geometry.
//! Each face contributes one oriented HLLD flux. The caller supplies the
//! stage cell averages and the actual prescribed generator velocities.
use mhd_core::{Conservative, IdealGas, Primitive, dot, riemann};
use moving_mesh::{
    parallel::{halo::FaceHalo, layout::Layout, partition::Partition},
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
    let cell_owners = mesh
        .cells()
        .iter()
        .map(|c| owners.owner(c.generator.id.entity()))
        .collect::<Result<Vec<_>, _>>()?;
    let endpoints = mesh
        .faces()
        .iter()
        .map(|f| (f.left as usize, f.right.map(|r| r as usize)))
        .collect::<Vec<_>>();
    let routes = FaceHalo::new(cell_owners, send, &endpoints)?;
    let states = layout.halo_rows("ale-states", &routes.to_faces, |i| {
        let Primitive {
            density,
            velocity: [vx, vy, vz],
            pressure,
            magnetic: [bx, by, bz],
        } = q[i];
        let [wx, wy, wz] = velocity[i];
        Ok([density, vx, vy, vz, pressure, bx, by, bz, wx, wy, wz])
    })?;
    let unpack = |i: usize| {
        let [density, vx, vy, vz, pressure, bx, by, bz, wx, wy, wz] = states[&i];
        (
            Primitive {
                density,
                velocity: [vx, vy, vz],
                pressure,
                magnetic: [bx, by, bz],
            },
            [wx, wy, wz],
        )
    };
    let fluxes = layout.halo_rows("ale-fluxes", &routes.to_cells, |i| {
        let f = &mesh.faces()[i];
        let l = f.left as usize;
        let r = f.right.ok_or("missing periodic neighbour")? as usize;
        if l == r {
            return Ok([0.; 5]);
        }
        let ((ql, wl), (qr, wr)) = (unpack(l), unpack(r));
        let handle = mesh.face_ref(i).map_err(|e| e.to_string())?;
        let normal_speed = motion.face(handle).map_err(|e| e.to_string())?.normal_speed;
        let mean = std::array::from_fn(|k| 0.5 * (wl[k] + wr[k]));
        let correction = normal_speed - dot(mean, f.normal);
        let face_velocity = std::array::from_fn(|k| mean[k] + correction * f.normal[k]);
        Ok(riemann(eos, ql, qr, f.normal, face_velocity)?
            .fluid
            .map(|v| f.area * v))
    })?;
    layout.rows(routes.to_faces.owners(), |i| {
        let mut rate = [0.; 5];
        for &(j, forward) in &routes.incidences[i] {
            for (x, v) in rate.iter_mut().zip(fluxes[&j]) {
                if forward {
                    *x -= v;
                } else {
                    *x += v;
                }
            }
        }
        if rate.iter().any(|v| !v.is_finite()) {
            return Err("nonfinite extensive rate".into());
        }
        Ok(rate)
    })
}
