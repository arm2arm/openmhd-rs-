//! Finite-step periodic M2c reference, with independent analytic cell averages.
//! Arguments: field motion step-count boost-index planes-per-axis [threads].
use mhd_core::{IdealGas, dot};
use mhd_vector_pot::{moving3::*, operators3::independent_divergence};
use moving_mesh::three_d::{
    fit::{FitOrder3, SampleKey3},
    operator_mesh::OperatorMesh3,
    *,
};
use std::f64::consts::{PI, TAU};

const END: f64 = 1. / 32.;
const AMPLITUDE: f64 = 0.05;
#[derive(Clone, Copy, PartialEq)]
enum Field {
    Uniform,
    ForceFree,
    Alfven,
    LowBeta,
}
#[derive(Clone, Copy)]
enum Motion {
    Fixed,
    Comoving,
    Deforming,
}
#[derive(Clone, Copy)]
struct Case {
    field: Field,
    motion: Motion,
    n: usize,
    boost: Vec3,
}
impl Case {
    fn gas_velocity(self) -> Vec3 {
        sum([1., 0.5, -0.25], self.boost)
    }
    fn guide(self) -> f64 {
        if self.field == Field::ForceFree {
            0.
        } else {
            0.5
        }
    }
    fn amplitude(self) -> f64 {
        if self.field == Field::Uniform {
            0.
        } else {
            AMPLITUDE
        }
    }
    fn mean(self) -> Vec3 {
        [self.guide() / 3.0_f64.sqrt(); 3]
    }
    fn pressure(self) -> f64 {
        if self.field == Field::LowBeta {
            0.005 * (self.guide().powi(2) + self.amplitude().powi(2))
        } else {
            1.
        }
    }
    fn plane(self, axis: usize, j: usize) -> (f64, f64) {
        let t = match self.n {
            3 => [0.125, 0.4375, 0.8125][j],
            _ => (j as f64 + 0.5 + [-0.125, 0., 0.125, 0.][(j + axis) % 4]) / self.n as f64,
        };
        let w = match self.motion {
            Motion::Fixed => 0.,
            Motion::Comoving => [1., 0.5, -0.25][axis],
            Motion::Deforming => {
                [-0.125, 0.25, -0.0625][axis] + [-0.5, 0.375, 0.125, 0.][(j + axis) % self.n % 4]
            }
        };
        (t, w + self.boost[axis])
    }
    fn indices(self, id: usize) -> [usize; 3] {
        [id % self.n, (id / self.n) % self.n, id / (self.n * self.n)]
    }
    /// In a product lattice the exact Voronoi interval ends halfway to the adjacent planes.
    fn center_width(self, id: usize, t: f64) -> (Vec3, Vec3) {
        let mut center = [0.; 3];
        let mut width = [0.; 3];
        let idx = self.indices(id);
        for k in 0..3 {
            let j = idx[k];
            let at = |p: usize| {
                let (r, w) = self.plane(k, p);
                r + t * w
            };
            let left = 0.5 * (at(j) + at((j + self.n - 1) % self.n) - f64::from(j == 0));
            let right = 0.5 * (at(j) + at((j + 1) % self.n) + f64::from(j + 1 == self.n));
            center[k] = 0.5 * (left + right);
            width[k] = right - left;
        }
        (center, width)
    }
    fn analytic(self, id: usize, t: f64) -> (CellState3, Vec3, Vec3, Vec3) {
        let (center, width) = self.center_width(id, t);
        let flow = self.gas_velocity();
        let volume = width.iter().product::<f64>();
        let phase = TAU
            * ((0..3).map(|k| center[k] - flow[k] * t).sum::<f64>()
                - 3.0_f64.sqrt() * self.guide() * t);
        let (s, c) = phase.sin_cos();
        let e = [1. / 2.0_f64.sqrt(), -1. / 2.0_f64.sqrt(), 0.];
        let f = [
            1. / 6.0_f64.sqrt(),
            1. / 6.0_f64.sqrt(),
            -2. / 6.0_f64.sqrt(),
        ];
        let b: Vec3 = std::array::from_fn(|k| self.amplitude() * (c * e[k] + s * f[k]));
        let form = width
            .iter()
            .map(|h| (PI * h).sin() / (PI * h))
            .product::<f64>();
        let bbar = b.map(|x| form * x);
        let v_wave = matches!(self.field, Field::Alfven | Field::LowBeta);
        let mean_v = if v_wave {
            std::array::from_fn(|k| flow[k] - bbar[k])
        } else {
            flow
        };
        let kinetic = 0.5 * dot(flow, flow)
            + if v_wave {
                0.5 * self.amplitude().powi(2) - dot(flow, bbar)
            } else {
                0.
            };
        let energy = 1.5 * self.pressure()
            + kinetic
            + 0.5 * (self.guide().powi(2) + self.amplitude().powi(2));
        let state = CellState3 {
            conserved: [1., mean_v[0], mean_v[1], mean_v[2], energy].map(|x| x * volume),
            potential: b.map(|v| -v / (TAU * 3.0_f64.sqrt())),
            phi: 0.,
        };
        (state, sum(self.mean(), bbar), center, width)
    }
}
fn sum(a: Vec3, b: Vec3) -> Vec3 {
    std::array::from_fn(|k| a[k] + b[k])
}
fn row(label: &str, values: impl IntoIterator<Item = f64>) {
    print!("{label}");
    for v in values {
        print!(" {v:.17e}");
    }
    println!();
}
fn snapshot(label: &str, sim: &PeriodicMhd3, case: Case) -> Result<()> {
    let g = sim.geometry();
    let mesh = OperatorMesh3::from_validated(g)?;
    let linear = (0..g.cells().len())
        .map(|i| mesh.fit(i, FitOrder3::Linear))
        .collect::<std::result::Result<Vec<_>, _>>()?;
    let d = independent_divergence(&mesh, sim.field(), &linear)?;
    for (i, c) in g.cells().iter().enumerate() {
        let id = c.generator.id.entity().counter() as usize;
        let s = sim.cells()[i];
        let (ref_q, ref_b, ref_c, width) = case.analytic(id, sim.time());
        let center: Vec3 = std::array::from_fn(|k| {
            c.generator.position[k] + c.centroid_offset[k] + (c.generator.winding.0[k] as f64)
        });
        row(
            label,
            [id as f64, c.volume]
                .into_iter()
                .chain(center)
                .chain(s.conserved)
                .chain(s.potential)
                .chain([s.phi])
                .chain(sim.field()[i])
                .chain([sim.primitives()[i].density, sim.primitives()[i].pressure])
                .chain(ref_q.conserved)
                .chain(ref_b)
                .chain(ref_c)
                .chain(width)
                .chain([d.cell_ls[i], d.face_mean[i], d.face_limited[i]]),
        );
    }
    Ok(())
}
fn run(case: Case, steps: usize) -> Result<()> {
    if !(1..=8192).contains(&steps) || !(3..=8).contains(&case.n) {
        return Err("expected 1..8192 steps and 3..8 planes".into());
    }
    let mut sites = Vec::new();
    let mut motion = std::collections::BTreeMap::new();
    for j in 0..case.n.pow(3) {
        let id = SampleKey3::from_words(0x4d3243, j as u64, Image3::ZERO).owner;
        let idx = case.indices(j);
        let planes: [_; 3] = std::array::from_fn(|k| case.plane(k, idx[k]));
        sites.push(Generator3 {
            id,
            position: planes.map(|(x, _)| x),
            winding: Image3::ZERO,
        });
        motion.insert(id, planes.map(|(_, v)| v));
    }
    let model = Model3 {
        eos: IdealGas::new(5. / 3.)?,
        mean_field: case.mean(),
        reference_velocity: case.gas_velocity(),
        field_scale: case.guide() + AMPLITUDE,
    };
    let mut sim = PeriodicMhd3::new(
        Domain3 {
            anchor: [0.; 3],
            width: [1.; 3],
            boundary: Boundary3::Periodic,
        },
        &sites,
        motion,
        model,
        |c| {
            Ok(case
                .analytic(c.generator.id.entity().counter() as usize, 0.)
                .0)
        },
    )?;
    snapshot("INITIAL", &sim, case)?;
    let dt = END / steps as f64;
    for j in 0..steps {
        let limit = sim.timestep_limit();
        let step = sim.step(dt)?;
        for (stage, report) in [step.predictor, step.corrector].into_iter().enumerate() {
            let signed: Vec3 =
                std::array::from_fn(|k| report.magnetic_transfers.iter().map(|v| v[k]).sum());
            let absolute: Vec3 =
                std::array::from_fn(|k| report.magnetic_transfers.iter().map(|v| v[k].abs()).sum());
            row(
                "STAGE",
                [
                    j as f64,
                    stage as f64,
                    sim.time(),
                    limit,
                    report.max_gcl_residual,
                    report.solve.iterations as f64,
                    report.solve.rhs_norm,
                    report.solve.true_residual,
                    report.min_density,
                    report.min_pressure,
                    report.auxiliary_intervals as f64,
                ]
                .into_iter()
                .chain(report.mean_field)
                .chain(signed)
                .chain(absolute),
            );
            if j + 1 == steps {
                for (i, (transfers, target)) in report
                    .magnetic_transfers
                    .iter()
                    .zip(&report.target_field)
                    .enumerate()
                {
                    row(
                        "CELL_LEDGER",
                        [stage as f64, i as f64]
                            .into_iter()
                            .chain(*transfers)
                            .chain(*target),
                    );
                }
            }
        }
    }
    snapshot("FINAL", &sim, case)?;
    row(
        "GAUGE",
        sim.gauge_offset()
            .into_iter()
            .chain(sim.origin().position)
            .chain(sim.origin().winding.0.map(|v| v as f64)),
    );
    Ok(())
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if !(5..=6).contains(&args.len()) {
        return Err("usage: m2c-smooth-step uniform|advection|alfven|low-beta fixed|comoving|deforming STEPS BOOST(0,1,2) N [THREADS]".into());
    }
    let field = match args[0].as_str() {
        "uniform" => Field::Uniform,
        "advection" => Field::ForceFree,
        "alfven" => Field::Alfven,
        "low-beta" => Field::LowBeta,
        _ => return Err("unknown field".into()),
    };
    let motion = match args[1].as_str() {
        "fixed" => Motion::Fixed,
        "comoving" => Motion::Comoving,
        "deforming" => Motion::Deforming,
        _ => return Err("unknown motion".into()),
    };
    let boost = match args[3].as_str() {
        "0" => [0.; 3],
        "1" => [2., -1., 0.5],
        "2" => [10., 7., -3.],
        _ => return Err("unknown boost".into()),
    };
    let steps = args[2].parse()?;
    let n = args[4].parse()?;
    let threads = args.get(5).map(|s| s.parse()).transpose()?.unwrap_or(1);
    moving_mesh::parallel::with_threads(threads, || {
        run(
            Case {
                field,
                motion,
                n,
                boost,
            },
            steps,
        )
    })??;
    Ok(())
}
