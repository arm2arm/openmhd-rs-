use crate::{GravityError, Vec3};

pub(crate) fn finite(x: f64, name: &'static str) -> Result<f64, GravityError> {
    if x.is_finite() {
        Ok(x)
    } else {
        Err(GravityError::Nonrepresentable(name))
    }
}

pub(crate) fn positive(x: f64, name: &'static str) -> Result<f64, GravityError> {
    if x.is_finite() && x > 0.0 {
        Ok(x)
    } else {
        Err(GravityError::InvalidValue(name))
    }
}

pub(crate) fn vector(x: Vec3, name: &'static str) -> Result<Vec3, GravityError> {
    for value in x {
        finite(value, name)?;
    }
    Ok(x)
}

pub(crate) fn mul(a: f64, b: f64, name: &'static str) -> Result<f64, GravityError> {
    let result = finite(a * b, name)?;
    if a != 0.0 && b != 0.0 && result == 0.0 {
        return Err(GravityError::Nonrepresentable(name));
    }
    Ok(result)
}

pub(crate) fn div(a: f64, b: f64, name: &'static str) -> Result<f64, GravityError> {
    let result = finite(a / b, name)?;
    if b == 0.0 || (a != 0.0 && result == 0.0) {
        return Err(GravityError::Nonrepresentable(name));
    }
    Ok(result)
}

pub(crate) fn add(a: f64, b: f64, name: &'static str) -> Result<f64, GravityError> {
    finite(a + b, name)
}

pub(crate) fn sub(a: Vec3, b: Vec3) -> Result<Vec3, GravityError> {
    vector([a[0] - b[0], a[1] - b[1], a[2] - b[2]], "displacement")
}

pub(crate) fn scale(x: Vec3, a: f64) -> Result<Vec3, GravityError> {
    Ok([
        mul(x[0], a, "vector product")?,
        mul(x[1], a, "vector product")?,
        mul(x[2], a, "vector product")?,
    ])
}

pub(crate) fn dot(a: Vec3, b: Vec3) -> Result<f64, GravityError> {
    let mut sum = Sum::default();
    for (left, right) in a.into_iter().zip(b) {
        sum.add(mul(left, right, "dot product")?)?;
    }
    sum.value()
}

pub(crate) fn norm(a: Vec3) -> Result<f64, GravityError> {
    finite(dot(a, a)?.sqrt(), "vector norm")
}

pub(crate) fn cross(a: Vec3, b: Vec3) -> Result<Vec3, GravityError> {
    let term = |i, j, k, l| {
        add(
            mul(a[i], b[j], "cross product")?,
            -mul(a[k], b[l], "cross product")?,
            "cross difference",
        )
    };
    Ok([term(1, 2, 2, 1)?, term(2, 0, 0, 2)?, term(0, 1, 1, 0)?])
}

/// Deterministic Neumaier reduction; no residual is subtracted from physics.
#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct Sum {
    sum: f64,
    correction: f64,
}

impl Sum {
    pub(crate) fn add(&mut self, x: f64) -> Result<(), GravityError> {
        finite(x, "sum input")?;
        let t = add(self.sum, x, "sum")?;
        let c = if self.sum.abs() >= x.abs() {
            add(self.sum - t, x, "sum correction")?
        } else {
            add(x - t, self.sum, "sum correction")?
        };
        self.correction = add(self.correction, c, "accumulated correction")?;
        self.sum = t;
        Ok(())
    }

    pub(crate) fn value(self) -> Result<f64, GravityError> {
        add(self.sum, self.correction, "corrected sum")
    }
}

#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct VectorSum([Sum; 3]);

impl VectorSum {
    pub(crate) fn add(&mut self, x: Vec3) -> Result<(), GravityError> {
        for (sum, value) in self.0.iter_mut().zip(x) {
            sum.add(value)?;
        }
        Ok(())
    }

    pub(crate) fn value(self) -> Result<Vec3, GravityError> {
        Ok([self.0[0].value()?, self.0[1].value()?, self.0[2].value()?])
    }
}
