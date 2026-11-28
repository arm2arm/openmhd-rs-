//! Spatial reconstruction and the two reevaluated right-hand sides (S1–S10).
use super::*;
use crate::auxiliary3::{SmoothVelocity3, VelocitySample3};
use mhd_core::{FaceCompletion, Primitive, cross, riemann_with_pressure_blend};
use moving_mesh::three_d::fit::{FitOrder3, PointFit3, SampleKey3, StencilSample3};
use moving_mesh::three_d::operator_mesh::{MeshFit3, OperatorMesh3};

pub(super) struct CellFits {
    linear: MeshFit3,
    faces: PointFit3,
    /// Face index and incidence orientation in the sample order of the scalar fit.
    samples: Vec<(usize, bool)>,
}

fn side(mesh: &OperatorMesh3, i: usize, j: usize, forward: bool) -> (usize, Vec3, Vec3) {
    let f = &mesh.faces()[j];
    let right = f.right.expect("periodic operator");
    let (dl, dr) = (
        sub(f.centroid, mesh.cells()[f.left].centroid),
        sub(f.centroid, mesh.lifted(right, f.right_image)),
    );
    if forward {
        debug_assert_eq!(i, f.left);
        (right, dl, dr)
    } else {
        debug_assert_eq!(i, right);
        (f.left, dr, dl)
    }
}

impl CellFits {
    pub(super) fn build(mesh: &OperatorMesh3, i: usize) -> Result<Self> {
        let mut samples = Vec::new();
        for &(j, forward) in mesh.incidences(i) {
            let f = &mesh.faces()[j];
            let (peer, displacement, _) = side(mesh, i, j, forward);
            let image = if forward {
                f.right_image
            } else {
                f.right_image.checked_neg()?
            };
            samples.push((
                StencilSample3 {
                    key: SampleKey3 {
                        owner: mesh.cells()[peer].id,
                        image,
                    },
                    displacement,
                    face_area: Some(f.area),
                },
                (j, forward),
            ));
        }
        samples.sort_by_key(|(s, _)| s.key);
        let (rows, samples) = samples.into_iter().unzip();
        Ok(Self {
            linear: mesh.fit(i, FitOrder3::Linear)?,
            faces: PointFit3::build(FitOrder3::Linear, mesh.cells()[i].volume, rows)?,
            samples,
        })
    }
}

fn pack(q: Primitive) -> [f64; 8] {
    let [x, y, z] = q.velocity;
    let [bx, by, bz] = q.magnetic;
    [q.density, x, y, z, q.pressure, bx, by, bz]
}
fn primitive([density, x, y, z, pressure, bx, by, bz]: [f64; 8]) -> Primitive {
    Primitive {
        density,
        velocity: [x, y, z],
        pressure,
        magnetic: [bx, by, bz],
    }
}
fn gradients<const N: usize>(fit: &MeshFit3, values: &[[f64; N]]) -> Result<[Vec3; N]> {
    let mut rows = [[0.; 3]; N];
    for (k, row) in rows.iter_mut().enumerate() {
        *row = fit
            .fit
            .apply(&fit.owners.iter().map(|&j| values[j][k]).collect::<Vec<_>>())?
            .gradient;
    }
    Ok(rows)
}
fn limited<const N: usize>(
    mesh: &OperatorMesh3,
    i: usize,
    values: &[[f64; N]],
    grad: &[[Vec3; N]],
    smooth: bool,
) -> [Vec3; N] {
    let mut low = [0.0_f64; N];
    let mut high = low;
    let mut concave = low;
    let mut convex = low;
    for &(face, forward) in mesh.incidences(i) {
        let (peer, d, other) = side(mesh, i, face, forward);
        let offset = sub(d, other);
        for k in 0..N {
            let jump = values[peer][k] - values[i][k];
            low[k] = low[k].min(jump);
            high[k] = high[k].max(jump);
            if smooth {
                let a = jump - dot(grad[i][k], offset);
                let b = dot(grad[peer][k], offset) - jump;
                concave[k] = concave[k].max((-a).min(-b));
                convex[k] = convex[k].max(a.min(b));
            }
        }
    }
    let mut scale = [1.0_f64; N];
    for &(face, forward) in mesh.incidences(i) {
        let (_, d, _) = side(mesh, i, face, forward);
        for (k, ratio) in scale.iter_mut().enumerate() {
            let extrap = dot(grad[i][k], d);
            if extrap > 0. {
                *ratio = ratio.min((high[k] + concave[k]) / extrap);
            }
            if extrap < 0. {
                *ratio = ratio.min((low[k] - convex[k]) / extrap);
            }
        }
    }
    std::array::from_fn(|k| grad[i][k].map(|v| v * scale[k]))
}

