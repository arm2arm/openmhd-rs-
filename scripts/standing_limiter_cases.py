#!/usr/bin/env python3
"""Explicit REANA case lists for the issue #26 limiter controls (no execution).

Each plan is one limiter configuration, because completed ladders are grouped
by mesh family only. Configurations, names, grids and physical times are the
registered ones from the wave and shock/vortex runners; only the documented
opt-in limiter options and per-case resources are added. See
docs/M1_STANDING_WAVE_PLAN.md. Resources are execution budgets, not gates.
"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from run_m1_physics import configurations as physics_configurations
from run_m1_wave_loop import configurations as wave_configurations

PROFILE = 'bulk-frame-heun-quadratic-v1'
RIEMANN = 'hlld-pressure'
OPTIONS = dict(accelerated_projection=True, projection_screening=1.)
# Projection solver and step controller of each labelled configuration. 'cached'
# is the 2026-11-13 campaign; the other two are the 2026-11-17 follow-up of
# docs/M1_FULL_VALIDATION_PLAN.md: the same equations solved by Jacobi-PCG,
# and that with the first trial at 0.95 of the CFL bound.
SOLVERS = {
    'cached': {},
    'iterative': dict(accelerated_projection=False),
    'iterative-step': dict(accelerated_projection=False, trial_step_fraction=.95),
}
# Limiter options of each labelled configuration; 'default' adds none.
VARIANTS = {
    'default': {},
    'potential-none': dict(potential_limiter='none'),
    'primitive-unlimited': dict(potential_limiter='neighbour-extrema', unlimited=True),
    'all-unlimited': dict(unlimited=True),
    'smooth-extrema': dict(potential_limiter='smooth-extrema'),
}
# (threads, memory, wall cap in seconds) by case family and resolution.
RESOURCES = {
    'wave': {8: (2, '4Gi', 900.), 16: (2, '4Gi', 900.), 32: (2, '4Gi', 1800.), 64: (2, '4Gi', 7200.),
             128: (4, '8Gi', 28800.), 256: (4, '16Gi', 86400.)},
    'brio-wu': {64: (2, '4Gi', 1800.), 128: (2, '4Gi', 1800.), 256: (2, '4Gi', 3600.),
                512: (2, '4Gi', 3600.), 1024: (2, '8Gi', 7200.)},
    'orszag-tang': {16: (2, '4Gi', 1800.), 32: (2, '4Gi', 1800.), 64: (2, '4Gi', 7200.),
                    128: (4, '8Gi', 28800.), 256: (4, '16Gi', 86400.)},
}
# Budgets for the complete registered matrices, where up to 166 cases share the
# cluster. Per-case wall times doubled with about 100 concurrent workflows on
# 2026-11-13, CPU limits are not enforced and N256 loops have no completed
# baseline, so the caps are wide. REANA stops any job after 604800 s.
CAMPAIGN_RESOURCES = {
    'wave': {8: (2, '4Gi', 3600.), 16: (2, '4Gi', 3600.), 32: (2, '4Gi', 7200.), 64: (2, '4Gi', 28800.),
             128: (4, '8Gi', 86400.), 256: (4, '16Gi', 518400.)},
    'brio-wu': {256: (2, '4Gi', 7200.), 512: (2, '4Gi', 7200.), 1024: (2, '8Gi', 14400.)},
    'orszag-tang': {64: (2, '4Gi', 28800.), 128: (4, '8Gi', 86400.), 256: (4, '16Gi', 518400.)},
}


def specification(kind, config, variant, resources=RESOURCES, solver='cached'):
    threads, memory, timeout = resources['wave' if kind == 'wave' else config['case']][config['n']]
    return dict(kind=kind, config=config,
                resources=dict(threads=threads, memory=memory, timeout_seconds=timeout),
                options=dict(OPTIONS, **SOLVERS[solver], **VARIANTS[variant]))


def registered_waves(quick=False, suite='physical', temporal=False):
    args = SimpleNamespace(suite=suite, candidate_mean=True, profile=PROFILE, quick=quick,
                           temporal=temporal, calibration=False, riemann=RIEMANN)
    return wave_configurations(args)[0]


def standing(variant, resolutions=(32, 64, 128, 256), boost=False):
    """Registered fixed-mesh standing Alfven ladders, regular and jitter .15."""
    return [specification('wave', c, variant) for c in registered_waves().values()
            if c['case'] == 'alfven' and c['parallel'] == 1. and c['motion_family'] == 'fixed'
            and c['n'] in resolutions and (boost or not any(c['boost']))]


def waves_medium(variant, resources=RESOURCES, solver='cached'):
    """The bounded N32/64 Alfven and loop set with every boost pair (48 cases)."""
    return [specification('wave', c, variant, resources, solver) for c in registered_waves(quick=True).values()]


def waves_full(variant, resources=CAMPAIGN_RESOURCES, solver='cached'):
    """The registered 112-run wave/loop/temporal matrix: N32-256 ladders, boost pairs and N64 time steps."""
    return [specification('wave', c, variant, resources, solver) for c in registered_waves(temporal=True).values()]


def mean_field(variant, resources=RESOURCES, solver='cached'):
    """The registered 24-run nonuniform mean-field boost ladder for this profile."""
    return [specification('wave', c, variant, resources, solver) for c in registered_waves(suite='mean').values()]


def physics(variant, vortex_resolutions=(64, 128, 256), resources=RESOURCES, solver='cached'):
    """Registered shock/vortex matrix; omitting N256 vortices makes a bounded screen."""
    return [specification('physics', c, variant, resources, solver)
            for c in physics_configurations(False, PROFILE, RIEMANN).values()
            if c['case'] == 'brio-wu' or c['n'] in vortex_resolutions]


PLANS = {
    'diag-none': lambda: standing('potential-none'),
    'diag-primitive': lambda: standing('primitive-unlimited', (32, 64, 128)),
    'diag-linear': lambda: standing('all-unlimited', (32, 64, 128)),
    'cand-standing': lambda: standing('smooth-extrema', boost=True),
    'cand-waves-medium': lambda: waves_medium('smooth-extrema'),
    'cand-mean': lambda: mean_field('smooth-extrema'),
    'cand-physics-screen': lambda: physics('smooth-extrema', (64, 128)),
    'cand-physics': lambda: physics('smooth-extrema'),
    # Complete registered matrices of the candidate, one plan per campaign phase.
    'full-medium': lambda: waves_medium('smooth-extrema', CAMPAIGN_RESOURCES),
    'full-mean': lambda: mean_field('smooth-extrema', CAMPAIGN_RESOURCES),
    'full-physics': lambda: physics('smooth-extrema', resources=CAMPAIGN_RESOURCES),
    'full-waves': lambda: waves_full('smooth-extrema'),
}
# The same four registered matrices for the two configurations of the follow-up.
for _label, _solver in (('iter', 'iterative'), ('step', 'iterative-step')):
    PLANS.update({
        f'{_label}-medium': lambda s=_solver: waves_medium('smooth-extrema', CAMPAIGN_RESOURCES, s),
        f'{_label}-mean': lambda s=_solver: mean_field('smooth-extrema', CAMPAIGN_RESOURCES, s),
        f'{_label}-physics': lambda s=_solver: physics('smooth-extrema', resources=CAMPAIGN_RESOURCES, solver=s),
        f'{_label}-waves': lambda s=_solver: waves_full('smooth-extrema', solver=s),
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', choices=sorted(PLANS))
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output file')
    cases = PLANS[args.plan]()
    args.output.write_text(json.dumps(cases, indent=1, allow_nan=False)+'\n')
    print(f'{args.plan}: {len(cases)} independent cases')


if __name__ == '__main__':
    main()
