"""Written-only GP-2 reference controls; each method must run on REANA later.

Expected fractions are the reviewed eps=4 manual GP-2 controls, not Rust
outputs. No complete physical/server/campaign packet is fabricated here.
Imports do not evaluate a force, load the shared codec, or create fixtures.
"""

import copy
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import galaxy_gravity_reference as reference


ZERO = "0000000000000000"
ONE = "3ff0000000000000"
TWO = "4000000000000000"
THREE = "4008000000000000"
FOUR = "4010000000000000"
FIVE = "4014000000000000"
A = "00000000000000010000000000000001"
B = "00000000000000010000000000000002"
C = "00000000000000010000000000000003"


def source(payload, mass=TWO, position=(ZERO, ZERO, ZERO)):
    return {"id": {"wrapper": "ParticleId", "payload_hex": payload},
            "mass_bits": mass, "position_bits": list(position)}


def physical(rows, g=ONE, epsilon=FOUR):
    return {"schema": reference.INPUT_SCHEMA,
            "model": {"boundary": "isolated", "kernel": "common-fixed-plummer",
                      "self_interaction": "excluded", "g_code_bits": g,
                      "epsilon_code_bits": epsilon}, "sources": rows}


def raw(data):
    return json.dumps(data, sort_keys=True, allow_nan=False).encode("utf-8")


def fraction(record):
    return Q(int(record["numerator_hex"], 16), int(record["denominator_hex"], 16))


def interval(record):
    return fraction(record["enclosure"]["lower"]), fraction(record["enclosure"]["upper"])


def axis_input():
    return physical([source(A), source(B, THREE, (THREE, ZERO, ZERO))])


