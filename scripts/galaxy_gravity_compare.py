"""Unintegrated exact G1 static comparison; every execution belongs on REANA.

No force evaluation or arithmetic on import. Uses the disclosed shared pinned
binary64 codec via the checked bridge. External process/server provenance is
never authenticated by an internally consistent packet or a passing error gate.
"""
from fractions import Fraction as Q
import hashlib
import json
import math
import re

import galaxy_gravity_bridge as bridge

LIMIT = 16 * 1024 * 1024
INTEGER_BITS = 65536
MAX_TERMS = 2048
MAX_CERTIFICATES = 16384
MAX_TOTAL_TERMS = 65536
MAX_COMPARISON_BITS = 1_048_576
TAU = '1/2000000000000'  # Existing common G1 algebra budget 5e-13.
PACKET_FILES = frozenset(('input.json', 'canonical_physical_input.json', 'reference.json',
    'status.json', 'sources.json', 'galaxy_gravity_reference.py',
    'galaxy_geometry3_reference.py', 'files.sha256.json'))


def require(condition, label):
    if not condition:
        raise ValueError(label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def keys(value, names, label):
    require(type(value) is dict and set(value) == set(names), label)


def parse(raw):
    require(type(raw) is bytes and len(raw) <= LIMIT, 'Bounded immutable JSON bytes')
    def unique(pairs):
        value = {}
        for k, item in pairs:
            require(k not in value, 'Duplicate JSON key')
            value[k] = item
        return value
    def invalid(_):
        raise ValueError('Noninteger/nonfinite JSON number')
    return json.loads(raw, object_pairs_hook=unique, parse_float=invalid, parse_constant=invalid)


def rational(record):
    keys(record, ('numerator_hex', 'denominator_hex'), 'Rational record keys')
    n, d = record['numerator_hex'], record['denominator_hex']
    require(type(n) is str and type(d) is str and len(n) <= 16385 and len(d) <= 16384
            and re.fullmatch('-?[0-9a-f]+', n) and re.fullmatch('[0-9a-f]+', d), 'Bounded hexadecimal rational')
    numerator, denominator = int(n, 16), int(d, 16)
    require(denominator > 0 and max(abs(numerator).bit_length(), denominator.bit_length()) <= INTEGER_BITS,
            'Positive bounded rational denominator')
    value = Q(numerator, denominator)
    require(format(value.numerator, 'x') == n and format(value.denominator, 'x') == d,
            'Reduced canonical rational')
    return value


def q_record(value):
    return dict(numerator_hex=format(value.numerator, 'x'), denominator_hex=format(value.denominator, 'x'))


def bounded(*values):
    require(all(type(v) in (int, Q) and max(abs(v.numerator).bit_length(), v.denominator.bit_length())
                <= MAX_COMPARISON_BITS for v in values), 'Comparison rational-size resource limit')
    return values[0] if len(values) == 1 else values


def word(value):
    bridge.finite_word(value, 'comparison.word')
    return bridge.exact(value)


def sqrt_bounds(q, bits):
    require(q > 0 and type(bits) is int and 0 <= bits <= 4096, 'Positive rational radical with bounded precision')
    n, d = math.isqrt(q.numerator), math.isqrt(q.denominator)
    if n * n == q.numerator and d * d == q.denominator:
        point = Q(n, d)
        return point, point
    lower = math.isqrt((q.numerator << (2 * bits)) // q.denominator)
    return Q(lower, 1 << bits), Q(lower + 1, 1 << bits)


class Certificates:
    """Check retained scalar enclosure/rounding proofs, never a force kernel."""
    def __init__(self):
        self.used = 0
        self.terms = 0

    def read(self, record):
        self.used += 1
        require(self.used <= MAX_CERTIFICATES, 'Certificate-count resource limit')
        keys(record, ('expression', 'structural_zero', 'exact_rational', 'enclosure',
                      'nearest_binary64', 'sqrt_fraction_bits', 'rounding_error_bound'), 'Scalar certificate keys')
        expression = record['expression']
        require(type(expression) is list and len(expression) <= MAX_TERMS, 'Bounded exact expression')
        self.terms += len(expression)
        require(self.terms <= MAX_TOTAL_TERMS, 'Total scalar-term resource limit')
        require(type(record['structural_zero']) is bool and record['structural_zero'] == (len(expression) == 0),
                'Structural zero requires empty exact expression')
        terms = []
        for term in expression:
            keys(term, ('coefficient', 'radicand'), 'Expression term keys')
            c, q = rational(term['coefficient']), rational(term['radicand'])
            require(c != 0 and q > 0, 'Nonzero coefficient and positive radicand')
            terms.append((c, q))
        require([q for _, q in terms] == sorted({q for _, q in terms}), 'Sorted distinct radicands')
        exact = all(q == 1 for _, q in terms)
        require(type(record['exact_rational']) is bool and record['exact_rational'] == exact,
                'Exact-rational certificate classification')
        bits = record['sqrt_fraction_bits']
        require(bits is None if exact else type(bits) is int and bits in (64, 128, 256, 512, 1024, 2048, 4096),
                'Registered scalar precision schedule')
        lo, hi = Q(0), Q(0)
        for c, q in terms:
            a, b = sqrt_bounds(q, 0 if exact else bits)
            if c < 0:
                a, b = b, a
            lo, hi = bounded(lo + bounded(c * a), hi + bounded(c * b))
        keys(record['enclosure'], ('lower', 'upper'), 'Enclosure exact keys')
        supplied = rational(record['enclosure']['lower']), rational(record['enclosure']['upper'])
        require(supplied == (lo, hi), 'Reproduced exact scalar enclosure proof')
        nearest = word(record['nearest_binary64'])
        expected = format(bridge.codec().binary64_bits(lo), '016x')
        require(expected == format(bridge.codec().binary64_bits(hi), '016x') == record['nearest_binary64'],
                'One certified nearest/ties-even binary64 word')
        require(rational(record['rounding_error_bound']) == max(abs(nearest - lo), abs(nearest - hi)),
                'Actual nearest-word rounding bound')
        return (lo, hi), record['structural_zero']


def absolute_error(actual, target):
    lo, hi = target
    require(lo <= hi, 'Ordered target enclosure')
    return bounded(max(lo - actual, actual - hi, Q(0)), max(abs(actual - lo), abs(actual - hi)))


def vector_error_squared(actual, target):
    require(len(actual) == len(target) == 3, 'Three component vector comparison')
    errors = [absolute_error(a, t) for a, t in zip(actual, target)]
    return bounded(sum((bounded(e[0] * e[0]) for e in errors), Q(0)),
                   sum((bounded(e[1] * e[1]) for e in errors), Q(0)))


def criterion(error, scale, structural_zero, *, squared=False, strict=False):
    elo, ehi = error
    dlo, dhi = scale
    require(0 <= elo <= ehi and 0 <= dlo <= dhi, 'Nonnegative error and independent scale')
    tau = Q(TAU)
    limit = tau * tau if squared else tau
    result = dict(metric='squared_euclidean_over_squared_scale' if squared else 'absolute_over_scale',
                  absolute_error_bounds=[q_record(elo), q_record(ehi)],
                  independent_scale_bounds=[q_record(dlo), q_record(dhi)],
                  structural_zero_scale=structural_zero, strict_inequality=strict,
                  limit=q_record(limit))
    if structural_zero:
        require(dlo == dhi == 0, 'Structural-zero scale must be exact zero')
        result.update(verdict='pass' if ehi == 0 else 'fail' if elo > 0 else 'unresolved',
                      policy='Exact absolute zero required; no denominator or tolerance floor')
        return result
    if dlo <= 0:
        result.update(verdict='unresolved', policy='Nonzero scale needs certified positive lower endpoint')
        return result
    if squared:
        dlo, dhi = bounded(dlo * dlo, dhi * dhi)
    bounds = bounded(elo / dhi, ehi / dlo)
    passed = bounds[1] < limit if strict else bounds[1] <= limit
    failed = bounds[0] >= limit if strict else bounds[0] > limit
    result.update(normalized_error_bounds=[q_record(v) for v in bounds],
                  verdict='pass' if passed else 'fail' if failed else 'unresolved')
    return result


def validate_packet(projection, packet):
    require(type(packet) is dict and set(packet) == PACKET_FILES
            and all(type(raw) is bytes and len(raw) <= LIMIT for raw in packet.values()), 'Exact eight-file reference packet')
    manifest = parse(packet['files.sha256.json'])
    keys(manifest, ('schema', 'files'), 'Reference manifest exact keys')
    require(manifest['schema'] == 'openmhd.gravity-reference-files.v1', 'Reference manifest schema')
    expected = {n: dict(sha256=sha(raw), bytes=len(raw)) for n, raw in packet.items() if n != 'files.sha256.json'}
    require(manifest['files'] == expected
            and all(type(row['bytes']) is int for row in manifest['files'].values()), 'Every retained body hash and byte count')
    require(packet['input.json'] == projection['reference_input_bytes']
            and packet['canonical_physical_input.json'] == projection['canonical_reference_input_bytes'],
            'Actual Rust-word original and canonical reference inputs')
    for name, expected_sha in (('galaxy_gravity_reference.py', bridge.REFERENCE_SOURCE_SHA256),
                               ('galaxy_geometry3_reference.py', bridge.HELPER_SHA256)):
        require(sha(packet[name]) == expected_sha, 'Exact independent source buffer: ' + name)
    sources = parse(packet['sources.json'])
    keys(sources, ('schema', 'files', 'runtime', 'note'), 'Reference source receipt keys')
    require(sources['schema'] == 'openmhd.gravity-reference-sources.v1', 'Reference sources schema')
    require(sources['files'] == {'scripts/' + name: dict(sha256=sha(packet[name]), bytes=len(packet[name]), copied_path=name)
                for name in ('galaxy_gravity_reference.py', 'galaxy_geometry3_reference.py')}, 'Copied source receipts')
    runtime = sources['runtime']
    keys(runtime, ('implementation', 'version', 'optimize'), 'Reference interpreter receipt')
    require(runtime['implementation'] == 'cpython' and type(runtime['version']) is str
            and type(runtime['optimize']) is int and runtime['optimize'] == 0, 'Unoptimized retained reference interpreter')
    status = parse(packet['status.json'])
    keys(status, ('schema', 'status', 'reference_exported', 'component_accepted', 'merger_accepted',
                 'physical_evolutions_run', 'reference_arithmetic_attempted', 'reference_arithmetic_completed', 'problem'),
         'Reference status exact keys')
    require(status['schema'] == 'openmhd.gravity-force-reference-status.v1' and status['status'] == 'complete'
            and status['reference_exported'] is True and status['reference_arithmetic_attempted'] is True
            and status['reference_arithmetic_completed'] is True and status['problem'] is None
            and status['component_accepted'] is False and status['merger_accepted'] is False
            and status['physical_evolutions_run'] is False, 'Actual retained complete reference status')
    reference = parse(packet['reference.json'])
    keys(reference, ('schema', 'input', 'source_count', 'unordered_pair_count', 'samples_by_particle_id',
                     'ordered_source_terms', 'unordered_pairs', 'pair_energy', 'raw_net_force',
                     'raw_net_torque_about_input_origin', 'half_sum_mass_phi_minus_pair_energy',
                     'independent_scales', 'scope', 'reference_resources'), 'Reference result exact keys')
    require(reference['schema'] == 'openmhd.gravity-force-reference.v1'
            and reference['input'] == dict(original_sha256=sha(packet['input.json']),
                word_preserving_sorted_sha256=sha(packet['canonical_physical_input.json'])), 'Reference target-input identity')
    keys(reference['scope'], ('physical_evolutions_run', 'candidate_comparison_run',
         'rust_cache_serialization_certified', 'physical_units_certified', 'component_accepted', 'merger_accepted'),
         'Independent reference scope keys')
    require(all(value is False for value in reference['scope'].values()), 'Independent reference retains nonacceptance')
    return reference


def compare(snapshot, packet):
    """Arithmetic for retained buffers, not external execution attestation."""
    projection = bridge.project_reference(snapshot)  # Revalidates immutable process/transcript/bodies.
    reference = validate_packet(projection, packet)
    join = projection['join']
    sources = join['checked_source']['particles']
    ids = [row['id'] for row in sources]
    n = len(ids)
    require(type(reference['source_count']) is int and reference['source_count'] == n
            and type(reference['unordered_pair_count']) is int and reference['unordered_pair_count'] == n * (n - 1) // 2,
            'Actual source and unordered pair counts')
    require(set(reference['samples_by_particle_id']) == set(ids), 'Exact ParticleId reference coverage')
    require(type(reference['ordered_source_terms']) is list
            and [(row['owner'], row['source']) for row in reference['ordered_source_terms']]
                == [(a, b) for a in ids for b in ids if a != b], 'Complete independent directed pair inventory')
    require(type(reference['unordered_pairs']) is list
            and [(row['left'], row['right']) for row in reference['unordered_pairs']]
                == [(a, b) for i, a in enumerate(ids) for b in ids[i + 1:]], 'Complete independent unordered pair inventory')
    samples = join['evaluation']['samples']
    require([s['id'] for s in samples] == ids, 'Original checked sorted sample order')
    proofs = Certificates()
    gates = {}
    for actual in samples:
        target = reference['samples_by_particle_id'][actual['id']]
        require(target['id_wrapper'] == 'ParticleId' and len(target['force']) == 3, 'Typed three-axis target')
        force = [proofs.read(v)[0] for v in target['force']]
        sf, zero_f = proofs.read(target['scales']['force_magnitude_sum'])
        sp, zero_p = proofs.read(target['scales']['potential_absolute_sum'])
        phi, _ = proofs.read(target['specific_potential'])
        prefix = 'particle.' + actual['id']
        gates[prefix + '.force'] = criterion(vector_error_squared([word(w) for w in actual['force']], force),
                                              sf, zero_f, squared=True)
        gates[prefix + '.specific_potential'] = criterion(absolute_error(word(actual['phi']), phi), sp, zero_p)
    energy, _ = proofs.read(reference['pair_energy'])
    se, zero_e = proofs.read(reference['independent_scales']['energy_absolute_sum'])
    gates['pair_energy'] = criterion(absolute_error(word(join['evaluation']['scales']['pair_energy']), energy), se, zero_e)
    for diagnostic, target_name, scale_name, gate_name in (
            ('raw_force', 'raw_net_force', 'net_force_interaction_sum', 'raw_net_force'),
            ('raw_torque_origin', 'raw_net_torque_about_input_origin', 'net_torque_interaction_sum', 'raw_net_torque_origin')):
        target = [proofs.read(v) for v in reference[target_name]]
        require(len(target) == 3 and all(z and bounds == (0, 0) for bounds, z in target),
                'GP2 raw reference force/torque must be structurally zero')
        scale, zero = proofs.read(reference['independent_scales'][scale_name])
        actual = [word(w) for w in join['raw_diagnostics'][diagnostic]]
        gates[gate_name] = criterion(vector_error_squared(actual, [v[0] for v in target]), scale, zero,
                                    squared=True, strict=True)
    identity, zero_identity = proofs.read(reference['half_sum_mass_phi_minus_pair_energy'])
    require(zero_identity and identity == (0, 0), 'Independent GP2 potential-energy identity is exact')
    verdicts = [row['verdict'] for row in gates.values()]
    result = dict(schema='openmhd.gravity-static-comparison.v1',
                arithmetic_verdict='pass' if all(v == 'pass' for v in verdicts) else
                    'fail' if 'fail' in verdicts else 'unresolved',
                gates=gates, checked_scalar_certificates=proofs.used,
                candidate_projection=join,
                reference_packet_sha256={name: sha(raw) for name, raw in packet.items()},
                candidate_scales_are_diagnostic_only=True, candidate_residuals_repaired=False,
                reference_packet_internal_consistency_verified=True,
                external_execution_provenance_verified=False, component_accepted=False, merger_accepted=False,
                scope='Supplied capped32 static algebra only; no gradient/covariance/orbit/gas/3D/merger acceptance')
    require(len(bridge.encode(result)) <= LIMIT, 'Serialized comparison output resource limit')
    return result
