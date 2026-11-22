#!/usr/bin/env python3
"""Independent, bounded GP-2 arithmetic; SOURCE PROPOSAL, not G1 acceptance.

No numerical work or helper import occurs on import. The CLI is intended for
one retained input per future REANA workflow, after independent source review.
The binary64 codec is a disclosed, SHA-pinned shared reference dependency.
"""

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
from dataclasses import dataclass
from fractions import Fraction


INPUT_SCHEMA = "openmhd.gravity-force-reference-input.v1"
REFERENCE_SCHEMA = "openmhd.gravity-force-reference.v1"
STATUS_SCHEMA = "openmhd.gravity-force-reference-status.v1"
HELPER_SHA256 = "2b9f55d5ed72a08a90c3445fcd62b7702598174e04603e7ecd0d672c387df2df"
MAX_SOURCES = 32
MAX_INPUT_BYTES = 1 << 20
MAX_OUTPUT_BYTES = 16 << 20
MAX_INTEGER_BITS = 65536
MAX_TERMS = 2048
MAX_ARITHMETIC_GROUPS = 2_000_000
PRECISION_SCHEDULE = (64, 128, 256, 512, 1024, 2048, 4096)
WORD = re.compile(r"[0-9a-f]{16}\Z")
PAYLOAD = re.compile(r"[0-9a-f]{32}\Z")
_CODEC = None


class ReferenceError(Exception):
    """Typed rejection; never a passing tolerance or a replacement value."""

    def __init__(self, code, stage, message):
        self.code, self.stage = code, stage
        super().__init__(message)


