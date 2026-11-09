#!/usr/bin/env python3
"""Compare a pinned REANA baseline with the diagonal-cache change, then threading.

Sequential runs, at most 24 threads. Timings are shared-cluster observations;
bit-identical physical outputs are required before the full campaign proceeds.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import resource
import subprocess
import time

from run_m1_bounded import CANDIDATE
from run_m1_wave_loop import ROOT, dump, sha


def verify_baseline(binary, provenance):
    if sha(binary) != provenance['binary_sha256']:
        raise ValueError('Baseline binary checksum mismatch')
    sources = provenance['source_sha256']
    names = sorted(p for p in sources if p.endswith('.rs') or p.endswith('Cargo.toml') or
                   p in ('Cargo.lock', 'rust-toolchain.toml'))
    changed = [p for p in names if sha(ROOT/p) != sources[p]]
    if changed != ['crates/mhd-vector-pot/src/projected_rate.rs']:
        raise ValueError('Unexpected numerical source differences: '+str(changed))
    return {p: sha(ROOT/p) for p in names}


def physical_hashes(directory):
    required = {'initial.csv','final.csv','summary.json','history.json'}
    files = {p.name: sha(p) for p in directory.iterdir()
             if p.is_file() and p.suffix in ('.json','.csv') and p.name != 'timing.json'}
    if not required <= files.keys():
        raise ValueError('Missing physical output')
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--baseline-provenance', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists(): parser.error('Use a fresh output directory')
    output.mkdir(parents=True)
    baseline = args.baseline.resolve()
    candidate = ROOT/'target/release/vector-potential'
    provenance = json.loads(args.baseline_provenance.read_text())
    sources = verify_baseline(baseline, provenance)
    baseline.chmod(0o755)
    report = dict(created_utc=datetime.now(timezone.utc).isoformat(), status='running', runs={},
                  comparisons=[], baseline_provenance=provenance, source_sha256=sources,
                  candidate_binary_sha256=sha(candidate), concurrent_simulations=1,
                  maximum_threads=24, scope='Bitwise parity and shared-cluster timing; not M1 acceptance')
    dump(output/'benchmark.json', report)

    def run(label, binary, config, threads):
        dest = output/label
        dest.mkdir()
        command = [str(binary),'--case',config['case'],'--profile',CANDIDATE,'--n',str(config['n']),
                   '--jitter','.15','--time',str(config['time']),'--motion','fixed','--threads',str(threads),
                   '--accelerated-projection','--projection-screening',str(config['kappa']),
                   '--output',str(dest),*config.get('extra',[])]
        row = dict(config=config, command=command, threads=threads, status='failed')
        report['runs'][label] = row
        print('Starting '+label, flush=True)
        start = time.monotonic()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        try:
            with (dest/'run.log').open('w') as log:
                done = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=600)
            row['returncode'] = done.returncode
            if done.returncode: raise ValueError('Failed evolution: '+label)
            summary = json.loads((dest/'summary.json').read_text())
            history = json.loads((dest/'history.json').read_text())
            if (not summary['completed'] or summary['time'] != config['time'] or summary['profile'] != CANDIDATE
                    or summary.get('projection_screening',0.) != config['kappa'] or not history):
                raise ValueError('Incomplete or mismatched output: '+label)
            if any(h['diagnostics']['rho_min'] <= 0 or h['diagnostics']['p_min'] <= 0 or
                   max(map(abs,h['diagnostics']['normalized_budget'])) > 1e-10 for h in history):
                raise ValueError('Positivity/budget failure: '+label)
            row.update(status='completed', physical_sha256=physical_hashes(dest),
                       timing=json.loads((dest/'timing.json').read_text()))
        except subprocess.TimeoutExpired:
            row['status']='timeout'
            raise
        finally:
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            row.update(wall_seconds=time.monotonic()-start,
                       cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
            dump(output/'benchmark.json',report)
        return row

    def compare(name, before, after):
        same = before['physical_sha256'] == after['physical_sha256']
        report['comparisons'].append(dict(name=name,bit_identical=same,
            wall_speedup=before['wall_seconds']/after['wall_seconds'],
            evolution_speedup=before['timing']['evolution_seconds']/after['timing']['evolution_seconds']))
        dump(output/'benchmark.json',report)
        if not same: raise ValueError('Physical outputs differ: '+name)

    cases = dict(wave64_k0=dict(case='alfven',n=64,time=.02,kappa=0.,extra=['--parallel-velocity','1']),
                 wave128_k1=dict(case='alfven',n=128,time=.02,kappa=1.,extra=['--parallel-velocity','1']),
                 shock512=dict(case='brio-wu',n=512,time=.02,kappa=1.,extra=['--ny','8']),
                 vortex32=dict(case='orszag-tang',n=32,time=.5,kappa=1.))
    try:
        for name, config in cases.items():
            before = run(name+'_baseline',baseline,config,1)
            after = run(name+'_cached',candidate,config,1)
            compare(name,before,after)
        reference = report['runs']['wave128_k1_cached']
        for threads in (4,12,24):
            row = run(f'wave128_k1_threads{threads}',candidate,cases['wave128_k1'],threads)
            compare(f'threads{threads}',reference,row)
        if verify_baseline(baseline,provenance) != sources or sha(candidate) != report['candidate_binary_sha256']:
            raise ValueError('Source/binary changed during benchmark')
        report['status']='completed'
    except (OSError,ValueError,KeyError,subprocess.TimeoutExpired) as error:
        report.update(status='failed',error=str(error))
    finally:
        report['ended_utc']=datetime.now(timezone.utc).isoformat()
        dump(output/'benchmark.json',report)
    return 0 if report['status']=='completed' else 1


if __name__ == '__main__': raise SystemExit(main())
