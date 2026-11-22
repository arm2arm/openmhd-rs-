"""Freeze complete fresh M1 evidence for separate review, never acceptance.

No evolution, build, workflow control, or repository mutation. Input must be a
successfully closed prepare_final_evidence.py output. Use a new --output path
for its immutable evidence subpacket; later reviewer files belong beside it.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

REVISION = '2bdcea0d28340e7429e10053a641f92d51fcc696'
SNAPSHOT = 'b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f'
BINARY = '18afcf0308338e2ea0ea7ef5e03dba46af9d7025f3ccf4a6a48ebbfe800d0725'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def files(root):
    return {p.relative_to(root).as_posix(): p for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}


def safe_path(root, name):
    p = PurePosixPath(name)
    assert not p.is_absolute() and '..' not in p.parts and str(p) == name, name
    path = root.joinpath(*p.parts)
    assert path.resolve().is_relative_to(root.resolve()), name
    return path


def verify_closed(root, manifest_name, children=None):
    children = children or {}
    manifest = json.loads((root / manifest_name).read_text())
    actual = files(root)
    actual.pop(manifest_name)
    for directory, child_manifest in children.items():
        verify_closed(root / directory, child_manifest)
        actual = {n: p for n,p in actual.items()
                  if not n.startswith(directory + '/') or n == directory + '/' + child_manifest}
    assert set(actual) == set(manifest), (str(root), 'inventory mismatch')
    for name, digest in manifest.items():
        assert sha(safe_path(root, name).read_bytes()) == digest, name
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source, out, repo = args.input.resolve(), args.output.resolve(), Path.cwd()
    assert not out.exists(), 'Preserve existing evidence'
    assert not out.is_relative_to(source) and not source.is_relative_to(out)
    input_manifest = verify_closed(source, 'sha256.json')
    summary = json.loads((source / 'summary.json').read_text())
    assert summary['snapshot_sha256'] == SNAPSHOT and summary['binary_sha256'] == BINARY
    expected = dict(verified_matrix_cases=214, independently_reduced_boost_pairs=99,
                    spatial_ladders=8, temporal_ladders=12, primary_shock_cases=12,
                    primary_vortex_cases=6, actual_raw_inputs=238)
    assert all(summary[k] == v for k,v in expected.items())
    assert summary['all_independent_checks_passed']
    assert not summary['full_m1_accepted'] and not summary['final_ai_output_review_passed']
    previous = repo / 'tests/reference/m1_acceptance'
    historical = repo / 'tests/reference/m1_iterative_step_campaigns'
    verify_closed(previous, 'archive_sha256.json', {'review': 'review_sha256.json'})
    verify_closed(historical, 'archive_sha256.json')
    snapshot_bytes = gzip.decompress((previous / 'snapshot.json.gz').read_bytes())
    assert sha(snapshot_bytes) == SNAPSHOT
    snapshot = json.loads(snapshot_bytes)
    frozen = {}
    for name, digest in snapshot['source_sha256'].items():
        if (name.startswith(('apps/', 'crates/', 'scripts/', 'benchmarks/', 'reana/',
                             'tests/reference/external_mhd/')) or
                name in ('Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml')):
            data = subprocess.check_output(['git', 'show', REVISION + ':' + name])
            assert sha(data) == digest, name
            frozen[name] = data
    scientific = [n for n in frozen if not n.startswith('tests/reference/')
                  and n != 'rust-toolchain.toml']
    assert len(scientific) == 226
    # All prerequisites above finish before this new evidence boundary exists.
    out.mkdir(parents=True)
    index = []

    def store(data, relative, origin, compress=False):
        target = safe_path(out, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        assert not target.exists(), relative
        encoded = gzip.compress(data, mtime=0) if compress else data
        target.write_bytes(encoded)
        index.append(dict(path=relative, origin=origin, encoding='gzip' if compress else 'identity',
                          original_bytes=len(data), original_sha256=sha(data),
                          stored_bytes=len(encoded), stored_sha256=sha(encoded)))

    selected = ['summary.json', 'registered_verdict.json', 'commands.json',
                'medium_independent.json', 'mean_independent.json',
                'waves_independent.json', 'physics_boost_independent.json',
                'shock/independent_reference.json', 'vortex/independent_reference.json',
                'vortex/independent_bins.json.gz', 'physics_inputs/input_receipts.json',
                'physics_inputs/provenance.json', 'physics_inputs/runs.json',
                'physics_inputs/observed_run_map.json', 'physics_inputs/checkpoint.json',
                'physics_inputs/plan.json', 'wave_inputs/runs.json', 'wave_inputs/manifest.json',
                'wave_inputs/provenance.json', 'wave_inputs/input_receipts.json']
    selected += [phase + '_provenance.json' for phase in ('medium', 'mean', 'waves', 'physics')]
    selected += [n for n in input_manifest if n.startswith(('tools/', 'logs/', 'observations/'))]
    for name in sorted(set(selected)):
        assert name in input_manifest, name
        data = safe_path(source, name).read_bytes()
        assert sha(data) == input_manifest[name], name
        compress = name.endswith('.json') and name != 'summary.json'
        store(data, 'fresh/' + name + ('.gz' if compress else ''),
              dict(kind='complete_fresh_collection', path=name,
                   manifest_sha256=sha((source / 'sha256.json').read_bytes())), compress)
    store((source / 'sha256.json').read_bytes(), 'fresh/original_collection_sha256.json',
          dict(kind='full_original_collection_manifest', raw_inputs_retained_outside_this_packet=True))
    for directory, label in ((previous, 'source_review_packet'), (historical, 'historical_campaigns')):
        before = {n: sha(p.read_bytes()) for n,p in files(directory).items()}
        for name in sorted(before):
            data = safe_path(directory, name).read_bytes()
            assert sha(data) == before[name], name
            store(data, label + '/' + name, dict(kind='retained_prior_packet',
                  repository_path=str(directory.relative_to(repo) / name)))
        assert before == {n: sha(p.read_bytes()) for n,p in files(directory).items()}
    catalog = {}
    for name, data in sorted(frozen.items()):
        store(data, 'frozen_source/' + name, dict(kind='frozen_git_blob', revision=REVISION, path=name))
        catalog[name] = sha(data)
    store((json.dumps(dict(revision=REVISION, scientific_files=226,
          includes_toolchain_and_external_references=True, sha256=catalog), indent=1)+'\n').encode(),
          'frozen_source_catalog.json', dict(kind='verified_frozen_git_catalog'))
    for name in ('M1_FINAL_AI_REVIEW.md', 'M1_CANDIDATE_AUDIT.md', 'M1_FINAL_ACCEPTANCE_PLAN.md',
                 'M1_FULL_VALIDATION_PLAN.md', 'M1_FINAL_ARCHIVE_PLAN.md'):
        data = (repo / 'docs' / name).read_bytes()
        store(data, 'documents/' + name, dict(kind='current_review_context', repository_path='docs/' + name))
    store(Path(__file__).read_bytes(), 'host_tools/pack_final_review_evidence.py',
          dict(kind='packager_source'))
    verifier = Path(__file__).with_name('verify_final_review_evidence.py')
    store(verifier.read_bytes(), 'verify_final_review_evidence.py', dict(kind='portable_read_only_verifier'))
    record = dict(schema='openmhd.m1-final-review-evidence.v1', created_utc=datetime.now(timezone.utc).isoformat(),
                  source_revision=REVISION, snapshot_sha256=SNAPSHOT, binary_sha256=BINARY,
                  input_collection_manifest_sha256=sha((source / 'sha256.json').read_bytes()),
                  current_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  full_m1_accepted=False, final_ai_output_review_passed=False,
                  raw_input_scope='All238 actual bytes verified by complete input collection; large raw files remain in original local/REANA artifacts, identified in fresh summary/receipts.',
                  source_scope='Historical Git blobs, not a requirement that future development working files stay frozen.',
                  next='Separate AI output review must pin evidence/sha256.json. Add review beside evidence, then close an outer archive and acceptance record only after all requirements pass.',
                  artifacts=index)
    (out / 'artifact_index.json').write_text(json.dumps(record, indent=1, allow_nan=False)+'\n')
    assert input_manifest == verify_closed(source, 'sha256.json')
    manifest = {n: sha(p.read_bytes()) for n,p in sorted(files(out).items())}
    (out / 'sha256.json').write_text(json.dumps(manifest, indent=1)+'\n')
    print('Frozen review evidence only; no final review or M1 acceptance:', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
