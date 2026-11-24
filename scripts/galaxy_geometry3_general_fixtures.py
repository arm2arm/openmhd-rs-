"""Registered G02--G04 inputs. Generate/evaluate fixtures only on REANA."""
from fractions import Fraction as Q
import hashlib
from itertools import product
import json
from pathlib import Path

import galaxy_geometry3_reference as rounding
import galaxy_geometry3_general_bridge as bridge

SEED = 20261122
BASES = ('jitter4', 'jitter6', 'jitter8', 'clustered', 'sliver', 'boundary_near',
         'separation_1e4', 'separation_1e8', 'separation_1e12',
         'cospherical_cube', 'coplanar', 'near_coplanar')
VARIANTS = ('base', 'reverse', 'shuffle', 'repeat', 'translate', 'seam', 'windings')


def random_word(*counter):
    raw = ('openmhd-m2a-jitter-sha256-v1/' + str(SEED) + '/' + '/'.join(map(str, counter))).encode('ascii')
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], 'big')


def coordinates(name):
    if name.startswith('jitter'):
        n = int(name[6:])
        return [[(Q(2 * k + 1, 2) + Q(3, 20) * (Q(random_word(n, *index, a), 1 << 63) - 1)) / n
                 for a, k in enumerate(index)] for index in product(range(n), repeat=3)]
    if name == 'clustered':
        return [[Q(2 * k + 1, 8) for k in index] for index in product(range(4), repeat=3)] + [
            [Q(1, 2) + Q(k, 1000) for k in index] for index in product((-1, 1), repeat=3)]
    if name == 'sliver':
        return [[Q(2 * x + 1, 8), Q(2 * y + 1, 8), Q(1, 2) + Q(z, 100000)]
                for x, y, z in product(range(4), range(4), (-1, 0, 1))]
    if name == 'boundary_near':
        return [list(v) for v in product((Q(1, 100000000), Q(1, 2), 1 - Q(1, 100000000)), repeat=3)]
    if name.startswith('separation_'):
        epsilon = Q(1, 10 ** int(name.split('1e')[1]))
        return [[Q(1, 2) - epsilon / 2, Q(1, 2), Q(1, 2)],
                [Q(1, 2) + epsilon / 2, Q(1, 2), Q(1, 2)]]
    if name == 'cospherical_cube':
        return [list(v) for v in product((Q(1, 4), Q(3, 4)), repeat=3)]
    if name in ('coplanar', 'near_coplanar'):
        epsilon = Q(0) if name == 'coplanar' else Q(1, 10 ** 12)
        return [[Q(2*x+1, 6), Q(2*y+1, 6), Q(1, 2) + (epsilon if (x+y)%2 else -epsilon)]
                for x, y in product(range(3), repeat=2)]
    raise ValueError('Unregistered fixture')


def build(base, variant='base'):
    if base not in BASES or variant not in VARIANTS:
        raise ValueError('Unregistered general geometry case')
    # The base words are rounded once. Transforms operate on these actual words.
    points = [[rounding.rounded(v) for v in p] for p in coordinates(base)]
    anchor = [Q(0)] * 3
    delta = [Q(371, 1000), -Q(219, 1000), Q(443, 1000)]
    if variant == 'windings':
        delta = [delta[0] + 2, delta[1] - 3, delta[2] + 4]
    generators = []
    for counter, p in enumerate(points):
        winding = [0, 0, 0]
        if variant == 'translate':
            anchor = delta
            p = [rounding.rounded(p[a] + delta[a]) for a in range(3)]
        elif variant in ('seam', 'windings'):
            values = [p[a] + delta[a] for a in range(3)]
            winding = [v.numerator // v.denominator for v in values]
            p = [rounding.rounded(values[a] - winding[a]) for a in range(3)]
            # Once-rounding at the upper seam must have an explicit carry.
            for a in range(3):
                if p[a] == 1:
                    p[a] = Q(0)
                    winding[a] += 1
        generators.append(dict(id=f'{73:016x}{counter:016x}',
            position_bits=[rounding.word(v) for v in p], winding=winding))
    if variant == 'reverse':
        generators.reverse()
    elif variant == 'shuffle':
        generators.sort(key=lambda g: hashlib.sha256(('openmhd-m2a-shuffle-v1/' + g['id']).encode('ascii')).digest())
    value = dict(schema='openmhd.geometry3.general-input.v1',
        case=dict(name=base + '__' + variant), method=bridge.METHOD, design_sha256=bridge.DESIGN_SHA256,
        scalar_encoding='16 lowercase hexadecimal IEEE754 binary64 bits',
        identity_encoding='32 lowercase namespace-first EntityId hexadecimal digits',
        domain=dict(boundary='periodic', anchor_bits=[rounding.word(v) for v in anchor], width_bits=[rounding.word(Q(1))] * 3),
        generators=generators)
    return value


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('ascii')


def catalog():
    return [dict(base=base, variant=variant, threads=threads,
                 name=f'{base}__{variant}__t{threads}',
                 required_success=base in BASES[:6],
                 zero_area_events_possible=not base.startswith('jitter'))
            for base in BASES for variant in VARIANTS for threads in (1, 2, 4)]
