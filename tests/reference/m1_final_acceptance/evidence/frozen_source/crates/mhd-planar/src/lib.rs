//! Experimental serial, strictly planar MHD with cell-centred Az and gas feedback.
//! The mesh may translate rigidly; deformation and the general 3D gauge are deferred.

use mhd_core::{Conservative, FluxMethod, IdealGas, Primitive, cross, riemann};
use moving_mesh::{Derivatives, Mesh, Vec2, dot};
use std::f64::consts::PI;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Case {
    OrszagTang,
    BrioWu,
    Uniform,
    Smooth,
    MagneticPressure,
}

impl Case {
    pub fn name(self) -> &'static str {
        match self {
            Self::OrszagTang => "orszag-tang",
            Self::BrioWu => "brio-wu",
            Self::Uniform => "uniform",
            Self::Smooth => "smooth",
            Self::MagneticPressure => "magnetic-pressure",
        }
    }
    pub fn lengths(self) -> Vec2 {
        if self == Self::BrioWu {
            [2.0, 0.125]
        } else {
            [1.0, 1.0]
        }
    }
    pub fn gamma(self) -> f64 {
        if self == Self::BrioWu { 2.0 } else { 5.0 / 3.0 }
    }
    pub fn mean_field(self) -> Vec2 {
        match self {
            Self::BrioWu => [0.75, 0.0],
            Self::Uniform | Self::Smooth => [0.3, 0.2],
            Self::OrszagTang | Self::MagneticPressure => [0.0, 0.0],
        }
    }
    fn initial(self, [x, y]: Vec2) -> (f64, Primitive) {
        let magnetic = [self.mean_field()[0], self.mean_field()[1], 0.0];
        match self {
            Self::MagneticPressure => (
                0.02 * (2.0 * PI * x).cos(),
                Primitive {
                    density: 1.0,
                    pressure: 1.0,
                    velocity: [0.0; 3],
                    magnetic,
                },
            ),
            Self::OrszagTang => {
                let scale = (4.0 * PI).sqrt();
                let az =
                    ((2.0 * PI * y).cos() / (2.0 * PI) + (4.0 * PI * x).cos() / (4.0 * PI)) / scale;
                (
                    az,
                    Primitive {
                        density: 25.0 / (36.0 * PI),
                        pressure: 5.0 / (12.0 * PI),
                        velocity: [-(2.0 * PI * y).sin(), (2.0 * PI * x).sin(), 0.0],
                        magnetic,
                    },
                )
            }
            Self::BrioWu => {
                // Two interfaces, one box-length apart; analyse only the central tube.
                let az = if x < 1.0 { -x } else { x - 2.0 };
                let (density, pressure) = if x < 1.0 { (1.0, 1.0) } else { (0.125, 0.1) };
                (
                    az,
                    Primitive {
                        density,
                        pressure,
                        velocity: [0.0; 3],
                        magnetic,
                    },
                )
            }
            Self::Uniform | Self::Smooth => {
                let density = if self == Self::Smooth {
                    1.0 + 0.1 * (2.0 * PI * x).sin()
                } else {
                    1.0
                };
                (
                    0.0,
                    Primitive {
                        density,
                        pressure: 1.0,
                        velocity: [0.4, -0.2, 0.0],
                        magnetic,
                    },
                )
            }
        }
    }
}

#[derive(Clone, Debug)]
pub struct Config {
    pub case: Case,
    pub nx: usize,
    pub ny: usize,
    pub jitter: f64,
    pub cfl: f64,
    pub boost: Vec2,
    pub mesh_velocity: Vec2,
    pub second_order_space: bool,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            case: Case::OrszagTang,
            nx: 24,
            ny: 24,
            jitter: 0.0,
            cfl: 0.3,
            boost: [0.0; 2],
            mesh_velocity: [0.0; 2],
            second_order_space: true,
        }
    }
}

#[derive(Clone, Debug)]
pub struct Simulation {
    pub config: Config,
    pub mesh: Mesh,
    pub eos: IdealGas,
    pub az: Vec<f64>,
    /// Cell integrals, not densities. They alone determine the conservation ledger.
    pub conserved: Vec<Conservative>,
    pub time: f64,
    pub steps: usize,
    pub rejected_steps: usize,
    pub cfl_rejections: usize,
    pub invalid_rejections: usize,
    pub hll_fallbacks: usize,
    neighbours: Derivatives,
    face_derivatives: Derivatives,
    initial_totals: Conservative,
}

struct Rate {
    q: Vec<Conservative>,
    a: Vec<f64>,
    dt_bound: f64,
    fallbacks: usize,
}

