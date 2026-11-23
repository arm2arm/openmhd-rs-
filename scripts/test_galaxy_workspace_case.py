"""REANA-only metadata controls; all synthetic Cargo/runtime bytes are inert.

No compiler, application, libtest executable or numerical kernel is invoked.
The small parent fixture is explicitly nonphysical and supplies no acceptance.
"""
import base64
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('workspace_case_under_test', ROOT / 'reana/galaxy_workspace_case.py')
JOB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(JOB)


def seal(buffers):
    return JOB.encode(dict(schema='openmhd.g00-source-leaf-inputs.v1',
        files={n: dict(sha256=JOB.sha(raw), bytes=len(raw)) for n, raw in buffers.items()}))


def leaf(restart=False):
    return dict(build_profile='debug', manifest='apps/openmhd/Cargo.toml' if restart else 'crates/control/Cargo.toml',
        target_kind=['test'] if restart else ['lib'], target_name='restart' if restart else 'control',
        source='apps/openmhd/tests/restart.rs' if restart else 'crates/control/src/lib.rs',
        selector='NONPHYSICAL_CONTROL', binary='binaries/debug/inert-not-an-executable', binary_sha256='0' * 64)


def fixture():
    item = leaf()
    source = Path('/NONPHYSICAL_CONTROL/source')
    snapshot = dict(source_revision='0' * 40, source_sha256={item['manifest']: '0' * 64,
        item['source']: '0' * 64, 'reana/remote.py': '1' * 64}, upload_sha256={'remote.py': '1' * 64})
    buffers = {'workspace_case.py': (ROOT / 'reana/galaxy_workspace_case.py').read_bytes(),
        'supervisor.py': (ROOT / 'tools/m1_evidence/reana_metadata_job.py').read_bytes(),
        'launcher.py': (ROOT / 'reana/galaxy_test_case.py').read_bytes(), 'snapshot.json': JOB.encode(snapshot)}
    snapshot_hash = JOB.sha(buffers['snapshot.json'])
    buffers['parent/runtime.json'] = JOB.encode(dict(snapshot_sha256=snapshot_hash, image=JOB.IMAGE,
        rustc='rustc 1.85.1 NONPHYSICAL_CONTROL', bootstrap_sha256='1' * 64))
    argv = [['cargo', 'fmt', '--check'], ['cargo', 'clippy', '--workspace', '--all-targets', '--all-features',
        '--locked', '--', '-D', 'warnings'], ['cargo', 'build', '--release', '--workspace', '--all-features', '--locked'],
        ['python', 'reana/galaxy_preflight.py', '--source', str(source), '--snapshot', str(source.parent / 'snapshot.json'),
         '--output', str(source.parent / 'outputs/galaxy-preflight'), '--jobs', '4']]
    commands = [dict(command=a, returncode=0, log='outputs/logs/' + str(i).zfill(2) + '.log', log_sha256='2' * 64)
                for i, a in enumerate(argv)]
    buffers['parent/execution.json'] = JOB.encode(dict(snapshot_sha256=snapshot_hash, status='completed',
        study='galaxy-source-preflight', jobs=4, runtime_sha256=JOB.sha(buffers['parent/runtime.json']), commands=commands))
    binary = dict(path=item['binary'], sha256=item['binary_sha256'], selectors=[item['selector']],
        manifest=item['manifest'], source=item['source'], target=dict(kind=item['target_kind'], name=item['target_name']), build_profile='debug')
    buffers['parent/preflight.json'] = JOB.encode(dict(schema='openmhd.galaxy-rust-preflight.v1',
        status='complete', snapshot_sha256=snapshot_hash, source_revision='0' * 40, jobs=4,
        before_after_source_identical=True, component_accepted=False, test_methods_executed=0,
        binaries=[binary], compiled_binaries=1, tests=[item], resolved_leaves=1,
        source_files={n: dict(sha256=h) for n, h in snapshot['source_sha256'].items()}))
    buffers['parent/commands.json'] = JOB.encode([dict(label='NONPHYSICAL_CONTROL_ONLY')])
    artifacts = {r['log']: r['log_sha256'] for r in commands}
    artifacts.update({'outputs/' + remote: JOB.sha(buffers['parent/' + name]) for name, remote in
        (('execution.json', 'execution.json'), ('runtime.json', 'runtime.json'),
         ('preflight.json', 'galaxy-preflight/preflight.json'), ('commands.json', 'galaxy-preflight/commands.json'))})
    buffers['parent/artifacts.sha256.json'] = JOB.encode(artifacts)
    workflow, uuid = 'nonphysical-control.1', '00000000-0000-0000-0000-000000000000'
    buffers['parent/observation.json'] = JOB.encode(dict(origin='server', matches=[
        dict(workflow=workflow, id=uuid, version=1, status='finished')]))
    buffers['parent/acquisition.json'] = JOB.encode(dict(schema='openmhd.g00-source-parent-acquisition.v1', status='complete',
        workflow=workflow, uuid=uuid, snapshot_sha256=snapshot_hash, all_required_metadata_and_logs_verified=True, binary_archive_acquired=False))
    buffers['parent/review.json'] = JOB.encode(dict(status='supported', component_accepted=False,
        snapshot_sha256=snapshot_hash, uuid=uuid, errors=[], logical_catalog_matches_original676=True))
    release = dict(schema='openmhd.g00-source-leaf-release.v1', job_sha256=JOB.sha(buffers['workspace_case.py']),
        source_revision='0' * 40, compiled_source_revision='0' * 40, snapshot_sha256=snapshot_hash,
        parent_review_sha256=JOB.sha(buffers['parent/review.json']),
        prerequisites={n: '0' * 64 for n in JOB.PREREQUISITES}, component_accepted=False)
    release['prerequisites']['source_slice_output_review'] = release['parent_review_sha256']
    buffers['root-release.json'] = JOB.encode(release)
    buffers['case.json'] = JOB.encode(dict(schema='openmhd.g00-source-leaf-case.v1', leaf=item,
        resources=dict(JOB.RESOURCES), parent_workflow=workflow, parent_uuid=uuid,
        root_release_sha256=JOB.sha(buffers['root-release.json'])))
    return buffers


