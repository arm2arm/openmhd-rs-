//! Isolated pointwise source and staged cleaning kernels for the M0 audit.
//! These do not replace the paper's face stencils or implement a coupled mesh step.
//! Source: arXiv:2609.35989v1 (38), (41)-(42), (49)-(50), (76), (81), (88), (90), (92).

pub type Vec3 = [f64; 3];
/// `[component][coordinate]`, e.g. gradient_a[a][b] = partial_b A_a.
pub type Jacobian = [[f64; 3]; 3];

#[derive(Clone, Copy, Debug)]
/// Local point data: A is the periodic potential, magnetic is the total B and
/// mean_magnetic is the separately stored background. Velocities are laboratory
/// values; centroid_velocity is not a mesh-generator or face velocity.
pub struct PointSources {
    pub potential: Vec3,
    pub fluid_velocity: Vec3,
    pub auxiliary_velocity: Vec3,
    pub centroid_velocity: Vec3,
    pub magnetic: Vec3,
    pub mean_magnetic: Vec3,
    pub gradient_a: Jacobian,
    pub gradient_auxiliary: Jacobian,
    pub gradient_phi: Vec3,
    pub current: Vec3,
    pub resistivity: f64,
}

#[derive(Clone, Copy, Debug)]
pub struct PotentialRate {
    pub induction: Vec3,
    pub distortion: Vec3,
    pub advection: Vec3,
    pub resistive: Vec3,
    pub cleaning: Vec3,
    pub mean_field: Vec3,
}

