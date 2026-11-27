//! Static, unlimited point curl. Array indices are [field component][coordinate].
use moving_mesh::three_d::{
    Tensor3, Vec3,
    fit::{FitError3, PointFit3, ScalarJet3},
};

pub fn curl(j: Tensor3) -> Vec3 {
    [j[2][1] - j[1][2], j[0][2] - j[2][0], j[1][0] - j[0][1]]
}
pub fn trace(j: Tensor3) -> f64 {
    j[0][0] + j[1][1] + j[2][2]
}

#[derive(Debug, Clone, Copy)]
pub struct MagneticJet3 {
    pub potential: [ScalarJet3; 3],
    pub field: Vec3,
    pub div_a: f64,
    pub same_fit_jacobian: Option<Tensor3>,
}
/// Observations are ordered by fit.samples(); an image looks up the same
/// periodic owner's potential. Manufactured lifted scalar fields may instead
/// supply a different value for each image.
pub fn recover(fit: &PointFit3, values: &[Vec3], mean: Vec3) -> Result<MagneticJet3, FitError3> {
    if !mean.into_iter().all(f64::is_finite) {
        return Err(FitError3::NonFinite);
    }
    let apply = |k: usize| fit.apply(&values.iter().map(|v| v[k]).collect::<Vec<_>>());
    let potential = [apply(0)?, apply(1)?, apply(2)?];
    let j = potential.map(|s| s.gradient);
    let c = curl(j);
    let field = std::array::from_fn(|i| mean[i] + c[i]);
    let same_fit_jacobian = match potential.map(|p| p.hessian) {
        [Some(a), Some(b), Some(c)] => Some(std::array::from_fn(|k| {
            std::array::from_fn(|i| [c[1][i] - b[2][i], a[2][i] - c[0][i], b[0][i] - a[1][i]][k])
        })),
        _ => None,
    };
    let div_a = trace(j);
    if !field
        .into_iter()
        .chain([div_a])
        .chain(same_fit_jacobian.into_iter().flatten().flatten())
        .all(f64::is_finite)
    {
        return Err(FitError3::NonFinite);
    }
    Ok(MagneticJet3 {
        potential,
        field,
        div_a,
        same_fit_jacobian,
    })
}
