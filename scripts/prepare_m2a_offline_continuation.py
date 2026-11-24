"""Restore each offline case's native parent-review binding before submission.

The execution-control proof applies to the campaign plan. The native runner's
source_slice_output_review field identifies the Rust build/catalog review.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reana'))
import galaxy_workspace_case as runner


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def inventory(folder):
    return {p.relative_to(folder).as_posix(): {'sha256': digest(p), 'bytes': p.stat().st_size}
            for p in folder.rglob('*') if p.is_file()}


def prepare(offline, original, control, destination):
    plan = read(offline / 'plan.json')
    if digest(offline / 'plan.json') != 'f82c979d38740f14342aa22f0abd5ca7a91ea120ac8f4b0c964b2d7de5b88d35':
        raise ValueError('Expected the released November 24 offline plan')
    if digest(original / 'plan.json') != plan['original_plan_sha256'] or digest(control) != plan['control216_proof_sha256']:
        raise ValueError('Original Rust plan or execution-control proof changed')
    originals = {entry['workflow']: entry for entry in read(original / 'plan.json')['cases']}
    destination.mkdir()
    entries = []
    for entry in plan['cases']:
        index = entry['directory']
        native = originals[entry['original_workflow']]
        if native['directory'] != index or inventory(offline / index) != entry['files']:
            raise ValueError(f'Input inventory changed for {index}')
        folder = destination / index
        shutil.copytree(offline / index, folder)
        for name in ('root-release.json', 'case.json', 'payload.json'):
            path = original / index / name
            if digest(path) != native['files'][name]['sha256']:
                raise ValueError(f'Original {index}/{name} changed')
            shutil.copyfile(path, folder / name)
        buffers = {name: (folder / name).read_bytes() for name in runner.FIXED}
        if buffers['workspace_case.py'] != Path(runner.__file__).read_bytes():
            raise ValueError('Validate with the runner used by the workflow')
        runner.validate_inputs(buffers, (folder / 'payload.json').read_bytes())
        case = read(folder / 'case.json')
        if case != native['specification'] or case['leaf'] != entry['specification']['leaf']:
            raise ValueError('Original case identity changed')
        entries.append(dict(entry, prior_offline_workflow=entry['workflow'],
                            workflow='openmhd-m2a-offline-r2-' + index + '.1',
                            specification=case, files=inventory(folder)))
    amended = dict(plan, cases=entries, superseded_plan_sha256=digest(offline / 'plan.json'))
    (destination / 'plan.json').write_text(json.dumps(amended, indent=2) + '\n')
    print(f'Validated {len(entries)} native payloads; plan {digest(destination / "plan.json")}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('offline', 'original', 'control', 'destination'):
        parser.add_argument(key, type=Path)
    prepare(**vars(parser.parse_args()))
