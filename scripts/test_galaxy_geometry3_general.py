"""Small deterministic general-geometry controls; every method runs on REANA."""
from fractions import Fraction as Q
import json
import unittest
from unittest import mock

import galaxy_geometry3_general_bridge as bridge
import galaxy_geometry3_general_compare as compare
import galaxy_geometry3_general_fixtures as fixtures
import galaxy_geometry3_general_reference as reference
import galaxy_geometry3_reference as ieee


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
                reference.certify_cell(planes,2)

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
