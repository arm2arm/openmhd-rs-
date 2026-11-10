#!/usr/bin/env python3
"""Decompose measured Alfven B errors into amplitude, phase, shape and Bx terms.

This is postprocessing of immutable snapshots, not an evolution or acceptance
criterion. On irregular cells the residual is the volume-weighted orthogonal
remainder of one analytic phase function, not a resolved Fourier spectrum.
"""
import argparse
import json
import math
from pathlib import Path

from run_m1_wave_loop import dump, read_snapshot, sha


def decompose(cells, time, parallel, boost):
    """Orthogonal projection onto the unit-norm analytic circular-wave mode."""
    volume = math.fsum(c['volume'] for c in cells)
    phase = [math.tau*(c['x']+(1-parallel-boost[0])*time) for c in cells]
    basis = [complex(math.cos(p), math.sin(p)) for p in phase]
    values = [complex(c['bz'], c['by'])/.1 for c in cells]
    overlaps = [q*e.conjugate() for q, e in zip(values, basis)]

    def weighted(values):
        return math.fsum(c['volume']*v for c, v in zip(cells, values))/volume

    coefficient = complex(weighted([z.real for z in overlaps]),
                          weighted([z.imag for z in overlaps]))
    amplitude = abs(coefficient)
    angle = math.atan2(coefficient.imag, coefficient.real)
    parts = dict(
        amplitude=(amplitude-1)**2,
        phase=4*amplitude*math.sin(angle/2)**2,
        shape=weighted([abs(q-coefficient*e)**2 for q, e in zip(values, basis)]),
        bx=weighted([((c['bx']-1)/.1)**2 for c in cells]),
    )
    total = weighted([abs(q-e)**2+((c['bx']-1)/.1)**2
                      for c, q, e in zip(cells, values, basis)])
    if not math.isclose(total, math.fsum(parts.values()), rel_tol=5e-10, abs_tol=1e-22):
        raise ValueError('Orthogonal error decomposition does not close')
    return dict(amplitude_relative=amplitude, phase_radians=angle,
                relative_B_L2=math.sqrt(total), squared_error_parts=parts,
                squared_error_fractions={k: v/total if total else 0. for k, v in parts.items()},
                identity_residual=total-math.fsum(parts.values()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, help='Completed wave packet with all original snapshots')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output file')
    directory = args.directory.resolve()
    runs = json.loads((directory/'runs.json').read_text())
    provenance = json.loads((directory/'provenance.json').read_text())
    if sha(directory/'runs.json') != provenance['result_sha256']['runs.json']:
        raise ValueError('Execution runs differ from provenance')
    report = dict(scope=__doc__, analysis_source_sha256=sha(Path(__file__).resolve()),
                  execution_provenance_sha256=sha(directory/'provenance.json'),
                  execution_runs_sha256=sha(directory/'runs.json'),
                  amplitude_scale=.1, mean_bx=1., runs={})
    for name, row in runs.items():
        c = row['config']
        if c['case'] != 'alfven' or name.startswith('temporal_'):
            continue
        if row['status'] != 'completed':
            raise ValueError('Incomplete wave: '+name)
        measured = {}
        stages = (('initial', 'initial.csv', 0.),
                  ('t0.25', 'checkpoint_0.25000000.csv', .25),
                  ('final', 'final.csv', c['target']))
        for stage, file, time in stages:
            path = directory/name/file
            if sha(path) != row['sha256'][file]:
                raise ValueError('Snapshot changed: '+str(path))
            result = decompose(read_snapshot(path, c['n'], time), time, c['parallel'], c['boost'])
            expected = row['errors'][stage]['B']['L2']/.1
            if not math.isclose(result['relative_B_L2'], expected, rel_tol=5e-10, abs_tol=1e-15):
                raise ValueError('Independent norm differs from registered measurement: '+name)
            measured[stage] = dict(time=time, snapshot_sha256=sha(path), **result)
        report['runs'][name] = dict(config=c, stages=measured)
    if not report['runs']:
        raise ValueError('No completed Alfven waves')
    dump(args.output, report)
    print('Decomposed', len(report['runs']), 'waves at three times; '
          'all raw hashes, norm comparisons and orthogonal identities verify.')


if __name__ == '__main__':
    main()
