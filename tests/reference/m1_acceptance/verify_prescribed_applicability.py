"""Inspect archived prescribed-flow evidence against current sources; no evolution.

This records source dependencies and existing observations, not current-binary
reproduction or independent review. Run from the repository root.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output')
    archive = Path('tests/reference/m1_completion/prescribed')
    manifest = json.loads((archive/'archive_sha256.json').read_text())
    verified = {}
    for name, expected in manifest.items():
        assert sha((archive/name).read_bytes()) == expected, name
        verified[name] = expected
    paths = [
        'apps/openmhd/src/bin/prescribed-loop.rs',
        'crates/mhd-vector-pot/src/transport.rs',
        'crates/mhd-vector-pot/src/diagnostics.rs',
        'crates/mhd-vector-pot/src/operators.rs',
        'crates/mhd-vector-pot/src/benchmarks.rs',
        'crates/moving-mesh/src/lib.rs',
    ]
    comparison = {}
    fragments = {}
    with tarfile.open(archive/'execution_sources.tar.gz') as source:
        for name in paths:
            old = source.extractfile(name).read()
            new = Path(name).read_bytes()
            comparison[name] = dict(archived_sha256=sha(old), current_sha256=sha(new),
                                    whole_file_unchanged=old == new)
            if name.endswith('operators.rs'):
                start, end = 'pub(crate) struct TransportStencil', 'pub(crate) struct PotentialStage'
                left = old.decode().split(start, 1)[1].split(end, 1)[0]
                right = new.decode().split(start, 1)[1].split(end, 1)[0]
                assert left == right
                fragments['TransportStencil'] = dict(unchanged=True, sha256=sha(left.encode()))
            if name.endswith('benchmarks.rs'):
                left = old.decode().split('#[cfg(test)]', 1)[0]
                right = new.decode().split('/// M0 periodic Brio-Wu embedding', 1)[0]
                assert left == right
                fragments['loop_initialization_and_reference_prefix'] = dict(
                    unchanged=True, sha256=sha(left.encode()))
    assert all(comparison[name]['whole_file_unchanged'] for name in paths[:3])
    summary = json.loads(gzip.decompress((archive/'summary.json.gz').read_bytes()))
    old_applicability = json.loads((archive/'applicability_20261110.json').read_text())
    report = dict(
        kind='Implementing-assistant static applicability inspection; no new evolution or binary reproduction.',
        development_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        analysis_source_sha256=sha(Path(__file__).read_bytes()),
        scope='Serial constant-flow-voronoi-v1 prescribed loop only; no conservative gas evolution.',
        verified_archive_files=verified, source_comparison=comparison, unchanged_fragments=fragments,
        summary_sha256=sha(json.dumps(summary, sort_keys=True).encode()),
        historical_results=old_applicability['historical_results'],
        changed_dependencies=[
            'operators::gradients now delegates to batched per-cell gradient/limiter paths; the old transport-prefix equality claim is no longer applicable.',
            'moving-mesh includes faster clipping, ordered per-cell construction, reconstruction guards and batched derivatives/limiters; mathematical expressions and reduction ordering require review.',
        ],
        applicable_existing_checks=[
            'fused_gradients_and_limiters_repeat_the_scalar_ones_bit_for_bit',
            'mesh geometry/all-pairs, thread equality and transport covariance/refinement checks in the current-source REANA preflight',
        ],
        disposition='Retain original results as scoped historical evidence. Current-source applicability awaits the final reviewer and actual preflight results; no fresh full-ladder binary identity claim.',
        full_m1_accepted=False,
    )
    args.output.write_text(json.dumps(report, indent=1, allow_nan=False)+'\n')
    print('Verified archived prescribed-flow files:', len(verified))


if __name__ == '__main__':
    main()
