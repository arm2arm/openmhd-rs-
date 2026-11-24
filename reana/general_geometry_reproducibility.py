"""Reduce two independently executed native geometry exports for one G04 pair."""
import argparse
from fractions import Fraction
from pathlib import Path

from general_geometry_capture import CATALOG_SHA256, native_export
import galaxy_geometry3_general_bridge as bridge
from galaxy_geometry3_general_compare import reproducibility, scalar
from run_geometry3_general import capture, digest, encode, parse, require


def without_case_line(raw, case):
    # The native input and output formats each have exactly one complete case row.
    marker = b'\ncase ' + case.encode('ascii') + b'\n'
    require(raw.count(marker) == 1, 'Unique validated case label')
    return raw.replace(marker, b'\ncase\n', 1)


def periodic_charts(source, transcript):
    """Reconstruct both incidence translations from the literal generator trajectories."""
    mesh = bridge.parse_transcript(transcript, source)
    width = [scalar(word) for word in mesh['domain']['width_bits']]
    length = max(width)
    generators = {g['id']: (list(map(scalar, g['position_bits'])), g['winding'])
                  for g in mesh['input_generators']}
    maximum = Fraction(0)
    worst = None
    right_count = seam_count = self_count = 0
    for cell in mesh['cells']:
        for incidence in cell['incidences']:
            if incidence['sign'] == 1:
                # The transcript parser already checked every left translation is zero.
                continue
            face = mesh['faces'][incidence['face']]
            key = face['key']
            require(key['kind'] == 'interior', 'Right incidence of a shared periodic face')
            left, kl = generators[key['lo']]
            right, kr = generators[key['hi']]
            wrapped = [m + b - a for m, a, b in zip(key['hi_image'], kl, kr)]
            right_count += 1
            seam_count += any(wrapped)
            self_count += key['lo'] == key['hi']
            for axis, word in enumerate(incidence['chart_translation_bits']):
                # In the right generator's chart a left-local point moves by -d.
                expected = left[axis] - right[axis] - wrapped[axis] * width[axis]
                actual = scalar(word)
                residual = abs(expected - actual) / length
                if residual > maximum:
                    maximum = residual
                    worst = dict(face=key, axis=axis, expected=str(expected), observed_word=word)
    require(right_count == len(mesh['faces']), 'One checked right translation per periodic face')
    limit = Fraction(1, 10**10)
    return dict(right_incidences=right_count, wrapped_image_incidences=seam_count,
                self_image_incidences=self_count, maximum_component_over_L=str(maximum),
                worst=worst, limit=str(limit), passed=maximum <= limit)


def reduce_pair(left, right, first, second):
    require(first['base'] == second['base'] and first['variant'] == 'base', 'Common base geometry')
    cross_thread = second['variant'] == 'base'
    require((cross_thread and first['threads'] == 1 and second['threads'] in (2, 4))
            or (not cross_thread and first['threads'] == second['threads']), 'Registered G04 pair')
    li, lo, lr = left
    ri, ro, rr = right
    require(lr['uuid'] != rr['uuid'], 'Two independent native executions')
    metrics = reproducibility(li, lo, ri, ro)
    left_case = first['base'] + '__base'
    right_case = second['base'] + '__' + second['variant']
    same_input = (without_case_line(bridge.convert_input(li), left_case)
                  == without_case_line(bridge.convert_input(ri), right_case))
    repeat = second['variant'] == 'repeat'
    require(not (cross_thread or repeat) or same_input, 'Identical native words for repeated geometry')
    exact = without_case_line(lo, left_case) == without_case_line(ro, right_case)
    charts = dict(left=periodic_charts(li, lo), right=periodic_charts(ri, ro))
    passed = metrics['passed'] and all(r['passed'] for r in charts.values()) and (not repeat or exact)
    return dict(schema='openmhd.geometry3.g04-pair.v1', left=lr, right=rr, metrics=metrics,
                same_native_input_except_case=same_input, same_transcript_except_case=exact,
                periodic_charts=charts, repeat_requires_exact_output=repeat, passed=passed,
                component_accepted=False)


def execute(catalog_path, left_path, right_path, left_name, right_name, output):
    raw = capture(catalog_path)
    require(digest(raw) == CATALOG_SHA256, 'Frozen REANA catalog')
    cases = {r['name']: r for r in parse(raw)['cases']}
    first, second = cases[left_name], cases[right_name]
    output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='openmhd.geometry3.g04-outcome.v1', left=left_name, right=right_name,
                  catalog_sha256=digest(raw), component_accepted=False, passed=False)
    try:
        left = native_export(left_path, first, capture(left_path / 'input.json'))
        right = native_export(right_path, second, capture(right_path / 'input.json'))
        record['reduction'] = reduce_pair(left, right, first, second)
        require(record['reduction']['passed'], 'Registered G04 pair failed')
        record['passed'] = True
    except Exception as exc:
        record.update(error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        (output / 'result.json').write_bytes(encode(record))
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--left', required=True)
    parser.add_argument('--right', required=True)
    args = parser.parse_args()
    execute(Path('catalog.json'), Path('left'), Path('right'), args.left, args.right, Path('outputs'))
