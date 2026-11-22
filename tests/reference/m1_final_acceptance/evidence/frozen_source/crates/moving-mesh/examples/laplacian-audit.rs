//! Frozen Fourier-mode probe. Accuracy of second derivatives does not imply
//! stability when their trace is used as an explicit diffusion operator.
use moving_mesh::{Derivatives, Mesh, QuadraticHessians};
use std::f64::consts::TAU;

fn main() -> Result<(), String> {
    println!(
        "jitter,kx,ky,operator,potential_rayleigh,magnetic_energy_rate,quadratic_laplacian_linf_bound"
    );
    for jitter in [0., 0.15] {
        let mesh = Mesh::lattice(16, 16, [1.; 2], jitter)?;
        let linear = Derivatives::build(&mesh, false)?;
        let hessian = QuadraticHessians::build(&mesh)?;
        for k in 0..=8 {
            for ky in [0, k] {
                if k == 0 && ky == k {
                    continue;
                }
                let a: Vec<_> = mesh
                    .cells
                    .iter()
                    .map(|c| {
                        (0.37
                            + TAU * (f64::from(k) * c.centroid[0] + f64::from(ky) * c.centroid[1]))
                            .sin()
                    })
                    .collect();
                let grad = linear.gradient(&a)?;
                let gx = linear.gradient(&grad.iter().map(|g| g[0]).collect::<Vec<_>>())?;
                let gy = linear.gradient(&grad.iter().map(|g| g[1]).collect::<Vec<_>>())?;
                let quadratic: Vec<_> = hessian.evaluate(&a)?.iter().map(|h| h[0] + h[1]).collect();
                let successive: Vec<_> = gx.iter().zip(gy).map(|(x, y)| x[0] + y[1]).collect();
                for (name, rate) in [("successive", successive), ("quadratic", quadratic)] {
                    let dr = linear.gradient(&rate)?;
                    let mut numerator = 0.;
                    let mut norm = 0.;
                    let mut magnetic = 0.;
                    for (i, c) in mesh.cells.iter().enumerate() {
                        numerator += c.volume * a[i] * rate[i];
                        norm += c.volume * a[i] * a[i];
                        magnetic += c.volume * (grad[i][0] * dr[i][0] + grad[i][1] * dr[i][1]);
                    }
                    println!(
                        "{jitter},{k},{ky},{name},{:.17e},{:.17e},{:.17e}",
                        numerator / norm,
                        magnetic,
                        hessian.laplacian_norm_bound()
                    );
                }
            }
        }
    }
    Ok(())
}
