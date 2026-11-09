#!/usr/bin/env python3
"""Verify and summarize the rejected Eq. (77) trials from an extracted archive."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import tarfile

STUDIES = ('primary', 'low', 'high', 'extended', 'quadratic_primary',
           'quadratic_extended', 'baseline')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def analyze(root):
    records = []
    verified_sources = 0
    for study in STUDIES:
        directory = root / study
        provenance = load(directory / 'provenance.json')
        source = directory / 'source.tar.gz'
        if sha(source) != provenance['source_archive_sha256']:
            raise ValueError(f'{study}: source archive hash mismatch')
        with tarfile.open(source) as archive:
            for name, digest in provenance['source_sha256'].items():
                data = archive.extractfile(name).read()
                if hashlib.sha256(data).hexdigest() != digest:
                    raise ValueError(f'{study}: source mismatch: {name}')
                verified_sources += 1
        for name, run in load(directory / 'runs.json').items():
            case = directory / name
            for filename, digest in run['files_sha256'].items():
                if sha(case / filename) != digest:
                    raise ValueError(f'{study}/{name}: changed {filename}')
            summary = run['summary']
            row = dict(study=study, name=name, completed=summary['completed'],
                       time=summary['time'], steps=summary['steps'],
                       seconds=run['seconds'], state_rejections=summary['rejected_state'],
                       final_p_min=summary['final']['p_min'])
            history = case / 'accepted_diagnostics.csv'
            if history.exists():
                with history.open() as stream:
                    data = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(stream)]
                if (len(data) != summary['steps'] + 1 or data[0]['time'] != 0 or
                        data[-1]['time'] != summary['time'] or
                        any(b['time'] <= a['time'] for a, b in zip(data, data[1:])) or
                        any(not math.isfinite(v) for r in data for v in r.values())):
                    raise ValueError(f'{study}/{name}: invalid accepted-state history')
                row.update(history=data, accepted_p_min=min(r['p_min'] for r in data),
                           accepted_rho_min=min(r['rho_min'] for r in data),
                           budget_max=max(r['budget_max'] for r in data))
            with (case / 'final.csv').open() as stream:
                row['bx_max_error'] = max(abs(float(r['bx']) - .75) for r in csv.DictReader(stream))
            records.append(row)
    with (root / 'checks/fourier_modes_phase.csv').open() as stream:
        modes = [{k: v if k == 'operator' else float(v) for k, v in r.items()}
                 for r in csv.DictReader(stream)]
    symbol_error = max(abs(r['potential_rayleigh'] - (2/3)*16**2 *
                          (math.cos(2*math.tau*r['kx']/16)-math.cos(math.tau*r['kx']/16)))
                       for r in modes if r['jitter'] == 0 and r['ky'] == 0 and r['operator'] == 'quadratic')
    if symbol_error > 1e-10:
        raise ValueError('Quadratic Fourier symbol disagrees with independent formula')
    return dict(runs=records, modes=modes, verified_source_members=verified_sources,
                fourier_symbol_max_error=symbol_error, full_m1_accepted=False,
                disposition='Both evolution profiles rejected and removed; original solver and gates retained.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.raw)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f'Verified {len(result["runs"])} runs and {result["verified_source_members"]} source members; '
          f'symbol error {result["fourier_symbol_max_error"]:.3g}; M1 remains unaccepted.')


if __name__ == '__main__':
    main()
