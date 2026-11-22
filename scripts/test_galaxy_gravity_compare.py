"""Unexecuted exact-algebra controls; execute each method only on REANA.

Synthetic bridge transcripts are labelled SCHEMA_ONLY and never Rust evidence.
No test, fixture, force/reference evaluation or codec work occurs on import.
"""
import copy
from fractions import Fraction as Q
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import galaxy_gravity_bridge as bridge
import galaxy_gravity_compare as compare
import galaxy_gravity_reference as reference
import test_galaxy_gravity_bridge as schema_fixture


def rational_certificate(value):
    value = Q(value)
    nearest = format(bridge.codec().binary64_bits(value), '016x')
    return dict(expression=[] if value == 0 else [dict(coefficient=compare.q_record(value),
                    radicand=compare.q_record(Q(1)))], structural_zero=value == 0, exact_rational=True,
                enclosure=dict(lower=compare.q_record(value), upper=compare.q_record(value)),
                nearest_binary64=nearest, sqrt_fraction_bits=None,
                rounding_error_bound=compare.q_record(abs(compare.word(nearest) - value)))


def decoded(bounds):
    return tuple(compare.rational(v) for v in bounds)


def packet_for_schema_fixture(root, count=2, shuffled=False):
    raw, stdout, _ = schema_fixture.fixture(count, shuffled=shuffled)
    snapshot = bridge.decode_snapshot(raw, stdout, b'', schema_fixture.process_control(raw, stdout))
    projection = bridge.project_reference(snapshot)
    path = root / 'input.json'
    path.write_bytes(projection['reference_input_bytes'])
    exported = root / 'reference'
    if reference.export_input(path, exported) != 0:
        raise RuntimeError('Independent reference export failed in REANA control')
    return snapshot, {name: (exported / name).read_bytes() for name in compare.PACKET_FILES}


def reseal(packet):
    result = dict(packet)
    result['files.sha256.json'] = reference.json_bytes(dict(schema='openmhd.gravity-reference-files.v1',
        files={name: dict(sha256=compare.sha(raw), bytes=len(raw)) for name, raw in result.items()
               if name != 'files.sha256.json'}))
    return result


