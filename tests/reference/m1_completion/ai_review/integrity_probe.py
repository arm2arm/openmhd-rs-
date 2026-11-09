#!/usr/bin/env python3
"""Independent small report-integrity probe; uses disposable synthetic packets."""
import ast
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'scripts'))
from run_m1_wave_loop import reanalyze, sha
from archive_m1_completion import archive
from run_prescribed_loop import evaluate

# Exercise the actual loader without requiring Matplotlib for this data-only test.
tree = ast.parse((ROOT/'scripts/plot_m1_completion.py').read_text())
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'load')
namespace = {'Path': Path, 'json': json, 'gzip': gzip, 'hashlib': hashlib}
exec(compile(ast.Module(body=[node], type_ignores=[]), '<plot loader>', 'exec'), namespace)

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    output = root/'raw'
    output.mkdir()
    for name, text in [('manifest.json', '{}'), ('runs.json', '{}'), ('summary.json', '{"pairs":[]}')]:
        (output/name).write_text(text)
    hashes = {name: sha(output/name) for name in ('manifest.json', 'runs.json', 'summary.json')}
    (output/'provenance.json').write_text(json.dumps({'revision': 'fixture', 'source_sha256': {}, 'result_sha256': hashes}))
    reanalyze(output)
    archive(output, root, root/'archived')
    assert namespace['load'](output) == namespace['load'](root/'archived')
    assert (root/'archived/execution_summary.json.gz').exists()
    (root/'archived/summary.json').write_text('{}')
    try:
        namespace['load'](root/'archived')
    except ValueError as error:
        print('shadow rejected:', error)
    else:
        raise AssertionError('unverified shadow accepted')
    (output/'summary.json').write_text('{}')
    try:
        namespace['load'](output)
    except ValueError as error:
        print('modified raw rejected:', error)
    else:
        raise AssertionError('modified raw accepted')

runs = {}
for n, error in [(32, .08), (64, .04), (128, .02), (256, None)]:
    record = {'status': 'completed', 'config': {'n': n, 'jitter': 0., 'motion': 'fixed'}}
    if error is not None:
        record['errors'] = {'passive_A': {'L1': error}}
    runs[f'loop_n{n}_base'] = record
result = evaluate(Path('.'), runs, [])['fixed_convergence'][0]
assert result['gate'].startswith('fail')
assert result['rows'][-1]['A_L1_over_peak'] is None
print('missing finest error:', result['gate'])
print('AI probe: corrected archive/raw equivalence and corruption checks PASS')
