"""SOURCE-ONLY static G1 bit bridge; no reference/force evaluation on import.

Canonical encodings are the explicitly pinned current Rust API, not a public
serialization standard. The caller must provide actual successful-process
evidence and separately retain source/compiler/binary/runtime/command joins.
This module never evaluates a force, repairs a residual, or accepts a component.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
from dataclasses import dataclass

MAX_INPUT_BYTES = 262144
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
MAX_BODY_BYTES = 65536
MAX_PARTICLES = 32
REFERENCE_SCHEMA = "openmhd.gravity-force-reference-input.v1"
HELPER_SHA256 = "2b9f55d5ed72a08a90c3445fcd62b7702598174e04603e7ecd0d672c387df2df"
REFERENCE_SOURCE_SHA256 = "91e11a87248f51f00dfa477708dd33f1f49b2cfd1e883a574991ec506fdeffbe"
DRIVER_SOURCE_SHA256 = "dceacc9a0b3a140ddb933e9357cbe898fea9b483e57cb4af63195e27247d68b9"
ZERO = "0000000000000000"
ONE = "3ff0000000000000"
CODEC = None
SOURCE_TAG = b"gravity-sources-v1\0collisionless\0"
STATE_TAG = b"gravity-catalog-v1\0"
MODEL_TAG = b"gravity-model-v1\0isolated-common-Plummer-no-self\0"
G1_TAG = b"gravity-units-v1\0dimensionless-G1-mu01"
SI_TAG = b"gravity-units-v1\0SI\0"
BACKEND_TAG = b"gravity-backend-v1\0serial-sorted-i<j-Neumaier\0"
EVALUATION_TAG = b"gravity-evaluation-v1\0"


class BridgeError(ValueError):
    def __init__(self, code, field):
        self.code, self.field = code, field
        super().__init__(code + ": " + field)


def require(condition, code, field):
    if not condition:
        raise BridgeError(code, field)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("ascii")


def finite_word(text, field):
    require(type(text) is str and re.fullmatch(r"[0-9a-f]{16}", text) is not None,
            "InvalidWord", field)
    require((int(text, 16) >> 52) & 0x7ff != 0x7ff, "NonfiniteWord", field)
    return text


def zero(text):
    return int(text, 16) & ((1 << 63) - 1) == 0


def positive(text):
    return not (int(text, 16) >> 63) and not zero(text)


def nonnegative(text):
    return positive(text) or zero(text)


def codec():
    """Disclosed shared exact codec, loaded only for future checked unit work.

    No gravity reference evaluation is called. Execute the one SHA-checked
    helper buffer, never import a second mutable path or change its globals.
    """
    global CODEC
    if CODEC is None:
        path = Path(__file__).with_name("galaxy_geometry3_reference.py")
        require(hasattr(os, "O_NOFOLLOW"), "HelperIdentity", "source.codec")
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
            with os.fdopen(fd, "rb") as stream:
                before = os.fstat(stream.fileno())
                require(stat.S_ISREG(before.st_mode) and before.st_size <= 1 << 20,
                        "HelperIdentity", "source.codec")
                raw = stream.read((1 << 20) + 1)
                after = os.fstat(stream.fileno())
            require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                    == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                    and len(raw) == before.st_size, "HelperIdentity", "source.codec")
        except OSError as exc:
            raise BridgeError("HelperIdentity", "source.codec") from exc
        require(len(raw) <= 1 << 20 and sha(raw) == HELPER_SHA256, "HelperIdentity", "source.codec")
        module = importlib.util.module_from_spec(importlib.util.spec_from_loader(
            "_gravity_bridge_pinned_codec", loader=None))
        module.__file__ = str(path)
        exec(compile(raw, str(path), "exec"), module.__dict__)
        CODEC = module
    return CODEC


def exact(word):
    return codec().exact_binary64(int(word, 16))


def rounded(value, field):
    helper = codec()
    try:
        result = format(helper.binary64_bits(value), "016x")
    except ValueError as exc:
        raise BridgeError("Nonrepresentable", field) from exc
    require(value == 0 or not zero(result), "Nonrepresentable", field)
    return result


def product(left, right, field):
    return rounded(exact(left) * exact(right), field)


def quotient(left, right, field):
    require(not zero(right), "Nonrepresentable", field)
    return rounded(exact(left) / exact(right), field)


def sqrt_word(value, field):
    """Correct RN-even positive sqrt using rational comparisons, no float/libm.

    Find consecutive nonnegative finite binary64 words bracketing sqrt(q).
    Compare q with the squared exact midpoint; even low bit decides a tie.
    This checks the small SI map only, never a force or candidate diagnostic.
    """
    q = exact(value)
    require(q > 0, "Nonrepresentable", field)
    low, high = 0, 0x7fefffffffffffff
    while low < high:
        middle = (low + high + 1) // 2
        x = codec().exact_binary64(middle)
        if x * x <= q:
            low = middle
        else:
            high = middle - 1
    x = codec().exact_binary64(low)
    if x * x == q:
        return format(low, "016x")
    require(low < 0x7fefffffffffffff, "Nonrepresentable", field)
    midpoint = (x + codec().exact_binary64(low + 1)) / 2
    selected = low + int(q > midpoint * midpoint or (q == midpoint * midpoint and low & 1))
    result = format(selected, "016x")
    require(positive(result), "Nonrepresentable", field)
    return result


class Tokens:
    def __init__(self, raw, limit, stage):
        require(type(raw) is bytes and 0 < len(raw) <= limit, "ResourceLimit", stage)
        require(raw.isascii() and raw.endswith(b"\n"), "InvalidASCII", stage)
        # Match Rust SplitAsciiWhitespace, not Python's extra VT separator.
        self.values = re.split(rb"[ \t\n\r\f]+", raw.strip(b" \t\n\r\f"))
        self.index, self.stage = 0, stage

    def take(self, field):
        require(self.index < len(self.values), "Truncated", field)
        value = self.values[self.index].decode("ascii")
        self.index += 1
        return value

    def expect(self, value, field):
        require(self.take(field) == value, "UnexpectedToken", field)

    def uint(self, bits, field):
        value = self.take(field)
        require(len(value) <= 20 and re.fullmatch(r"0|[1-9][0-9]*", value) is not None,
                "InvalidDecimal", field)
        result = int(value)
        require(result < 1 << bits, "IntegerOverflow", field)
        return result

    def word(self, field):
        return finite_word(self.take(field), field)

    def vector(self, field):
        return [self.word(field + "." + str(k)) for k in range(3)]

    def label(self, field):
        result = self.take(field)
        require(1 <= len(result) <= 160 and re.fullmatch(r"[A-Za-z0-9._-]+", result) is not None,
                "InvalidLabel", field)
        return result

    def payload(self, field):
        result = self.take(field)
        require(re.fullmatch(r"[0-9a-f]{32}", result) is not None, "InvalidId", field)
        return result

    def end(self):
        self.expect("end", self.stage + ".end")
        require(self.index == len(self.values), "TrailingContent", self.stage)


def particle(tokens, field):
    tokens.expect("particle", field)
    result = {"id": tokens.payload(field + ".id"), "kind": tokens.take(field + ".kind"),
              "component": tokens.uint(16, field + ".component"),
              "galaxy": tokens.uint(32, field + ".galaxy"),
              "class": tokens.uint(16, field + ".class"), "mass": tokens.word(field + ".mass"),
              "position": tokens.vector(field + ".position"),
              "momentum": tokens.vector(field + ".momentum")}
    require(result["kind"] in ("dm", "star"), "InvalidSpecies", field)
    require(positive(result["mass"]), "NonpositiveMass", field)
    # Constructor p/m admissibility only; no pair/kernel/diagnostic recreation.
    for k, p in enumerate(result["momentum"]):
        if not zero(p):
            quotient(p, result["mass"], field + ".velocity." + str(k))
    return result


def parse_input(raw):
    t = Tokens(raw, MAX_INPUT_BYTES, "input")
    t.expect("openmhd-gravity-force-input-v1", "input.header")
    t.expect("case", "input.case")
    case = t.label("input.case")
    t.expect("stage", "input.stage")
    t.expect("static-force-snapshot", "input.stage")
    t.expect("clock", "input.clock")
    time, revision = t.word("input.time"), t.uint(64, "input.revision")
    t.expect("backend", "input.backend")
    backend = t.uint(64, "input.backend")
    t.expect("units", "input.units")
    branch = t.take("input.units")
    require(branch in ("dimensionless-g1", "si"), "UnsupportedUnits", "input.units")
    units = {"branch": branch}
    if branch == "si":
        units["inputs"] = [t.word("input.units." + name) for name in ("L", "M", "V", "G", "mu0")]
        require(all(positive(w) for w in units["inputs"]), "NonpositiveUnit", "input.units")
        units["provenance"] = t.label("input.units.provenance")
    t.expect("softening", "input.softening")
    epsilon, common_class = t.word("input.epsilon"), t.uint(16, "input.class")
    require(positive(epsilon), "NonpositiveEpsilon", "input.epsilon")
    product(epsilon, epsilon, "input.epsilon_squared")
    t.expect("count", "input.count")
    count = t.uint(64, "input.count")
    require(count <= MAX_PARTICLES, "SourceLimit", "input.count")
    particles = [particle(t, "input.particle." + str(i)) for i in range(count)]
    t.end()
    require(len({p["id"] for p in particles}) == count, "DuplicateId", "input.particles")
    require(all(p["class"] == common_class for p in particles), "ClassMismatch", "input.particles")
    return {"case": case, "stage": "static-force-snapshot", "time": time, "revision": revision,
            "backend_revision": backend, "units": units, "epsilon": epsilon, "class": common_class,
            "input_order": [p["id"] for p in particles], "particles": sorted(particles, key=lambda p: p["id"])}


def u(value, width=8):
    return value.to_bytes(width, "big")


def wb(word):
    return bytes.fromhex(word)


def sized(raw):
    return u(len(raw)) + raw


def unit_body(source):
    spec = source["units"]
    if spec["branch"] == "dimensionless-g1":
        return G1_TAG, ONE
    l, m, v, g, mu0 = spec["inputs"]
    # Exact declared Rust operation order, rounding each operation once.
    t = quotient(l, v, "units.time")
    v2 = product(v, v, "units.v2")
    l3 = product(product(l, l, "units.l2"), l, "units.l3")
    rho = quotient(m, l3, "units.rho")
    pressure = product(rho, v2, "units.pressure")
    energy = product(m, v2, "units.energy")
    momentum = product(m, v, "units.momentum")
    angular = product(l, momentum, "units.angular_momentum")
    acceleration = quotient(v2, l, "units.acceleration")
    force = quotient(energy, l, "units.force")
    b = product(v, sqrt_word(product(mu0, rho, "units.B_radicand"), "units.B_sqrt"), "units.B")
    a = product(b, l, "units.A")
    power = quotient(energy, t, "units.power")
    volume_power = quotient(pressure, t, "units.volume_power")
    g_code = quotient(product(g, m, "units.G_numerator"), product(l, v2, "units.G_denominator"), "units.G")
    scales = [l, m, v, t, rho, pressure, energy, momentum, angular, acceleration,
              v2, force, b, a, power, volume_power]
    require(all(positive(w) for w in scales + [g_code]), "NonpositiveUnit", "units.derived")
    return (SI_TAG + b"".join(wb(w) for w in spec["inputs"])
            + sized(spec["provenance"].encode("ascii"))
            + b"".join(wb(w) for w in scales) + wb(g_code)), g_code


def canonical_bodies(source):
    units, g_code = unit_body(source)
    particles = source["particles"]
    sources = SOURCE_TAG + u(len(particles))
    for p in particles:
        sources += (p["id"].encode("ascii") + u(0 if p["kind"] == "dm" else 1, 1)
                    + u(p["class"], 2) + wb(p["mass"]) + b"".join(wb(w) for w in p["position"]))
    state = STATE_TAG + wb(source["time"]) + u(source["revision"]) + sized(sources)
    for p in particles:
        state += b"".join(wb(w) for w in p["momentum"]) + u(p["component"], 2) + u(p["galaxy"], 4)
    return {"sources": sources, "state": state,
            "model": MODEL_TAG + wb(g_code) + wb(source["epsilon"]) + u(source["class"], 2),
            "units": units, "backend": BACKEND_TAG + u(source["backend_revision"])}, g_code


class Body:
    def __init__(self, raw):
        self.raw, self.offset = raw, 0

    def take(self, count, field):
        require(self.offset + count <= len(self.raw), "BodyTruncated", field)
        result = self.raw[self.offset:self.offset + count]
        self.offset += count
        return result

    def match(self, expected, field):
        require(self.take(len(expected), field) == expected, "CanonicalMismatch", field)

    def end(self, field):
        require(self.offset == len(self.raw), "BodyTrailingContent", field)


def hex_body(t, field):
    length = t.uint(64, field + ".length")
    require(length <= MAX_BODY_BYTES, "BodyLimit", field)
    digest = t.take(field + ".sha256")
    require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None, "InvalidDigest", field)
    text = t.take(field + ".body")
    require(len(text) == length * 2 and re.fullmatch(r"[0-9a-f]+", text) is not None,
            "BodyLengthOrHex", field)
    raw = bytes.fromhex(text)
    require(sha(raw) == digest, "BodyDigest", field)
    return raw


def optional(t, name, width):
    field = "diagnostic." + name
    t.expect("diagnostic", field)
    t.expect(name, field)
    kind = t.take(field)
    require(kind in ("some", "none"), "InvalidOption", field)
    if kind == "none":
        return None
    return t.word(field) if width == 1 else t.vector(field)


def parse_transcript(raw_input, stdout):
    """Pure checked-schema decoder, NOT successful-process or provenance proof.

    Exposed for small nonphysical schema controls. Use decode_snapshot plus
    actual caller evidence before projecting any real Rust comparison input.
    """
    source = parse_input(raw_input)
    expected, g_code = canonical_bodies(source)
    t = Tokens(stdout, MAX_OUTPUT_BYTES, "stdout")
    t.expect("openmhd-gravity-force-candidate-v1", "stdout.header")
    for label, value in [("status", "complete"), ("component_accepted", "false"),
                         ("case", source["case"]), ("stage", "static-force-snapshot")]:
        t.expect(label, "stdout." + label)
        t.expect(value, "stdout." + label)
    t.expect("input_sha256", "stdout.input_sha256")
    require(t.take("stdout.input_sha256") == sha(raw_input), "RawInputDigest", "stdout.input_sha256")
    t.expect("clock", "stdout.clock")
    require(t.word("stdout.time") == source["time"] and t.uint(64, "stdout.revision") == source["revision"],
            "EchoMismatch", "stdout.clock")
    t.expect("backend_revision", "stdout.backend_revision")
    require(t.uint(64, "stdout.backend_revision") == source["backend_revision"], "EchoMismatch", "stdout.backend_revision")
    t.expect("model", "stdout.model")
    for label in ["isolated", "common-fixed-plummer", "excluded"]:
        t.expect(label, "stdout.model")
    require(t.word("stdout.G") == g_code and t.word("stdout.epsilon") == source["epsilon"]
            and t.uint(16, "stdout.class") == source["class"], "EchoMismatch", "stdout.model")
    t.expect("units_physical", "stdout.units_physical")
    t.expect("true" if source["units"]["branch"] == "si" else "false", "stdout.units_physical")
    count = len(source["particles"])
    pairs = count * (count - 1) // 2
    t.expect("counts", "stdout.counts")
    require(t.uint(64, "stdout.count") == count and t.uint(64, "stdout.pairs") == pairs,
            "CountMismatch", "stdout.counts")
    for payload in source["input_order"]:
        t.expect("input_order", "stdout.input_order")
        require(t.payload("stdout.input_order") == payload, "OrderMismatch", "stdout.input_order")
    bodies = {}
    for label in ["sources", "state", "model", "units", "backend"]:
        t.expect("identity", "identity." + label)
        t.expect(label, "identity." + label)
        body = hex_body(t, "identity." + label)
        cursor = Body(body)
        cursor.match(expected[label], "identity." + label)
        cursor.end("identity." + label)
        bodies[label] = body
    t.expect("cache_clock", "cache.clock")
    require(t.word("cache.time") == source["time"] and t.uint(64, "cache.revision") == source["revision"],
            "CacheClockMismatch", "cache.clock")
    for label in ["sources", "state", "model", "units", "backend"]:
        t.expect("identity", "cache." + label)
        t.expect("cache_" + label, "cache." + label)
        cursor = Body(hex_body(t, "cache." + label))
        cursor.match(expected[label], "cache." + label)
        cursor.end("cache." + label)
    for i, original in enumerate(source["particles"]):
        echoed = particle(t, "stdout.particle." + str(i))
        require(echoed == original, "ParticleEchoMismatch", "stdout.particle." + str(i))
    samples = []
    for i, p in enumerate(source["particles"]):
        field = "sample." + str(i)
        t.expect("sample", field)
        require(t.payload(field + ".id") == p["id"], "SampleOrderMismatch", field)
        sample = {"id": p["id"], "force": t.vector(field + ".force"),
                  "phi": t.word(field + ".phi"), "force_scale": t.word(field + ".force_scale"),
                  "potential_scale": t.word(field + ".potential_scale")}
        require(nonnegative(sample["force_scale"]) and nonnegative(sample["potential_scale"]), "NegativeScale", field)
        require(zero(sample["phi"]) or not positive(sample["phi"]), "PositivePotential", field)
        samples.append(sample)
    t.expect("evaluation_scales", "evaluation.scales")
    scales = {k: t.word("evaluation." + k) for k in ["pair_energy", "energy_scale", "net_force_scale", "torque_scale"]}
    require(all(nonnegative(scales[k]) for k in ["energy_scale", "net_force_scale", "torque_scale"]),
            "NegativeScale", "evaluation.scales")
    t.expect("evaluation_bytes", "evaluation.bytes")
    evaluation = hex_body(t, "evaluation.bytes")
    c = Body(evaluation)
    c.match(EVALUATION_TAG, "evaluation.tag")
    c.match(wb(source["time"]), "evaluation.time")
    c.match(u(source["revision"]), "evaluation.revision")
    for label in ["sources", "state", "model", "units", "backend"]:
        c.match(sized(expected[label]), "evaluation." + label)
    c.match(wb(g_code), "evaluation.private_G")
    c.match(wb(source["epsilon"]), "evaluation.private_epsilon")
    c.match(u(pairs), "evaluation.pair_count")
    for key, word in scales.items():
        c.match(wb(word), "evaluation." + key)
    c.match(u(count), "evaluation.sample_count")
    for i, sample in enumerate(samples):
        c.match(sample["id"].encode("ascii"), "evaluation.sample." + str(i) + ".id")
        for k, word in enumerate(sample["force"] + [sample["phi"], sample["force_scale"], sample["potential_scale"]]):
            c.match(wb(word), "evaluation.sample." + str(i) + ".word." + str(k))
    c.end("evaluation.bytes")
    diagnostic = {}
    for label in ["raw_force", "raw_torque_origin"]:
        t.expect(label, label)
        diagnostic[label] = t.vector(label)
    for label, width in [("mass", 1), ("momentum", 3), ("angular_momentum_origin", 3),
                         ("kinetic_lab", 1), ("pair_energy", 1), ("hamiltonian_lab", 1)]:
        t.expect("diagnostic", "diagnostic." + label)
        t.expect(label, "diagnostic." + label)
        diagnostic[label] = t.word("diagnostic." + label) if width == 1 else t.vector("diagnostic." + label)
    for label, width in [("center_of_mass", 3), ("center_velocity", 3), ("angular_momentum_internal", 3),
                         ("kinetic_internal", 1), ("virial_work", 1), ("inertia_internal", 1)]:
        diagnostic[label] = optional(t, label, width)
    t.expect("diagnostic", "diagnostic.virial_residual")
    t.expect("virial_residual", "diagnostic.virial_residual")
    virial_kind = t.take("diagnostic.virial_residual")
    require(virial_kind in ("defined", "undefined"), "InvalidVirial", "diagnostic.virial_residual")
    virial_value = t.word("diagnostic.virial_residual") if virial_kind == "defined" else t.take("diagnostic.virial_residual")
    diagnostic["virial_residual"] = {"kind": virial_kind, "value": virial_value}
    t.end()
    require(diagnostic["pair_energy"] == scales["pair_energy"], "DiagnosticMismatch", "diagnostic.pair_energy")
    require(nonnegative(diagnostic["kinetic_lab"]), "NegativeDiagnostic", "diagnostic.kinetic_lab")
    opts = [diagnostic[n] for n in ["center_of_mass", "center_velocity", "angular_momentum_internal",
                                    "kinetic_internal", "virial_work", "inertia_internal"]]
    if count == 0:
        require(all(v is None for v in opts) and diagnostic["virial_residual"] ==
                {"kind": "undefined", "value": "empty"}, "UndefinedReasonMismatch", "diagnostic.empty")
        empty_values = (list(scales.values()) + [diagnostic[n] for n in
                        ["mass", "kinetic_lab", "pair_energy", "hamiltonian_lab"]]
                        + sum((diagnostic[n] for n in ["raw_force", "raw_torque_origin", "momentum", "angular_momentum_origin"]), []))
        require(all(zero(w) for w in empty_values), "StructuralZeroMismatch", "diagnostic.empty")
    else:
        require(all(v is not None for v in opts) and positive(diagnostic["mass"]), "MissingDiagnostic", "diagnostic.nonempty")
        require(nonnegative(diagnostic["kinetic_internal"]) and nonnegative(diagnostic["inertia_internal"]),
                "NegativeDiagnostic", "diagnostic.internal")
        defined = positive(diagnostic["kinetic_internal"]) or not zero(diagnostic["virial_work"])
        require((virial_kind == "defined" and nonnegative(virial_value)) if defined else
                diagnostic["virial_residual"] == {"kind": "undefined", "value": "nonpositive-scale"},
                "UndefinedReasonMismatch", "diagnostic.virial_residual")
    if count <= 1:
        require(all(zero(w) for w in list(scales.values()) +
                    [w for s in samples for w in s["force"] + [s["phi"], s["force_scale"], s["potential_scale"]]]),
                "StructuralZeroMismatch", "evaluation.no_pairs")
        require(all(zero(w) for w in diagnostic["raw_force"] + diagnostic["raw_torque_origin"]),
                "StructuralZeroMismatch", "diagnostic.no_pairs")
        if count == 1:
            require(zero(diagnostic["kinetic_internal"]) and zero(diagnostic["virial_work"]),
                    "StructuralZeroMismatch", "diagnostic.one_particle")
    else:
        require(not nonnegative(scales["pair_energy"]) and positive(scales["energy_scale"])
                and all(not nonnegative(s["phi"]) and positive(s["potential_scale"]) for s in samples),
                "PairSignMismatch", "evaluation.potential_energy")
        positions = [[ZERO if zero(w) else w for w in p["position"]] for p in source["particles"]]
        if all(p == positions[0] for p in positions):
            require(all(zero(w) for s in samples for w in s["force"] + [s["force_scale"]])
                    and zero(scales["net_force_scale"]) and zero(scales["torque_scale"])
                    and all(zero(w) for w in diagnostic["raw_force"] + diagnostic["raw_torque_origin"]),
                    "StructuralZeroMismatch", "evaluation.coincident")
    return {"schema": "openmhd.gravity-force-decoded.v1", "source": source, "g_code_bits": g_code,
            "identities": {k: {"bytes": len(v), "sha256": sha(v), "hex": v.hex()} for k, v in bodies.items()},
            "evaluation": {"bytes": len(evaluation), "sha256": sha(evaluation), "hex": evaluation.hex(),
                           "pair_count": pairs, "samples": samples, "scales": scales},
            "diagnostics": diagnostic, "component_accepted": False, "physical_evolutions_run": False}


def validate_process(raw_input, stdout, stderr, evidence):
    require(type(raw_input) is bytes and type(stdout) is bytes and type(stderr) is bytes,
            "ProcessSchema", "process.buffers")
    require(0 < len(raw_input) <= MAX_INPUT_BYTES and 0 < len(stdout) <= MAX_OUTPUT_BYTES
            and len(stderr) <= MAX_OUTPUT_BYTES, "ResourceLimit", "process.buffers")
    keys = {"schema", "invocation_id", "outcome", "returncode", "timed_out", "logs_closed", "writers_stopped",
            "input_sha256", "stdout_sha256", "stdout_bytes", "stderr_sha256", "stderr_bytes"}
    require(type(evidence) is dict and set(evidence) == keys, "ProcessSchema", "process")
    require(evidence["schema"] == "openmhd.gravity-force-process-evidence.v1"
            and type(evidence["invocation_id"]) is str
            and re.fullmatch(r"[A-Za-z0-9._-]{1,160}", evidence["invocation_id"]) is not None,
            "ProcessSchema", "process")
    require(type(evidence["returncode"]) is int and evidence["returncode"] == 0
            and evidence["outcome"] == "success" and evidence["timed_out"] is False
            and evidence["logs_closed"] is True and evidence["writers_stopped"] is True,
            "ProcessNotSuccessful", "process")
    require(type(evidence["stdout_bytes"]) is int and type(evidence["stderr_bytes"]) is int
            and evidence["input_sha256"] == sha(raw_input)
            and evidence["stdout_sha256"] == sha(stdout) and evidence["stdout_bytes"] == len(stdout)
            and evidence["stderr_sha256"] == sha(stderr) and evidence["stderr_bytes"] == len(stderr),
            "ProcessBufferMismatch", "process")


@dataclass(frozen=True)
class Snapshot:
    raw_input: bytes
    stdout: bytes
    stderr: bytes
    process_json: bytes


def decode_snapshot(raw_input, stdout, stderr, process):
    """Requires caller's actual finalized process evidence; cannot attest it."""
    require(type(raw_input) is bytes and type(stdout) is bytes, "ProcessSchema", "process.buffers")
    validate_process(raw_input, stdout, stderr, process)
    parse_transcript(raw_input, stdout)
    return Snapshot(raw_input, stdout, stderr, encode(process))