def command():
    return dict(outcome='success', returncode=0, cleanup=dict(writers_settled=True, direct_child_reaped=True,
        leader_held_until_group_close=True, group_authority_lost=False))


def artifact(source, item, *, test=True, name=None):
    return dict(reason='compiler-artifact', manifest_path=str(source / item['manifest']),
        target=dict(kind=item['target_kind'], name=name or item['target_name'], src_path=str(source / item['source'])),
        profile=dict(test=test), executable=str(source / 'target/debug' / (name or item['target_name'])))


def large_tool_workspace(work, mutate=False):
    """Inert sparse Cargo with the actual recorded tool's length; no ELF runs.

    The parent validator and process launcher are replaced only for this control.
    Real file reads, tool fences, stage orchestration, native witness parsing and
    the complete output publication remain production code.
    """
    buffers = fixture()
    for name, raw in buffers.items():
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    (work / 'payload.json').write_bytes(seal(buffers))
    source = work / 'source'
    source.mkdir()
    (source / 'control.rs').write_bytes(b'NONPHYSICAL_SOURCE_ONLY')
    snapshot = dict(source_sha256={'control.rs': JOB.sha((source / 'control.rs').read_bytes())})
    runtime = dict(snapshot_sha256=JOB.sha(buffers['snapshot.json']), image=JOB.IMAGE,
                   machine=os.uname().machine, rustc='rustc 1.85.1 NONPHYSICAL_CONTROL\n')
    output = work / 'outputs'
    output.mkdir()
    (output / 'runtime.json').write_bytes(JOB.encode(runtime))
    tool = work / 'runtime/rust/bin/cargo'
    tool.parent.mkdir(parents=True)
    with tool.open('wb') as stream:
        stream.truncate(35341752)
    (tool.parent / 'rustc').write_bytes(b'INERT_RUSTC_NOT_EXECUTABLE')
    binary = source / 'target/debug/control'
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b'INERT_LIBTEST_NOT_EXECUTABLE')
    item = leaf()
    listing = (item['selector'] + ': test\n').encode()
    cargo = b'\n'.join(json.dumps(row).encode() for row in (
        artifact(source, item), dict(reason='build-finished', success=True)))
    raw_leaf = ("running 1 test\ntest NONPHYSICAL_CONTROL ... ok\n\n"
                "test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n").encode()
    values = dict(compiler=runtime['rustc'].encode(), compile=cargo, list=listing,
                  **{'ignored-list': b'', 'leaf': raw_leaf})
    def stage(out, src, label, argv, supervisor, native, env, links, stages):
        stages.append(dict(label=label, argv=argv, command=command(),
                           stdout_base64=base64.b64encode(values[label]).decode(), stderr_base64=''))
        if mutate and label == 'leaf':
            with tool.open('r+b') as stream:
                stream.write(b'CHANGED_WITH_SAME_LENGTH')
        return values[label]
    with mock.patch.object(JOB, 'validate_inputs', return_value=(dict(leaf=item), snapshot, [item['selector']])), \
         mock.patch.object(JOB, 'execute_stage', side_effect=stage):
        code = JOB.run(work)
    return code, tool, JOB.parse((output / 'result.json').read_bytes()), JOB.parse((output / 'child_result.json').read_bytes())


