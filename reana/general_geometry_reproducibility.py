"""Reduce two independently executed native geometry exports for one G04 pair."""
import argparse
from pathlib import Path
from uuid import UUID

from general_geometry_candidate import BINARY_SHA256, CATALOG_SHA256
import galaxy_geometry3_general_bridge as bridge
from galaxy_geometry3_general_compare import reproducibility
from run_geometry3_general import capture, describe, digest, encode, parse, require


def export(directory, selection):
    source = capture(directory / 'input.json')
    before = parse(capture(directory / 'before.json'))
    after = parse(capture(directory / 'after.json'))
    require(before == after and len(before) == 1 and before[0]['status'] == 'finished',
            'Stable terminal workflow observations around acquisition')
    workflow = before[0]
    uid = str(UUID(workflow['id']))
    require(workflow['id'] == uid and workflow['workflow'] == f"{workflow['name']}.{workflow['version']}",
            'Exact acquired workflow identity')
    outputs = directory / 'outputs'
    status = parse(capture(outputs / 'status.json'))
    command = parse(capture(outputs / 'command.json'))
    stdout, stderr = (capture(outputs / name) for name in ('stdout.txt', 'stderr.txt'))
    name = bridge.parse_input(source)['case']['name']
    require(name == selection['base'] + '__' + selection['variant']
            and describe(source) == {k: selection['input'][k] for k in ('bytes', 'sha256')},
            'Frozen literal selection')
    converted = bridge.convert_input(source)
    links = dict(binary_sha256=BINARY_SHA256, catalog_sha256=CATALOG_SHA256,
                 input_sha256=digest(source), converted_input_sha256=digest(converted))
    require(status['schema'] == 'openmhd.geometry3.general-native-export.v1'
            and status['status'] == 'complete' and status['case'] == name
            and status['declared_threads'] == selection['threads']
            and status['backend'] == 'serial HalfSpaceOracle3'
            and status['returncode'] == 0 and status['links'] == command['links'] == links
            and status['stdout'] == describe(stdout) and status['stderr'] == describe(stderr),
            'Complete native export bound to its actual inputs and outputs')
    work = Path(command['cwd'])
    cleanup = command['cleanup']
    require(work.parts[-4:] == ('workflows', uid, 'outputs', 'work')
            and command['command'] == [str(work / 'geometry3-case'), str(work / 'input.txt')]
            and command['outcome'] == 'success' and command['returncode'] == 0
            and cleanup['writers_settled'] is True and cleanup['direct_child_reaped'] is True
            and cleanup['leader_held_until_group_close'] is True and cleanup['group_authority_lost'] is False,
            'Closed native process in the acquired workflow')
    receipt = dict(selection=selection['name'], workflow=workflow['workflow'], uuid=uid,
                   binary_sha256=BINARY_SHA256, input=describe(source), stdout=describe(stdout))
    return source, stdout, receipt


def without_case_line(raw, case):
    # The native input and output formats each have exactly one complete case row.
    marker = b'\ncase ' + case.encode('ascii') + b'\n'
    require(raw.count(marker) == 1, 'Unique validated case label')
    return raw.replace(marker, b'\ncase\n', 1)


def reduce_pair(left, right, first, second):
    require(first['base'] == second['base'] and first['variant'] == 'base', 'Common base geometry')
    cross_thread = second['variant'] == 'base'
    require((cross_thread and first['threads'] == 1 and second['threads'] in (2, 4))
            or (not cross_thread and first['threads'] == second['threads']), 'Registered G04 pair')
    li, lo, lr = left
    ri, ro, rr = right
    require(lr['uuid'] != rr['uuid'], 'Two independent native executions')
    metrics = reproducibility(li, lo, ri, ro)
    left_case = first['base'] + '__base'
    right_case = second['base'] + '__' + second['variant']
    same_input = (without_case_line(bridge.convert_input(li), left_case)
                  == without_case_line(bridge.convert_input(ri), right_case))
    repeat = second['variant'] == 'repeat'
    require(not (cross_thread or repeat) or same_input, 'Identical native words for repeated geometry')
    exact = without_case_line(lo, left_case) == without_case_line(ro, right_case)
    return dict(schema='openmhd.geometry3.g04-pair.v1', left=lr, right=rr, metrics=metrics,
                same_native_input_except_case=same_input, same_transcript_except_case=exact,
                repeat_requires_exact_output=repeat, passed=metrics['passed'] and (not repeat or exact),
                component_accepted=False)


def execute(catalog_path, left_path, right_path, left_name, right_name, output):
    raw = capture(catalog_path)
    require(digest(raw) == CATALOG_SHA256, 'Frozen REANA catalog')
    cases = {r['name']: r for r in parse(raw)['cases']}
    first, second = cases[left_name], cases[right_name]
    output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='openmhd.geometry3.g04-outcome.v1', left=left_name, right=right_name,
                  catalog_sha256=digest(raw), component_accepted=False, passed=False)
    try:
        left = export(left_path, first)
        right = export(right_path, second)
        record['reduction'] = reduce_pair(left, right, first, second)
        require(record['reduction']['passed'], 'Registered G04 pair failed')
        record['passed'] = True
    except Exception as exc:
        record.update(error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        (output / 'result.json').write_bytes(encode(record))
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--left', required=True)
    parser.add_argument('--right', required=True)
    args = parser.parse_args()
    execute(Path('catalog.json'), Path('left'), Path('right'), args.left, args.right, Path('outputs'))
