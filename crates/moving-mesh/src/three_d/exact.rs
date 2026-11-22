//! Independently written bounded signed dyadic arithmetic for predicates.
//! A value is sign * little-endian integer * 2^exponent. No float predicate
//! tolerance, epsilon snapping, random perturbation or third-party code.
use super::GeometryError3;
use std::cmp::Ordering;

const MAX_WORDS: usize = 1024;
type Result<T> = std::result::Result<T, GeometryError3>;

#[derive(Clone, Debug)]
pub(crate) struct D {
    sign: i8,
    words: Vec<u32>,
    exponent: i32,
}

impl D {
    pub fn zero() -> Self { Self { sign: 0, words: Vec::new(), exponent: 0 } }
    pub fn one() -> Self { Self::from_f64(1.0) }

    /// Caller validates finite input first; no arithmetic rounding occurs here.
    pub fn from_f64(x: f64) -> Self {
        let bits = x.to_bits();
        let e = ((bits >> 52) & 2047) as i32;
        let fraction = bits & ((1_u64 << 52) - 1);
        let significand = if e == 0 { fraction } else { fraction | (1_u64 << 52) };
        if significand == 0 { return Self::zero(); }
        let mut result = Self {
            sign: if bits >> 63 == 0 { 1 } else { -1 },
            words: vec![significand as u32, (significand >> 32) as u32],
            exponent: if e == 0 { -1074 } else { e - 1023 - 52 },
        };
        result.normalize();
        result
    }

    fn normalize(&mut self) {
        while self.words.last() == Some(&0) { self.words.pop(); }
        if self.words.is_empty() { *self = Self::zero(); return; }
        let whole = self.words.iter().take_while(|v| **v == 0).count();
        if whole != 0 {
            self.words.drain(..whole);
            self.exponent += (32 * whole) as i32;
        }
        let shift = self.words[0].trailing_zeros();
        if shift != 0 {
            for i in 0..self.words.len() {
                let upper = self.words.get(i + 1).copied().unwrap_or(0);
                self.words[i] = (self.words[i] >> shift) | (upper << (32 - shift));
            }
            self.exponent += shift as i32;
            while self.words.last() == Some(&0) { self.words.pop(); }
        }
    }

    pub fn sign(&self) -> i8 { self.sign }
    pub fn neg(&self) -> Self { let mut r = self.clone(); r.sign = -r.sign; r }
    pub fn half(&self) -> Self { let mut r = self.clone(); r.exponent -= 1; r }

    fn shifted(&self, exponent: i32) -> Result<Vec<u32>> {
        if self.sign == 0 { return Ok(Vec::new()); }
        let bits = usize::try_from(self.exponent - exponent)
            .map_err(|_| GeometryError3::ResourceLimit("dyadic exponent alignment"))?;
        let whole = bits / 32;
        let shift = bits % 32;
        let length = self.words.len() + whole + usize::from(shift != 0);
        if length > MAX_WORDS { return Err(GeometryError3::ResourceLimit("dyadic words")); }
        let mut result = vec![0; length];
        for (i, value) in self.words.iter().enumerate() {
            result[i + whole] |= *value << shift;
            if shift != 0 { result[i + whole + 1] |= *value >> (32 - shift); }
        }
        while result.last() == Some(&0) { result.pop(); }
        Ok(result)
    }

    pub fn add(&self, other: &Self) -> Result<Self> {
        if self.sign == 0 { return Ok(other.clone()); }
        if other.sign == 0 { return Ok(self.clone()); }
        let exponent = self.exponent.min(other.exponent);
        let a = self.shifted(exponent)?;
        let b = other.shifted(exponent)?;
        let magnitude = a.len().cmp(&b.len()).then_with(|| a.iter().rev().cmp(b.iter().rev()));
        if self.sign != other.sign && magnitude == Ordering::Equal { return Ok(Self::zero()); }
        let (large, small, sign) = if magnitude == Ordering::Less {
            (&b, &a, other.sign)
        } else { (&a, &b, self.sign) };
        let mut words = Vec::with_capacity(large.len() + 1);
        if self.sign == other.sign {
            let mut carry = 0_u64;
            for i in 0..large.len() {
                let sum = u64::from(large[i]) + u64::from(small.get(i).copied().unwrap_or(0)) + carry;
                words.push(sum as u32);
                carry = sum >> 32;
            }
            if carry != 0 { words.push(carry as u32); }
        } else {
            let mut borrow = 0_i64;
            for i in 0..large.len() {
                let difference = i64::from(large[i]) - i64::from(small.get(i).copied().unwrap_or(0)) - borrow;
                words.push(difference as u32);
                borrow = i64::from(difference < 0);
            }
        }
        if words.len() > MAX_WORDS { return Err(GeometryError3::ResourceLimit("dyadic words")); }
        let mut result = Self { sign, words, exponent };
        result.normalize();
        Ok(result)
    }

