//! S10–S12. Cache the shared-face curl rows for both actions in each normal solve.
use super::*;
use mhd_core::cross;

pub(super) struct ScreenedCurl {
    rows: Vec<Vec<(usize, Vec3)>>,
    volumes: Vec<f64>,
    diagonal: Vec<Vec3>,
}

fn inner(a: &[Vec3], b: &[Vec3]) -> f64 {
    a.iter().zip(b).map(|(&x, &y)| dot(x, y)).sum()
}

impl ScreenedCurl {
    pub(super) fn new(op: &SharedFaceCurl3) -> Result<Self> {
        let mesh = op.mesh();
        let volumes: Vec<_> = mesh.cells().iter().map(|c| c.volume).collect();
        let mut cell_rows = vec![BTreeMap::<usize, Vec3>::new(); volumes.len()];
        for (j, f) in mesh.faces().iter().enumerate() {
            let right = f.right.ok_or("periodic face without neighbour")?;
            if f.left == right {
                continue;
            }
            let weights = op.face_weights(j)?;
            for (i, oriented_area) in [(f.left, f.area), (right, -f.area)] {
                for (&source, &weight) in &weights {
                    let g = cell_rows[i].entry(source).or_default();
                    for (x, n) in g.iter_mut().zip(f.normal) {
                        *x += oriented_area * n * weight;
                    }
                }
            }
        }
        let mut diagonal = vec![[0.; 3]; volumes.len()];
        let rows = cell_rows
            .into_iter()
            .zip(&volumes)
            .map(|(row, &v)| {
                row.into_iter()
                    .map(|(j, w)| {
                        let g = w.map(|x| x / v);
                        for (k, d) in diagonal[j].iter_mut().enumerate() {
                            *d += v * (g[(k + 1) % 3].powi(2) + g[(k + 2) % 3].powi(2));
                        }
                        (j, g)
                    })
                    .collect()
            })
            .collect();
        let peak = diagonal.iter().flatten().copied().fold(0., f64::max);
        if diagonal
            .iter()
            .flatten()
            .any(|&d| !d.is_finite() || (d > 0. && d < 1e-14 * peak))
        {
            return Err("screened curl has a nonfinite or poorly scaled column".into());
        }
        Ok(Self {
            rows,
            volumes,
            diagonal,
        })
    }
    fn curl(&self, x: &[Vec3]) -> Vec<Vec3> {
        self.rows
            .iter()
            .map(|row| {
                row.iter()
                    .fold([0.; 3], |s, &(j, g)| add(s, cross(g, x[j])))
            })
            .collect()
    }
    fn dual(&self, x: &[Vec3]) -> Vec<Vec3> {
        let mut y = vec![[0.; 3]; x.len()];
        for ((row, &b), &v) in self.rows.iter().zip(x).zip(&self.volumes) {
            let weighted = b.map(|x| v * x);
            for &(j, g) in row {
                y[j] = add(y[j], cross(weighted, g));
            }
        }
        y
    }
    fn normal(&self, x: &[Vec3]) -> Vec<Vec3> {
        self.dual(&self.curl(x))
            .into_iter()
            .enumerate()
            .map(|(i, y)| std::array::from_fn(|k| y[k] + self.diagonal[i][k] * x[i][k]))
            .collect()
    }
    fn precondition(&self, x: &[Vec3]) -> Vec<Vec3> {
        x.iter()
            .zip(&self.diagonal)
            .map(|(r, d)| std::array::from_fn(|k| if d[k] == 0. { 0. } else { r[k] / d[k] }))
            .collect()
    }
    pub(super) fn correction(
        &self,
        defect: &[Vec3],
        interval: f64,
    ) -> Result<(Vec<Vec3>, SolveReport)> {
        let b: Vec<_> = self
            .dual(defect)
            .into_iter()
            .map(|v| v.map(|x| interval * x))
            .collect();
        let norm = inner(&b, &b).sqrt();
        if !norm.is_finite()
            || b.iter()
                .flatten()
                .zip(self.diagonal.iter().flatten())
                .any(|(&x, &d)| d == 0. && x != 0.)
        {
            return Err("inconsistent screened induction RHS".into());
        }
        let mut x = vec![[0.; 3]; b.len()];
        if norm <= 1e-30 {
            return Ok((
                x,
                SolveReport {
                    iterations: 0,
                    rhs_norm: norm,
                    true_residual: norm,
                },
            ));
        }
        let mut r = b.clone();
        let mut p = self.precondition(&r);
        let mut rz = inner(&r, &p);
        for iterations in 1..=24 * b.len() {
            let hp = self.normal(&p);
            let curvature = inner(&p, &hp);
            if !(curvature.is_finite() && curvature > 0. && rz.is_finite() && rz > 0.) {
                return Err("invalid screened induction curvature".into());
            }
            let alpha = rz / curvature;
            for i in 0..x.len() {
                x[i] = axpy(x[i], alpha, p[i]);
                r[i] = axpy(r[i], -alpha, hp[i]);
            }
            if inner(&r, &r).sqrt() <= 1e-11 * norm {
                let residual: Vec<_> = self
                    .normal(&x)
                    .into_iter()
                    .zip(&b)
                    .map(|(h, &rhs)| sub(rhs, h))
                    .collect();
                let true_residual = inner(&residual, &residual).sqrt() / norm;
                if !true_residual.is_finite() || true_residual > 1e-9 {
                    return Err("screened induction true residual exceeds tolerance".into());
                }
                return Ok((
                    x,
                    SolveReport {
                        iterations,
                        rhs_norm: norm,
                        true_residual,
                    },
                ));
            }
            let z = self.precondition(&r);
            let next = inner(&r, &z);
            for (direction, v) in p.iter_mut().zip(z) {
                *direction = axpy(v, next / rz, *direction);
            }
            rz = next;
        }
        Err("screened induction iteration limit".into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use moving_mesh::three_d::fit::SampleKey3;
    #[test]
    fn moving_screen_matches_independent_face_actions_and_normal_residual() {
        let sites: Vec<_> = include_str!("../../tests/fixtures/m2c_shared_jitter.bits")
            .lines()
            .enumerate()
            .map(|(i, row)| {
                let x: Vec<_> = row
                    .split_whitespace()
                    .map(|v| f64::from_bits(u64::from_str_radix(v, 16).unwrap()))
                    .collect();
                Generator3 {
                    id: SampleKey3::from_words(7, i as u64, Image3::ZERO).owner,
                    position: x.try_into().unwrap(),
                    winding: Image3::ZERO,
                }
            })
            .collect();
        let g = HalfSpaceOracle3::build_supported_periodic(
            Domain3 {
                anchor: [0.; 3],
                width: [1.; 3],
                boundary: Boundary3::Periodic,
            },
            &sites,
        )
        .unwrap();
        let op = SharedFaceCurl3::from_validated(g.geometry()).unwrap();
        let cached = ScreenedCurl::new(&op).unwrap();
        let a: Vec<Vec3> = (0..sites.len())
            .map(|i| std::array::from_fn(|k| (((7 * i + 11 * k + 1) % 19) as f64 - 9.) / 16.))
            .collect();
        let direct = op.apply(&a).unwrap();
        let gram = op.gram_diagonal().unwrap();
        let worst = |v: &[Vec3], w: &[Vec3]| {
            v.iter()
                .flatten()
                .zip(w.iter().flatten())
                .map(|(a, b)| (a - b).abs())
                .fold(0., f64::max)
        };
        assert!(worst(&direct, &cached.curl(&a)) < 1e-12);
        assert!(worst(&gram, &cached.diagonal) < 1e-12);
        let dt = 1. / 32.;
        let (z, report) = cached.correction(&a, dt).unwrap();
        let scaled = |b: &[Vec3]| {
            b.iter()
                .zip(&cached.volumes)
                .map(|(v, h)| v.map(|x| x * h))
                .collect::<Vec<_>>()
        };
        let physical: Vec<_> = op
            .apply(&z)
            .unwrap()
            .iter()
            .zip(&a)
            .map(|(&v, &target)| axpy(v, -dt, target))
            .collect();
        let mut residual = op.transpose(&scaled(&physical)).unwrap();
        for ((v, d), x) in residual.iter_mut().zip(gram).zip(z) {
            for k in 0..3 {
                v[k] += d[k] * x[k];
            }
        }
        assert!(inner(&residual, &residual).sqrt() / report.rhs_norm < 1e-9);
        assert!(inner(&physical, &physical).sqrt() > 1e-4 && report.iterations > 0);
        let (zero, sol) = cached.correction(&a, 0.).unwrap();
        assert!(zero.iter().flatten().all(|x| *x == 0.));
        assert_eq!(sol.iterations, 0);
    }
}
