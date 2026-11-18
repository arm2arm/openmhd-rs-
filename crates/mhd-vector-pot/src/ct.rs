//! Independent fixed/rigid Voronoi constrained-transport comparator.
//! Mocz et al. (2014), equations 25–32, with explicit Heun/2.5D extensions.
//! Not the Springel et al. (2026) cell-centred A method. See M1_CT_COMPARATOR.md.

use crate::operators::{components, gradients, primitive};
use mhd_core::{Conservative, FluxMethod, IdealGas, Primitive, cross, riemann, riemann_rusanov};
use moving_mesh::{Derivatives, Mesh, Vec2, dot};
use std::collections::BTreeMap;

pub const PROFILE: &str = "voronoi-ct-heun-v1";
pub const ADMISSIBLE_PROFILE: &str = "voronoi-ct-admissible-v1";

/// Frozen-rate comparators; the historical CT evolution remains reconstructed HLLD.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RateScheme {
    ReconstructedHlld,
    CellHlld,
    CellRusanov,
}

fn inverse(a: f64, b: f64, c: f64) -> Result<[f64; 3], String> {
    let det = a * c - b * b;
    if !det.is_finite() || det <= 1e-12 * (a + c).powi(2) {
        return Err("ill-conditioned CT fit".into());
    }
    Ok([c / det, -b / det, a / det])
}
fn multiply(m: [f64; 3], v: Vec2) -> Vec2 {
    [m[0] * v[0] + m[1] * v[1], m[1] * v[0] + m[2] * v[1]]
}
fn periodic_delta(a: Vec2, b: Vec2, lengths: Vec2) -> Vec2 {
    std::array::from_fn(|k| {
        let d = a[k] - b[k];
        d - (d / lengths[k]).round() * lengths[k]
    })
}

