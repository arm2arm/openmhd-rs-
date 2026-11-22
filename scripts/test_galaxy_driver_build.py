"""Unexecuted metadata controls; dummy bytes are NEVER Rust build evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

PROPOSAL = Path(__file__).with_name('galaxy_driver_build.py')
SOURCE = PROPOSAL if PROPOSAL.exists() else Path(__file__).resolve().parents[1] / 'reana/galaxy_driver_build.py'
SPEC = importlib.util.spec_from_file_location('driver_build_under_test', SOURCE)
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class DriverBuildMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / 'source'
        self.source.mkdir()
        self.files = {}
        for _, target, base in BUILD.TARGETS.values():
            for name in (base + '/Cargo.toml', base + '/examples/' + target + '.rs'):
                path = self.source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'SCHEMA_ONLY_NOT_RUST_SOURCE\n')
                self.files[name] = {'sha256': BUILD.sha(path.read_bytes()), 'bytes': path.stat().st_size}
        self.binary = self.source / 'target/release/examples/gravity-force-case'
        self.binary.parent.mkdir(parents=True)
        self.binary.write_bytes(b'SCHEMA_ONLY_NOT_AN_EXECUTABLE')
        self.row = {
            'reason': 'compiler-artifact', 'package_id': 'SCHEMA_ONLY_OPAQUE_PACKAGE_ID',
            'manifest_path': str(self.source / 'crates/gravity/Cargo.toml'),
            'target': {'name': 'gravity-force-case', 'kind': ['example'], 'crate_types': ['bin'],
                       'test': False, 'src_path': str(self.source / 'crates/gravity/examples/gravity-force-case.rs')},
            'profile': {'test': False, 'opt_level': '3'}, 'features': [],
            'executable': str(self.binary),
        }

    def log(self, row=None, finish=None):
        return (json.dumps(self.row if row is None else row) + '\n'
                + json.dumps({'reason': 'build-finished', 'success': True} if finish is None else finish)
                + '\n').encode()

    def metadata(self, raw=None):
        return BUILD.artifact_metadata(self.log() if raw is None else raw,
                                       self.source, 'gravity', self.files)

    def test_exact_explicit_release_example_commands(self):
        for kind, (package, target, _) in BUILD.TARGETS.items():
            self.assertEqual(BUILD.build_argv('/cargo', kind, 4), ['/cargo', 'build', '--release',
                '--package', package, '--example', target, '--all-features', '--locked',
                '--message-format=json', '--jobs', '4',
                '--config', 'build.rustc="/rustc"', '--config', 'build.rustc-wrapper=""',
                '--config', 'build.rustc-workspace-wrapper=""',
                '--config', 'env.RUSTC={value="/rustc",force=true,relative=false}',
                '--config', 'env.RUSTC_WRAPPER={value="",force=true,relative=false}',
                '--config', 'env.RUSTC_WORKSPACE_WRAPPER={value="",force=true,relative=false}',
                '--config', 'env.CARGO_BUILD_RUSTC={value="/rustc",force=true,relative=false}',
                '--config', 'env.CARGO_BUILD_RUSTC_WRAPPER={value="",force=true,relative=false}',
                '--config', 'env.CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER={value="",force=true,relative=false}'])

    def test_build_jobs_and_target_are_strict(self):
        for kind, jobs in [('gravity', True), ('gravity', 1), ('gravity', 4.0), ('unknown', 4)]:
            with self.assertRaisesRegex(ValueError, 'Explicit driver'):
                BUILD.build_argv('/cargo', kind, jobs)

    def test_valid_schema_only_cargo_artifact_is_metadata_not_execution(self):
        actual = self.metadata()
        self.assertEqual(actual['original_binary'], 'target/release/examples/gravity-force-case')
        self.assertEqual(actual['source'], 'crates/gravity/examples/gravity-force-case.rs')
        self.assertEqual(actual['profile'], {'test': False, 'opt_level': '3'})

    def test_libtest_profile_is_rejected(self):
        for value in (True, 0, None):
            row = copy.deepcopy(self.row)
            row['profile']['test'] = value
            with self.assertRaisesRegex(ValueError, 'non-libtest'):
                self.metadata(self.log(row))

    def test_target_test_policy_and_kind_are_exact(self):
        for key, value in [('test', True), ('crate_types', ['lib']), ('kind', ['example', 'bin']),
                           ('name', 'other-example')]:
            row = copy.deepcopy(self.row)
            row['target'][key] = value
            with self.assertRaisesRegex(ValueError, 'Exact standalone example'):
                self.metadata(self.log(row))

    def test_nonrelease_artifact_is_rejected(self):
        row = copy.deepcopy(self.row)
        row['profile']['opt_level'] = '0'
        with self.assertRaisesRegex(ValueError, 'Release non-libtest'):
            self.metadata(self.log(row))

    def test_numeric_cargo_success_is_not_boolean(self):
        with self.assertRaisesRegex(ValueError, 'completion boolean'):
            self.metadata(self.log(finish={'reason': 'build-finished', 'success': 1}))

    def test_missing_failed_duplicate_completions_are_rejected(self):
        for raw in (json.dumps(self.row).encode(), self.log(finish={'reason': 'build-finished', 'success': False}),
                    self.log() + b'{"reason":"build-finished","success":true}\n'):
            with self.assertRaisesRegex(ValueError, 'Unique successful Cargo'):
                self.metadata(raw)

    def test_duplicate_matching_artifacts_are_rejected(self):
        raw = json.dumps(self.row).encode() + b'\n' + self.log()
        with self.assertRaisesRegex(ValueError, 'Unique successful Cargo'):
            self.metadata(raw)

    def test_manifest_and_source_must_be_exact_snapshot_paths(self):
        for field in ('manifest_path', 'src_path'):
            row = copy.deepcopy(self.row)
            if field == 'src_path':
                row['target'][field] += '.changed'
            else:
                row[field] += '.changed'
            with self.assertRaisesRegex(ValueError, 'Exact Cargo source/manifest'):
                self.metadata(self.log(row))

    def test_snapshot_membership_is_required(self):
        del self.files['crates/gravity/examples/gravity-force-case.rs']
        with self.assertRaisesRegex(ValueError, 'original snapshot'):
            self.metadata()

    def test_binary_path_must_be_unaliased_release_example(self):
        for path in (self.source / 'target/debug/examples/gravity-force-case',
                     self.root / 'outside/gravity-force-case',
                     self.binary.parent / 'other-name'):
            row = copy.deepcopy(self.row)
            row['executable'] = str(path)
            with self.assertRaisesRegex(ValueError, 'Canonical example executable'):
                self.metadata(self.log(row))

    def test_linked_binary_is_rejected(self):
        target = self.root / 'unrelated'
        target.write_bytes(b'NOT_AN_EXECUTABLE')
        self.binary.unlink()
        self.binary.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'Canonical example executable'):
            self.metadata()

    def test_source_receipts_check_both_examples_and_exact_bytes(self):
        snapshot = {'source_sha256': {name: row['sha256'] for name, row in self.files.items()}}
        self.assertEqual(BUILD.source_receipts(self.source, snapshot), self.files)
        name = 'crates/gravity/examples/gravity-force-case.rs'
        (self.source / name).write_bytes(b'CHANGED_SCHEMA_ONLY_BYTES')
        with self.assertRaisesRegex(ValueError, 'Changed/excessive source'):
            BUILD.source_receipts(self.source, snapshot)

    def test_regular_read_rejects_links_and_bounds(self):
        with self.assertRaisesRegex(ValueError, 'Regular bounded'):
            BUILD.regular(self.source, self.binary.relative_to(self.source).as_posix(), 1)
        linked = self.source / 'linked'
        linked.symlink_to(self.binary)
        with self.assertRaisesRegex(ValueError, 'Linked path'):
            BUILD.regular(self.source, 'linked')

    def test_opaque_binary_parts_reassemble_exact_original_bytes(self):
        raw = b'SCHEMA_ONLY_NOT_RUST\n' + b'x' * BUILD.PART_BYTES
        self.binary.write_bytes(raw)
        output = self.root / 'output'
        output.mkdir()
        exported = BUILD.export_binary(self.source, self.metadata(), output)
        blocks = [(output / row['path']).read_bytes() for row in exported['parts']]
        self.assertEqual(b''.join(blocks), raw)
        self.assertEqual(len(blocks), 2)
        self.assertTrue(all(0 < len(block) <= BUILD.PART_BYTES for block in blocks))
        self.assertEqual(exported['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual((output / exported['path']).read_bytes(), raw)

    def test_export_collision_preserves_first_bytes(self):
        output = self.root / 'output'
        output.mkdir()
        record = self.metadata()
        exported = BUILD.export_binary(self.source, record, output)
        original = (output / exported['path']).read_bytes()
        with self.assertRaises(FileExistsError):
            BUILD.export_binary(self.source, record, output)
        self.assertEqual((output / exported['path']).read_bytes(), original)

    def test_duplicate_json_and_unsafe_paths_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Repeated JSON key'):
            BUILD.parse(b'{"a":1,"a":2}')
        for name in ('../escape', '/absolute', 'a//b', '', './a'):
            with self.assertRaises(ValueError):
                BUILD.relative(name)

    def test_existing_destination_rejects_before_any_launch(self):
        output = self.root / 'existing'
        output.mkdir()
        marker = output / 'original'
        marker.write_bytes(b'PRESERVE')
        with self.assertRaisesRegex(ValueError, 'Fresh output'):
            BUILD.run(self.source, self.root / 'absent-snapshot', self.root / 'absent-release', output)
        self.assertEqual(marker.read_bytes(), b'PRESERVE')
        self.assertEqual(list(output.iterdir()), [marker])

    def test_final_export_fence_detects_later_original_binary_change(self):
        output = self.root / 'output'
        output.mkdir()
        exported = BUILD.export_binary(self.source, self.metadata(), output)
        BUILD.verify_export(self.source, output, exported)
        self.binary.write_bytes(b'CHANGED_AFTER_LATER_BUILD')
        with self.assertRaisesRegex(ValueError, 'Original binary changed'):
            BUILD.verify_export(self.source, output, exported)

    def test_final_export_fence_detects_changed_part_with_unchanged_binaries(self):
        output = self.root / 'output'
        output.mkdir()
        exported = BUILD.export_binary(self.source, self.metadata(), output)
        BUILD.verify_export(self.source, output, exported)
        part = output / exported['parts'][0]['path']
        part.write_bytes(b'CHANGED_PART_ONLY')
        with self.assertRaisesRegex(ValueError, 'Exported part changed'):
            BUILD.verify_export(self.source, output, exported)

    def helpers(self):
        # Future canonical REANA method only; imports no scientific candidate.
        repo = Path(__file__).resolve().parents[1]
        native = BUILD.load_pinned(repo, BUILD.NATIVE_PATH, BUILD.NATIVE_SHA, 'driver_control_native')
        supervisor = BUILD.load_pinned(repo, BUILD.SUPERVISOR_PATH, BUILD.SUPERVISOR_SHA,
                                       'driver_control_supervisor')
        return native, supervisor

    def command_row(self, argv, seconds, links):
        # NONPHYSICAL partial metadata only, never a completed Rust/workflow packet.
        return dict(schema='openmhd.metadata-command.v1', command=list(argv), cwd=str(self.source),
            started_utc='2026-01-01T00:00:00+00:00', finished_utc='2026-01-01T00:00:01+00:00',
            duration_seconds=1, outcome='success', returncode=0, error_type=None, pid=7, process_group=7,
            timeout_seconds=seconds, timeout_scope='direct-child-wait', links=copy.deepcopy(links),
            external_terminal_evidence_required=False,
            NONPHYSICAL_partial_metadata_control=True,
            cleanup=dict(writers_settled=True, direct_child_reaped=True,
                         leader_held_until_group_close=True, group_authority_lost=False,
                         remaining_live_pids=[], leader_identity=dict(pid=7, process_group=7,
                                                                    session=7, starttime='123')))

    def command_fixture(self):
        native, supervisor = self.helpers()
        output = self.root / 'partial-command-control'
        output.mkdir()
        links = {'runtime': BUILD.sha(b'NONPHYSICAL initial runtime')}
        commands = [('compiler', ['/SCHEMA_ONLY/rustc', '-Vv'], 60)] + [
            (kind, BUILD.build_argv('/SCHEMA_ONLY/cargo', kind, 4), 1800) for kind in BUILD.TARGETS]
        receipts = []
        for label, argv, seconds in commands:
            destination = output / label
            destination.mkdir()
            native.persist(destination / 'command.json', self.command_row(argv, seconds, links))
            (destination / 'stdout.txt').write_bytes(('NONPHYSICAL ' + label + ' stdout').encode())
            (destination / 'stderr.txt').write_bytes(('NONPHYSICAL ' + label + ' stderr').encode())
            receipts.append(BUILD.command_receipt(output, label, argv, self.source, seconds, links, supervisor))
        records = [dict(kind=r['label'], build_receipt=copy.deepcopy(r),
                       build_command_sha256=r['command']['sha256'], cargo_stdout_sha256=r['stdout']['sha256'],
                       cargo_stderr_sha256=r['stderr']['sha256']) for r in receipts[1:]]
        report = dict(command_labels=['compiler', 'geometry', 'gravity'],
                      command_receipts=copy.deepcopy(receipts), binaries=records,
                      NONPHYSICAL_partial_metadata_control=True)
        # No source/runtime/build/export/binary packet is supplied to run or accepted.
        return output, commands, links, supervisor, report, receipts, native

    def generation_fixture(self):
        native, _ = self.helpers()
        snapshot = {'source_sha256': {name: row['sha256'] for name, row in self.files.items()}}
        snapshot_path, release_path = self.root / 'snapshot.json', self.root / 'release.json'
        snapshot_raw, release_raw = BUILD.encode(snapshot), b'NONPHYSICAL generation-fence release only'
        snapshot_path.write_bytes(snapshot_raw)
        release_path.write_bytes(release_raw)
        (self.root / 'outputs').mkdir()
        prepared = b'NONPHYSICAL prepared runtime'
        (self.root / 'outputs/runtime.json').write_bytes(prepared)
        compiler_files = {}
        for name in ('cargo', 'rustc'):
            path = self.root / 'runtime/rust/bin' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'NONPHYSICAL NOT EXECUTABLE ' + name.encode())
            compiler_files[name] = BUILD.descriptor(path.read_bytes())
        output = self.root / 'partial-runtime-control'
        output.mkdir()
        observation = b'NONPHYSICAL initial output runtime'
        (output / 'runtime.json').write_bytes(observation)
        args = (self.source, snapshot_path, snapshot_raw, release_path, release_raw, self.root,
                prepared, snapshot, self.files, compiler_files, output, observation)
        return args, native

    def prelaunch_fixture(self):
        native, supervisor = self.helpers()
        repo = Path(__file__).resolve().parents[1]
        for name, raw in ((BUILD.JOB_PATH, Path(BUILD.__file__).read_bytes()),
            (BUILD.NATIVE_PATH, (repo / BUILD.NATIVE_PATH).read_bytes()),
            (BUILD.SUPERVISOR_PATH, (repo / BUILD.SUPERVISOR_PATH).read_bytes()),
            ('reana/remote.py', b'NONPHYSICAL remote source, never executed')):
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            self.files[name] = BUILD.descriptor(raw)
        snapshot = dict(source_revision='a' * 40,
            source_sha256={n: row['sha256'] for n, row in self.files.items()},
            upload_sha256={'remote.py': self.files['reana/remote.py']['sha256']})
        release = dict(schema='openmhd.galaxy-driver-build-release.v1', source_revision='a' * 40,
            source_sha256=snapshot['source_sha256'], preflight_review_sha256='b' * 64,
            coordinator_release_sha256='c' * 64)
        snapshot_path, release_path = self.root / 'snapshot.json', self.root / 'release.json'
        snapshot_raw = BUILD.encode(snapshot)
        snapshot_path.write_bytes(snapshot_raw)
        release_path.write_bytes(BUILD.encode(release))
        version = 'rustc 1.85.1 NONPHYSICAL partial probe control\n'
        prepared = dict(snapshot_sha256=BUILD.sha(snapshot_raw), bootstrap_file='remote.py',
            bootstrap_sha256=snapshot['upload_sha256']['remote.py'], rustc=version)
        (self.root / 'outputs').mkdir()
        (self.root / 'outputs/runtime.json').write_bytes(BUILD.encode(prepared))
        for name in ('cargo', 'rustc'):
            path = self.root / 'runtime/rust/bin' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'NONPHYSICAL NOT EXECUTABLE ' + name.encode())
        # No real runtime/compiler result is claimed; the only returned command
        # below is a labelled partial compiler schema, before a sentinel Cargo stop.
        return native, supervisor, snapshot_path, release_path, version

    def test_conflicting_compiler_environment_is_pinned_before_cargo_launch(self):
        native, real_supervisor, snapshot_path, release_path, version = self.prelaunch_fixture()
        sentinel, seen = RuntimeError('NONPHYSICAL stop before Cargo process'), []
        def supervise(argv, cwd, environment, stdout, stderr, timeout):
            seen.append((list(argv), dict(environment), timeout))
            if len(seen) == 1:
                stdout.write(version.encode())
                return self.command_row(argv, timeout, {})
            raise sentinel
        supervisor = SimpleNamespace(supervise=supervise, interval=real_supervisor.interval,
            runtime_record=lambda *_: dict(schema='NONPHYSICAL partial prelaunch observation'))
        def load(_source, path, _expected, _name):
            return native if path == BUILD.NATIVE_PATH else supervisor
        conflicting = {key: 'NONPHYSICAL_UNWANTED_SELECTION' for key in BUILD.COMPILER_KEYS}
        output = self.root / 'prelaunch-output'
        with mock.patch.dict(BUILD.os.environ, conflicting), \
             mock.patch.object(BUILD, 'load_pinned', side_effect=load):
            with self.assertRaises(RuntimeError) as caught:
                BUILD.run(self.source, snapshot_path, release_path, output)
        self.assertIs(caught.exception, sentinel)
        self.assertEqual(len(seen), 2)
        rustc, cargo = self.root / 'runtime/rust/bin/rustc', self.root / 'runtime/rust/bin/cargo'
        self.assertEqual(seen[0][0], [str(rustc), '-Vv'])
        self.assertEqual(seen[1][0][:13], [str(cargo), 'build', '--release', '--package', 'moving-mesh',
            '--example', 'geometry3-case', '--all-features', '--locked', '--message-format=json', '--jobs', '4', '--config'])
        for _, environment, _ in seen:
            self.assertEqual(environment['RUSTC'], str(rustc))
            self.assertEqual(environment['CARGO_BUILD_RUSTC'], str(rustc))
            self.assertTrue(all(environment[k] == '' for k in BUILD.COMPILER_KEYS
                                if k not in ('RUSTC', 'CARGO_BUILD_RUSTC')))
            self.assertEqual(environment['CARGO_HOME'], str(self.root / 'runtime/cargo'))
        self.assertIn('build.rustc=' + json.dumps(str(rustc)), seen[1][0])
        self.assertIn('env.RUSTC_WORKSPACE_WRAPPER={value="",force=true,relative=false}', seen[1][0])
        observation = BUILD.parse((output / 'runtime.json').read_bytes())
        self.assertEqual(set(observation['compiler_selection']['environment']), set(BUILD.COMPILER_KEYS))
        self.assertNotIn('NONPHYSICAL_UNWANTED_SELECTION', (output / 'runtime.json').read_text())
        self.assertIs(observation['compiler_selection']['inherited_override_values_retained'], False)
        command = BUILD.parse((output / 'geometry/command.json').read_bytes())
        self.assertEqual(command['status'], 'unknown_closure')
        self.assertEqual(command['command'], seen[1][0])
        self.assertTrue(command['external_terminal_evidence_required'])
        report = BUILD.parse((output / 'build.json').read_bytes())
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['command_labels'], ['compiler'])
        self.assertEqual(report['binaries'], [])
        self.assertFalse((output / 'export.json').exists())

    def test_settled_command_generation_fence_precedes_artifact_attribution(self):
        native, real_supervisor, snapshot_path, release_path, version = self.prelaunch_fixture()
        seen = []
        def supervise(argv, cwd, environment, stdout, stderr, timeout):
            seen.append(list(argv))
            stdout.write(version.encode())
            (self.source / 'crates/gravity/examples/gravity-force-case.rs').write_bytes(b'NONPHYSICAL changed source')
            return self.command_row(argv, timeout, {})
        supervisor = SimpleNamespace(supervise=supervise, interval=real_supervisor.interval,
            runtime_record=lambda *_: dict(schema='NONPHYSICAL partial prelaunch observation'))
        def load(_source, path, _expected, _name):
            return native if path == BUILD.NATIVE_PATH else supervisor
        output = self.root / 'fence-output'
        with mock.patch.object(BUILD, 'load_pinned', side_effect=load):
            with self.assertRaisesRegex(ValueError, 'Changed/excessive source inventory'):
                BUILD.run(self.source, snapshot_path, release_path, output)
        self.assertEqual(len(seen), 1)
        report = BUILD.parse((output / 'build.json').read_bytes())
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['command_labels'], [])
        self.assertEqual(report['binaries'], [])
        self.assertFalse((output / 'geometry').exists())

    def test_late_runtime_cannot_be_resealed_against_initial_observation(self):
        args, native = self.generation_fixture()
        BUILD.generation_fence(*args)
        output = args[-2]
        (output / 'runtime.json').write_bytes(b'NONPHYSICAL changed output runtime')
        BUILD.close_output(output, native)
        self.assertEqual(BUILD.parse((output / 'files.sha256.json').read_bytes())['runtime.json'],
                         BUILD.descriptor((output / 'runtime.json').read_bytes()))
        with self.assertRaisesRegex(ValueError, 'Initial build runtime changed'):
            BUILD.generation_fence(*args)

    def test_late_prior_command_cannot_be_resealed_against_settled_receipt(self):
        output, commands, links, supervisor, report, receipts, native = self.command_fixture()
        BUILD.verify_command_links(self.source, output, commands, links, supervisor, report, receipts)
        path = output / 'compiler/command.json'
        changed = BUILD.parse(path.read_bytes())
        changed['NONPHYSICAL_late_unrelated_field'] = 'changed'
        native.persist(path, changed)
        BUILD.close_output(output, native)
        with self.assertRaisesRegex(ValueError, 'Settled command/stdout/stderr identities changed'):
            BUILD.verify_command_links(self.source, output, commands, links, supervisor, report, receipts)

    def test_late_stdout_and_stderr_cannot_be_resealed_against_settled_receipts(self):
        output, commands, links, supervisor, report, receipts, native = self.command_fixture()
        BUILD.verify_command_links(self.source, output, commands, links, supervisor, report, receipts)
        for label in ('compiler', 'geometry', 'gravity'):
            for channel in ('stdout.txt', 'stderr.txt'):
                with self.subTest(label=label, channel=channel):
                    path = output / label / channel
                    original = path.read_bytes()
                    path.write_bytes(original + b'NONPHYSICAL late change')
                    BUILD.close_output(output, native)
                    with self.assertRaisesRegex(ValueError, 'Settled command/stdout/stderr identities changed'):
                        BUILD.verify_command_links(self.source, output, commands, links, supervisor, report, receipts)
                    path.write_bytes(original)
                    BUILD.verify_command_links(self.source, output, commands, links, supervisor, report, receipts)

    def test_exact_three_command_coverage_and_literal_writer_fields_are_required(self):
        output, commands, links, supervisor, report, receipts, native = self.command_fixture()
        BUILD.verify_command_links(self.source, output, commands, links, supervisor, report, receipts)
        for field in ('command_labels', 'command_receipts'):
            changed = copy.deepcopy(report)
            changed[field].pop()
            with self.assertRaisesRegex(ValueError, 'Exact compiler/geometry/gravity'):
                BUILD.verify_command_links(self.source, output, commands, links, supervisor, changed, receipts)
        path = output / 'geometry/command.json'
        original = path.read_bytes()
        for field, value in (('writers_settled', 1), ('direct_child_reaped', False),
                             ('leader_held_until_group_close', False), ('group_authority_lost', True),
                             ('remaining_live_pids', [7])):
            changed = BUILD.parse(original)
            changed['cleanup'][field] = value
            native.persist(path, changed)
            with self.assertRaisesRegex(ValueError, 'Successful supervised build and closed writers'):
                BUILD.verify_command_links(self.source, output, commands, links, supervisor, report, receipts)
        for field, value in (('command', ['NONPHYSICAL wrong argv']), ('cwd', 'relative'),
                             ('timeout_seconds', True), ('links', {})):
            changed = BUILD.parse(original)
            changed[field] = value
            native.persist(path, changed)
            with self.assertRaisesRegex(ValueError, 'Exact settled build argv/cwd/timeout/links'):
                BUILD.verify_command_links(self.source, output, commands, links, supervisor, report, receipts)
        path.write_bytes(original)
        BUILD.verify_command_links(self.source, output, commands, links, supervisor, report, receipts)

    def test_both_exports_bind_final_actual_cargo_command_and_stream_receipts(self):
        output, commands, links, supervisor, report, receipts, _ = self.command_fixture()
        BUILD.verify_command_links(self.source, output, commands, links, supervisor, report, receipts)
        for index in (0, 1):
            for field in ('build_command_sha256', 'cargo_stdout_sha256', 'cargo_stderr_sha256', 'build_receipt'):
                changed = copy.deepcopy(report)
                changed['binaries'][index][field] = {} if field == 'build_receipt' else '0' * 64
                with self.assertRaisesRegex(ValueError, 'Export record contradicts final actual Cargo'):
                    BUILD.verify_command_links(self.source, output, commands, links, supervisor, changed, receipts)

    def test_closure_publication_failure_retains_exact_sentinel_and_failed_state(self):
        native, _ = self.helpers()
        output = self.root / 'partial-publication-control'
        output.mkdir()
        # Only the internal publication phase: no full source, commands, binary,
        # valid runtime or passing Rust/workflow packet is fabricated.
        report = dict(schema='NONPHYSICAL partial publication phase', status='complete',
            binaries=[], component_accepted=False, test_methods_executed=0, numerical_cases_executed=0)
        sentinel, seen, original_close = RuntimeError('NONPHYSICAL closure publication sentinel'), [], BUILD.close_output
        def fail_after_close(path, helper):
            seen.append(path)
            original_close(path, helper)
            if len(seen) == 1:
                raise sentinel
        with mock.patch.object(BUILD, 'close_output', side_effect=fail_after_close):
            with self.assertRaises(RuntimeError) as caught:
                BUILD.publish_complete(output, report, native)
        self.assertIs(caught.exception, sentinel)
        self.assertEqual(len(seen), 2)
        failed = BUILD.parse((output / 'build.json').read_bytes())
        self.assertEqual((failed['status'], failed['error_type']), ('failed', 'RuntimeError'))
        self.assertIs(failed['component_accepted'], False)
        self.assertIs(failed['external_terminal_evidence_required'], True)
        self.assertFalse((output / 'export.json').exists())
        self.assertTrue((output / 'export.failed.json').is_file())
        self.assertTrue((output / 'files.failed.sha256.json').is_file())
        self.assertEqual(BUILD.parse((output / 'files.sha256.json').read_bytes()), BUILD.output_inventory(output))
