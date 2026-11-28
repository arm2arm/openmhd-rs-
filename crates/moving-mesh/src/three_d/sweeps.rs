//! Geometric conservation on one prescribed, fixed-domain substep.
//! Endpoint area quadrature and its shared graph correction are recorded separately.
use super::moments::Sum;
use super::{FaceKey3, GeometryEpoch3, GeometryError3, MotionRates3, ValidatedGeometry3};
use galaxy_types::CellId;
use std::collections::BTreeMap;

#[derive(Clone, Debug, PartialEq)]
pub enum SweepError3 {
    Geometry(GeometryError3),
    ChangedDomainOrOwners,
    ChangedTrajectory,
    InvalidTimestep,
    MovingWall,
    NonFinite,
    IncompatibleComponent {
        anchor: CellId,
        residual: f64,
        bound: f64,
    },
    SingularGraph,
    UnclosedCell {
        owner: CellId,
        relative: f64,
    },
    ExchangeCatalog,
}
impl From<GeometryError3> for SweepError3 {
    fn from(value: GeometryError3) -> Self {
        Self::Geometry(value)
    }
}
impl std::fmt::Display for SweepError3 {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "shared swept volume: {self:?}")
    }
}
impl std::error::Error for SweepError3 {}

#[derive(Clone, Copy, Debug)]
pub struct FaceSweep3 {
    /// Signed volume swept outward from the canonical left cell.
    pub raw: f64,
    pub correction: f64,
    /// Positive endpoint quadrature area divided by a fixed box area.
    pub weight: f64,
}

#[derive(Clone, Copy, Debug)]
pub struct ComponentSweep3 {
    pub anchor: CellId,
    pub count: usize,
    pub raw_compatibility_residual: f64,
    /// Infinity-norm condition estimate of the grounded weighted Laplacian.
    pub grounded_condition_inf: f64,
}

#[derive(Clone, Debug)]
pub struct SharedSweeps3 {
    pub start_epoch: GeometryEpoch3,
    pub end_epoch: GeometryEpoch3,
    predictor: bool,
    faces: BTreeMap<FaceKey3, FaceSweep3>,
    owners: Vec<CellId>,
    pub components: Vec<ComponentSweep3>,
    pub max_raw_relative_defect: f64,
    pub max_corrected_relative_defect: f64,
}

pub struct SweepExchange3<const N: usize> {
    /// The single corrected exchange for every canonical face. Positive leaves the left owner.
    pub faces: BTreeMap<FaceKey3, [f64; N]>,
    pub cell_increments: BTreeMap<CellId, [f64; N]>,
}

#[derive(Clone, Copy)]
struct Edge {
    left: usize,
    right: usize,
    weight: f64,
    key: FaceKey3,
}

fn sum(values: impl IntoIterator<Item = f64>) -> f64 {
    let mut s = Sum::default();
    for v in values {
        s.add(v);
    }
    s.get()
}

// Grounding the smallest persistent ID leaves an SPD graph matrix. Factor a
// dense reference system; both the mesh size and this solver are bounded by
// the small-oracle profile. RHS vectors are not mean-subtracted.
fn cholesky(a: &mut [Vec<f64>]) -> Result<(), SweepError3> {
    for i in 0..a.len() {
        let (previous, rest) = a.split_at_mut(i);
        let row = &mut rest[0];
        for (j, prior) in previous.iter().enumerate() {
            let product = sum(row[..j].iter().zip(&prior[..j]).map(|(x, y)| x * y));
            row[j] = (row[j] - product) / prior[j];
        }
        let diagonal = row[i] - sum(row[..i].iter().map(|x| x * x));
        if !diagonal.is_finite() || diagonal <= 0.0 {
            return Err(SweepError3::SingularGraph);
        }
        row[i] = diagonal.sqrt();
    }
    Ok(())
}

fn solve(factor: &[Vec<f64>], mut v: Vec<f64>) -> Result<Vec<f64>, SweepError3> {
    for (i, row) in factor.iter().enumerate() {
        v[i] = (v[i] - sum(row[..i].iter().zip(&v[..i]).map(|(x, y)| x * y))) / row[i];
    }
    for i in (0..v.len()).rev() {
        v[i] = (v[i]
            - sum(factor[i + 1..]
                .iter()
                .zip(&v[i + 1..])
                .map(|(row, x)| row[i] * x)))
            / factor[i][i];
    }
    if !v.iter().all(|v| v.is_finite()) {
        return Err(SweepError3::NonFinite);
    }
    Ok(v)
}

