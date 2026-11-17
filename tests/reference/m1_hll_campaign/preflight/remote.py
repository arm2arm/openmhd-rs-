#!/usr/bin/env python3
"""Run unchanged OpenMHD study commands in an isolated REANA workspace."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request

WORK = Path.cwd().resolve()
SOURCE = WORK/'source'
OUTPUT = WORK/'outputs'
RUNTIME = WORK/'runtime'
RUST = '1.85.1'
RUST_MANIFEST_SHA256 = '1e7dae690cd12e27405a97e64704917489a27c650201bf47780a936055d67909'
IMAGE = 'gitlab-p4n.aip.de:5005/p4nreana/reana-env@sha256:aebd7911df9e1e97ad67d15f4c32ab23996000282183fad3bf7a480756522bd7'
STUDIES = ('smoke', 'regression', 'original', 'candidate', 'prescribed', 'heun', 'threading', 'auxiliary', 'spline-full', 'physics', 'm1-bounded', 'm1-campaign')
STUDIES += ('m1-cache-campaign', 'm1-reporting-campaign', 'm1-hll-campaign')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')


def extract(archive, destination, regular_only=False):
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            p = PurePosixPath(member.name)
            if p.is_absolute() or '..' in p.parts or member.isdev():
                raise ValueError('Unsafe archive path')
            if regular_only and not member.isfile():
                raise ValueError('Source snapshot must contain regular files only')
            if member.issym() or member.islnk():
                target = PurePosixPath(member.linkname)
                if target.is_absolute() or '..' in target.parts:
                    raise ValueError('Unsafe archive link')
        tar.extractall(destination, filter='data')


def download(url, path, digest):
    if path.exists() and sha(path) == digest:
        return
    partial = path.with_name(path.name+'.partial')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as response, partial.open('wb') as stream:
                shutil.copyfileobj(response, stream)
            if sha(partial) != digest:
                raise ValueError(f'Checksum mismatch: {path.name}')
            partial.replace(path)
            return
        except (OSError, ValueError) as error:
            partial.unlink(missing_ok=True)
            if attempt == 2:
                raise RuntimeError(f'Download failed after three attempts: {path.name}') from error
            print(f'Retrying verified download: {path.name}', flush=True)
            time.sleep(2**attempt)


def environment():
    # Only runtime paths and thread controls are added; credentials are not job inputs.
    env = dict(os.environ)
    env.update(PATH=str(RUNTIME/'rust/bin')+os.pathsep+env['PATH'],
               CARGO_HOME=str(RUNTIME/'cargo'), CARGO_BUILD_JOBS='4',
               RUST_TEST_THREADS='1',
               RAYON_NUM_THREADS='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               MPLCONFIGDIR=str(RUNTIME/'matplotlib'))
    return env


def verify_source(metadata):
    for name, digest in metadata['source_sha256'].items():
        if sha(SOURCE/name) != digest:
            raise ValueError(f'Changed source: {name}')


def prepare(resume=False):
    if (OUTPUT/'execution.json').exists():
        raise ValueError('Preparation cannot modify a workspace with an execution record.')
    if not resume and (SOURCE.exists() or RUNTIME.exists()):
        raise ValueError('Preparation requires a fresh workflow workspace.')
    metadata = json.loads((WORK/'snapshot.json').read_text())
    for name, digest in metadata['upload_sha256'].items():
        if sha(WORK/name) != digest:
            raise ValueError(f'Changed upload: {name}')
    for filename, record in metadata['archives'].items():
        with (WORK/filename).open('wb') as archive:
            for name in record['parts']:
                with (WORK/name).open('rb') as part:
                    shutil.copyfileobj(part, archive)
        if sha(WORK/filename) != record['sha256']:
            raise ValueError('Reassembled archive checksum mismatch: '+filename)
    OUTPUT.mkdir(exist_ok=True)
    if not SOURCE.exists():
        subprocess.run(['git', 'clone', '--no-checkout', str(WORK/'source.bundle'), str(SOURCE)], check=True)
        subprocess.run(['git', 'reset', '--mixed', metadata['revision']], cwd=SOURCE, check=True, stdout=subprocess.DEVNULL)
        extract(WORK/'source.tar.gz', SOURCE, regular_only=True)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip()
    if revision != metadata['revision']:
        raise ValueError('Prepared Git revision changed')
    verify_source(metadata)
    RUNTIME.mkdir(exist_ok=True)
    downloads = RUNTIME/'downloads'
    downloads.mkdir(exist_ok=True)
    manifest = downloads/'rust-manifest.toml'
    download(f'https://static.rust-lang.org/dist/channel-rust-{RUST}.toml', manifest, RUST_MANIFEST_SHA256)
    import tomllib
    release = tomllib.loads(manifest.read_text())
    targets = {'x86_64': 'x86_64-unknown-linux-gnu', 'aarch64': 'aarch64-unknown-linux-gnu'}
    target = targets[platform.machine()]
    packages = {}
    for name in ('rustc', 'cargo', 'rust-std', 'rustfmt-preview', 'clippy-preview'):
        package = release['pkg'][name]['target'][target]
        archive = downloads/Path(package['xz_url']).name
        download(package['xz_url'], archive, package['xz_hash'])
        extract(archive, downloads)
        directory = downloads/archive.name.removesuffix('.tar.xz')
        subprocess.run(['sh', str(directory/'install.sh'), '--prefix='+str(RUNTIME/'rust'), '--disable-ldconfig'], check=True)
        packages[name] = {'url': package['xz_url'], 'sha256': package['xz_hash']}
        shutil.rmtree(directory)
    env = environment()
    runtime = {'created_utc': datetime.now(timezone.utc).isoformat(), 'image': IMAGE,
               'platform': platform.platform(), 'machine': platform.machine(),
               'python': sys.version, 'rust_packages': packages,
               'rustc': subprocess.check_output(['rustc', '-Vv'], env=env, text=True),
               'snapshot_sha256': sha(WORK/'snapshot.json'),
               'bootstrap_sha256': sha(Path(__file__)), 'bootstrap_file': Path(__file__).name,
               'source_bootstrap_sha256': metadata['source_sha256']['reana/remote.py'],
               'resumed_preparation': resume,
               'visible_cpus': os.cpu_count(), 'thread_policy': 'study controls case/thread allocation within 24 cores; FFI threads=1'}
    for name in ('cpu.max', 'memory.max'):
        p = Path('/sys/fs/cgroup')/name
        if p.exists():
            runtime[name] = p.read_text().strip()
    for name in ('numpy', 'matplotlib'):
        runtime[name] = __import__(name).__version__
    dump(OUTPUT/'runtime.json', runtime)
    print('Verified source and pinned Rust toolchain are ready.', flush=True)


def commands(study, jobs):
    python = sys.executable
    if study in ('m1-cache-campaign', 'm1-reporting-campaign'):
        campaign = commands('m1-campaign', jobs)
        script = 'run_projection_cache_benchmark.py' if study=='m1-cache-campaign' else 'run_projection_metadata_check.py'
        output = 'results/reana_projection-cache' if study=='m1-cache-campaign' else 'results/reana_projection-metadata'
        return campaign[:-1] + [
            [python, 'scripts/'+script,
             '--baseline', str(WORK/'baseline-vector-potential'),
             '--baseline-provenance', str(WORK/'baseline-provenance.json'),
             '--output-dir', output], campaign[-1]]
    if study == 'm1-hll-campaign':
        campaign = commands('m1-campaign', jobs)
        campaign[-1].extend(['--riemann', 'hll'])
        return campaign
    if study == 'm1-campaign':
        return commands('smoke', jobs)[:7] + [
            ['cargo', 'test', '--release', '--workspace', '--all-targets', '--locked'],
            [python, 'scripts/run_m1_campaign.py', '--jobs', str(jobs),
             '--output-dir', 'results/reana_m1-campaign'],
        ]
    if study == 'm1-bounded':
        return commands('smoke', jobs)[:7] + [
            [python, 'scripts/run_m1_bounded.py', '--medium', '--medium-jobs', str(jobs),
             '--output-dir', 'results/reana_m1-bounded'],
        ]
    if study == 'physics':
        return commands('smoke', jobs)[:7] + [
            [python, 'scripts/run_m1_physics.py', '--jobs', str(jobs),
             '--output-dir', 'results/reana_physics'],
        ]
    if study == 'spline-full':
        return commands('smoke', jobs)[:7] + [
            [python, 'scripts/run_m1_wave_loop.py', '--suite', 'physical', '--temporal',
             '--profile', 'bulk-frame-heun-spline-v1', '--jobs', str(jobs),
             '--output-dir', 'results/reana_spline-full'],
        ]
    if study == 'threading':
        if jobs != 1:
            raise ValueError('Threading study requires jobs=1: one simulation with up to 24 threads')
        return commands('smoke', jobs)[:7] + [
            [python, 'scripts/run_threading_validation.py', '--output-dir', 'results/reana_threading'],
        ]
    if study in ('heun', 'auxiliary'):
        return commands('smoke', jobs)[:7] + [
            [python, 'scripts/run_heun_temporal.py', '--jobs', str(jobs), '--output-dir', 'results/reana_'+study,
             *(['--auxiliary-study'] if study == 'auxiliary' else [])],
            [python, 'scripts/plot_heun_temporal.py', 'results/reana_'+study],
        ]
    if study == 'smoke':
        return [
            ['cargo', 'fmt', '--check'],
            ['cargo', 'clippy', '--all-targets', '--all-features', '--locked', '--', '-D', 'warnings'],
            ['cargo', 'test', '--workspace', '--locked'],
            ['cargo', 'build', '--release', '--workspace', '--locked'],
            [python, '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_*.py'],
            [python, 'scripts/check_m0_spec.py'],
            [python, 'scripts/check_reference_packet.py'],
            ['target/release/vector-potential', '--case', 'alfven', '--profile', 'bulk-frame-signal-v1',
             '--n', '8', '--time', '0.02', '--output', 'results/reana_smoke_wave'],
            ['target/release/prescribed-loop', '--n', '8', '--time', '0.02', '--output', 'results/reana_smoke_loop'],
        ]
    if study == 'regression':
        return [[python, '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_*.py']] + [[python, 'scripts/'+name] for name in
                ('run_core_flux_validation.py', 'run_mesh_validation.py', 'run_kinematic_2d.py',
                 'run_coupled_2d.py', 'run_vector_potential.py')]
    common = ['--jobs', str(jobs), '--output-dir', 'results/reana_'+study]
    if study == 'prescribed':
        return [[python, 'scripts/run_prescribed_loop.py', *common]]
    options = ['--suite', 'physical'] if study == 'original' else ['--profile', 'bulk-frame-signal-v1']
    return [[python, 'scripts/run_m1_wave_loop.py', *options, '--temporal', *common]]


def run(study, jobs):
    if (OUTPUT/'execution.json').exists():
        raise ValueError('Use a fresh workflow for reruns; existing execution records are retained.')
    metadata = json.loads((WORK/'snapshot.json').read_text())
    verify_source(metadata)
    env = environment()
    logs = OUTPUT/'logs'
    logs.mkdir(exist_ok=True)
    report = {'study': study, 'jobs': jobs, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'snapshot_sha256': sha(WORK/'snapshot.json'), 'runtime_sha256': sha(OUTPUT/'runtime.json'),
              'status': 'running', 'commands': [],
              'scope': 'Execution status is separate from scientific acceptance; known failed gates remain in summaries.'}
    report['execution_cgroup'] = {name: (Path('/sys/fs/cgroup')/name).read_text().strip()
                                 for name in ('cpu.max','memory.max') if (Path('/sys/fs/cgroup')/name).exists()}
    report['visible_cpus'] = os.cpu_count()
    dump(OUTPUT/'execution.json', report)
    code = 0
    try:
        for i, command in enumerate(commands(study, jobs)):
            print('Running: '+ ' '.join(command), flush=True)
            start = time.monotonic()
            log = logs/f'{i:02d}.log'
            with log.open('w') as stream:
                done = subprocess.run(command, cwd=SOURCE, env=env, stdout=stream, stderr=subprocess.STDOUT)
            report['commands'].append({'command': command, 'returncode': done.returncode,
                                       'seconds': time.monotonic()-start, 'log': str(log.relative_to(WORK)), 'log_sha256': sha(log)})
            dump(OUTPUT/'execution.json', report)
            if done.returncode:
                raise RuntimeError(f'Command {i} failed; see {log.relative_to(WORK)}')
        if study in ('original', 'candidate', 'prescribed', 'spline-full'):
            raw = SOURCE/'results'/('reana_'+study)
            summary = json.loads((raw/'summary.json').read_text())
            records = json.loads((raw/'runs.json').read_text())
            expected = {'original': 112, 'candidate': 184, 'prescribed': 32, 'spline-full': 112}[study]
            if len(records) != expected or any(r['status'] != 'completed' for r in records.values()):
                raise ValueError('Incomplete or failed evolutions; raw outputs are retained.')
            report['completed_evolutions'] = len(records)
            report['scientific_summary'] = 'outputs/'+study+'/summary.json.gz'
            subprocess.run([sys.executable, 'scripts/archive_m1_completion.py', str(raw), str(SOURCE),
                            str(OUTPUT/study)], cwd=SOURCE, env=env, check=True)
        if study in ('heun', 'auxiliary'):
            raw = SOURCE/('results/reana_'+study)
            summary = json.loads((raw/'summary.json').read_text())
            expected = 80 if study == 'auxiliary' else 40
            if summary['completed_evolutions'] != expected:
                raise ValueError('Incomplete Heun investigation')
            report['completed_evolutions'] = expected
            report['scientific_summary'] = 'outputs/'+study+'/summary.json'
            (OUTPUT/study).mkdir()
            for name in ('summary.json', 'runs.json', 'manifest.json', 'provenance.json', 'temporal.png'):
                shutil.copyfile(raw/name, OUTPUT/study/name)
            with tarfile.open(OUTPUT/(study+'-raw.tar.gz'), 'w:gz') as archive:
                archive.add(raw, arcname=study)
        if study == 'physics':
            raw = SOURCE/'results/reana_physics'
            summary = json.loads((raw/'summary.json').read_text())
            records = json.loads((raw/'runs.json').read_text())
            destination = OUTPUT/'physics'
            destination.mkdir()
            for name in ('summary.json', 'runs.json', 'manifest.json', 'provenance.json'):
                shutil.copyfile(raw/name, destination/name)
            # Raw cells/polygons remain in the workflow workspace, covered by
            # the per-run SHA manifest. Export compact diagnostics/projections.
            with tarfile.open(OUTPUT/'physics-measurements.tar.gz', 'w:gz') as archive:
                for case in sorted(records):
                    for name in ('summary.json', 'history.json', 'physics.json', 'timing.json',
                                 'projected_bins.json', 'failure.txt', 'run.log'):
                        if (raw/case/name).exists():
                            archive.add(raw/case/name, arcname=case+'/'+name)
            report['completed_evolutions'] = summary['completed_evolutions']
            report['scientific_summary'] = 'outputs/physics/summary.json'
            if not summary['complete'] or not summary['registered_configuration'] or len(records) != 30:
                raise ValueError('Incomplete general shock/vortex study; failed outputs are retained.')
        if study == 'threading':
            raw = SOURCE/'results/reana_threading'
            summary = json.loads((raw/'summary.json').read_text())
            records = json.loads((raw/'runs.json').read_text())
            if summary['status'] != 'completed' or len(records) != 9:
                raise ValueError('Incomplete threading study')
            report['completed_evolutions'] = len(records)
            (OUTPUT/'threading').mkdir()
            for name in ('summary.json', 'runs.json', 'provenance.json'):
                shutil.copyfile(raw/name, OUTPUT/'threading'/name)
            report['scientific_summary'] = 'outputs/threading/summary.json'
            with tarfile.open(OUTPUT/'threading-raw.tar.gz', 'w:gz') as archive:
                archive.add(raw, arcname='threading')
        verify_source(metadata)
        report['status'] = 'completed'
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = str(error)
        code = 1
    finally:
        if study in ('m1-cache-campaign', 'm1-reporting-campaign'):
            packet = 'projection-cache' if study=='m1-cache-campaign' else 'projection-metadata'
            summary_name = 'benchmark.json' if study=='m1-cache-campaign' else 'report.json'
            raw = SOURCE/('results/reana_'+packet)
            if raw.exists():
                with tarfile.open(OUTPUT/(packet+'-raw.tar.gz'), 'w:gz') as archive:
                    archive.add(raw, arcname=packet)
                if (raw/summary_name).exists():
                    shutil.copyfile(raw/summary_name, OUTPUT/(packet+'.json'))
        if study in ('m1-campaign', 'm1-cache-campaign', 'm1-reporting-campaign', 'm1-hll-campaign'):
            raw = SOURCE/'results/reana_m1-campaign'
            if raw.exists():
                destination = OUTPUT/study
                destination.mkdir(exist_ok=True)
                if (raw/'campaign.json').exists():
                    shutil.copyfile(raw/'campaign.json', destination/'campaign.json')
                    report['scientific_summary'] = 'outputs/'+study+'/campaign.json'
                # Full snapshots stay in the workflow workspace with per-run hashes.
                # Export all compact diagnostics, including failed/partial phases.
                with tarfile.open(OUTPUT/(study+'-measurements.tar.gz'), 'w:gz') as archive:
                    for p in sorted(raw.rglob('*')):
                        if p.is_file() and (p.suffix in ('.log', '.txt') or
                                           (p.suffix=='.json' and p.name not in ('geometry.json','geometry_vertices.json'))):
                            archive.add(p, arcname=str(p.relative_to(raw)), recursive=False)
        # Preserve the gate and every failed/partial stage even when its command exits 1.
        if study == 'm1-bounded':
            raw = SOURCE/'results/reana_m1-bounded'
            if raw.exists():
                destination = OUTPUT/study
                destination.mkdir(exist_ok=True)
                if (raw/'gate.json').exists():
                    shutil.copyfile(raw/'gate.json', destination/'gate.json')
                    report['scientific_summary'] = 'outputs/'+study+'/gate.json'
                with tarfile.open(OUTPUT/(study+'-raw.tar.gz'), 'w:gz') as archive:
                    archive.add(raw, arcname=study)
        report['ended_utc'] = datetime.now(timezone.utc).isoformat()
        dump(OUTPUT/'execution.json', report)
        dump(OUTPUT/'artifacts.sha256.json', {str(p.relative_to(WORK)): sha(p)
             for p in sorted(OUTPUT.rglob('*')) if p.is_file() and p.name != 'artifacts.sha256.json'})
    sys.exit(code)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'run'))
    parser.add_argument('--study', choices=STUDIES, default='smoke')
    parser.add_argument('--jobs', type=int, default=24)
    parser.add_argument('--resume-prepare', action='store_true',
                        help='Recover preparation only, after validating the original source and cached downloads')
    args = parser.parse_args()
    if not 1 <= args.jobs <= 24:
        parser.error('jobs must be between 1 and 24')
    if args.stage == 'prepare':
        prepare(args.resume_prepare)
    else:
        run(args.study, args.jobs)


if __name__ == '__main__':
    main()