    pub fn sub(&self, other: &Self) -> Result<Self> { self.add(&other.neg()) }

    pub fn mul(&self, other: &Self) -> Result<Self> {
        if self.sign == 0 || other.sign == 0 { return Ok(Self::zero()); }
        if self.words.len() + other.words.len() > MAX_WORDS {
            return Err(GeometryError3::ResourceLimit("dyadic product words"));
        }
        let mut words = vec![0; self.words.len() + other.words.len()];
        for (i, a) in self.words.iter().enumerate() {
            let mut carry = 0_u64;
            for (j, b) in other.words.iter().enumerate() {
                let product = u64::from(*a) * u64::from(*b) + u64::from(words[i + j]) + carry;
                words[i + j] = product as u32;
                carry = product >> 32;
            }
            words[i + other.words.len()] = carry as u32;
        }
        let mut result = Self { sign: self.sign * other.sign, words,
                                exponent: self.exponent + other.exponent };
        result.normalize();
        Ok(result)
    }

    pub fn cmp(&self, other: &Self) -> Result<Ordering> { Ok(self.sub(other)?.sign.cmp(&0)) }

    fn leading(&self) -> (f64, i32) {
        let bits = 32 * (self.words.len() - 1) + (32 - self.words.last().unwrap().leading_zeros()) as usize;
        let keep = bits.min(53);
        let shift = bits - keep;
        let mut value = 0_u64;
        for k in (shift..bits).rev() {
            value = (value << 1) | u64::from((self.words[k / 32] >> (k % 32)) & 1);
        }
        (value as f64, self.exponent + shift as i32)
    }

    /// Floating output only: top-53-bit truncation on each operand, ordinary
    /// division and binary scaling. No correctly-rounded-ratio or propagated
    /// error-enclosure claim, particularly in subnormal/extreme-scale regimes.
    pub fn ratio(&self, denominator: &Self) -> Result<f64> {
        if denominator.sign == 0 { return Err(GeometryError3::SingularIntersection); }
        if self.sign == 0 { return Ok(0.0); }
        let (a, ae) = self.leading();
        let (b, be) = denominator.leading();
        let result = f64::from(self.sign * denominator.sign) * (a / b) * 2.0_f64.powi(ae - be);
        if !result.is_finite() || result == 0.0 {
            return Err(GeometryError3::Unrepresentable("exact rational output"));
        }
        Ok(result)
    }
}

pub(crate) fn dot(a: &[D; 3], b: &[D; 3]) -> Result<D> {
    a[0].mul(&b[0])?.add(&a[1].mul(&b[1])?)?.add(&a[2].mul(&b[2])?)
}

pub(crate) fn det(rows: &[[D; 3]; 3]) -> Result<D> {
    let minor = |a: usize, b: usize| rows[1][a].mul(&rows[2][b])?.sub(&rows[1][b].mul(&rows[2][a])?);
    rows[0][0].mul(&minor(1, 2)?)?.sub(&rows[0][1].mul(&minor(0, 2)?)?)?
        .add(&rows[0][2].mul(&minor(0, 1)?)?)
}

#[derive(Clone, Debug)]
pub(crate) struct Point {
    pub numerator: [D; 3],
    pub denominator: D,
}

impl Point {
    pub fn same(&self, other: &Self) -> Result<bool> {
        for a in 0..3 {
            if self.numerator[a].mul(&other.denominator)?.cmp(&other.numerator[a].mul(&self.denominator)?)? != Ordering::Equal {
                return Ok(false);
            }
        }
        Ok(true)
    }

    pub fn compare_axis(&self, other: &Self, axis: usize) -> Result<Ordering> {
        self.numerator[axis].mul(&other.denominator)?.cmp(&other.numerator[axis].mul(&self.denominator)?)
    }

    pub fn translated(&self, offset: &[D; 3]) -> Result<Self> {
        let mut numerator = self.numerator.clone();
        for a in 0..3 { numerator[a] = numerator[a].add(&offset[a].mul(&self.denominator)?)?; }
        Ok(Self { numerator, denominator: self.denominator.clone() })
    }

