"""Execute the static geometry export for one frozen G02–G04 input on REANA."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tools/m1_evidence')]
import galaxy_geometry3_general_bridge as bridge
import galaxy_geometry3_general_fixtures as fixtures
import galaxy_test_case as launcher
import reana_metadata_job as supervisor
from run_geometry3_general import capture, describe, digest, encode, require

# The G01 build used for all 252 published static analytic comparisons.
BINARY_SHA256 = '6eb185eb1a423fcdc7f23c5b865b5f09e5acc20ac81f89141b527932fe67f4a2'

# Opt-in predicate allowance built at 95d4d8d58252.
LARGE_BINARY_SHA256 = 'd8b279448578d721fd3501464f377a5dee88e3236438e6dc29c12f0158da9b8b'
LARGE_BUILD_UUID = '2844b652-4dbc-455c-94ad-f9a4595cd67d'

CATALOG_SHA256 = '3d590b1615e13faaa4a368e87018dabdc6cf694a8a8b8fbd03d56694b9a83cc3'


def execute(input_path, binary_path, catalog_path, threads, output, large_geometry_budget=False):
    source = capture(input_path)
    binary = capture(binary_path)
    binary_hash = LARGE_BINARY_SHA256 if large_geometry_budget else BINARY_SHA256
    require(digest(binary) == binary_hash, 'Reviewed static geometry executable for the selected budget')
    selection = bridge.parse_input(source)['case']['name']
    base, variant = selection.split('__')
    require(base in fixtures.BASES and variant in fixtures.VARIANTS and threads in (1, 2, 4),
            'Registered general geometry selection')
    catalog = capture(catalog_path)
    require(digest(catalog) == CATALOG_SHA256, 'Frozen REANA input catalog')
    records = [r for r in json.loads(catalog)['cases']
               if (r['base'], r['variant'], r['threads']) == (base, variant, threads)]
    require(len(records) == 1 and records[0]['input']['sha256'] == digest(source),
            'Exact frozen words for the selected case')
    output = output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    work = output / 'work'
    work.mkdir()
    input_txt = work / 'input.txt'
    converted = bridge.convert_input(source)
    input_txt.write_bytes(converted)
    executable = work / 'geometry3-case'
    executable.write_bytes(binary)
    executable.chmod(0o700)
    env = dict(os.environ, RAYON_NUM_THREADS=str(threads), OMP_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    # The serial all-pairs driver took 242 seconds for the 216-generator jittered mesh.
    timeout = 600
    if base == 'jitter8':
        timeout = 3600
    elif base not in fixtures.BASES[:6] and (variant, threads) == ('base', 1):
        timeout = 300
    links = dict(binary_sha256=binary_hash, catalog_sha256=CATALOG_SHA256, input_sha256=digest(source),
                 converted_input_sha256=digest(converted))
    if large_geometry_budget:
        links.update(predicate_budget=2_500_000_000, build_uuid=LARGE_BUILD_UUID)
    record = dict(schema='openmhd.geometry3.general-native-export.v1', case=selection,
                  declared_threads=threads, backend='serial HalfSpaceOracle3',
                  links=links, component_accepted=False, status='started')
    status_path = output / 'status.json'
    status_path.write_bytes(encode(record))
    try:
        command = launcher.launch_native(supervisor, [str(executable), str(input_txt)],
            work, env, output, timeout, links)
        cleanup = command.get('cleanup', {})
        require(cleanup.get('writers_settled') is True and cleanup.get('direct_child_reaped') is True
                and cleanup.get('leader_held_until_group_close') is True
                and cleanup.get('group_authority_lost') is False, 'Closed native process and writers')
        stdout, stderr = (capture(output / n) for n in ('stdout.txt', 'stderr.txt'))
        record.update(stdout=describe(stdout), stderr=describe(stderr), returncode=command['returncode'])
        require(capture(executable) == capture(binary_path) == binary
                and capture(input_txt) == converted and capture(input_path) == source,
                'Stable native executable and literal inputs')
        if command['returncode'] != 0:
            # A typed rejection is evidence for later G03 adjudication. Keep the
            # failed command and exact diagnostic even when the input is difficult.
            rejected = re.fullmatch(rb'geometry3 candidate export rejected: 3D geometry rejected: '
                                    rb'([A-Za-z]+)(?: [^\n]*|\([^\n]*\))?\n', stderr)
            if command['returncode'] == 1 and not stdout and rejected:
                record['geometry_error_variant'] = rejected[1].decode('ascii')
            raise ValueError('Native geometry export failed')
        require(command['outcome'] == 'success', 'Successful executable outcome')
        decoded = bridge.parse_transcript(stdout, source)
        record.update(status='complete', cells=len(decoded['cells']), faces=len(decoded['faces']))
    except Exception as error:
        record.update(status='failed', error=str(error))
        raise
    finally:
        status_path.write_bytes(encode(record))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--threads', type=int, choices=(1, 2, 4), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--large-geometry-budget', action='store_true')
    args = parser.parse_args()
    execute(args.input, args.binary, args.catalog, args.threads, args.output, args.large_geometry_budget)