def project_reference(snapshot):
    """Words only; no force/reference evaluation, time advance or SI conversion.

    Three distinct reference-input identities: emitted original-order bytes,
    existing reference's word-preserving sorted body, and explicitly named
    numeric-equivalence body (only signed-zero position words normalized).
    Metadata/state/units/time stay outside the existing physical-input schema.
    """
    require(type(snapshot) is Snapshot, "SnapshotRequired", "projection")
    require(type(snapshot.process_json) is bytes and len(snapshot.process_json) <= 16384,
            "ProcessSchema", "projection.process_json")
    try:
        process = json.loads(snapshot.process_json)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise BridgeError("ProcessSchema", "projection.process_json") from exc
    validate_process(snapshot.raw_input, snapshot.stdout, snapshot.stderr, process)
    require(encode(process) == snapshot.process_json,
            "ProcessSchema", "projection.process_json")
    parsed = parse_transcript(snapshot.raw_input, snapshot.stdout)
    source = parsed["source"]
    rows = {p["id"]: {"id": {"wrapper": "ParticleId", "payload_hex": p["id"]},
                          "mass_bits": p["mass"], "position_bits": p["position"]}
            for p in source["particles"]}
    model = {"boundary": "isolated", "kernel": "common-fixed-plummer", "self_interaction": "excluded",
             "g_code_bits": parsed["g_code_bits"], "epsilon_code_bits": source["epsilon"]}
    raw = encode({"schema": REFERENCE_SCHEMA, "model": model, "sources": [rows[k] for k in source["input_order"]]})
    canonical = encode({"schema": REFERENCE_SCHEMA, "model": model, "sources": [rows[k] for k in sorted(rows)]})
    numeric = json.loads(canonical)
    for row in numeric["sources"]:
        row["position_bits"] = [ZERO if zero(w) else w for w in row["position_bits"]]
    return {"reference_input_bytes": raw, "canonical_reference_input_bytes": canonical,
            "numeric_reference_input_bytes": encode(numeric),
            "join": {"schema": "openmhd.gravity-force-reference-projection.v1",
                     "original_ascii_input_sha256": sha(snapshot.raw_input),
                     "stdout_sha256": sha(snapshot.stdout), "stderr_sha256": sha(snapshot.stderr),
                     "process_evidence_sha256": sha(snapshot.process_json), "invocation_id": process["invocation_id"],
                     "raw_reference_input_sha256": sha(raw), "word_preserving_sorted_reference_sha256": sha(canonical),
                     "numeric_reference_input_sha256": sha(encode(numeric)),
                     "numeric_equivalence_rule": "sorted ParticleIds; positive model/mass words unchanged; position +/-zero -> +zero only",
                     "checked_source": source, "canonical_identities": parsed["identities"],
                     "evaluation": parsed["evaluation"], "raw_diagnostics": parsed["diagnostics"],
                     "reference_source_required_sha256": REFERENCE_SOURCE_SHA256,
                     "driver_source_required_sha256": DRIVER_SOURCE_SHA256,
                     "codec_required_sha256": HELPER_SHA256,
                     "scope": {"physical_evolutions_run": False, "reference_evaluation_run": False,
                               "candidate_comparison_run": False, "compiler_binary_runtime_attested": False,
                               "component_accepted": False, "merger_accepted": False}}}
