#!/usr/bin/env python3
"""Render actual exported static3D face edges; execution belongs on REANA.

This diagnostic introduces no Voronoi reconstruction, trajectories, interpolation,
fluid state or acceptance decision. It consumes an original literal input and
the corresponding complete Rust transcript through the source-pinned bridge.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import struct
import sys
import types

BRIDGE_SHA256 = 'bbb5f5d0603d665ac1f0904741bc868953a047418711e6c98280636c08a03c16'
MAX_EDGES = 100000
MAX_INPUT_BYTES = 128 * 1024
MAX_TRANSCRIPT_BYTES = 16 * 1024 * 1024
PALETTE = ('#176b91', '#b54c3b', '#347c5b', '#8a5ca1', '#9a711b', '#387d8c')


def require(value, message):
    if not value:
        raise ValueError(message)


def descriptor(raw):
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def read_bounded(path, limit):
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, 'Input exceeds diagnostic rendering limit')
    return raw


def load_bridge(path):
    raw = read_bounded(path, 1024 * 1024)
    require(descriptor(raw)['sha256'] == BRIDGE_SHA256, 'Exact reviewed geometry bridge source')
    # Execute precisely the held bytes, rather than reading the source again
    # through a module loader. This executes only in an authorized REANA render.
    module = types.ModuleType('geometry3_diagnostic_bridge')
    module.__file__ = str(path.resolve())
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module, raw


def vector(words):
    values = tuple(struct.unpack('>d', bytes.fromhex(word))[0] for word in words)
    require(len(values) == 3 and all(math.isfinite(x) for x in values), 'Finite recorded3D vector')
    return values


def shifted(point, origin, translation=(0.0, 0.0, 0.0)):
    value = tuple(origin[a] + (point[a] + translation[a]) for a in range(3))
    require(all(math.isfinite(x) for x in value), 'Renderable chart addition must remain finite')
    return value


def scene(decoded, selected_id):
    """Only apply the recorded chart; never recompute a face or fold a polygon."""
    cells, faces = decoded['cells'], decoded['faces']
    positions = {row['id']: vector(row['position_bits']) for row in decoded['input_generators']}
    require(set(positions) == {row['id'] for row in cells}, 'Exact recorded generator inventory')
    periodic = decoded['domain']['boundary'] == 'periodic'
    require(not periodic or selected_id is not None,
            'Periodic rendering requires --cell: one complete owner chart, no artificial box folding')
    selected = None if selected_id is None else next((row for row in cells if row['id'] == selected_id), None)
    require(selected_id is None or selected is not None, 'Selected persistent cell is present')
    segments, colors, rendered = [], [], []

    def append(face_index, origin, translation, color_id, sign):
        polygon = [shifted(vector(words), origin, translation)
                   for words in faces[face_index]['polygon_offset_bits']]
        require(len(segments) + len(polygon) <= MAX_EDGES, 'Bounded actual exported edge count')
        color = PALETTE[int(hashlib.sha256(color_id.encode('ascii')).hexdigest()[:8], 16) % len(PALETTE)]
        for index, point in enumerate(polygon):
            segments.append((point, polygon[(index + 1) % len(polygon)]))
            colors.append(color)
        rendered.append({'face': face_index, 'incidence_sign': sign, 'owner_id': color_id})

    if selected is not None:
        # Include both incidences of a self-image face. Deduplicating by face
        # index would incorrectly discard the opposite side of a periodic cell.
        for incidence in selected['incidences']:
            append(incidence['face'], positions[selected_id],
                   vector(incidence['chart_translation_bits']), selected_id, incidence['sign'])
        shown_generators = [(selected_id, positions[selected_id])]
        chart = 'one recorded owner chart; periodic faces are not folded'
    else:
        # All bounded shared faces occur once, in their canonical left chart.
        for index, face in enumerate(faces):
            owner = cells[face['left']]['id']
            append(index, positions[owner], (0.0, 0.0, 0.0), owner, 1)
        shown_generators = sorted(positions.items())
        chart = 'bounded canonical shared faces, each face shown once'
    require(segments, 'Nonempty recorded face geometry')
    points = [point for edge in segments for point in edge]
    points += [point for _, point in shown_generators]
    bounds = [(min(p[a] for p in points), max(p[a] for p in points)) for a in range(3)]
    require(all(math.isfinite(hi - lo) and hi > lo for lo, hi in bounds),
            'Finite nondegenerate displayed3D extent')
    return segments, colors, shown_generators, bounds, chart, rendered


def render(input_path, transcript_path, bridge_path, output, selected_id, dpi):
    require(type(dpi) is int and 72 <= dpi <= 400, 'Diagnostic resolution72..400dpi')
    renderer_path = Path(__file__)
    renderer_raw = read_bounded(renderer_path, 1024 * 1024)
    input_raw = read_bounded(input_path, MAX_INPUT_BYTES)
    transcript_raw = read_bounded(transcript_path, MAX_TRANSCRIPT_BYTES)
    bridge, bridge_raw = load_bridge(bridge_path)
    decoded = bridge.parse_transcript(transcript_raw, input_raw)
    require(decoded['numeric_gates_evaluated'] is False
            and decoded['execution_provenance_verified'] is False
            and decoded['component_accepted'] is False, 'Rendering cannot accept a scientific gate')
    segments, colors, generators, bounds, chart, rendered = scene(decoded, selected_id)
    output.mkdir(parents=False, exist_ok=False)
    report = {'schema': 'openmhd.geometry3.diagnostic-render.v1', 'status': 'started',
              'case': decoded['case'], 'geometry_epoch': decoded['epoch'],
              'boundary': decoded['domain']['boundary'], 'selected_cell': selected_id,
              'chart': chart, 'source_input': descriptor(input_raw),
              'source_transcript': descriptor(transcript_raw), 'bridge': descriptor(bridge_raw),
              'renderer': descriptor(renderer_raw),
              'rendered_face_incidences': rendered, 'exported_face_count': len(decoded['faces']),
              'edge_count': len(segments), 'generator_count': len(generators), 'dpi': dpi,
              'python': platform.python_version(), 'physical_evolution_performed': False,
              'time_or_motion_inferred': False, 'numeric_gates_evaluated': False,
              'execution_provenance_verified': False, 'component_accepted': False}

    def publish_report():
        (output / 'render.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')

    figure = None
    plt = None
    try:
        (output / 'literal_input.json').write_bytes(input_raw)
        (output / 'candidate_transcript.txt').write_bytes(transcript_raw)
        (output / 'bridge.py').write_bytes(bridge_raw)
        (output / 'renderer.py').write_bytes(renderer_raw)
        publish_report()
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Line3DCollection

        report['matplotlib'] = matplotlib.__version__
        plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
        figure = plt.figure(figsize=(15, 5.8), facecolor='white')
        spans = [hi - lo for lo, hi in bounds]
        normalized_aspect = [span / max(spans) for span in spans]
        require(all(math.isfinite(x) and x > 0.0 for x in normalized_aspect), 'Representable display aspect ratio')
        for index, (elev, azim, title) in enumerate(((25, -55, 'Oblique view'),
                                                   (25, 35, 'Rotated view'),
                                                   (85, -90, 'Near-top view')), 1):
            axes = figure.add_subplot(1, 3, index, projection='3d')
            axes.add_collection3d(Line3DCollection(segments, colors=colors, linewidths=0.9, alpha=0.85))
            axes.scatter(*zip(*(point for _, point in generators)), color='#202c34', s=14,
                         depthshade=False, label='Recorded generators')
            for setter, (lo, hi) in zip((axes.set_xlim, axes.set_ylim, axes.set_zlim), bounds):
                margin = 0.04 * (hi - lo)
                require(math.isfinite(lo - margin) and math.isfinite(hi + margin), 'Finite plot limits')
                setter(lo - margin, hi + margin)
            axes.set_box_aspect(normalized_aspect)
            axes.set_proj_type('ortho')
            axes.view_init(elev=elev, azim=azim)
            axes.set(xlabel='x', ylabel='y', zlabel='z', title=title)
            axes.tick_params(labelsize=8)
        label = 'all bounded shared faces' if selected_id is None else 'cell ' + selected_id
        figure.suptitle('Static3D Voronoi geometry | ' + decoded['case']['name'], fontsize=14, y=0.98)
        figure.text(0.5, 0.08, label + ' | coordinates: candidate code units', ha='center')
        figure.text(0.5, 0.035, 'Recorded polygon edges; diagnostic only. No motion or scientific acceptance inferred.',
                    ha='center', fontsize=9, color='#52616a')
        figure.subplots_adjust(left=0.025, right=0.975, bottom=0.2, top=0.87, wspace=0.1)
        for extension in ('png', 'svg'):
            figure.savefig(output / ('mesh3d.' + extension), dpi=dpi, facecolor='white')
        plt.close(figure)
        figure = None
        require(input_path.read_bytes() == input_raw and transcript_path.read_bytes() == transcript_raw
                and bridge_path.read_bytes() == bridge_raw and renderer_path.read_bytes() == renderer_raw,
                'Original geometry/decoder/renderer bytes unchanged through render')
        report.update(status='complete', outputs={name: descriptor((output / name).read_bytes())
                       for name in ('mesh3d.png', 'mesh3d.svg')})
        publish_report()
        inventory = {path.name: descriptor(path.read_bytes()) for path in sorted(output.iterdir()) if path.is_file()}
        (output / 'files.sha256.json').write_text(json.dumps(inventory, indent=2) + '\n')
    except BaseException as error:
        report.update(status='failed', error_type=type(error).__name__)
        if figure is not None and plt is not None:
            try:
                plt.close(figure)
            except BaseException as cleanup_error:
                report['cleanup_error_type'] = type(cleanup_error).__name__
        try:
            publish_report()
        except BaseException:
            # Storage/interpreter loss can leave an unclosed partial output.
            # Preserve the original error; a report alone never proves success.
            pass
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='Original literal-input JSON')
    parser.add_argument('--transcript', type=Path, required=True, help='Actual complete geometry3-case stdout')
    parser.add_argument('--bridge', type=Path,
                        default=Path(__file__).resolve().with_name('galaxy_geometry3_bridge.py'))
    parser.add_argument('--output', type=Path, required=True, help='New absent output directory')
    parser.add_argument('--cell', help='Exact persistent ID; mandatory for a periodic owner chart')
    parser.add_argument('--dpi', type=int, default=180)
    args = parser.parse_args(argv)
    render(args.input, args.transcript, args.bridge, args.output, args.cell, args.dpi)


if __name__ == '__main__':
    main()
