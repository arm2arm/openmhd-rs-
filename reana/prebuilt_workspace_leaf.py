"""Run one catalogued workspace test from its original REANA build."""
import base64
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import sys
import tarfile
import types
import zipfile


# Both the build and all its individual archive members were verified in
# docs/galaxy/results/workspace_recovery_20261125/verification.json.
ARCHIVE = 'e324f3bb1c7d5b6c93c717e0dccd4f9921f6219cce3a2e17d4e074fbe2936ca7'
PARENT_UUID = '5c48383b-2685-49ed-8518-f1b37180c09c'
PREFLIGHT = '19428f5b1642c5da97b1bc95a6364a0e48c6a2c483df2023d549977358503a91'
ORIGINAL_RUNNER = 'bfa16640bb2bfef7852cba623d52bbd6c21d236488a23917bd20fbc76e34aca9'
THREADS = ('RUST_TEST_THREADS', 'RAYON_NUM_THREADS', 'OMP_NUM_THREADS',
           'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')
RESOURCES = {'threads': 1, 'memory': '2Gi', 'command_timeout_seconds': 1800}
CONTENTS = ('result.json', 'command.json', 'stdout.txt', 'stderr.txt')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def materials(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        require(len(members) < 32 and len({m.filename for m in members}) == len(members)
                and sum(m.file_size for m in members) <= 16 * 1024 * 1024, 'Bounded case inputs')
        data = {m.filename: archive.read(m) for m in members}
    require(digest(data['workspace_case.py']) == ORIGINAL_RUNNER, 'Original validation helper')
    runner = types.ModuleType('workspace_case')
    runner.__file__ = 'workspace_case.py'
    exec(compile(data['workspace_case.py'], runner.__file__, 'exec'), runner.__dict__)
    require(set(data) == runner.FIXED | {'payload.json', 'export.json', 'source.tar.gz'},
            'Exact input inventory')
    case, snapshot, selectors = runner.validate_inputs({n: data[n] for n in runner.FIXED}, data['payload.json'])
    leaf = case['leaf']
    require(case['parent_uuid'] == PARENT_UUID and digest(data['parent/preflight.json']) == PREFLIGHT,
            'Qualified workspace preflight')
    require((leaf['manifest'], leaf['target_name']) != ('apps/openmhd/Cargo.toml', 'restart'),
            'Restart integration target requires the source-layout build')
    artifacts = runner.parse(data['parent/artifacts.sha256.json'])
    export = runner.parse(data['export.json'])
    require(digest(data['export.json']) == artifacts['outputs/galaxy-preflight/export.json']
            and export['archive_sha256'] == ARCHIVE and export['preflight_sha256'] == PREFLIGHT
            and leaf['binary_sha256'] == export['members'][leaf['binary']]['sha256']
            == artifacts['outputs/galaxy-preflight/' + leaf['binary']], 'Original exported binary')
    require(digest(data['source.tar.gz']) == snapshot['archives']['source.tar.gz']['sha256'],
            'Original workspace source archive')
    return runner, data, leaf, selectors, snapshot, export['members'][leaf['binary']]['bytes']


def restore_source(raw, snapshot, directory):
    directory.mkdir()
    pins = snapshot['source_sha256']
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        for member in archive:
            require(member.isfile() and member.name in pins and member.name not in seen,
                    'Exact regular source members')
            content = archive.extractfile(member).read()
            require(digest(content) == pins[member.name], 'Original source bytes')
            seen.add(member.name)
            path = directory / member.name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    require(seen == set(pins), 'Complete source layout')


def run(work):
    output = work / 'outputs'
    output.mkdir()
    stages = []
    report = {'status': 'failed', 'schema': 'openmhd.prebuilt-workspace-leaf.v1',
              'uuid': work.name, 'resources': RESOURCES, 'component_accepted': False}
    try:
        require(sys.flags.optimize == 0 and os.uname().machine == 'x86_64', 'Linux x86-64 target')
        packed = (work / 'materials.zip').read_bytes()
        runner, data, leaf, names, snapshot, size = materials(packed)
        source = work / 'source'
        restore_source(data['source.tar.gz'], snapshot, source)
        binary = source / 'target' / leaf['build_profile'] / 'deps' / Path(leaf['binary']).name
        binary.parent.mkdir(parents=True, exist_ok=True)
        require(0 < size <= runner.MAX_EXECUTABLE_BYTES, 'Bounded catalog binary')
        with gzip.open(work / 'libtest.gz', 'rb') as gz:
            raw = gz.read(size + 1)
        require(len(raw) == size and digest(raw) == leaf['binary_sha256'], 'Binary size and hash')
        binary.write_bytes(raw)
        binary.chmod(0o755)
        del raw
        supervisor = runner.load_module('native_supervisor', data['supervisor.py'], work / 'supervisor.py')
        launcher = runner.load_module('native_launcher', data['launcher.py'], work / 'launcher.py')
        env = dict(os.environ, **dict.fromkeys(THREADS, '1'))
        links = {'materials_sha256': digest(packed), 'runner_sha256': digest(Path(__file__).read_bytes()),
                 'binary_sha256': leaf['binary_sha256'], 'preflight_sha256': PREFLIGHT}
        report.update(leaf=leaf, input_links=links, machine=os.uname().machine, python=platform.python_version(),
                      parent_uuid=PARENT_UUID, thread_environment={k: env[k] for k in THREADS})
        for label, arguments in (('list', ['--list', '--format', 'terse']),
                                 ('ignored-list', ['--list', '--ignored', '--format', 'terse']),
                                 ('leaf', ['--exact', leaf['selector'], '--test-threads', '1',
                                           '--color', 'never', '--show-output'])):
            stdout = runner.execute_stage(output, source, label, [str(binary), *arguments],
                                          supervisor, launcher, env, links, stages)
            if label == 'list':
                require(runner.listing(stdout) == names, 'Exact target test catalog')
            elif label == 'ignored-list':
                require(stdout == b'', 'Empty ignored-test list')
            else:
                report['witness'] = launcher.witness(stdout, leaf['selector'], len(names))
        require(digest(binary.read_bytes()) == leaf['binary_sha256']
                and (work / 'materials.zip').read_bytes() == packed
                and all(digest((source / n).read_bytes()) == h for n, h in snapshot['source_sha256'].items()),
                'Unchanged binary, test inputs and frozen source')
        report['status'] = 'passed'
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc))
    finally:
        items = {'result.json': json.dumps(report, indent=2).encode(),
                 'command.json': json.dumps(stages).encode()}
        for channel in ('stdout', 'stderr'):
            items[channel + '.txt'] = base64.b64decode(stages[-1][channel + '_base64']) if stages else b''
        items['manifest.json'] = json.dumps({n: digest(v) for n, v in items.items()}).encode()
        with tarfile.open(output / 'evidence.tar.gz', 'w:gz') as archive:
            for name, content in items.items():
                info = tarfile.TarInfo(name)
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(run(Path.cwd().resolve()))
