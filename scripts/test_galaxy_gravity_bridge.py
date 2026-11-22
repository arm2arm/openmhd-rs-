"""SOURCE-ONLY parser/schema controls; future execution is REANA-only.

All candidate-looking bytes below are explicitly SYNTHETIC SCHEMA CONTROLS,
not Rust output, process observations, numerical comparisons or physical
packets. A real built Rust-positive transcript is a separate mandatory gate.
No test/reference/parser calculation occurs merely by importing this module.
"""

import hashlib
import json
import unittest

import galaxy_gravity_bridge as bridge


Z = "0000000000000000"
NZ = "8000000000000000"
ONE = "3ff0000000000000"
TWO = "4000000000000000"
NEG_ONE = "bff0000000000000"
SUB = "0000000000000001"
ID1 = "00000000000000000000000000000001"
ID2 = "00000000000000000000000000000002"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def be(value, width=8):
    return value.to_bytes(width, "big")


def words(values):
    return b"".join(bytes.fromhex(w) for w in values)


def sized(raw):
    return be(len(raw)) + raw


def fixture(count=0, *, si=False, g=ONE, shuffled=False, signed=False, moving=False):
    """Independent literal field layout, no bridge encoder or force kernel.

    Only 0/1 and two distinct coincident unit masses are used. For the two
    coincident masses eps=1, the literal Phi/U=-G is hand-derived, but these
    bytes remain schema controls and must never be called a Rust-positive run.
    """
    if count not in (0, 1, 2):
        raise ValueError("fixture is deliberately small and nonphysical")
    if moving and (count != 2 or signed or si or g != ONE):
        raise ValueError("one explicit unit-mass counterstream schema control only")
    positions = [NEG_ONE, NZ, SUB] if signed else [Z, Z, Z]
    particles = [(ID1, "dm", 1, 2, positions, [ONE, Z, Z] if moving else [Z] * 3),
                 (ID2, "star", 3, 4, positions, [NEG_ONE, Z, Z] if moving else [Z] * 3)][:count]
    original = list(reversed(particles)) if shuffled else particles
    unit_row = "si " + " ".join([ONE, ONE, ONE, g, ONE, "SCHEMA_ONLY.units"]) if si else "dimensionless-g1"
    input_lines = ["openmhd-gravity-force-input-v1", "case SCHEMA_ONLY", "stage static-force-snapshot",
                   "clock " + NZ + " 11", "backend 9", "units " + unit_row,
                   "softening " + ONE + " 7", "count " + str(count)]
    for payload, kind, component, galaxy, position, momentum in original:
        input_lines.append("particle " + " ".join([payload, kind, str(component), str(galaxy), "7", ONE,
                                                    *position, *momentum]))
    raw = ("\n".join(input_lines + ["end"]) + "\n").encode()
    bodies = {}
    # These literal tag/field tables are independent of bridge canonical_bodies.
    bodies["sources"] = b"gravity-sources-v1\0collisionless\0" + be(count)
    for payload, kind, _, _, position, _ in particles:
        bodies["sources"] += payload.encode() + bytes([0 if kind == "dm" else 1]) + b"\x00\x07" + words([ONE, *position])
    bodies["state"] = b"gravity-catalog-v1\0" + words([NZ]) + be(11) + sized(bodies["sources"])
    for _, _, component, galaxy, _, momentum in particles:
        bodies["state"] += words(momentum) + be(component, 2) + be(galaxy, 4)
    bodies["model"] = b"gravity-model-v1\0isolated-common-Plummer-no-self\0" + words([g, ONE]) + b"\x00\x07"
    if si:
        bodies["units"] = (b"gravity-units-v1\0SI\0" + words([ONE, ONE, ONE, g, ONE])
                           + sized(b"SCHEMA_ONLY.units") + words([ONE] * 16 + [g]))
    else:
        bodies["units"] = b"gravity-units-v1\0dimensionless-G1-mu01"
    bodies["backend"] = b"gravity-backend-v1\0serial-sorted-i<j-Neumaier\0" + be(9)
    negative_g = format(int(g, 16) | (1 << 63), "016x")
    energy = negative_g if count == 2 else Z
    energy_scale = g if count == 2 else Z
    sample_words = [Z, Z, Z, energy, Z, energy_scale]
    global_words = [energy, energy_scale, Z, Z]
    evaluation = b"gravity-evaluation-v1\0" + words([NZ]) + be(11)
    for key in ["sources", "state", "model", "units", "backend"]:
        evaluation += sized(bodies[key])
    offsets = {"private_G": len(evaluation), "private_epsilon": len(evaluation) + 8,
               "pair_count": len(evaluation) + 16, "global_words": len(evaluation) + 24}
    evaluation += words([g, ONE]) + be(1 if count == 2 else 0) + words(global_words)
    offsets["sample_count"] = len(evaluation)
    evaluation += be(count)
    for payload, *_ in particles:
        evaluation += payload.encode() + words(sample_words)
    lines = ["openmhd-gravity-force-candidate-v1", "status complete", "component_accepted false",
             "case SCHEMA_ONLY", "stage static-force-snapshot", "input_sha256 " + digest(raw),
             "clock " + NZ + " 11", "backend_revision 9",
             "model isolated common-fixed-plummer excluded " + g + " " + ONE + " 7",
             "units_physical " + ("true" if si else "false"), "counts " + str(count) + " " + str(1 if count == 2 else 0)]
    lines += ["input_order " + p[0] for p in original]
    for key in ["sources", "state", "model", "units", "backend"]:
        body = bodies[key]
        lines.append("identity " + key + " " + str(len(body)) + " " + digest(body) + " " + body.hex())
    lines.append("cache_clock " + NZ + " 11")
    for key in ["sources", "state", "model", "units", "backend"]:
        body = bodies[key]
        lines.append("identity cache_" + key + " " + str(len(body)) + " " + digest(body) + " " + body.hex())
    for payload, kind, component, galaxy, position, momentum in particles:
        lines.append("particle " + " ".join([payload, kind, str(component), str(galaxy), "7", ONE,
                                              *position, *momentum]))
    for payload, *_ in particles:
        lines.append("sample " + payload + " " + " ".join(sample_words))
    lines += ["evaluation_scales " + " ".join(global_words),
              "evaluation_bytes " + str(len(evaluation)) + " " + digest(evaluation) + " " + evaluation.hex(),
              "raw_force " + " ".join([Z] * 3), "raw_torque_origin " + " ".join([Z] * 3),
              "diagnostic mass " + [Z, ONE, TWO][count], "diagnostic momentum " + " ".join([Z] * 3),
              "diagnostic angular_momentum_origin " + " ".join([Z] * 3), "diagnostic kinetic_lab " + (ONE if moving else Z),
              "diagnostic pair_energy " + energy, "diagnostic hamiltonian_lab " + (Z if moving else energy)]
    for name in ["center_of_mass", "center_velocity", "angular_momentum_internal"]:
        value = positions if name == "center_of_mass" else [Z] * 3
        lines.append("diagnostic " + name + (" some " + " ".join(value) if count else " none"))
    for name in ["kinetic_internal", "virial_work", "inertia_internal"]:
        value = ONE if moving and name == "kinetic_internal" else Z
        lines.append("diagnostic " + name + (" some " + value if count else " none"))
    virial = "defined " + ONE if moving else "undefined " + ("nonpositive-scale" if count else "empty")
    lines += ["diagnostic virial_residual " + virial, "end"]
    return raw, ("\n".join(lines) + "\n").encode(), {"bodies": bodies, "evaluation": evaluation, "offsets": offsets}


