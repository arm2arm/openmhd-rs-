use crate::checked::{mul, positive};
use crate::identity::f64_bytes;
use crate::units::UnitSystem;
use crate::{GravityError, Identity};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SofteningClass(u16);

impl SofteningClass {
    pub const fn new(value: u16) -> Self {
        Self(value)
    }

    pub const fn value(self) -> u16 {
        self.0
    }
}

#[derive(Clone, Debug)]
pub struct FixedPlummer {
    epsilon: f64,
    epsilon_squared: f64,
    class: SofteningClass,
}

impl FixedPlummer {
    pub fn new(epsilon: f64, class: SofteningClass) -> Result<Self, GravityError> {
        positive(epsilon, "common epsilon")?;
        let epsilon_squared = mul(epsilon, epsilon, "epsilon squared")?;
        Ok(Self { epsilon, epsilon_squared, class })
    }

    pub fn epsilon(&self) -> f64 {
        self.epsilon
    }

    pub fn class(&self) -> SofteningClass {
        self.class
    }

    pub(crate) fn squared(&self) -> f64 {
        self.epsilon_squared
    }
}

#[derive(Clone, Debug)]
pub struct GravityModel {
    units: UnitSystem,
    softening: FixedPlummer,
    identity: Identity,
}

impl GravityModel {
    pub fn new(units: UnitSystem, softening: FixedPlummer) -> Self {
        let mut bytes = b"gravity-model-v1\0isolated-common-Plummer-no-self\0".to_vec();
        f64_bytes(&mut bytes, units.g_code());
        f64_bytes(&mut bytes, softening.epsilon);
        bytes.extend_from_slice(&softening.class.value().to_be_bytes());
        Self { units, softening, identity: Identity::new(bytes) }
    }

    pub fn units(&self) -> &UnitSystem {
        &self.units
    }

    pub fn softening(&self) -> &FixedPlummer {
        &self.softening
    }

    pub fn g(&self) -> f64 {
        self.units.g_code()
    }

    pub fn identity(&self) -> &Identity {
        &self.identity
    }
}
