"""REANA-only orchestration controls; all dummy inputs are nonphysical.

No Rust executable or force/reference evaluator is called by these controls.
Mocked byte closures are deliberately invalid as physical reference packets.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'reana/galaxy_gravity_force_case.py'
SPEC = importlib.util.spec_from_file_location('force_case_under_test', SOURCE)
JOB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(JOB)


def fixture():
    sources = {'supervisor.py': 'tools/m1_evidence/reana_metadata_job.py',
        'launcher.py': 'reana/galaxy_test_case.py',
        'galaxy_gravity_bridge.py': 'scripts/galaxy_gravity_bridge.py',
        'galaxy_gravity_compare.py': 'scripts/galaxy_gravity_compare.py',
        'galaxy_gravity_reference.py': 'scripts/galaxy_gravity_reference.py',
        'galaxy_geometry3_reference.py': 'scripts/galaxy_geometry3_reference.py'}
    buffers = {name: (ROOT / path).read_bytes() for name, path in sources.items()}
    buffers.update({'runner.py': SOURCE.read_bytes(), 'input.txt': b'NONPHYSICAL_METADATA_ONLY\n',
                    'gravity.part0000': b'NONPHYSICAL_NOT_AN_EXECUTABLE'})
    buffers['root-release.json'] = JOB.encode(dict(schema='openmhd.gravity-force-root-release.v1',
        wrapper_source_revision='0' * 40, build_source_revision='0' * 40,
        rust_source_inventory_sha256='0' * 64, runner_sha256=JOB.sha(buffers['runner.py']),
        binary=JOB.descriptor(buffers['gravity.part0000']), input_sha256=JOB.sha(buffers['input.txt']),
        prerequisites={n: '0' * 64 for n in JOB.PREREQUISITES}, component_accepted=False))
    reseal_case(buffers)
    return buffers


def reseal_case(buffers):
    buffers['case.json'] = JOB.encode(dict(schema='openmhd.gravity-force-case.v1',
        name='NONPHYSICAL_METADATA_CONTROL', resources=dict(JOB.RESOURCES),
        root_release_sha256=JOB.sha(buffers['root-release.json'])))


def seal(buffers):
    return JOB.encode(dict(schema='openmhd.gravity-force-case-inputs.v1',
        files={name: JOB.descriptor(raw) for name, raw in buffers.items()},
        binary=dict(**JOB.descriptor(buffers['gravity.part0000']), parts=['gravity.part0000'])))


def command():
    return dict(schema='openmhd.metadata-command.v1', outcome='success', returncode=0,
        external_terminal_evidence_required=False,
        cleanup=dict(writers_settled=True, direct_child_reaped=True,
            leader_held_until_group_close=True, group_authority_lost=False, remaining_live_pids=[]))


def comparison():
    # A verdict-helper control only. It contains no physical expressions,
    # source catalog, reference certificates or executable provenance.
    return dict(schema='openmhd.gravity-static-comparison.v1', arithmetic_verdict='pass',
        candidate_projection=dict(checked_source=dict(particles=[])),
        gates={n: dict(verdict='pass') for n in ('pair_energy', 'raw_net_force', 'raw_net_torque_origin')},
        external_execution_provenance_verified=False, component_accepted=False, merger_accepted=False,
        candidate_scales_are_diagnostic_only=True, candidate_residuals_repaired=False)


def prepare_work(work):
    buffers = fixture()
    for path, raw in buffers.items():
        (work / path).write_bytes(raw)
    (work / 'payload.json').write_bytes(seal(buffers))


class GravityForceCaseMetadataTests(unittest.TestCase):
    def test_metadata_keeps_exact_opaque_binary_without_running_it(self):
        buffers = fixture()
        case, release, binary = JOB.validate_inputs(buffers, seal(buffers))
        self.assertEqual(binary, b'NONPHYSICAL_NOT_AN_EXECUTABLE')
        self.assertEqual(case['name'], 'NONPHYSICAL_METADATA_CONTROL')
        self.assertIs(release['component_accepted'], False)

    def test_resealed_source_changes_and_unsealed_input_changes_reject(self):
        buffers = fixture()
        buffers['galaxy_gravity_compare.py'] += b'\n# CONTROL_SOURCE_REPLACEMENT\n'
        with self.assertRaisesRegex(ValueError, 'immutable source pins'):
            JOB.validate_inputs(buffers, seal(buffers))
        buffers = fixture()
        original = seal(buffers)
        buffers['input.txt'] += b'CHANGED'
        with self.assertRaisesRegex(ValueError, 'input hashes'):
            JOB.validate_inputs(buffers, original)

    def test_binary_order_extra_input_and_boolean_resource_reject(self):
        buffers = fixture()
        payload = JOB.parse(seal(buffers))
        payload['binary']['parts'] *= 2
        with self.assertRaisesRegex(ValueError, 'Ordered bounded'):
            JOB.validate_inputs(buffers, JOB.encode(payload))
        buffers['unexpected'] = b'EXTRA'
        with self.assertRaisesRegex(ValueError, 'input inventory'):
            JOB.validate_inputs(buffers, seal(buffers))
        buffers = fixture()
        case = JOB.parse(buffers['case.json'])
        case['resources']['threads'] = True
        buffers['case.json'] = JOB.encode(case)
        with self.assertRaisesRegex(ValueError, 'Case resources'):
            JOB.validate_inputs(buffers, seal(buffers))

    def test_each_external_prerequisite_and_original_input_link_is_required(self):
        for name in JOB.PREREQUISITES:
            buffers = fixture()
            release = JOB.parse(buffers['root-release.json'])
            del release['prerequisites'][name]
            buffers['root-release.json'] = JOB.encode(release)
            reseal_case(buffers)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'separately reviewed'):
                JOB.validate_inputs(buffers, seal(buffers))
        buffers = fixture()
        release = JOB.parse(buffers['root-release.json'])
        release['input_sha256'] = 'f' * 64
        buffers['root-release.json'] = JOB.encode(release)
        reseal_case(buffers)
        with self.assertRaisesRegex(ValueError, 'original input links'):
            JOB.validate_inputs(buffers, seal(buffers))

    def test_duplicate_nonfinite_and_overflowing_json_reject(self):
        for raw, message in ((b'{"x":1,"x":2}', 'Duplicate'),
                             (b'{"x":NaN}', 'Finite'), (b'{"x":1e400}', 'Finite')):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, message):
                JOB.parse(raw)

    def test_process_evidence_requires_closed_held_leader_and_exact_raw_hashes(self):
        evidence = JOB.process_evidence(command(), b'INPUT', b'RAW_STDOUT', b'RAW_STDERR', 'control')
        self.assertEqual(evidence['stdout_sha256'], JOB.sha(b'RAW_STDOUT'))
        self.assertEqual(evidence['stderr_bytes'], len(b'RAW_STDERR'))
        for field, value in (('returncode', False), ('returncode', 1), ('outcome', 'unknown')):
            changed = command()
            changed[field] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, 'closed actual process'):
                JOB.process_evidence(changed, b'I', b'O', b'E', 'control')
        for field in ('writers_settled', 'direct_child_reaped', 'leader_held_until_group_close'):
            changed = command()
            changed['cleanup'][field] = None
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'closed actual process'):
                JOB.successful_command(changed)

    def test_exact_gate_inventory_summary_and_scope_cannot_be_relaxed(self):
        value = comparison()
        self.assertTrue(JOB.comparison_passed(value))
        for name in ('pair_energy', 'raw_net_force', 'raw_net_torque_origin'):
            changed = copy.deepcopy(value)
            del changed['gates'][name]
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Exact per-particle'):
                JOB.comparison_passed(changed)
        changed = copy.deepcopy(value)
        changed['gates']['raw_net_force']['verdict'] = 'unresolved'
        with self.assertRaisesRegex(ValueError, 'summary consistency'):
            JOB.comparison_passed(changed)
        changed['arithmetic_verdict'] = 'unresolved'
        self.assertFalse(JOB.comparison_passed(changed))
        changed = dict(value, candidate_residuals_repaired=True)
        with self.assertRaisesRegex(ValueError, 'arithmetic-only scope'):
            JOB.comparison_passed(changed)

    def test_particle_gate_coverage_uses_actual_ids(self):
        value = comparison()
        identifier = '0' * 31 + '1'
        value['candidate_projection']['checked_source']['particles'] = [dict(id=identifier)]
        with self.assertRaisesRegex(ValueError, 'Exact per-particle'):
            JOB.comparison_passed(value)
        for suffix in ('.force', '.specific_potential'):
            value['gates']['particle.' + identifier + suffix] = dict(verdict='pass')
        self.assertTrue(JOB.comparison_passed(value))
        value['candidate_projection']['checked_source']['particles'] *= 2
        with self.assertRaisesRegex(ValueError, 'Unique sorted'):
            JOB.comparison_passed(value)

    def test_reference_byte_closure_keeps_nonphysical_fixture_nonaccepting(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            buffers = {n: b'NONPHYSICAL_NOT_A_REFERENCE' for n in JOB.PACKET_FILES if n != 'files.sha256.json'}
            buffers['input.json'] = b'NONPHYSICAL_INPUT'
            buffers['status.json'] = b'{"status":"not_executed_nonphysical"}'
            for n in ('galaxy_gravity_reference.py', 'galaxy_geometry3_reference.py'):
                buffers[n] = (ROOT / 'scripts' / n).read_bytes()
            for n, raw in buffers.items():
                (root / n).write_bytes(raw)
            (root / 'files.sha256.json').write_bytes(JOB.encode(dict(
                schema='openmhd.gravity-reference-files.v1', files={n: JOB.descriptor(v) for n, v in buffers.items()})))
            retained = JOB.read_reference_packet(root, b'NONPHYSICAL_INPUT')
            self.assertEqual(retained['status.json'], b'{"status":"not_executed_nonphysical"}')
            with self.assertRaisesRegex(ValueError, 'reference input, sources'):
                JOB.read_reference_packet(root, b'DIFFERENT_INPUT')
            (root / 'unexpected').write_bytes(b'EXTRA')
            with self.assertRaisesRegex(ValueError, 'eight-body'):
                JOB.read_reference_packet(root, b'NONPHYSICAL_INPUT')

    def test_prelaunch_failure_closes_nonpassing_eight_artifact_envelope(self):
        with tempfile.TemporaryDirectory() as name:
            work = Path(name)
            (work / 'payload.json').write_bytes(b'{"schema":"wrong","files":{}}')
            with mock.patch.object(JOB, 'load_held') as loader:
                code = JOB.run(work)
            self.assertEqual(code, 1)
            loader.assert_not_called()
            output = work / 'outputs'
            self.assertEqual({p.name for p in output.iterdir()}, set(JOB.OUTPUTS))
            result = JOB.parse((output / 'result.json').read_bytes())
            self.assertEqual(result['status'], 'failed')
            self.assertIs(result['component_accepted'], False)

    def test_escaping_candidate_supervision_keeps_original_unknown_journal(self):
        with tempfile.TemporaryDirectory() as name:
            work = Path(name)
            prepare_work(work)
            original = JOB.encode(dict(outcome='unknown', finished_utc=None, returncode=None,
                                       cleanup=dict(writers_settled=None)))
            def interrupted(supervisor, argv, cwd, environment, output, timeout, links):
                (output / 'command.json').write_bytes(original)
                (output / 'stdout.txt').write_bytes(b'CONTROL_PARTIAL_CANDIDATE_LOG')
                raise RuntimeError('CONTROL_SUPERVISION_LOSS')
            launcher = SimpleNamespace(launch_native=mock.Mock(side_effect=interrupted))
            reducer = SimpleNamespace(compare=mock.Mock(side_effect=AssertionError('Never compare')))
            modules = [SimpleNamespace(runtime_record=lambda *args: {}), launcher, SimpleNamespace(), reducer]
            with mock.patch.object(JOB, 'load_held', side_effect=modules):
                code = JOB.run(work)
            self.assertEqual(code, 1)
            self.assertEqual(launcher.launch_native.call_count, 1)
            reducer.compare.assert_not_called()
            output = work / 'outputs'
            self.assertEqual((output / 'child_raw.bin').read_bytes(), b'CONTROL_PARTIAL_CANDIDATE_LOG')
            self.assertEqual((work / 'force_private/candidate_command/command.json').read_bytes(), original)
            result = JOB.parse((output / 'result.json').read_bytes())
            self.assertTrue(result['external_terminal_evidence_required'])
            self.assertIsNone(JOB.parse((output / 'command.json').read_bytes())['candidate']['returncode'])

    def test_reference_failure_preserves_candidate_and_never_calls_reducer(self):
        with tempfile.TemporaryDirectory() as name:
            work = Path(name)
            prepare_work(work)
            def stage(supervisor, argv, cwd, environment, output, timeout, links):
                row = command()
                if output.name == 'reference_command':
                    row.update(outcome='nonzero', returncode=1)
                (output / 'command.json').write_bytes(JOB.encode(row))
                (output / 'stdout.txt').write_bytes(b'CONTROL_LOG_' + output.name.encode())
                (output / 'stderr.txt').write_bytes(b'')
                return row
            launcher = SimpleNamespace(launch_native=mock.Mock(side_effect=stage))
            bridge = SimpleNamespace(decode_snapshot=mock.Mock(return_value=object()),
                project_reference=mock.Mock(return_value=dict(reference_input_bytes=b'NONPHYSICAL_PROJECTED_WORDS')))
            reducer = SimpleNamespace(compare=mock.Mock(side_effect=AssertionError('Never compare')))
            modules = [SimpleNamespace(runtime_record=lambda *args: {}), launcher, bridge, reducer]
            with mock.patch.object(JOB, 'load_held', side_effect=modules):
                code = JOB.run(work)
            self.assertEqual(code, 1)
            self.assertEqual(launcher.launch_native.call_count, 2)
            reducer.compare.assert_not_called()
            output = work / 'outputs'
            self.assertEqual((output / 'stdout.txt').read_bytes(), b'CONTROL_LOG_candidate_command')
            journals = JOB.parse((output / 'command.json').read_bytes())
            self.assertEqual(journals['candidate']['returncode'], 0)
            self.assertEqual(journals['reference']['returncode'], 1)

    def test_optimized_execution_stops_before_output_creation(self):
        with tempfile.TemporaryDirectory() as name:
            for options, extra in ((['-O'], {}), ([], {'PYTHONOPTIMIZE': '1'})):
                environment = dict(os.environ, **extra)
                child = subprocess.run([sys.executable, '-B', *options, str(SOURCE)], cwd=name,
                    env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
                self.assertNotEqual(child.returncode, 0)
                self.assertIn(b'Optimized force comparison rejected', child.stderr)
                self.assertFalse((Path(name) / 'outputs').exists())