fn solve_components(
    owners: &[CellId],
    defect: &[f64],
    scales: &[f64],
    edges: &[Edge],
) -> Result<(Vec<f64>, Vec<ComponentSweep3>), SweepError3> {
    let n = owners.len();
    let mut adjacency = vec![Vec::new(); n];
    for edge in edges {
        adjacency[edge.left].push(edge.right);
        adjacency[edge.right].push(edge.left);
    }
    let mut seen = vec![false; n];
    let mut lambda = vec![0.0; n];
    let mut reports = Vec::new();
    for anchor in 0..n {
        if seen[anchor] {
            continue;
        }
        let mut nodes = vec![anchor];
        seen[anchor] = true;
        let mut current = 0;
        while current < nodes.len() {
            for &other in &adjacency[nodes[current]] {
                if !seen[other] {
                    seen[other] = true;
                    nodes.push(other);
                }
            }
            current += 1;
        }
        nodes.sort_unstable();
        let residual = sum(nodes.iter().map(|&i| defect[i]));
        let bound = (128.0 * f64::EPSILON) * sum(nodes.iter().map(|&i| scales[i]));
        if !residual.is_finite() || !bound.is_finite() {
            return Err(SweepError3::NonFinite);
        }
        if residual.abs() > bound {
            return Err(SweepError3::IncompatibleComponent {
                anchor: owners[anchor],
                residual,
                bound,
            });
        }
        let mut cond = 1.0;
        if nodes.len() > 1 {
            let index: BTreeMap<_, _> = nodes[1..]
                .iter()
                .enumerate()
                .map(|(i, &node)| (node, i))
                .collect();
            let m = index.len();
            let mut a = vec![vec![0.0; m]; m];
            for edge in edges {
                let left = index.get(&edge.left).copied();
                let right = index.get(&edge.right).copied();
                if let Some(i) = left {
                    a[i][i] += edge.weight;
                }
                if let Some(i) = right {
                    a[i][i] += edge.weight;
                }
                if let (Some(i), Some(j)) = (left, right) {
                    a[i][j] -= edge.weight;
                    a[j][i] -= edge.weight;
                }
            }
            let norm = a
                .iter()
                .map(|r| sum(r.iter().map(|x| x.abs())))
                .fold(0.0, f64::max);
            cholesky(&mut a)?;
            let x = solve(&a, nodes[1..].iter().map(|&i| defect[i]).collect())?;
            // A grounded graph Laplacian has nonnegative inverse; its maximum
            // row sum follows from one additional solve with an all-ones RHS.
            let row_sums = solve(&a, vec![1.0; m])?;
            cond = norm * row_sums.into_iter().fold(0.0, f64::max);
            if !cond.is_finite() {
                return Err(SweepError3::NonFinite);
            }
            for (&i, value) in nodes[1..].iter().zip(x) {
                lambda[i] = value;
            }
        }
        reports.push(ComponentSweep3 {
            anchor: owners[anchor],
            count: nodes.len(),
            raw_compatibility_residual: residual,
            grounded_condition_inf: cond,
        });
    }
    Ok((lambda, reports))
}

impl SharedSweeps3 {
    /// Old-face Euler quadrature for the provisional state on the rebuilt volumes.
    pub fn euler(
        start: &ValidatedGeometry3,
        old: &MotionRates3,
        end: &ValidatedGeometry3,
        dt: f64,
    ) -> Result<Self, SweepError3> {
        Self::build(start, old, end, None, dt)
    }
    /// Endpoint trapezoid on the canonical face-key union for the final state.
    pub fn heun(
        start: &ValidatedGeometry3,
        old: &MotionRates3,
        end: &ValidatedGeometry3,
        new: &MotionRates3,
        dt: f64,
    ) -> Result<Self, SweepError3> {
        Self::build(start, old, end, Some(new), dt)
    }
    pub fn faces(&self) -> &BTreeMap<FaceKey3, FaceSweep3> {
        &self.faces
    }

