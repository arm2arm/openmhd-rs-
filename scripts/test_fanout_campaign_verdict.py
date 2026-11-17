"""The fan-out verdict applies the registered phase checks and never claims acceptance."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import fanout_campaign_verdict as reducer
import run_m1_bounded as bounded

PROFILE = reducer.PROFILE
RIEMANN = 'hlld-pressure'
LIMITER = 'smooth-extrema'
BINARY = 'b'*64
OPTIONS = dict(accelerated_projection=True, projection_screening=1., potential_limiter=LIMITER)
# As the binary writes it: the cached factorization is recorded only when it is used.
SUMMARY = dict(profile=PROFILE, projection_screening=1., riemann_solver='hlld-pressure-blend-v1',
               potential_limiter='smooth-extrema-v1', limited=True, projection_solver='cached-cholesky-pcg')
# (iterative projection, trial step fraction) of the three registered configurations.
CACHED, ITERATIVE, ITERATIVE_STEP = (False, None), (True, None), (True, .95)


def options(configuration=CACHED):
    iterative, step = configuration
    result = dict(OPTIONS, accelerated_projection=not iterative)
    if step is not None:
        result['trial_step_fraction'] = step
    return result


def summary_of(configuration=CACHED):
    iterative, step = configuration
    result = dict(SUMMARY)
    if iterative:
        result.pop('projection_solver')
    if step is not None:
        result['trial_step_fraction'] = step
    return result


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def record(config, configuration=CACHED):
    run = dict(status='completed', config=config, positive_and_conservative=True, summary=summary_of(configuration))
    if config['case'] == 'alfven':
        run['errors'] = dict(final=dict(B=dict(L1=1e-4)))
    if config['case'] in ('brio-wu', 'orszag-tang'):
        run['state_and_diagnostic_gates'] = True
    return run


def pairs(configs, status='pass'):
    return [dict(names=[n, n.removesuffix('_base')+'_boost'], status=status)
            for n in configs if n.endswith('_base')]


def write_plan(directory, configs, kind, snapshot_sha256, summary, configuration=CACHED):
    cases = []
    for index, config in enumerate(configs.values()):
        folder = f'case-{index:04d}'
        dump(directory/'download'/folder/'outputs/execution.json', dict(binary_sha256=BINARY))
        cases.append(dict(directory=folder, specification=dict(kind=kind, config=config,
                                                                options=options(configuration))))
    dump(directory/'plan.json', dict(snapshot_sha256=snapshot_sha256, cases=cases))
    dump(directory/'runs.json', {n: record(c, configuration) for n, c in configs.items()})
    dump(directory/'checkpoint.json', dict(all_terminal=True, observation_errors={}, execution_failures=[],
                                           summaries={kind: summary}))


def write_bounded(directory, snapshot_sha256, configuration=CACHED):
    iterative, step = configuration
    study = reducer.BOUNDED_STUDIES[configuration]
    names = [stage[0] for stage in bounded.stages(PROFILE, 1., False)]
    gate = dict(provenance=dict(profile=PROFILE, projection_screening=1., riemann_solver=RIEMANN,
                                potential_limiter=LIMITER, accelerated_projection=not iterative),
                stages=[dict(name=n, status='pass') for n in names], bounded_blockers_closed=True,
                source_and_binary_unchanged=True, potential_limiter=LIMITER, full_m1_accepted=False)
    if iterative:
        gate['iterative_projection'] = True
    if step is not None:
        gate['provenance']['trial_step_fraction'] = gate['trial_step_fraction'] = step
    dump(directory/study/'gate.json', gate)
    dump(directory/'execution.json', dict(status='completed', study=study, snapshot_sha256=snapshot_sha256))
    dump(directory/'artifacts.sha256.json',
         {f'outputs/{study}/gate.json': reducer.sha(directory/study/'gate.json')})


def campaign(root, configuration=CACHED):
    """A complete synthetic campaign in which every registered phase check holds."""
    snapshot = root/'snapshot.json'
    snapshot.write_text('{"fixture": true}\n')
    digest = reducer.sha(snapshot)
    dump(root/'preflight/preflight.json', dict(snapshot_sha256=digest, binary_sha256=BINARY))
    cases = reducer.registered(RIEMANN)
    refinement = [dict(profile=PROFILE, jitter=jitter, variable=variable, values=[[x, 1e-16] for x in coordinates],
                       successive_B_L1_orders=[1.]*(len(coordinates)-1))
                  for jitter in (0., .15) for variable, coordinates in (('n', [8, 16, 32, 64]), ('dt', [.001, .0005, .00025]))]
    write_plan(root/'medium', cases['medium'], 'wave', digest, dict(pairs=pairs(cases['medium'])), configuration)
    write_plan(root/'mean', cases['mean'], 'wave', digest, dict(pairs=pairs(cases['mean']), mean_refinement=refinement),
               configuration)
    write_plan(root/'physics', cases['physics'], 'physics', digest,
               dict(all_registered_physics_gates=True, completed_evolutions=30), configuration)
    write_plan(root/'waves', cases['waves'], 'wave', digest,
               dict(pairs=pairs(cases['waves'], 'pass under both reported normalizations'),
                    alfven_convergence=[dict(gate='pass') for _ in range(8)],
                    temporal=[dict(status='completed', errors=dict(B=dict(L1=1e-5))) for _ in range(12)]),
               configuration)
    write_bounded(root/'bounded', digest, configuration)
    directories = {name: root/name for name in ('bounded', 'medium', 'mean', 'physics', 'waves')}
    return snapshot, root/'preflight', directories


def edit(path, change):
    value = json.loads(path.read_text())
    change(value)
    path.write_text(json.dumps(value))


class FanoutVerdict(unittest.TestCase):
    def run_verdict(self, root):
        snapshot, preflight, directories = campaign(root) if not (root/'snapshot.json').exists() else (
            root/'snapshot.json', root/'preflight', {n: root/n for n in ('bounded', 'medium', 'mean', 'physics', 'waves')})
        return reducer.verdict(snapshot, preflight, directories, RIEMANN, LIMITER)

    def test_registered_matrices_have_the_campaign_sizes(self):
        cases = reducer.registered(RIEMANN)
        self.assertEqual({k: len(v) for k, v in cases.items()}, dict(medium=48, mean=24, waves=112, physics=30))
        for group in cases.values():
            for config in group.values():
                self.assertEqual((config['profile'], config['riemann_solver']), (PROFILE, RIEMANN))

    def test_complete_passing_campaign_passes_every_phase_without_claiming_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_verdict(Path(temp))
        self.assertEqual(tuple(result['phases']), reducer.PHASES)
        for name, item in result['phases'].items():
            self.assertTrue(item['passed'], (name, item))
            self.assertTrue(item['checks'])
        self.assertTrue(result['all_registered_phase_checks_passed'])
        self.assertFalse(result['full_m1_accepted'])
        self.assertEqual(result['configuration'], dict(profile=PROFILE, accelerated_projection=True,
                                                       projection_screening=1., riemann_solver=RIEMANN,
                                                       potential_limiter=LIMITER, trial_step_fraction=None))
        self.assertEqual(result['binary_sha256'], BINARY)

    def test_follow_up_configurations_pass_only_with_their_own_metadata(self):
        for configuration in (ITERATIVE, ITERATIVE_STEP):
            iterative, step = configuration
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                snapshot, preflight, directories = campaign(root, configuration)
                run = lambda c=configuration: reducer.verdict(snapshot, preflight, directories, RIEMANN, LIMITER, *c)
                result = run()
                self.assertTrue(result['all_registered_phase_checks_passed'], result['phases'])
                self.assertFalse(result['full_m1_accepted'])
                self.assertEqual((result['configuration']['accelerated_projection'],
                                  result['configuration']['trial_step_fraction']), (False, step))
                # The same evidence read as another configuration fails at every phase that checks it.
                for other in {CACHED, ITERATIVE, ITERATIVE_STEP} - {configuration}:
                    wrong = run(other)
                    self.assertFalse(wrong['all_registered_phase_checks_passed'])
                    for name in ('bounded_short', 'bounded_medium', 'mean', 'physics', 'waves'):
                        self.assertFalse(wrong['phases'][name]['passed'], (configuration, other, name))
                # One run that used the cached factorization, or another step controller, fails its plan.
                for change in (lambda s: s.update(projection_solver='cached-cholesky-pcg'),
                               lambda s: s.update(trial_step_fraction=.9),
                               lambda s: s.pop('trial_step_fraction', None) if step else s.update(trial_step_fraction=.95)):
                    original = (root/'waves/runs.json').read_text()
                    edit(root/'waves/runs.json', lambda v: change(v[next(iter(v))]['summary']))
                    failed = run()['phases']['waves']
                    self.assertFalse(failed['passed'])
                    self.assertFalse(failed['checks']['candidate_and_limiter_metadata'])
                    (root/'waves/runs.json').write_text(original)
                self.assertTrue(run()['all_registered_phase_checks_passed'])
        with self.assertRaises(ValueError):
            reducer.verdict(Path('x'), Path('y'), {}, RIEMANN, LIMITER, False, .95)

    def test_each_kind_of_missing_or_failed_evidence_fails_its_phase(self):
        first = lambda runs: next(iter(runs))
        mutations = [
            ('waves', 'waves/runs.json', lambda v: v[first(v)].update(status='failed'), 'every_planned_case_completed'),
            ('waves', 'waves/runs.json', lambda v: v[first(v)].update(status='failed'), 'all_completed'),
            ('waves', 'waves/runs.json', lambda v: v[first(v)]['summary'].pop('potential_limiter'),
             'candidate_and_limiter_metadata'),
            ('waves', 'waves/runs.json', lambda v: v[first(v)]['summary'].update(riemann_solver='hlld'),
             'execution_configuration'),
            ('waves', 'waves/checkpoint.json',
             lambda v: v['summaries']['wave']['alfven_convergence'][0].update(gate='fail'), 'spatial_gates'),
            ('waves', 'waves/checkpoint.json',
             lambda v: v['summaries']['wave']['pairs'][0].update(status='fail'), 'boost_pairs'),
            ('waves', 'waves/checkpoint.json', lambda v: v['summaries']['wave']['temporal'].pop(), 'temporal_measured'),
            ('waves', 'waves/checkpoint.json', lambda v: v.update(all_terminal=False), 'terminal_without_errors'),
            ('physics', 'physics/runs.json', lambda v: v[first(v)]['summary'].pop('potential_limiter'),
             'candidate_and_limiter_metadata'),
            ('physics', 'physics/checkpoint.json',
             lambda v: v['summaries']['physics'].update(all_registered_physics_gates=False), 'physics_gates'),
            ('physics', 'physics/plan.json', lambda v: v['cases'].pop(), 'registered_cases'),
            ('mean', 'mean/download/case-0003/outputs/execution.json', lambda v: v.update(binary_sha256='c'*64),
             'same_binary'),
            ('mean', 'mean/checkpoint.json', lambda v: v['summaries']['wave']['mean_refinement'].pop(),
             'mean_refinement_measured'),
            ('mean', 'mean/plan.json', lambda v: v.update(snapshot_sha256='0'*64), 'same_snapshot'),
            ('mean', 'mean/runs.json', lambda v: v[first(v)]['summary'].update(potential_limiter='none'),
             'candidate_and_limiter_metadata'),
            ('bounded_medium', 'medium/plan.json',
             lambda v: v['cases'][0]['specification']['options'].pop('potential_limiter'), 'registered_options'),
            ('bounded_medium', 'medium/checkpoint.json',
             lambda v: v['summaries']['wave']['pairs'][0].update(status='fail'), 'boost_pairs_passed'),
            ('bounded_medium', 'medium/checkpoint.json', lambda v: v['observation_errors'].update(w='lost'),
             'terminal_without_errors'),
            ('bounded_short', f'bounded/{reducer.STUDY}/gate.json', lambda v: v['stages'][1].update(status='fail'),
             'four_short_stages_passed'),
            ('bounded_short', 'bounded/execution.json', lambda v: v.update(study='m1-bounded'), 'workflow_completed'),
            ('bounded_short', 'bounded/execution.json', lambda v: v.update(snapshot_sha256='0'*64), 'same_snapshot'),
        ]
        for name, path, change, check in mutations:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                campaign(root)
                edit(root/path, change)
                result = self.run_verdict(root)
                item = result['phases'][name]
                self.assertFalse(item['passed'], (name, check))
                self.assertIs(item['checks'][check], False, (name, check, item))
                self.assertFalse(result['all_registered_phase_checks_passed'])
                self.assertFalse(result['full_m1_accepted'])

    def test_bounded_gate_file_and_configuration_are_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot, _, directories = campaign(root)
            digest = reducer.sha(snapshot)
            check = lambda limiter=LIMITER: reducer.bounded_checks(directories['bounded'], digest, RIEMANN, limiter)
            self.assertTrue(all(check().values()))
            self.assertFalse(check(None)['configuration'])     # the gate ran another limiter than requested
            gate = root/'bounded'/reducer.STUDY/'gate.json'
            original = gate.read_text()
            edit(gate, lambda v: v['provenance'].pop('potential_limiter'))
            self.assertFalse(check()['configuration'])
            self.assertFalse(check()['gate_file_unchanged'])   # edited after the workflow hashed it
            gate.write_text(original)
            self.assertTrue(all(check().values()))

    def test_calibration_checks_use_the_registered_n128_cases(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            campaign(root)
            name = f'alfven_{PROFILE}_v0.0_j0.15_fixed_n128_base'
            edit(root/'waves/runs.json', lambda v: v[name]['errors']['final']['B'].update(L1=.0021))
            result = self.run_verdict(root)
            self.assertIs(result['phases']['calibration_wave']['checks']['amplitude_error'], False)
            self.assertTrue(result['phases']['waves']['passed'])   # the amplitude limit is the calibration check
            edit(root/'physics/runs.json',
                 lambda v: v['orszag-tang_n128_j0.15_base'].update(state_and_diagnostic_gates=False))
            result = self.run_verdict(root)
            self.assertIs(result['phases']['calibration_vortex']['checks']['diagnostics'], False)

    def test_missing_evidence_is_a_failed_phase_and_foreign_preflight_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot, preflight, directories = campaign(root)
            missing = dict(directories, waves=root/'absent', bounded=root/'absent')
            result = reducer.verdict(snapshot, preflight, missing, RIEMANN, LIMITER)
            for name in ('waves', 'calibration_wave', 'bounded_short'):
                self.assertFalse(result['phases'][name]['passed'])
                self.assertIn('error', result['phases'][name])
            self.assertTrue(result['phases']['physics']['passed'])
            self.assertFalse(result['all_registered_phase_checks_passed'])
            edit(preflight/'preflight.json', lambda v: v.update(snapshot_sha256='0'*64))
            with self.assertRaises(ValueError):
                reducer.verdict(snapshot, preflight, directories, RIEMANN, LIMITER)
            with self.assertRaises(ValueError):
                reducer.verdict(snapshot, preflight, directories, RIEMANN, 'minmod')

    def test_phase_wrapper_requires_true_checks(self):
        self.assertTrue(reducer.phase(lambda: dict(a=True))['passed'])
        for checks in (dict(), dict(a=True, b=False), dict(a=1), dict(a=None)):
            self.assertFalse(reducer.phase(lambda: copy.deepcopy(checks))['passed'])
        failed = reducer.phase(lambda: {}['missing'])
        self.assertFalse(failed['passed'])
        self.assertIn('KeyError', failed['error'])


if __name__ == '__main__':
    unittest.main()