fn cross(a: Vec3, b: Vec3) -> Vec3 {
    [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
}

fn finite_vec(v: Vec3) -> bool {
    v.iter().all(|x| x.is_finite())
}
fn finite(value: f64, context: &str) -> Result<f64, String> {
    if value.is_finite() {
        Ok(value)
    } else {
        Err(format!("nonfinite {context}"))
    }
}
fn positive(value: f64, context: &str) -> Result<f64, String> {
    if value.is_finite() && value > 0.0 {
        Ok(value)
    } else {
        Err(format!("{context} must be finite and positive"))
    }
}
fn interval(dt: f64) -> Result<(), String> {
    if dt.is_finite() && dt >= 0.0 {
        Ok(())
    } else {
        Err("time interval must be finite and nonnegative".into())
    }
}

impl PotentialRate {
    pub fn total(self) -> Vec3 {
        std::array::from_fn(|k| {
            self.induction[k]
                + self.distortion[k]
                + self.advection[k]
                + self.resistive[k]
                + self.cleaning[k]
                + self.mean_field[k]
        })
    }
}

impl PointSources {
    pub fn rate(self) -> Result<PotentialRate, String> {
        if ![
            self.potential,
            self.fluid_velocity,
            self.auxiliary_velocity,
            self.centroid_velocity,
            self.magnetic,
            self.mean_magnetic,
            self.gradient_phi,
            self.current,
        ]
        .into_iter()
        .all(finite_vec)
            || !self
                .gradient_a
                .into_iter()
                .chain(self.gradient_auxiliary)
                .all(finite_vec)
            || !self.resistivity.is_finite()
            || self.resistivity < 0.0
        {
            return Err(
                "point source requires finite vectors/Jacobians and nonnegative resistivity".into(),
            );
        }
        let relative_fluid =
            std::array::from_fn(|k| self.fluid_velocity[k] - self.auxiliary_velocity[k]);
        let relative_mesh: Vec3 =
            std::array::from_fn(|k| self.centroid_velocity[k] - self.auxiliary_velocity[k]);
        let result = PotentialRate {
            induction: cross(relative_fluid, self.magnetic),
            distortion: std::array::from_fn(|b| {
                -(0..3)
                    .map(|a| self.gradient_auxiliary[a][b] * self.potential[a])
                    .sum::<f64>()
            }),
            advection: std::array::from_fn(|a| {
                (0..3)
                    .map(|b| self.gradient_a[a][b] * relative_mesh[b])
                    .sum()
            }),
            resistive: self.current.map(|j| -self.resistivity * j),
            cleaning: self.gradient_phi,
            mean_field: cross(self.auxiliary_velocity, self.mean_magnetic),
        };
        if ![
            result.induction,
            result.distortion,
            result.advection,
            result.resistive,
            result.cleaning,
            result.mean_field,
            result.total(),
        ]
        .into_iter()
        .all(finite_vec)
        {
            return Err("point source overflow".into());
        }
        Ok(result)
    }
}

#[derive(Clone, Copy, Debug)]
pub struct Cleaning {
    alpha: f64,
    beta: f64,
}

impl Default for Cleaning {
    fn default() -> Self {
        Self {
            alpha: 1.0,
            beta: 0.15,
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub struct CleaningBounds {
    /// Printed equation (49), r/(alpha cs).
    pub hyperbolic: f64,
    /// Printed equation (50), r^2/D, D=alpha cs r/beta.
    pub diffusive: f64,
}

/// Immutable initial source data enforce equation (90)'s frozen div(A) and cs.
#[derive(Clone, Copy, Debug)]
pub struct CleaningStage {
    parameters: Cleaning,
    phi_initial: f64,
    divergence_initial: f64,
    sound_speed_initial: f64,
    rate_initial: f64,
}

impl Cleaning {
    /// This active-cleaning kernel requires positive alpha and beta. Disabling
    /// cleaning is an explicit caller decision, not represented by invalid bounds.
    pub fn new(alpha: f64, beta: f64) -> Result<Self, String> {
        positive(alpha, "alpha")?;
        positive(beta, "beta")?;
        Ok(Self { alpha, beta })
    }
    pub fn alpha(self) -> f64 {
        self.alpha
    }
    pub fn beta(self) -> f64 {
        self.beta
    }

    pub fn rate(
        self,
        phi: f64,
        divergence_a: f64,
        sound_speed: f64,
        radius: f64,
    ) -> Result<f64, String> {
        finite(phi, "cleaning scalar")?;
        finite(divergence_a, "potential divergence")?;
        positive(sound_speed, "sound speed")?;
        positive(radius, "cell radius")?;
        finite(
            self.alpha * sound_speed.powi(2) * divergence_a
                - self.beta * sound_speed * phi / radius,
            "cleaning rate",
        )
    }

    pub fn bounds(self, sound_speed: f64, radius: f64) -> Result<CleaningBounds, String> {
        positive(sound_speed, "sound speed")?;
        positive(radius, "cell radius")?;
        let hyperbolic = positive(radius / (self.alpha * sound_speed), "hyperbolic bound")?;
        let diffusive = positive(self.beta * hyperbolic, "diffusive bound")?;
        Ok(CleaningBounds {
            hyperbolic,
            diffusive,
        })
    }

    pub fn begin(
        self,
        phi: f64,
        divergence_a: f64,
        sound_speed: f64,
        radius: f64,
    ) -> Result<CleaningStage, String> {
        let rate_initial = self.rate(phi, divergence_a, sound_speed, radius)?;
        Ok(CleaningStage {
            parameters: self,
            phi_initial: phi,
            divergence_initial: divergence_a,
            sound_speed_initial: sound_speed,
            rate_initial,
        })
    }
}

impl CleaningStage {
    pub fn initial_rate(self) -> f64 {
        self.rate_initial
    }

    pub fn predicted_phi(self, dt: f64) -> Result<f64, String> {
        interval(dt)?;
        finite(
            self.phi_initial + dt * self.rate_initial,
            "predicted cleaning scalar",
        )
    }

    pub fn endpoint_rate(self, dt: f64, endpoint_radius: f64) -> Result<f64, String> {
        self.parameters.rate(
            self.predicted_phi(dt)?,
            self.divergence_initial,
            self.sound_speed_initial,
            endpoint_radius,
        )
    }

    pub fn finish_phi(self, dt: f64, endpoint_radius: f64) -> Result<f64, String> {
        interval(dt)?;
        let rate_end = self.endpoint_rate(dt, endpoint_radius)?;
        finite(
            self.phi_initial + 0.5 * dt * (self.rate_initial + rate_end),
            "updated cleaning scalar",
        )
    }
}
