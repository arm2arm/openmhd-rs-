#!/usr/bin/env python3
"""Figure of the issue #26 limiter controls (read-only; no evolution).

Left and middle: observed B L1 order per refinement step from controls.json,
on the regular and the jittered mesh, with the unchanged 1.8 requirement.
Right: where the N256 distortion (By without its mean and fundamental) sits
on the regular mesh, from two hash-checked snapshots. Colour is the state of
the A-transport limiter; marker shape is the primitive limiter. The tables in
README.md carry every plotted number.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
NAME = 'alfven_bulk-frame-heun-quadratic-v1_v1.0_j0.0_fixed_n256_base'
# Validated categorical slots 1-3 on the light chart surface (see the dataviz palette check in README).
DEFAULT, OFF, CANDIDATE = '#2a78d6', '#eb6834', '#1baf7a'
SURFACE, INK, SECONDARY, MUTED, GRID, AXIS = '#fcfcfb', '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7'
PX = .72  # points per logical pixel at 100 logical pixels per inch
SERIES = [  # label in controls.json, colour, marker, legend text
    ('baseline', DEFAULT, 'o', 'default A limiter (baseline)'),
    ('primitive-unlimited', DEFAULT, 's', 'default A limiter, primitives unlimited'),
    ('potential-none', OFF, 'o', 'A limiter off'),
    ('all-unlimited', OFF, 's', 'A limiter off, primitives unlimited'),
    ('smooth-extrema', CANDIDATE, 'D', 'candidate smooth-extrema'),
]
STEPS = ('32-64', '64-128', '128-256')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distortion(path):
    """Column profile of By without its volume-weighted mean and fundamental."""
    with path.open() as stream:
        cells = [{k: float(row[k]) for k in ('x', 'volume', 'by')} for row in csv.DictReader(stream)]
    phase = lambda q: math.tau*q['x']
    sine = 2*math.fsum(q['volume']*q['by']*math.sin(phase(q)) for q in cells)
    cosine = 2*math.fsum(q['volume']*q['by']*math.cos(phase(q)) for q in cells)
    mean = math.fsum(q['volume']*q['by'] for q in cells)
    columns = {}
    for q in cells:
        residual = q['by']-mean-sine*math.sin(phase(q))-cosine*math.cos(phase(q))
        columns.setdefault(round(q['x'], 12), []).append(residual)
    xs = sorted(columns)
    return xs, [math.fsum(columns[x])/len(columns[x]) for x in xs]


def style(axis):
    axis.set_facecolor(SURFACE)
    for side in ('top', 'right', 'left'):
        axis.spines[side].set_visible(False)
    axis.spines['bottom'].set_color(AXIS)
    axis.spines['bottom'].set_linewidth(PX)
    axis.tick_params(colors=MUTED, labelsize=11*PX, length=0, pad=6*PX)
    axis.grid(axis='y', color=GRID, linewidth=PX, linestyle='-')
    axis.set_axisbelow(True)


def orders(axis, controls, jitter, title, labelled):
    style(axis)
    drawn = {}
    # The candidate coincides with "A limiter off": an open diamond around that point keeps both visible.
    for label, colour, marker, _ in SERIES:
        ladder = next(l for l in controls['configurations'][label]['ladders']
                      if l['jitter'] == jitter and l['frame'] == 'base')
        points = [(i, ladder['successive_B_L1'][s]) for i, s in enumerate(STEPS) if s in ladder['successive_B_L1']]
        if not points:
            continue
        if label == 'smooth-extrema':
            axis.plot(*zip(*points), linewidth=0, marker=marker, markersize=16*PX, markerfacecolor='none',
                      markeredgecolor=colour, markeredgewidth=2*PX, zorder=4, clip_on=False)
        else:
            axis.plot(*zip(*points), color=colour, linewidth=2*PX, marker=marker, markersize=8*PX,
                      markeredgecolor=SURFACE, markeredgewidth=2*PX, solid_capstyle='round',
                      solid_joinstyle='round', zorder=3, clip_on=False)
        drawn[label] = points
    axis.axhline(1.8, color=SECONDARY, linewidth=PX, zorder=1)
    # The requirement label goes where no series crosses it: right on the regular mesh, left on the jittered one.
    side = dict(xy=(2.25, 1.8), ha='right') if labelled else dict(xy=(-.25, 1.8), ha='left')
    axis.annotate('required: at least 1.8', xytext=(0, 3), textcoords='offset points', color=SECONDARY,
                  fontsize=11*PX, va='bottom', **side)
    if labelled:  # Direct labels only where the two groups are well apart; the legend names every series.
        # The upper label sits left of the candidate's diamond, which shares that end point.
        for label, text, offset in (('baseline', 'default A limiter', (0, -14)),
                                    ('potential-none', 'A limiter off and candidate', (-14, 11))):
            x, y = drawn[label][-1]
            axis.annotate(text, (x, y), xytext=offset, textcoords='offset points', color=INK,
                          fontsize=11*PX, ha='right', va='center')
    axis.set_xlim(-.3, 2.3)
    axis.set_ylim(1.45, 2.05)
    axis.set_xticks(range(3), ['32 to 64', '64 to 128', '128 to 256'])
    axis.set_yticks([1.5, 1.6, 1.7, 1.8, 1.9, 2.0])
    axis.set_title(title, color=INK, fontsize=12*PX, loc='left', pad=10*PX)
    axis.set_xlabel('refinement step (cells per side)', color=SECONDARY, fontsize=12*PX, labelpad=6*PX)
    return drawn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controls', type=Path, default=HERE/'controls.json')
    parser.add_argument('--baseline-raw', type=Path, required=True, help='waves directory of the stopped campaign')
    parser.add_argument('--none-plan', type=Path, required=True, help='fan-out plan directory of the none ladder')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--provenance', type=Path, required=True)
    args = parser.parse_args()
    controls = json.loads(args.controls.read_text())
    snapshots = {'baseline': args.baseline_raw/NAME/'final.csv', 'potential-none': args.none_plan/'raw'/NAME/'final.csv'}
    for label, path in snapshots.items():
        row = next(r for l in controls['configurations'][label]['ladders'] if l['jitter'] == 0. and l['frame'] == 'base'
                   for r in l['rows'] if r['n'] == 256)
        if sha(path) != row['final_sha256']:
            raise ValueError('Snapshot differs from the reduced one: '+label)

    plt.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['Helvetica Neue', 'Arial', 'DejaVu Sans'],
                         'svg.fonttype': 'none'})
    figure, (left, middle, right) = plt.subplots(1, 3, figsize=(13.2, 4.9), dpi=100, facecolor=SURFACE,
                                                 gridspec_kw=dict(width_ratios=[1, 1, 1.3], wspace=.22))
    drawn = {'regular': orders(left, controls, 0., 'Regular mesh', True),
             'jitter .15': orders(middle, controls, .15, 'Jittered mesh (.15)', False)}
    left.set_ylabel('observed order of the B L1 error', color=SECONDARY, fontsize=12*PX, labelpad=8*PX)
    middle.tick_params(labelleft=False)

    style(right)
    profiles = {label: distortion(path) for label, path in snapshots.items()}
    for label, colour in (('baseline', DEFAULT), ('potential-none', OFF)):
        xs, values = profiles[label]
        right.plot(xs, [1e4*v for v in values], color=colour, linewidth=2*PX, solid_capstyle='round',
                   solid_joinstyle='round', zorder=3)
    peak = max(abs(v) for v in profiles['baseline'][1])*1e4
    for x in (0., .5, 1.):
        right.axvline(x, color=GRID, linewidth=PX, zorder=1)
    right.annotate('extrema of Az: x = 0, .5, 1', (.5, peak*1.12), xytext=(6, 0), textcoords='offset points',
                   color=MUTED, fontsize=11*PX, ha='left', va='bottom')
    right.annotate('default A limiter', (.515, -peak*.82), xytext=(8, 0), textcoords='offset points', color=INK,
                   fontsize=11*PX, ha='left', va='center')
    right.annotate('A limiter off', (.25, 0), xytext=(0, 7), textcoords='offset points', color=INK,
                   fontsize=11*PX, ha='center', va='bottom')
    right.set_xlim(0, 1)
    right.set_ylim(-peak*1.3, peak*1.3)
    right.set_xticks([0, .25, .5, .75, 1], ['0', '.25', '.5', '.75', '1'])
    right.set_title('Where the N256 error sits (regular mesh)', color=INK, fontsize=12*PX, loc='left', pad=10*PX)
    right.set_xlabel('position x', color=SECONDARY, fontsize=12*PX, labelpad=6*PX)
    right.set_ylabel('By distortion (units of 0.0001)', color=SECONDARY, fontsize=12*PX, labelpad=8*PX)

    handles = [plt.Line2D([], [], linewidth=0, marker=marker, markersize=12*PX, markerfacecolor='none',
                          markeredgecolor=colour, markeredgewidth=2*PX, label=text) if label == 'smooth-extrema'
               else plt.Line2D([], [], color=colour, marker=marker, linewidth=2*PX, markersize=8*PX,
                               markeredgecolor=SURFACE, markeredgewidth=PX, label=text)
               for label, colour, marker, text in SERIES]
    legend = figure.legend(handles=handles, loc='lower center', ncol=5, frameon=False, fontsize=11*PX,
                           handlelength=2.2, columnspacing=1.8, bbox_to_anchor=(.5, .005))
    for text in legend.get_texts():
        text.set_color(SECONDARY)
    figure.suptitle('Fixed-mesh standing Alfvén wave: convergence with and without the limiter on the A transport gradients',
                    x=.06, y=.975, ha='left', color=INK, fontsize=14*PX, fontweight='semibold')
    figure.subplots_adjust(left=.06, right=.985, top=.83, bottom=.22)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=200, facecolor=SURFACE)
    record = dict(scope='Read-only plot of reduced controls; diagnostic, not acceptance.',
                  script_sha256=sha(Path(__file__)), controls_sha256=sha(args.controls),
                  snapshots_sha256={label: sha(path) for label, path in snapshots.items()},
                  image_sha256=sha(args.output), matplotlib=matplotlib.__version__,
                  plotted_orders={mesh: {label: [[STEPS[i], value] for i, value in points]
                                         for label, points in series.items()} for mesh, series in drawn.items()},
                  distortion_peak={label: max(abs(v) for v in values) for label, (_, values) in profiles.items()},
                  palette=dict(default_A_limiter=DEFAULT, A_limiter_off=OFF, candidate=CANDIDATE, surface=SURFACE))
    args.provenance.write_text(json.dumps(record, indent=1, allow_nan=False)+'\n')
    print('wrote', args.output, args.provenance)


if __name__ == '__main__':
    main()