#[derive(Clone, Debug)]
pub struct Diagnostics {
    pub totals: Conservative,
    pub relative_budget_error: f64,
    pub min_density: f64,
    pub min_pressure: f64,
    pub magnetic_energy: f64,
    pub mean_b: Vec2,
    pub div_limited_rms: f64,
    pub div_ls_rms: f64,
    pub div_face_rms: f64,
    pub div_face_max: f64,
    pub smooth_l1: f64,
}

fn components(q: Primitive) -> [f64; 7] {
    [
        q.density,
        q.velocity[0],
        q.velocity[1],
        q.velocity[2],
        q.pressure,
        q.magnetic[0],
        q.magnetic[1],
    ]
}
fn primitive(q: [f64; 7]) -> Primitive {
    Primitive {
        density: q[0],
        velocity: [q[1], q[2], q[3]],
        pressure: q[4],
        magnetic: [q[5], q[6], 0.0],
    }
}

impl Simulation {
    pub fn new(config: Config) -> Result<Self, String> {
        if !config.cfl.is_finite()
            || config.cfl <= 0.0
            || config.cfl > 0.4
            || !config
                .boost
                .iter()
                .chain(config.mesh_velocity.iter())
                .all(|x| x.is_finite())
        {
            return Err("CFL must be in (0,0.4], velocities finite".into());
        }
        let mesh = Mesh::lattice(config.nx, config.ny, config.case.lengths(), config.jitter)?;
        let neighbours = Derivatives::build(&mesh, false)?;
        let face_derivatives = Derivatives::build(&mesh, true)?;
        let eos = IdealGas::new(config.case.gamma())?;
        let initial: Vec<_> = mesh
            .cells
            .iter()
            .map(|c| {
                let x = std::array::from_fn(|k| c.centroid[k].rem_euclid(mesh.lengths[k]));
                config.case.initial(x)
            })
            .collect();
        let az: Vec<_> = initial.iter().map(|(a, _)| *a).collect();
        let gradient = neighbours.gradient(&az)?;
        let mean = config.case.mean_field();
        let mut conserved = Vec::with_capacity(mesh.cells.len());
        for (i, (_, q)) in initial.iter().enumerate() {
            let mut q = *q;
            q.magnetic = [mean[0] + gradient[i][1], mean[1] - gradient[i][0], 0.0];
            for k in 0..2 {
                q.velocity[k] += config.boost[k];
            }
            conserved.push(eos.conservative(q)?.map(|x| x * mesh.cells[i].volume));
        }
        let initial_totals = std::array::from_fn(|k| conserved.iter().map(|q| q[k]).sum());
        Ok(Self {
            config,
            mesh,
            eos,
            az,
            conserved,
            time: 0.0,
            steps: 0,
            rejected_steps: 0,
            cfl_rejections: 0,
            invalid_rejections: 0,
            hll_fallbacks: 0,
            neighbours,
            face_derivatives,
            initial_totals,
        })
    }

    pub fn primitives(&self) -> Result<Vec<Primitive>, String> {
        self.recover(&self.conserved, &self.az)
    }

    fn recover(&self, conserved: &[Conservative], az: &[f64]) -> Result<Vec<Primitive>, String> {
        let g = self.neighbours.gradient(az)?;
        let mean = self.config.case.mean_field();
        conserved
            .iter()
            .enumerate()
            .map(|(i, q)| {
                self.eos
                    .recover(
                        q.map(|x| x / self.mesh.cells[i].volume),
                        [mean[0] + g[i][1], mean[1] - g[i][0], 0.0],
                    )
                    .map_err(|e| format!("cell {i}: {e}"))
            })
            .collect()
    }

