"""Small REANA control using the retained eight-cell native cube and a wrong seam chart."""
from pathlib import Path

from general_geometry_reproducibility import periodic_charts
import galaxy_geometry3_general_bridge as bridge
from run_geometry3_general import capture, describe, encode, require


def main():
    source = capture(Path('input.json'))
    original = capture(Path('candidate.txt'))
    mesh = bridge.parse_transcript(original, source)
    require(mesh['case']['name'] == 'cospherical_cube__base', 'Registered cube control')
    matching = periodic_charts(source, original)
    require(matching['passed'] and matching['right_incidences'] == 24
            and matching['wrapped_image_incidences'] == 12 and matching['maximum_component_over_L'] == '0',
            'Exact unmodified periodic cube charts')

    face_index, axis = next((idx, a) for idx, face in enumerate(mesh['faces'])
                            for a, winding in enumerate(face['right_wrapped_image']) if winding)
    corrupted = original.splitlines(keepends=True)
    row = next(i for i, line in enumerate(corrupted)
               if line.startswith(b'incidence ') and line.split()[2:4] == [str(face_index).encode(), b'-1'])
    fields = corrupted[row].split()
    require(fields[-3 + axis] != b'0000000000000000', 'Nonzero seam translation to perturb')
    fields[-3 + axis] = b'0000000000000000'
    corrupted[row] = b' '.join(fields) + b'\n'
    altered = b''.join(corrupted)
    rejected = periodic_charts(source, altered)
    require(not rejected['passed'] and rejected['maximum_component_over_L'] == '1/2'
            and rejected['worst']['face'] == mesh['faces'][face_index]['key']
            and rejected['worst']['axis'] == axis, 'Half-box chart error attributed to the changed face and axis')
    out = Path('outputs')
    out.mkdir()
    (out / 'changed.txt').write_bytes(altered)
    (out / 'check.json').write_bytes(encode(dict(matching=matching, deliberately_changed=rejected,
        source=describe(source), original=describe(original), changed=describe(altered),
        passed=True, component_accepted=False)))


if __name__ == '__main__':
    main()