    pub fn scaled_f64(&self, length: &D) -> Result<[f64; 3]> {
        let denominator = self.denominator.mul(length)?;
        Ok([self.numerator[0].ratio(&denominator)?, self.numerator[1].ratio(&denominator)?,
            self.numerator[2].ratio(&denominator)?])
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_cancellation_retains_below_binary64_ulp_terms() {
        // Exact integer identity (2^53 + 1) - 2^53 = 1; binary64 addition
        // alone would lose the 1. This tests the predicate representation.
        let large = D::from_f64(9_007_199_254_740_992.0);
        let result = large.add(&D::one()).unwrap().sub(&large).unwrap();
        assert_eq!(result.cmp(&D::one()).unwrap(), Ordering::Equal);
        assert_eq!(result.sub(&D::one()).unwrap().sign(), 0);
    }

    #[test]
    fn dyadic_subnormal_and_signed_zero_decode_exactly() {
        let tiny = D::from_f64(f64::from_bits(1));
        let twice = D::from_f64(f64::from_bits(2));
        assert_eq!(tiny.add(&tiny).unwrap().cmp(&twice).unwrap(), Ordering::Equal);
        assert_eq!(tiny.add(&tiny.neg()).unwrap().sign(), 0);
        let negative_tiny = D::from_f64(f64::from_bits((1_u64 << 63) | 1));
        assert_eq!(negative_tiny.sign(), -1);
        assert_eq!(negative_tiny.cmp(&tiny.neg()).unwrap(), Ordering::Equal);
        assert_eq!(D::from_f64(-1.5).cmp(&D::from_f64(1.5).neg()).unwrap(), Ordering::Equal);
        assert_eq!(D::from_f64(-0.0).sign(), 0);
        assert_eq!(D::from_f64(0.0).sign(), 0);
    }

    #[test]
    fn integer_product_carry_matches_binomial_identity() {
        // a=2^32-1, so (a+1)^2-a^2-2a-1 = 0 exactly.
        let a = D::from_f64(4_294_967_295.0);
        let b = D::from_f64(4_294_967_296.0);
        let residual = b.mul(&b).unwrap().sub(&a.mul(&a).unwrap()).unwrap()
            .sub(&a.add(&a).unwrap()).unwrap().sub(&D::one()).unwrap();
        assert_eq!(residual.sign(), 0);

        // Construct 2^64-1 by exact operations, never a rounded f64 literal.
        // Its two full limbs force overlapping product rows and carry addition.
        let two64 = b.mul(&b).unwrap();
        let multi = two64.sub(&D::one()).unwrap();
        assert_eq!(multi.exponent, 0);
        assert_eq!(multi.words, vec![u32::MAX; 2]);
        let square = multi.mul(&multi).unwrap();
        // Independent power-of-two decodes give the binomial reference
        // (2^64-1)^2 = 2^128-2^65+1, without another multi-limb product.
        let two128 = D::from_f64(f64::from_bits((1023_u64 + 128) << 52));
        let two65 = D::from_f64(f64::from_bits((1023_u64 + 65) << 52));
        let expected = two128.sub(&two65).unwrap().add(&D::one()).unwrap();
        assert_eq!(square.cmp(&expected).unwrap(), Ordering::Equal);
        assert_eq!(square.exponent, 0);
        assert_eq!(square.words, vec![1, 0, u32::MAX - 1, u32::MAX]);

        // Borrow through four words: 2^128-1 = sum_{k=0}^3 (2^32-1)*2^(32*k).
        let borrowed = two128.sub(&D::one()).unwrap();
        assert_eq!(borrowed.exponent, 0);
        assert_eq!(borrowed.words, vec![u32::MAX; 4]);
        // A half-bit alignment yields 2^128-1/2 = (2^129-1)*2^-1;
        // adding the remaining half then carries back to the power of two.
        let aligned = borrowed.add(&D::one().half()).unwrap();
        assert_eq!(aligned.exponent, -1);
        assert_eq!(aligned.words, vec![u32::MAX, u32::MAX, u32::MAX, u32::MAX, 1]);
        assert_eq!(aligned.add(&D::one().half()).unwrap().cmp(&two128).unwrap(), Ordering::Equal);
    }

    #[test]
    fn determinant_orientation_and_exact_coplanar_contact() {
        let rows = [[1.0, 1.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]].map(|r| r.map(D::from_f64));
        assert_eq!(det(&rows).unwrap().cmp(&D::one()).unwrap(), Ordering::Equal);
        let swapped = [rows[1].clone(), rows[0].clone(), rows[2].clone()];
        assert_eq!(det(&swapped).unwrap().sign(), -1);
        let flat = [rows[0].clone(), rows[1].clone(), rows[0].clone()];
        assert_eq!(det(&flat).unwrap().sign(), 0);
    }
}