    fn rate(&self, conserved: &[Conservative], az: &[f64]) -> Result<Rate, String> {
        let q = self.recover(conserved, az)?;
        let arrays: Vec<_> = q.iter().map(|q| components(*q)).collect();
        let gradients: Vec<Vec<Vec2>> = (0..7)
            .map(|k| {
                let values: Vec<_> = arrays.iter().map(|q| q[k]).collect();
                if self.config.second_order_space {
                    self.mesh
                        .limit_gradients(&values, &self.neighbours.gradient(&values)?)
                } else {
                    Ok(vec![[0.0; 2]; q.len()])
                }
            })
            .collect::<Result<_, String>>()?;
        let a_gradient = self
            .mesh
            .limit_gradients(az, &self.neighbours.gradient(az)?)?;
        let w = [
            self.config.mesh_velocity[0],
            self.config.mesh_velocity[1],
            0.0,
        ];
        let mean = self.config.case.mean_field();
        let mut rate = Rate {
            q: vec![[0.0; 5]; q.len()],
            a: vec![0.0; q.len()],
            dt_bound: f64::INFINITY,
            fallbacks: 0,
        };
        let mut perimeters = vec![0.0; q.len()];
        let mut wave_sums = vec![0.0; q.len()];
        // One Riemann solve and one signed exchange per shared periodic face.
        for face in &self.mesh.faces {
            let dl = self.mesh.displacement(face, face.left);
            let dr = self.mesh.displacement(face, face.right);
            let extrapolate = |i: usize, d: Vec2| {
                primitive(std::array::from_fn(|k| {
                    arrays[i][k] + dot(gradients[k][i], d)
                }))
            };
            let flux = riemann(
                self.eos,
                extrapolate(face.left, dl),
                extrapolate(face.right, dr),
                [face.normal[0], face.normal[1], 0.0],
                w,
            )?;
            if flux.method == FluxMethod::HllFallback {
                rate.fallbacks += 1;
            }
            for (i, sign) in [(face.left, -1.0), (face.right, 1.0)] {
                for k in 0..5 {
                    rate.q[i][k] += sign * face.area * flux.fluid[k];
                }
                // Eq. (69), planar u_i = v_i. Numerical EMF agrees with v* x B*
                // for HLLD; HLL uses its flux-consistent EMF (explicit E choice).
                rate.a[i] +=
                    face.area * (flux.electromotive[2] - cross(q[i].velocity, flux.magnetic)[2]);
                perimeters[i] += face.area;
                wave_sums[i] += face.area * flux.max_speed;
            }
        }
        for i in 0..q.len() {
            rate.a[i] /= perimeters[i];
            rate.a[i] += q[i].velocity[0] * mean[1] - q[i].velocity[1] * mean[0];
            let b = [w[0] - q[i].velocity[0], w[1] - q[i].velocity[1]];
            let mut adv_bound = 0.0;
            for s in &self.face_derivatives.samples[i] {
                let face = &self.mesh.faces[s.index];
                let (j, _) = self.mesh.neighbour(face, i);
                let di = self.mesh.displacement(face, i);
                let dj = self.mesh.displacement(face, j);
                // Eq. (71): transport velocity is -b, hence this donor sign.
                let upwind = if dot(b, di) < 0.0 {
                    az[i] + dot(a_gradient[i], di)
                } else {
                    az[j] + dot(a_gradient[j], dj)
                };
                let coefficient = dot(b, s.weight);
                rate.a[i] += coefficient * (upwind - az[i]);
                adv_bound += coefficient.abs();
            }
            rate.dt_bound = rate
                .dt_bound
                .min(self.config.cfl * self.mesh.cells[i].volume / wave_sums[i]);
            if adv_bound > 0.0 {
                rate.dt_bound = rate.dt_bound.min(self.config.cfl / adv_bound);
            }
        }
        if !rate.a.iter().all(|x| x.is_finite())
            || !rate.dt_bound.is_finite()
            || rate.dt_bound <= 0.0
        {
            return Err("invalid potential rate or timestep bound".into());
        }
        Ok(rate)
    }

    /// Synchronized method-of-lines Heun, re-closing B=curl(A) at each stage.
    /// This is an explicit reference choice, not the paper's endpoint PDE predictor.
    pub fn advance_to(&mut self, target: f64) -> Result<(), String> {
        if !target.is_finite() || target < self.time {
            return Err("invalid target time".into());
        }
        while self.time < target {
            let r0 = self.rate(&self.conserved, &self.az)?;
            let mut dt = r0.dt_bound.min(target - self.time);
            let mut accepted = None;
            let mut last_error = String::new();
            for _ in 0..16 {
                let mut rejected_for_cfl = false;
                let qs: Vec<_> = self
                    .conserved
                    .iter()
                    .zip(&r0.q)
                    .map(|(q, r)| std::array::from_fn(|k| q[k] + dt * r[k]))
                    .collect();
                let astar: Vec<_> = self.az.iter().zip(&r0.a).map(|(a, r)| a + dt * r).collect();
                match self.rate(&qs, &astar) {
                    Ok(r1) if dt <= r1.dt_bound * (1.0 + 1e-12) => {
                        let next_q: Vec<_> = self
                            .conserved
                            .iter()
                            .zip(&r0.q)
                            .zip(&r1.q)
                            .map(|((q, r), s)| {
                                std::array::from_fn(|k| q[k] + 0.5 * dt * (r[k] + s[k]))
                            })
                            .collect();
                        let next_a: Vec<_> = self
                            .az
                            .iter()
                            .zip(&r0.a)
                            .zip(&r1.a)
                            .map(|((a, r), s)| a + 0.5 * dt * (r + s))
                            .collect();
                        match self.recover(&next_q, &next_a) {
                            Ok(_) => {
                                accepted = Some((next_q, next_a, r1.fallbacks));
                                break;
                            }
                            Err(e) => last_error = e,
                        }
                    }
                    Ok(_) => {
                        last_error = "endpoint CFL bound exceeded".into();
                        rejected_for_cfl = true;
                    }
                    Err(e) => last_error = e,
                }
                dt *= 0.5;
                self.rejected_steps += 1;
                if rejected_for_cfl {
                    self.cfl_rejections += 1;
                } else {
                    self.invalid_rejections += 1;
                }
            }
            let (q, a, fallbacks) = accepted
                .ok_or_else(|| format!("step rejected at t={}: {last_error}", self.time))?;
            if self.time + dt == self.time || self.steps >= 1_000_000 {
                return Err("timestep underflow or step limit".into());
            }
            self.conserved = q;
            self.az = a;
            self.time = (self.time + dt).min(target);
            self.steps += 1;
            self.hll_fallbacks += r0.fallbacks + fallbacks;
        }
        Ok(())
    }

