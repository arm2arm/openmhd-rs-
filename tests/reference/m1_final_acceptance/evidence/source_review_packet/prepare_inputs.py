"""Stage retained REANA observations for independent reducers; never runs evolution.

Run from repository root. Missing geometry/bin observations may be downloaded
from their original workflows with --client PATH_TO_REANA_ADAPTER. --cache may
reuse another stage only after checking the candidate run's exact artifact hash.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['waves', 'physics'])
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--cache', type=Path, action='append', default=[])
    parser.add_argument('--client', type=Path)
    args = parser.parse_args()
    source, out = args.directory.resolve(), args.output.resolve()
    if out.exists():
        parser.error('Use a fresh stage')
    out.mkdir(parents=True)
    runs = json.loads((source/'runs.json').read_text())
    plan = json.loads((source/'plan.json').read_text())
    entries = {row['specification']['config']['name']: row for row in plan['cases']}
    assert set(entries) == set(runs)
    assert all(row['status'] == 'completed' and row['config'] == entries[name]['specification']['config']
               for name, row in runs.items())
    shutil.copyfile(source/'runs.json', out/'runs.json')
    (out/'manifest.json').write_text(json.dumps({name: row['specification']['config']
                                               for name, row in entries.items()}, indent=1)+'\n')
    reference = Path('tests/reference/external_mhd')
    pinned = json.loads((reference/'provenance.json').read_text())
    provenance = dict(scope='Read-only adapter of original completed case observations; not original execution provenance.',
                      original_run_map_sha256=sha(source/'runs.json'), plan_sha256=sha(source/'plan.json'),
                      snapshot_sha256=plan['snapshot_sha256'],
                      reference_sha256=pinned['result_sha256'],
                      source_sha256={'benchmarks/m0/packet.json': sha(Path('benchmarks/m0/packet.json'))})
    (out/'provenance.json').write_text(json.dumps(provenance, indent=1)+'\n')
    observations = []
    for name, run in runs.items():
        config = run['config']
        if args.phase == 'physics' and not (config['jitter'] == 0. or config.get('jitter_mode') == 'columns'):
            continue
        directory = out/name
        directory.mkdir()
        files = ['final.csv']
        if args.phase == 'physics':
            files += ['geometry.json']
            if config['case'] == 'orszag-tang':
                files += ['projected_bins.json']
        for file in files:
            expected = run['sha256'][file]
            candidates = [source/'raw'/name/file, *(cache.resolve()/name/file for cache in args.cache)]
            found = next((path for path in candidates if path.exists() and sha(path) == expected), None)
            downloaded = False
            if found is None:
                if args.client is None:
                    raise FileNotFoundError(f'Missing verified {name}/{file}; supply --client or --cache')
                destination = out/'downloads'/name
                destination.mkdir(parents=True, exist_ok=True)
                remote = 'outputs/case/'+file
                receipt = subprocess.run([sys.executable, str(args.client.resolve()), 'download', '-w',
                                          entries[name]['workflow'], '-o', str(destination), remote],
                                         capture_output=True, text=True, timeout=1800)
                (destination/(file+'.download.log')).write_text(receipt.stdout+receipt.stderr)
                found = destination/remote
                assert receipt.returncode == 0 and found.exists() and sha(found) == expected
                downloaded = True
            (directory/file).symlink_to(found.resolve())
            observations.append(dict(name=name, artifact=file, sha256=expected,
                                     workflow=entries[name]['workflow'], local_source=str(found),
                                     downloaded=downloaded))
    (out/'input_receipts.json').write_text(json.dumps(observations, indent=1)+'\n')
    print('Staged hash-checked observations:', len(observations))


if __name__ == '__main__':
    main()
