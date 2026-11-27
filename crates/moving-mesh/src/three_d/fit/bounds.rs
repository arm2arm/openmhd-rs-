//! Outward binary64 enclosures for decisions on the selected QR branch.
#[derive(Clone, Copy, Debug)]
pub(super) struct Bound(pub f64, pub f64);

fn next(x: f64, up: bool) -> f64 {
    if x.is_nan() || x == if up { f64::INFINITY } else { f64::NEG_INFINITY } {
        return x;
    }
    if x == 0.0 {
        return if up {
            f64::from_bits(1)
        } else {
            -f64::from_bits(1)
        };
    }
    let bits = x.to_bits();
    f64::from_bits(if (x > 0.0) == up { bits + 1 } else { bits - 1 })
}

impl Bound {
    pub fn point(v: f64) -> Self {
        Self(v, v)
    }
    pub fn add(self, b: Self) -> Self {
        Self(next(self.0 + b.0, false), next(self.1 + b.1, true))
    }
    pub fn neg(self) -> Self {
        Self(-self.1, -self.0)
    }
    pub fn sub(self, b: Self) -> Self {
        self.add(b.neg())
    }
    pub fn mul(self, b: Self) -> Self {
        let v = [self.0 * b.0, self.0 * b.1, self.1 * b.0, self.1 * b.1];
        Self(
            next(v.into_iter().fold(f64::INFINITY, f64::min), false),
            next(v.into_iter().fold(f64::NEG_INFINITY, f64::max), true),
        )
    }
    pub fn div(self, b: Self) -> Self {
        if b.0 <= 0.0 && b.1 >= 0.0 {
            return Self(f64::NEG_INFINITY, f64::INFINITY);
        }
        self.mul(Self(next(1.0 / b.1, false), next(1.0 / b.0, true)))
    }
    pub fn abs(self) -> Self {
        Self(
            if self.0 <= 0.0 && self.1 >= 0.0 {
                0.0
            } else {
                self.0.abs().min(self.1.abs())
            },
            self.0.abs().max(self.1.abs()),
        )
    }
    pub fn sqrt(self) -> Self {
        Self(
            next(self.0.max(0.0).sqrt(), false).max(0.0),
            next(self.1.sqrt(), true),
        )
    }
    pub fn max(self, b: Self) -> Self {
        Self(self.0.max(b.0), self.1.max(b.1))
    }
    pub fn norm(x: &[Self]) -> Self {
        // A common power-of-two scale avoids overflow in sum of squares. A
        // scaled sum encloses the real norm for any point in the input box.
        let hi = x.iter().map(|a| a.abs().1).fold(0.0, f64::max);
        if hi == 0.0 || !hi.is_finite() {
            return Self(0.0, hi);
        }
        let scale = Self::point(f64::from_bits((hi.to_bits() & (0x7ffu64 << 52)).max(1)));
        let mut sum = Self::point(0.);
        for value in x {
            let a = value.abs().div(scale);
            sum = sum.add(a.mul(a));
        }
        sum.sqrt().mul(scale)
    }
    pub fn cbrt(v: f64) -> Self {
        let x = v.cbrt();
        let mut lo = x;
        let mut hi = x;
        loop {
            let b = Self::point(lo);
            if b.mul(b).mul(b).1 <= v {
                break;
            }
            lo = next(lo, false);
        }
        loop {
            let b = Self::point(hi);
            if b.mul(b).mul(b).0 >= v {
                break;
            }
            hi = next(hi, true);
        }
        Self(lo, hi)
    }
}