def body_change(stdout, label, transform):
    lines = stdout.decode().splitlines()
    prefix = "evaluation_bytes " if label == "evaluation" else "identity " + label + " "
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            fields = line[len(prefix):].split()
            body = transform(bytes.fromhex(fields[2]))
            lines[i] = prefix + str(len(body)) + " " + digest(body) + " " + body.hex()
            return ("\n".join(lines) + "\n").encode()
    raise ValueError("missing targeted synthetic row")


def process_control(raw, stdout, stderr=b""):
    # A schema-only caller stub, NOT an observed process/workflow receipt.
    return {"schema": "openmhd.gravity-force-process-evidence.v1", "invocation_id": "SCHEMA_ONLY.not-a-run",
            "outcome": "success", "returncode": 0, "timed_out": False, "logs_closed": True,
            "writers_stopped": True, "input_sha256": digest(raw), "stdout_sha256": digest(stdout),
            "stdout_bytes": len(stdout), "stderr_sha256": digest(stderr), "stderr_bytes": len(stderr)}


class GravityBridgeMetadataTests(unittest.TestCase):
    def rejected(self, raw, stdout, code, field):
        with self.assertRaises(bridge.BridgeError) as caught:
            bridge.parse_transcript(raw, stdout)
        self.assertEqual((caught.exception.code, caught.exception.field), (code, field))

    def test_empty_literal_bodies_and_explicit_undefined_reason(self):
        raw, stdout, meta = fixture()
        parsed = bridge.parse_transcript(raw, stdout)
        self.assertEqual(meta["bodies"]["sources"], b"gravity-sources-v1\0collisionless\0" + bytes(8))
        self.assertEqual(parsed["source"]["input_order"], [])
        self.assertEqual(parsed["evaluation"]["pair_count"], 0)
        self.assertEqual(parsed["diagnostics"]["virial_residual"], {"kind": "undefined", "value": "empty"})
        self.rejected(raw, stdout.replace(b"undefined empty", b"undefined nonpositive-scale"),
                      "UndefinedReasonMismatch", "diagnostic.empty")

    def test_single_signed_zero_subnormal_and_negative_coordinate_words(self):
        raw, stdout, _ = fixture(1, signed=True)
        parsed = bridge.parse_transcript(raw, stdout)
        self.assertEqual(parsed["source"]["particles"][0]["position"], [NEG_ONE, NZ, SUB])
        self.assertEqual(parsed["source"]["time"], NZ)
        self.assertEqual(parsed["evaluation"]["samples"][0]["force"], [Z] * 3)
        self.assertEqual(parsed["diagnostics"]["virial_residual"]["value"], "nonpositive-scale")

    def test_distinct_coincident_sources_retain_negative_potential_and_energy(self):
        raw, stdout, _ = fixture(2)
        parsed = bridge.parse_transcript(raw, stdout)
        self.assertEqual([s["id"] for s in parsed["evaluation"]["samples"]], [ID1, ID2])
        self.assertEqual(parsed["evaluation"]["scales"]["pair_energy"], NEG_ONE)
        self.assertEqual([s["phi"] for s in parsed["evaluation"]["samples"]], [NEG_ONE, NEG_ONE])

    def test_input_order_is_separate_from_sorted_particles_and_samples(self):
        raw, stdout, _ = fixture(2, shuffled=True)
        parsed = bridge.parse_transcript(raw, stdout)
        self.assertEqual(parsed["source"]["input_order"], [ID2, ID1])
        self.assertEqual([p["id"] for p in parsed["source"]["particles"]], [ID1, ID2])
        altered = stdout.replace(("input_order " + ID2).encode(), ("input_order " + ID1).encode(), 1)
        self.rejected(raw, altered, "OrderMismatch", "stdout.input_order")

    def test_truncated_extra_and_reordered_protocol_rows_reject_causally(self):
        raw, stdout, _ = fixture()
        bridge.parse_transcript(raw, stdout)
        self.rejected(raw, stdout[:-4], "Truncated", "stdout.end")
        self.rejected(raw, stdout + b"unexpected\n", "TrailingContent", "stdout")
        self.rejected(raw, stdout.replace(b"status complete", b"case complete", 1), "UnexpectedToken", "stdout.status")
        self.rejected(raw + b"extra\n", stdout, "TrailingContent", "input")

    def test_ascii_caps_labels_and_rust_whitespace_are_explicit(self):
        raw, stdout, _ = fixture()
        self.rejected(raw.replace(b"case SCHEMA_ONLY", b"case bad/label"), stdout, "InvalidLabel", "input.case")
        self.rejected(raw[:-1], stdout, "InvalidASCII", "input")
        self.rejected(raw.replace(b"stage ", b"stage\x0b"), stdout, "UnexpectedToken", "input.stage")
        with self.assertRaises(bridge.BridgeError) as caught:
            bridge.parse_input(b"x" * (bridge.MAX_INPUT_BYTES + 1))
        self.assertEqual(caught.exception.code, "ResourceLimit")

    def test_unsigned_narrowing_bounds_and_snapshot_cap(self):
        raw, stdout, _ = fixture()
        bridge.parse_transcript(raw, stdout)
        for old, new, code, field in [
                (b"backend 9", b"backend 09", "InvalidDecimal", "input.backend"),
                (b"backend 9", b"backend 18446744073709551616", "IntegerOverflow", "input.backend"),
                (b"softening " + ONE.encode() + b" 7", b"softening " + ONE.encode() + b" 65536", "IntegerOverflow", "input.class"),
                (b"count 0", b"count 33", "SourceLimit", "input.count")]:
            with self.subTest(field=field):
                self.rejected(raw.replace(old, new), stdout, code, field)
        one, out, _ = fixture(1)
        self.rejected(one.replace(b"dm 1 2 7", b"dm 1 4294967296 7"), out, "IntegerOverflow", "input.particle.0.galaxy")
        self.rejected(one.replace(b"dm 1 2 7", b"dm 65536 2 7"), out, "IntegerOverflow", "input.particle.0.component")

    def test_word_width_uppercase_nonfinite_and_positive_boundaries(self):
        raw, stdout, _ = fixture()
        bridge.parse_transcript(raw, stdout)
        for word, code in [("3FF0000000000000", "InvalidWord"), ("3ff000000000000", "InvalidWord"),
                           ("7ff0000000000000", "NonfiniteWord"), ("7ff8000000000001", "NonfiniteWord"),
                           (NZ, "NonpositiveEpsilon"), (SUB, "Nonrepresentable")]:
            changed = raw.replace(("softening " + ONE).encode(), ("softening " + word).encode())
            with self.subTest(word=word):
                self.rejected(changed, stdout, code, "input.epsilon_squared" if word == SUB else "input.epsilon")

    def test_identity_species_duplicate_class_and_mass_rejections(self):
        raw, stdout, _ = fixture(2)
        bridge.parse_transcript(raw, stdout)
        self.rejected(raw.replace(ID2.encode(), ID1.encode()), stdout, "DuplicateId", "input.particles")
        self.rejected(raw.replace(b" star ", b" gas "), stdout, "InvalidSpecies", "input.particle.1")
        self.rejected(raw.replace(b"dm 1 2 7", b"dm 1 2 8"), stdout, "ClassMismatch", "input.particles")
        self.rejected(raw.replace(("dm 1 2 7 " + ONE).encode(), ("dm 1 2 7 " + NZ).encode()),
                      stdout, "NonpositiveMass", "input.particle.0")
        self.rejected(raw.replace(ID1.encode(), b"A" * 32), stdout, "InvalidId", "input.particle.0.id")
        self.rejected(raw.replace(ID1.encode(), b"0" * 31), stdout, "InvalidId", "input.particle.0.id")
        one, _, _ = fixture(1)
        zero_id = bridge.parse_input(one.replace(ID1.encode(), b"0" * 32))
        self.assertEqual(zero_id["input_order"], ["0" * 32])

    def test_raw_input_digest_and_clock_backend_echo(self):
        raw, stdout, _ = fixture()
        bridge.parse_transcript(raw, stdout)
        self.rejected(raw + b"\n", stdout, "RawInputDigest", "stdout.input_sha256")
        self.rejected(raw, stdout.replace(("clock " + NZ + " 11").encode(), ("clock " + Z + " 11").encode(), 1),
                      "EchoMismatch", "stdout.clock")
        self.rejected(raw, stdout.replace(b"backend_revision 9", b"backend_revision 10"), "EchoMismatch", "stdout.backend_revision")

    def test_particle_metadata_and_sorted_sample_echo_are_checked(self):
        raw, stdout, _ = fixture(2)
        bridge.parse_transcript(raw, stdout)
        for old, new in [(b"star 3 4 7", b"star 3 5 7"), (b"star 3 4 7", b"dm 3 4 7")]:
            with self.subTest(new=new):
                self.rejected(raw, stdout.replace(old, new), "ParticleEchoMismatch", "stdout.particle.1")
        self.rejected(raw, stdout.replace(("sample " + ID1).encode(), ("sample " + ID2).encode(), 1),
                      "SampleOrderMismatch", "sample.0")

    def test_complete_primary_identity_bodies_not_just_matching_digests(self):
        raw, stdout, _ = fixture(1)
        bridge.parse_transcript(raw, stdout)
        for label in ["sources", "state", "model", "units", "backend"]:
            with self.subTest(label=label):
                altered = body_change(stdout, label, lambda body: b"X" + body[1:])
                self.rejected(raw, altered, "CanonicalMismatch", "identity." + label)

    def test_all_cache_copies_and_exact_end_are_required(self):
        raw, stdout, _ = fixture(1)
        bridge.parse_transcript(raw, stdout)
        for label in ["sources", "state", "model", "units", "backend"]:
            with self.subTest(label=label):
                altered = body_change(stdout, "cache_" + label, lambda body: body + b"\0")
                self.rejected(raw, altered, "BodyTrailingContent", "cache." + label)
        self.rejected(raw, stdout.replace(("cache_clock " + NZ + " 11").encode(),
                                          ("cache_clock " + NZ + " 12").encode()), "CacheClockMismatch", "cache.clock")

    def test_declared_length_hex_digest_and_truncated_body_are_distinct(self):
        raw, stdout, meta = fixture()
        bridge.parse_transcript(raw, stdout)
        body = meta["bodies"]["sources"]
        prefix = ("identity sources " + str(len(body)) + " ").encode()
        self.rejected(raw, stdout.replace(prefix, ("identity sources " + str(len(body) + 1) + " ").encode(), 1),
                      "BodyLengthOrHex", "identity.sources")
        self.rejected(raw, stdout.replace(prefix + digest(body).encode(), prefix + b"0" * 64, 1),
                      "BodyDigest", "identity.sources")
        self.rejected(raw, body_change(stdout, "sources", lambda b: b[:-1]), "BodyTruncated", "identity.sources")

    def test_private_evaluation_pins_and_pair_count_are_consumed(self):
        raw, stdout, meta = fixture(2)
        bridge.parse_transcript(raw, stdout)
        for key, replacement, field in [("private_G", words([TWO]), "evaluation.private_G"),
                                        ("private_epsilon", words([TWO]), "evaluation.private_epsilon"),
                                        ("pair_count", be(2), "evaluation.pair_count"),
                                        ("sample_count", be(1), "evaluation.sample_count")]:
            offset = meta["offsets"][key]
            altered = body_change(stdout, "evaluation", lambda b: b[:offset] + replacement + b[offset + 8:])
            with self.subTest(key=key):
                self.rejected(raw, altered, "CanonicalMismatch", field)

    def test_readable_samples_and_global_scales_must_match_evaluation(self):
        raw, stdout, _ = fixture(2)
        bridge.parse_transcript(raw, stdout)
        old = ("sample " + ID1 + " " + Z).encode()
        self.rejected(raw, stdout.replace(old, ("sample " + ID1 + " " + ONE).encode(), 1),
                      "CanonicalMismatch", "evaluation.sample.0.word.0")
        old = ("evaluation_scales " + NEG_ONE + " " + ONE).encode()
        self.rejected(raw, stdout.replace(old, ("evaluation_scales " + NEG_ONE + " " + TWO).encode(), 1),
                      "CanonicalMismatch", "evaluation.energy_scale")
        self.rejected(raw, body_change(stdout, "evaluation", lambda b: b + b"\0"), "BodyTrailingContent", "evaluation.bytes")

    def test_counts_model_units_and_diagnostic_duplicate_cannot_disagree(self):
        raw, stdout, _ = fixture(2)
        bridge.parse_transcript(raw, stdout)
        self.rejected(raw, stdout.replace(b"counts 2 1", b"counts 2 2"), "CountMismatch", "stdout.counts")
        self.rejected(raw, stdout.replace(("excluded " + ONE).encode(), ("excluded " + TWO).encode(), 1),
                      "EchoMismatch", "stdout.model")
        self.rejected(raw, stdout.replace(b"units_physical false", b"units_physical true"), "UnexpectedToken", "stdout.units_physical")
        self.rejected(raw, stdout.replace(("diagnostic pair_energy " + NEG_ONE).encode(), ("diagnostic pair_energy " + Z).encode()),
                      "DiagnosticMismatch", "diagnostic.pair_energy")

    def test_defined_virial_and_nonempty_options_have_distinct_failure_branches(self):
        raw, stdout, _ = fixture(2, moving=True)
        parsed = bridge.parse_transcript(raw, stdout)
        self.assertEqual(parsed["diagnostics"]["virial_residual"], {"kind": "defined", "value": ONE})
        self.rejected(raw, stdout.replace(("defined " + ONE).encode(), b"undefined nonpositive-scale"),
                      "UndefinedReasonMismatch", "diagnostic.virial_residual")
        old = ("diagnostic center_velocity some " + " ".join([Z] * 3)).encode()
        self.rejected(raw, stdout.replace(old, b"diagnostic center_velocity none"),
                      "MissingDiagnostic", "diagnostic.nonempty")

    def test_si_words_and_all_derived_unit_fields_bind_actual_G(self):
        raw, stdout, _ = fixture(1, si=True, g=TWO)
        parsed = bridge.parse_transcript(raw, stdout)
        self.assertEqual(parsed["g_code_bits"], TWO)
        self.assertEqual(parsed["source"]["units"]["inputs"], [ONE, ONE, ONE, TWO, ONE])
        # Last unit word is actual G-code; mutate a derived scale while retaining hash correctness.
        altered = body_change(stdout, "units", lambda b: b[:-16] + words([TWO]) + b[-8:])
        self.rejected(raw, altered, "CanonicalMismatch", "identity.units")
        g1, out, _ = fixture()
        self.rejected(g1.replace(b"units dimensionless-g1", ("units dimensionless-g1 " + TWO).encode()), out,
                      "UnexpectedToken", "input.softening")

    def test_nontrivial_unit_sqrt_RN_even_and_checked_velocity_boundaries(self):
        # Independent mathematical controls, not measured physical-unit agreement.
        # The literal sqrt(2) significand is between these exact squared
        # rounding midpoints; this is not another call to sqrt_word as oracle.
        n = int("16a09e667f3bcd", 16)
        self.assertLess((2 * n - 1) ** 2, 1 << 107)
        self.assertLess(1 << 107, (2 * n + 1) ** 2)
        self.assertEqual(bridge.sqrt_word(TWO, "control.sqrt"), "3ff6a09e667f3bcd")
        self.assertEqual(bridge.sqrt_word(ONE, "control.sqrt"), ONE)
        raw, stdout, _ = fixture(1)
        old = ("7 " + ONE + " " + Z + " " + Z + " " + Z + " " + Z + " " + Z + " " + Z).encode()
        new = ("7 " + SUB + " " + Z + " " + Z + " " + Z + " 7fefffffffffffff " + Z + " " + Z).encode()
        self.rejected(raw.replace(old, new), stdout, "Nonrepresentable", "input.particle.0.velocity.0")

    def test_actual_word_projection_preserves_metadata_and_separate_identities(self):
        raw, stdout, _ = fixture(2, shuffled=True, signed=True)
        snapshot = bridge.decode_snapshot(raw, stdout, b"", process_control(raw, stdout))
        projected = bridge.project_reference(snapshot)
        emitted = json.loads(projected["reference_input_bytes"])
        canonical = json.loads(projected["canonical_reference_input_bytes"])
        numeric = json.loads(projected["numeric_reference_input_bytes"])
        self.assertEqual([s["id"]["payload_hex"] for s in emitted["sources"]], [ID2, ID1])
        self.assertEqual([s["id"]["payload_hex"] for s in canonical["sources"]], [ID1, ID2])
        self.assertEqual(canonical["sources"][0]["position_bits"], [NEG_ONE, NZ, SUB])
        self.assertEqual(numeric["sources"][0]["position_bits"], [NEG_ONE, Z, SUB])
        join = projected["join"]
        self.assertEqual(join["checked_source"]["time"], NZ)
        self.assertEqual(join["checked_source"]["revision"], 11)
        self.assertEqual(join["original_ascii_input_sha256"], digest(raw))
        self.assertNotEqual(join["raw_reference_input_sha256"], join["word_preserving_sorted_reference_sha256"])
        self.assertNotEqual(join["numeric_reference_input_sha256"], join["word_preserving_sorted_reference_sha256"])
        self.assertFalse(join["scope"]["component_accepted"])
        self.assertFalse(join["scope"]["candidate_comparison_run"])

    def test_si_reference_projection_does_not_convert_code_state_twice(self):
        raw, stdout, _ = fixture(1, si=True, g=TWO, signed=True)
        snapshot = bridge.decode_snapshot(raw, stdout, b"", process_control(raw, stdout))
        p = bridge.project_reference(snapshot)
        reference = json.loads(p["reference_input_bytes"])
        self.assertEqual(reference["model"]["g_code_bits"], TWO)
        self.assertEqual(reference["model"]["epsilon_code_bits"], ONE)
        self.assertEqual(reference["sources"][0]["mass_bits"], ONE)
        self.assertEqual(reference["sources"][0]["position_bits"], [NEG_ONE, NZ, SUB])
        self.assertEqual(p["join"]["checked_source"]["time"], NZ)
        self.assertEqual(set(reference), {"schema", "model", "sources"})

    def test_process_nonzero_timeout_unclosed_and_bool_exit_are_not_success(self):
        raw, stdout, _ = fixture()
        bridge.parse_transcript(raw, stdout)
        for key, value in [("returncode", 1), ("returncode", False), ("timed_out", True),
                           ("logs_closed", False), ("writers_stopped", False), ("outcome", "running")]:
            evidence = process_control(raw, stdout)
            evidence[key] = value
            with self.subTest(key=key, value=value):
                with self.assertRaises(bridge.BridgeError) as caught:
                    bridge.decode_snapshot(raw, stdout, b"", evidence)
                self.assertEqual((caught.exception.code, caught.exception.field), ("ProcessNotSuccessful", "process"))

    def test_process_buffers_and_forged_carrier_cannot_bypass_rechecking(self):
        raw, stdout, _ = fixture()
        evidence = process_control(raw, stdout)
        evidence["stdout_sha256"] = "0" * 64
        with self.assertRaises(bridge.BridgeError) as caught:
            bridge.decode_snapshot(raw, stdout, b"", evidence)
        self.assertEqual(caught.exception.code, "ProcessBufferMismatch")
        good = bridge.decode_snapshot(raw, stdout, b"", process_control(raw, stdout))
        forged = bridge.Snapshot(raw, stdout + b"extra\n", b"", good.process_json)
        with self.assertRaises(bridge.BridgeError) as caught:
            bridge.project_reference(forged)
        self.assertEqual(caught.exception.code, "ProcessBufferMismatch")
        for invalid in [b"{", "not bytes", b"x" * 16385]:
            with self.subTest(carrier=type(invalid).__name__, size=len(invalid)):
                carrier = bridge.Snapshot(raw, stdout, b"", invalid)
                with self.assertRaises(bridge.BridgeError) as caught:
                    bridge.project_reference(carrier)
                self.assertEqual((caught.exception.code, caught.exception.field),
                                 ("ProcessSchema", "projection.process_json"))
        carrier = bridge.Snapshot("not bytes", stdout, b"", good.process_json)
        with self.assertRaises(bridge.BridgeError) as caught:
            bridge.project_reference(carrier)
        self.assertEqual((caught.exception.code, caught.exception.field), ("ProcessSchema", "process.buffers"))


if __name__ == "__main__":
    unittest.main()
