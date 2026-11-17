#!/usr/bin/env python3
"""Pinned REANA preflight and bounded no-evolution HLL/HLLD shock comparison (#24)."""
from datetime import datetime, timezone
import json
import subprocess
import sys
import time

import remote


def main():
    if sys.platform!='linux':raise ValueError('Run on REANA Linux')
    metadata=json.loads((remote.WORK/'snapshot.json').read_text())
    report=dict(status='running',scientific_acceptance=False,commands=[],
                started_utc=datetime.now(timezone.utc).isoformat(),
                snapshot_sha256=remote.sha(remote.WORK/'snapshot.json'),
                source_revision=metadata['source_revision'])
    path=remote.OUTPUT/'hll_execution.json';env=remote.environment()
    commands=[
        ['cargo','fmt','--check'],
        ['cargo','clippy','--all-targets','--all-features','--locked','--','-D','warnings'],
        ['cargo','test','--release','--workspace','--all-targets','--locked'],
        ['cargo','build','--release','-p','openmhd','--bin','vector-potential','--locked'],
        [sys.executable,'-m','unittest','discover','-s','scripts','-p','test_*.py'],
        [sys.executable,'scripts/check_m0_spec.py'],
        [sys.executable,'scripts/check_reference_packet.py'],
        [sys.executable,'scripts/run_hll_shock_probe.py',str(remote.WORK/'original-runs.json.gz')],
    ]
    try:
        remote.verify_source(metadata)
        if remote.sha(remote.WORK/'original-runs.json.gz') != metadata['upload_sha256']['original-runs.json.gz']:
            raise ValueError('Changed original run records')
        for index,command in enumerate(commands):
            log_path=remote.OUTPUT/f'check_{index:02d}.log';start=time.monotonic()
            with log_path.open('w') as log:
                done=subprocess.run(command,cwd=remote.SOURCE,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900)
            report['commands'].append(dict(command=command,seconds=time.monotonic()-start,returncode=done.returncode,log_sha256=remote.sha(log_path)))
            remote.dump(path,report);print(command,done.returncode,flush=True)
            if done.returncode:raise ValueError('Command failed')
        remote.verify_source(metadata);report['status']='completed'
    except Exception as error:
        report.update(status='failed',error=f'{type(error).__name__}: {error}')
    finally:
        report['ended_utc']=datetime.now(timezone.utc).isoformat();remote.dump(path,report)
        remote.dump(remote.OUTPUT/'hll_artifacts.sha256.json',{
            str(p.relative_to(remote.WORK)):remote.sha(p)
            for directory in (remote.OUTPUT,remote.SOURCE/'results/hll_shock_probe')
            for p in sorted(directory.rglob('*')) if p.is_file()})
    return 0 if report['status']=='completed' else 1


if __name__=='__main__':raise SystemExit(main())