class GravityStaticComparisonTests(unittest.TestCase):
    def test_scalar_error_interval_and_independent_positive_denominator(self):
        self.assertEqual(compare.absolute_error(Q(3), (Q(1), Q(2))), (Q(1), Q(2)))
        row = compare.criterion((Q(2), Q(3)), (Q(4), Q(5)), False)
        self.assertEqual(decoded(row['normalized_error_bounds']), (Q(2, 5), Q(3, 4)))
        self.assertEqual(row['verdict'], 'fail')

    def test_squared_vector_gate_uses_sum_not_component_max(self):
        tau = Q(compare.TAU)
        target = [(Q(0), Q(0))] * 3
        errors = compare.vector_error_squared([4 * tau / 5, 4 * tau / 5, Q(0)], target)
        self.assertEqual(errors, (32 * tau * tau / 25,) * 2)
        row = compare.criterion(errors, (Q(1), Q(1)), False, squared=True)
        self.assertEqual(row['verdict'], 'fail')

    def test_squared_denominator_and_threshold_boundary(self):
        row = compare.criterion((Q(4), Q(9)), (Q(4), Q(5)), False, squared=True)
        self.assertEqual(decoded(row['normalized_error_bounds']), (Q(4, 25), Q(9, 16)))
        tau = Q(compare.TAU)
        at = compare.criterion((tau * tau,) * 2, (Q(1), Q(1)), False, squared=True)
        strict = compare.criterion((tau * tau,) * 2, (Q(1), Q(1)), False, squared=True, strict=True)
        self.assertEqual(at['verdict'], 'pass')
        self.assertEqual(strict['verdict'], 'fail')

    def test_threshold_crossing_is_unresolved_and_never_rounded_to_pass(self):
        tau = Q(compare.TAU)
        row = compare.criterion((tau / 2, 2 * tau), (Q(1), Q(1)), False)
        self.assertEqual(row['verdict'], 'unresolved')
        self.assertEqual(decoded(row['normalized_error_bounds']), (tau / 2, 2 * tau))

    def test_structural_zero_requires_exact_absolute_zero_without_floor(self):
        zero = compare.criterion((Q(0), Q(0)), (Q(0), Q(0)), True)
        tiny = Q(1, 10 ** 1000)
        changed = compare.criterion((tiny, tiny), (Q(0), Q(0)), True)
        self.assertEqual(zero['verdict'], 'pass')
        self.assertEqual(changed['verdict'], 'fail')
        self.assertNotIn('normalized_error_bounds', zero)
        self.assertEqual(decoded(changed['absolute_error_bounds']), (tiny, tiny))

    def test_nonzero_scale_with_zero_lower_bound_is_unresolved(self):
        row = compare.criterion((Q(0), Q(0)), (Q(0), Q(1)), False)
        self.assertEqual(row['verdict'], 'unresolved')
        with self.assertRaisesRegex(ValueError, 'Structural-zero scale'):
            compare.criterion((Q(0), Q(0)), (Q(0), Q(1)), True)

    def test_exact_words_preserve_subnormal_and_signed_zero_numerically(self):
        self.assertEqual(compare.word('0000000000000001'), Q(1, 1 << 1074))
        self.assertEqual(compare.word('8000000000000001'), -Q(1, 1 << 1074))
        self.assertEqual(compare.word('8000000000000000'), Q(0))
        self.assertEqual(compare.word('0000000000000000'), Q(0))
        with self.assertRaises(bridge.BridgeError):
            compare.word('7ff0000000000000')

    def test_rational_certificate_independent_manual_fraction_and_rounding(self):
        record = rational_certificate(Q(-6, 5))
        bounds, zero = compare.Certificates().read(record)
        self.assertEqual(bounds, (Q(-6, 5), Q(-6, 5)))
        self.assertFalse(zero)
        zero_bounds, structural = compare.Certificates().read(rational_certificate(0))
        self.assertEqual(zero_bounds, (Q(0), Q(0)))
        self.assertTrue(structural)

    def test_irrational_certificate_checks_integer_enclosure_and_sign(self):
        budget = reference.Budget()
        record = reference.certify(reference.Expression(budget).add_term(Q(-3), Q(2)))
        bounds, zero = compare.Certificates().read(record)
        lo, hi = bounds
        self.assertFalse(zero)
        self.assertLess(lo, hi)
        self.assertLess(hi, 0)
        self.assertLessEqual(hi * hi, Q(18))
        self.assertLessEqual(Q(18), lo * lo)

    def test_changed_enclosure_word_and_rounding_bound_reject_distinctly(self):
        original = rational_certificate(Q(1, 3))
        changes = (
            ('enclosure', lambda r: r['enclosure'].update(lower=compare.q_record(Q(0))),
             'Reproduced exact scalar enclosure'),
            ('nearest', lambda r: r.update(nearest_binary64='3ff0000000000000'),
             'One certified nearest'),
            ('error', lambda r: r.update(rounding_error_bound=compare.q_record(Q(1))),
             'Actual nearest-word rounding bound'))
        for _, change, expected in changes:
            record = copy.deepcopy(original)
            change(record)
            with self.assertRaisesRegex(ValueError, expected):
                compare.Certificates().read(record)

    def test_bad_rational_encodings_and_structural_flags_reject(self):
        for row in (dict(numerator_hex='00', denominator_hex='1'),
                    dict(numerator_hex='2', denominator_hex='2'),
                    dict(numerator_hex='-0', denominator_hex='1'),
                    dict(numerator_hex='1', denominator_hex='0')):
            with self.assertRaises(ValueError):
                compare.rational(row)
        changed = rational_certificate(0)
        changed['structural_zero'] = 1
        with self.assertRaisesRegex(ValueError, 'Structural zero'):
            compare.Certificates().read(changed)

    def test_certificates_reject_duplicate_radicals_and_boolean_precision(self):
        record = rational_certificate(1)
        record['expression'].append(copy.deepcopy(record['expression'][0]))
        with self.assertRaisesRegex(ValueError, 'Sorted distinct radicands'):
            compare.Certificates().read(record)
        record = reference.certify(reference.Expression(reference.Budget()).add_term(Q(1), Q(2)))
        record['sqrt_fraction_bits'] = True
        with self.assertRaisesRegex(ValueError, 'Registered scalar precision'):
            compare.Certificates().read(record)
        checker = compare.Certificates()
        checker.terms = compare.MAX_TOTAL_TERMS
        with self.assertRaisesRegex(ValueError, 'Total scalar-term resource'):
            checker.read(rational_certificate(1))
        checker = compare.Certificates()
        checker.used = compare.MAX_CERTIFICATES
        with self.assertRaisesRegex(ValueError, 'Certificate-count resource'):
            checker.read(rational_certificate(0))
        with self.assertRaisesRegex(ValueError, 'Comparison rational-size'):
            compare.bounded(1 << compare.MAX_COMPARISON_BITS)

    def test_schema_candidate_reference_arithmetic_does_not_attest_a_rust_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            snapshot, packet = packet_for_schema_fixture(Path(temporary), shuffled=True)
            result = compare.compare(snapshot, packet)
            self.assertEqual(result['arithmetic_verdict'], 'pass')
            self.assertFalse(result['external_execution_provenance_verified'])
            self.assertFalse(result['component_accepted'])
            self.assertFalse(result['merger_accepted'])
            self.assertTrue(result['candidate_scales_are_diagnostic_only'])
            self.assertFalse(result['candidate_residuals_repaired'])
            self.assertEqual(result['candidate_projection']['invocation_id'], 'SCHEMA_ONLY.not-a-run')

    def test_reference_packet_changed_original_input_and_source_cannot_be_resealed(self):
        with tempfile.TemporaryDirectory() as temporary:
            snapshot, packet = packet_for_schema_fixture(Path(temporary))
            projection = bridge.project_reference(snapshot)
            changed = dict(packet, **{'input.json': packet['input.json'] + b'\n'})
            with self.assertRaisesRegex(ValueError, 'Actual Rust-word original'):
                compare.validate_packet(projection, reseal(changed))
            changed = dict(packet, **{'galaxy_gravity_reference.py': packet['galaxy_gravity_reference.py'] + b'\n'})
            with self.assertRaisesRegex(ValueError, 'Exact independent source buffer'):
                compare.validate_packet(projection, reseal(changed))

    def test_missing_body_bad_hash_and_failed_reference_status_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            snapshot, packet = packet_for_schema_fixture(Path(temporary), count=0)
            projection = bridge.project_reference(snapshot)
            missing = dict(packet)
            del missing['sources.json']
            with self.assertRaisesRegex(ValueError, 'Exact eight-file'):
                compare.validate_packet(projection, missing)
            changed = dict(packet, **{'reference.json': packet['reference.json'] + b'\n'})
            with self.assertRaisesRegex(ValueError, 'Every retained body hash'):
                compare.validate_packet(projection, changed)
            changed = dict(packet)
            status = json.loads(changed['status.json'])
            status['status'] = 'failed'
            changed['status.json'] = reference.json_bytes(status)
            with self.assertRaisesRegex(ValueError, 'Actual retained complete reference'):
                compare.validate_packet(projection, reseal(changed))

    def test_resealed_missing_particle_and_pair_inventories_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            snapshot, packet = packet_for_schema_fixture(Path(temporary))
            for field, expected in (('samples_by_particle_id', 'Exact ParticleId'),
                                    ('ordered_source_terms', 'Complete independent directed'),
                                    ('unordered_pairs', 'Complete independent unordered')):
                changed = dict(packet)
                value = json.loads(changed['reference.json'])
                value[field].pop(next(iter(value[field]))) if isinstance(value[field], dict) else value[field].pop()
                changed['reference.json'] = reference.json_bytes(value)
                with self.assertRaisesRegex(ValueError, expected):
                    compare.compare(snapshot, reseal(changed))

    def test_reference_acceptance_claim_and_false_runtime_optimize_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            snapshot, packet = packet_for_schema_fixture(Path(temporary), count=1)
            changed = dict(packet)
            value = json.loads(changed['reference.json'])
            value['scope']['component_accepted'] = True
            changed['reference.json'] = reference.json_bytes(value)
            with self.assertRaisesRegex(ValueError, 'Independent reference retains nonacceptance'):
                compare.compare(snapshot, reseal(changed))
            changed = dict(packet)
            value = json.loads(changed['sources.json'])
            value['runtime']['optimize'] = False
            changed['sources.json'] = reference.json_bytes(value)
            with self.assertRaisesRegex(ValueError, 'Unoptimized retained reference'):
                compare.compare(snapshot, reseal(changed))

    def test_empty_one_body_and_coincident_zero_channels_stay_absolute(self):
        for count in (0, 1, 2):
            with tempfile.TemporaryDirectory() as temporary:
                snapshot, packet = packet_for_schema_fixture(Path(temporary), count=count)
                result = compare.compare(snapshot, packet)
                self.assertEqual(result['arithmetic_verdict'], 'pass')
                for name in ('raw_net_force', 'raw_net_torque_origin'):
                    gate = result['gates'][name]
                    self.assertTrue(gate['structural_zero_scale'])
                    self.assertNotIn('normalized_error_bounds', gate)
                    self.assertEqual(decoded(gate['absolute_error_bounds']), (Q(0), Q(0)))

    def test_injected_candidate_scale_cannot_hide_nonzero_force_at_zero_target(self):
        # Deliberately bypass only the bridge dependency for a normalization
        # sensitivity control. The altered projection is not a valid real
        # coincident-source bridge output, process receipt or Rust comparison.
        with tempfile.TemporaryDirectory() as temporary:
            snapshot, packet = packet_for_schema_fixture(Path(temporary))
            projection = bridge.project_reference(snapshot)
            sample = projection['join']['evaluation']['samples'][0]
            sample['force'][0] = '3ff0000000000000'
            sample['force_scale'] = '7fefffffffffffff'
            with mock.patch.object(bridge, 'project_reference', return_value=projection):
                result = compare.compare(snapshot, packet)
            gate = result['gates']['particle.' + sample['id'] + '.force']
            self.assertEqual(gate['verdict'], 'fail')
            self.assertTrue(gate['structural_zero_scale'])
            self.assertNotIn('normalized_error_bounds', gate)
            self.assertFalse(result['external_execution_provenance_verified'])


if __name__ == '__main__':
    unittest.main()
