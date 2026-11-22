#!/usr/bin/env python3
"""Verify the factor-shift reporting fix against the pinned pre-cache REANA binary.

Only the known erroneous screened shift label may differ. Original bytes and
all comparison hashes are preserved. No scientific acceptance is inferred.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from run_m1_wave_loop import ROOT, dump, read_snapshot, sha
from run_projection_cache_benchmark import physical_hashes


def comparison_hashes(directory, accelerated, screening, corrected):
    hashes=physical_hashes(directory)
    summary=json.loads((directory/'summary.json').read_text())
    if accelerated:
        expected=screening if corrected and screening>0 else 1e-8
        if summary.get('projection_preconditioner_shift') != expected:
            raise ValueError('Incorrect reported factor shift')
        del summary['projection_preconditioner_shift']
    elif 'projection_preconditioner_shift' in summary:
        raise ValueError('Uncached solve reports a cached factor')
    if summary.get('projection_screening',0.) != screening:
        raise ValueError('Screening configuration mismatch')
    hashes['summary.json']=hashlib.sha256(json.dumps(summary,sort_keys=True).encode()).hexdigest()
    return hashes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--baseline-provenance',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    out=args.output_dir.resolve()
    if out.exists():parser.error('Use a fresh directory')
    out.mkdir(parents=True)
    baseline=args.baseline.resolve();candidate=ROOT/'target/release/vector-potential'
    provenance=json.loads(args.baseline_provenance.read_text())
    if sha(baseline)!=provenance['binary_sha256']:raise ValueError('Baseline binary changed')
    names=[p for p in provenance['source_sha256'] if p.endswith('.rs') or p.endswith('Cargo.toml') or p in ('Cargo.lock','rust-toolchain.toml')]
    sources={p:sha(ROOT/p) for p in names}
    changed=sorted(p for p in names if sources[p]!=provenance['source_sha256'][p])
    expected=['apps/openmhd/src/bin/vector-potential.rs','crates/mhd-vector-pot/src/general.rs',
              'crates/mhd-vector-pot/src/projected_rate.rs','crates/mhd-vector-pot/tests/heun.rs']
    if changed!=expected:raise ValueError('Unreviewed numerical differences: '+str(changed))
    baseline.chmod(0o755)
    report=dict(status='running',baseline_provenance=provenance,source_sha256=sources,
                candidate_binary_sha256=sha(candidate),comparisons=[],runs={},
                scope='Reporting correction plus independently benchmarked diagonal cache; not M1 acceptance')
    dump(out/'report.json',report)
    try:
        for profile in ('bulk-frame-heun-projected-v1','bulk-frame-heun-quadratic-v1'):
            for accelerated,screening in ((False,0.),(False,1.),(True,0.),(True,.5),(True,1.)):
                label=f'{profile}_a{int(accelerated)}_k{screening}'
                comparisons=[]
                for corrected,binary in ((False,baseline),(True,candidate)):
                    name=label+('_corrected' if corrected else '_baseline');dest=out/name;dest.mkdir()
                    command=[str(binary),'--case','alfven','--profile',profile,'--n','8','--jitter','.15',
                             '--time','.002','--parallel-velocity','1','--projection-screening',str(screening),
                             '--output',str(dest),*(['--accelerated-projection'] if accelerated else [])]
                    row=dict(command=command,status='failed',timeout_seconds=120)
                    report['runs'][name]=row
                    with (dest/'run.log').open('w') as log:
                        try:done=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=120)
                        except subprocess.TimeoutExpired:
                            row['status']='timeout'
                            raise
                    row['returncode']=done.returncode
                    if done.returncode:raise ValueError('Evolution failed: '+name)
                    summary=json.loads((dest/'summary.json').read_text())
                    if not summary['completed'] or summary['time']!=.002 or summary['profile']!=profile:
                        raise ValueError('Incomplete/mismatched run')
                    read_snapshot(dest/'initial.csv',8,0.);read_snapshot(dest/'final.csv',8,.002)
                    row.update(status='completed',physical_sha256=physical_hashes(dest))
                    comparisons.append(comparison_hashes(dest,accelerated,screening,corrected))
                same=comparisons[0]==comparisons[1]
                report['comparisons'].append(dict(name=label,physical_outputs_unchanged=same))
                dump(out/'report.json',report)
                if not same:raise ValueError('Unexpected output change: '+label)
        if sources!={p:sha(ROOT/p) for p in names} or sha(candidate)!=report['candidate_binary_sha256']:
            raise ValueError('Source/binary changed')
        report['status']='completed'
    except (OSError,ValueError,KeyError,subprocess.TimeoutExpired) as error:
        report.update(status='failed',error=str(error))
    finally:dump(out/'report.json',report)
    return 0 if report['status']=='completed' else 1


if __name__=='__main__':raise SystemExit(main())
