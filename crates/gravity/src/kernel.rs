//! GP-2: differentiate the fixed Plummer pair potential, with d = x_right-x_left.
use crate::checked::{add, div, dot, mul, positive, scale, sub};
use crate::softening::GravityModel;
use crate::state::Particle;
use crate::{GravityError, Vec3};

#[derive(Clone, Copy, Debug)]
pub struct PairInteraction {
    pub force_on_left: Vec3,
    pub specific_potential_left: f64,
    pub specific_potential_right: f64,
    pub energy: f64,
}

pub fn pair(
    model: &GravityModel,
    left: &Particle,
    right: &Particle,
) -> Result<PairInteraction, GravityError> {
    if left.id() == right.id() {
        return Err(GravityError::SelfPair);
    }
    if left.softening() != model.softening().class()
        || right.softening() != model.softening().class()
    {
        return Err(GravityError::UnsupportedSofteningClass);
    }
    let d = sub(right.position(), left.position())?;
    let s2 = add(dot(d, d)?, model.softening().squared(), "softened distance squared")?;
    let s = positive(s2.sqrt(), "softened distance")?;
    let s3 = mul(s2, s, "softened distance cubed")?;
    let g_left = mul(model.g(), left.mass(), "G times left mass")?;
    let g_right = mul(model.g(), right.mass(), "G times right mass")?;
    let g_pair = mul(g_left, right.mass(), "G times pair masses")?;
    let coefficient = div(g_pair, s3, "pair force coefficient")?;
    Ok(PairInteraction {
        force_on_left: scale(d, coefficient)?,
        specific_potential_left: -div(g_right, s, "left potential")?,
        specific_potential_right: -div(g_left, s, "right potential")?,
        energy: -div(g_pair, s, "pair energy")?,
    })
}
