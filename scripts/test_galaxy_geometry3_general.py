"""Small deterministic general-geometry controls; every method runs on REANA."""
from fractions import Fraction as Q
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

import galaxy_geometry3_general_bridge as bridge
import galaxy_geometry3_general_compare as compare
import galaxy_geometry3_general_fixtures as fixtures
import galaxy_geometry3_general_reference as reference
import galaxy_geometry3_reference as ieee
import run_geometry3_general as tasks


def one_cell():
    value=fixtures.build('cospherical_cube')
    value['case']['name']='single_cell_reference_control'
    value['generators']=value['generators'][:1]
    return fixtures.encode(value)


class GeneralGeometryTests(unittest.TestCase):
    def test_integer_intersection_is_exact_and_oriented(self):
        planes=[dict(n=(2,0,0),h=1),dict(n=(0,3,0),h=1),dict(n=(0,0,-5),h=-1)]
        numerator,denominator=reference.intersection(planes,(0,1,2))
        self.assertEqual(tuple(Q(x,denominator) for x in numerator),(Q(1,2),Q(1,3),Q(1,5)))

    def test_singular_support_has_no_false_vertex(self):
        planes=[dict(n=(1,0,0),h=1),dict(n=(2,0,0),h=2),dict(n=(0,1,0),h=1)]
        self.assertIsNone(reference.intersection(planes,(0,1,2)))

    def test_dyadic_enclosures_are_outward(self):
        for value in (Q(1,3),Q(-1,3),Q(0),Q(2**100)):
            lo,hi=map(Q,reference.enclosure(value))
            self.assertLessEqual(lo,value);self.assertGreaterEqual(hi,value)
            self.assertLessEqual(hi-lo,Q(1,2**160))

    def test_radical_enclosures_certify_squares(self):
        for value in (Q(0),Q(1),Q(2),Q(1,3),Q(1,10**40)):
            lo,hi=map(Q,reference.sqrt_enclosure(value))
            self.assertGreaterEqual(lo,0);self.assertLessEqual(lo*lo,value);self.assertGreaterEqual(hi*hi,value)
            self.assertLessEqual(hi-lo,Q(1,2**160))

    def test_one_cell_volume_centroid_tensor_and_six_faces(self):
        result=reference.evaluate(one_cell());self.assertTrue(result['exact_volume_closure'])
        self.assertEqual(len(result['cells']),1);self.assertEqual(len(result['faces']),3)
        cell=result['cells'][0]
        self.assertEqual(list(map(Q,cell['volume'])),[Q(1),Q(1)])
        for a in range(3):
            self.assertEqual(list(map(Q,cell['centroid'][a])),[Q(0),Q(0)])
            for b in range(3):
                lo,hi=map(Q,cell['central_moment'][a][b]);expected=Q(1,12) if a==b else Q(0)
                self.assertLessEqual(lo,expected);self.assertGreaterEqual(hi,expected)
        self.assertEqual(cell['certificate']['faces'],6)

    def test_cospherical_cube_exact_volumes_and_reciprocal_faces(self):
        result=reference.evaluate(fixtures.encode(fixtures.build('cospherical_cube')))
        self.assertEqual(len(result['cells']),8);self.assertEqual(len(result['faces']),24)
        for cell in result['cells']:
            self.assertEqual(list(map(Q,cell['volume'])),[Q(1,8),Q(1,8)])
            self.assertTrue(cell['certificate']['closed_oriented_surface'])

    def test_coplanar_generators_still_make_full_dimensional_periodic_cells(self):
        result=reference.evaluate(fixtures.encode(fixtures.build('coplanar')))
        self.assertEqual(len(result['cells']),9)
        for c in result['cells']:
            self.assertGreater(Q(c['volume'][0]),0)
            self.assertEqual(c['certificate']['vertices']-c['certificate']['edges']+c['certificate']['faces'],2)

    def test_missing_qhull_corner_cannot_become_reference_success(self):
        class Incomplete:
            dual_facets=[[0,2,4],[0,2,5],[0,3,4]]
        planes=reference.constraints('a',{'a':(0,0,0)},(2,2,2),{'a':(0,0,0)})
        with mock.patch('scipy.spatial.HalfspaceIntersection',return_value=Incomplete()):
            with self.assertRaisesRegex(ValueError,'Full-dimensional|closed|sphere'):
                reference.certified_surface(planes, 2, reference.proposed_vertices(planes, 2))
            _, _, certificate = reference.certify_cell(planes, 2)
            self.assertEqual(certificate['vertex_enumeration'], 'exact-edge-walk')
            self.assertEqual((certificate['vertices'], certificate['faces']), (8, 6))

    def test_all_registered_jitter_bounds_counts_and_unique_ids(self):
        for n in (4,6,8):
            value=fixtures.build('jitter'+str(n));self.assertEqual(len(value['generators']),n**3)
            self.assertEqual(len({g['id'] for g in value['generators']}),n**3)
            for g in value['generators']:
                for word in g['position_bits']:
                    x=ieee.exact_binary64(int(word,16));self.assertGreater(x,0);self.assertLess(x,1)
                    nearest=(x*n).numerator//(x*n).denominator
                    self.assertLessEqual(abs(x*n-Q(2*nearest+1,2)),Q(3,20)+Q(1,2**48))

    def test_reverse_and_shuffle_preserve_actual_words_and_ids(self):
        base=fixtures.build('jitter4');expected={g['id']:g for g in base['generators']}
        for variant in ('reverse','shuffle','repeat'):
            changed=fixtures.build('jitter4',variant)
            self.assertEqual({g['id']:g for g in changed['generators']},expected)
            if variant!='repeat':self.assertNotEqual(changed['generators'],base['generators'])

    def test_seam_and_multiple_windings_preserve_uniform_physical_translation(self):
        base={g['id']:g for g in fixtures.build('jitter4')['generators']}
        for variant,delta in [('seam',(Q(371,1000),-Q(219,1000),Q(443,1000))),
                              ('windings',(Q(2371,1000),-Q(3219,1000),Q(4443,1000)))]:
            value=fixtures.build('jitter4',variant)
            for g in value['generators']:
                for a in range(3):
                    x=ieee.exact_binary64(int(g['position_bits'][a],16))+g['winding'][a]
                    old=ieee.exact_binary64(int(base[g['id']]['position_bits'][a],16))
                    self.assertLessEqual(abs(x-old-delta[a]),Q(1,2**51))

    def test_general_bridge_retains_nonzero_trajectory_windings(self):
        value=fixtures.build('jitter4','windings');raw=fixtures.encode(value)
        self.assertEqual(bridge.parse_input(raw),value)
        converted=bridge.convert_input(raw)
        for g in value['generators']:
            self.assertIn(('generator '+g['id']+' ').encode(),converted)
            self.assertTrue(any(g['winding']))

    def test_general_bridge_rejects_duplicate_ids(self):
        value=fixtures.build('cospherical_cube');value['generators'][1]['id']=value['generators'][0]['id']
        with self.assertRaisesRegex(ValueError,'Duplicate generator'):
            bridge.parse_input(fixtures.encode(value))

    def test_general_bridge_rejects_wrong_registration(self):
        value=fixtures.build('cospherical_cube');value['design_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Registered input'):
            bridge.parse_input(fixtures.encode(value))

    def test_comparison_enclosure_error_includes_reference_uncertainty(self):
        self.assertEqual(compare.error(Q(0),['-1/10','1/5']),Q(1,5))
        self.assertEqual(compare.error(Q(3),['1','2']),Q(2))
        with self.assertRaisesRegex(ValueError,'Ordered'):
            compare.error(Q(0),['2','1'])

    def test_canonical_trajectory_key_is_equivariant_under_seam_crossings(self):
        zero={'a':(0,0,0),'b':(0,0,0)}
        after={'a':(3,-2,5),'b':(2,-2,4)}
        old=reference.plane_key('a','b',(0,0,0),zero)
        new=reference.plane_key('a','b',(-1,0,-1),after)
        self.assertEqual(old,new)

    def test_literal_packet_freezes_every_actual_word_array_and_thread_case(self):
        files=tasks.literal_packet();catalog=json.loads(files['catalog.json'])
        self.assertEqual(catalog['distinct_inputs'],84)
        self.assertEqual(len(catalog['cases']),252)
        self.assertEqual({r['threads'] for r in catalog['cases']},{1,2,4})
        self.assertEqual(len({r['name'] for r in catalog['cases']}),252)
        self.assertFalse(catalog['candidate_invoked']);self.assertFalse(catalog['reference_evaluated'])
        for row in catalog['cases']:
            data=files[row['input']['path']]
            self.assertEqual(hashlib.sha256(data).hexdigest(),row['input']['sha256'])
            self.assertEqual(len(data),row['input']['bytes'])
            self.assertEqual(len(bridge.parse_input(data)['generators']),row['input']['generators'])
            self.assertEqual(row['required_success'],row['base'] in fixtures.BASES[:6])

    def test_capsule_preserves_exact_members_and_rejects_unsafe_names(self):
        original={'b.json':b'{}\n','inputs/a.txt':b'actual words\n'}
        packed=tasks.capsule(original)
        with tarfile.open(fileobj=io.BytesIO(packed),mode='r:gz') as archive:
            self.assertEqual(archive.getnames(),sorted(original))
            for name,raw in original.items():
                self.assertEqual(archive.extractfile(name).read(),raw)
        for name in ('../escape','/absolute','a/../escape','.','a\\escape'):
            with self.assertRaises(ValueError):
                tasks.capsule({name:b'unsafe'})

    def test_reference_task_seals_actual_input_and_exact_reference(self):
        raw=one_cell()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'input.json';path.write_bytes(raw)
            output=root/'reference'
            status=tasks.execute('reference',output,{'input':path})
            self.assertEqual(status['status'],'complete')
            self.assertFalse(status['execution_provenance_verified'])
            identities=json.loads((output/'files.sha256.json').read_bytes())
            for name,expected in identities.items():
                actual=(output/name).read_bytes()
                self.assertEqual(tasks.describe(actual),expected)
            self.assertEqual((output/'input.json').read_bytes(),raw)
            result=json.loads((output/'reference.json').read_bytes())
            self.assertTrue(result['exact_volume_closure'])
            self.assertEqual(result['input_sha256'],hashlib.sha256(raw).hexdigest())
            with tarfile.open(output/'packet.tar.gz',mode='r:gz') as archive:
                self.assertEqual(archive.extractfile('input.json').read(),raw)
                self.assertEqual(json.loads(archive.extractfile('status.json').read()),status)

    def test_failed_reference_preserves_actual_input_and_failure_packet(self):
        raw=one_cell()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'input.json';path.write_bytes(raw);output=root/'failed'
            with mock.patch.object(reference,'evaluate',side_effect=ValueError('deliberate reference failure')):
                with self.assertRaisesRegex(ValueError,'deliberate reference failure'):
                    tasks.execute('reference',output,{'input':path})
            status=json.loads((output/'status.json').read_bytes())
            self.assertEqual(status['status'],'failed')
            self.assertEqual(status['error_type'],'ValueError')
            self.assertFalse((output/'packet.tar.gz').exists())
            with tarfile.open(output/'failure-records.tar.gz',mode='r:gz') as archive:
                self.assertEqual(archive.extractfile('failed_inputs/input.bin').read(),raw)
                self.assertEqual(json.loads(archive.extractfile('status.json').read())['status'],'failed')

    def test_task_rejects_existing_output_without_altering_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);sentinel=root/'kept';sentinel.write_bytes(b'original')
            with self.assertRaisesRegex(ValueError,'Fresh task output'):
                tasks.execute('fixtures',root,{})
            self.assertEqual(sentinel.read_bytes(),b'original')
            self.assertEqual(sorted(p.name for p in root.iterdir()),['kept'])

    def test_held_input_rejects_symlinks_and_duplicate_or_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'actual';path.write_bytes(b'input')
            link=root/'linked';link.symlink_to(path)
            with self.assertRaisesRegex(ValueError,'Linked input'):
                tasks.capture(link)
            self.assertEqual(tasks.capture(path),b'input')
        for raw in (b'{"n":1e400}',b'{"n":NaN}',b'{"n":1,"n":2}'):
            with self.assertRaises(ValueError):
                tasks.parse(raw)