    fn build(
        start: &ValidatedGeometry3,
        old: &MotionRates3,
        end: &ValidatedGeometry3,
        new: Option<&MotionRates3>,
        dt: f64,
    ) -> Result<Self, SweepError3> {
        if !dt.is_finite() || dt <= 0.0 {
            return Err(SweepError3::InvalidTimestep);
        }
        if start.domain() != end.domain()
            || !start
                .cells()
                .iter()
                .map(|c| c.generator.id)
                .eq(end.cells().iter().map(|c| c.generator.id))
        {
            return Err(SweepError3::ChangedDomainOrOwners);
        }
        if old.epoch() != start.epoch() || new.is_some_and(|r| r.epoch() != end.epoch()) {
            return Err(GeometryError3::EpochMismatch.into());
        }
        if new.is_some_and(|r| r.trajectory_digest() != old.trajectory_digest()) {
            return Err(SweepError3::ChangedTrajectory);
        }
        let l = start.domain().width.into_iter().fold(0.0, f64::max);
        let area_scale = l * l;
        if !area_scale.is_finite() || area_scale <= 0.0 {
            return Err(SweepError3::NonFinite);
        }
        let mut faces = BTreeMap::<FaceKey3, FaceSweep3>::new();
        let stages = [
            (start, Some(old), if new.is_some() { 0.5 } else { 1.0 }),
            (end, new, 0.5),
        ];
        for (geometry, rates, share) in stages {
            for (i, f) in geometry.faces().iter().enumerate() {
                let entry = faces.entry(f.key).or_insert(FaceSweep3 {
                    raw: 0.0,
                    correction: 0.0,
                    weight: 0.0,
                });
                if let Some(r) = rates {
                    let flux = r.face(geometry.face_ref(i)?)?.volume_flux;
                    if f.right.is_none() && flux != 0.0 {
                        return Err(SweepError3::MovingWall);
                    }
                    entry.raw += dt * (share * flux);
                    entry.weight += share * (f.area / area_scale);
                    if !entry.raw.is_finite() || !entry.weight.is_finite() || entry.weight <= 0.0 {
                        return Err(SweepError3::NonFinite);
                    }
                }
            }
        }
        let owners: Vec<_> = start.cells().iter().map(|c| c.generator.id).collect();
        let index: BTreeMap<_, _> = owners
            .iter()
            .copied()
            .enumerate()
            .map(|(i, id)| (id, i))
            .collect();
        let n = owners.len();
        let mut flux = vec![Sum::default(); n];
        let mut scales: Vec<_> = start
            .cells()
            .iter()
            .zip(end.cells())
            .map(|(a, b)| a.volume + b.volume)
            .collect();
        let volumes: Vec<_> = start
            .cells()
            .iter()
            .zip(end.cells())
            .map(|(a, b)| b.volume - a.volume)
            .collect();
        let cell_scales: Vec<_> = start
            .cells()
            .iter()
            .zip(end.cells())
            .map(|(a, b)| a.volume.max(b.volume))
            .collect();
        let mut edges = Vec::new();
        for (&key, f) in &faces {
            if let FaceKey3::Interior { lo, hi, .. } = key {
                if lo == hi || f.weight == 0.0 {
                    continue;
                }
                let (left, right) = (index[&lo], index[&hi]);
                flux[left].add(f.raw);
                flux[right].add(-f.raw);
                scales[left] += f.raw.abs();
                scales[right] += f.raw.abs();
                edges.push(Edge {
                    key,
                    left,
                    right,
                    weight: f.weight,
                });
            }
        }
        let defect: Vec<_> = volumes.iter().zip(flux).map(|(v, f)| v - f.get()).collect();
        let max_raw_relative_defect = defect
            .iter()
            .zip(&cell_scales)
            .map(|(r, v)| r.abs() / v)
            .fold(0.0, f64::max);
        let (lambda, components) = solve_components(&owners, &defect, &scales, &edges)?;
        let mut corrected_flux = vec![Sum::default(); n];
        for e in edges {
            let row = faces.get_mut(&e.key).expect("edge from face union");
            row.correction = e.weight * (lambda[e.left] - lambda[e.right]);
            let sweep = row.raw + row.correction;
            corrected_flux[e.left].add(sweep);
            corrected_flux[e.right].add(-sweep);
        }
        let mut max_corrected_relative_defect = 0.0_f64;
        for (i, f) in corrected_flux.into_iter().enumerate() {
            let relative = (volumes[i] - f.get()).abs() / cell_scales[i];
            if !relative.is_finite() || relative > 1e-12 {
                return Err(SweepError3::UnclosedCell {
                    owner: owners[i],
                    relative,
                });
            }
            max_corrected_relative_defect = max_corrected_relative_defect.max(relative);
        }
        Ok(Self {
            start_epoch: start.epoch(),
            end_epoch: end.epoch(),
            predictor: new.is_none(),
            faces,
            owners,
            components,
            max_raw_relative_defect,
            max_corrected_relative_defect,
        })
    }