class WorkspaceCaseMetadataTests(unittest.TestCase):
    def test_actual_size_inert_cargo_reaches_one_leaf_and_both_tool_fences(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            code, tool, result, child = large_tool_workspace(work)
            self.assertEqual(tool.stat().st_size, 35341752)
            self.assertGreater(tool.stat().st_size, JOB.MAX_BYTES)
            self.assertEqual(code, 0, result)
            self.assertEqual(result['status'], 'passed')
            self.assertEqual(result['passing_leaves'], 1)
            self.assertEqual([r['label'] for r in child['stages']], ['compiler', 'compile', 'list', 'ignored-list', 'leaf'])
            self.assertEqual(set(p.name for p in (work / 'outputs').iterdir()), set(JOB.OUTPUTS))

    def test_actual_size_inert_cargo_changed_after_leaf_is_not_passing(self):
        with tempfile.TemporaryDirectory() as temporary:
            code, tool, result, child = large_tool_workspace(Path(temporary), mutate=True)
            self.assertEqual(tool.stat().st_size, 35341752)
            self.assertEqual(code, 1)
            self.assertEqual(result['status'], 'failed')
            self.assertIn('Compiler and Cargo unchanged', result['error'])
            self.assertEqual(len(child['stages']), 5)

    def test_tool_bound_does_not_relax_metadata_or_allow_unbounded_executables(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            folder = work / 'runtime/rust/bin'
            folder.mkdir(parents=True)
            (folder / 'rustc').write_bytes(b'INERT')
            tool = folder / 'cargo'
            with tool.open('wb') as stream:
                stream.truncate(35341752)
            with self.assertRaisesRegex(ValueError, 'Bounded regular file'):
                JOB.regular(work, 'runtime/rust/bin/cargo')
            self.assertEqual(set(JOB.compiler_pins(work)), {'runtime/rust/bin/cargo', 'runtime/rust/bin/rustc'})
            with tool.open('wb') as stream:
                stream.truncate(JOB.MAX_EXECUTABLE_BYTES + 1)
            with self.assertRaisesRegex(ValueError, 'Bounded regular file'):
                JOB.compiler_pins(work)

    def test_nonphysical_parent_metadata_preserves_one_exact_leaf(self):
        buffers = fixture()
        case, snapshot, names = JOB.validate_inputs(buffers, seal(buffers))
        self.assertEqual(names, ['NONPHYSICAL_CONTROL'])
        self.assertEqual(case['leaf'], leaf())
        self.assertEqual(snapshot['source_revision'], '0' * 40)

    def test_duplicate_nonfinite_and_overflow_metadata_reject(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e400}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                JOB.parse(raw)

    def test_changed_payload_and_resealed_supervisor_reject(self):
        buffers = fixture()
        original = seal(buffers)
        buffers['workspace_case.py'] += b'\n'
        with self.assertRaisesRegex(ValueError, 'input bytes'):
            JOB.validate_inputs(buffers, original)
        buffers = fixture()
        buffers['supervisor.py'] += b'\n'
        with self.assertRaisesRegex(ValueError, 'Immutable'):
            JOB.validate_inputs(buffers, seal(buffers))

    def test_boolean_resources_and_overflowing_timeout_reject(self):
        for field, value in (('build_threads', True), ('test_threads', True), ('command_timeout_seconds', float('inf'))):
            buffers = fixture()
            case = JOB.parse(buffers['case.json'])
            case['resources'][field] = value
            if math_is_infinite(value):
                # Raw JSON exponent overflow exercises parsing before equality.
                buffers['case.json'] = json.dumps(case).replace('Infinity', '1e400').encode()
            else:
                buffers['case.json'] = JOB.encode(case)
            with self.subTest(field=field), self.assertRaises(ValueError):
                JOB.validate_inputs(buffers, seal(buffers))

    def test_parent_pending_ambiguous_and_changed_uuid_reject(self):
        for change in ('pending', 'duplicate', 'uuid'):
            buffers = fixture()
            observation = JOB.parse(buffers['parent/observation.json'])
            if change == 'duplicate':
                observation['matches'] *= 2
            elif change == 'uuid':
                observation['matches'][0]['id'] = 'f' * 36
            else:
                observation['matches'][0]['status'] = 'pending'
            buffers['parent/observation.json'] = JOB.encode(observation)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'finished parent UUID'):
                JOB.validate_inputs(buffers, seal(buffers))

    def test_parent_acquisition_scope_and_review_error_reject(self):
        for name, field, value in (('acquisition', 'binary_archive_acquired', True),
                                  ('acquisition', 'all_required_metadata_and_logs_verified', False),
                                  ('review', 'errors', ['NONPHYSICAL_REVIEW_FAILURE'])):
            buffers = fixture()
            key = 'parent/' + name + '.json'
            value_dict = JOB.parse(buffers[key])
            value_dict[field] = value
            buffers[key] = JOB.encode(value_dict)
            with self.subTest(name=name, field=field), self.assertRaises(ValueError):
                JOB.validate_inputs(buffers, seal(buffers))

    def test_wrong_selector_and_duplicate_parent_leaf_reject(self):
        for duplicate in (False, True):
            buffers = fixture()
            if duplicate:
                report = JOB.parse(buffers['parent/preflight.json'])
                report['tests'] *= 2
                report['resolved_leaves'] = 2
                buffers['parent/preflight.json'] = JOB.encode(report)
                artifacts = JOB.parse(buffers['parent/artifacts.sha256.json'])
                artifacts['outputs/galaxy-preflight/preflight.json'] = JOB.sha(buffers['parent/preflight.json'])
                buffers['parent/artifacts.sha256.json'] = JOB.encode(artifacts)
            else:
                case = JOB.parse(buffers['case.json'])
                case['leaf']['selector'] = 'A_DIFFERENT_LEAF'
                buffers['case.json'] = JOB.encode(case)
            with self.subTest(duplicate=duplicate), self.assertRaisesRegex(ValueError, 'exact original catalog leaf'):
                JOB.validate_inputs(buffers, seal(buffers))

    def test_compiler_selection_is_scalar_absolute_and_forced(self):
        argv = JOB.compiler_config(Path('/fixed/rust/bin/rustc'))
        values = argv[1::2]
        self.assertIn('build.rustc="/fixed/rust/bin/rustc"', values)
        self.assertIn('env.RUSTC.value="/fixed/rust/bin/rustc"', values)
        self.assertIn('env.RUSTC.force=true', values)
        self.assertIn('env.RUSTC_WRAPPER.value=""', values)
        self.assertFalse(any('={' in value for value in values))
        with self.assertRaisesRegex(ValueError, 'Absolute compiler'):
            JOB.compiler_config(Path('relative-rustc'))

    def test_inherited_target_wrapper_flags_and_parallelism_are_removed(self):
        with mock.patch.dict(os.environ, {'CARGO_TARGET_X_RUNNER': 'INERT_BAD_RUNNER', 'CARGO_BUILD_TARGET': 'BAD_TARGET',
            'RUSTC_WRAPPER': 'BAD_WRAPPER', 'RUSTFLAGS': 'BAD_FLAGS', 'RAYON_NUM_THREADS': '99'}):
            env = JOB.environment(Path('/fixed'))
        self.assertNotIn('CARGO_TARGET_X_RUNNER', env)
        self.assertNotIn('CARGO_BUILD_TARGET', env)
        self.assertEqual(env['RUSTC_WRAPPER'], '')
        self.assertEqual(env['RUSTFLAGS'], '')
        self.assertEqual(env['RAYON_NUM_THREADS'], '1')
        self.assertEqual(env['CARGO_BUILD_JOBS'], '4')

    def test_each_target_kind_and_profile_builds_without_running_a_method(self):
        for kind, flag in (('lib', '--lib'), ('test', '--test'), ('bin', '--bin'), ('example', '--example')):
            item = leaf()
            item.update(target_kind=[kind], build_profile='release')
            argv = JOB.build_argv(Path('/fixed'), item)
            with self.subTest(kind=kind):
                self.assertIn(flag, argv)
                self.assertIn('--no-run', argv)
                self.assertIn('--locked', argv)
                self.assertIn('--release', argv)
                self.assertEqual(argv[argv.index('--jobs') + 1], '4')
                self.assertNotIn('--workspace', argv)

    def test_cargo_duplicate_failed_and_wrong_target_artifacts_reject(self):
        source, item = Path('/fixed/source'), leaf()
        row = artifact(source, item)
        finish = dict(reason='build-finished', success=True)
        for rows in ([row, row, finish], [row, dict(reason='build-finished', success=False)],
                     [artifact(source, item, name='another'), finish]):
            # Cargo is JSON-lines, not pretty-printed JSON.
            raw = b'\n'.join(json.dumps(r).encode() for r in rows)
            with self.subTest(rows=len(rows)), self.assertRaisesRegex(ValueError, 'Unique successful'):
                JOB.select_artifacts(raw, source, item)

    def test_restart_requires_real_nontest_application_and_retains_both(self):
        source, item = Path('/fixed/source'), leaf(True)
        target = artifact(source, item)
        finish = dict(reason='build-finished', success=True)
        raw = lambda rows: b'\n'.join(json.dumps(r).encode() for r in rows)
        with self.assertRaisesRegex(ValueError, 'restart application dependency'):
            JOB.select_artifacts(raw([target, finish]), source, item)
        app_item = dict(item, target_kind=['bin'], target_name='vector-potential', source='apps/openmhd/src/bin/vector-potential.rs')
        application = artifact(source, app_item, test=False)
        selected = JOB.select_artifacts(raw([target, application, finish]), source, item)
        self.assertEqual(selected, [target, application])
        application['profile']['test'] = True
        with self.assertRaisesRegex(ValueError, 'restart application dependency'):
            JOB.select_artifacts(raw([target, application, finish]), source, item)

    def test_listing_rejects_ignored_benchmark_duplicate_or_nonplain_rows(self):
        self.assertEqual(JOB.listing(b'one: test\ntwo::three: test\n'), ['one', 'two::three'])
        self.assertEqual(JOB.listing(b''), [])
        for raw in (b'one: benchmark\n', b'one: test\none: test\n', b'one (ignored): test\n'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                JOB.listing(raw)

    def test_unknown_reaped_or_unsettled_command_never_passes(self):
        for section, field, value in (('outer', 'returncode', False), ('outer', 'outcome', 'unknown'),
                ('cleanup', 'writers_settled', False), ('cleanup', 'direct_child_reaped', False),
                ('cleanup', 'leader_held_until_group_close', False), ('cleanup', 'group_authority_lost', True)):
            row = command()
            (row if section == 'outer' else row['cleanup'])[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'command closure'):
                JOB.settled(row)

    def test_escaping_supervision_retains_pending_receipt_and_both_log_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            observed = []
            def persist(path, value):
                path.write_bytes(JOB.encode(value))
            def launch(*args):
                destination = args[4]
                observed.append(list(args[1]))
                persist(destination / 'command.json', dict(status='unknown_closure', cleanup=dict(writers_settled=None)))
                (destination / 'stdout.txt').write_bytes(b'PARTIAL_OUT')
                (destination / 'stderr.txt').write_bytes(b'PARTIAL_ERR')
                raise RuntimeError('EXACT_CONTROL_SENTINEL')
            stages = []
            with self.assertRaisesRegex(RuntimeError, '^EXACT_CONTROL_SENTINEL$'):
                JOB.execute_stage(output, output, 'control', ['INERT_NOT_EXECUTED'], None,
                    SimpleNamespace(persist=persist, launch_native=launch), {}, {}, stages)
            self.assertEqual(observed, [['INERT_NOT_EXECUTED']])
            self.assertEqual(stages[0]['command']['status'], 'unknown_closure')
            self.assertEqual(base64.b64decode(stages[0]['stdout_base64']), b'PARTIAL_OUT')
            self.assertEqual(base64.b64decode(stages[0]['stderr_base64']), b'PARTIAL_ERR')

    def test_invalid_input_retains_preparation_runtime_in_failed_eight_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            output = work / 'outputs'
            output.mkdir()
            original = b'{"NONPHYSICAL_PREPARATION_RUNTIME":true}\n'
            (output / 'runtime.json').write_bytes(original)
            (work / 'payload.json').write_bytes(b'INVALID_JSON')
            self.assertEqual(JOB.run(work), 1)
            self.assertEqual({p.name for p in output.iterdir()}, set(JOB.OUTPUTS))
            self.assertEqual(JOB.parse((output / 'result.json').read_bytes())['status'], 'failed')
            child = JOB.parse((output / 'child_result.json').read_bytes())
            self.assertEqual(base64.b64decode(child['prepared_runtime_base64']), original)
            self.assertEqual(child['stages'], [])
            artifacts = JOB.parse((output / 'artifacts.sha256.json').read_bytes())
            self.assertEqual(len(artifacts), 7)
            self.assertTrue(all(JOB.sha((work / n).read_bytes()) == h for n, h in artifacts.items()))

    def test_unexpected_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            output = work / 'outputs'
            output.mkdir()
            (output / 'runtime.json').write_bytes(b'ORIGINAL')
            (output / 'result.json').write_bytes(b'PREVIOUS_RESULT')
            with self.assertRaisesRegex(ValueError, 'Fresh prepared'):
                JOB.run(work)
            self.assertEqual((output / 'result.json').read_bytes(), b'PREVIOUS_RESULT')

    def test_symlink_hardlink_and_parent_traversal_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'original').write_bytes(b'CONTROL')
            (root / 'linked').symlink_to(root / 'original')
            with self.assertRaisesRegex(ValueError, 'Linked'):
                JOB.regular(root, 'linked')
            os.link(root / 'original', root / 'hardlink')
            with self.assertRaisesRegex(ValueError, 'regular'):
                JOB.regular(root, 'hardlink')
            with self.assertRaisesRegex(ValueError, 'relative path'):
                JOB.regular(root, '../escape')


def math_is_infinite(value):
    return type(value) is float and value == float('inf')


if __name__ == '__main__':
    unittest.main()
