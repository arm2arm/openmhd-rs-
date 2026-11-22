"""Independent affine-fit arithmetic and failure controls."""
from decimal import Decimal
import tempfile
from pathlib import Path
import unittest

from check_shock_curl_audit import check, fit


class IndependentFit(unittest.TestCase):
    def test_known_affine_field_with_unequal_weights(self):
        rows = [dict(dx=x, dy=y, area=w, az=2+3*x-4*y)
                for x, y, w in [(-.5, -.25, .3), (.5, -.25, .7),
                                 (-.5, .25, .2), (.5, .25, .8)]]
        for value, expected in zip(fit(rows), [2, 3, -4]):
            self.assertLess(abs(value-Decimal(expected)), Decimal('1e-60'))

    def test_singular_and_invalid_samples_are_rejected(self):
        rows = [dict(dx=x, dy=0., area=1., az=x) for x in (-1., 0., 1.)]
        with self.assertRaisesRegex(ValueError, 'Singular'):
            fit(rows)
        rows[0]['area'] = -1.
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            fit(rows)

    def test_missing_measurements_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path/'summary.csv').write_text('nx,jitter,field\n')
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                check(path)


if __name__ == '__main__':
    unittest.main()