/// Cached oriented incidence and linear recovery on immutable comoving geometry.
#[derive(Clone, Debug)]
pub struct Geometry {
    pub vertices: Vec<Vec2>,
    /// Minus/plus endpoint in direction t=(-ny,nx) of the stored face normal.
    pub endpoints: Vec<[usize; 2]>,
    interpolation: Vec<Vec<(usize, f64)>>,
    recovery: Vec<Vec<(usize, Vec2)>>,
}
impl Geometry {
    pub fn new(mesh: &Mesh) -> Result<Self, String> {
        mesh.validate()?;
        let mut vertices: Vec<Vec2> = Vec::new();
        let mut incident: Vec<Vec<usize>> = Vec::new();
        let mut buckets: BTreeMap<[i64; 2], Vec<usize>> = BTreeMap::new();
        // Spatial hash is only a candidate search; an actual distance test and
        // exact cell incidence check below reject incorrect endpoint matches.
        let bins = 1_000_000_000_i64;
        let tolerance = 1e-10 * mesh.lengths[0].min(mesh.lengths[1]);
        let mut endpoints = Vec::new();
        for (f, face) in mesh.faces.iter().enumerate() {
            let mut ids = [0; 2];
            for (slot, sign) in [-1., 1.].into_iter().enumerate() {
                let t = [-face.normal[1], face.normal[0]];
                let p = std::array::from_fn(|k| {
                    (face.centroid[k] + sign * 0.5 * face.area * t[k]).rem_euclid(mesh.lengths[k])
                });
                let key: [i64; 2] = std::array::from_fn(|k| {
                    ((p[k] / mesh.lengths[k] * bins as f64).floor() as i64).rem_euclid(bins)
                });
                let mut matches = Vec::new();
                for dx in -1..=1 {
                    for dy in -1..=1 {
                        let key = [
                            (key[0] + dx).rem_euclid(bins),
                            (key[1] + dy).rem_euclid(bins),
                        ];
                        if let Some(candidates) = buckets.get(&key) {
                            for &v in candidates {
                                let d = periodic_delta(p, vertices[v], mesh.lengths);
                                if d[0].hypot(d[1]) <= tolerance {
                                    matches.push(v);
                                }
                            }
                        }
                    }
                }
                if matches.len() > 1 {
                    return Err("ambiguous CT vertex match".into());
                }
                let v = if let Some(&v) = matches.first() {
                    v
                } else {
                    let v = vertices.len();
                    vertices.push(p);
                    incident.push(Vec::new());
                    buckets.entry(key).or_default().push(v);
                    v
                };
                ids[slot] = v;
                incident[v].push(f);
            }
            if ids[0] == ids[1] {
                return Err("collapsed CT face".into());
            }
            endpoints.push(ids);
        }
        for cell in &mesh.cells {
            let mut incidence: BTreeMap<usize, i32> = BTreeMap::new();
            for &(f, sign) in &cell.faces {
                *incidence.entry(endpoints[f][0]).or_default() -= sign as i32;
                *incidence.entry(endpoints[f][1]).or_default() += sign as i32;
            }
            if incidence.values().any(|&n| n != 0) {
                return Err("CT cell boundary does not telescope".into());
            }
        }
        let mut interpolation = Vec::new();
        for (v, faces) in incident.iter().enumerate() {
            if faces.len() < 3 {
                return Err("CT vertex has fewer than three faces".into());
            }
            let offsets: Vec<_> = faces
                .iter()
                .map(|&f| periodic_delta(mesh.faces[f].centroid, vertices[v], mesh.lengths))
                .collect();
            let scale = offsets.iter().map(|d| d[0].hypot(d[1])).fold(0., f64::max);
            let x: Vec<Vec2> = offsets.iter().map(|d| d.map(|q| q / scale)).collect();
            let count = faces.len() as f64;
            let mean: Vec2 = std::array::from_fn(|k| x.iter().map(|d| d[k]).sum::<f64>() / count);
            let mut cov = [0.; 3];
            for d in &x {
                let d = [d[0] - mean[0], d[1] - mean[1]];
                cov[0] += d[0] * d[0];
                cov[1] += d[0] * d[1];
                cov[2] += d[1] * d[1];
            }
            let correction = multiply(inverse(cov[0], cov[1], cov[2])?, mean);
            let row: Vec<_> = faces
                .iter()
                .zip(&x)
                .map(|(&f, d)| {
                    (
                        f,
                        1. / count - dot(correction, [d[0] - mean[0], d[1] - mean[1]]),
                    )
                })
                .collect();
            let sum: f64 = row.iter().map(|(_, w)| w).sum();
            let moment: Vec2 =
                std::array::from_fn(|k| row.iter().zip(&x).map(|((_, w), d)| w * d[k]).sum());
            if (sum - 1.).abs() > 1e-10 || moment.iter().any(|d| d.abs() > 1e-10) {
                return Err("CT EMF interpolation violates affine moments".into());
            }
            interpolation.push(row);
        }
        let mut recovery = Vec::new();
        for (i, cell) in mesh.cells.iter().enumerate() {
            let mut matrix = [0.; 3];
            let mut rows = Vec::new();
            for &(f, _) in &cell.faces {
                let face = &mesh.faces[f];
                let d = mesh.displacement(face, i);
                let w2 = 1. / dot(d, d);
                let n = face.normal;
                matrix[0] += w2 * n[0] * n[0];
                matrix[1] += w2 * n[0] * n[1];
                matrix[2] += w2 * n[1] * n[1];
                rows.push((f, n.map(|x| w2 * x / face.area)));
            }
            let inv = inverse(matrix[0], matrix[1], matrix[2])?;
            recovery.push(
                rows.into_iter()
                    .map(|(f, r)| (f, multiply(inv, r)))
                    .collect(),
            );
        }
        Ok(Self {
            vertices,
            endpoints,
            interpolation,
            recovery,
        })
    }
    pub fn fluxes(&self, mesh: &Mesh, az: impl Fn(Vec2) -> f64, mean: Vec2) -> Vec<f64> {
        let a: Vec<_> = self.vertices.iter().map(|&x| az(x)).collect();
        self.endpoints
            .iter()
            .zip(&mesh.faces)
            .map(|(&[minus, plus], f)| a[plus] - a[minus] + f.area * dot(mean, f.normal))
            .collect()
    }
    pub fn field(&self, flux: &[f64]) -> Vec<Vec2> {
        self.recovery
            .iter()
            .map(|row| std::array::from_fn(|k| row.iter().map(|&(f, w)| w[k] * flux[f]).sum()))
            .collect()
    }
    pub fn flux_rate(&self, face_emf: &[f64]) -> Vec<f64> {
        let vertex: Vec<f64> = self
            .interpolation
            .iter()
            .map(|row| row.iter().map(|&(f, w)| w * face_emf[f]).sum())
            .collect();
        self.endpoints
            .iter()
            .map(|&[minus, plus]| vertex[plus] - vertex[minus])
            .collect()
    }
    pub fn divergence(&self, mesh: &Mesh, flux: &[f64]) -> Vec<f64> {
        mesh.cells
            .iter()
            .map(|c| c.faces.iter().map(|&(f, s)| s * flux[f]).sum::<f64>() / c.volume)
            .collect()
    }
}

