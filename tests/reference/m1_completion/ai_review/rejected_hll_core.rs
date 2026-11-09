//! Independent ideal-MHD kernels in Lorentz-Heaviside units (mu_0 = 1).
//! See docs/COUPLED_2D.md for equations, fallback policy and limitations.

pub type Vec3 = [f64; 3];
/// Density, three momentum densities and total energy density. B is supplied separately.
pub type Conservative = [f64; 5];

#[derive(Clone, Copy, Debug)]
pub struct Primitive {
    pub density: f64,
    pub velocity: Vec3,
    pub pressure: f64,
    pub magnetic: Vec3,
}

#[derive(Clone, Copy, Debug)]
pub struct IdealGas {
    gamma: f64,
}

impl IdealGas {
    pub fn new(gamma: f64) -> Result<Self, String> {
        if !gamma.is_finite() || gamma <= 1.0 {
            return Err("gamma must be finite and greater than one".into());
        }
        Ok(Self { gamma })
    }

    pub fn gamma(self) -> f64 {
        self.gamma
    }

    pub fn conservative(self, q: Primitive) -> Result<Conservative, String> {
        q.validate()?;
        let energy = q.pressure / (self.gamma - 1.0)
            + 0.5 * (q.density * dot(q.velocity, q.velocity) + dot(q.magnetic, q.magnetic));
        let u = [
            q.density,
            q.density * q.velocity[0],
            q.density * q.velocity[1],
            q.density * q.velocity[2],
            energy,
        ];
        if !u.iter().all(|x| x.is_finite()) {
            return Err("conservative conversion overflow".into());
        }
        Ok(u)
    }

    /// Reject invalid states; never floor pressure or reset conserved energy.
    pub fn recover(self, u: Conservative, magnetic: Vec3) -> Result<Primitive, String> {
        if !u.iter().chain(magnetic.iter()).all(|x| x.is_finite()) || u[0] <= 0.0 {
            return Err("nonfinite conservative state or nonpositive density".into());
        }
        let velocity = [u[1] / u[0], u[2] / u[0], u[3] / u[0]];
        let pressure = (self.gamma - 1.0)
            * (u[4] - 0.5 * (u[0] * dot(velocity, velocity) + dot(magnetic, magnetic)));
        let q = Primitive {
            density: u[0],
            velocity,
            pressure,
            magnetic,
        };
        q.validate()?;
        Ok(q)
    }

    /// Fast magnetosonic speed for a validated primitive and unit normal.
    /// Scale speeds before forming the discriminant to avoid squaring physical
    /// pressures/field energies, which can overflow or underflow unnecessarily.
    pub fn fast_speed(self, q: Primitive, normal: Vec3) -> f64 {
        let root_rho = q.density.sqrt();
        let sound = self.gamma.sqrt() * (q.pressure.sqrt() / root_rho);
        let alfven = q.magnetic.map(|b| b / root_rho);
        let magnitude = |v: Vec3| v[0].hypot(v[1]).hypot(v[2]);
        let scale = sound.max(magnitude(alfven));
        if scale == 0.0 || !scale.is_finite() {
            return scale;
        }
        let a = sound / scale;
        let b = alfven.map(|v| v / scale);
        let bn = dot(b, normal);
        let bt = std::array::from_fn(|k| b[k] - bn * normal[k]);
        let a2 = a * a;
        let b2 = dot(b, b);
        // (a²+b²)²-4a²bn² = (a²-b²)²+4a²bt², evaluated with hypot.
        let discriminant_root = (a2 - b2).hypot(2.0 * a * magnitude(bt));
        scale * (0.5 * (a2 + b2 + discriminant_root)).sqrt()
    }
}

impl Primitive {
    pub fn validate(self) -> Result<(), String> {
        if self.density <= 0.0
            || self.pressure <= 0.0
            || ![self.density, self.pressure]
                .iter()
                .chain(self.velocity.iter())
                .chain(self.magnetic.iter())
                .all(|x| x.is_finite())
        {
            return Err(
                "primitive state requires finite values, positive density and pressure".into(),
            );
        }
        Ok(())
    }
}

pub fn dot(a: Vec3, b: Vec3) -> f64 {
    a.iter().zip(b).map(|(x, y)| x * y).sum()
}

