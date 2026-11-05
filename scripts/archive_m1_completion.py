#!/usr/bin/env python3
"""Archive completed M1 study ledgers and figure inputs after raw-hash checks.

Completion here means every planned run has a recorded outcome, including failures;
it does not mean numerical acceptance. Large raw CSVs remain in the execution tree.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
from m1_mesh_cache import validate_reuse


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def verify(directory):
    names = ('manifest.json', 'runs.json', 'summary.json', 'provenance.json',
             'execution_provenance.json', 'execution_summary.json',
             'measurement_provenance.json', 'reuse_origin.json',
             'interruption.json', 'external_stop.json')
    paths = [directory/n for n in names if (directory/n).is_file()]
    paths += [p for p in (directory/'reuse_source').rglob('*') if p.is_file()]
    captured = {str(p.relative_to(directory)): p.read_bytes() for p in paths}
    read = lambda name: json.loads(captured[name])
    digest = lambda name: hashlib.sha256(captured[name]).hexdigest()
    original = 'execution_provenance.json' in captured
    provenance = read('execution_provenance.json' if original else 'provenance.json')
    # Validate reuse against the same captured bytes that will be archived.
    with tempfile.TemporaryDirectory(prefix='m1-reuse-check-') as tmp:
        for name, raw in captured.items():
            if name == 'reuse_origin.json' or name.startswith('reuse_source/'):
                target = Path(tmp)/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
        validate_reuse(Path(tmp), provenance)
    expected = provenance.get('result_sha256', {})
    for name in ('manifest.json', 'runs.json'):
        if name not in expected or digest(name) != expected[name]:
            raise ValueError(f'incomplete or changed execution metadata: {directory/name}')
    summary = 'execution_summary.json' if original else 'summary.json'
    if digest(summary) != expected['summary.json']:
        raise ValueError('changed original execution summary')
    if original:
        analysis = read('measurement_provenance.json')
        if digest('summary.json') != analysis['summary_sha256']:
            raise ValueError('changed measured summary')
        if digest('execution_provenance.json') != analysis['execution_provenance_sha256']:
            raise ValueError('changed execution provenance')
        for name, key in [('runs.json', 'raw_runs_sha256'),
                          ('execution_summary.json', 'execution_summary_sha256')]:
            if digest(name) != analysis[key]:
                raise ValueError('changed measurement input digest')
    manifest, runs = read('manifest.json'), read('runs.json')
    measured = read('summary.json')['runs']
    if set(manifest) != set(runs):
        raise ValueError('not every planned run has an outcome')
    if set(measured) != set(runs):
        raise ValueError('measurement run set differs from execution')
    for name, run in runs.items():
        if run['config'] != manifest[name]:
            raise ValueError('run configuration differs from manifest')
        hashes = run.get('sha256', run.get('artifacts_sha256'))
        if not hashes:
            raise ValueError('missing raw artifact hashes')
        if 'exit_code' in run and 'returncode' in run and run['exit_code'] != run['returncode']:
            raise ValueError('conflicting exit code fields')
        status = run['status']
        code = run.get('exit_code', run.get('returncode'))
        if type(code) is not int or status not in ('completed', 'failed', 'failed evolution'):
            raise ValueError('unknown or nonterminal execution outcome')
        if (status == 'completed') != (code == 0):
            raise ValueError('status and exit code disagree')
        required = {'run.log'}
        if status == 'completed':
            required.update(('initial.csv', 'final.csv', 'summary.json'))
            case = run['config']['case']
            if case in ('brio', 'vortex'):
                required.add('polygons.csv')
            if case == 'alfven' and run['config'].get('dt') is None:
                required.add('checkpoint_0.25000000.csv')
        if not required <= hashes.keys():
            raise ValueError('successful run lacks required recorded artifacts')
        for filename, raw_digest in hashes.items():
            if sha(directory/name/filename) != raw_digest:
                raise ValueError(f'changed raw artifact: {name}/{filename}')
        measurement = measured[name]
        if measurement['config'] != run['config'] or measurement['status'] != status:
            raise ValueError('measurement identity differs from execution')
        if status == 'completed' and run['config']['case'] in ('brio', 'vortex'):
            projection = directory/name/'projection.json'
            projection_digest = measurement.get('projection_sha256')
            if projection_digest is None:
                raise ValueError('projection is not sealed; rerun --analyze-only with the current measurement script')
            if not projection.is_file():
                raise ValueError('missing measured projection')
            raw = projection.read_bytes()
            if hashlib.sha256(raw).hexdigest() != projection_digest:
                raise ValueError('changed measured projection')
            captured[str(projection.relative_to(directory))] = raw
    return runs, captured


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wave-dir', type=Path)
    parser.add_argument('--remaining-dir', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    sources = [(label, path) for label, path in
               [('wave', args.wave_dir), ('remaining', args.remaining_dir)] if path is not None]
    if not sources:
        parser.error('supply at least one completed study')
    verified = {label: verify(path) for label, path in sources}
    records = {label: data[0] for label, data in verified.items()}
    out = args.output_dir
    if out.exists():
        raise FileExistsError(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.m1-archive-', dir=out.parent) as tmp:
        staging = Path(tmp)/'payload'
        staging.mkdir()
        originals = {}
        for label, (_, captured) in verified.items():
            for name, raw in captured.items():
                relative = Path(name)
                target = staging/label/relative.with_suffix(relative.suffix+'.gz')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(gzip.compress(raw, mtime=0))
                if gzip.decompress(target.read_bytes()) != raw:
                    raise ValueError('archive round-trip differs')
                originals[str(target.relative_to(staging))] = hashlib.sha256(raw).hexdigest()
        metadata = {
            'scope': 'Verified execution ledgers and figure inputs, not an acceptance assertion.',
            'large_raw_csv_policy': 'Retained in execution directories; original digests and commands are in run ledgers.',
            'script_sha256': sha(Path(__file__)),
            'sources': {label: str(path.resolve()) for label, path in sources},
            'run_outcomes': {label: {status: sum(r['status'] == status for r in runs.values())
                                    for status in sorted({r['status'] for r in runs.values()})}
                             for label, runs in records.items()},
            'uncompressed_sha256': originals,
            'archive_sha256': {str(p.relative_to(staging)): sha(p) for p in sorted(staging.rglob('*')) if p.is_file()},
        }
        (staging/'archive_provenance.json').write_text(json.dumps(metadata, indent=2)+'\n')
        if out.exists():
            raise FileExistsError(out)
        staging.rename(out)
    print(f'Verified and archived {sum(map(len, records.values()))} recorded run outcomes: {out}')


if __name__ == '__main__':
    main()
