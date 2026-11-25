"""Verify acquired workflow and native-output identities without running the target."""
from pathlib import Path
from uuid import UUID

from general_geometry_candidate import BINARY_SHA256, CATALOG_SHA256, LARGE_BINARY_SHA256, LARGE_BUILD_UUID
import galaxy_geometry3_general_bridge as bridge
from run_geometry3_general import capture, describe, digest, parse, require


def terminal_workflow(directory, expected='finished'):
    before = parse(capture(directory / 'before.json'))
    after = parse(capture(directory / 'after.json'))
    require(before == after and len(before) == 1 and before[0]['status'] == expected,
            'Stable terminal workflow observations around acquisition')
    workflow = before[0]
    uid = str(UUID(workflow['id']))
    require(workflow['id'] == uid and workflow['workflow'] == f"{workflow['name']}.{workflow['version']}",
            'Exact acquired workflow identity')
    return workflow


def native_command(directory, selection, source, workflow_status):
    workflow = terminal_workflow(directory, workflow_status)
    uid = workflow['id']
    outputs = directory / 'outputs'
    status = parse(capture(outputs / 'status.json'))
    command = parse(capture(outputs / 'command.json'))
    stdout, stderr = (capture(outputs / name) for name in ('stdout.txt', 'stderr.txt'))
    name = bridge.parse_input(source)['case']['name']
    require(name == selection['base'] + '__' + selection['variant']
            and describe(source) == {k: selection['input'][k] for k in ('bytes', 'sha256')},
            'Frozen literal selection')
    converted = bridge.convert_input(source)
    binary_hash = status['links']['binary_sha256']
    require(binary_hash in (BINARY_SHA256, LARGE_BINARY_SHA256), 'Reviewed native build')
    links = dict(binary_sha256=binary_hash, catalog_sha256=CATALOG_SHA256,
                 input_sha256=digest(source), converted_input_sha256=digest(converted))
    if binary_hash == LARGE_BINARY_SHA256:
        links.update(predicate_budget=2_500_000_000, build_uuid=LARGE_BUILD_UUID)
    require(status['schema'] == 'openmhd.geometry3.general-native-export.v1'
            and status['component_accepted'] is False and status['case'] == name
            and status['declared_threads'] == selection['threads']
            and status['backend'] == 'serial HalfSpaceOracle3'
            and status['returncode'] == command['returncode'] and status['links'] == command['links'] == links
            and status['stdout'] == describe(stdout) and status['stderr'] == describe(stderr),
            'Complete native export bound to its actual inputs and outputs')
    work = Path(command['cwd'])
    cleanup = command['cleanup']
    require(work.parts[-4:] == ('workflows', uid, 'outputs', 'work')
            and command['command'] == [str(work / 'geometry3-case'), str(work / 'input.txt')]
            and cleanup['writers_settled'] is True and cleanup['direct_child_reaped'] is True
            and cleanup['leader_held_until_group_close'] is True and cleanup['group_authority_lost'] is False,
            'Closed native process in the acquired workflow')
    receipt = dict(selection=selection['name'], workflow=workflow['workflow'], uuid=uid,
                   binary_sha256=binary_hash, input=describe(source), stdout=describe(stdout), stderr=describe(stderr))
    return status, command, stdout, stderr, receipt


def native_export(directory, selection, source):
    status, command, stdout, _, receipt = native_command(directory, selection, source, 'finished')
    require(status['status'] == 'complete' and command['outcome'] == 'success' and command['returncode'] == 0,
            'Successful native export')
    return source, stdout, receipt