#[derive(Clone, Debug)]
pub struct Config {
    /// Separate global conservative convex limiter; not a positivity theorem.
    pub admissible_limiter: bool,
    pub gamma: f64,
    pub mean_xy: Vec2,
    pub mesh_velocity: Vec2,
    pub cfl: f64,
    pub max_dt: f64,
}
impl Default for Config {
    fn default() -> Self {
        Self {
            admissible_limiter: false,
            gamma: 5. / 3.,
            mean_xy: [0.; 2],
            mesh_velocity: [0.; 2],
            cfl: 0.3,
            max_dt: f64::INFINITY,
        }
    }
}
#[derive(Clone, Debug)]
pub struct State {
    pub fluid: Vec<Conservative>,
    pub flux: Vec<f64>,
    pub bz_integral: Vec<f64>,
}
#[derive(Debug)]
struct Rate {
    state: State,
    dt: f64,
    fallbacks: usize,
}

#[derive(Clone, Debug)]
pub struct Simulation {
    pub config: Config,
    /// Immutable comoving geometry; add mesh_velocity*time for lab positions.
    pub mesh: Mesh,
    pub geometry: Geometry,
    pub state: State,
    pub eos: IdealGas,
    pub time: f64,
    pub steps: usize,
    pub rejections: usize,
    pub hll_fallbacks: usize,
    pub hll_fallbacks_attempted: usize,
    pub limited_stages: usize,
    pub minimum_theta: f64,
    pub low_order_rejections: usize,
    /// Failed high-order rate evaluations, including discarded attempts.
    pub high_order_rate_failures: usize,
    stencil: Derivatives,
    initial_totals: Conservative,
    budget_scale: Conservative,
}
#[derive(Clone, Debug)]
pub struct Diagnostics {
    pub min_density: f64,
    pub min_pressure: f64,
    pub magnetic_energy: f64,
    pub budget_max: f64,
    pub div_ct_max: f64,
    pub div_ct_rms: f64,
    pub div_ls_rms: f64,
    pub div_face_rms: f64,
}

