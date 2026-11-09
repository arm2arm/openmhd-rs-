#!/usr/bin/env python3
"""Read-only configuration/command cross-check for a completed spatial wave matrix."""
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);runs=json.loads((root/'runs.json').read_text());manifest=json.loads((root/'manifest.json').read_text())
names=[n for n in manifest if n.startswith('alfven_')];assert len(names)==64
for name in names:
    r=runs[name];c=r['config'];s=r['summary'];assert c==manifest[name] and c['name']==name
    suffix='boost' if name.endswith('_boost') else 'base';boost=[2.,-1.,0.] if suffix=='boost' else [0.,0.,0.]
    assert name==f"alfven_{c['profile']}_v{c['parallel']}_j{c['jitter']}_{c['motion_family']}_n{c['n']}_{suffix}"
    assert c['n'] in (32,64,128,256) and c['jitter'] in (0.,.15) and c['parallel'] in (0.,1.) and c['motion_family'] in ('fixed','comoving')
    assert c['case']=='alfven' and c['dt'] is None and c['target']==1. and c['boost']==boost
    mesh=[c['parallel'],0.] if c['motion_family']=='comoving' else [0.,0.]
    assert c['mesh_velocity']==[a+b for a,b in zip(mesh,boost)]
    for ck,sk in [('n','n'),('jitter','jitter'),('parallel','parallel_velocity'),('profile','profile'),('boost','boost'),('mesh_velocity','mesh_velocity')]:assert c[ck]==s[sk]
    command=r['command'];assert len(command)%2==1 and len(set(command[1::2]))==len(command[1::2]);options=dict(zip(command[1::2],command[2::2]))
    assert Path(command[0]).resolve()==(root.parent.parent/'target/release/vector-potential').resolve()
    assert options['--case']=='alfven' and options['--profile']==c['profile'] and options['--motion']=='rigid' and '--dt' not in options
    assert int(options['--n'])==c['n'] and float(options['--jitter'])==c['jitter'] and float(options['--parallel-velocity'])==c['parallel']
    assert float(options['--time'])==1. and float(options['--checkpoint'])==.25
    assert [float(options['--boost-'+k]) for k in ('x','y','z')]==boost
    assert [float(options['--mesh-'+k]) for k in ('x','y')]==c['mesh_velocity']
    assert Path(options['--output']).resolve()==(root/name).resolve()
    assert r['status']=='completed' and r['returncode']==0 and s['completed'] and s['time']==1.
print('All64 spatial wave names/configs/summaries/commands agree, including velocities, geometry labels, target and checkpoint times; no timestep override.')
