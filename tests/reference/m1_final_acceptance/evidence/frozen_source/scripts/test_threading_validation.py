import tempfile
from pathlib import Path
import unittest
from run_threading_validation import PHYSICAL_FILES, compare_outputs


class ThreadComparisons(unittest.TestCase):
    def test_changed_or_missing_scientific_output_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory)/'a', Path(directory)/'b'
            a.mkdir()
            b.mkdir()
            for name in PHYSICAL_FILES:
                (a/name).write_text('exact reference')
                (b/name).write_text('exact reference')
            compare_outputs(a, b)
            (b/'history.json').write_text('changed budget')
            with self.assertRaisesRegex(ValueError, 'Changed scientific'):
                compare_outputs(a, b)
            (b/'history.json').unlink()
            with self.assertRaises(FileNotFoundError):
                compare_outputs(a, b)


if __name__ == '__main__':
    unittest.main()
