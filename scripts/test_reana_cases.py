"""Remote orchestration regressions: dependencies, concurrent starts and early failures."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import reana_cases as fanout
from run_m1_wave_loop import configurations

PROFILE = 'bulk-frame-heun-quadratic-v1'


def case(name='alfven_probe_base', n=32):
    return dict(kind='wave', config=dict(name=name, case='alfven', profile=PROFILE, n=n,
                jitter=0., parallel=1., motion_family='fixed', mesh_velocity=[0., 0.],
                boost=[0., 0., 0.], dt=None, target=1., riemann_solver='hlld-pressure'),
                resources=dict(threads=2, memory='4Gi', timeout_seconds=180.),
                options=dict(accelerated_projection=True, projection_screening=1.))


def prerequisite(root):
    snapshot = root/'snapshot.json'
    fanout.dump(snapshot, {'fixture': 'frozen source'})
    directory = root/'preflight'
    directory.mkdir()
    spec = importlib.util.spec_from_file_location('fixture_remote', fanout.ROOT/'reana/remote.py')
    remote = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(remote)
    checks = [dict(command=c, returncode=0) for c in remote.commands('m1-fanout-preflight', 1)]
    fanout.dump(directory/'runtime.json', dict(machine='x86_64', image=fanout.IMAGE))
    receipt = dict(schema=1, snapshot_sha256=fanout.sha(snapshot), machine='x86_64', image=fanout.IMAGE,
                   runtime_sha256=fanout.sha(directory/'runtime.json'), commands=checks,
                   binary_sha256=hashlib.sha256(b'verified executable').hexdigest())
    fanout.dump(directory/'preflight.json', receipt)
    fanout.dump(directory/'execution.json', dict(status='completed', study='m1-fanout-preflight', commands=checks,
                snapshot_sha256=fanout.sha(snapshot), runtime_sha256=receipt['runtime_sha256']))
    return snapshot, directory


def seal_preflight(directory):
    hashes = {'outputs/'+p.name: fanout.sha(p) for p in directory.iterdir() if p.name != 'artifacts.sha256.json'}
    hashes['outputs/vector-potential'] = fanout.load(directory/'preflight.json')['binary_sha256']
    fanout.dump(directory/'artifacts.sha256.json', hashes)


class FanoutTests(unittest.TestCase):
    def test_frozen_wave_matrix_has_not_changed(self):
        args = SimpleNamespace(suite='physical', candidate_mean=False, profile=PROFILE, quick=False,
                               temporal=True, calibration=False, riemann='hlld-pressure')
        configs, pairs = configurations(args)
        self.assertEqual(len(configs), 112)
        self.assertEqual(len(pairs), 48)
        # Canonical SHA256 of the immutable 2026-11-10 manifest, independently archived.
        self.assertEqual(hashlib.sha256(json.dumps(configs, sort_keys=True).encode()).hexdigest(),
                         '837708886a47143cb8cbe61e7400d9685c6b346278dd7b856baf93c6a0b7c72b')

    def test_failed_incomplete_or_changed_preflight_blocks_cases(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot, directory = prerequisite(root)
            seal_preflight(directory)
            self.assertEqual(fanout.verify_preflight(snapshot, directory)['machine'], 'x86_64')
            baseline = fanout.load(directory/'execution.json')
            for change in ('failed', 'missing-command', 'nonzero'):
                execution = copy.deepcopy(baseline)
                if change == 'failed': execution['status'] = 'failed'
                elif change == 'missing-command': execution['commands'].pop()
                else: execution['commands'][2]['returncode'] = 1
                fanout.dump(directory/'execution.json', execution)
                seal_preflight(directory)
                with self.assertRaises(ValueError): fanout.verify_preflight(snapshot, directory)
            fanout.dump(directory/'execution.json', baseline)
            seal_preflight(directory)
            snapshot.write_text('changed source')
            with self.assertRaises(ValueError): fanout.verify_preflight(snapshot, directory)

    def test_invalid_names_resources_and_projection_never_reach_execution(self):
        fanout.validate_case(case())
        for field, key, value in [('config', 'name', '../outside'), ('resources', 'threads', 0),
                                  ('resources', 'memory', '0Gi'), ('resources', 'timeout_seconds', float('inf')),
                                  ('options', 'projection_screening', -1), ('config', 'target', 0)]:
            spec = case()
            spec[field][key] = value
            with self.assertRaises(ValueError): fanout.validate_case(spec)

    def test_submission_starts_independent_workflows_concurrently_once(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            entries = []
            for i in range(2):
                directory = root/str(i)
                directory.mkdir()
                fanout.dump(directory/'payload.json', {'input_sha256': {}})
                fanout.dump(directory/'reana.yaml', {'fixture': i})
                entries.append(dict(directory=str(i), workflow=f'fixture-{i}.1',
                               payload_sha256=fanout.sha(directory/'payload.json'),
                               workflow_sha256=fanout.sha(directory/'reana.yaml')))
            fanout.dump(root/'plan.json', {'cases': entries})
            started = threading.Barrier(2)
            def fake_client(command, arguments, cwd=None):
                self.assertEqual(arguments[0], 'run')
                started.wait(timeout=5)  # A serial launcher cannot satisfy the barrier.
                return 'created/uploaded/started'
            with patch.object(fanout, 'client', side_effect=fake_client) as client:
                result = fanout.submit(root, ['fixture-client'])
                self.assertEqual({x['status'] for x in result.values()}, {'submitted'})
                self.assertEqual(client.call_count, 2)
                with self.assertRaises(ValueError): fanout.submit(root, ['fixture-client'])
                self.assertEqual(client.call_count, 2)

    def test_complete_failed_ladder_detected_with_unfinished_sibling(self):
        specs, runs = [], {}
        for n in (32, 64, 128, 256):
            spec = case(f'alfven_fixture_n{n}_base', n)
            specs.append(spec)
            runs[spec['config']['name']] = dict(config=spec['config'], status='completed',
                positive_and_conservative=True, errors={'final': {'B': {'L1': 1./n}}})
        specs.append(case('unrelated_pending_case'))
        report = fanout.evaluate_ready(Path('.'), specs, runs)
        self.assertTrue(report['verified_required_failure'])
        self.assertEqual(report['completed_cases'], 4)
        self.assertFalse(report['full_m1_accepted'])
        del runs['alfven_fixture_n256_base']
        self.assertFalse(fanout.evaluate_ready(Path('.'), specs, runs)['verified_required_failure'])

    def test_mismatched_pair_configuration_is_rejected(self):
        a, b = case('wave_base')['config'], case('wave_boost')['config']
        with self.assertRaises(ValueError): fanout.wave_pairs({'wave_base': a, 'wave_boost': b})
        b.update(boost=[2., -1., 0.], mesh_velocity=[2., -1.])
        self.assertEqual(len(fanout.wave_pairs({'wave_base': a, 'wave_boost': b})), 1)
        b['target'] = .5
        with self.assertRaises(ValueError): fanout.wave_pairs({'wave_base': a, 'wave_boost': b})
        b['target'] = a['target']
        b['riemann_solver'] = 'hll'
        with self.assertRaises(ValueError): fanout.wave_pairs({'wave_base': a, 'wave_boost': b})
        extra = case()
        extra['config']['unlimited'] = True
        with self.assertRaises(ValueError): fanout.validate_case(extra)

    def test_verified_failure_cancels_only_pending_sibling_after_saving_evidence(self):
        self.monitor_fixture(download_error=False)

    def test_download_error_is_not_a_physical_failure_or_reason_to_cancel(self):
        self.monitor_fixture(download_error=True)

    def monitor_fixture(self, download_error):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            specs = [case('alfven_failed_base'), case('pending_case')]
            entries = [dict(workflow=f'fixture-{i}.1', directory=str(i), specification=s, payload_sha256='payload')
                       for i, s in enumerate(specs)]
            fanout.dump(root/'plan.json', dict(cases=entries, snapshot_sha256='snapshot', analysis_sha256={}))
            stops = []
            def fake_client(command, arguments, cwd=None):
                action, workflow = arguments[0], arguments[arguments.index('-w')+1]
                if action == 'status':
                    return json.dumps([{'status': 'finished' if workflow == 'fixture-0.1' else 'running'}])
                if action == 'download':
                    if download_error: raise RuntimeError('transient download error')
                    local = Path(arguments[arguments.index('-o')+1])/'outputs'
                    local.mkdir()
                    record = dict(config=specs[0]['config'], status='failed', positive_and_conservative=False)
                    fanout.dump(local/'record.json', record)
                    fanout.dump(local/'execution.json', dict(case=specs[0], payload_sha256='payload',
                        snapshot_sha256='snapshot', record_sha256=fanout.sha(local/'record.json')))
                    fanout.dump(local/'artifacts.sha256.json', {'outputs/'+p.name: fanout.sha(p) for p in local.iterdir()})
                    return ''
                if action == 'stop':
                    self.assertTrue(fanout.load(root/'checkpoint.json')['verified_required_failure'])
                    stops.append(workflow)
                    return ''
                raise AssertionError(action)
            with patch.object(fanout, 'client', side_effect=fake_client):
                report = fanout.inspect(root, ['fixture-client'])
            self.assertEqual(stops, [] if download_error else ['fixture-1.1'])
            self.assertEqual(report['verified_required_failure'], not download_error)
            self.assertEqual(bool(report['observation_errors']), download_error)
            self.assertFalse(report['all_terminal'])
            self.assertEqual((root/'first_failure.json').exists(), not download_error)


if __name__ == '__main__':
    unittest.main()
