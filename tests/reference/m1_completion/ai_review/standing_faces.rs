//! Independent AI-review diagnostic, not a production solver or scientific acceptance.
//! N64 regular standing wave, gamma=5/3, mean B=(1,0,0), periodic unit square.
//! Uses the public solver primitives, initial cached derivative stencil, limiter,
//! predictor at tau=0 and auxiliary sample at the left incident cell centroid.
//! The fixed common-dt pair is diagnostic; it is not the original CFL trajectory.
//! Optional argv[1] is the original t=.25 base snapshot for exact state comparison.
use mhd_core::{
    FaceCompletion, FaceFlux, IdealGas, Primitive, Vec3, cross, dot, riemann,
    riemann_with_completion,
};
use mhd_vector_pot::auxiliary::{SmoothVelocity, VelocitySample};
use mhd_vector_pot::benchmarks::alfven_initial;
use mhd_vector_pot::general::{Config, Motion, Profile, Simulation};
use mhd_vector_pot::operators::{PrimitiveGradient, predict};
use moving_mesh::{Derivatives, Mesh};
use std::fs;
fn components(q: Primitive) -> [f64; 8] {
    [
        q.density,
        q.velocity[0],
        q.velocity[1],
        q.velocity[2],
        q.pressure,
        q.magnetic[0],
        q.magnetic[1],
        q.magnetic[2],
    ]
}
fn src(f: FaceFlux, u: Vec3) -> Vec3 {
    let x = cross(u, f.magnetic);
    std::array::from_fn(|k| f.electromotive[k] - x[k])
}
fn delta(a: &[f64], b: &[f64]) -> f64 {
    a.iter()
        .zip(b)
        .map(|(a, b)| (a - b).abs())
        .fold(0., f64::max)
}
fn speeds(eos: IdealGas, l: Primitive, r: Primitive, n: Vec3) -> [f64; 5] {
    let bn = 0.5 * (dot(l.magnetic, n) + dot(r.magnetic, n));
    let l = Primitive {
        magnetic: std::array::from_fn(|k| l.magnetic[k] + (bn - dot(l.magnetic, n)) * n[k]),
        ..l
    };
    let r = Primitive {
        magnetic: std::array::from_fn(|k| r.magnetic[k] + (bn - dot(r.magnetic, n)) * n[k]),
        ..r
    };
    let vl = dot(l.velocity, n);
    let vr = dot(r.velocity, n);
    let cf = eos.fast_speed(l, n).max(eos.fast_speed(r, n));
    let sl = vl.min(vr) - cf;
    let sr = vl.max(vr) + cf;
    let pl = l.pressure + 0.5 * dot(l.magnetic, l.magnetic);
    let pr = r.pressure + 0.5 * dot(r.magnetic, r.magnetic);
    let dl = l.density * (sl - vl);
    let dr = r.density * (sr - vr);
    let sm = (dr * vr - dl * vl - pr + pl) / (dr - dl);
    let rl = l.density * (sl - vl) / (sl - sm);
    let rr = r.density * (sr - vr) / (sr - sm);
    [
        sl,
        sm - bn.abs() / rl.sqrt(),
        sm,
        sm + bn.abs() / rr.sqrt(),
        sr,
    ]
}
#[derive(Clone)]
struct Record {
    face: usize,
    left: usize,
    right: usize,
    kind: String,
    score: f64,
    flux: f64,
    b: f64,
    n: Vec3,
    u: Vec3,
    l: Primitive,
    r: Primitive,
    s: Vec3,
    changed: Vec3,
    waves: [f64; 5],
}
fn scan(sim: &Simulation, label: &str) {
    let mesh = &sim.state().mesh;
    let q = sim.primitives().unwrap();
    let eos = IdealGas::new(5. / 3.).unwrap();
    let stencil = Derivatives::build(mesh, false).unwrap();
    let reconstruction = mesh.reconstruction().unwrap();
    let mut g: Vec<PrimitiveGradient> = vec![[[0.; 2]; 8]; q.len()];
    for k in 0..8 {
        let values: Vec<_> = q.iter().map(|q| components(*q)[k]).collect();
        let raw = stencil.gradient(&values).unwrap();
        let grad = reconstruction.limit_gradients(&values, &raw).unwrap();
        for (out, v) in g.iter_mut().zip(grad) {
            out[k] = v;
        }
    }
    let samples: Vec<_> = q
        .iter()
        .zip(&mesh.cells)
        .map(|(q, c)| VelocitySample {
            position: c.centroid,
            volume: c.volume,
            velocity: q.velocity,
        })
        .collect();
    let auxiliary =
        SmoothVelocity::build(mesh.lengths, &samples, sim.state().auxiliary_origin).unwrap();
    let boost = [2., -1., 0.];
    let mut records = Vec::new();
    for (i, f) in mesh.faces.iter().enumerate() {
        let l = predict(eos, q[f.left], g[f.left], mesh.displacement(f, f.left), 0.).unwrap();
        let r = predict(
            eos,
            q[f.right],
            g[f.right],
            mesh.displacement(f, f.right),
            0.,
        )
        .unwrap();
        let n = [f.normal[0], f.normal[1], 0.];
        let old = riemann(eos, l, r, n, [0.; 3]).unwrap();
        let aux = auxiliary
            .sample(mesh.cells[f.left].centroid, 0.)
            .unwrap()
            .velocity;
        let s = src(old, aux);
        let mut candidates = Vec::new();
        let rev = riemann(eos, r, l, n.map(|v| -v), [0.; 3]).unwrap();
        candidates.push(("reversal".to_string(), rev, aux, rev.fluid.map(|v| -v)));
        let shift = |mut q: Primitive| {
            q.velocity = std::array::from_fn(|k| q.velocity[k] + boost[k]);
            q
        };
        let boosted = riemann(eos, shift(l), shift(r), n, boost).unwrap();
        let mut fluid = boosted.fluid;
        for k in 0..3 {
            fluid[k + 1] -= boost[k] * fluid[0];
        }
        fluid[4] = boosted.fluid[4] - (0..3).map(|k| boost[k] * boosted.fluid[k + 1]).sum::<f64>()
            + 0.5 * dot(boost, boost) * fluid[0];
        candidates.push((
            "joint_boost_2_-1_0".to_string(),
            boosted,
            std::array::from_fn(|k| aux[k] + boost[k]),
            fluid,
        ));
        for k in 0..3 {
            for direction in [-1_i64, 1] {
                let mut ll = l;
                let bits = ll.velocity[k].to_bits();
                ll.velocity[k] = f64::from_bits(if direction < 0 {
                    bits.saturating_sub(1)
                } else {
                    bits + 1
                });
                let p = riemann(eos, ll, r, n, [0.; 3]).unwrap();
                candidates.push((format!("left_v{k}_ulp{direction}"), p, aux, p.fluid));
            }
        }
        for (kind, p, u, fluid) in candidates {
            let changed = src(p, u);
            records.push(Record {
                face: i,
                left: f.left,
                right: f.right,
                kind,
                score: delta(&s, &changed),
                flux: delta(&old.fluid, &fluid),
                b: delta(&old.magnetic, &p.magnetic),
                n,
                u: aux,
                l,
                r,
                s,
                changed,
                waves: speeds(eos, l, r, n),
            });
        }
    }
    records.sort_by(|a, b| b.score.total_cmp(&a.score));
    println!(
        "SCAN label={label} time={} steps={} origin={:?} records={}",
        sim.time(),
        sim.counters().steps,
        sim.state().auxiliary_origin,
        records.len()
    );
    for kind in [
        "reversal",
        "joint_boost_2_-1_0",
        "left_v0_ulp-1",
        "left_v0_ulp1",
        "left_v1_ulp-1",
        "left_v1_ulp1",
        "left_v2_ulp-1",
        "left_v2_ulp1",
    ] {
        let r = records.iter().find(|r| r.kind == kind).unwrap();
        println!(
            "KIND {kind} source_max={:.17e} fluid_at_source_max={:.17e} face={}",
            r.score, r.flux, r.face
        );
    }
    for r in records.iter().take(4) {
        println!(
            "face={} left={} right={} kind={} source_max={:.17e} fluid_max={:.17e} Bface_max={:.17e}\n normal={:?} waves_SL_SAL_SM_SAR_SR={:?}\n left_state={:?}\n right_state={:?}\n aux={:?}\n source={:?}\n changed_source={:?}",
            r.face,
            r.left,
            r.right,
            r.kind,
            r.score,
            r.flux,
            r.b,
            r.n,
            r.waves,
            components(r.l),
            components(r.r),
            r.u,
            r.s,
            r.changed
        );
    }
}
fn compare_snapshot(sim: &Simulation, path: &str) {
    let text = fs::read_to_string(path).unwrap();
    let mut lines = text.lines();
    let headers: Vec<_> = lines.next().unwrap().split(',').collect();
    let keys = ["rho", "vx", "vy", "vz", "p", "bx", "by", "bz"];
    let indices = keys.map(|k| headers.iter().position(|h| *h == k).unwrap());
    let q = sim.primitives().unwrap();
    let mut maximum = 0_f64;
    let mut count = 0;
    for (i, line) in lines.enumerate() {
        let row: Vec<f64> = line.split(',').map(|v| v.parse().unwrap()).collect();
        for (k, j) in indices.iter().enumerate() {
            maximum = maximum.max((row[*j] - components(q[i])[k]).abs());
        }
        count += 1;
    }
    println!("REFERENCE path={path} cells={count} primitive_max_diff={maximum:.17e}");
    assert_eq!(count, q.len());
    assert!(maximum <= 1e-14);
}
fn prepared(sim: &Simulation) -> (Vec<Primitive>, Vec<PrimitiveGradient>, SmoothVelocity) {
    let mesh = &sim.state().mesh;
    let q = sim.primitives().unwrap();
    let initial_mesh = Mesh::lattice(64, 64, [1.; 2], 0.).unwrap();
    let stencil = Derivatives::build(&initial_mesh, false).unwrap();
    let reconstruction = mesh.reconstruction().unwrap();
    let mut g = vec![[[0.; 2]; 8]; q.len()];
    for k in 0..8 {
        let values: Vec<_> = q.iter().map(|q| components(*q)[k]).collect();
        let grad = reconstruction
            .limit_gradients(&values, &stencil.gradient(&values).unwrap())
            .unwrap();
        for (out, v) in g.iter_mut().zip(grad) {
            out[k] = v;
        }
    }
    let samples: Vec<_> = q
        .iter()
        .zip(&mesh.cells)
        .map(|(q, c)| VelocitySample {
            position: c.centroid,
            volume: c.volume,
            velocity: q.velocity,
        })
        .collect();
    let aux = SmoothVelocity::build(mesh.lengths, &samples, sim.state().auxiliary_origin).unwrap();
    (q, g, aux)
}
fn actual_pair(base: &Simulation, boosted: &Simulation, label: &str) {
    let boost = [2., -1., 0.];
    let mesh = &base.state().mesh;
    let mb = &boosted.state().mesh;
    let eos = IdealGas::new(5. / 3.).unwrap();
    let (qa, ga, auxa) = prepared(base);
    let (qb, gb, auxb) = prepared(boosted);
    let mut records = Vec::new();
    let mut signals = Vec::new();
    let mut pressure = 0_f64;
    for (a, b) in qa.iter().zip(&qb) {
        pressure = pressure.max((a.pressure - b.pressure).abs());
    }
    for (i, f) in mesh.faces.iter().enumerate() {
        let n = [f.normal[0], f.normal[1], 0.];
        let a = |j| predict(eos, qa[j], ga[j], mesh.displacement(f, j), 0.).unwrap();
        let b = |j| predict(eos, qb[j], gb[j], mb.displacement(&mb.faces[i], j), 0.).unwrap();
        let l = a(f.left);
        let r = a(f.right);
        let lb = b(f.left);
        let rb = b(f.right);
        let ua = auxa
            .sample(mesh.cells[f.left].centroid, 0.)
            .unwrap()
            .velocity;
        let ub = auxb.sample(mb.cells[f.left].centroid, 0.).unwrap().velocity;
        let fa = riemann(eos, l, r, n, [0.; 3]).unwrap();
        let fb = riemann(eos, lb, rb, n, boost).unwrap();
        let mut fluid = fb.fluid;
        for k in 0..3 {
            fluid[k + 1] -= boost[k] * fluid[0];
        }
        fluid[4] = fb.fluid[4] - (0..3).map(|k| boost[k] * fb.fluid[k + 1]).sum::<f64>()
            + 0.5 * dot(boost, boost) * fluid[0];
        let sa = src(fa, ua);
        let sb = src(fb, ub);
        let fsa =
            riemann_with_completion(eos, l, r, n, [0.; 3], FaceCompletion::SignalWeighted).unwrap();
        let fsb =
            riemann_with_completion(eos, lb, rb, n, boost, FaceCompletion::SignalWeighted).unwrap();
        let sig = delta(&src(fsa, ua), &src(fsb, ub));
        signals.push(sig);
        let rest = |mut q: Primitive| {
            q.velocity = std::array::from_fn(|k| q.velocity[k] - boost[k]);
            q
        };
        records.push((
            delta(&sa, &sb),
            i,
            delta(&fa.fluid, &fluid),
            sig,
            components(l),
            components(r),
            components(rest(lb)),
            components(rest(rb)),
            speeds(eos, l, r, n),
            speeds(eos, rest(lb), rest(rb), n),
            sa,
            sb,
            ua,
            ub,
            n,
        ));
    }
    records.sort_by(|a, b| b.0.total_cmp(&a.0));
    println!(
        "ACTUAL_PAIR label={label} time={} pressure_max={pressure:.17e} signal_source_max={:.17e}",
        base.time(),
        signals.into_iter().fold(0., f64::max)
    );
    for r in records.iter().take(4) {
        println!(
            "ACTUAL face={} normal={:?} old_source_max={:.17e} transformed_fluid_max={:.17e} signal_source_diff={:.17e}\n left={:?} right={:?}\n boosted_rest_left={:?} boosted_rest_right={:?}\n old_waves={:?} boosted_rest_waves={:?}\n source={:?} boosted_source={:?}\n aux={:?} boosted_aux={:?}",
            r.1, r.14, r.0, r.2, r.3, r.4, r.5, r.6, r.7, r.8, r.9, r.10, r.11, r.12, r.13
        );
    }
}
fn common_step() {
    let dt = 1e-6;
    let boost = [2., -1., 0.];
    for profile in [Profile::BulkFrameV1, Profile::BulkFrameSignalV1] {
        let mesh = Mesh::lattice(64, 64, [1.; 2], 0.).unwrap();
        let config = Config {
            profile,
            mean_magnetic: [1., 0., 0.],
            motion: Motion::Fixed,
            magnetic_scale: 1.,
            max_dt: dt,
            ..Config::default()
        };
        let mut a = Simulation::new(mesh.clone(), config.clone(), |x| {
            alfven_initial(x, 1., [0.; 3])
        })
        .unwrap();
        let mut b = Simulation::new(
            mesh,
            Config {
                motion: Motion::Rigid([2., -1.]),
                ..config
            },
            |x| alfven_initial(x, 1., boost),
        )
        .unwrap();
        a.advance_to(dt).unwrap();
        b.advance_to(dt).unwrap();
        let qa = a.primitives().unwrap();
        let qb = b.primitives().unwrap();
        let mut l1 = 0.;
        let mut max_b = 0_f64;
        let mut max_a = 0_f64;
        for (i, (qa, qb)) in qa.iter().zip(qb).enumerate() {
            let diff: Vec3 = std::array::from_fn(|k| qa.magnetic[k] - qb.magnetic[k]);
            l1 += a.state().mesh.cells[i].volume * diff[0].hypot(diff[1]).hypot(diff[2]);
            max_b = max_b.max(delta(&qa.magnetic, &qb.magnetic));
            max_a = max_a.max(delta(&a.state().potential[i], &b.state().potential[i]));
        }
        println!(
            "COMMON_DT profile={} dt={dt:.17e} steps={}/{} B_vector_L1={l1:.17e} B_component_max={max_b:.17e} reduced_A_max={max_a:.17e}",
            profile.name(),
            a.counters().steps,
            b.counters().steps
        );
    }
}
fn common_trajectory() {
    let dt = 1e-4;
    let boost = [2., -1., 0.];
    let mesh = Mesh::lattice(64, 64, [1.; 2], 0.).unwrap();
    let config = Config {
        profile: Profile::BulkFrameV1,
        mean_magnetic: [1., 0., 0.],
        motion: Motion::Fixed,
        magnetic_scale: 1.,
        max_dt: dt,
        ..Config::default()
    };
    let mut a = Simulation::new(mesh.clone(), config.clone(), |x| {
        alfven_initial(x, 1., [0.; 3])
    })
    .unwrap();
    let mut b = Simulation::new(
        mesh,
        Config {
            motion: Motion::Rigid([2., -1.]),
            ..config
        },
        |x| alfven_initial(x, 1., boost),
    )
    .unwrap();
    for j in 1..=200 {
        let previous_a = a.clone();
        let previous_b = b.clone();
        a.advance_to(j as f64 * dt).unwrap();
        b.advance_to(j as f64 * dt).unwrap();
        let qa = a.primitives().unwrap();
        let qb = b.primitives().unwrap();
        let maximum = qa
            .iter()
            .zip(qb)
            .map(|(a, b)| delta(&a.magnetic, &b.magnetic))
            .fold(0., f64::max);
        if j <= 2 || j % 20 == 0 || maximum > 1e-11 {
            println!(
                "TRAJECTORY common_dt={dt:.17e} step={j} time={:.17e} accepted_steps={}/{} B_component_max={maximum:.17e}",
                a.time(),
                a.counters().steps,
                b.counters().steps
            );
        }
        if maximum > 1e-11 {
            actual_pair(&previous_a, &previous_b, "common_dt_before_threshold");
            actual_pair(&a, &b, "common_dt_after_threshold");
            return;
        }
    }
    println!(
        "TRAJECTORY no B-component difference above 1e-11 through t=.02; first nonlinear branch unisolated"
    );
}

