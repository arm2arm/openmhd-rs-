#!/usr/bin/env python3
"""Independent CLI continuation comparison; run with a fixed built executable."""
import hashlib
import json
import pathlib
import subprocess
import sys

exe = pathlib.Path(sys.argv[1]).resolve()
root = pathlib.Path(sys.argv[2]).resolve()
root.mkdir(parents=True, exist_ok=True)
artifacts = ['initial.csv', 'checkpoint_0.01000000.csv', 'checkpoint_0.02000000.csv',
             'final.csv', 'summary.json', 'history.json', 'polygons.csv']
report = {'executable_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
          'commands': [], 'cases': []}

def run(args, output):
    cmd = [str(exe), *args, '--output', str(output)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    report['commands'].append({'argv': cmd, 'status': p.returncode,
                               'stdout': p.stdout, 'stderr': p.stderr})
    if p.returncode:
        raise RuntimeError(report['commands'][-1])

for name, extra in [
    ('fixed-paper', []),
    ('fixed-projected-unlimited', ['--profile', 'bulk-frame-hll-projected-v1', '--unlimited']),
    ('fluid', ['--profile', 'bulk-frame-hll-projected-v1', '--motion', 'fluid']),
    ('prescribed', ['--profile', 'bulk-frame-hll-projected-v1', '--motion', 'prescribed']),
]:
    base = root / name
    args = ['--case', 'smooth', '--n', '6', '--jitter', '.15', '--time', '.03',
            '--dt', '.002', '--checkpoint', '.01', '--checkpoint', '.02', *extra]
    run(args, base / 'whole')
    run([*args, '--checkpoint-steps', '2', '--stop-after-steps', '7'], base / 'partial')
    run(['--resume', str(base / 'partial/restart.chk'), '--checkpoint-steps', '3'], base / 'resumed')
    hashes = {}
    for name_of_file in artifacts:
        whole = (base / 'whole' / name_of_file).read_bytes()
        resumed = (base / 'resumed' / name_of_file).read_bytes()
        assert whole == resumed, (name, name_of_file)
        hashes[name_of_file] = hashlib.sha256(whole).hexdigest()
    steps = json.loads((base / 'whole/summary.json').read_text())['steps']
    report['cases'].append({'name': name, 'accepted_steps': steps, 'identical_artifacts_sha256': hashes})
    print(name, '7 artifacts byte-identical;', steps, 'accepted steps')
(root / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
