"""Stage the O01 arithmetic controls and fixture selections without evaluating a target."""
import argparse
from pathlib import Path

from geometry3_operator_fixtures import DESIGN_SHA256, catalog
from prepare_general_geometry_jobs import ROOT, digest, stage, write_json


METHODS = ('test_noncentral_product_all_curl_placements_and_chart_samples',
           'test_basis_coverage_affine_weights_and_rank_deficiency')


def prepare(output):
    if digest((ROOT / 'docs/galaxy/MESH_3D_SPEC.md').read_bytes()) != DESIGN_SHA256:
        raise ValueError('O01 mesh specification differs from the registered design')
    modules = ('geometry3_operator_fixtures.py', 'galaxy_geometry3_reference.py')
    inputs = {n: (ROOT / 'scripts' / n).read_bytes() for n in modules}
    output.mkdir()
    plan = dict(design_sha256=DESIGN_SHA256, controls=[], fixtures=[])
    tests = dict(inputs, **{'test_geometry3_operator_fixtures.py':
                           (ROOT / 'scripts/test_geometry3_operator_fixtures.py').read_bytes()})
    # This parent only imports the same source and resolves both exact selectors.
    parent_program = (
        "import unittest\n"
        "import test_geometry3_operator_fixtures as tests\n"
        f"names = {METHODS!r}\n"
        "observed = unittest.defaultTestLoader.getTestCaseNames(tests.ManufacturedOperators)\n"
        "if sorted(names) != observed: raise ValueError('O01 source/test identity')\n"
        "print(*observed, sep='\\n')\n"
    )
    parent = output / 'preflight'
    controls = dict(tests, **{'resolve_controls.py': parent_program.encode()})
    plan['preflight'] = stage(parent, controls, 'resolve_controls.py > imported.txt', ['imported.txt'],
                              1, '2Gi', 300, 'import-operator-reference', output_prefix='')
    for method in METHODS:
        folder = output / 'controls' / method
        selector = 'test_geometry3_operator_fixtures.ManufacturedOperators.' + method
        command = f'-m unittest -v {selector} > test.txt 2>&1'
        job = stage(folder, tests, command, ['test.txt'], 1, '2Gi', 300, 'check-operator-reference', output_prefix='')
        plan['controls'].append(dict(job, selector=selector))
    for name in catalog():
        # Reference generation writes one immutable packet; it does not execute a Rust fit.
        folder = output / 'fixtures' / name
        command = 'geometry3_operator_fixtures.py ' + name + ' fixture.json'
        job = stage(folder, inputs, command, ['fixture.json'], 1, '2Gi', 300, 'freeze-operator-input', output_prefix='')
        plan['fixtures'].append(job)
    write_json(output / 'plan.json', plan)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    prepare(parser.parse_args().destination)