impl Simulation {
    /// initial returns (periodic Az, physical primitive); Bxy is replaced by
    /// the face-flux recovery before constructing the initial fluid energy.
    pub fn new(
        mesh: Mesh,
        config: Config,
        initial: impl Fn(Vec2) -> (f64, Primitive),
    ) -> Result<Self, String> {
        if !config.cfl.is_finite()
            || config.cfl <= 0.
            || config.cfl > 0.4
            || config.max_dt.is_nan()
            || config.max_dt <= 0.
            || !config
                .mean_xy
                .iter()
                .chain(&config.mesh_velocity)
                .all(|x| x.is_finite())
        {
            return Err("invalid CT configuration".into());
        }
        let eos = IdealGas::new(config.gamma)?;
        let geometry = Geometry::new(&mesh)?;
        let stencil = Derivatives::build(&mesh, false)?;
        let flux = geometry.fluxes(&mesh, |x| initial(x).0, config.mean_xy);
        let magnetic = geometry.field(&flux);
        let mut fluid = Vec::new();
        let mut bz_integral = Vec::new();
        for (i, c) in mesh.cells.iter().enumerate() {
            let x = std::array::from_fn(|k| c.centroid[k].rem_euclid(mesh.lengths[k]));
            let mut q = initial(x).1;
            q.magnetic[0] = magnetic[i][0];
            q.magnetic[1] = magnetic[i][1];
            fluid.push(eos.conservative(q)?.map(|x| x * c.volume));
            bz_integral.push(q.magnetic[2] * c.volume);
        }
        let initial_totals: Conservative =
            std::array::from_fn(|k| fluid.iter().map(|q| q[k]).sum());
        // Fixed initial L1 integrals with a mass/energy-derived momentum scale.
        let momentum_scale = (2. * initial_totals[0] * initial_totals[4]).sqrt();
        let budget_scale = std::array::from_fn(|k| {
            fluid
                .iter()
                .map(|q| q[k].abs())
                .sum::<f64>()
                .max(if (1..4).contains(&k) {
                    momentum_scale
                } else {
                    initial_totals[k].abs()
                })
        });
        Ok(Self {
            config,
            mesh,
            geometry,
            state: State {
                fluid,
                flux,
                bz_integral,
            },
            eos,
            time: 0.,
            steps: 0,
            rejections: 0,
            hll_fallbacks: 0,
            hll_fallbacks_attempted: 0,
            limited_stages: 0,
            minimum_theta: 1.,
            low_order_rejections: 0,
            high_order_rate_failures: 0,
            stencil,
            initial_totals,
            budget_scale,
        })
    }
    pub fn recover(&self, state: &State) -> Result<Vec<Primitive>, String> {
        if state.fluid.len() != self.mesh.cells.len()
            || state.bz_integral.len() != self.mesh.cells.len()
            || state.flux.len() != self.mesh.faces.len()
        {
            return Err("invalid CT state dimensions".into());
        }
        let b = self.geometry.field(&state.flux);
        self.mesh
            .cells
            .iter()
            .enumerate()
            .map(|(i, c)| {
                self.eos
                    .recover(
                        state.fluid[i].map(|q| q / c.volume),
                        [b[i][0], b[i][1], state.bz_integral[i] / c.volume],
                    )
                    .map_err(|e| format!("CT cell {i}: {e}"))
            })
            .collect()
    }
    fn rate(&self, state: &State, attempted: &mut usize) -> Result<Rate, String> {
        self.rate_with_scheme(state, attempted, RateScheme::ReconstructedHlld)
    }
    fn rate_with_scheme(
        &self,
        state: &State,
        attempted: &mut usize,
        scheme: RateScheme,
    ) -> Result<Rate, String> {
        let q = self.recover(state)?;
        let arrays: Vec<_> = q.iter().map(|&p| components(p)).collect();
        let g = if scheme == RateScheme::ReconstructedHlld {
            gradients(&self.mesh, &self.stencil, &arrays, true)?
        } else {
            vec![[[0.; 2]; 8]; q.len()]
        };
        let w = [
            self.config.mesh_velocity[0],
            self.config.mesh_velocity[1],
            0.,
        ];
        let mut out = State {
            fluid: vec![[0.; 5]; q.len()],
            flux: Vec::new(),
            bz_integral: vec![0.; q.len()],
        };
        let mut speed = vec![0.; q.len()];
        let mut emf = Vec::new();
        let mut fallbacks = 0;
        for f in &self.mesh.faces {
            let reconstruct = |i| {
                let d = self.mesh.displacement(f, i);
                primitive(std::array::from_fn(|k| arrays[i][k] + dot(g[i][k], d)))
            };
            let solve = if scheme == RateScheme::CellRusanov {
                riemann_rusanov
            } else {
                riemann
            };
            let flux = solve(
                self.eos,
                reconstruct(f.left)?,
                reconstruct(f.right)?,
                [f.normal[0], f.normal[1], 0.],
                w,
            )?;
            if flux.method == FluxMethod::HllFallback {
                fallbacks += 1;
                *attempted += 1;
            }
            for (i, s) in [(f.left, -1.), (f.right, 1.)] {
                for k in 0..5 {
                    out.fluid[i][k] += s * f.area * flux.fluid[k];
                }
                out.bz_integral[i] += s * f.area * flux.induction[2];
                speed[i] += f.area * flux.max_speed;
            }
            emf.push(flux.electromotive[2] - cross(w, flux.magnetic)[2]);
        }
        out.flux = self.geometry.flux_rate(&emf);
        let dt = self
            .mesh
            .cells
            .iter()
            .zip(speed)
            .map(|(c, s)| self.config.cfl * c.volume / s)
            .fold(self.config.max_dt, f64::min);
        if !dt.is_finite()
            || dt <= 0.
            || !out
                .flux
                .iter()
                .chain(&out.bz_integral)
                .chain(out.fluid.iter().flatten())
                .all(|x| x.is_finite())
        {
            return Err("nonfinite CT rate or CFL bound".into());
        }
        Ok(Rate {
            state: out,
            dt,
            fallbacks,
        })
    }
    /// One accepted Heun step; invalid stages retry without altering old state.
    pub fn step(&mut self, target: f64) -> Result<(), String> {
        if !target.is_finite() || target <= self.time {
            return Err("invalid CT target".into());
        }
        if self.config.admissible_limiter {
            return self.step_admissible(target);
        }
        let mut attempted = 0;
        let r0 = self.rate(&self.state, &mut attempted);
        self.hll_fallbacks_attempted += attempted;
        let r0 = r0?;
        let mut dt = r0.dt.min(target - self.time);
        let mut last = String::new();
        for _ in 0..16 {
            let trial = add(&self.state, &r0.state, dt);
            let mut attempted = 0;
            let r1 = self.rate(&trial, &mut attempted);
            self.hll_fallbacks_attempted += attempted;
            let accepted = r1.and_then(|r1| {
                if dt > r1.dt * (1. + 1e-12) {
                    return Err("CT endpoint CFL".into());
                }
                let next = average(&self.state, &add(&trial, &r1.state, dt));
                self.recover(&next)?;
                Ok((next, r1.fallbacks))
            });
            match accepted {
                Ok((state, falls)) => {
                    self.state = state;
                    self.time += dt;
                    self.steps += 1;
                    self.hll_fallbacks += r0.fallbacks + falls;
                    return Ok(());
                }
                Err(e) => {
                    last = e;
                    self.rejections += 1;
                    dt *= 0.5;
                }
            }
            if self.time + dt == self.time {
                break;
            }
        }
        Err(format!(
            "CT retries exhausted at t={:.17e}: {last}",
            self.time
        ))
    }

