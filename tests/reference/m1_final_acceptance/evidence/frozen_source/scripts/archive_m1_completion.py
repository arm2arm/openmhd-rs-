#!/usr/bin/env python3
"""Verify and compact a completed #7 execution packet without relabelling its source."""
import argparse
import gzip
import io
import json
from pathlib import Path
import tarfile
from run_m1_wave_loop import ROOT, dump, sha


def archive(source, checkout, destination):
    execution=source/'execution_provenance.json'
    if not execution.exists(): execution=source/'provenance.json'
    provenance=json.loads(execution.read_text())
    original_summary=source/'execution_summary.json'
    if not original_summary.exists(): original_summary=source/'summary.json'
    for name,digest in provenance['result_sha256'].items():
        path=original_summary if name=='summary.json' else source/name
        if sha(path)!=digest: raise ValueError(f'changed execution result {name}')
    measurement=source/'measurement_provenance.json'
    if measurement.exists():
        measured=json.loads(measurement.read_text())
        if (sha(source/'summary.json')!=measured['summary_sha256'] or
            sha(execution)!=measured['execution_provenance_sha256'] or
            sha(original_summary)!=measured['execution_summary_sha256']):
            raise ValueError('changed measurement provenance/input/output')
    elif sha(source/'summary.json')!=provenance['result_sha256']['summary.json']:
        raise ValueError('changed summary without measurement provenance')
    runs=json.loads((source/'runs.json').read_text())
    manifest=json.loads((source/'manifest.json').read_text())
    if set(runs)!=set(manifest): raise ValueError('incomplete execution packet')
    for name,r in runs.items():
        for filename,digest in r['sha256'].items():
            if sha(source/name/filename)!=digest: raise ValueError(f'changed raw file {name}/{filename}')
    for name,digest in provenance['source_sha256'].items():
        if sha(checkout/name)!=digest: raise ValueError(f'changed source {name}')
    if destination.exists(): raise ValueError('archive destination already exists')
    destination.mkdir(parents=True)
    for name in ('summary.json','manifest.json','runs.json'):
        (destination/(name+'.gz')).write_bytes(gzip.compress((source/name).read_bytes(),mtime=0))
    (destination/'execution_provenance.json').write_bytes(execution.read_bytes())
    if measurement.exists():
        (destination/'measurement_provenance.json').write_bytes(measurement.read_bytes())
        (destination/'execution_summary.json.gz').write_bytes(gzip.compress(original_summary.read_bytes(),mtime=0))
        measurement_sources=measured.get('measurement_source_sha256',{})
        if isinstance(measurement_sources,str):
            measurement_sources={'scripts/run_m1_wave_loop.py':measurement_sources}
        if measurement_sources:
            buffer=io.BytesIO()
            with tarfile.open(fileobj=buffer,mode='w') as tar:
                for name,digest in sorted(measurement_sources.items()):
                    if sha(ROOT/name)!=digest: raise ValueError(f'changed analysis source {name}')
                    data=(ROOT/name).read_bytes();info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644
                    tar.addfile(info,io.BytesIO(data))
            (destination/'measurement_sources.tar.gz').write_bytes(gzip.compress(buffer.getvalue(),mtime=0))
    # A dirty revision is reproducible from the exact source bytes, not just HEAD.
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w') as tar:
        for name in sorted(provenance['source_sha256']):
            data=(checkout/name).read_bytes();info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644
            tar.addfile(info,io.BytesIO(data))
    (destination/'execution_sources.tar.gz').write_bytes(gzip.compress(buffer.getvalue(),mtime=0))
    selected=[]
    for name,r in runs.items():
        c=r['config']
        # Modest raw samples for independent inspection; all numerical tables retained.
        # Retain the full N256 counterexample and its earlier negative control.
        if (c['n']==256 and c['jitter']==0. and c.get('case')=='alfven'
            and c.get('profile')=='bulk-frame-signal-v1' and c['parallel']==1.
            and c['motion_family']=='fixed' and name.startswith('alfven_')):
            selected.append(name)
            continue
        if c['n']!=64 or c['jitter']!=0.: continue
        if c.get('case')=='alfven' and c['parallel']==1. and c['motion_family']=='fixed' and not name.startswith('temporal_'):
            selected.append(name)
        elif c.get('case')=='loop' and name.endswith('_base'):
            selected.append(name)
        elif 'case' not in c and name.endswith('_base'):
            selected.append(name)
    for name in selected:
        for path in sorted((source/name).glob('*.csv')):
            dest=destination/'snapshots'/name/(path.name+'.gz');dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(gzip.compress(path.read_bytes(),mtime=0))
    dump(destination/'archive_sha256.json',{str(p.relative_to(destination)):sha(p) for p in sorted(destination.rglob('*')) if p.is_file()})
    print(f'Archived {len(runs)} verified runs, {len(selected)} snapshot selections: {destination}')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('checkout',type=Path);parser.add_argument('destination',type=Path)
    a=parser.parse_args();archive(a.source.resolve(),a.checkout.resolve(),a.destination.resolve())


if __name__=='__main__': main()
