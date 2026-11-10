"""Plot independently verified primary shock profiles and reference ladders."""
from pathlib import Path
import gzip
import hashlib
import io
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sha = lambda data: hashlib.sha256(data).hexdigest()


def main():
    report = json.loads((HERE/'independent_reference.json').read_text())
    assert sha((HERE/'reduce_reference.py').read_bytes()) == report['analysis_source_sha256']
    assert sha(gzip.decompress((HERE/'runs_checkpoint.json.gz').read_bytes())) == report['run_map_sha256']
    path = ROOT/'tests/reference/external_mhd/brio_8192.csv.gz'
    assert sha(path.read_bytes()) == report['reference_sha256']
    reference = np.genfromtxt(io.BytesIO(gzip.decompress(path.read_bytes())), names=True, delimiter=',')
    packet = ROOT/'benchmarks/m0/packet.json'
    assert sha(packet.read_bytes()) == report['packet_sha256']
    limits = json.loads(packet.read_text())['cases']['brio-wu']['gate']['finest_scaled_L1_max']
    fields = ('rho', 'p', 'vx', 'by')
    labels = ('Density', 'Pressure', 'Velocity vx', 'Magnetic By')
    fig, axes = plt.subplots(2, 4, figsize=(14.8, 7.3), layout='constrained')
    colors = {'regular': '#2676b9', 'columns': '#c58421'}
    used = {}
    for family, suffix in (('regular', 'j0.0'), ('columns', 'j0.15c')):
        name = 'brio-wu_n1024_'+suffix+'_base'
        data_bytes = gzip.decompress((HERE/'snapshots'/name/'final.csv.gz').read_bytes())
        assert sha(data_bytes) == report['input_sha256'][name+'/final.csv']
        used[name+'/final.csv'] = sha(data_bytes)
        data = np.genfromtxt(io.BytesIO(data_bytes), names=True, delimiter=',')
        assert len(data) == 4096 and np.array_equal(data['id'], np.arange(4096))
        for col, field in enumerate(fields):
            for row in range(4):
                cells = data[row*1024:(row+1)*1024]
                assert np.ptp(cells['y']) < 1e-12
                axes[0, col].plot(cells['x'], cells[field], color=colors[family],
                                  lw=.9, alpha=.7, label=family.capitalize()+' N1024' if row == 0 else None)
            ladder = sorted([r for r in report['measured'].values()
                             if r['family'] == family and r['frame'] == 'base'], key=lambda r: r['resolution'])
            axes[1, col].loglog([r['resolution'] for r in ladder],
                                [r['reference_errors'][field]['L1'] for r in ladder],
                                '-o', color=colors[family], markersize=4, label=family.capitalize())
    for col, (field, label) in enumerate(zip(fields, labels)):
        axes[0, col].plot(reference['x'], reference[field], color='#222222', lw=1.,
                          ls='--', label='Athena++ N8192')
        axes[0, col].set(xlim=(.5, 1.5), xlabel='x', title=label)
        axes[1, col].axhline(limits[field], color='#555555', ls='--', lw=.9, label='Finest-grid limit')
        axes[1, col].set(xlabel='Nx', ylabel='Scaled reference L1', ylim=(.001, .06))
        axes[1, col].set_xticks([256, 512, 1024], labels=['256', '512', '1024'])
        axes[1, col].xaxis.set_minor_locator(NullLocator())
        for row in range(2):
            axes[row, col].grid(alpha=.18)
    axes[0, 0].legend(fontsize=7.5)
    axes[1, 0].legend(fontsize=8)
    fig.suptitle('Pressure-blend Brio–Wu at t=0.1: primary reference and refinement checks pass\n'
                 'All four physical rows shown; lower norms use independent rectangular-cell reference integration', fontsize=13)
    fig.supxlabel('Regular and column meshes carry the registered profile gates. Planar jitter is separate; full M1 remains pending.', fontsize=9)
    image = ROOT/'docs/images/m1_completion/pressure_shock_reference.png'
    fig.savefig(image, dpi=170)
    plt.close(fig)
    provenance = dict(scope=__doc__, script_sha256=sha(Path(__file__).read_bytes()),
                      independent_report_sha256=sha((HERE/'independent_reference.json').read_bytes()),
                      reference_sha256=report['reference_sha256'], inputs=used,
                      plot_sha256=sha(image.read_bytes()), numpy=np.__version__, matplotlib=matplotlib.__version__)
    (HERE/'plot_provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')


if __name__ == '__main__':
    main()
