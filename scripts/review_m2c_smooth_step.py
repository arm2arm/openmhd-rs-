"""Replay the small coupled M2c experiment from original REANA outputs (stdlib only)."""
import argparse
import gzip
import hashlib
import json
import math
import tarfile
from pathlib import Path

END = 1 / 32
BOOSTS = [(0, 0, 0), (2, -1, .5), (10, 7, -3)]
SUM = math.fsum


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def norm(v):
    return math.sqrt(SUM(x*x for x in v))


def delta(a, b):
    return [x-y for x, y in zip(a, b)]


def cell_oracle(case, n, i, t):
    field, motion, _, boost_index, _, _ = case
    boost = BOOSTS[int(boost_index)]
    u = [1+boost[0], .5+boost[1], -.25+boost[2]]
    idx = [i % n, i // n % n, i // n**2]
    def position(axis, p):
        shift, j = divmod(p, n)
        x = [.125, .4375, .8125][j] if n == 3 else (j+.5+[-.125,0,.125,0][(j+axis)%4])/n
        speed = 0 if motion == 'fixed' else u[axis]-boost[axis]
        if motion == 'deforming':
            speed = [-.125,.25,-.0625][axis]+[-.5,.375,.125,0][(j+axis)%n%4]
        return x+shift+t*(boost[axis]+speed)
    center, width = [], []
    for axis,j in enumerate(idx):
        left, here, right = [position(axis, k) for k in (j-1, j, j+1)]
        center.append((left+2*here+right)/4)
        width.append((right-left)/2)
    guide = 0 if field == 'advection' else .5
    amp = 0 if field == 'uniform' else .05
    phase = math.tau*(SUM(center)-t*(SUM(u)+math.sqrt(3)*guide))
    cc, ss = amp*math.cos(phase)/math.sqrt(2), amp*math.sin(phase)/math.sqrt(6)
    bpoint = [cc+ss,-cc+ss,-2*ss]
    sinc = math.prod(math.sin(math.pi*h)/(math.pi*h) for h in width)
    db = [sinc*v for v in bpoint]
    wave = field in ('alfven','low-beta')
    vel = [v-x*wave for v,x in zip(u,db)]
    pressure = .005*(guide**2+amp**2) if field=='low-beta' else 1.
    energy = 1.5*pressure+.5*(norm(u)**2+guide**2+amp**2)
    if wave:
        energy += .5*amp**2-SUM(v*b for v,b in zip(u,db))
    vol = math.prod(width)
    return dict(volume=vol, position=center, width=width, q=[vol*v for v in [1,*vel,energy]],
                b=[v+guide/math.sqrt(3) for v in db], a=[-v/(math.tau*math.sqrt(3)) for v in bpoint])


def field_rms(cells, reference):
    return math.sqrt(SUM(c['volume']*SUM(x*x for x in delta(c['b'],r['b'])) for c,r in zip(cells,reference)))


def decode(case, raw):
    fields, motion, ns, bs, size, _ = case['args']
    steps,n,bi = int(ns),int(size),int(bs)
    group = {}
    for line in raw.decode('ascii').splitlines():
        tag,*words = line.split()
        row = [float(x) for x in words]
        require(all(math.isfinite(x) for x in row), 'nonfinite native output')
        group.setdefault(tag,[]).append(row)
    require(set(group)=={'INITIAL','FINAL','STAGE','CELL_LEDGER','GAUGE'},'output inventory')
    snapshots=[]; analytic=[]; geom=0.
    for tag,t in [('INITIAL',0.),('FINAL',END)]:
        cells=[]; exact=[]
        require(len(group[tag])==n**3,'cell count')
        for i,r in enumerate(group[tag]):
            require(r[0]==i and len(r)==36, 'ordered cell schema')
            ref=cell_oracle(case['args'],n,i,t)
            v,center,q,a,phi,b,rho,p=r[1],r[2:5],r[5:10],r[10:13],r[13],r[14:17],r[17],r[18]
            require(max(map(abs,delta(r[19:24],ref['q'])+delta(r[24:27],ref['b'])+
                    delta(r[27:30],ref['position'])+delta(r[30:33],ref['width'])) )<3e-13,'independent analytic words')
            geom=max(geom, abs(v/ref['volume']-1), max(map(abs,delta(center,ref['position']))))
            require(abs(rho-q[0]/v)<1e-12,'density vs mass')
            thermal=q[4]/v-SUM(x*x for x in q[1:4])/(2*q[0]*v)-.5*SUM(x*x for x in b)
            require(abs(p-(2/3)*thermal)<2e-12,'independent thermal closure')
            if tag=='INITIAL':
                require(max(map(abs,delta(q,ref['q'])+delta(a,ref['a'])+[phi]))<3e-14,'analytic initial Q/A')
            cells.append(dict(volume=v,position=center,q=q,a=a,phi=phi,b=b,rho=rho,p=p,div=r[33:36]))
            exact.append(ref)
        snapshots.append(cells);analytic.append(exact)
    start,end=snapshots
    def summed(c,k):return SUM(row['q'][k] for row in c)
    mass,energy=summed(start,0),summed(start,4)
    scales=[mass,*[mass*math.sqrt(2*energy/mass)]*3,energy]
    budget=max(abs(summed(start,k)-summed(end,k))/scale for k,scale in enumerate(scales))
    guide=0 if fields=='advection' else .5
    mean=[guide/math.sqrt(3)]*3
    scale=guide+.05
    actual_mean=lambda c:[SUM(a['volume']*a['b'][j] for a in c)/SUM(a['volume'] for a in c) for j in range(3)]
    mean_error=max(abs(x)/scale for c in snapshots for x in delta(actual_mean(c),mean))
    stages=group['STAGE'];require(len(stages)==2*steps,'stage count')
    stages_min_rho=math.inf; stages_min_p=math.inf; gcl=0.; residual=0.; peak_iter=0;stage_time_error=0.
    totals=[[] for _ in range(3)]; unsigned=[[] for _ in range(3)]
    for j,s in enumerate(stages):
        require(len(s)==20 and s[:2]==[j//2,j%2] and s[3]>=END/steps and s[10] in (1,2,4),'stage schema/CFL')
        stage_time_error=max(stage_time_error,abs(s[2]-(j//2+1)*END/steps))
        gcl=max(gcl,s[4]);peak_iter=max(peak_iter,int(s[5]))
        residual=max(residual,s[7]);stages_min_rho=min(stages_min_rho,s[8]);stages_min_p=min(stages_min_p,s[9])
        mean_error=max(mean_error,max(abs(x)/scale for x in delta(s[11:14],mean)))
        for k in range(3):
            require(s[17+k]+1e-15>=abs(s[14+k]),'unsigned partition')
            if j%2:
                totals[k].append(s[14+k]); unsigned[k].append(s[17+k])
    def magnetic(c):
        return SUM(.5*r['volume']*SUM(v*v for v in r['b']) for r in c)
    eb=magnetic(start)
    energy_partition=abs(magnetic(end)-eb-SUM(SUM(values) for values in totals))/eb
    require(len(group['CELL_LEDGER'])==2*n**3,'last-step per-cell ledger')
    mismatches=[]
    for j,r in enumerate(group['CELL_LEDGER']):
        require(len(r)==8 and r[:2]==[j//(n**3),j%(n**3)],'cell ledger identity')
        if r[0]==1:
            cell=end[int(r[1])]
            mismatches.append(cell['volume']*norm(delta(r[5:8],cell['b']))**2)
    require(len(group['GAUGE'])==1 and len(group['GAUGE'][0])==9,'constant gauge/origin')
    u=[1+BOOSTS[bi][0],.5+BOOSTS[bi][1],-.25+BOOSTS[bi][2]]
    k_ref=[END*(u[(j+1)%3]*mean[(j+2)%3]-u[(j+2)%3]*mean[(j+1)%3]) for j in range(3)]
    require(max(map(abs,delta(group['GAUGE'][0][:3],k_ref)))<1e-12,'constant gauge advance')
    minp=min(stages_min_p,min(c['p'] for c in start+end))
    rho=min(stages_min_rho,min(c['rho'] for c in start+end))
    uni=0.
    if fields=='uniform':
        for c in end:
            uni=max(uni,abs(c['rho']-1.),abs(c['p']-1.),*map(abs,delta(c['b'],mean)),
                    *[abs(c['q'][j+1]/c['q'][0]-u[j]) for j in range(3)])
    div=[math.sqrt(SUM(c['volume']*c['div'][j]**2 for c in end)) for j in range(3)]
    metrics=dict(steps=steps,n=n,mean_error=mean_error,gas_budget=budget,gcl=gcl,normal_residual=residual,
                 max_iterations=peak_iter,min_pressure=minp,min_density=rho,geometry_error=geom,uniform_drift=uni,
                 partition_residual=energy_partition,signed_transfer=[SUM(x) for x in totals],
                 absolute_transfer=[SUM(x) for x in unsigned],initial_EB=eb,final_EB=magnetic(end),
                 finite_target_rms=math.sqrt(SUM(mismatches)),divergence_rms=div,
                 initial_analytic_field_rms=field_rms(start,analytic[0]),final_analytic_field_rms=field_rms(end,analytic[1]))
    metrics['checks_pass']=(mean_error<=1e-9 and budget<=1e-10 and gcl<=1e-12 and residual<=1e-9 and
                            minp>0 and rho>0 and geom<=1e-12 and uni<=1e-10 and energy_partition<=1e-10
                            and stage_time_error<=1e-13)
    return metrics,end


def reduce(packet):
    with tarfile.open(packet) as ar:
        require(all(m.isfile() for m in ar),'regular receipt files')
        bodies={m.name:ar.extractfile(m).read() for m in ar.getmembers()}
        require(len(bodies)==len(ar.getmembers()),'unique packet members')
    data=lambda n:json.loads(bodies[n])
    plan=data('plan.json'); build=data('build/build.json')
    require(build['source']==plan['source'] and sha(bodies['build/build.json'])==plan['build_sha256'],'source and build')
    parent=data('build/terminal.json')
    require(parent['status']=='finished' and parent['id']==plan['parent'] and parent['version']==1,'parent identity')
    require(len(build['commands'])==4 and all(x['returncode']==0 and x['sha256']==sha(bodies[f'build/build-{i}.log']) for i,x in enumerate(build['commands'])),'four build gates')
    endpoints={}; results={}; controls={}; workflows={}; runtime={}
    for k,c in plan['cases'].items():
        get=lambda p:data(f'{k}/{p}')
        result=get('result.json');service=get('service.json');terminal=get('terminal.json')
        require(result['case']==c and c['source']==plan['source'] and c['parent']==parent['id'] and terminal['version']==1 and
                terminal['status']=='finished' and terminal['id']==service['uuid'] and c['program_sha256']==build['programs'][c['program']]['sha256'],'case/source/workflow join '+k)
        require(terminal['workflow']==service['workflow'] and sha(bodies[f'{k}/reana.yaml'])==service['spec']
                and sha(bodies[f'{k}/inputs.json'])==service['inputs'],'input identity '+k)
        for name,entry in service['outputs'].items():
            body=bodies[f'{k}/{name}']
            require(sha(body)==entry['sha256'] and len(body)==entry['bytes'],'original output '+k)
        raw=gzip.decompress(bodies[f'{k}/stdout.gz'])
        require(result['complete'] and result['returncode']==0 and result['stdout_sha256']==sha(raw)
                and result['stderr_sha256']==sha(bodies[f'{k}/stderr.txt']),'native completion '+k)
        workflows[k]=terminal['id'];runtime[k]=result['seconds']
        if c['kind']=='test':
            selector=c['args'][1]
            require(selector in build['programs'][c['program']]['selectors'] and ('test '+selector+' ... ok').encode() in raw and b'test result: ok. 1 passed;' in raw,'unit '+k)
            controls[k]=selector
        else:
            results[k],endpoints[k]=decode(c,raw)
    require(len(set(workflows.values()))==len(workflows),'unique workflows')
    def label(field,steps,boost=0,size=3,threads=2):
        return f'{field}-deforming-n{size}-s{steps}-b{boost}-t{threads}'
    pairs={}
    for field in ['uniform','advection','alfven','low-beta']:
        for bi in (1,2):
            ca=label(field,16);cb=label(field,16,bi);B=BOOSTS[bi]
            a=endpoints[ca];b=endpoints[cb]
            max_q=max_p=max_field=0.
            for l,r in zip(a,b):
                q=r['q'];q0=[q[0],*[q[j+1]-q[0]*B[j] for j in range(3)],
                                  q[4]-SUM(q[j+1]*B[j] for j in range(3))+.5*q[0]*SUM(x*x for x in B)]
                max_q=max(max_q,max(abs(x) for x in delta(l['q'],q0))/l['volume'])
                max_p=max(max_p,abs(l['rho']-r['rho']),abs(l['p']-r['p']))
                max_field=max(max_field,norm(delta(l['b'],r['b']))/(.5 if field=='uniform' else .05))
            pairs[cb]=dict(max_field_over_amplitude=max_field,max_gas_density_components=max_q,max_primitive=max_p,
                           checks_pass=max(max_field,max_q,max_p)<=1e-8)
    key1=label('advection',16,threads=1);key2=label('advection',16)
    threads=data(key1+'/result.json')['stdout_sha256']==data(key2+'/result.json')['stdout_sha256']
    temporal={}
    for n in (8,16,32,64,128):
        temporal[n]=field_rms(endpoints[label('advection',n)],endpoints[label('advection',2*n)])
    orders=[math.log2(temporal[n]/temporal[2*n]) for n in (8,16,32,64)]
    return dict(source=plan['source'],protocol=plan['protocol'],build_uuid=parent['id'],workflows=workflows,
                controls=controls,physics=results,boosts=pairs,thread_outputs_identical=threads,
                field_step_halving_rms=temporal,step_halving_orders=orders,runtime_seconds=runtime,
                scoped_checks_pass=all(v['checks_pass'] for v in list(results.values())+list(pairs.values())) and threads and min(orders)>=1.8,
                m2c_accepted=False)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('packet',type=Path);ap.add_argument('output',type=Path)
    args=ap.parse_args();summary=reduce(args.packet)
    args.output.write_text(json.dumps(summary,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print('physics', len(summary['physics']), 'controls',len(summary['controls']), 'scoped checks',summary['scoped_checks_pass'])

