#!/usr/bin/env python3
"""Plot the measured repeated-pattern controls and their actual Voronoi faces."""
import argparse
from collections import defaultdict
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
from matplotlib.collections import LineCollection
import matplotlib.pyplot as plt


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def mesh_panel(axis, path, title):
    geometry = rows(path/'geometry.csv')
    initial = rows(path/'initial.csv')
    faces = defaultdict(list)
    for r in rows(path/'stencils.csv'):
        faces[int(r['id'])].append(r)
    status = dict(line.split('=', 1) for line in (path/'status.txt').read_text().splitlines())
    length = float(status['length_y'])
    dx = 2/256
    origin_y = float(geometry[253]['cy'])
    limits = [-5.3, 1.4, -3., 3.]
    segments, special, points, values, labels = [], [], [], [], []
    for row, q in zip(geometry, initial):
        i = int(row['id'])
        for sx in [-2., 0., 2.]:
            for sy in [-length, 0., length]:
                x = (float(row['cx'])+sx-2)/dx
                y = (float(row['cy'])+sy-origin_y)/dx
                if not (limits[0]-1 < x < limits[1]+1 and limits[2]-4 < y < limits[3]+4):
                    continue
                points.append((x, y))
                values.append(float(q['by']))
                for face in faces[i]:
                    nx, ny = float(face['nx']), float(face['ny'])
                    half = .5*float(face['area'])/dx
                    fx, fy = x+float(face['face_dx'])/dx, y+float(face['face_dy'])/dx
                    segment = [(fx-half*ny, fy+half*nx), (fx+half*ny, fy-half*nx)]
                    segments.append(segment)
                    if i == 253 and int(face['neighbor_base']) in [254, 255]:
                        special.append(segment)
                if i in [253, 254, 255] and limits[0] < x < limits[1] and limits[2] < y < limits[3]:
                    labels.append((x,y,i,float(q['by'])))
    axis.add_collection(LineCollection(segments, colors='#777777', linewidths=.7))
    axis.add_collection(LineCollection(special, colors='#c33434', linewidths=2.2))
    cloud = axis.scatter([p[0] for p in points], [p[1] for p in points], c=values,
                         vmin=-1., vmax=1., cmap='coolwarm', s=28, edgecolors='black', linewidths=.35)
    for x,y,i,value in labels:
        axis.annotate(f'{i}\nBy={value:.3f}', (x,y), xytext=(4,5), textcoords='offset points',
                      fontsize=7, bbox=dict(facecolor='white', alpha=.85, edgecolor='none', pad=1))
    axis.axvline(0, color='black', ls=':', lw=1)
    axis.set(xlim=limits[:2], ylim=limits[2:], xlabel='(x − periodic seam) / Δx',
             ylabel='(y − centre of cell 253) / Δx', title=title)
    axis.set_aspect('equal', adjustable='box')
    return cloud


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fig = plt.figure(figsize=(12, 8), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[.85, 1.])
    history_axis = fig.add_subplot(grid[0, :])
    for name, label, color, style in [
            ('original', 'Stretched, 4 rows', '#b52f2f', '-'),
            ('repeat2', 'Same pattern ×2, 8 rows', '#c85b1d', '--'),
            ('repeat4', 'Same pattern ×4, 16 rows', '#86655a', ':'),
            ('compressed2', 'Compressed ×1/2, 4 rows', '#3983ac', '-'),
            ('compressed4', 'Compressed ×1/4, 4 rows', '#2d8a58', '-'),
            ('compressed4_repeat4', 'Compressed ×1/4, repeated ×4', '#7776b7', '--')]:
        history = rows(args.directory/name/'history.csv')
        history_axis.plot([float(r['time']) for r in history], [float(r['p_min']) for r in history],
                          label=label, color=color, ls=style, lw=1.8)
        if (args.directory/name/'failure.txt').exists():
            history_axis.plot(float(history[-1]['time']), float(history[-1]['p_min']), 'x', color=color, ms=8)
    history_axis.set(xlabel='Simulation time', ylabel='Minimum gas pressure', xlim=(0,.0102), ylim=(-.004,.108))
    history_axis.legend(ncol=3, fontsize=8, loc='upper right')
    history_axis.grid(alpha=.2)
    left, right = fig.add_subplot(grid[1, 0]), fig.add_subplot(grid[1, 1])
    mesh_panel(left, args.directory/'original', 'Original shape: cell 253 connects to 254 and 255')
    cloud = mesh_panel(right, args.directory/'compressed4', 'Compressed shape: connection 253–255 disappears')
    fig.colorbar(cloud, ax=[left,right], label='Initial cell-centred By', shrink=.85, pad=.02)
    fig.suptitle('Same perturbation pattern: repetition retains the failure, compression stabilizes the short run\nGeometry diagnostics only — original M1 and Bx gates remain unresolved', fontsize=12)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=170)
    plt.close(fig)


if __name__ == '__main__':
    main()
