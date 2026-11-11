#!/usr/bin/env python3
"""One immutable, preflight-verified M1 simulation in one REANA workflow."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import sys
import tarfile
from datetime import datetime, timezone


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def dump(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def run(work):
    output = work/'outputs'
    output.mkdir()  # Reruns must use a fresh workflow; never overwrite evidence.
    report = {'status': 'preparing', 'started_utc': datetime.now(timezone.utc).isoformat(),
              'visible_cpus': os.cpu_count(), 'machine': platform.machine(),
              'cgroup': {n: p.read_text().strip() for n in ('cpu.max', 'memory.max')
                         if (p := Path('/sys/fs/cgroup')/n).exists()}}
    code = 1
    try:
        payload = json.loads((work/'payload.json').read_text())
        for name, digest in payload['input_sha256'].items():
            p = PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or sha(work/name) != digest:
                raise ValueError('Changed/unsafe workflow input: '+name)
        metadata = json.loads((work/'snapshot.json').read_text())
        for target, parts in payload['parts'].items():
            if target not in ('source.tar.gz', 'vector-potential'):
                raise ValueError('Unexpected assembled input')
            with (work/target).open('wb') as stream:
                for part in parts:
                    if part not in payload['input_sha256']:
                        raise ValueError('Unverified archive part')
                    with (work/part).open('rb') as source:
                        shutil.copyfileobj(source, stream)
        if sha(work/'source.tar.gz') != metadata['archives']['source.tar.gz']['sha256']:
            raise ValueError('Changed source archive')
        source = work/'source'
        source.mkdir()
        with tarfile.open(work/'source.tar.gz') as archive:
            for member in archive.getmembers():
                p = PurePosixPath(member.name)
                if p.is_absolute() or '..' in p.parts or not member.isfile():
                    raise ValueError('Unsafe source archive')
            archive.extractall(source, filter='data')
        for name, digest in metadata['source_sha256'].items():
            if sha(source/name) != digest:
                raise ValueError('Changed source: '+name)
        if sha(work/'case.py') != metadata['source_sha256']['reana/case.py']:
            raise ValueError('Bootstrap differs from frozen source')
        sys.path.insert(0, str(source/'scripts'))
        from reana_cases import verify_preflight, validate_case
        receipt = verify_preflight(work/'snapshot.json', work/'preflight')
        binary = work/'vector-potential'
        if sha(binary) != receipt['binary_sha256'] or platform.machine() != receipt['machine']:
            raise ValueError('Prebuilt binary or architecture mismatch')
        binary.chmod(0o755)
        spec = json.loads((work/'case.json').read_text())
        validate_case(spec)
        report.update(status='running', case=spec, binary_sha256=sha(binary),
                      snapshot_sha256=sha(work/'snapshot.json'), payload_sha256=sha(work/'payload.json'),
                      preflight_sha256=sha(work/'preflight/preflight.json'))
        dump(output/'execution.json', report)
        os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                          RAYON_NUM_THREADS=str(spec['resources']['threads']))
        raw = output/'raw'
        raw.mkdir()
        options = dict(spec['options'], threads=spec['resources']['threads'],
                       timeout=spec['resources']['timeout_seconds'])
        if spec['kind'] == 'wave':
            from run_m1_wave_loop import run_case
            name, record = run_case(spec['config'], binary, raw, **options)
        else:
            from run_m1_physics import run_case, reference
            refs = {case: reference(filename)[0] for case, filename in
                    [('brio-wu', 'brio_8192.csv.gz'), ('orszag-tang', 'vortex_512.csv.gz')]}
            packet = json.loads((source/'benchmarks/m0/packet.json').read_text())
            name, record = run_case(spec['config'], binary, raw, packet, refs, **options)
        dump(output/'record.json', record)
        for filename, digest in metadata['source_sha256'].items():
            if sha(source/filename) != digest:
                raise ValueError('Source changed during execution: '+filename)
        passed = (record['status'] == 'completed' and record.get('positive_and_conservative', False)
                  and record.get('state_and_diagnostic_gates', True))
        report.update(status='completed' if passed else 'failed', record_sha256=sha(output/'record.json'),
                      single_case_gates_passed=passed,
                      scope='Single-case checks only; pair/convergence gates and M1 remain separate.')
        code = 0 if passed else 1
    except Exception as error:
        report.update(status='failed', error=str(error))
    finally:
        report['ended_utc'] = datetime.now(timezone.utc).isoformat()
        dump(output/'execution.json', report)
        dump(output/'artifacts.sha256.json', {str(p.relative_to(work)): sha(p)
             for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'artifacts.sha256.json'})
    return code


if __name__ == '__main__':
    sys.exit(run(Path.cwd().resolve()))
