import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import run_projection_cache_benchmark as benchmark


class CacheBenchmark(unittest.TestCase):
    def test_physical_comparison_excludes_only_timing(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ('initial.csv','final.csv','summary.json','history.json','physics.json','timing.json'):
                (root/name).write_text('original')
            before=benchmark.physical_hashes(root)
            (root/'timing.json').write_text('new timing')
            self.assertEqual(before,benchmark.physical_hashes(root))
            (root/'physics.json').write_text('changed physics')
            self.assertNotEqual(before,benchmark.physical_hashes(root))
            (root/'final.csv').unlink()
            with self.assertRaises(ValueError): benchmark.physical_hashes(root)

    def test_baseline_rejects_changed_binary_or_other_numerics(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            names=('crates/mhd-vector-pot/src/projected_rate.rs','crates/mhd-core/src/lib.rs','Cargo.lock')
            for name in names:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('original')
            binary=root/'binary';binary.write_bytes(b'baseline')
            provenance=dict(binary_sha256=benchmark.sha(binary),
                            source_sha256={n:benchmark.sha(root/n) for n in names})
            with patch.object(benchmark,'ROOT',root):
                (root/names[0]).write_text('cache change')
                self.assertEqual(len(benchmark.verify_baseline(binary,provenance)),3)
                (root/names[1]).write_text('another change')
                with self.assertRaises(ValueError): benchmark.verify_baseline(binary,provenance)
                binary.write_bytes(b'wrong')
                with self.assertRaisesRegex(ValueError,'binary checksum'): benchmark.verify_baseline(binary,provenance)


if __name__=='__main__': unittest.main()