    /// Apply -Ubar*delta once to a supplied integrated physical exchange (or
    /// induction diagnostic) then scatter opposite signs. Densities must be
    /// old only for Euler, old and provisional for Heun.
    pub fn exchanges<const N: usize>(
        &self,
        physical: &BTreeMap<FaceKey3, [f64; N]>,
        old: &BTreeMap<CellId, [f64; N]>,
        predicted: Option<&BTreeMap<CellId, [f64; N]>>,
    ) -> Result<SweepExchange3<N>, SweepError3> {
        let valid = |q: &BTreeMap<CellId, [f64; N]>| {
            q.keys().copied().eq(self.owners.iter().copied())
                && q.values().flatten().all(|x| x.is_finite())
        };
        if !physical.keys().eq(self.faces.keys())
            || !valid(old)
            || predicted.is_some() == self.predictor
            || predicted.is_some_and(|q| !valid(q))
        {
            return Err(SweepError3::ExchangeCatalog);
        }
        let mut sums: BTreeMap<_, _> = self
            .owners
            .iter()
            .map(|&id| (id, [Sum::default(); N]))
            .collect();
        let mut faces = BTreeMap::new();
        for (&key, s) in &self.faces {
            let mut ex = physical[&key];
            match key {
                FaceKey3::Interior { lo, hi, .. } => {
                    if lo != hi {
                        for (k, x) in ex.iter_mut().enumerate() {
                            let mean = if let Some(q) = predicted {
                                0.25 * old[&lo][k]
                                    + 0.25 * old[&hi][k]
                                    + 0.25 * q[&lo][k]
                                    + 0.25 * q[&hi][k]
                            } else {
                                0.5 * old[&lo][k] + 0.5 * old[&hi][k]
                            };
                            *x = (-mean).mul_add(s.correction, *x);
                            sums.get_mut(&lo).unwrap()[k].add(-*x);
                            sums.get_mut(&hi).unwrap()[k].add(*x);
                        }
                    }
                }
                FaceKey3::Boundary { cell, .. } => {
                    for (acc, x) in sums.get_mut(&cell).unwrap().iter_mut().zip(ex) {
                        acc.add(-x);
                    }
                }
            }
            if !ex.iter().all(|x| x.is_finite()) {
                return Err(SweepError3::NonFinite);
            }
            faces.insert(key, ex);
        }
        let cell_increments: BTreeMap<_, _> = sums
            .into_iter()
            .map(|(id, s)| (id, s.map(Sum::get)))
            .collect();
        if !cell_increments.values().flatten().all(|x| x.is_finite()) {
            return Err(SweepError3::NonFinite);
        }
        Ok(SweepExchange3 {
            faces,
            cell_increments,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::three_d::Image3;
    use galaxy_types::EntityId;

    fn id(i: u64) -> CellId {
        CellId::new(EntityId::new(8, i))
    }
    fn edge(left: usize, right: usize, image: i64, weight: f64) -> Edge {
        Edge {
            left,
            right,
            weight,
            key: FaceKey3::Interior {
                lo: id(left as u64),
                hi: id(right as u64),
                hi_image: Image3([image, 0, 0]),
            },
        }
    }

    #[test]
    fn opposite_defects_on_disconnected_components_are_rejected() {
        let owners = [id(0), id(1), id(2), id(3)];
        let edges = [edge(0, 1, 0, 1.0), edge(2, 3, 0, 1.0)];
        let result = solve_components(&owners, &[0.125, 0.0, -0.125, 0.0], &[1.0; 4], &edges);
        assert!(
            matches!(result,Err(SweepError3::IncompatibleComponent{anchor,residual,..}) if anchor==id(0) && residual==0.125)
        );
    }

    #[test]
    fn parallel_image_edges_split_in_ratio_of_face_weights() {
        let owners = [id(0), id(1), id(2)];
        let edges = [edge(0, 1, 0, 1.0), edge(0, 1, 1, 3.0)];
        let (x, report) = solve_components(&owners, &[0.5, -0.5, 0.0], &[1.0; 3], &edges).unwrap();
        assert_eq!(x[0], 0.0);
        assert_eq!(x[2], 0.0);
        assert_eq!(report.len(), 2);
        assert!((x[0] - x[1] - 0.125).abs() < 1.0e-15);
        assert!((3.0 * (x[0] - x[1]) - 0.375).abs() < 1.0e-15);
    }
}
