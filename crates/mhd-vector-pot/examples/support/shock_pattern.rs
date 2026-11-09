//! Diagnostic geometry only: reuse the original four-row perturbation pattern.
use moving_mesh::Mesh;

pub fn mesh(nx: usize, jitter: f64, height: f64, copies: usize) -> Result<Mesh, String> {
    if nx > 256
        || !height.is_finite()
        || !(0.03125..=0.125).contains(&height)
        || !(1..=4).contains(&copies)
    {
        return Err(
            "pattern controls require nx<=256, height .03125..=.125 and 1..=4 copies".into(),
        );
    }
    let original = Mesh::lattice(nx, 4, [2., 0.125], jitter)?;
    if height == 0.125 && copies == 1 {
        return Ok(original);
    }
    let scale = height / 0.125;
    let points = (0..copies)
        .flat_map(|tile| {
            original
                .generators
                .iter()
                .map(move |p| [p[0], scale * p[1] + tile as f64 * height])
        })
        .collect();
    Mesh::build(points, [2., height * copies as f64])
}
