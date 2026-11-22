//! Minoshima–Miyoshi (2021), Eqs. (9)–(13), shock-only correction.
//! The multidimensional velocity stencil is supplied by the caller.

#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct ShockSensor {
    pub normal_difference: f64,
    pub transverse_difference: f64,
}

impl ShockSensor {
    pub fn factor(self, fast_speed: f64) -> Result<f64, String> {
        if !fast_speed.is_finite()
            || fast_speed <= 0.
            || !self.normal_difference.is_finite()
            || !self.transverse_difference.is_finite()
        {
            return Err("invalid shock sensor or fast speed".into());
        }
        let numerator = fast_speed - self.normal_difference.min(0.);
        let denominator = fast_speed - self.transverse_difference.min(0.);
        if !numerator.is_finite() || !denominator.is_finite() {
            return Err("shock sensor overflow".into());
        }
        let ratio = (numerator / denominator).min(1.);
        Ok((ratio * ratio) * (ratio * ratio))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn sensor_has_published_limits_and_no_activation_for_normal_compression() {
        for (normal_difference, transverse_difference, expected) in [
            (0., 0., 1.),
            (-2., 0., 1.),
            (-3., -2., 1.),
            (2., 1., 1.),
            (0., -1., 1. / 16.),
            (-1., -3., 1. / 16.),
        ] {
            let s = ShockSensor {
                normal_difference,
                transverse_difference,
            };
            assert_eq!(s.factor(1.).unwrap(), expected);
            assert_eq!(
                ShockSensor {
                    normal_difference: 4. * normal_difference,
                    transverse_difference: 4. * transverse_difference
                }
                .factor(4.)
                .unwrap(),
                expected
            );
        }
        assert!(ShockSensor::default().factor(0.).is_err());
        assert!(
            ShockSensor {
                normal_difference: f64::NAN,
                ..ShockSensor::default()
            }
            .factor(1.)
            .is_err()
        );
    }
}