    fn paired_rates(
        &self,
        state: &State,
        attempted: &mut usize,
        failures: &mut usize,
    ) -> Result<(Rate, Option<Rate>), String> {
        let low = self.rate_with_scheme(state, &mut 0, RateScheme::CellRusanov)?;
        let high = match self.rate(state, attempted) {
            Ok(r) => Some(r),
            Err(_) => {
                *failures += 1;
                None
            }
        };
        Ok((low, high))
    }
    fn limited_euler(
        &self,
        state: &State,
        rates: &(Rate, Option<Rate>),
        dt: f64,
        low_failures: &mut usize,
    ) -> Result<(State, f64), String> {
        let low = add(state, &rates.0.state, dt);
        let low_q = match self.recover(&low) {
            Ok(q) => q,
            Err(e) => {
                *low_failures += 1;
                return Err(format!("CT low-order Euler inadmissible: {e}"));
            }
        };
        let Some(high) = &rates.1 else {
            return Ok((low, 0.));
        };
        let high = add(state, &high.state, dt);
        self.limit_states(low, &low_q, high)
    }
    fn limit_states(
        &self,
        low: State,
        low_q: &[Primitive],
        high: State,
    ) -> Result<(State, f64), String> {
        let bxy = self.geometry.field(&high.flux);
        let high_b: Vec<[f64; 3]> = bxy
            .iter()
            .enumerate()
            .map(|(i, b)| [b[0], b[1], high.bz_integral[i] / self.mesh.cells[i].volume])
            .collect();
        let passes = |theta: f64| {
            self.mesh.cells.iter().enumerate().all(|(i, c)| {
                let q = std::array::from_fn(|k| {
                    (low.fluid[i][k] + theta * (high.fluid[i][k] - low.fluid[i][k])) / c.volume
                });
                let b = std::array::from_fn(|k| {
                    low_q[i].magnetic[k] + theta * (high_b[i][k] - low_q[i].magnetic[k])
                });
                self.eos.recover(q, b).is_ok_and(|p| {
                    p.density >= 1e-10 * low_q[i].density && p.pressure >= 1e-10 * low_q[i].pressure
                })
            })
        };
        if passes(1.) && self.recover(&high).is_ok() {
            return Ok((high, 1.));
        }
        let (mut left, mut right) = (0., 1.);
        for _ in 0..52 {
            let middle = 0.5 * (left + right);
            if passes(middle) {
                left = middle;
            } else {
                right = middle;
            }
        }
        // Stay just inside the computed boundary, then check the *actual*
        // face-flux recovery. There is no energy or pressure reassignment.
        let theta = left * (1. - 1e-12);
        let state = blend(&low, &high, theta);
        let q = self.recover(&state)?;
        if q.iter()
            .zip(low_q)
            .any(|(p, l)| p.density < 1e-10 * l.density || p.pressure < 1e-10 * l.pressure)
        {
            return Err("CT convex blend lost admissibility to roundoff".into());
        }
        Ok((state, theta))
    }
    fn step_admissible(&mut self, target: f64) -> Result<(), String> {
        let mut attempted = 0;
        let mut high_failures = 0;
        let first = self.paired_rates(&self.state, &mut attempted, &mut high_failures);
        self.hll_fallbacks_attempted += attempted;
        self.high_order_rate_failures += high_failures;
        let first = first?;
        let bound = |pair: &(Rate, Option<Rate>)| {
            pair.1.as_ref().map_or(pair.0.dt, |h| h.dt.min(pair.0.dt))
        };
        let mut dt = bound(&first).min(target - self.time);
        let mut last = String::new();
        for _ in 0..16 {
            let mut low_failures = 0;
            let mut attempted = 0;
            let mut high_failures = 0;
            let trial = (|| {
                let (stage, theta0) =
                    self.limited_euler(&self.state, &first, dt, &mut low_failures)?;
                let second = self.paired_rates(&stage, &mut attempted, &mut high_failures)?;
                if dt > bound(&second) * (1. + 1e-12) {
                    return Err("CT limited endpoint CFL".into());
                }
                let (euler, theta1) = self.limited_euler(&stage, &second, dt, &mut low_failures)?;
                let next = average(&self.state, &euler);
                self.recover(&next)?;
                let mut used = 0;
                for (theta, pair) in [(theta0, &first), (theta1, &second)] {
                    if theta > 0. {
                        used += pair.1.as_ref().map_or(0, |r| r.fallbacks);
                    }
                }
                Ok((next, [theta0, theta1], used))
            })();
            self.hll_fallbacks_attempted += attempted;
            self.high_order_rate_failures += high_failures;
            self.low_order_rejections += low_failures;
            match trial {
                Ok((next, thetas, used)) => {
                    self.state = next;
                    self.time += dt;
                    self.steps += 1;
                    self.hll_fallbacks += used;
                    for theta in thetas {
                        self.minimum_theta = self.minimum_theta.min(theta);
                        self.limited_stages += usize::from(theta < 1.);
                    }
                    return Ok(());
                }
                Err(e) => {
                    last = e;
                    self.rejections += 1;
                    dt *= 0.5;
                }
            }
            if self.time + dt == self.time {
                break;
            }
        }
        Err(format!(
            "CT admissibility retries exhausted at t={:.17e}: {last}",
            self.time
        ))
    }
    pub fn advance_to(&mut self, target: f64) -> Result<(), String> {
        if !target.is_finite() || target < self.time {
            return Err("invalid CT target".into());
        }
        while self.time < target {
            self.step(target)?;
        }
        Ok(())
    }
    /// Frozen fixed/rigid geometry rates: dE, dK, dM, dp, all per volume.
    pub fn energy_rates(&self) -> Result<Vec<[f64; 4]>, String> {
        self.energy_rates_with_scheme(RateScheme::ReconstructedHlld)
    }
    /// Frozen diagnostic; does not mutate state or solver selection.
    pub fn energy_rates_with_scheme(&self, scheme: RateScheme) -> Result<Vec<[f64; 4]>, String> {
        let q = self.recover(&self.state)?;
        let rate = self.rate_with_scheme(&self.state, &mut 0, scheme)?;
        let db = self.geometry.field(&rate.state.flux);
        Ok(q.iter()
            .enumerate()
            .map(|(i, q)| {
                let v = self.mesh.cells[i].volume;
                let du = rate.state.fluid[i].map(|x| x / v);
                let dk = (0..3)
                    .map(|k| q.velocity[k] * du[k + 1] - 0.5 * q.velocity[k].powi(2) * du[0])
                    .sum::<f64>();
                let dm = q.magnetic[0] * db[i][0]
                    + q.magnetic[1] * db[i][1]
                    + q.magnetic[2] * rate.state.bz_integral[i] / v;
                [du[4], dk, dm, (self.eos.gamma() - 1.) * (du[4] - dk - dm)]
            })
            .collect())
    }
    /// Trial Euler diagnostic at a fraction of this scheme's CFL bound.
    /// Returns (dt, recovered trial primitives) without updating the simulation.
    pub fn euler_probe(
        &self,
        scheme: RateScheme,
        fraction: f64,
    ) -> Result<(f64, Vec<Primitive>), String> {
        if !fraction.is_finite() || fraction <= 0. || fraction > 1. {
            return Err("invalid CT probe fraction".into());
        }
        let r = self.rate_with_scheme(&self.state, &mut 0, scheme)?;
        let dt = fraction * r.dt;
        Ok((dt, self.recover(&add(&self.state, &r.state, dt))?))
    }
    pub fn diagnostics(&self) -> Result<Diagnostics, String> {
        let q = self.recover(&self.state)?;
        let bx: Vec<_> = q.iter().map(|p| p.magnetic[0]).collect();
        let by: Vec<_> = q.iter().map(|p| p.magnetic[1]).collect();
        let gx = self.stencil.gradient(&bx)?;
        let gy = self.stencil.gradient(&by)?;
        let ct = self.geometry.divergence(&self.mesh, &self.state.flux);
        let volume: f64 = self.mesh.cells.iter().map(|c| c.volume).sum();
        let rms = |a: &[f64]| {
            (a.iter()
                .zip(&self.mesh.cells)
                .map(|(x, c)| x * x * c.volume)
                .sum::<f64>()
                / volume)
                .sqrt()
        };
        let ls: Vec<_> = gx.iter().zip(&gy).map(|(x, y)| x[0] + y[1]).collect();
        let mut face = vec![0.; q.len()];
        for f in &self.mesh.faces {
            let flux = f.area
                * (0.5 * (bx[f.left] + bx[f.right]) * f.normal[0]
                    + 0.5 * (by[f.left] + by[f.right]) * f.normal[1]);
            face[f.left] += flux;
            face[f.right] -= flux;
        }
        for (x, c) in face.iter_mut().zip(&self.mesh.cells) {
            *x /= c.volume;
        }
        let budget_max = (0..5)
            .map(|k| {
                ((self.state.fluid.iter().map(|q| q[k]).sum::<f64>() - self.initial_totals[k])
                    / self.budget_scale[k])
                    .abs()
            })
            .fold(0., f64::max);
        Ok(Diagnostics {
            min_density: q.iter().map(|p| p.density).fold(f64::INFINITY, f64::min),
            min_pressure: q.iter().map(|p| p.pressure).fold(f64::INFINITY, f64::min),
            magnetic_energy: q
                .iter()
                .zip(&self.mesh.cells)
                .map(|(p, c)| 0.5 * mhd_core::dot(p.magnetic, p.magnetic) * c.volume)
                .sum(),
            budget_max,
            div_ct_max: ct.iter().map(|x| x.abs()).fold(0., f64::max),
            div_ct_rms: rms(&ct),
            div_ls_rms: rms(&ls),
            div_face_rms: rms(&face),
        })
    }
}
fn add(a: &State, b: &State, dt: f64) -> State {
    State {
        fluid: a
            .fluid
            .iter()
            .zip(&b.fluid)
            .map(|(a, b)| std::array::from_fn(|k| a[k] + dt * b[k]))
            .collect(),
        flux: a
            .flux
            .iter()
            .zip(&b.flux)
            .map(|(a, b)| a + dt * b)
            .collect(),
        bz_integral: a
            .bz_integral
            .iter()
            .zip(&b.bz_integral)
            .map(|(a, b)| a + dt * b)
            .collect(),
    }
}
fn average(a: &State, b: &State) -> State {
    let mut out = add(a, b, 1.);
    for q in &mut out.fluid {
        *q = q.map(|x| 0.5 * x);
    }
    for x in out.flux.iter_mut().chain(&mut out.bz_integral) {
        *x *= 0.5;
    }
    out
}

