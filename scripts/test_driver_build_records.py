"""Written, UNEXECUTED metadata controls; no complete synthetic build packet.

Each positive is a labelled nonphysical fragment of a record interface. No
fixture is an executable, a real workflow, a compiler observation, or proof of
build success. Import/tests must execute only on REANA after source review.
"""
import copy
import importlib.util
import json
from pathlib import Path
import unittest


LOCAL = Path(__file__).with_name('driver_build_records.py')
SOURCE = LOCAL if LOCAL.exists() else Path(__file__).resolve().parents[1] / 'tools/galaxy_evidence/driver_build_records.py'
SPEC = importlib.util.spec_from_file_location('build_record_controls', SOURCE)
RECORDS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECORDS)


def raw(value):
    return (json.dumps(value, allow_nan=False) + '\n').encode()


class DriverBuildRecordTests(unittest.TestCase):
    def command(self):
        argv, seconds = RECORDS.argv_for('compiler', '/NONPHYSICAL/source')
        return {'schema': 'openmhd.metadata-command.v1', 'outcome': 'success', 'returncode': 0,
            'error_type': None, 'external_terminal_evidence_required': False, 'command': argv,
            'cwd': '/NONPHYSICAL/source', 'timeout_seconds': seconds, 'timeout_scope': 'direct-child-wait',
            'links': {'NONPHYSICAL_FRAGMENT': 'NOT_A_DIGEST_ATTESTATION'},
            'pid': 123, 'process_group': 123,
            'started_utc': '2026-11-22T00:00:00+00:00', 'finished_utc': '2026-11-22T00:00:01+00:00',
            'duration_seconds': 1.0,
            'cleanup': {'writers_settled': True, 'direct_child_reaped': True,
                'leader_held_until_group_close': True, 'group_authority_lost': False, 'remaining_live_pids': [],
                'leader_identity': {'pid': 123, 'process_group': 123, 'session': 123, 'starttime': '12345'}}}

    def check_command(self, value):
        return RECORDS.command_record(raw(value), 'compiler', '/NONPHYSICAL/source', self.command()['links'])

    def cargo(self):
        return {'reason': 'compiler-artifact', 'package_id': 'NONPHYSICAL_FRAGMENT',
            'features': [], 'manifest_path': '/NONPHYSICAL/source/crates/gravity/Cargo.toml',
            'target': {'kind': ['example'], 'crate_types': ['bin'], 'name': 'gravity-force-case',
                'test': False, 'src_path': '/NONPHYSICAL/source/crates/gravity/examples/gravity-force-case.rs'},
            'profile': {'test': False, 'opt_level': '3'},
            'executable': '/NONPHYSICAL/source/target/release/examples/gravity-force-case'}

    def check_cargo(self, row=None, ending=None):
        return RECORDS.cargo_record(raw(self.cargo() if row is None else row)
            + raw({'reason': 'build-finished', 'success': True} if ending is None else ending),
            'gravity', '/NONPHYSICAL/source')

    def parts(self):
        body = b'NONPHYSICAL_OPAQUE_BYTES_NOT_AN_EXECUTABLE'
        name = 'parts/gravity.part0000'
        return {'kind': 'gravity', 'path': 'binaries/gravity-force-case', **RECORDS.descriptor(body),
                'parts': [{'path': name, **RECORDS.descriptor(body)}]}, {RECORDS.PREFIX + name: body}

    def test_duplicate_and_nonfinite_json_rejected(self):
        finite = RECORDS.parse(b'{"integer":1,"fraction":1.25,"exponent":1e2,"nested":[-2.5e-1]}')
        self.assertEqual(finite, {'integer': 1, 'fraction': 1.25, 'exponent': 100.0, 'nested': [-0.25]})
        self.assertIs(type(finite['integer']), int)
        for value in (finite['fraction'], finite['exponent'], finite['nested'][0]):
            self.assertIs(type(value), float)
        for value in (b'{"key":1,"key":2}', b'{"key":NaN}', b'{"key":Infinity}', b'{"key":-Infinity}',
                      b'1e400', b'-1e400', b'{"uninspected":1e400}',
                      b'{"outer":[{"uninspected":-1e400}]}'):
            with self.assertRaises(ValueError):
                RECORDS.parse(value)
        # A labelled partial command is valid before adding an otherwise
        # uninspected member; this is not a complete build/workflow fixture.
        command = self.command()
        self.assertEqual(self.check_command(command), command)
        for spelling in (b'1e400', b'-1e400'):
            uninspected = raw(command).rstrip()[:-1] + b',"uninspected":' + spelling + b'}'
            with self.assertRaisesRegex(ValueError, 'Nonfinite JSON'):
                RECORDS.command_record(uninspected, 'compiler', '/NONPHYSICAL/source', command['links'])

    def test_json_requires_bounded_bytes(self):
        for value in ('{}', bytearray(b'{}'), b' ' * (RECORDS.MAX_METADATA + 1)):
            with self.assertRaisesRegex(ValueError, 'Bounded JSON bytes'):
                RECORDS.parse(value)

    def test_json_structural_equality_preserves_numeric_types(self):
        self.assertTrue(RECORDS.same({'a': [False, 0]}, {'a': [False, 0]}))
        self.assertFalse(RECORDS.same({'a': False}, {'a': 0}))
        self.assertFalse(RECORDS.same({'a': 1}, {'a': 1.0}))

    def test_descriptor_rejects_boolean_and_out_of_range_sizes(self):
        for size in (True, False, -1, 1.0, RECORDS.MAX_BINARY + 1):
            with self.assertRaisesRegex(ValueError, 'integer byte count'):
                RECORDS.described({'sha256': 'a' * 64, 'bytes': size})
        self.assertEqual(RECORDS.described(RECORDS.descriptor(b'fragment')), RECORDS.descriptor(b'fragment'))

    def test_descriptor_keys_and_digests_exact(self):
        for value in ({'sha256': 'A' * 64, 'bytes': 1}, {'sha256': 'a' * 63, 'bytes': 1},
                      {'sha256': 'a' * 64, 'bytes': 1, 'extra': 1}):
            with self.assertRaises(ValueError):
                RECORDS.described(value)

    def test_relative_and_absolute_path_grammars(self):
        for name in ('', '../x', '/absolute', 'a/../x', 'a//x', './x'):
            with self.assertRaises(ValueError):
                RECORDS.relative(name)
        for name in ('relative', '//server/x', '/a/../x', '/a//x'):
            with self.assertRaises(ValueError):
                RECORDS.absolute(name)
        self.assertEqual(RECORDS.relative('parts/gravity.part0000'), 'parts/gravity.part0000')

    def test_pinned_compiler_policy_contains_all_six_forced_values(self):
        value = RECORDS.compiler_policy('/NONPHYSICAL/runtime/rust/bin/rustc')
        self.assertEqual(set(value['environment']), set(RECORDS.COMPILER_KEYS))
        self.assertFalse(value['inherited_override_values_retained'])
        self.assertEqual(value['environment']['RUSTC'], '/NONPHYSICAL/runtime/rust/bin/rustc')
        self.assertEqual(value['environment']['CARGO_BUILD_RUSTC'], value['environment']['RUSTC'])
        for key in RECORDS.COMPILER_KEYS:
            self.assertIn('env.' + key + '.value=' + json.dumps(value['environment'][key]),
                          value['cargo_config_argv'])
            self.assertIn('env.' + key + '.force=true', value['cargo_config_argv'])
            self.assertIn('env.' + key + '.relative=false', value['cargo_config_argv'])

    def test_three_exact_commands_and_timeouts(self):
        self.assertEqual(RECORDS.argv_for('compiler', '/NONPHYSICAL/source'),
                         (['/NONPHYSICAL/runtime/rust/bin/rustc', '-Vv'], 60))
        for kind, package, target in (('geometry', 'moving-mesh', 'geometry3-case'),
                                      ('gravity', 'gravity', 'gravity-force-case')):
            argv, seconds = RECORDS.argv_for(kind, '/NONPHYSICAL/source')
            self.assertEqual(seconds, 1800)
            self.assertEqual(argv[:13], ['/NONPHYSICAL/runtime/rust/bin/cargo', 'build', '--release',
                '--package', package, '--example', target, '--all-features', '--locked',
                '--message-format=json', '--jobs', '4', '--config'])
            self.assertEqual(argv[12:], RECORDS.compiler_policy('/NONPHYSICAL/runtime/rust/bin/rustc')['cargo_config_argv'])

    def test_closed_command_fragment_supported_without_build_claim(self):
        row = self.command()
        self.assertEqual(self.check_command(row), row)

    def test_command_nonzero_and_unknown_outcomes_rejected(self):
        for key, value in (('outcome', 'unknown'), ('returncode', 1), ('returncode', False),
                           ('error_type', 'Failure'), ('external_terminal_evidence_required', True)):
            row = self.command()
            row[key] = value
            with self.assertRaisesRegex(ValueError, 'Successful native command'):
                self.check_command(row)

    def test_command_invocation_and_receipt_links_exact(self):
        for key, value in (('command', ['/other', '-Vv']), ('cwd', '/OTHER/source'),
                           ('timeout_seconds', True), ('timeout_scope', 'total-job'), ('links', {})):
            row = self.command()
            row[key] = value
            with self.assertRaisesRegex(ValueError, 'invocation and links'):
                self.check_command(row)

    def test_writer_cleanup_requires_literal_flags_and_empty_live_set(self):
        for key, value in (('writers_settled', 1), ('direct_child_reaped', False),
                           ('leader_held_until_group_close', None), ('group_authority_lost', 0),
                           ('remaining_live_pids', [5])):
            row = self.command()
            row['cleanup'][key] = value
            with self.assertRaisesRegex(ValueError, 'Settled original command writers'):
                self.check_command(row)

    def test_private_leader_pid_pgid_sid_and_starttime_join(self):
        for key, value in (('pid', True), ('process_group', 321), ('session', 321), ('starttime', 'not-a-clock')):
            row = self.command()
            row['cleanup']['leader_identity'][key] = value
            with self.assertRaisesRegex(ValueError, 'private leader/session'):
                self.check_command(row)

    def test_command_time_order_utc_and_duration_rejected(self):
        for key, value in (('finished_utc', '2026-11-21T00:00:00+00:00'),
                           ('started_utc', '2026-11-22T00:00:00'), ('duration_seconds', True),
                           ('duration_seconds', -1)):
            row = self.command()
            row[key] = value
            with self.assertRaises(ValueError):
                self.check_command(row)

    def test_command_receipt_binds_both_logs_and_actual_command_bytes(self):
        buffers = {RECORDS.PREFIX + 'compiler/' + key: value for key, value in
                   (('command.json', raw(self.command())), ('stdout.txt', b'NONPHYSICAL STDOUT'),
                    ('stderr.txt', b'NONPHYSICAL STDERR'))}
        first = RECORDS.command_receipt(buffers, 'compiler')
        for key, name in (('command', 'command.json'), ('stdout', 'stdout.txt'), ('stderr', 'stderr.txt')):
            changed = dict(buffers)
            changed[RECORDS.PREFIX + 'compiler/' + name] += b'changed'
            self.assertNotEqual(RECORDS.command_receipt(changed, 'compiler')[key], first[key])

    def test_standalone_cargo_fragment_supported_without_executable(self):
        result = self.check_cargo()
        self.assertEqual(result['kind'], 'gravity')
        self.assertEqual(result['original_binary'], 'target/release/examples/gravity-force-case')

    def test_cargo_test_target_and_profile_not_examples(self):
        for section, key, value in (('target', 'test', 0), ('target', 'kind', ['example', 'bin']),
                                    ('target', 'name', 'other'), ('profile', 'test', True),
                                    ('profile', 'opt_level', '0')):
            row = self.cargo()
            row[section][key] = value
            with self.assertRaises(ValueError):
                self.check_cargo(row)

    def test_cargo_paths_and_success_are_not_inferred(self):
        for key in ('executable', 'manifest_path'):
            row = self.cargo()
            row[key] = '/OTHER/source/file'
            with self.assertRaisesRegex(ValueError, 'Cargo source/manifest/executable'):
                self.check_cargo(row)
        for value in (False, 1, None):
            with self.assertRaises(ValueError):
                self.check_cargo(ending={'reason': 'build-finished', 'success': value})

    def test_duplicate_cargo_example_or_finish_rejected(self):
        artifact, finished = raw(self.cargo()), raw({'reason': 'build-finished', 'success': True})
        for value in (artifact + artifact + finished, artifact + finished + finished, artifact):
            with self.assertRaisesRegex(ValueError, 'One successful Cargo build and example'):
                RECORDS.cargo_record(value, 'gravity', '/NONPHYSICAL/source')

    def test_one_nonphysical_part_reassembles_only_opaque_identity(self):
        record, buffers = self.parts()
        self.assertEqual(RECORDS.binary_parts(record, buffers), ['parts/gravity.part0000'])

    def test_part_corruption_missing_order_and_boolean_size_rejected(self):
        record, buffers = self.parts()
        bad = copy.deepcopy(record)
        bad['parts'][0]['path'] = 'parts/gravity.part0001'
        with self.assertRaisesRegex(ValueError, 'Contiguous ordered'):
            RECORDS.binary_parts(bad, buffers)
        bad = copy.deepcopy(record)
        bad['parts'][0]['bytes'] = True
        with self.assertRaisesRegex(ValueError, 'integer byte count'):
            RECORDS.binary_parts(bad, buffers)
        changed = {key: value + b'corrupt' for key, value in buffers.items()}
        with self.assertRaisesRegex(ValueError, 'Exact full binary part bytes'):
            RECORDS.binary_parts(record, changed)

    def test_short_nonfinal_part_and_total_hash_rejected(self):
        record, buffers = self.parts()
        record['parts'].append({**record['parts'][0], 'path': 'parts/gravity.part0001'})
        buffers[RECORDS.PREFIX + 'parts/gravity.part0001'] = next(iter(buffers.values()))
        with self.assertRaisesRegex(ValueError, 'Exact full binary part bytes'):
            RECORDS.binary_parts(record, buffers)
        record, buffers = self.parts()
        record['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Reassembled binary byte identity'):
            RECORDS.binary_parts(record, buffers)

    def test_zero_or_excessive_part_inventories_rejected(self):
        record, buffers = self.parts()
        for values in ([], [record['parts'][0]] * 513):
            record['parts'] = values
            with self.assertRaisesRegex(ValueError, 'Bounded binary parts'):
                RECORDS.binary_parts(record, buffers)

    def test_remote_closure_rejects_extra_failed_inventory_before_omission_claim(self):
        buffers = {RECORDS.PREFIX + 'files.sha256.json': raw({'export.failed.json': RECORDS.descriptor(b'failed')})}
        with self.assertRaisesRegex(ValueError, 'Exact complete remote build closure'):
            RECORDS.manifest_records(buffers, [])

    def test_partial_metadata_closure_does_not_hide_extra_acquired_buffers(self):
        # An empty-record closure fragment is NOT a complete build: the outer
        # verify_records API requires both real source-linked binary records.
        names = ['build.json', 'runtime.json', 'export.json', *[label + '/' + name
                 for label in RECORDS.LABELS for name in ('command.json', 'stdout.txt', 'stderr.txt')]]
        buffers = {RECORDS.PREFIX + name: b'NONPHYSICAL_CLOSURE_FRAGMENT' for name in names}
        buffers[RECORDS.PREPARED] = b'NONPHYSICAL_PREPARATION_FRAGMENT'
        buffers[RECORDS.PREFIX + 'files.sha256.json'] = raw({name: RECORDS.descriptor(buffers[RECORDS.PREFIX + name])
                                                          for name in names})
        self.assertEqual(RECORDS.manifest_records(buffers, []), {})
        buffers[RECORDS.PREFIX + 'export.failed.json'] = b'NONPHYSICAL_FAILED_FRAGMENT'
        with self.assertRaisesRegex(ValueError, 'Exact acquired record/part buffers'):
            RECORDS.manifest_records(buffers, [])

    def test_remote_closure_changed_body_rejected_against_unchanged_inventory(self):
        names = ['build.json', 'runtime.json', 'export.json', *[label + '/' + name
                 for label in RECORDS.LABELS for name in ('command.json', 'stdout.txt', 'stderr.txt')]]
        buffers = {RECORDS.PREFIX + name: b'NONPHYSICAL_CLOSURE_FRAGMENT' for name in names}
        buffers[RECORDS.PREPARED] = b'NONPHYSICAL_PREPARATION_FRAGMENT'
        manifest = {name: RECORDS.descriptor(buffers[RECORDS.PREFIX + name]) for name in names}
        buffers[RECORDS.PREFIX + 'files.sha256.json'] = raw(manifest)
        buffers[RECORDS.PREFIX + 'geometry/stdout.txt'] += b'changed'
        with self.assertRaisesRegex(ValueError, 'Remote build closure byte identity'):
            RECORDS.manifest_records(buffers, [])

    def test_source_map_requires_exact_buffers_before_pins(self):
        for buffers in ({}, {'extra': b'NONPHYSICAL'}):
            with self.assertRaisesRegex(ValueError, 'Exact selected source map'):
                RECORDS.source_records({'source_sha256': {'selected': 'a' * 64}}, buffers)
        with self.assertRaisesRegex(ValueError, 'Selected source byte identity'):
            RECORDS.source_records({'source_sha256': {'selected': 'a' * 64}}, {'selected': b'NONPHYSICAL'})

    def test_full_interface_rejects_absent_authentic_inputs_without_success_fixture(self):
        with self.assertRaisesRegex(ValueError, 'Exact snapshot/release objects'):
            RECORDS.verify_records({}, raw({}), raw({}), {})
        with self.assertRaisesRegex(ValueError, 'Remote buffer mapping'):
            RECORDS.verify_records([], raw({}), raw({}), {})
