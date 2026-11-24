"""Classify a captured native geometry rejection for G02/G03/G04 review."""
import argparse
from decimal import Decimal
from pathlib import Path
import re
import sys

from prepare_general_geometry_jobs import ROOT, read_literals

sys.path.insert(0, str(ROOT / 'reana'))
from general_geometry_capture import native_command
from run_geometry3_general import encode, parse, require


def inspect(selection, source, directory):
    status, command, stdout, stderr, receipt = native_command(directory, selection, source, 'failed')
    result = dict(native=receipt, returncode=command['returncode'], outcome=command['outcome'],
                  required_positive_geometry=selection['required_success'],
                  classification='native_failure', component_accepted=False)
    if (stdout or command['returncode'] != 1 or command['outcome'] != 'nonzero'
            or status['status'] != 'failed' or status.get('error') != 'Native geometry export failed'):
        return result
    match = re.fullmatch(rb'geometry3 candidate export rejected: 3D geometry rejected: '
                         rb'([A-Za-z]+)(?: [^\n]*|\([^\n]*\))?\n', stderr)
    if not match:
        return result
    variant = match[1].decode('ascii')
    require(status['geometry_error_variant'] == variant, 'Typed error agrees with Rust stderr')
    result.update(variant=variant, diagnostic=stderr.decode('utf-8'), classification='typed_rejection')
    if variant != 'UncertainMetric':
        return result
    number = rb'([0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?)'
    detail = re.fullmatch(rb'geometry3 candidate export rejected: 3D geometry rejected: UncertainMetric '
                          rb'\{ quantity: "(triangle area|tetrahedron volume)", value: ' + number
                          + rb', separation_bound: ' + number + rb' \}\n', stderr)
    require(detail is not None, 'Complete native metric-uncertainty diagnostic')
    quantity, value, bound = [field.decode('ascii') for field in detail.groups()]
    require(0 < Decimal(value) <= Decimal(bound), 'Positive integral within the reported separation bound')
    result.update(quantity=quantity, value=value, separation_bound=bound,
                  classification='required_positive_geometry_rejected' if selection['required_success']
                  else 'metric_ambiguity_for_individual_review')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('selection')
    parser.add_argument('native_capture', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    members = read_literals()
    cases = {r['name']: r for r in parse(members['catalog.json'])['cases']}
    case = cases[args.selection]
    report = inspect(case, members[case['input']['path']], args.native_capture)
    with args.output.open('xb') as stream:
        stream.write(encode(report))
