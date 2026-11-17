"""Read-only reduction of completed REANA snapshots; no workflow mutations."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import json
import math
import shutil
import subprocess

root = Path('results/reana_remote_m1_pressure_reuse_20261110')
remote = Path('source/results/reana_m1-campaign/waves')
raw = root / remote
runs = json.loads((raw/'runs.json').read_text())
manifest = json.loads((raw/'manifest.json').read_text())
names = [f'alfven_bulk-frame-heun-quadratic-v1_v1.0_j{j}_fixed_n{n}_base'
         for j in (0., .15) for n in (32, 64, 128, 256)]


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fetch(name):
    expected = runs[name]['sha256']['final.csv']
    destination = raw/name/'final.csv'
    if destination.exists() and sha(destination) == expected:
        return
    cached = root/'source/results/reana_m1-campaign/bounded/waves_medium'/name/'final.csv'
    if cached.exists() and sha(cached) == expected:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cached, destination)
        return
    for attempt in range(3):
        result = subprocess.run(['python3', '/tmp/openmhd-reana-command.py', 'download',
                                 '-w', 'openmhd-m1-pressure-reuse-20261110.1', '-o', str(root),
                                 str(remote/name/'final.csv')],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=180)
        if result.returncode == 0 and destination.exists() and sha(destination) == expected:
            return
    raise RuntimeError('Unverified snapshot download: '+name)


with ThreadPoolExecutor(max_workers=4) as pool:
    for _ in pool.map(fetch, names):
        pass
print('All eight snapshot hashes verified.', flush=True)
cases = {}
for name in names:
    run = runs[name]
    config = run['config']
    assert config == manifest[name]
    assert run['status'] == 'completed' and run['positive_and_conservative']
    assert config['profile'] == run['summary']['profile'] == 'bulk-frame-heun-quadratic-v1'
    assert config['riemann_solver'] == 'hlld-pressure'
    assert run['summary']['riemann_solver'] == 'hlld-pressure-blend-v1'
    assert run['summary']['projection_screening'] == 1.
    assert config['parallel'] == 1. and config['boost'] == [0., 0., 0.]
    assert config['target'] == 1. and config['motion_family'] == 'fixed'
    volumes, weighted, squared, absolute = [], [], [], []
    with (raw/name/'final.csv').open() as stream:
        for index, row in enumerate(csv.DictReader(stream)):
            assert int(row['id']) == index and float(row['time']) == config['target']
            x, volume, bx, by, bz = (float(row[k]) for k in ('x', 'volume', 'bx', 'by', 'bz'))
            assert all(math.isfinite(value) for value in (x, volume, bx, by, bz))
            assert volume > 0 and float(row['rho']) > 0 and float(row['p']) > 0
            angle = math.tau*(x+(1-config['parallel']-config['boost'][0])*config['target'])
            error = math.sqrt((bx-1.)**2 + (by-.1*math.sin(angle))**2 + (bz-.1*math.cos(angle))**2)
            volumes.append(volume)
            weighted.append(volume*error)
            squared.append(volume*error**2)
            absolute.append(error)
    assert len(volumes) == config['n']**2
    volume = math.fsum(volumes)
    assert abs(volume-1.) < 1e-10
    norms = dict(L1=math.fsum(weighted)/volume, L2=math.sqrt(math.fsum(squared)/volume), max=max(absolute))
    difference = max(abs(norms[key]-run['errors']['final']['B'][key]) for key in norms)
    assert difference < 2e-13, (name, difference)
    cases[name] = dict(n=config['n'], final_sha256=run['sha256']['final.csv'], B_errors=norms,
                       production_norm_disagreement=difference, elapsed_seconds=run['seconds'])
ladders = []
for jitter in (0., .15):
    family = [f'alfven_bulk-frame-heun-quadratic-v1_v1.0_j{jitter}_fixed_n{n}_base' for n in (32, 64, 128, 256)]
    errors = [cases[name]['B_errors']['L1'] for name in family]
    order = math.log(errors[1]/errors[3])/math.log(4)
    row = dict(jitter=jitter, names=family, B_L1=errors, finest_three_order=order,
               minimum_required_order=1.8, finest_relative_B_L1=errors[-1]/.1,
               maximum_allowed_relative_B_L1=.02,
               spatial_gate_passed=order >= 1.8 and errors[-1]/.1 <= .02)
    ladders.append(row)
    print(json.dumps(row), flush=True)
report = dict(checked_utc=datetime.now(timezone.utc).isoformat(), workflow='openmhd-m1-pressure-reuse-20261110.1',
              run_map_sha256=sha(raw/'runs.json'), manifest_sha256=sha(raw/'manifest.json'),
              reduction_script_sha256=sha(Path(__file__)),
              scope='Independent CSV/stdlib reduction of the two completed fixed-mesh standing-wave base ladders only. No production error routine imported, no new test/evolution, no workflow stop or restart. All other acceptance requirements remain separate.',
              cases=cases, ladders=ladders, verified_required_failure=any(not row['spatial_gate_passed'] for row in ladders),
              full_m1_accepted=False)
(root/'standing_wave_gate_check_20261111.json').write_text(json.dumps(report, indent=2)+'\n')
