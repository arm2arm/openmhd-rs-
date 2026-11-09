#!/usr/bin/env python3
"""Four bounded shock-development checks; never a substitute for full M1 validation."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import math
from pathlib import Path
import shutil
import subprocess
import tarfile
import time

from run_m1_physics import BOOST, PROFILE, boost_comparison, load_json, validate_run
from run_m1_wave_loop import ROOT, dump, read_cells, sha


def configurations(profile):
    return {f'j{jitter}_{label}': dict(name=f'j{jitter}_{label}', case='brio-wu',
             n=256, ny=4, jitter=jitter, boost=list(boost), time=.01, profile=profile)
            for jitter in (0., .15) for label, boost in (('base', (0.,0.,0.)), ('boost', BOOST))}


def assess(configs, runs, pairs):
    complete = len(configs) == 4 and set(runs) == set(configs) and all(
        r['status'] == 'completed' for r in runs.values())
    stability = complete and all(r['positive_and_conservative'] for r in runs.values())
    boost = len(pairs) == 2 and all(p['status'] == 'pass' for p in pairs)
    diagnostics = complete and all(r['diagnostic_checks_passed'] for r in runs.values())
    return dict(completed_cases=sum(r['status']=='completed' for r in runs.values()),
                expected_cases=4, complete=complete, stability_and_budget=stability,
                boost_checks=boost, short_diagnostic_checks=diagnostics,
                short_screen_passed=stability and boost and diagnostics,
                full_m1_accepted=False,
                scope='Short t=.01 development screen only. Full t=.1 shock, convergence, wave/loop/vortex and M1 gates remain required; no long jobs are submitted.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--profile', default=PROFILE)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--timeout', type=float, default=30., help='Wall seconds per case; a timeout is incomplete, never a pass')
    parser.add_argument('--dt', type=float, help='Optional smaller timestep cap, for a separate investigation')
    parser.add_argument('--trace-energy', action='store_true')
    args=parser.parse_args()
    if not 1<=args.jobs<=4:parser.error('jobs must be 1..4')
    if not math.isfinite(args.timeout) or not 0<args.timeout<=60:parser.error('timeout must be in (0,60] seconds')
    if args.dt is not None and (not math.isfinite(args.dt) or args.dt<=0):parser.error('dt must be finite and positive')
    output=args.output_dir.resolve()
    if output.exists():parser.error('Use a fresh output directory')
    output.mkdir(parents=True)
    paths=sorted({*ROOT.glob('crates/**/*.rs'), *ROOT.glob('apps/**/*.rs'),
                  *ROOT.glob('crates/*/Cargo.toml'), *ROOT.glob('apps/*/Cargo.toml'),
                  ROOT/'Cargo.toml', ROOT/'Cargo.lock', ROOT/'rust-toolchain.toml',
                  Path(__file__).resolve(), ROOT/'scripts/run_m1_physics.py', ROOT/'scripts/run_m1_wave_loop.py',
                  ROOT/'scripts/physics_projection.py', ROOT/'benchmarks/m0/packet.json',
                  ROOT/'docs/M1_SHOCK_INVESTIGATION.md'})
    sources={str(p.relative_to(ROOT)):sha(p) for p in paths}
    with tarfile.open(output/'source.tar.gz','w:gz') as archive:
        for p in paths:archive.add(p,arcname=str(p.relative_to(ROOT)))
    cargo=shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
    subprocess.run([cargo,'build','--release','--locked','-p','openmhd','--bin','vector-potential'],cwd=ROOT,check=True)
    binary=ROOT/'target/release/vector-potential'
    provenance=dict(created_utc=datetime.now(timezone.utc).isoformat(), source_sha256=sources,
                    binary_sha256=sha(binary), source_archive_sha256=sha(output/'source.tar.gz'),
                    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    rustc=subprocess.check_output([str(Path(cargo).with_name('rustc')),'-Vv'],text=True),
                    jobs=args.jobs, threads_per_case=1, timeout_seconds=args.timeout,
                    dt_cap=args.dt, trace_energy=args.trace_energy)
    configs=configurations(args.profile);packet=load_json(ROOT/'benchmarks/m0/packet.json')
    dump(output/'manifest.json',configs);dump(output/'provenance.json',provenance)

    def run(c):
        dest=output/c['name'];dest.mkdir()
        command=[str(binary),'--case',c['case'],'--profile',c['profile'],'--n',str(c['n']),
                 '--jitter',str(c['jitter']),'--time',str(c['time']),'--motion','rigid',
                 '--mesh-x',str(c['boost'][0]),'--mesh-y',str(c['boost'][1]),
                 '--boost-x',str(c['boost'][0]),'--boost-y',str(c['boost'][1]),'--output',str(dest)]
        if args.dt is not None:command+=['--dt',str(args.dt)]
        if args.trace_energy:command+=['--trace-energy']
        record=dict(config=c,command=command,status='failed');start=time.monotonic()
        try:
            with (dest/'run.log').open('w') as log:
                done=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=args.timeout)
            record['returncode']=done.returncode
            summary=load_json(dest/'summary.json');record['summary']=summary
            if done.returncode or not summary['completed']:
                failure=dest/'failure.txt'
                raise ValueError(failure.read_text() if failure.exists() else 'failed evolution; inspect run.log')
            history=load_json(dest/'history.json');physics=load_json(dest/'physics.json')
            initial=read_cells(dest/'initial.csv');cells=read_cells(dest/'final.csv')
            validate_run(c,summary,history,physics,load_json(dest/'geometry.json'),initial,cells)
            positive=all(h['diagnostics']['rho_min']>0 and h['diagnostics']['p_min']>0
                         and max(map(abs,h['diagnostics']['normalized_budget']))<=packet['solver']['budget_tolerance'] for h in history)
            gate=packet['cases']['brio-wu']['gate']
            diagnostics=dict(bx_max_error=max(abs(x['bx']-.75) for x in cells),signal_travel_x=physics['signal_travel_x'])
            checks=dict(bx=diagnostics['bx_max_error']<=gate['bx_max_error'],
                        seam=physics['signal_tracking'] and 0<=diagnostics['signal_travel_x']<gate['seam_max_signal_travel'])
            record.update(status='completed',positive_and_conservative=positive,
                          diagnostic_values=diagnostics,diagnostic_checks=checks,diagnostic_checks_passed=all(checks.values()))
        except subprocess.TimeoutExpired:
            record.update(status='timeout',error='Wall-time cap reached; incomplete execution')
        except (OSError,ValueError,KeyError) as error:
            record['error']=str(error)
        record['seconds']=time.monotonic()-start
        record['files_sha256']={p.name:sha(p) for p in dest.iterdir() if p.is_file()}
        return c['name'],record

    runs={};started=time.monotonic()
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for future in as_completed([pool.submit(run,c) for c in configs.values()]):
            name,r=future.result();runs[name]=r;dump(output/'runs.json',runs)
            print(f'{name}: {r["status"]} in {r["seconds"]:.2f}s; t={r.get("summary",{}).get("time", "incomplete")}',flush=True)
    pairs=[]
    for jitter in (0.,.15):
        names=[f'j{jitter}_base',f'j{jitter}_boost'];pair=dict(names=names,status='unexecuted')
        if all(runs[n]['status']=='completed' for n in names):
            pair.update(boost_comparison(*(read_cells(output/n/'final.csv') for n in names),configs[names[0]],runs[names[0]]['summary']))
            pair['status']='pass' if pair['passed'] else 'fail'
        pairs.append(pair)
    summary=assess(configs,runs,pairs);summary.update(boost_pairs=pairs,wall_seconds=time.monotonic()-started)
    unchanged=sources=={str(p.relative_to(ROOT)):sha(p) for p in paths} and sha(binary)==provenance['binary_sha256']
    summary['source_and_binary_unchanged']=unchanged
    summary['short_screen_passed'] &= unchanged
    dump(output/'summary.json',summary)
    provenance['results_sha256']={n:sha(output/n) for n in ('manifest.json','runs.json','summary.json')};dump(output/'provenance.json',provenance)
    print(f'Short screen: {"PASS" if summary["short_screen_passed"] else "FAIL"}; {summary["wall_seconds"]:.2f}s. Full M1 acceptance: not evaluated.')
    return 0 if summary['short_screen_passed'] else 1


if __name__=='__main__':raise SystemExit(main())
