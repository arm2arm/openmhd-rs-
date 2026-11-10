import json
from pathlib import Path
import tempfile
import unittest

from run_projection_metadata_check import comparison_hashes


class ReportingParity(unittest.TestCase):
    def test_only_the_documented_shift_change_is_permitted(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ('initial.csv','final.csv','history.json'):(root/name).write_text('unchanged')
            summary=dict(completed=True,time=.002,projection_preconditioner_shift=1e-8,projection_screening=1.)
            save=lambda:(root/'summary.json').write_text(json.dumps(summary))
            save();old=comparison_hashes(root,True,1.,False)
            with self.assertRaises(ValueError):comparison_hashes(root,True,1.,True)
            summary['projection_preconditioner_shift']=1.;save()
            self.assertEqual(old,comparison_hashes(root,True,1.,True))
            summary['time']=.001;save()
            self.assertNotEqual(old,comparison_hashes(root,True,1.,True))
            with self.assertRaises(ValueError):comparison_hashes(root,False,1.,True)
            del summary['projection_preconditioner_shift'];save()
            comparison_hashes(root,False,1.,True)
            summary['projection_screening']=.5;save()
            with self.assertRaises(ValueError):comparison_hashes(root,False,1.,True)


if __name__=='__main__':unittest.main()
