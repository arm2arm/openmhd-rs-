"""Stage one registered REANA comparison using acquired reference and native results."""
import argparse
import io
from pathlib import Path
import sys
import tarfile

from prepare_general_geometry_jobs import ROOT, read_literals, shared_sources, stage, write_json

sys.path.insert(0, str(ROOT / 'reana'))
from general_geometry_capture import native_export, terminal_workflow
from run_geometry3_general import (MAX_CAPSULE_BYTES, MAX_RAW_BYTES, capture, describe, digest,
                                   parse, require)


def read_reference(directory, source, modules):
    workflow = terminal_workflow(directory)
    outputs = directory / 'outputs'
    raw = capture(outputs / 'packet.tar.gz')
    require(len(raw) <= MAX_CAPSULE_BYTES
            and parse(capture(outputs / 'packet.sha256.json')) == describe(raw), 'Reference packet identity')
    names = {'input.json', 'reference.json', 'status.json', 'files.sha256.json'}
    files = {}
    size = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r|gz') as archive:
        for member in archive:
            size += member.size
            require(member.isfile() and member.name in names and member.name not in files
                    and 0 <= member.size and size <= MAX_RAW_BYTES, 'Bounded reference packet inventory')
            files[member.name] = archive.extractfile(member).read()
    require(set(files) == names and parse(files['files.sha256.json']) == {
        n: describe(b) for n, b in files.items() if n != 'files.sha256.json'
    }, 'Complete reference manifest')
    status = parse(files['status.json'])
    require(files['status.json'] == capture(outputs / 'status.json') and status['action'] == 'reference'
            and status['status'] == 'complete' and files['input.json'] == source
            and status['input_identities'] == {'input': describe(source)}
            and status['source_sha256'] == {Path(n).name: digest(b) for n, b in modules.items()},
            'Complete reference from the frozen source and literal')
    result = parse(files['reference.json'])
    require(result['schema'] == 'openmhd.geometry3.certified-general-reference.v1'
            and result['input_sha256'] == digest(source) and result['exact_volume_closure'] is True,
            'Independent reference certificate')
    return files['reference.json'], dict(workflow=workflow['workflow'], uuid=workflow['id'],
                                        packet=describe(raw), reference=describe(files['reference.json']))


def prepare(name, reference_directory, native_directory, destination):
    members = read_literals()
    modules = shared_sources(members)
    selections = {r['name']: r for r in parse(members['catalog.json'])['cases']}
    case = selections[name]
    source = members[case['input']['path']]
    _, transcript, native = native_export(native_directory, case, source)
    reference_sources = shared_sources(members, current_reference=True)
    reference_status = parse(capture(reference_directory / 'outputs/status.json'))
    if reference_status['source_sha256'] == {Path(n).name: digest(b) for n, b in modules.items()}:
        reference_sources = modules
    reference, receipt = read_reference(reference_directory, source, reference_sources)
    require(native['uuid'] != receipt['uuid'], 'Independent reference and native workflows')
    inputs = dict(modules, **{'input.json': source, 'candidate.txt': transcript,
                              'reference.json': reference})
    command = ('scripts/run_geometry3_general.py compare --input input.json --candidate candidate.txt '
               '--reference reference.json --output outputs')
    staged = stage(destination, inputs, command, ['status.json', 'packet.tar.gz', 'packet.sha256.json'],
                   1, '4Gi', 600, 'compare-static-geometry')
    write_json(destination / 'staged.json', dict(staged, selection=name, native=native, reference=receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('selection')
    parser.add_argument('reference_capture', type=Path)
    parser.add_argument('native_capture', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    prepare(args.selection, args.reference_capture, args.native_capture, args.destination)
