//! Factor Ahat P = QR in sample-key order. Only the small triangular system
//! is inverted. The interval calculation follows the recorded pivot choices.
use super::{FitError3, bounds::Bound as B};

pub(super) fn length(x: &[f64]) -> f64 {
    let (mut scale, mut sum) = (0.0, 1.0);
    for &v in x {
        let a = v.abs();
        if a > scale {
            sum = 1.0 + sum * (scale / a).powi(2);
            scale = a;
        } else if a > 0.0 {
            sum += (a / scale).powi(2);
        }
    }
    scale * sum.sqrt()
}
pub(super) struct Qr {
    pub permutation: Vec<usize>,
    pub diagonal: Vec<f64>,
    pub condition: f64,
    pub condition_bounds: [f64; 2],
    pub pivot_ratio_bounds: [f64; 2],
    pub scales: Vec<f64>,
    pub map: Vec<Vec<f64>>,
}

impl Qr {
    pub fn build(
        mut a: Vec<Vec<f64>>,
        mut ab: Vec<Vec<B>>,
        weights: &[f64],
    ) -> Result<Self, FitError3> {
        let p = a.len();
        let n = weights.len();
        let scales: Vec<_> = a.iter().map(|c| length(c)).collect();
        let mut permutation: Vec<_> = (0..p).collect();
        let mut tau = vec![0.; p];
        for j in 0..p {
            if scales[j] == 0. {
                return Err(FitError3::RankDeficient);
            }
            if !scales[j].is_finite() {
                return Err(FitError3::NonFinite);
            }
            let s = B::norm(&ab[j]);
            if s.0 <= 0.0 {
                return Err(FitError3::PeriodicFitDecisionUnresolved);
            }
            for (x, b) in a[j].iter_mut().zip(&mut ab[j]) {
                *x /= scales[j];
                *b = b.div(s);
            }
        }
        for k in 0..p {
            let mut best = k;
            let mut highest = length(&a[k][k..]);
            for j in k + 1..p {
                let score = length(&a[j][k..]);
                if score > highest || (score == highest && permutation[j] < permutation[best]) {
                    best = j;
                    highest = score;
                }
            }
            permutation.swap(k, best);
            a.swap(k, best);
            ab.swap(k, best);
            let previous_lower = (0..k).map(|i| ab[i][i].abs().0).fold(0., f64::max);
            let (left, right) = a.split_at_mut(k + 1);
            let v = &mut left[k];
            let (lb, rb) = ab.split_at_mut(k + 1);
            let vb = &mut lb[k];
            let normb = B::norm(&vb[k..]);
            if k > 0 && normb.1 < 1e-10 * previous_lower {
                return Err(FitError3::RankDeficient);
            }
            if highest == 0.0 || normb.0 <= 0.0 || !normb.1.is_finite() {
                return Err(FitError3::PeriodicFitDecisionUnresolved);
            }
            let negative = v[k] >= 0.;
            let beta = if negative { -highest } else { highest };
            let beta_b = if negative { normb.neg() } else { normb };
            let denom = v[k] - beta;
            let denom_b = vb[k].sub(beta_b);
            tau[k] = 1. - v[k] / beta;
            let t = B::point(1.).sub(vb[k].div(beta_b));
            for (x, b) in v[k + 1..].iter_mut().zip(&mut vb[k + 1..]) {
                *x /= denom;
                *b = b.div(denom_b);
            }
            v[k] = beta;
            vb[k] = beta_b;
            for (col, cb) in right.iter_mut().zip(rb.iter_mut()) {
                let mut z = col[k];
                let mut zb = cb[k];
                for i in k + 1..n {
                    z += v[i] * col[i];
                    zb = zb.add(vb[i].mul(cb[i]));
                }
                z *= tau[k];
                zb = zb.mul(t);
                col[k] -= z;
                cb[k] = cb[k].sub(zb);
                for i in k + 1..n {
                    col[i] -= v[i] * z;
                    cb[i] = cb[i].sub(vb[i].mul(zb));
                }
            }
        }
        let mut r = vec![vec![0.; p]; p];
        let mut rb = vec![vec![B::point(0.); p]; p];
        let mut diagonal = Vec::with_capacity(p);
        let mut mind = B(f64::INFINITY, f64::INFINITY);
        let mut maxd = B::point(0.);
        for i in 0..p {
            let sign = a[i][i].signum();
            diagonal.push(a[i][i].abs());
            let di = ab[i][i].abs();
            mind = B(mind.0.min(di.0), mind.1.min(di.1));
            maxd = maxd.max(di);
            for j in i..p {
                r[i][j] = sign * a[j][i];
                rb[i][j] = if sign < 0.0 { ab[j][i].neg() } else { ab[j][i] };
            }
        }
        let ratio = mind.div(maxd);
        if ratio.1 < 1e-10 {
            return Err(FitError3::RankDeficient);
        }
        if !ratio.0.is_finite() || ratio.0 < 1e-10 {
            return Err(FitError3::PeriodicFitDecisionUnresolved);
        }
        let mut inv = vec![vec![0.; p]; p];
        let mut ib = vec![vec![B::point(0.); p]; p];
        for j in 0..p {
            for i in (0..=j).rev() {
                let rhs = if i == j { 1. } else { 0. };
                let mut sum = 0.;
                let mut sb = B::point(0.);
                for k in i + 1..=j {
                    sum += r[i][k] * inv[k][j];
                    sb = sb.add(rb[i][k].mul(ib[k][j]));
                }
                inv[i][j] = (rhs - sum) / r[i][i];
                ib[i][j] = B::point(rhs).sub(sb).div(rb[i][i]);
            }
        }
        let norm1 = |m: &[Vec<f64>]| {
            (0..p)
                .map(|j| (0..=j).map(|i| m[i][j].abs()).sum::<f64>())
                .fold(0., f64::max)
        };
        let normb = |m: &[Vec<B>]| {
            (0..p)
                .map(|j| (0..=j).fold(B::point(0.), |s, i| s.add(m[i][j].abs())))
                .fold(B::point(0.), B::max)
        };
        let condition = norm1(&r) * norm1(&inv);
        let cb = normb(&rb).mul(normb(&ib));
        if cb.0 > 1e8 {
            return Err(FitError3::IllConditioned);
        }
        if !(cb.1 <= 1e8 && condition.is_finite()) {
            return Err(FitError3::PeriodicFitDecisionUnresolved);
        }
        // Form each row of the pseudoinverse by applying Q to R^-T e_j.
        let mut map = vec![vec![0.; n]; p];
        for k in 0..p {
            let j = permutation[k];
            let row = &mut map[j];
            for i in k..p {
                row[i] = inv[k][i] * a[i][i].signum() / scales[j];
            }
            for l in (0..p).rev() {
                let mut z = row[l];
                for (&v, &x) in a[l][l + 1..].iter().zip(&row[l + 1..]) {
                    z += v * x;
                }
                z *= tau[l];
                row[l] -= z;
                for (&v, x) in a[l][l + 1..].iter().zip(&mut row[l + 1..]) {
                    *x -= v * z;
                }
            }
            for (x, w) in row.iter_mut().zip(weights) {
                *x *= w;
            }
        }
        if map.iter().flatten().any(|x| !x.is_finite()) {
            return Err(FitError3::NonFinite);
        }
        Ok(Self {
            permutation,
            diagonal,
            condition,
            condition_bounds: [cb.0, cb.1],
            pivot_ratio_bounds: [ratio.0, ratio.1],
            scales,
            map,
        })
    }
}