    /// Geometry is stored in a translating reference frame; never subtract wrapped
    /// positions to infer a velocity. Rigid translation preserves all mesh metrics.
    pub fn position(&self, i: usize) -> Vec2 {
        std::array::from_fn(|k| {
            (self.mesh.cells[i].centroid[k] + self.config.mesh_velocity[k] * self.time)
                .rem_euclid(self.mesh.lengths[k])
        })
    }

    pub fn diagnostics(&self) -> Result<Diagnostics, String> {
        let q = self.primitives()?;
        let volume = self.mesh.lengths[0] * self.mesh.lengths[1];
        let totals: Conservative =
            std::array::from_fn(|k| self.conserved.iter().map(|q| q[k]).sum());
        let relative_budget_error = (0..5)
            .map(|k| {
                (totals[k] - self.initial_totals[k]).abs()
                    / self.initial_totals[k].abs().max(self.initial_totals[0])
            })
            .fold(0.0, f64::max);
        let bx: Vec<_> = q.iter().map(|q| q.magnetic[0]).collect();
        let by: Vec<_> = q.iter().map(|q| q.magnetic[1]).collect();
        let dx = self.neighbours.gradient(&bx)?;
        let dy = self.neighbours.gradient(&by)?;
        let limited_bx = self.mesh.limit_gradients(&bx, &dx)?;
        let limited_by = self.mesh.limit_gradients(&by, &dy)?;
        // Independent flux diagnostic: arithmetic mean normal B per face.
        let mut div_face = vec![0.0; q.len()];
        let mut div_limited = vec![0.0; q.len()];
        for face in &self.mesh.faces {
            let normal_b = 0.5
                * ((bx[face.left] + bx[face.right]) * face.normal[0]
                    + (by[face.left] + by[face.right]) * face.normal[1]);
            div_face[face.left] += face.area * normal_b / self.mesh.cells[face.left].volume;
            div_face[face.right] -= face.area * normal_b / self.mesh.cells[face.right].volume;
            let dl = self.mesh.displacement(face, face.left);
            let dr = self.mesh.displacement(face, face.right);
            let bn_limited = normal_b
                + 0.5
                    * (face.normal[0]
                        * (dot(limited_bx[face.left], dl) + dot(limited_bx[face.right], dr))
                        + face.normal[1]
                            * (dot(limited_by[face.left], dl) + dot(limited_by[face.right], dr)));
            div_limited[face.left] += face.area * bn_limited / self.mesh.cells[face.left].volume;
            div_limited[face.right] -= face.area * bn_limited / self.mesh.cells[face.right].volume;
        }
        let sum = |values: Vec<f64>| {
            values
                .iter()
                .zip(&self.mesh.cells)
                .map(|(x, c)| x * c.volume)
                .sum::<f64>()
                / volume
        };
        let smooth_l1 = if self.config.case == Case::Smooth {
            sum(q
                .iter()
                .enumerate()
                .map(|(i, q)| {
                    let x = self.position(i)[0] - (0.4 + self.config.boost[0]) * self.time;
                    (q.density - 1.0 - 0.1 * (2.0 * PI * x).sin()).abs()
                })
                .collect())
        } else {
            0.0
        };
        Ok(Diagnostics {
            totals,
            relative_budget_error,
            min_density: q.iter().map(|q| q.density).fold(f64::INFINITY, f64::min),
            min_pressure: q.iter().map(|q| q.pressure).fold(f64::INFINITY, f64::min),
            magnetic_energy: 0.5
                * volume
                * sum(q
                    .iter()
                    .map(|q| q.magnetic[0].powi(2) + q.magnetic[1].powi(2))
                    .collect()),
            mean_b: [sum(bx), sum(by)],
            div_limited_rms: sum(div_limited.iter().map(|d| d * d).collect()).sqrt(),
            div_ls_rms: sum((0..q.len())
                .map(|i| (dx[i][0] + dy[i][1]).powi(2))
                .collect())
            .sqrt(),
            div_face_rms: sum(div_face.iter().map(|d| d * d).collect()).sqrt(),
            div_face_max: div_face.iter().map(|d| d.abs()).fold(0.0, f64::max),
            smooth_l1,
        })
    }
}
