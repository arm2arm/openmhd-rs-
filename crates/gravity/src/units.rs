//! GP-1. No arbitrary physical L/M/V choice also imposes code G=1.
use crate::checked::{div, finite, mul, positive};
use crate::identity::{f64_bytes, sized_bytes};
use crate::{GravityError, Identity};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(usize)]
pub enum Quantity {
    Length,
    Mass,
    Velocity,
    Time,
    Density,
    Pressure,
    Energy,
    Momentum,
    AngularMomentum,
    Acceleration,
    SpecificPotential,
    Force,
    MagneticField,
    VectorPotential,
    Power,
    VolumetricPower,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CgsQuantity {
    Density,
    SpecificEnergy,
    Pressure,
    VolumetricPower,
}

#[derive(Clone, Debug)]
pub struct SiInputs {
    pub length_m: f64,
    pub mass_kg: f64,
    pub velocity_m_per_s: f64,
    pub g_si: f64,
    pub mu0_si: f64,
    pub provenance: String,
}

#[derive(Clone, Debug)]
struct PhysicalUnits {
    inputs: SiInputs,
    scales: [f64; 16],
    g_code: f64,
}

/// Immutable single owner of SI scales/constants, or an explicit non-SI fixture.
#[derive(Clone, Debug)]
pub struct UnitSystem {
    physical: Option<PhysicalUnits>,
    identity: Identity,
}

impl UnitSystem {
    pub fn dimensionless_g1() -> Self {
        Self {
            physical: None,
            identity: Identity::new(b"gravity-units-v1\0dimensionless-G1-mu01".to_vec()),
        }
    }

    /// Constants/provenance are caller-supplied physical inputs, not NIST defaults.
    pub fn si(
        length_m: f64,
        mass_kg: f64,
        velocity_m_per_s: f64,
        g_si: f64,
        mu0_si: f64,
        provenance: &str,
    ) -> Result<Self, GravityError> {
        for (value, name) in [
            (length_m, "length unit"),
            (mass_kg, "mass unit"),
            (velocity_m_per_s, "velocity unit"),
            (g_si, "SI G"),
            (mu0_si, "SI permeability"),
        ] {
            positive(value, name)?;
        }
        if provenance.trim().is_empty() {
            return Err(GravityError::InvalidValue("unit provenance"));
        }
        let l = length_m;
        let m = mass_kg;
        let v = velocity_m_per_s;
        let t = div(l, v, "time unit")?;
        let v2 = mul(v, v, "velocity squared unit")?;
        let l3 = mul(mul(l, l, "length squared unit")?, l, "volume unit")?;
        let rho = div(m, l3, "density unit")?;
        let pressure = mul(rho, v2, "pressure unit")?;
        let energy = mul(m, v2, "energy unit")?;
        let momentum = mul(m, v, "momentum unit")?;
        let angular_momentum = mul(l, momentum, "angular momentum unit")?;
        let acceleration = div(v2, l, "acceleration unit")?;
        let force = div(energy, l, "force unit")?;
        let b = mul(
            v,
            mul(mu0_si, rho, "magnetic unit radicand")?.sqrt(),
            "B unit",
        )?;
        let a = mul(b, l, "A unit")?;
        let power = div(energy, t, "power unit")?;
        let volume_power = div(pressure, t, "volumetric power unit")?;
        let g_code = div(
            mul(g_si, m, "code G numerator")?,
            mul(l, v2, "code G denominator")?,
            "code G",
        )?;
        let scales = [
            l,
            m,
            v,
            t,
            rho,
            pressure,
            energy,
            momentum,
            angular_momentum,
            acceleration,
            v2,
            force,
            b,
            a,
            power,
            volume_power,
        ];
        for value in scales {
            positive(value, "derived SI scale")?;
        }
        positive(g_code, "derived code G")?;
        let mut bytes = b"gravity-units-v1\0SI\0".to_vec();
        for value in [l, m, v, g_si, mu0_si] {
            f64_bytes(&mut bytes, value);
        }
        sized_bytes(&mut bytes, provenance.as_bytes());
        for value in scales {
            f64_bytes(&mut bytes, value);
        }
        f64_bytes(&mut bytes, g_code);
        Ok(Self {
            physical: Some(PhysicalUnits {
                scales,
                g_code,
                inputs: SiInputs {
                    length_m,
                    mass_kg,
                    velocity_m_per_s,
                    g_si,
                    mu0_si,
                    provenance: provenance.to_owned(),
                },
            }),
            identity: Identity::new(bytes),
        })
    }

    pub fn identity(&self) -> &Identity {
        &self.identity
    }

    pub fn g_code(&self) -> f64 {
        self.physical.as_ref().map_or(1.0, |p| p.g_code)
    }

    pub fn is_physical(&self) -> bool {
        self.physical.is_some()
    }

    pub fn si_inputs(&self) -> Option<&SiInputs> {
        self.physical.as_ref().map(|p| &p.inputs)
    }

    pub fn scale(&self, quantity: Quantity) -> Result<f64, GravityError> {
        self.physical
            .as_ref()
            .map(|p| p.scales[quantity as usize])
            .ok_or(GravityError::PhysicalUnitsRequired)
    }

    pub fn to_si(&self, quantity: Quantity, code_value: f64) -> Result<f64, GravityError> {
        finite(code_value, "code conversion input")?;
        mul(code_value, self.scale(quantity)?, "code to SI")
    }

    pub fn from_si(&self, quantity: Quantity, si_value: f64) -> Result<f64, GravityError> {
        finite(si_value, "SI conversion input")?;
        div(si_value, self.scale(quantity)?, "SI to code")
    }

    /// Named cgs boundary after the single SI map; no second base-unit system.
    pub fn to_cgs(&self, quantity: CgsQuantity, code_value: f64) -> Result<f64, GravityError> {
        let (si, factor) = match quantity {
            CgsQuantity::Density => (Quantity::Density, 1e-3),
            CgsQuantity::SpecificEnergy => (Quantity::SpecificPotential, 1e4),
            CgsQuantity::Pressure => (Quantity::Pressure, 10.0),
            CgsQuantity::VolumetricPower => (Quantity::VolumetricPower, 10.0),
        };
        mul(self.to_si(si, code_value)?, factor, "SI to cgs boundary")
    }

    pub fn from_cgs(&self, quantity: CgsQuantity, cgs_value: f64) -> Result<f64, GravityError> {
        let (si, factor) = match quantity {
            CgsQuantity::Density => (Quantity::Density, 1e-3),
            CgsQuantity::SpecificEnergy => (Quantity::SpecificPotential, 1e4),
            CgsQuantity::Pressure => (Quantity::Pressure, 10.0),
            CgsQuantity::VolumetricPower => (Quantity::VolumetricPower, 10.0),
        };
        finite(cgs_value, "cgs conversion input")?;
        self.from_si(si, div(cgs_value, factor, "cgs to SI boundary")?)
    }
}
