//! Versioned exact-bit persistence of accepted general-reference states.
use super::*;
use mhd_io::{Decoder, Encoder};
use moving_mesh::checkpoint as mesh_io;
use std::path::Path;
use std::sync::OnceLock;
include!(concat!(env!("OUT_DIR"), "/restart_build.rs"));
const VERSION: u64 = 1;
// Include the actual artifact as well as source/build metadata: Cargo configuration
// can alter code generation without exposing every effective setting to build.rs.
fn executable_fingerprint() -> Result<[u8; 32], String> {
    static HASH: OnceLock<Result<[u8; 32], String>> = OnceLock::new();
    HASH.get_or_init(|| {
        let path = std::env::current_exe().map_err(|e| e.to_string())?;
        let bytes = std::fs::read(path).map_err(|e| e.to_string())?;
        Ok(mhd_io::digest(&[&bytes]))
    })
    .clone()
}
const PROFILES: [Profile; 8] = [
    Profile::PaperGlobalV2,
    Profile::BulkFrameV1,
    Profile::BulkFrameHllV1,
    Profile::BulkFrameHllQuadraticV1,
    Profile::BulkFrameHllConsistentV1,
    Profile::BulkFrameHllMatchedV1,
    Profile::BulkFrameHllCompactV1,
    Profile::BulkFrameHllProjectedV1,
];
fn write_rows<const N: usize>(w: &mut Encoder, rows: &[[f64; N]]) {
    w.usize(rows.len());
    for row in rows {
        w.floats(row);
    }
}
fn read_rows<const N: usize>(r: &mut Decoder<'_>) -> Result<Vec<[f64; N]>, String> {
    let n = r.count(N * 8)?;
    (0..n).map(|_| r.floats()).collect()
}
impl Simulation {
    /// SHA-256 of relevant source bytes, locked dependencies and compiler/build settings.
    pub fn restart_fingerprint() -> [u8; 32] {
        mhd_io::digest(SOURCE_PARTS)
    }
    /// Metadata belongs to the caller (e.g. pending output targets); it shares the checksum.
    pub fn checkpoint_bytes(&self, metadata: &[u8]) -> Result<Vec<u8>, String> {
        self.validate_restart()?;
        if mesh_io::mesh_bytes(&self.state.mesh)? != mesh_io::mesh_bytes(&self.geometry.mesh)? {
            return Err("accepted mesh/cache mismatch".into());
        }
        let mut w = Encoder::new();
        w.bytes(&Self::restart_fingerprint());
        w.bytes(&executable_fingerprint()?);
        let c = &self.config;
        w.usize(PROFILES.iter().position(|p| *p == c.profile).unwrap());
        w.float(c.gamma);
        w.floats(&c.mean_magnetic);
        match &c.motion {
            Motion::Fixed => w.u64(0),
            Motion::Rigid(v) => {
                w.u64(1);
                w.floats(v);
            }
            Motion::Fluid => w.u64(2),
            Motion::Prescribed(v) => {
                w.u64(3);
                write_rows(&mut w, v);
            }
        }
        w.float(c.cfl);
        w.float(c.max_dt);
        w.boolean(c.limited);
        w.float(c.magnetic_scale);
        w.float(self.time);
        w.floats(&self.reference_velocity);
        w.floats(&self.initial_totals);
        w.floats(&self.budget_scales);
        w.floats(&self.initial_mean);
        let s = &self.state;
        write_rows(&mut w, &s.potential);
        w.floats(&s.gauge_offset);
        w.usize(s.phi.len());
        for &p in &s.phi {
            w.float(p);
        }
        write_rows(&mut w, &s.conserved);
        w.floats(&s.auxiliary_origin);
        let c = &self.counters;
        for n in [
            c.steps,
            c.rejected_geometry,
            c.rejected_state,
            c.rejected_cfl,
            c.hll_fallbacks,
            c.hll_fallbacks_attempted,
            c.auxiliary_coarsenings,
        ] {
            w.usize(n);
        }
        w.usize(c.auxiliary_roots.len());
        for &n in &c.auxiliary_roots {
            w.usize(n);
        }
        w.boolean(c.min_dt.is_some());
        if let Some(d) = c.min_dt {
            w.float(d);
        }
        for d in [
            c.max_dt,
            c.max_signal_x,
            c.max_face_signal,
            c.integrated_signal_travel,
            c.geometric_conservation_max,
        ] {
            w.float(d);
        }
        let g = &self.geometry;
        w.bytes(&mesh_io::encode(
            &g.mesh,
            &g.neighbours,
            &g.faces,
            g.quadratic.as_ref(),
            g.compact.as_ref(),
        )?);
        w.bytes(metadata);
        Ok(mhd_io::seal(VERSION, &w.finish()))
    }
    pub fn from_checkpoint(bytes: &[u8]) -> Result<(Self, Vec<u8>), String> {
        let mut r = Decoder::new(mhd_io::unseal(bytes, VERSION)?);
        if r.bytes()? != Self::restart_fingerprint() {
            return Err("restart is incompatible with this source/compiler/target/build; use the original compatible build".into());
        }
        if r.bytes()? != executable_fingerprint()? {
            return Err(
                "restart executable fingerprint differs; use the saved original executable".into(),
            );
        }
        let profile = *PROFILES.get(r.usize()?).ok_or("invalid restart profile")?;
        let gamma = r.float()?;
        let mean_magnetic = r.floats()?;
        let motion = match r.u64()? {
            0 => Motion::Fixed,
            1 => Motion::Rigid(r.floats()?),
            2 => Motion::Fluid,
            3 => Motion::Prescribed(read_rows(&mut r)?),
            _ => return Err("invalid restart motion".into()),
        };
        let config = Config {
            profile,
            gamma,
            mean_magnetic,
            motion,
            cfl: r.float()?,
            max_dt: r.float()?,
            limited: r.boolean()?,
            magnetic_scale: r.float()?,
        };
        let time = r.float()?;
        let reference_velocity = r.floats()?;
        let initial_totals = r.floats()?;
        let budget_scales = r.floats()?;
        let initial_mean = r.floats()?;
        let potential = read_rows(&mut r)?;
        let gauge_offset = r.floats()?;
        let n = r.count(8)?;
        let phi = (0..n).map(|_| r.float()).collect::<Result<_, _>>()?;
        let conserved = read_rows(&mut r)?;
        let auxiliary_origin = r.floats()?;
        let mut counters = Counters {
            steps: r.usize()?,
            rejected_geometry: r.usize()?,
            rejected_state: r.usize()?,
            rejected_cfl: r.usize()?,
            hll_fallbacks: r.usize()?,
            hll_fallbacks_attempted: r.usize()?,
            auxiliary_coarsenings: r.usize()?,
            ..Counters::default()
        };
        let n = r.count(8)?;
        counters.auxiliary_roots = (0..n).map(|_| r.usize()).collect::<Result<_, _>>()?;
        counters.min_dt = if r.boolean()? { Some(r.float()?) } else { None };
        counters.max_dt = r.float()?;
        counters.max_signal_x = r.float()?;
        counters.max_face_signal = r.float()?;
        counters.integrated_signal_travel = r.float()?;
        counters.geometric_conservation_max = r.float()?;
        let g = mesh_io::decode(r.bytes()?)?;
        let state = State {
            mesh: g.mesh.clone(),
            potential,
            gauge_offset,
            phi,
            conserved,
            auxiliary_origin,
        };
        let geometry = Arc::new(Geometry {
            mesh: g.mesh,
            neighbours: g.neighbours,
            faces: g.faces,
            quadratic: g.quadratic,
            compact: g.compact,
        });
        let metadata = r.bytes()?.to_vec();
        r.finish()?;
        let sim = Self {
            state,
            geometry,
            config,
            time,
            reference_velocity,
            counters,
            initial_totals,
            budget_scales,
            initial_mean,
        };
        sim.validate_restart()?;
        sim.primitives()?;
        Ok((sim, metadata))
    }
    pub fn write_checkpoint(&self, path: &Path, metadata: &[u8]) -> Result<(), String> {
        mhd_io::write_atomic(path, &self.checkpoint_bytes(metadata)?)
    }
    pub fn read_checkpoint(path: &Path) -> Result<(Self, Vec<u8>), String> {
        Self::from_checkpoint(&std::fs::read(path).map_err(|e| format!("{}: {e}", path.display()))?)
    }
    fn validate_restart(&self) -> Result<(), String> {
        let c = &self.config;
        let s = &self.state;
        let n = s.mesh.cells.len();
        let k = &self.counters;
        // Reserve ample integer headroom for the remaining bounded run. These
        // counters are diagnostics, never inputs to a physical reconstruction.
        let count_limit = (1_000_001_u128 * n as u128 * 1024).min((usize::MAX / 2) as u128);
        if [
            k.rejected_geometry,
            k.rejected_state,
            k.rejected_cfl,
            k.hll_fallbacks,
            k.hll_fallbacks_attempted,
            k.auxiliary_coarsenings,
        ]
        .iter()
        .any(|&v| v as u128 > count_limit)
        {
            return Err("restart counter exceeds supported range".into());
        }
        IdealGas::new(c.gamma)?;
        if !c.cfl.is_finite()
            || c.cfl <= 0.
            || c.cfl > 0.3
            || c.max_dt.is_nan()
            || c.max_dt <= 0.
            || !c.magnetic_scale.is_finite()
            || c.magnetic_scale <= 0.
        {
            return Err("invalid restart configuration".into());
        }
        match &c.motion {
            Motion::Rigid(v) if !v.iter().all(|x| x.is_finite()) => {
                return Err("invalid rigid restart velocity".into());
            }
            Motion::Prescribed(v) if v.len() != n || !v.iter().flatten().all(|x| x.is_finite()) => {
                return Err("invalid prescribed restart velocities".into());
            }
            _ => {}
        }
        if self.geometry.quadratic.is_some() != c.profile.quadratic()
            || self.geometry.compact.is_some() != c.profile.compact()
            || s.potential.len() != n
            || s.phi.len() != n
            || s.conserved.len() != n
        {
            return Err("restart state/profile shape mismatch".into());
        }
        if !s
            .potential
            .iter()
            .flatten()
            .chain(s.phi.iter())
            .chain(s.conserved.iter().flatten())
            .chain(&s.gauge_offset)
            .chain(&s.auxiliary_origin)
            .chain(&c.mean_magnetic)
            .chain(&self.reference_velocity)
            .chain(&self.initial_totals)
            .chain(&self.budget_scales)
            .chain(&self.initial_mean)
            .all(|x| x.is_finite())
            || self.budget_scales.iter().any(|x| *x <= 0.)
            || !self.time.is_finite()
            || self.time < 0.
        {
            return Err("invalid restart state or baselines".into());
        }
        if k.steps > 1_000_000
            || k.auxiliary_roots.len() != k.steps
            || k.auxiliary_roots.iter().any(|x| ![1, 2, 4].contains(x))
            || k.hll_fallbacks > k.hll_fallbacks_attempted
            || k.min_dt.is_some() != (k.steps > 0)
            || (k.steps == 0) != (self.time == 0.)
            || k.min_dt
                .is_some_and(|x| !x.is_finite() || x <= 0. || x > k.max_dt)
            || ![
                k.max_dt,
                k.max_signal_x,
                k.max_face_signal,
                k.integrated_signal_travel,
                k.geometric_conservation_max,
            ]
            .iter()
            .all(|x| x.is_finite() && *x >= 0.)
        {
            return Err("invalid restart counters".into());
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f64::consts::TAU;
    fn make(profile: Profile, motion: Motion, limited: bool, jitter: f64) -> Simulation {
        Simulation::new(
            Mesh::lattice(6, 6, [1.; 2], jitter).unwrap(),
            Config {
                profile,
                motion,
                limited,
                mean_magnetic: [1., 0.2, -0.1],
                ..Config::default()
            },
            |p| {
                let mut q = crate::benchmarks::alfven_initial(p, 0., [4., -3., 0.5]);
                q.phi = 0.0001 * (TAU * p[0]).sin();
                q
            },
        )
        .unwrap()
    }
    fn roundtrip(sim: &Simulation) -> Simulation {
        let bytes = sim.checkpoint_bytes(b"driver metadata").unwrap();
        let (copy, metadata) = Simulation::from_checkpoint(&bytes).unwrap();
        assert_eq!(metadata, b"driver metadata");
        assert_eq!(bytes, copy.checkpoint_bytes(&metadata).unwrap());
        copy
    }
    #[test]
    fn accepted_step_resume_matches_every_final_state_bit() {
        let mut rejected = 0;
        let mut cases = PROFILES
            .iter()
            .map(|&p| (p, Motion::Fixed, true, 0.15))
            .collect::<Vec<_>>();
        cases.push((
            Profile::BulkFrameHllProjectedV1,
            Motion::Rigid([4., -3.]),
            true,
            0.15,
        ));
        cases.push((Profile::BulkFrameHllProjectedV1, Motion::Fluid, false, 0.15));
        let mesh = Mesh::lattice(6, 6, [1.; 2], 0.).unwrap();
        let velocities = mesh
            .generators
            .iter()
            .map(|p| [0.1 * (TAU * p[1]).sin(), 0.1 * (TAU * p[0]).cos()])
            .collect();
        cases.push((
            Profile::BulkFrameHllProjectedV1,
            Motion::Prescribed(velocities),
            true,
            0.,
        ));
        for (profile, motion, limited, jitter) in cases {
            let mut whole = make(profile, motion, limited, jitter);
            let original_faces = whole.state.mesh.faces.len();
            let mut split = roundtrip(&whole); // Includes valid infinite timestep cap and zero counters.
            whole.advance_to(0.05).unwrap();
            assert!(
                !split
                    .advance_with_observer(0.05, |s| Ok(if s.counters.steps == 3 {
                        StepControl::Stop
                    } else {
                        StepControl::Continue
                    }))
                    .unwrap()
            );
            assert!(split.time < 0.05);
            split = roundtrip(&split);
            split.advance_to(0.05).unwrap();
            assert_eq!(
                whole.checkpoint_bytes(b"").unwrap(),
                split.checkpoint_bytes(b"").unwrap(),
                "profile {}",
                profile.name()
            );
            assert_eq!(
                format!("{:?}", whole.diagnostics().unwrap()),
                format!("{:?}", split.diagnostics().unwrap())
            );
            rejected += whole.counters.rejected_cfl
                + whole.counters.rejected_geometry
                + whole.counters.rejected_state;
            if matches!(whole.config.motion, Motion::Rigid(_)) {
                assert_ne!(whole.state.gauge_offset, [0.; 3]);
                assert_ne!(whole.state.auxiliary_origin, [0.; 2]);
                assert!(
                    whole
                        .state
                        .mesh
                        .generators
                        .iter()
                        .zip(
                            &make(profile, Motion::Rigid([4., -3.]), limited, jitter)
                                .state
                                .mesh
                                .generators
                        )
                        .any(|(p, q)| p[0] < q[0])
                );
            }
            if matches!(whole.config.motion, Motion::Prescribed(_)) {
                assert_ne!(original_faces, whole.state.mesh.faces.len());
            }
        }
        assert!(
            rejected > 0,
            "exercise counters after discarded trial steps"
        );
    }
    #[test]
    fn incompatible_or_invalid_checkpoint_is_rejected() {
        let mut sim = make(Profile::BulkFrameHllProjectedV1, Motion::Fixed, true, 0.15);
        let bytes = sim.checkpoint_bytes(b"").unwrap();
        let mut payload = mhd_io::unseal(&bytes, VERSION).unwrap().to_vec();
        payload[8] ^= 1;
        assert!(
            Simulation::from_checkpoint(&mhd_io::seal(VERSION, &payload))
                .unwrap_err()
                .contains("incompatible")
        );
        sim.state.phi.pop();
        assert!(sim.checkpoint_bytes(b"").is_err());
        sim.state.phi.push(f64::NAN);
        assert!(sim.checkpoint_bytes(b"").is_err());
        sim.state.phi.fill(0.);
        sim.counters.hll_fallbacks_attempted = usize::MAX;
        assert!(sim.checkpoint_bytes(b"").is_err());
    }
    #[test]
    fn observer_error_retains_complete_accepted_state() {
        let mut sim = make(Profile::BulkFrameHllProjectedV1, Motion::Fixed, true, 0.15);
        let error = sim
            .advance_with_observer(0.05, |_| Err("simulated write failure".into()))
            .unwrap_err();
        assert_eq!(error, "simulated write failure");
        assert_eq!(sim.counters.steps, 1);
        let mut resumed = roundtrip(&sim);
        resumed.advance_to(0.05).unwrap();
        let mut whole = make(Profile::BulkFrameHllProjectedV1, Motion::Fixed, true, 0.15);
        whole.advance_to(0.05).unwrap();
        assert_eq!(
            resumed.checkpoint_bytes(b"").unwrap(),
            whole.checkpoint_bytes(b"").unwrap()
        );
    }
}