pub fn cross(a: Vec3, b: Vec3) -> Vec3 {
    [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FluxMethod {
    Upwind,
    Hlld,
    HllFallback,
}

/// State used to complete the A-face source's undetermined normal EMF.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum FaceCompletion {
    /// Historical single/double-star selection, including collapsed fans.
    #[default]
    Intermediate,
    /// Continuous two-wave average; conservative HLLD fluxes are unchanged.
    HllAverage,
}

#[derive(Clone, Copy, Debug)]
pub struct FaceFlux {
    /// Laboratory ALE flux per unit area, oriented along the input normal.
    pub fluid: Conservative,
    pub induction: Vec3,
    /// Laboratory (v cross B); obtained from the numerical induction flux.
    /// In an HLL fallback this need not equal the product of the HLL average state.
    pub electromotive: Vec3,
    pub velocity: Vec3,
    pub magnetic: Vec3,
    pub max_speed: f64,
    pub method: FluxMethod,
}

type State = [f64; 8]; // rho, momentum(3), E, B(3)

fn state(eos: IdealGas, q: Primitive) -> Result<State, String> {
    let u = eos.conservative(q)?;
    Ok([
        u[0],
        u[1],
        u[2],
        u[3],
        u[4],
        q.magnetic[0],
        q.magnetic[1],
        q.magnetic[2],
    ])
}

fn physical_flux(u: State, p_total: f64) -> State {
    let v = [u[1] / u[0], u[2] / u[0], u[3] / u[0]];
    let b = [u[5], u[6], u[7]];
    [
        u[1],
        u[1] * v[0] + p_total - b[0] * b[0],
        u[2] * v[0] - b[0] * b[1],
        u[3] * v[0] - b[0] * b[2],
        (u[4] + p_total) * v[0] - b[0] * dot(v, b),
        0.0,
        v[0] * b[1] - b[0] * v[1],
        v[0] * b[2] - b[0] * v[2],
    ]
}

fn jump_flux(f: State, s: f64, from: State, to: State) -> State {
    std::array::from_fn(|k| f[k] + s * (to[k] - from[k]))
}

fn admissible(eos: IdealGas, u: State) -> bool {
    eos.recover([u[0], u[1], u[2], u[3], u[4]], [u[5], u[6], u[7]])
        .is_ok()
}

fn star(u: State, speed: f64, middle: f64, pt: f64, pt_star: f64) -> Option<State> {
    let rho = u[0];
    let v = [u[1] / rho, u[2] / rho, u[3] / rho];
    let b = [u[5], u[6], u[7]];
    let d = rho * (speed - v[0]) * (speed - middle) - b[0] * b[0];
    let scale = (rho * (speed - v[0]) * (speed - middle)).abs() + b[0] * b[0];
    if (speed - middle).abs() <= 1e-12 * (speed.abs() + middle.abs()).max(1e-100)
        || d.abs() <= 1e-12 * scale.max(1e-100)
    {
        return None;
    }
    let rs = rho * (speed - v[0]) / (speed - middle);
    let vs = [
        middle,
        v[1] - b[0] * b[1] * (middle - v[0]) / d,
        v[2] - b[0] * b[2] * (middle - v[0]) / d,
    ];
    let factor = (rho * (speed - v[0]).powi(2) - b[0] * b[0]) / d;
    let bs = [b[0], b[1] * factor, b[2] * factor];
    let energy =
        ((speed - v[0]) * u[4] - pt * v[0] + pt_star * middle + b[0] * (dot(v, b) - dot(vs, bs)))
            / (speed - middle);
    Some([
        rs,
        rs * vs[0],
        rs * vs[1],
        rs * vs[2],
        energy,
        bs[0],
        bs[1],
        bs[2],
    ])
}

fn double_stars(l: State, r: State) -> (State, State) {
    let roots = [l[0].sqrt(), r[0].sqrt()];
    let denom = roots[0] + roots[1];
    let sign = if l[5] >= 0.0 { 1.0 } else { -1.0 };
    let mut ll = l;
    let mut rr = r;
    for k in 1..3 {
        let vl = l[k + 1] / l[0];
        let vr = r[k + 1] / r[0];
        let vb = (roots[0] * vl + roots[1] * vr + sign * (r[k + 5] - l[k + 5])) / denom;
        let bb =
            (roots[0] * r[k + 5] + roots[1] * l[k + 5] + sign * roots[0] * roots[1] * (vr - vl))
                / denom;
        ll[k + 1] = l[0] * vb;
        rr[k + 1] = r[0] * vb;
        ll[k + 5] = bb;
        rr[k + 5] = bb;
    }
    let vdotb = |u: State| (u[1] * u[5] + u[2] * u[6] + u[3] * u[7]) / u[0];
    ll[4] = l[4] - sign * roots[0] * (vdotb(l) - vdotb(ll));
    rr[4] = r[4] + sign * roots[1] * (vdotb(r) - vdotb(rr));
    (ll, rr)
}

fn hlld(
    eos: IdealGas,
    l: State,
    r: State,
    speeds: [f64; 2],
    pressures: [f64; 2],
) -> Option<(State, State)> {
    let [sl, sr] = speeds;
    let [pl, pr] = pressures;
    let vl = l[1] / l[0];
    let vr = r[1] / r[0];
    let dl = l[0] * (sl - vl);
    let dr = r[0] * (sr - vr);
    let sm = (dr * vr - dl * vl - pr + pl) / (dr - dl);
    let ps = pl + dl * (sm - vl);
    if !sm.is_finite() || ps <= 0.0 || sm < sl || sm > sr {
        return None;
    }
    let ls = star(l, sl, sm, pl, ps)?;
    let rs = star(r, sr, sm, pr, ps)?;
    if !admissible(eos, ls) || !admissible(eos, rs) {
        return None;
    }
    let sal = sm - l[5].abs() / ls[0].sqrt();
    let sar = sm + r[5].abs() / rs[0].sqrt();
    let tolerance = 1e-12 * sl.abs().max(sr.abs());
    if sal < sl - tolerance || sar > sr + tolerance {
        return None;
    }
    let fl = physical_flux(l, pl);
    let fr = physical_flux(r, pr);
    let fls = jump_flux(fl, sl, l, ls);
    let frs = jump_flux(fr, sr, r, rs);
    // At Bn=0 the rotational waves collapse to the contact: no division by Bn.
    if sal >= 0.0 {
        return Some((fls, ls));
    }
    if sar <= 0.0 {
        return Some((frs, rs));
    }
    let (lss, rss) = double_stars(ls, rs);
    if !admissible(eos, lss) || !admissible(eos, rss) {
        return None;
    }
    if sm >= 0.0 {
        Some((jump_flux(fls, sal, ls, lss), lss))
    } else {
        Some((jump_flux(frs, sar, rs, rss), rss))
    }
}

/// HLLD in a moving face's rest frame, with a common arithmetic-mean normal B.
/// Degenerate/nonphysical intermediate states use a counted two-wave HLL fallback.
/// The input primitives, rather than cell conserved energies, define face energy.
pub fn riemann(
    eos: IdealGas,
    left: Primitive,
    right: Primitive,
    normal: Vec3,
    face_velocity: Vec3,
) -> Result<FaceFlux, String> {
    riemann_with_completion(
        eos,
        left,
        right,
        normal,
        face_velocity,
        FaceCompletion::Intermediate,
    )
}

/// Explicit engineering completion for vector-potential consumers.
/// See docs/M1_COMPLETION_PLAN.md. `riemann` preserves the historical convention.
pub fn riemann_with_completion(
    eos: IdealGas,
    left: Primitive,
    right: Primitive,
    normal: Vec3,
    face_velocity: Vec3,
    completion: FaceCompletion,
) -> Result<FaceFlux, String> {
    left.validate()?;
    right.validate()?;
    if !normal
        .iter()
        .chain(face_velocity.iter())
        .all(|x| x.is_finite())
        || (dot(normal, normal) - 1.0).abs() > 1e-12
    {
        return Err("face requires a unit normal and finite velocity".into());
    }
    let reference = if normal[2].abs() < 0.9 {
        [0.0, 0.0, 1.0]
    } else {
        [0.0, 1.0, 0.0]
    };
    let mut tangent = cross(reference, normal);
    let norm = dot(tangent, tangent).sqrt();
    tangent.iter_mut().for_each(|x| *x /= norm);
    let frame = [normal, tangent, cross(normal, tangent)];
    let project = |v: Vec3| frame.map(|e| dot(e, v));
    let rotate = |v: Vec3| std::array::from_fn(|k| (0..3).map(|j| frame[j][k] * v[j]).sum());
    let bn = 0.5 * (dot(left.magnetic, normal) + dot(right.magnetic, normal));
    let local = |mut q: Primitive| {
        q.velocity = project(std::array::from_fn(|k| q.velocity[k] - face_velocity[k]));
        q.magnetic = project(q.magnetic);
        q.magnetic[0] = bn;
        q
    };
    let lq = local(left);
    let rq = local(right);
    let l = state(eos, lq)?;
    let r = state(eos, rq)?;
    let cf = eos
        .fast_speed(lq, [1.0, 0.0, 0.0])
        .max(eos.fast_speed(rq, [1.0, 0.0, 0.0]));
    let sl = lq.velocity[0].min(rq.velocity[0]) - cf;
    let sr = lq.velocity[0].max(rq.velocity[0]) + cf;
    if !cf.is_finite() || cf <= 0.0 || !sl.is_finite() || !sr.is_finite() {
        return Err("nonfinite or unrepresentable Riemann wave speeds".into());
    }
    let pl = lq.pressure + 0.5 * dot(lq.magnetic, lq.magnetic);
    let pr = rq.pressure + 0.5 * dot(rq.magnetic, rq.magnetic);
    let fl = physical_flux(l, pl);
    let fr = physical_flux(r, pr);
    let (f, u, method) = if sl >= 0.0 {
        (fl, l, FluxMethod::Upwind)
    } else if sr <= 0.0 {
        (fr, r, FluxMethod::Upwind)
    } else if let Some((f, u)) = hlld(eos, l, r, [sl, sr], [pl, pr]) {
        (f, u, FluxMethod::Hlld)
    } else {
        let flux = std::array::from_fn(|k| {
            (sr * fl[k] - sl * fr[k] + sl * sr * (r[k] - l[k])) / (sr - sl)
        });
        let average = std::array::from_fn(|k| (sr * r[k] - sl * l[k] - fr[k] + fl[k]) / (sr - sl));
        (flux, average, FluxMethod::HllFallback)
    };
    if !f.iter().all(|x| x.is_finite()) || !admissible(eos, u) {
        return Err("Riemann solution is nonfinite or inadmissible, including HLL fallback".into());
    }
    let u = if completion == FaceCompletion::HllAverage && sl < 0.0 && sr > 0.0 {
        let average = std::array::from_fn(|k| (sr * r[k] - sl * l[k] - fr[k] + fl[k]) / (sr - sl));
        if !admissible(eos, average) {
            return Err("inadmissible HLL A-face completion".into());
        }
        average
    } else {
        u
    };
    let momentum_rest = rotate([f[1], f[2], f[3]]);
    let magnetic = rotate([u[5], u[6], u[7]]);
    let induction_rest = rotate([f[5], f[6], f[7]]);
    let emf_rest = cross(normal, induction_rest);
    let boost_emf = cross(face_velocity, magnetic);
    let velocity_rest: Vec3 = rotate([u[1] / u[0], u[2] / u[0], u[3] / u[0]]);
    // A normal 1D induction flux determines only the tangential electric field.
    // Complete its normal component from the returned intermediate state.
    let normal_emf = dot(normal, cross(velocity_rest, magnetic));
    let fluid = [
        f[0],
        momentum_rest[0] + face_velocity[0] * f[0],
        momentum_rest[1] + face_velocity[1] * f[0],
        momentum_rest[2] + face_velocity[2] * f[0],
        f[4] + dot(face_velocity, momentum_rest) + 0.5 * dot(face_velocity, face_velocity) * f[0],
    ];
    let result = FaceFlux {
        fluid,
        induction: std::array::from_fn(|k| induction_rest[k] - bn * face_velocity[k]),
        electromotive: std::array::from_fn(|k| emf_rest[k] + normal[k] * normal_emf + boost_emf[k]),
        velocity: std::array::from_fn(|k| velocity_rest[k] + face_velocity[k]),
        magnetic,
        max_speed: sl.abs().max(sr.abs()),
        method,
    };
    if !result
        .fluid
        .iter()
        .chain(result.induction.iter())
        .chain(result.electromotive.iter())
        .chain(result.velocity.iter())
        .chain(result.magnetic.iter())
        .all(|x| x.is_finite())
        || !result.max_speed.is_finite()
    {
        return Err("laboratory flux conversion overflow".into());
    }
    Ok(result)
}