class GravityReferenceArithmeticTests(unittest.TestCase):
    def assert_exact(self, record, expected):
        self.assertTrue(record["exact_rational"])
        self.assertEqual(interval(record), (Q(expected), Q(expected)))
        self.assertEqual(record["structural_zero"], expected == 0)

    def assert_vector(self, records, expected):
        self.assertEqual(len(records), 3)
        for record, value in zip(records, expected):
            self.assert_exact(record, value)

    def evaluate(self, data):
        return reference.evaluate(reference.parse_input(raw(data)))

    def assert_rejected(self, data, code):
        with self.assertRaises(reference.ReferenceError) as raised:
            reference.parse_input(raw(data))
        self.assertEqual(raised.exception.code, code)

    def test_axis_pair_rational_force_potential_energy_and_scales(self):
        result = self.evaluate(axis_input())
        a, b = (result["samples_by_particle_id"][key] for key in (A, B))
        self.assert_vector(a["force"], (Q(18, 125), 0, 0))
        self.assert_vector(b["force"], (Q(-18, 125), 0, 0))
        self.assert_exact(a["specific_potential"], Q(-3, 5))
        self.assert_exact(b["specific_potential"], Q(-2, 5))
        self.assert_exact(result["pair_energy"], Q(-6, 5))
        self.assert_exact(a["scales"]["force_magnitude_sum"], Q(18, 125))
        self.assert_exact(result["independent_scales"]["energy_absolute_sum"], Q(6, 5))
        self.assert_exact(result["independent_scales"]["net_force_interaction_sum"], Q(36, 125))
        self.assert_exact(result["independent_scales"]["net_torque_interaction_sum"], Q(54, 125))
        self.assert_vector(result["raw_net_force"], (0, 0, 0))
        self.assert_vector(result["raw_net_torque_about_input_origin"], (0, 0, 0))
        self.assert_exact(result["half_sum_mass_phi_minus_pair_energy"], 0)
        self.assertEqual(result["unordered_pair_count"], 1)
        self.assertEqual(len(result["ordered_source_terms"]), 2)
        first_term = result["ordered_source_terms"][0]
        self.assertEqual((first_term["owner"], first_term["source"]), (A, B))
        self.assertEqual(fraction(first_term["softened_distance_squared"]), 25)
        self.assertEqual([fraction(q) for q in first_term["force_sqrt_q_coefficients"]], [Q(18, 625), 0, 0])
        self.assertEqual(fraction(first_term["phi_sqrt_q_coefficient"]), Q(-3, 25))

    def test_oblique_negative_coordinates_and_unrepaired_individual_torque(self):
        data = physical([source(A, TWO, ("c010000000000000", ONE, TWO)),
                         source(B, THREE, ("c008000000000000", THREE, FOUR))])
        result = self.evaluate(data)
        a, b = (result["samples_by_particle_id"][key] for key in (A, B))
        self.assert_vector(a["force"], (Q(6, 125), Q(12, 125), Q(12, 125)))
        self.assert_vector(a["torque_about_input_origin"], (Q(-12, 125), Q(60, 125), Q(-54, 125)))
        self.assert_vector(b["torque_about_input_origin"], (Q(12, 125), Q(-60, 125), Q(54, 125)))
        self.assert_vector(result["raw_net_torque_about_input_origin"], (0, 0, 0))
        lo, hi = interval(result["independent_scales"]["net_torque_interaction_sum"])
        # 4<sqrt(21)<5 and 5<sqrt(34)<6; no candidate-derived scale.
        self.assertGreater(lo, Q(162, 125))
        self.assertLess(hi, Q(198, 125))

    def test_distinct_colocated_pair_keeps_potential_energy_and_zero_scales(self):
        position = (ONE, "c000000000000000", THREE)
        result = self.evaluate(physical([source(A, TWO, position), source(B, THREE, position)]))
        self.assertEqual(result["unordered_pair_count"], 1)
        self.assert_exact(result["pair_energy"], Q(-3, 2))
        self.assert_exact(result["samples_by_particle_id"][A]["specific_potential"], Q(-3, 4))
        self.assert_exact(result["samples_by_particle_id"][B]["specific_potential"], Q(-1, 2))
        for sample in result["samples_by_particle_id"].values():
            self.assert_vector(sample["force"], (0, 0, 0))
            self.assert_exact(sample["scales"]["force_magnitude_sum"], 0)
        self.assert_exact(result["independent_scales"]["net_force_interaction_sum"], 0)
        self.assert_exact(result["independent_scales"]["net_torque_interaction_sum"], 0)

    def test_empty_and_one_source_have_no_self_terms_or_invented_com(self):
        for rows in ([], [source("00000000000000000000000000000000", TWO,
                                 (ONE, "c000000000000000", THREE))]):
            with self.subTest(count=len(rows)):
                result = self.evaluate(physical(rows))
                self.assertEqual(result["source_count"], len(rows))
                self.assertEqual(result["unordered_pairs"], [])
                self.assertEqual(result["ordered_source_terms"], [])
                self.assert_exact(result["pair_energy"], 0)
                self.assertNotIn("center_of_mass", result)
                for sample in result["samples_by_particle_id"].values():
                    self.assert_exact(sample["specific_potential"], 0)
                    self.assert_vector(sample["force"], (0, 0, 0))
        self.assert_rejected(physical([], epsilon=ZERO), "NonpositiveInput")

    def test_triplet_sorted_ids_separate_unordered_energy_and_directed_phi(self):
        result = self.evaluate(physical([source(C, FIVE), source(A), source(B, THREE, (THREE, ZERO, ZERO))]))
        self.assertEqual(list(result["samples_by_particle_id"]), [A, B, C])
        self.assertEqual(result["unordered_pair_count"], 3)
        self.assertEqual(len(result["ordered_source_terms"]), 6)
        for key, force, phi in ((A, Q(18, 125), Q(-37, 20)),
                                (B, Q(-63, 125), Q(-7, 5)),
                                (C, Q(45, 125), Q(-11, 10))):
            self.assert_vector(result["samples_by_particle_id"][key]["force"], (force, 0, 0))
            self.assert_exact(result["samples_by_particle_id"][key]["specific_potential"], phi)
        for pair, expected in zip(result["unordered_pairs"], (Q(-6, 5), Q(-5, 2), Q(-3))):
            self.assert_exact(pair["energy"], expected)
        self.assert_exact(result["pair_energy"], Q(-67, 10))
        self.assert_exact(result["independent_scales"]["net_force_interaction_sum"], Q(126, 125))
        self.assert_exact(result["independent_scales"]["net_torque_interaction_sum"], Q(189, 125))

    def test_registered_q_uses_actual_word_not_exact_decimal(self):
        q = Q(4722366482869645, 1 << 72)
        data = physical([source(A, ONE), source(B, "3eb0c6f7a0b5ed8d", (THREE, ZERO, ZERO))])
        parsed = reference.parse_input(raw(data))
        self.assertEqual(parsed.sources[1].mass, q)
        self.assertNotEqual(parsed.sources[1].mass, Q(1, 1000000))
        result = reference.evaluate(parsed)
        self.assert_vector(result["samples_by_particle_id"][A]["force"], (3 * q / 125, 0, 0))
        self.assert_exact(result["samples_by_particle_id"][A]["specific_potential"], -q / 5)
        self.assert_exact(result["samples_by_particle_id"][B]["specific_potential"], Q(-1, 5))
        self.assert_exact(result["pair_energy"], -q / 5)
        self.assert_exact(result["independent_scales"]["net_force_interaction_sum"], 6 * q / 125)

    def test_nontrivial_radical_pair_has_certified_bounds_not_candidate_values(self):
        # d=1, epsilon=1 -> q=2, F=sqrt(2)/4, Phi=U=-sqrt(2)/2.
        result = self.evaluate(physical([source(A, ONE), source(B, ONE, (ONE, ZERO, ZERO))], epsilon=ONE))
        f = result["samples_by_particle_id"][A]["force"][0]
        lo, hi = interval(f)
        self.assertLessEqual(lo * lo, Q(1, 8))
        self.assertGreaterEqual(hi * hi, Q(1, 8))
        self.assertLess(hi - lo, Q(1, 1 << 60))
        self.assertFalse(f["exact_rational"])
        # Independent midpoint test for this literal's nearest word: for
        # S=0x16a09e667f3bcd, F lies strictly between (2S+-1)/2^55.
        significand = 0x16a09e667f3bcd
        self.assertLess((2 * significand - 1) ** 2, 1 << 107)
        self.assertGreater((2 * significand + 1) ** 2, 1 << 107)
        self.assertEqual(f["nearest_binary64"], "3fd6a09e667f3bcd")
        rounded = Q(significand, 1 << 54)
        self.assertEqual(fraction(f["rounding_error_bound"]), max(abs(rounded - lo), abs(rounded - hi)))
        p_lo, p_hi = interval(result["pair_energy"])
        self.assertLess(p_hi, 0)
        self.assertGreaterEqual(p_lo * p_lo, Q(1, 2))
        self.assertLessEqual(p_hi * p_hi, Q(1, 2))
        self.assertEqual(reference.sqrt_interval(Q(2), 2, reference.Budget()), (Q(5, 4), Q(3, 2)))

    def test_negative_interval_coefficients_reverse_the_correct_endpoints(self):
        budget = reference.Budget()
        expression = reference.Expression(budget).add_term(1, 1).add_term(-3, 2)
        self.assertEqual(reference.expression_interval(expression, 2), (Q(-7, 2), Q(-11, 4)))
        # sqrt(9/4) is exact at every permitted precision.
        self.assertEqual(reference.sqrt_interval(Q(9, 4), 0, budget), (Q(3, 2), Q(3, 2)))

    def test_square_class_and_interval_cancellation_are_exact_not_zero_floors(self):
        budget = reference.Budget()
        for terms in (((1, 8), (-2, 2)), ((1, 18), (-3, 2)),
                      ((1, 2), (1, 3), (-1, 2), (-1, 3))):
            expression = reference.Expression(budget)
            for coefficient, radicand in terms:
                expression.add_term(coefficient, radicand)
            result = reference.certify(expression)
            self.assert_exact(result, 0)
            self.assertEqual(result["nearest_binary64"], ZERO)
            self.assertEqual(result["expression"], [])
        # A nonzero rational below half the minimum subnormal rounds to zero
        # but remains nonzero in the exact record, with no clipped expression.
        tiny = reference.Expression(budget).add_term(Q(1, 1 << 1076), 1)
        record = reference.certify(tiny)
        self.assertFalse(record["structural_zero"])
        self.assert_exact(record, Q(1, 1 << 1076))
        self.assertEqual(record["nearest_binary64"], ZERO)

    def test_actual_bit_identity_signed_zero_input_bytes_and_id_permutation(self):
        data = axis_input()
        first = reference.parse_input(raw(data))
        permuted = copy.deepcopy(data)
        permuted["sources"].reverse()
        second = reference.parse_input(raw(permuted))
        self.assertNotEqual(first.raw_sha256, second.raw_sha256)
        self.assertEqual(first.canonical_sha256, second.canonical_sha256)
        signed = copy.deepcopy(data)
        signed["sources"][0]["position_bits"][1] = "8000000000000000"
        third = reference.parse_input(raw(signed))
        self.assertEqual(first.sources, third.sources)
        self.assertNotEqual(first.canonical_sha256, third.canonical_sha256)
        self.assertIn(b"8000000000000000", third.canonical)
        self.assertEqual(first.raw_sha256, hashlib.sha256(raw(data)).hexdigest())

    def test_invalid_words_identity_model_and_schema_fail_before_arithmetic(self):
        self.assertEqual(reference.parse_input(raw(axis_input())).sources[0].payload, A)
        mutations = []
        for word, code in ((ZERO, "NonpositiveInput"), ("bff0000000000000", "NonpositiveInput"),
                           ("7ff0000000000000", "NonfiniteInput"), ("7ff8000000000001", "NonfiniteInput"),
                           ("3FF0000000000000", "InvalidWord")):
            for field in ("g_code_bits", "epsilon_code_bits"):
                data = axis_input()
                data["model"][field] = word
                mutations.append((data, code))
            data = axis_input()
            data["sources"][0]["mass_bits"] = word
            mutations.append((data, code))
        data = axis_input()
        data["sources"][0]["position_bits"][0] = "fff0000000000000"
        mutations.append((data, "NonfiniteInput"))
        data = axis_input()
        data["sources"][0]["mass_bits"] = True
        mutations.append((data, "InvalidWord"))
        data = axis_input()
        data["sources"][1]["id"]["payload_hex"] = A
        mutations.append((data, "DuplicateIdentity"))
        data = axis_input()
        data["sources"][0]["id"]["wrapper"] = "CellId"
        mutations.append((data, "InvalidIdentity"))
        data = axis_input()
        data["gas_geometry_epoch"] = None
        mutations.append((data, "InvalidSchema"))
        data = axis_input()
        data["model"]["boundary"] = "periodic"
        mutations.append((data, "UnsupportedModel"))
        for data, code in mutations:
            with self.subTest(code=code, data=data):
                self.assert_rejected(data, code)
        for invalid in (b'{"schema":1}', b'{"schema":NaN}', b'{"schema":0.0}',
                        b'{"schema":true}', b'{"schema":"x","schema":"x"}'):
            with self.assertRaises(reference.ReferenceError) as raised:
                reference.parse_input(invalid)
            self.assertEqual(raised.exception.code, "InvalidSchema")

    def test_source_byte_integer_and_operation_resources_reject_without_values(self):
        data = physical([source(format(index, "032x")) for index in range(reference.MAX_SOURCES + 1)])
        self.assert_rejected(data, "ResourceLimit")
        with self.assertRaises(reference.ReferenceError) as raised:
            reference.parse_input(b" " * (reference.MAX_INPUT_BYTES + 1))
        self.assertEqual(raised.exception.code, "ResourceLimit")
        for budget, values in ((reference.Budget(groups=1), (Q(1), Q(2))),
                                (reference.Budget(integer_bits=8), (Q(1 << 8),))):
            with self.assertRaises(reference.ReferenceError) as raised:
                for value in values:
                    budget.check(value)
            self.assertEqual(raised.exception.code, "ResourceLimit")

    def test_unresolved_rounding_overflow_and_precision_never_export_a_floor(self):
        e = reference.Expression(reference.Budget()).add_term(1, 2)
        with self.assertRaises(reference.ReferenceError) as raised:
            reference.certify(e, (0,))
        self.assertEqual(raised.exception.code, "RoundingUnresolved")
        huge = reference.Expression(reference.Budget()).add_term(1 << 1024, 1)
        with self.assertRaises(reference.ReferenceError) as raised:
            reference.certify(huge)
        self.assertEqual(raised.exception.code, "FiniteRoundingRequired")
        with self.assertRaises(reference.ReferenceError) as raised:
            reference.certify(e, (4097,))
        self.assertEqual(raised.exception.code, "ResourceLimit")

    def test_pinned_shared_codec_rejects_wrong_bytes_before_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "galaxy_geometry3_reference.py"
            path.write_text("raise AssertionError('must never execute unpinned source')\n", encoding="utf-8")
            with self.assertRaises(reference.ReferenceError) as raised:
                reference._load_binary64_helper(path)
            self.assertEqual(raised.exception.code, "HelperIdentity")

    def test_failed_arithmetic_keeps_closed_nonaccepting_input_and_no_reference(self):
        # Finite largest masses, colocated distinct IDs: Phi finite but U is
        # not finite binary64. No successful reference may escape this failure.
        data = physical([source(A, "7fefffffffffffff"), source(B, "7fefffffffffffff")], epsilon=ONE)
        with tempfile.TemporaryDirectory() as temporary:
            source_path = Path(temporary) / "input.json"
            source_path.write_bytes(raw(data))
            output = Path(temporary) / "output"
            self.assertEqual(reference.export_input(source_path, output), 1)
            status = json.loads((output / "status.json").read_bytes())
            self.assertEqual(status["status"], "failed")
            self.assertEqual(status["problem"]["code"], "FiniteRoundingRequired")
            self.assertFalse(status["reference_exported"])
            self.assertFalse(status["component_accepted"])
            self.assertTrue(status["reference_arithmetic_attempted"])
            self.assertFalse(status["reference_arithmetic_completed"])
            self.assertFalse((output / "reference.json").exists())
            self.assertEqual((output / "input.json").read_bytes(), raw(data))
            manifest = json.loads((output / "files.sha256.json").read_bytes())["files"]
            self.assertEqual(set(manifest), {"status.json", "sources.json", "input.json", "canonical_physical_input.json",
                                             "galaxy_gravity_reference.py", "galaxy_geometry3_reference.py"})
            for name, receipt in manifest.items():
                captured = (output / name).read_bytes()
                self.assertEqual(receipt, {"sha256": hashlib.sha256(captured).hexdigest(), "bytes": len(captured)})

    def test_single_input_export_is_closed_arithmetic_only_and_rejects_reuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            source_path = Path(temporary) / "input.json"
            source_path.write_bytes(raw(axis_input()))
            output = Path(temporary) / "output"
            self.assertEqual(reference.export_input(source_path, output), 0)
            status = json.loads((output / "status.json").read_bytes())
            self.assertEqual(status["status"], "complete")
            self.assertTrue(status["reference_exported"])
            self.assertFalse(status["component_accepted"])
            self.assertFalse(status["physical_evolutions_run"])
            self.assertTrue(status["reference_arithmetic_attempted"])
            self.assertTrue(status["reference_arithmetic_completed"])
            result = json.loads((output / "reference.json").read_bytes())
            self.assert_exact(result["pair_energy"], Q(-6, 5))
            self.assertTrue(all(value is False for value in result["scope"].values()))
            self.assertEqual(result["input"]["original_sha256"], hashlib.sha256(raw(axis_input())).hexdigest())
            manifest = json.loads((output / "files.sha256.json").read_bytes())["files"]
            self.assertEqual(set(manifest), {p.name for p in output.iterdir()} - {"files.sha256.json"})
            for name, receipt in manifest.items():
                captured = (output / name).read_bytes()
                self.assertEqual(receipt, {"sha256": hashlib.sha256(captured).hexdigest(), "bytes": len(captured)})
            sources = json.loads((output / "sources.json").read_bytes())["files"]
            self.assertEqual(sources["scripts/galaxy_geometry3_reference.py"]["sha256"], reference.HELPER_SHA256)
            for receipt in sources.values():
                captured = (output / receipt["copied_path"]).read_bytes()
                self.assertEqual(receipt["sha256"], hashlib.sha256(captured).hexdigest())
                self.assertEqual(receipt["bytes"], len(captured))
            with self.assertRaises(reference.ReferenceError) as raised:
                reference.export_input(source_path, output)
            self.assertEqual(raised.exception.code, "InvalidDestination")


if __name__ == "__main__":
    unittest.main()
