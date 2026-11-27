//! Free-intercept, point-sampled scalar fits at three-dimensional centroids.
mod bounds;
mod qr;

use super::{Image3, Tensor3, Vec3};
use bounds::Bound as B;
use galaxy_types::CellId;
use qr::{Qr, length};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FitOrder3 {
    Linear,
    Quadratic,
}
impl FitOrder3 {
    pub fn columns(self) -> usize {
        match self {
            Self::Linear => 4,
            Self::Quadratic => 10,
        }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FitError3 {
    InvalidVolume,
    InvalidSample,
    DuplicateSample,
    InsufficientSamples,
    RankDeficient,
    IllConditioned,
    PeriodicFitDecisionUnresolved,
    NonFinite,
    ImageOverflow,
    MissingNeighbour,
    UnsupportedBoundary,
    SampleLimit,
}
impl std::fmt::Display for FitError3 {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}
impl std::error::Error for FitError3 {}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct SampleKey3 {
    pub owner: CellId,
    pub image: Image3,
}
#[derive(Clone, Copy, Debug)]
pub struct StencilSample3 {
    pub key: SampleKey3,
    pub displacement: Vec3,
    /// Required for the one-ring linear fit. The quadratic fit uses 1/r.
    pub face_area: Option<f64>,
}
#[derive(Clone, Debug)]
pub struct FitQuality3 {
    pub samples: usize,
    pub rank: usize,
    pub h: f64,
    pub scales: Vec<f64>,
    pub permutation: Vec<usize>,
    pub positive_diagonal: Vec<f64>,
    pub kappa1_r: f64,
    pub kappa1_bounds: [f64; 2],
    pub pivot_ratio_bounds: [f64; 2],
    pub coefficient_l1: Vec<f64>,
}
#[derive(Clone, Copy, Debug)]
pub struct ScalarJet3 {
    pub value: f64,
    pub gradient: Vec3,
    pub hessian: Option<Tensor3>,
    pub weighted_rms_residual: f64,
}

#[derive(Clone, Debug)]
pub struct PointFit3 {
    pub order: FitOrder3,
    pub quality: FitQuality3,
    samples: Vec<StencilSample3>,
    weights: Vec<f64>,
    map: Vec<Vec<f64>>,
}

fn basis(d: Vec3) -> [f64; 10] {
    let [x, y, z] = d;
    [
        1.,
        x,
        y,
        z,
        x * x * 0.5,
        y * y * 0.5,
        z * z * 0.5,
        x * y,
        x * z,
        y * z,
    ]
}
fn basis_bounds(d: [B; 3]) -> [B; 10] {
    let [x, y, z] = d;
    let half = B::point(0.5);
    [
        B::point(1.),
        x,
        y,
        z,
        x.mul(x).mul(half),
        y.mul(y).mul(half),
        z.mul(z).mul(half),
        x.mul(y),
        x.mul(z),
        y.mul(z),
    ]
}
impl PointFit3 {
    /// Values passed to apply must follow samples() order (full owner/image keys).
    pub fn build(
        order: FitOrder3,
        volume: f64,
        mut samples: Vec<StencilSample3>,
    ) -> Result<Self, FitError3> {
        let p = order.columns();
        let n = samples.len();
        if !volume.is_normal() || volume < 0. {
            return Err(FitError3::InvalidVolume);
        }
        if n <= p {
            return Err(FitError3::InsufficientSamples);
        }
        if n > 256 {
            return Err(FitError3::SampleLimit);
        }
        samples.sort_by_key(|s| s.key);
        if samples.windows(2).any(|w| w[0].key == w[1].key) {
            return Err(FitError3::DuplicateSample);
        }
        let h = volume.cbrt();
        let hb = B::cbrt(volume);
        let mut a = vec![Vec::with_capacity(n); p];
        let mut ab = vec![Vec::with_capacity(n); p];
        let mut weights = Vec::with_capacity(n);
        for sample in &samples {
            let d = sample.displacement;
            let db = d.map(B::point);
            if d.iter().any(|a| !a.is_finite()) || d == [0.; 3] {
                return Err(FitError3::InvalidSample);
            }
            let (w, wb) = match order {
                FitOrder3::Linear => {
                    let a = sample.face_area.ok_or(FitError3::InvalidSample)?;
                    (a, B::point(a))
                }
                FitOrder3::Quadratic => (1. / length(&d), B::point(1.).div(B::norm(&db))),
            };
            if !w.is_finite() || w <= 0. {
                return Err(FitError3::InvalidSample);
            }
            let sw = w.sqrt();
            let sb = wb.sqrt();
            weights.push(sw);
            let x = basis(d.map(|v| v / h));
            let xb = basis_bounds(db.map(|v| v.div(hb)));
            for j in 0..p {
                a[j].push(sw * x[j]);
                ab[j].push(sb.mul(xb[j]));
            }
        }
        let qr = Qr::build(a, ab, &weights)?;
        let mut map = qr.map;
        for (i, row) in map.iter_mut().enumerate() {
            let scale = match i {
                0 => 1.,
                1..=3 => h,
                _ => h * h,
            };
            for x in row.iter_mut() {
                *x /= scale;
            }
            if row.iter().any(|x| !x.is_finite()) {
                return Err(FitError3::NonFinite);
            }
        }
        let quality = FitQuality3 {
            samples: n,
            rank: p,
            h,
            scales: qr.scales,
            permutation: qr.permutation,
            positive_diagonal: qr.diagonal,
            kappa1_r: qr.condition,
            kappa1_bounds: qr.condition_bounds,
            pivot_ratio_bounds: qr.pivot_ratio_bounds,
            coefficient_l1: map
                .iter()
                .map(|r| r.iter().map(|x| x.abs()).sum())
                .collect(),
        };
        Ok(Self {
            order,
            quality,
            samples,
            weights,
            map,
        })
    }

    pub fn samples(&self) -> &[StencilSample3] {
        &self.samples
    }
    /// Rows are in physical units. They act on sample-minus-baseline values.
    pub fn coefficients(&self) -> &[Vec<f64>] {
        &self.map
    }
    pub fn apply(&self, y: &[f64]) -> Result<ScalarJet3, FitError3> {
        if y.len() != self.samples.len() || y.iter().any(|x| !x.is_finite()) {
            return Err(FitError3::InvalidSample);
        }
        let base = y[0];
        let mut c = [0.; 10];
        for (v, row) in c.iter_mut().zip(&self.map) {
            *v = row.iter().zip(y).map(|(a, q)| a * (q - base)).sum();
        }
        let mut residual = 0.;
        let mut sum_w = 0.;
        for ((sample, &q), &sw) in self.samples.iter().zip(y).zip(&self.weights) {
            let x = basis(sample.displacement);
            let r = (q - base) - x.iter().zip(c).map(|(x, v)| x * v).sum::<f64>();
            residual += (sw * r).powi(2);
            sum_w += sw * sw;
        }
        let value = base + c[0];
        let rms = (residual / sum_w).sqrt();
        if !value.is_finite() || !rms.is_finite() || c.iter().any(|x| !x.is_finite()) {
            return Err(FitError3::NonFinite);
        }
        Ok(ScalarJet3 {
            value,
            gradient: [c[1], c[2], c[3]],
            hessian: (self.order == FitOrder3::Quadratic).then_some([
                [c[4], c[7], c[8]],
                [c[7], c[5], c[9]],
                [c[8], c[9], c[6]],
            ]),
            weighted_rms_residual: rms,
        })
    }
}

impl SampleKey3 {
    pub fn from_words(namespace: u64, counter: u64, image: Image3) -> Self {
        Self {
            owner: CellId::new(galaxy_types::EntityId::new(namespace, counter)),
            image,
        }
    }
}
