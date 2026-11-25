"""Check a terminal offline regression capture against its staged native case.

This reads captured REANA outputs. It never runs Cargo or a test executable.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reana'))
import galaxy_workspace_case as runner
from galaxy_test_case import witness

PLAN_SHA256 = 'd9d323a4c681eaf10a8f4ade64040907c0ca89cf0657cb86a79b424f840b442b'
TOOL_PINS = {
    'runtime/rust/bin/cargo': '87e9ff02f95ea17d877e7c4eeb0f365f50fe3827f5afec132131ff3b8031a57e',
    'runtime/rust/bin/rustc': 'f8d033fd72e878ec60493788c8bffec2e6c154dcab6f0cb4c145af8ada26a7ed',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def planned_case(directory):
    plan_raw = (directory.parent / 'plan.json').read_bytes()
    require(sha(plan_raw) == PLAN_SHA256, 'Offline regression plan')
    entry, = [e for e in json.loads(plan_raw)['cases'] if e['directory'] == directory.name]
    return entry


def verify(directory, capture):
    entry = planned_case(directory)
    return _verify_terminal_case(directory, capture, entry, entry['workflow'])


def verify_retry(directory, capture, intent_path, failed_capture):
    entry = planned_case(directory)
    intent_raw = intent_path.read_bytes()
    intent = json.loads(intent_raw)
    before, after = [json.loads((failed_capture / n).read_bytes()) for n in ('before.json', 'after.json')]
    original, = before
    require(before == after and original == intent['original']
            and original['status'] == 'failed' and original['version'] == 1
            and original['workflow'] == entry['workflow'], 'Failed original workflow identity')
    manifest = (failed_capture / 'outputs/artifacts.sha256.json').read_bytes()
    require(sha(manifest) == intent['original_failure_manifest_sha256']
            and json.loads(manifest) == {'outputs/' + n: sha((failed_capture / 'outputs' / n).read_bytes())
                                         for n in runner.OUTPUTS if n != 'artifacts.sha256.json'}
            and json.loads((failed_capture / 'outputs/result.json').read_bytes())['status'] == 'failed',
            'Original failure artifacts')
    require(intent['plan_sha256'] == PLAN_SHA256 and intent['directory'] == entry['directory']
            and intent['case'] == entry['specification'] and intent['inputs'] == entry['files']
            and intent['workflow'] != original['workflow'], 'Explicit retry of the same planned inputs')
    result = _verify_terminal_case(directory, capture, entry, intent['workflow'])
    require(result['uuid'] != original['id'], 'Distinct retry workflow UUID')
    return dict(result, original_workflow=original['workflow'], original_uuid=original['id'],
                retry_intent_sha256=sha(intent_raw))


def _verify_terminal_case(directory, capture, entry, workflow):
    before, after = [json.loads((capture / n).read_bytes()) for n in ('before.json', 'after.json')]
    observed, = before
    require(before == after and observed['status'] == 'finished'
            and observed['workflow'] == workflow and observed['version'] == 1,
            'Finished same-UUID observations')
    inputs = {n: (directory / n).read_bytes() for n in entry['files']}
    require({n: dict(sha256=sha(b), bytes=len(b)) for n,b in inputs.items()} == entry['files'],
            'Exact staged inputs')
    case, snapshot, selectors = runner.validate_inputs({n: inputs[n] for n in runner.FIXED},
                                                        inputs['payload.json'])
    leaf = case['leaf']
    raw = {n: (capture / 'outputs' / n).read_bytes() for n in runner.OUTPUTS}
    require(json.loads(raw['artifacts.sha256.json']) ==
            {'outputs/' + n: sha(b) for n,b in raw.items() if n != 'artifacts.sha256.json'}, 'Output manifest')
    result, runtime, child, command = [json.loads(raw[n + '.json']) for n in ('result','runtime','child_result','command')]
    require(result['status'] == 'passed' and result['test_leaves_executed'] == result['passing_leaves'] == 1
            and result['case'] == case == entry['specification'] and result['component_accepted'] is False
            and result['payload_sha256'] == sha(inputs['payload.json'])
            and result['snapshot_sha256'] == sha(inputs['snapshot.json']), 'Executed native case identity')
    stages = child['stages']
    require(stages == command['stages'] and [s['label'] for s in stages] ==
            ['compiler','compile','list','ignored-list','leaf'], 'Complete stage sequence')
    for stage in stages:
        runner.settled(stage['command'])
        require(stage['command']['command'] == stage['argv'], 'Exact closed stage command')
    stdout = [base64.b64decode(s['stdout_base64'], validate=True) for s in stages]
    stderr = [base64.b64decode(s['stderr_base64'], validate=True) for s in stages]
    prepared_raw = base64.b64decode(child['prepared_runtime_base64'], validate=True)
    prepared = json.loads(prepared_raw)
    require(prepared['rustc'] == json.loads(inputs['parent/runtime.json'])['rustc'] == stdout[0].decode()
            and runtime['compiler_stdout_sha256'] == sha(stdout[0]) and runtime['tool_pins'] == TOOL_PINS
            and sha(prepared_raw) == runtime['prepared_runtime_sha256']
            and runtime['machine'] == prepared['machine'] == 'x86_64'
            and runtime['image'] == prepared['image'] == runner.IMAGE
            and prepared['snapshot_sha256'] == result['snapshot_sha256']
            and runtime['declared_resources'] == case['resources'], 'Actual toolchain and image')
    install = prepared['offline_dependencies']
    require(install['packages'] == 80 and install['source_replacement'] is True and install['network_offline'] is True
            and install['bundle_sha256'] == sha(inputs['locked-dependency-inputs/bundle.json'])
            and install['source_lock_sha256'] == snapshot['source_sha256']['Cargo.lock']
            and install['installer_sha256'] == sha(inputs['locked_dependencies.py']), 'Offline dependency identities')
    require(runtime['thread_environment'] == dict(CARGO_BUILD_JOBS='4', RUST_TEST_THREADS='1', RAYON_NUM_THREADS='1',
            OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1'), 'Declared thread allocation')
    work = PurePosixPath(stages[0]['argv'][0]).parents[3]
    require(work.name == observed['id'] and stages[0]['argv'] == [str(work/'runtime/rust/bin/rustc'), '-Vv']
            and stages[1]['argv'] == runner.build_argv(work,leaf), 'UUID and exact Cargo target build')
    messages = [json.loads(line) for line in stdout[1].splitlines() if line.startswith(b'{')]
    require([m['success'] for m in messages if m.get('reason') == 'build-finished'] == [True], 'Successful Cargo build')
    targets = [(leaf['manifest'],leaf['target_kind'],leaf['target_name'],leaf['source'],True)]
    if targets[0][:3] == ('apps/openmhd/Cargo.toml',['test'],'restart'):
        targets.append(('apps/openmhd/Cargo.toml',['bin'],'vector-potential','apps/openmhd/src/bin/vector-potential.rs',False))
    records = child['compiled_executables']
    require(len(records) == len(targets), 'Exact executable count')
    for record, expected in zip(records, targets):
        a = record['artifact']
        target = a['target']
        def relative(name):
            return str(PurePosixPath(name).relative_to(work/'source'))
        require(a in messages and a['reason'] == 'compiler-artifact' and
                (relative(a['manifest_path']),target['kind'],target['name'],relative(target['src_path']),a['profile']['test']) == expected,
                'Original target or CLI restart executable')
        name = PurePosixPath(a['executable'])
        require(name.is_relative_to(work/'source/target') and '..' not in name.parts
                and re.fullmatch('[a-f0-9]{64}',record['sha256'])
                and 0 < record['bytes'] == record['file_identity']['st_size']
                and record['file_identity']['st_nlink'] >= 1, 'Held Cargo executable identity')
    binary = records[0]['artifact']['executable']
    require(stages[2]['argv'] == [binary,'--list','--format','terse'] and runner.listing(stdout[2]) == selectors
            and stages[3]['argv'] == [binary,'--list','--ignored','--format','terse'] and stdout[3] == b'',
            'Exact preflight catalog and no ignored tests')
    require(stages[4]['argv'] == [binary,'--exact',leaf['selector'],'--test-threads','1','--color','never','--show-output']
            and stdout[4] == raw['stdout.txt'] == raw['child_raw.bin'] and stderr[4] == raw['stderr.txt']
            and child['witness'] == witness(stdout[4], leaf['selector'], len(selectors)), 'One matching raw pass')
    return dict(workflow=workflow, uuid=observed['id'], leaf=leaf,
                result_sha256=sha(raw['result.json']), manifest_sha256=sha(raw['artifacts.sha256.json']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--retry-intent', type=Path, help='Pre-submission record naming the retry workflow')
    parser.add_argument('--failed-capture', type=Path, help='Terminal capture of the failed original workflow')
    args = parser.parse_args()
    if bool(args.retry_intent) != bool(args.failed_capture):
        parser.error('--retry-intent and --failed-capture must be supplied together')
    if args.retry_intent:
        result = verify_retry(args.case, args.capture, args.retry_intent, args.failed_capture)
    else:
        result = verify(args.case, args.capture)
    print(json.dumps(result, indent=2))