def require(condition, code, stage, message):
    if not condition:
        raise ReferenceError(code, stage, message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def read_regular(path, limit):
    """One bounded regular-file buffer; no final symlink or changing fstat."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    require(hasattr(os, "O_NOFOLLOW"), "UnsupportedHost", "io", "O_NOFOLLOW is required")
    try:
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode), "InvalidFile", "io", "Not a regular file")
            require(before.st_size <= limit, "ResourceLimit", "io", "Input/source size limit")
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
    except OSError as exc:
        raise ReferenceError("InputUnavailable", "io", type(exc).__name__) from exc
    require(len(raw) <= limit and len(raw) == before.st_size,
            "ResourceLimit", "io", "File size changed or exceeds limit")
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
            "InputChanged", "io", "File changed during capture")
    return raw


def _load_binary64_helper(path):
    raw = read_regular(path, MAX_INPUT_BYTES)
    require(digest(raw) == HELPER_SHA256, "HelperIdentity", "source", "Binary64 helper hash mismatch")
    # Execute ONLY those pinned retained bytes, not a second mutable-path read.
    # Source review/import preflight precedes future use; no outside dependency.
    spec = importlib.util.spec_from_loader("_g1_pinned_binary64_reference", loader=None)
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def codec():
    global _CODEC
    if _CODEC is None:
        _CODEC = _load_binary64_helper(Path(__file__).with_name("galaxy_geometry3_reference.py"))
    return _CODEC


class Budget:
    """Checked operation GROUP budget, not a Rust flop count or OS time bound."""

    def __init__(self, groups=MAX_ARITHMETIC_GROUPS, integer_bits=MAX_INTEGER_BITS):
        require(type(groups) is int and 0 < groups <= MAX_ARITHMETIC_GROUPS
                and type(integer_bits) is int and 0 < integer_bits <= MAX_INTEGER_BITS,
                "ResourceLimit", "arithmetic", "Invalid budget")
        self.groups, self.integer_bits, self.used = groups, integer_bits, 0

    def check(self, *values):
        self.used += 1
        require(self.used <= self.groups, "ResourceLimit", "arithmetic", "Arithmetic group budget exhausted")
        for value in values:
            require(type(value) in (int, Fraction), "InternalArithmetic", "arithmetic", "Nonrational operand")
            parts = (value.numerator, value.denominator) if isinstance(value, Fraction) else (value,)
            require(all(abs(part).bit_length() <= self.integer_bits for part in parts),
                    "ResourceLimit", "arithmetic", "Integer size budget exhausted")
        return values[0] if len(values) == 1 else values


def q_record(value):
    """Hex integers avoid decimal digit-limit/float serialization ambiguities."""
    value = Fraction(value)
    return {"numerator_hex": format(value.numerator, "x"),
            "denominator_hex": format(value.denominator, "x")}


def exact_keys(value, keys, stage):
    require(type(value) is dict and set(value) == set(keys),
            "InvalidSchema", stage, "Exact object key set required")


def _pairs_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "InvalidSchema", "input", "Duplicate JSON key")
        result[key] = value
    return result


def _reject_number(_text):
    raise ReferenceError("InvalidSchema", "input", "JSON numeric tokens are forbidden; use binary64 words")


def parse_word(word, positive=False):
    require(type(word) is str and WORD.fullmatch(word) is not None,
            "InvalidWord", "input", "Expected 16 lower-case hex digits")
    bits = int(word, 16)
    require((bits >> 52) & 0x7ff != 0x7ff, "NonfiniteInput", "input", "Nonfinite binary64 word")
    value = codec().exact_binary64(bits)
    require(not positive or value > 0, "NonpositiveInput", "input", "Expected strictly positive input")
    return value


@dataclass(frozen=True)
class Source:
    payload: str
    mass: Fraction
    position: tuple


@dataclass(frozen=True)
class PhysicalInput:
    raw_sha256: str
    canonical_sha256: str
    canonical: bytes
    g: Fraction
    epsilon: Fraction
    sources: tuple


def parse_input(raw):
    require(type(raw) is bytes and len(raw) <= MAX_INPUT_BYTES,
            "ResourceLimit", "input", "Input must be bounded bytes")
    try:
        data = json.loads(raw, object_pairs_hook=_pairs_object, parse_int=_reject_number,
                          parse_float=_reject_number, parse_constant=_reject_number)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ReferenceError("InvalidSchema", "input", "Malformed JSON") from exc
    exact_keys(data, ("schema", "model", "sources"), "input")
    require(data["schema"] == INPUT_SCHEMA, "InvalidSchema", "input", "Wrong schema")
    model = data["model"]
    exact_keys(model, ("boundary", "kernel", "self_interaction", "g_code_bits", "epsilon_code_bits"), "input")
    require(model["boundary"] == "isolated" and model["kernel"] == "common-fixed-plummer"
            and model["self_interaction"] == "excluded", "UnsupportedModel", "input", "GP-2 isolated model required")
    g = parse_word(model["g_code_bits"], positive=True)
    epsilon = parse_word(model["epsilon_code_bits"], positive=True)
    require(type(data["sources"]) is list and len(data["sources"]) <= MAX_SOURCES,
            "ResourceLimit", "input", "Source count limit")
    sources, seen = [], set()
    for row in data["sources"]:
        exact_keys(row, ("id", "mass_bits", "position_bits"), "input")
        exact_keys(row["id"], ("wrapper", "payload_hex"), "input")
        payload = row["id"]["payload_hex"]
        require(row["id"]["wrapper"] == "ParticleId" and type(payload) is str
                and PAYLOAD.fullmatch(payload) is not None,
                "InvalidIdentity", "input", "Explicit ParticleId payload required")
        require(payload not in seen, "DuplicateIdentity", "input", "Duplicate persistent payload")
        seen.add(payload)
        mass = parse_word(row["mass_bits"], positive=True)
        require(type(row["position_bits"]) is list and len(row["position_bits"]) == 3,
                "InvalidSchema", "input", "Exactly three position words required")
        position = tuple(parse_word(word) for word in row["position_bits"])
        sources.append(Source(payload, mass, position))
    # Word-preserving canonical order is distinct from input-byte identity.
    data["sources"].sort(key=lambda row: row["id"]["payload_hex"])
    canonical = json_bytes(data)
    return PhysicalInput(digest(raw), digest(canonical), canonical, g, epsilon,
                         tuple(sorted(sources, key=lambda source: source.payload)))


def rational_sqrt(value, budget):
    value = Fraction(value)
    require(value >= 0, "InternalArithmetic", "radical", "Negative radicand")
    budget.check(value)
    n, d = math.isqrt(value.numerator), math.isqrt(value.denominator)
    budget.check(n * n, d * d)
    return Fraction(n, d) if n * n == value.numerator and d * d == value.denominator else None


class Expression:
    """Sum of exact c*sqrt(q); no candidate-order floating accumulation."""

    def __init__(self, budget):
        self.budget, self.terms = budget, {}

    def add_term(self, coefficient, radicand):
        coefficient, radicand = Fraction(coefficient), Fraction(radicand)
        self.budget.check(coefficient, radicand)
        require(radicand >= 0, "InternalArithmetic", "radical", "Negative radicand")
        if coefficient == 0 or radicand == 0:
            return self
        value = self.budget.check(self.terms.get(radicand, Fraction(0)) + coefficient)
        if value:
            self.terms[radicand] = value
        else:
            self.terms.pop(radicand, None)
        require(len(self.terms) <= MAX_TERMS, "ResourceLimit", "arithmetic", "Expression term limit")
        return self

    def add(self, other, factor=1):
        factor = Fraction(factor)
        for radicand, coefficient in sorted(other.terms.items()):
            self.add_term(self.budget.check(coefficient * factor), radicand)
        return self

    def normalized(self):
        # Quotient-square equivalence detects cancellation without factoring.
        result = Expression(self.budget)
        for q, c in sorted(self.terms.items()):
            root = rational_sqrt(q, self.budget)
            if root is not None:
                result.add_term(self.budget.check(c * root), Fraction(1))
                continue
            merged = False
            for base in sorted(result.terms):
                ratio = self.budget.check(q / base)
                root = rational_sqrt(ratio, self.budget)
                if root is not None:
                    result.add_term(self.budget.check(c * root), base)
                    merged = True
                    break
            if not merged:
                result.add_term(c, q)
        return result

    def record(self):
        return [{"coefficient": q_record(c), "radicand": q_record(q)}
                for q, c in sorted(self.terms.items())]


def sqrt_interval(q, bits, budget):
    require(type(bits) is int and 0 <= bits <= PRECISION_SCHEDULE[-1],
            "ResourceLimit", "radical", "Radical precision limit")
    root = rational_sqrt(q, budget)
    if root is not None:
        return root, root
    scaled = budget.check(q.numerator << (2 * bits))
    lower_integer = math.isqrt(budget.check(scaled // q.denominator))
    denominator = budget.check(1 << bits)
    lower = budget.check(Fraction(lower_integer, denominator))
    upper = budget.check(Fraction(lower_integer + 1, denominator))
    return lower, upper


def expression_interval(expression, bits):
    lower, upper = Fraction(0), Fraction(0)
    for q, c in sorted(expression.terms.items()):
        lo, hi = sqrt_interval(q, bits, expression.budget)
        if c < 0:
            lo, hi = hi, lo
        lower = expression.budget.check(lower + expression.budget.check(c * lo))
        upper = expression.budget.check(upper + expression.budget.check(c * hi))
    return lower, upper


def certify(expression, schedule=PRECISION_SCHEDULE):
    require(type(schedule) is tuple and len(schedule) > 0
            and all(type(k) is int and 0 <= k <= PRECISION_SCHEDULE[-1] for k in schedule)
            and all(a < b for a, b in zip(schedule, schedule[1:])),
            "ResourceLimit", "rounding", "Invalid refinement schedule")
    expression = expression.normalized()
    exact_rational = all(q == 1 for q in expression.terms)
    for bits in ((0,) if exact_rational else schedule):
        lower, upper = expression_interval(expression, bits)
        try:
            lo_word = codec().binary64_bits(lower)
            hi_word = codec().binary64_bits(upper)
        except ValueError as exc:
            if exact_rational:
                raise ReferenceError("FiniteRoundingRequired", "rounding", "Exact result has no finite rounded word") from exc
            continue
        if lo_word == hi_word:
            rounded = codec().exact_binary64(lo_word)
            error = expression.budget.check(max(abs(rounded - lower), abs(rounded - upper)))
            return {"expression": expression.record(), "structural_zero": not expression.terms,
                    "exact_rational": exact_rational,
                    "enclosure": {"lower": q_record(lower), "upper": q_record(upper)},
                    "nearest_binary64": format(lo_word, "016x"),
                    "sqrt_fraction_bits": None if exact_rational else bits,
                    "rounding_error_bound": q_record(error)}
    raise ReferenceError("RoundingUnresolved", "rounding", "No unique finite rounded word within refinement budget")


def dot(a, b, budget):
    total = Fraction(0)
    for x, y in zip(a, b):
        total = budget.check(total + budget.check(x * y))
    return total


def cross(a, b, budget):
    return tuple(budget.check(budget.check(a[(k + 1) % 3] * b[(k + 2) % 3])
                              - budget.check(a[(k + 2) % 3] * b[(k + 1) % 3])) for k in range(3))


def evaluate(physical, budget=None, schedule=PRECISION_SCHEDULE):
    """Only a validated collisionless physical input; no orbit/cache/unit claim."""
    require(type(physical) is PhysicalInput, "InvalidSchema", "evaluation", "Parsed physical input required")
    # Recheck the public immutable carrier against its word-preserving body;
    # constructing a dataclass must not bypass source/model/resource checks.
    checked = parse_input(physical.canonical)
    require(type(physical.raw_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", physical.raw_sha256)
            and physical.canonical == checked.canonical
            and physical.canonical_sha256 == checked.canonical_sha256
            and physical.g == checked.g and physical.epsilon == checked.epsilon
            and physical.sources == checked.sources,
            "InvalidSchema", "evaluation", "Physical input carrier/body mismatch")
    budget = Budget() if budget is None else budget
    require(type(budget) is Budget, "ResourceLimit", "evaluation", "Checked budget required")
    new = lambda: Expression(budget)
    rows, ordered_terms, pairs = {}, [], []
    net_force, net_torque = [new() for _ in range(3)], [new() for _ in range(3)]
    total_energy, energy_scale, net_force_scale, net_torque_scale = new(), new(), new(), new()
    half_sum_mass_phi = new()
    epsilon2 = budget.check(physical.epsilon * physical.epsilon)

    def pair_data(left, right):
        d = tuple(budget.check(b - a) for a, b in zip(left.position, right.position))
        r2 = dot(d, d, budget)
        q = budget.check(r2 + epsilon2)
        q2 = budget.check(q * q)
        coefficient = budget.check(budget.check(budget.check(physical.g * left.mass) * right.mass) / q2)
        return d, r2, q, coefficient

    # Each owner's directed contributions are independently constructed. This
    # is deliberately distinct from Rust's paired Neumaier f64 accumulator.
    for owner in physical.sources:
        force, torque = [new() for _ in range(3)], [new() for _ in range(3)]
        component_abs, torque_component_abs = [new() for _ in range(3)], [new() for _ in range(3)]
        phi, force_scale, phi_scale = new(), new(), new()
        for source in physical.sources:
            if owner.payload == source.payload:
                continue
            d, r2, q, coefficient = pair_data(owner, source)
            fc = tuple(budget.check(coefficient * coordinate) for coordinate in d)
            tc = cross(owner.position, fc, budget)
            pc = budget.check(-budget.check(physical.g * source.mass) / q)
            for axis in range(3):
                force[axis].add_term(fc[axis], q)
                torque[axis].add_term(tc[axis], q)
                component_abs[axis].add_term(abs(fc[axis]), q)
                torque_component_abs[axis].add_term(abs(tc[axis]), q)
            phi.add_term(pc, q)
            phi_scale.add_term(-pc, q)
            force_scale.add_term(coefficient, budget.check(r2 * q))
            ordered_terms.append({"owner": owner.payload, "source": source.payload,
                                  "displacement": [q_record(v) for v in d],
                                  "softened_distance_squared": q_record(q),
                                  "force_sqrt_q_coefficients": [q_record(v) for v in fc],
                                  "torque_sqrt_q_coefficients": [q_record(v) for v in tc],
                                  "phi_sqrt_q_coefficient": q_record(pc)})
        for axis in range(3):
            net_force[axis].add(force[axis])
            net_torque[axis].add(torque[axis])
        half_sum_mass_phi.add(phi, budget.check(owner.mass / 2))
        rows[owner.payload] = {"id_wrapper": "ParticleId", "force": [certify(e, schedule) for e in force],
                               "specific_potential": certify(phi, schedule),
                               "torque_about_input_origin": [certify(e, schedule) for e in torque],
                               "scales": {"force_magnitude_sum": certify(force_scale, schedule),
                                          "potential_absolute_sum": certify(phi_scale, schedule),
                                          "force_component_absolute_sums": [certify(e, schedule) for e in component_abs],
                                          "torque_component_absolute_sums": [certify(e, schedule) for e in torque_component_abs]}}

    # Independent unordered energy pass; U is not defined by sum(m Phi)/2.
    for index, left in enumerate(physical.sources):
        for right in physical.sources[index + 1:]:
            d, r2, q, coefficient = pair_data(left, right)
            uc = budget.check(-budget.check(budget.check(physical.g * left.mass) * right.mass) / q)
            pair_u, magnitude = new().add_term(uc, q), new().add_term(coefficient, budget.check(r2 * q))
            total_energy.add(pair_u)
            energy_scale.add(pair_u, -1)
            net_force_scale.add(magnitude, 2)
            for position in (left.position, right.position):
                radicand = budget.check(budget.check(dot(position, position, budget) * r2) * q)
                net_torque_scale.add_term(coefficient, radicand)
            pairs.append({"left": left.payload, "right": right.payload,
                          "softened_distance_squared": q_record(q),
                          "energy": certify(pair_u, schedule),
                          "force_magnitude": certify(magnitude, schedule)})
    identity_residual = new().add(half_sum_mass_phi).add(total_energy, -1)
    result = {"schema": REFERENCE_SCHEMA,
              "input": {"original_sha256": physical.raw_sha256,
                        "word_preserving_sorted_sha256": physical.canonical_sha256},
              "source_count": len(physical.sources), "unordered_pair_count": len(pairs),
              "samples_by_particle_id": rows, "ordered_source_terms": ordered_terms,
              "unordered_pairs": pairs, "pair_energy": certify(total_energy, schedule),
              "raw_net_force": [certify(e, schedule) for e in net_force],
              "raw_net_torque_about_input_origin": [certify(e, schedule) for e in net_torque],
              "half_sum_mass_phi_minus_pair_energy": certify(identity_residual, schedule),
              "independent_scales": {"energy_absolute_sum": certify(energy_scale, schedule),
                                     "net_force_interaction_sum": certify(net_force_scale, schedule),
                                     "net_torque_interaction_sum": certify(net_torque_scale, schedule)},
              "scope": {"physical_evolutions_run": False, "candidate_comparison_run": False,
                        "rust_cache_serialization_certified": False, "physical_units_certified": False,
                        "component_accepted": False, "merger_accepted": False}}
    # These are this implementation's checked groups, not candidate flop/error bounds.
    result["reference_resources"] = {"checked_arithmetic_groups": budget.used,
                                     "max_groups": budget.groups, "max_integer_bits": budget.integer_bits,
                                     "source_limit": MAX_SOURCES, "term_limit": MAX_TERMS,
                                     "sqrt_fraction_bits_schedule": list(schedule)}
    require(len(json_bytes(result)) <= MAX_OUTPUT_BYTES, "ResourceLimit", "export", "Reference output size limit")
    return result


def _write_new(path, raw):
    with open(path, "xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _replace_status(root, value):
    # Private fresh directory. Retain a temporary if publication fails.
    temporary = root / "status.pending.json"
    _write_new(temporary, json_bytes(value))
    os.replace(temporary, root / "status.json")


def _close_manifest(root):
    entries = {}
    for path in sorted(root.iterdir()):
        require(path.name != "files.sha256.json", "InvalidDestination", "export", "Manifest already exists")
        raw = read_regular(path, MAX_OUTPUT_BYTES)
        entries[path.name] = {"sha256": digest(raw), "bytes": len(raw)}
    _write_new(root / "files.sha256.json", json_bytes({"schema": "openmhd.gravity-reference-files.v1", "files": entries}))


def export_input(input_path, output):
    """Fresh one-input receipt, never an exportable full physical campaign."""
    root = Path(output)
    try:
        root.mkdir(mode=0o700, parents=False, exist_ok=False)
    except OSError as exc:
        raise ReferenceError("InvalidDestination", "export", type(exc).__name__) from exc
    status = {"schema": STATUS_SCHEMA, "status": "initializing", "reference_exported": False,
              "component_accepted": False, "merger_accepted": False, "physical_evolutions_run": False,
              "reference_arithmetic_attempted": False, "reference_arithmetic_completed": False,
              "problem": None}
    try:
        _replace_status(root, status)
        source_path = Path(__file__)
        helper_path = source_path.with_name("galaxy_geometry3_reference.py")
        source_raw = read_regular(source_path, MAX_INPUT_BYTES)
        helper_raw = read_regular(helper_path, MAX_INPUT_BYTES)
        require(digest(helper_raw) == HELPER_SHA256, "HelperIdentity", "source", "Binary64 helper hash mismatch")
        source_receipt = {"schema": "openmhd.gravity-reference-sources.v1", "files": {
            "scripts/galaxy_gravity_reference.py": {"sha256": digest(source_raw), "bytes": len(source_raw),
                                                     "copied_path": "galaxy_gravity_reference.py"},
            "scripts/galaxy_geometry3_reference.py": {"sha256": digest(helper_raw), "bytes": len(helper_raw),
                                                      "copied_path": "galaxy_geometry3_reference.py"}},
            "runtime": {"implementation": sys.implementation.name, "version": sys.version,
                        "optimize": sys.flags.optimize},
            "note": "Exact source identities only; no invented Git, Rust-cache, units or workflow certificate."}
        _write_new(root / "sources.json", json_bytes(source_receipt))
        _write_new(root / "galaxy_gravity_reference.py", source_raw)
        _write_new(root / "galaxy_geometry3_reference.py", helper_raw)
        raw = read_regular(input_path, MAX_INPUT_BYTES)
        _write_new(root / "input.json", raw)
        physical = parse_input(raw)
        _write_new(root / "canonical_physical_input.json", physical.canonical)
        status.update(reference_arithmetic_attempted=True)
        _replace_status(root, status)
        result = evaluate(physical)
        status.update(reference_arithmetic_completed=True)
        require(read_regular(input_path, MAX_INPUT_BYTES) == raw
                and read_regular(source_path, MAX_INPUT_BYTES) == source_raw
                and read_regular(helper_path, MAX_INPUT_BYTES) == helper_raw,
                "InputChanged", "export", "Source/input final fence failed")
        _write_new(root / "reference.json", json_bytes(result))
        status.update(status="complete", reference_exported=True)
        _replace_status(root, status)
        _close_manifest(root)
        return 0
    except BaseException as exc:
        if isinstance(exc, ReferenceError):
            problem = {"code": exc.code, "stage": exc.stage, "message": str(exc)}
        else:
            problem = {"code": type(exc).__name__, "stage": "unexpected", "message": "Reference export did not complete"}
        status.update(status="failed", reference_exported=False, problem=problem)
        # I/O/process loss can itself prevent closure; never turn that into success.
        try:
            _replace_status(root, status)
            if not (root / "files.sha256.json").exists():
                _close_manifest(root)
        except BaseException:
            pass
        return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        return export_input(args.input, args.output)
    except ReferenceError as exc:
        print(json.dumps({"code": exc.code, "stage": exc.stage}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
