//! Same grounded weighted graph as the dense reference, stored once per face.
//! All sums and edge traversals follow the deterministic reference ordering.
use super::{Edge, SweepError3, sum};
use std::collections::BTreeMap;

pub(super) struct GroundedGraph {
    edges: Vec<(usize, usize, f64)>,
    diagonal: Vec<f64>,
    pub(super) norm_inf: f64,
}

impl GroundedGraph {
    pub(super) fn new(index: &BTreeMap<usize, usize>, edges: &[Edge]) -> Result<Self, SweepError3> {
        let m = index.len();
        // Index m represents the zero-potential anchor. Edges in other
        // components have neither endpoint in this component's unknowns.
        let mut rows = Vec::new();
        let mut diagonal = vec![0.; m];
        let mut off_diagonal = vec![0.; m];
        for edge in edges {
            let i = index.get(&edge.left).copied().unwrap_or(m);
            let j = index.get(&edge.right).copied().unwrap_or(m);
            if i == m && j == m {
                continue;
            }
            if !edge.weight.is_finite() || edge.weight <= 0. {
                return Err(SweepError3::SingularGraph);
            }
            for (row, peer) in [(i, j), (j, i)] {
                if row < m {
                    diagonal[row] += edge.weight;
                    if peer < m {
                        off_diagonal[row] += edge.weight;
                    }
                }
            }
            rows.push((i, j, edge.weight));
        }
        if !diagonal.iter().all(|d| d.is_finite() && *d > 0.) {
            return Err(SweepError3::SingularGraph);
        }
        let norm_inf = diagonal
            .iter()
            .zip(&off_diagonal)
            .map(|(d, o)| d + o)
            .fold(0., f64::max);
        if !norm_inf.is_finite() {
            return Err(SweepError3::NonFinite);
        }
        Ok(Self {
            edges: rows,
            diagonal,
            norm_inf,
        })
    }

    fn apply(&self, x: &[f64], out: &mut [f64]) {
        out.fill(0.);
        for &(i, j, w) in &self.edges {
            let flux = w * (x.get(i).copied().unwrap_or(0.) - x.get(j).copied().unwrap_or(0.));
            if let Some(a) = out.get_mut(i) {
                *a += flux;
            }
            if let Some(a) = out.get_mut(j) {
                *a -= flux;
            }
        }
    }

    pub(super) fn solve(&self, rhs: &[f64]) -> Result<Vec<f64>, SweepError3> {
        let mut r = rhs.to_vec();
        let mut x = vec![0.; rhs.len()];
        let inf = |v: &[f64]| v.iter().fold(0.0_f64, |a, b| a.max(b.abs()));
        let dot = |a: &[f64], b: &[f64]| sum(a.iter().zip(b).map(|(s, t)| s * t));
        let scale = inf(rhs);
        if !rhs.iter().all(|v| v.is_finite()) {
            return Err(SweepError3::NonFinite);
        }
        if scale == 0. {
            return Ok(x);
        }
        let mut p: Vec<_> = r.iter().zip(&self.diagonal).map(|(a, d)| a / d).collect();
        let mut rz = dot(&r, &p);
        let mut product = vec![0.; rhs.len()];
        for iteration in 0..(2 * rhs.len()).clamp(64, 4096) {
            self.apply(&p, &mut product);
            let curvature = dot(&p, &product);
            if !curvature.is_finite() || curvature <= 0. || !rz.is_finite() || rz <= 0. {
                return Err(SweepError3::SingularGraph);
            }
            let alpha = rz / curvature;
            for (((x, r), p), q) in x.iter_mut().zip(&mut r).zip(&p).zip(&product) {
                *x += alpha * p;
                *r -= alpha * q;
            }
            // In particular the condition-number witness solves Lx=1. Its
            // attainable residual includes cancellation of O(||L|| ||x||).
            // The swept-volume exchange also has a separate per-cell GCL gate.
            let tolerance = 1e-13 * scale + 32. * f64::EPSILON * self.norm_inf * inf(&x);
            if !tolerance.is_finite() {
                return Err(SweepError3::NonFinite);
            }
            let candidate = inf(&r) <= tolerance;
            if candidate || iteration % 64 == 63 {
                self.apply(&x, &mut product);
                for (q, b) in product.iter_mut().zip(rhs) {
                    *q = b - *q;
                }
                if !product.iter().all(|v| v.is_finite()) {
                    return Err(SweepError3::NonFinite);
                }
                if inf(&product) <= tolerance {
                    return Ok(x);
                }
                if candidate {
                    r.copy_from_slice(&product);
                    for ((p, r), d) in p.iter_mut().zip(&r).zip(&self.diagonal) {
                        *p = r / d;
                    }
                    rz = dot(&r, &p);
                    continue;
                }
            }
            let next_rz = sum(r.iter().zip(&self.diagonal).map(|(v, d)| v * (v / d)));
            let beta = next_rz / rz;
            for ((p, r), d) in p.iter_mut().zip(&r).zip(&self.diagonal) {
                *p = r / d + beta * *p;
            }
            rz = next_rz;
        }
        Err(SweepError3::GraphSolveDidNotConverge)
    }
}
