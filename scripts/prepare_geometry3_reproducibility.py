"""Plan G04 candidate dependencies or stage one REANA reduction from acquired outputs."""
import argparse
import json
from pathlib import Path

from prepare_general_geometry_jobs import ROOT, NATIVE, read_literals, shared_sources, stage, write_json


def pairs(cases):
    index = {(c['base'], c['variant'], c['threads']): c for c in cases}
    if len(index) != len(cases):
        raise ValueError('Duplicate frozen case selection')
    for second in cases:
        base, variant, threads = (second[k] for k in ('base', 'variant', 'threads'))
        if variant == 'base' and threads == 1:
            continue
        first = index[base, 'base', 1 if variant == 'base' else threads]
        yield first, second


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    plan = actions.add_parser('plan')
    plan.add_argument('output', type=Path)
    job = actions.add_parser('stage')
    job.add_argument('right_selection')
    job.add_argument('left_capture', type=Path)
    job.add_argument('right_capture', type=Path)
    job.add_argument('destination', type=Path)
    args = parser.parse_args()
    members = read_literals()
    cases = json.loads(members['catalog.json'])['cases']
    registered = {b['name']: (a, b) for a, b in pairs(cases)}
    if args.action == 'plan':
        with args.output.open('x') as stream:
            json.dump([dict(left=a['name'], right=b['name']) for a, b in registered.values()],
                      stream, indent=2)
            stream.write('\n')
        return
    first, second = registered[args.right_selection]
    inputs = shared_sources(members)
    for name in (*NATIVE, 'reana/general_geometry_capture.py', 'reana/general_geometry_reproducibility.py'):
        inputs[name] = (ROOT / name).read_bytes()
    inputs['catalog.json'] = members['catalog.json']
    for side, selection, folder in (('left', first, args.left_capture), ('right', second, args.right_capture)):
        inputs[side + '/input.json'] = members[selection['input']['path']]
        for name in ('before.json', 'after.json', 'outputs/status.json', 'outputs/command.json',
                     'outputs/stdout.txt', 'outputs/stderr.txt'):
            inputs[side + '/' + name] = (folder / name).read_bytes()
    command = (f"reana/general_geometry_reproducibility.py --left {first['name']} "
               f"--right {second['name']}")
    record = stage(args.destination, inputs, command, ['result.json'], 1, '4Gi', 600, 'check-g04-pair')
    write_json(args.destination / 'staged.json', record)


if __name__ == '__main__':
    main()
