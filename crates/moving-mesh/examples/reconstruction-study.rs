//! Manufactured periodic scalar/planar-curl study; no fluid evolution.
use moving_mesh::{Derivatives, Mesh, Vec2};
use std::f64::consts::TAU;

fn scalar([x, y]: Vec2) -> f64 {
    (TAU * x).sin() * (TAU * y).sin()
}

fn exact([x, y]: Vec2) -> Vec2 {
    [
        TAU * (TAU * x).cos() * (TAU * y).sin(),
        TAU * (TAU * x).sin() * (TAU * y).cos(),
    ]
}

fn norms(mesh: &Mesh, gradients: &[Vec2]) -> [f64; 2] {
    let mut errors = [0.0; 2];
    let total: f64 = mesh.cells.iter().map(|c| c.volume).sum();
    for (c, g) in mesh.cells.iter().zip(gradients) {
        let e = exact(c.centroid);
        let norm = (g[0] - e[0]).hypot(g[1] - e[1]);
        errors[0] += c.volume * norm / total;
        errors[1] += c.volume * norm * norm / total;
    }
    [errors[0], errors[1].sqrt()]
}

fn run() -> Result<(), String> {
    println!("jitter,n,operator,l1,l2,condition,relative_volume_error,relative_closure_error");
    for jitter in [0.0, 0.15] {
        let mut first = [[0.0; 2]; 3];
        let mut previous = [[0.0; 2]; 3];
        for n in [8, 16, 32] {
            let mesh = Mesh::lattice(n, n, [1.0; 2], jitter)?;
            let cells = Derivatives::build(&mesh, false)?;
            let faces = Derivatives::build(&mesh, true)?;
            let values: Vec<_> = mesh.cells.iter().map(|c| scalar(c.centroid)).collect();
            let face_values: Vec<_> = mesh.faces.iter().map(|f| scalar(f.centroid)).collect();
            let raw = cells.gradient(&values)?;
            let limited = mesh.limit_gradients(&values, &raw)?;
            let face_gradient = faces.gradient(&face_values)?;
            let volume_error = (mesh.cells.iter().map(|c| c.volume).sum::<f64>() - 1.0).abs();
            let closure_error = mesh
                .cells
                .iter()
                .map(|c| {
                    let mut closure = [0.0; 2];
                    let mut perimeter = 0.0;
                    for &(f, sign) in &c.faces {
                        let face = &mesh.faces[f];
                        perimeter += face.area;
                        for (k, value) in closure.iter_mut().enumerate() {
                            *value += sign * face.area * face.normal[k];
                        }
                    }
                    closure[0].hypot(closure[1]) / perimeter
                })
                .fold(0.0, f64::max);
            for (i, (label, gradients, condition)) in [
                ("neighbour_raw", &raw, cells.worst_condition),
                ("neighbour_limited", &limited, cells.worst_condition),
                ("face_raw", &face_gradient, faces.worst_condition),
            ]
            .into_iter()
            .enumerate()
            {
                let error = norms(&mesh, gradients);
                if !error.iter().all(|e| e.is_finite() && *e > 0.0) {
                    return Err("nonfinite/zero study error".into());
                }
                if n == 8 {
                    first[i] = error;
                }
                if i == 0 && n > 8 {
                    for (k, value) in error.iter().enumerate() {
                        let order = (previous[i][k] / value).log2();
                        if order <= if jitter == 0.0 { 1.8 } else { 0.7 } {
                            return Err(format!("raw-neighbour order gate failed: {order}"));
                        }
                    }
                }
                if n == 32 && (0..2).any(|k| error[k] >= first[i][k]) {
                    return Err(format!("{label}: finest error did not decrease"));
                }
                previous[i] = error;
                println!(
                    "{jitter},{n},{label},{:.17e},{:.17e},{condition:.17e},{volume_error:.17e},{closure_error:.17e}",
                    error[0], error[1]
                );
            }
        }
    }
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("reconstruction-study: {e}");
        std::process::exit(1);
    }
}