fn blend(a: &State, b: &State, theta: f64) -> State {
    State {
        fluid: a
            .fluid
            .iter()
            .zip(&b.fluid)
            .map(|(a, b)| std::array::from_fn(|k| a[k] + theta * (b[k] - a[k])))
            .collect(),
        flux: a
            .flux
            .iter()
            .zip(&b.flux)
            .map(|(a, b)| a + theta * (b - a))
            .collect(),
        bz_integral: a
            .bz_integral
            .iter()
            .zip(&b.bz_integral)
            .map(|(a, b)| a + theta * (b - a))
            .collect(),
    }
}

#[cfg(test)]
mod admissibility_tests {
    use super::*;
    #[test]
    fn joint_magnetic_fluid_blend_is_positive_and_preserves_budgets_and_divergence() {
        for jitter in [0., 0.15] {
            let sim = Simulation::new(
                Mesh::lattice(8, 8, [1., 1.], jitter).unwrap(),
                Config {
                    mean_xy: [0.3, 0.2],
                    ..Config::default()
                },
                |_| {
                    (
                        0.,
                        Primitive {
                            density: 1.,
                            pressure: 0.01,
                            velocity: [0.; 3],
                            magnetic: [0.3, 0.2, 0.],
                        },
                    )
                },
            )
            .unwrap();
            let low = sim.state.clone();
            let low_q = sim.recover(&low).unwrap();
            let mut high = low.clone();
            high.flux = sim.geometry.fluxes(
                &sim.mesh,
                |x| (std::f64::consts::TAU * x[0]).sin(),
                [0.3, 0.2],
            );
            assert!(sim.recover(&high).is_err());
            let (limited, theta) = sim.limit_states(low.clone(), &low_q, high).unwrap();
            assert!(theta > 0. && theta < 1.);
            assert!(
                sim.recover(&limited)
                    .unwrap()
                    .iter()
                    .all(|q| q.pressure > 0.)
            );
            assert_eq!(limited.fluid, low.fluid);
            assert!(
                sim.geometry
                    .divergence(&sim.mesh, &limited.flux)
                    .iter()
                    .all(|d| d.abs() < 1e-11)
            );
            let (unchanged, theta) = sim.limit_states(low.clone(), &low_q, low.clone()).unwrap();
            assert_eq!(theta, 1.);
            assert_eq!(unchanged.fluid, low.fluid);
            assert_eq!(unchanged.flux, low.flux);
        }
    }
}