pub(super) struct Closure {
    pub b: Vec<Vec3>,
    pub gas: Vec<Primitive>,
    pub auxiliary: SmoothVelocity3,
    pub bulk: Vec3,
}
impl Epoch {
    pub(super) fn close(
        &self,
        model: &Model3,
        state: &[CellState3],
        origin: Vec3,
    ) -> Result<Closure> {
        let mesh = self.op.field().mesh();
        let a: Vec<_> = state.iter().map(|v| v.potential).collect();
        let b: Vec<_> = self
            .op
            .field()
            .apply(&a)?
            .into_iter()
            .map(|v| add(v, model.mean_field))
            .collect();
        let mut gas = Vec::with_capacity(b.len());
        let mut samples = Vec::with_capacity(b.len());
        let mut bulk = [0.; 3];
        let mut total = 0.;
        for ((s, c), &field) in state.iter().zip(mesh.cells()).zip(&b) {
            let q = model
                .eos
                .recover(s.conserved.map(|x| x / c.volume), field)?;
            if !s.phi.is_finite() {
                return Err("nonfinite cleaning field".into());
            }
            bulk = axpy(bulk, c.volume, q.velocity);
            total += c.volume;
            samples.push(VelocitySample3 {
                id: c.id,
                position: c.centroid,
                volume: c.volume,
                velocity: q.velocity,
            });
            gas.push(q);
        }
        let mean = mesh
            .cells()
            .iter()
            .zip(&b)
            .fold([0.; 3], |sum, (c, &field)| axpy(sum, c.volume, field))
            .map(|x| x / total);
        if mean
            .into_iter()
            .zip(model.mean_field)
            .any(|(v, h)| !v.is_finite() || (v - h).abs() > 1e-9 * model.field_scale)
        {
            return Err("configured periodic mean exceeded".into());
        }
        let auxiliary = SmoothVelocity3::deposit(mesh.domain().width, origin, &samples, 4)?;
        Ok(Closure {
            b,
            gas,
            auxiliary,
            bulk: bulk.map(|x| x / total),
        })
    }
    pub(super) fn rates(
        &self,
        state: &[CellState3],
        closed: &Closure,
        model: &Model3,
        velocity: &BTreeMap<CellId, Vec3>,
    ) -> Result<Rates> {
        let g = self.support.geometry();
        let motion = self.rates.cells_and_faces();
        let op = self.op.field();
        let mesh = op.mesh();
        let n = state.len();
        let q: Vec<_> = closed.gas.iter().copied().map(pack).collect();
        let a: Vec<_> = state.iter().map(|s| s.potential).collect();
        let phi: Vec<_> = state.iter().map(|s| [s.phi]).collect();
        let q_grad: Vec<_> = self
            .fits
            .iter()
            .map(|f| gradients(&f.linear, &q))
            .collect::<Result<_>>()?;
        let a_grad: Vec<_> = op
            .fits
            .iter()
            .map(|f| gradients(f, &a))
            .collect::<Result<_>>()?;
        let phi_grad: Vec<_> = op
            .fits
            .iter()
            .map(|f| gradients(f, &phi).map(|v| v[0]))
            .collect::<Result<_>>()?;
        let q_lim: Vec<_> = (0..n)
            .map(|i| limited(mesh, i, &q, &q_grad, false))
            .collect();
        let a_lim: Vec<_> = (0..n)
            .map(|i| limited(mesh, i, &a, &a_grad, true))
            .collect();
        let mut ratios = vec![1.0_f64; n];
        for f in mesh.faces() {
            let l = f.left;
            let r = f.right.unwrap();
            let ratio = q[l][4].min(q[r][4]) / q[l][4].max(q[r][4]);
            ratios[l] = ratios[l].min(ratio);
            ratios[r] = ratios[r].min(ratio);
        }
        let mut face_flux = BTreeMap::new();
        let mut solutions = Vec::new();
        let mut db = vec![[0.; 3]; n];
        for (j, f) in mesh.faces().iter().enumerate() {
            let l = f.left;
            let (r, dl, dr) = side(mesh, l, j, true);
            let reconstruct = |i: usize, d: Vec3| {
                primitive(std::array::from_fn(|k| q[i][k] + dot(q_lim[i][k], d)))
            };
            let w = axpy(
                [0.; 3],
                0.5,
                add(velocity[&mesh.cells()[l].id], velocity[&mesh.cells()[r].id]),
            );
            let wn = motion.face(g.face_ref(j)?)?.normal_speed;
            let face_velocity = axpy(w, wn - dot(w, f.normal), f.normal);
            let flux = riemann_with_pressure_blend(
                model.eos,
                reconstruct(l, dl),
                reconstruct(r, dr),
                f.normal,
                face_velocity,
                FaceCompletion::SignalWeighted,
                ratios[l].min(ratios[r]).powi(3),
            )?;
            let target = axpy(
                flux.induction,
                dot(f.normal, flux.magnetic),
                model.reference_velocity,
            )
            .map(|x| f.area * x);
            if l != r {
                db[l] = sub(db[l], target);
                db[r] = add(db[r], target);
            }
            let entry = std::array::from_fn(|k| {
                if k < 5 {
                    f.area * flux.fluid[k]
                } else {
                    target[k - 5]
                }
            });
            face_flux.insert(g.faces()[j].key, entry);
            solutions.push(flux);
        }
        let geom_rate = self.op.apply(&self.support, &self.rates, &a)?;
        let mut raw = Vec::with_capacity(n);
        let mut chi = Vec::with_capacity(n);
        let mut target = Vec::with_capacity(n);
        let mut timestep_limit = f64::INFINITY;
        for (i, c) in mesh.cells().iter().enumerate() {
            let kinematics = motion.cell(g.cell_ref(i)?)?;
            let u = closed.auxiliary.sample(c.centroid)?;
            let relative = sub(kinematics.centroid_velocity, u.value);
            let fit = &self.fits[i];
            let mut values = Vec::with_capacity(fit.samples.len());
            let mut emf = [0.; 3];
            let mut area = 0.;
            for &(j, forward) in &fit.samples {
                let f = &mesh.faces()[j];
                let (other, dx, dx_other) = side(mesh, i, j, forward);
                let (donor, d) = if dot(relative, dx) < 0. {
                    (i, dx)
                } else {
                    (other, dx_other)
                };
                values.push(std::array::from_fn::<_, 3, _>(|k| {
                    a[donor][k] + dot(a_lim[donor][k], d)
                }));
                let sol = &solutions[j];
                emf = axpy(
                    emf,
                    f.area,
                    sub(sol.electromotive, cross(u.value, sol.magnetic)),
                );
                area += f.area;
            }
            let mean_source = cross(sub(u.value, model.reference_velocity), model.mean_field);
            let mut rate = add(phi_grad[i], mean_source);
            for (k, v) in rate.iter_mut().enumerate() {
                let face_values: Vec<_> = values.iter().map(|r| r[k] - a[i][k]).collect();
                let transport = dot(relative, fit.faces.apply(&face_values)?.gradient);
                let distortion: f64 = (0..3).map(|j| u.jacobian[j][k] * a[i][j]).sum();
                *v += emf[k] / area - distortion + transport;
            }
            let cs2 = model.eos.gamma() * q[i][4] / q[i][0];
            let radius = (3. * c.volume / (4. * std::f64::consts::PI)).cbrt();
            let cleaning = crate::gauge::Cleaning::default().bounds(cs2.sqrt(), radius)?;
            let wave_sum: f64 = fit
                .samples
                .iter()
                .map(|&(j, _)| mesh.faces()[j].area * solutions[j].max_speed)
                .sum();
            let mut bound = cleaning
                .hyperbolic
                .min(cleaning.diffusive)
                .min(c.volume / wave_sum);
            let coeff = fit.faces.coefficients();
            let raw_weights: Vec<_> = (0..fit.samples.len())
                .map(|j| dot(relative, [coeff[1][j], coeff[2][j], coeff[3][j]]))
                .collect();
            let others = &raw_weights[1..];
            let transport =
                others.iter().sum::<f64>().abs() + others.iter().map(|v| v.abs()).sum::<f64>();
            bound = bound.min(1. / transport);
            for k in 0..3 {
                bound = bound.min(1. / u.jacobian.iter().map(|row| row[k].abs()).sum::<f64>());
            }
            for &(j, forward) in &fit.samples {
                let (peer, _, _) = side(mesh, i, j, forward);
                let dw = sub(velocity[&c.id], velocity[&mesh.cells()[peer].id]);
                bound = bound.min(radius / dot(dw, dw).sqrt());
            }
            timestep_limit = timestep_limit.min(0.3 * bound);
            let div_a: f64 = (0..3).map(|k| a_grad[i][k][k]).sum();
            chi.push(crate::gauge::Cleaning::default().rate(
                state[i].phi,
                div_a,
                cs2.sqrt(),
                radius,
            )?);
            raw.push(rate);
            target.push(std::array::from_fn(|k| {
                (db[i][k] - kinematics.volume_rate * closed.b[i][k]) / c.volume
            }));
        }
        let raw_curl = op.apply(&raw)?;
        let defect = (0..n)
            .map(|i| sub(sub(target[i], geom_rate[i]), raw_curl[i]))
            .collect();
        let averages = mesh
            .cells()
            .iter()
            .enumerate()
            .map(|(i, c)| {
                (
                    c.id,
                    std::array::from_fn(|k| {
                        if k < 5 {
                            state[i].conserved[k] / c.volume
                        } else {
                            closed.b[i][k - 5]
                        }
                    }),
                )
            })
            .collect();
        if !timestep_limit.is_finite() || timestep_limit <= 0. {
            return Err("invalid MHD timestep limit".into());
        }
        Ok(Rates {
            timestep_limit,
            raw,
            chi,
            defect,
            face_flux,
            averages,
        })
    }
}
