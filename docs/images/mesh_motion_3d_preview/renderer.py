"""Independent kinematic 3D Voronoi geometry illustration; run only on REANA.

No OpenMHD candidate state, fluid update, magnetic evolution or validation gate
is evaluated. This small floating-point clipping routine is a drawing utility.
"""
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import sys
import time

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MPLCONFIGDIR'] = '/tmp/openmhd-kinematic-preview-matplotlib'


def digest(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def dependency_preflight():
    import numpy
    import matplotlib
    from PIL import Image
    text = Path(__file__).read_bytes()
    compile(text, __file__, 'exec')
    Path('preflight.json').write_text(json.dumps({
        'status': 'ready_for_diagnostic_render', 'source': digest(text),
        'python': platform.python_version(), 'numpy': numpy.__version__,
        'matplotlib': matplotlib.__version__, 'pillow': Image.__version__,
        'diagnostic_only': True, 'tests_executed': 0,
        'candidate_solver_executed': False, 'component_accepted': False}, indent=2) + '\n')


def render():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgba
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
    from PIL import Image

    source = Path(__file__).read_bytes()
    preflight = json.loads(Path('preflight.json').read_bytes())
    if preflight['source'] != digest(source):
        raise ValueError('Renderer changed after dependency preflight')
    out = Path('outputs')
    out.mkdir(exist_ok=False)
    (out / 'renderer.py').write_bytes(source)
    started = time.time()
    initial = np.array([(x, y, z) for x in (.17, .5, .83)
                        for y in (.17, .5, .83) for z in (.17, .5, .83)])
    # A smooth, periodic prescribed path in all three axes. No RNG or fluid data.
    amplitudes = np.array([.068, .071, .063])
    phases = 2 * np.pi * np.column_stack((initial[:, 1] + .35 * initial[:, 2],
                                        initial[:, 2] + .4 * initial[:, 0],
                                        initial[:, 0] + .3 * initial[:, 1]))

    def seeds(t):
        return initial + amplitudes * (np.sin(2 * np.pi * t + phases) - np.sin(phases))

    box_faces = [
        [(0,0,0),(0,0,1),(0,1,1),(0,1,0)],
        [(1,0,0),(1,1,0),(1,1,1),(1,0,1)],
        [(0,0,0),(1,0,0),(1,0,1),(0,0,1)],
        [(0,1,0),(0,1,1),(1,1,1),(1,1,0)],
        [(0,0,0),(0,1,0),(1,1,0),(1,0,0)],
        [(0,0,1),(1,0,1),(1,1,1),(0,1,1)],
    ]

    def clip(faces, normal, offset):
        result, intersections = [], []
        for poly in faces:
            clipped = []
            for a, b in zip(poly, poly[1:] + poly[:1]):
                da, db = float(a @ normal - offset), float(b @ normal - offset)
                ina, inb = da <= 1e-11, db <= 1e-11
                if ina:
                    clipped.append(a)
                if ina != inb:
                    q = a + (b-a) * (da / (da-db))
                    clipped.append(q)
                    intersections.append(q)
            clean = []
            for point in clipped:
                if not clean or np.linalg.norm(point-clean[-1]) > 1e-10:
                    clean.append(point)
            if len(clean) > 2 and np.linalg.norm(clean[0]-clean[-1]) < 1e-10:
                clean.pop()
            if len(clean) >= 3:
                result.append(clean)
        cut = []
        for point in intersections:
            if all(np.linalg.norm(point-other) > 1e-9 for other in cut):
                cut.append(point)
        if len(cut) >= 3:
            center = np.mean(cut, axis=0)
            unit = normal / np.linalg.norm(normal)
            basis = np.eye(3)[int(np.argmin(np.abs(unit)))]
            u = np.cross(unit, basis)
            u /= np.linalg.norm(u)
            v = np.cross(unit, u)
            cut.sort(key=lambda p: math.atan2((p-center) @ v, (p-center) @ u))
            result.append(cut)
        return result

    def geometry(t):
        points = seeds(t)
        if not (np.isfinite(points).all() and np.min(points) > 0 and np.max(points) < 1):
            raise ValueError('Prescribed generators must remain inside the box')
        cells = []
        for i, p in enumerate(points):
            faces = [[np.array(q, dtype=float) for q in poly] for poly in box_faces]
            for j, q in enumerate(points):
                if i != j:
                    faces = clip(faces, q-p, .5 * float(q@q-p@p))
            if not faces:
                raise ValueError('Empty drawing cell')
            cells.append(faces)
        return points, cells

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'svg.fonttype': 'none', 'savefig.facecolor': '#f5f8fb'})
    blue, teal, orange = '#70b8d2', '#3b9f9b', '#ef8b54'

    def panel(ax, t, title):
        points, cells = geometry(t)
        edge_rows, face_rows, face_colors = [], [], []
        for i, faces in enumerate(cells):
            p0 = initial[i]
            # Remove a front corner so that the genuine interior cells are visible.
            if p0[0] > .6 and p0[1] < .6 and p0[2] > .6:
                continue
            highlighted = i == 13
            color = orange if highlighted else (teal if p0[2] < .4 else blue)
            alpha = .65 if highlighted else .11
            for polygon in faces:
                face_rows.append(polygon)
                face_colors.append(to_rgba(color, alpha))
                edge_rows.extend((a,b) for a,b in zip(polygon, polygon[1:] + polygon[:1]))
        ax.add_collection3d(Poly3DCollection(face_rows, facecolors=face_colors,
                                            edgecolors='none', zsort='average'))
        ax.add_collection3d(Line3DCollection(edge_rows, colors='#346780',
                                            linewidths=.62, alpha=.67))
        ax.scatter(*points.T, s=11, color='#17394d', depthshade=False, alpha=.9)
        ax.scatter(*points[13], s=32, color='#b84a28', depthshade=False)
        for i in (4, 10, 13, 16, 22):
            history = np.array([seeds(tau)[i] for tau in np.linspace(0, t, 12)])
            ax.plot(*history.T, color='#db713e', linewidth=1.5, alpha=.9)
        ax.set(xlim=(-.02,1.02), ylim=(-.02,1.02), zlim=(-.02,1.02))
        ax.set_box_aspect((1,1,1))
        ax.set_proj_type('ortho')
        ax.view_init(elev=24, azim=-58)
        ax.set_axis_off()
        ax.set_title(title, color='#17394d', fontsize=13, pad=0)

    figure = plt.figure(figsize=(15,6.2), facecolor='#f5f8fb')
    for k, (t, title) in enumerate(((0, 'Initial mesh'), (.25, 'Deformation'),
                                   (.5, 'Further motion')), 1):
        panel(figure.add_subplot(1,3,k,projection='3d'), t, title + f'   t = {t:.2f}')
    figure.suptitle('Moving Voronoi mesh in 3D', x=.065, ha='left', y=.965,
                   fontsize=24, weight='bold', color='#17394d')
    figure.text(.066,.87,'27 moving generators  /  shared polyhedral faces  /  fixed bounding box',
                color='#597381', fontsize=12)
    figure.text(.066,.075,'Orange trails show generator motion. A corner is cut away to reveal interior cells.',
                color='#597381', fontsize=10)
    figure.text(.066,.032,'KINEMATIC GEOMETRY PREVIEW  ·  prescribed motion; no fluid or magnetic evolution',
                color='#8b5a38', fontsize=10)
    figure.subplots_adjust(left=.025,right=.98,top=.84,bottom=.15,wspace=-.05)
    figure.savefig(out/'moving_mesh_3d.png',dpi=180)
    figure.savefig(out/'moving_mesh_3d.svg')
    plt.close(figure)

    frames = []
    for frame, t in enumerate(np.linspace(0, 1, 25)):
        figure = plt.figure(figsize=(7,7),facecolor='#f5f8fb')
        panel(figure.add_axes((.02,.12,.96,.78),projection='3d'), float(t), '')
        figure.text(.08,.94,'Moving mesh in 3D',fontsize=22,weight='bold',color='#17394d')
        figure.text(.08,.89,f'Prescribed generator motion   ·   t = {t:.2f}',fontsize=11,color='#597381')
        figure.text(.08,.05,'Kinematic preview · no fluid/MHD evolution',fontsize=10,color='#8b5a38')
        buffer = io.BytesIO()
        figure.savefig(buffer,format='png',dpi=105)
        plt.close(figure)
        buffer.seek(0)
        frames.append(Image.open(buffer).convert('RGB'))
    frames[0].save(out/'moving_mesh_3d.gif',save_all=True,append_images=frames[1:],
                   duration=110,loop=0,optimize=False)
    report = {'status':'complete','purpose':'independent kinematic visualization',
              'geometry':'Euclidean Voronoi cells clipped to the unit cube',
              'drawing_algorithm':'floating-point halfspace polygon clipping; diagnostic only',
              'source':digest(source),'python':sys.version,'numpy':np.__version__,
              'matplotlib':matplotlib.__version__,'pillow':Image.__version__,
              'visible_cpus':os.cpu_count(),'declared_resources':{'cpu':1,'memory':'2Gi'},
              'threads':1,'elapsed_seconds':time.time()-started,
              'generators':27,'frames':25,'motion':'specified smooth periodic paths in all three axes',
              'snapshot_times':[0,.25,.5],'initial_generators':initial.tolist(),
              'motion_amplitudes':amplitudes.tolist(),'motion_phases':phases.tolist(),
              'candidate_solver_executed':False,'fluid_evolution':False,
              'magnetic_evolution':False,'component_accepted':False}
    for name in ('cpu.max','memory.max'):
        path = Path('/sys/fs/cgroup')/name
        if path.exists():
            report[name] = path.read_text().strip()
    (out/'render.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    rows = {str(p):digest(p.read_bytes()) for p in sorted(out.iterdir()) if p.is_file()}
    (out/'artifacts.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps({'status':'complete','images':list(rows),'seconds':report['elapsed_seconds']}))


if __name__ == '__main__':
    if sys.argv[1:] == ['preflight']:
        dependency_preflight()
    elif sys.argv[1:] == ['render']:
        render()
    else:
        raise SystemExit('Specify preflight or render')