fn signal_control() {
    let dt = 1e-4;
    let mesh = Mesh::lattice(64, 64, [1.; 2], 0.).unwrap();
    let config = Config {
        profile: Profile::BulkFrameSignalV1,
        mean_magnetic: [1., 0., 0.],
        motion: Motion::Fixed,
        magnetic_scale: 1.,
        max_dt: dt,
        ..Config::default()
    };
    let mut a = Simulation::new(mesh.clone(), config.clone(), |x| {
        alfven_initial(x, 1., [0.; 3])
    })
    .unwrap();
    let mut b = Simulation::new(
        mesh,
        Config {
            motion: Motion::Rigid([2., -1.]),
            ..config
        },
        |x| alfven_initial(x, 1., [2., -1., 0.]),
    )
    .unwrap();
    for j in 1..=2 {
        a.advance_to(j as f64 * dt).unwrap();
        b.advance_to(j as f64 * dt).unwrap();
        let qa = a.primitives().unwrap();
        let qb = b.primitives().unwrap();
        let maximum = qa
            .iter()
            .zip(qb)
            .map(|(a, b)| delta(&a.magnetic, &b.magnetic))
            .fold(0., f64::max);
        println!(
            "SIGNAL_CONTROL common_dt={dt:.17e} step={j} time={:.17e} accepted_steps={}/{} B_component_max={maximum:.17e}",
            a.time(),
            a.counters().steps,
            b.counters().steps
        );
    }
}
fn actual_initial_ulp() {
    let eos = IdealGas::new(5. / 3.).unwrap();
    let n = [1., 0., 0.];
    let u = [1., 0.0028998268722361478, -0.08989463303932034];
    let l = Primitive {
        density: 1.,
        velocity: [1., 1.181371317230881e-5, -0.09987954562051725],
        pressure: 0.09999999999999995,
        magnetic: [1., 1.1794744992119077e-5, -0.09971917832646955],
    };
    let r = Primitive {
        velocity: [1., -1.1813713172283656e-5, -0.09987954562051725],
        magnetic: [1., -1.1794744992119077e-5, -0.09971917832646955],
        ..l
    };
    let mut perturbed = l;
    perturbed.velocity[0] = f64::from_bits(1_f64.to_bits() - 1);
    for completion in [FaceCompletion::Intermediate, FaceCompletion::SignalWeighted] {
        let a = riemann_with_completion(eos, l, r, n, [0.; 3], completion).unwrap();
        let b = riemann_with_completion(eos, perturbed, r, n, [0.; 3], completion).unwrap();
        println!(
            "INITIAL_FACE94_FIXTURE completion={completion:?} source_max={:.17e} fluid_max={:.17e} Bface_max={:.17e}",
            delta(&src(a, u), &src(b, u)),
            delta(&a.fluid, &b.fluid),
            delta(&a.magnetic, &b.magnetic)
        );
    }
}
fn main() {
    let mut sim = Simulation::new(
        Mesh::lattice(64, 64, [1.; 2], 0.).unwrap(),
        Config {
            profile: Profile::BulkFrameV1,
            mean_magnetic: [1., 0., 0.],
            motion: Motion::Fixed,
            magnetic_scale: 1.,
            ..Config::default()
        },
        |x| alfven_initial(x, 1., [0.; 3]),
    )
    .unwrap();
    scan(&sim, "initial");
    let boosted = Simulation::new(
        sim.state().mesh.clone(),
        Config {
            profile: Profile::BulkFrameV1,
            mean_magnetic: [1., 0., 0.],
            motion: Motion::Rigid([2., -1.]),
            magnetic_scale: 1.,
            ..Config::default()
        },
        |x| alfven_initial(x, 1., [2., -1., 0.]),
    )
    .unwrap();
    actual_pair(&sim, &boosted, "initial");
    common_step();
    common_trajectory();
    signal_control();
    actual_initial_ulp();
    sim.advance_to(0.25).unwrap();
    if let Some(path) = std::env::args().nth(1) {
        compare_snapshot(&sim, &path);
    } else {
        println!("REFERENCE omitted; supply original base t=.25 CSV as argv[1]");
    }
    scan(&sim, "quarter");
}
