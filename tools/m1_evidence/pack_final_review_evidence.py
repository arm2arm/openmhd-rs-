"""Freeze repaired complete M1 evidence for separate review; never acceptance.

No numerical/reducer execution, build or workflow control. Successful packaging
requires the complete collector's actual214 cases; failed output is preserved.
"""
if not __debug__:
    raise RuntimeError("Optimized Python cannot package M1 evidence")

import argparse
from datetime import datetime, timezone
import gzip
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True


def load_portable():
    path = Path(__file__).with_name('verify_final_review_evidence.py')
    spec = importlib.util.spec_from_file_location('m1_portable_archive',path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    v = load_portable()
    source,out,repo = args.input.resolve(),args.output.resolve(),Path.cwd().resolve()
    v.require(not out.exists(),'Use new immutable evidence destination')
    v.require(out.name == 'evidence','Review evidence must be a sibling evidence/ boundary')
    v.require(not out.is_relative_to(source) and not source.is_relative_to(out),'Overlapping collection/export')
    for closed in ('m1_acceptance','m1_iterative_step_campaigns'):
        v.require(not out.is_relative_to(repo/'tests/reference'/closed),'Historical packet is closed')
    original_bytes = v.safe_path(source,'sha256.json').read_bytes()
    input_manifest = v.verify_closed(source,'sha256.json')
    manifest_digest = v.sha(original_bytes)
    summary = v.read(source,'summary.json')
    v.require(summary['snapshot_sha256'] == v.SNAPSHOT and summary['binary_sha256'] == v.BINARY
        and summary['all_independent_checks_passed'] is True and summary['full_m1_accepted'] is False
        and summary['final_ai_output_review_passed'] is False,'Complete fresh collection required')
    for key,value in dict(verified_matrix_cases=214,independently_reduced_boost_pairs=99,
        spatial_ladders=8,temporal_ladders=12,primary_shock_cases=12,primary_vortex_cases=6,actual_raw_inputs=238).items():
        v.require(summary[key] == value,'Incomplete collection: '+key)
    capture = v.read(source,'metadata_capture.json')
    selected,omitted = v.export_selection(input_manifest,summary,capture)
    # All omitted files are still read/verified by the full input closure. Tie
    # every decoded raw duplicate's hash AND length to the actual consumed input.
    for name,row in omitted.items():
        data = v.safe_path(source,name).read_bytes()
        raw = gzip.decompress(data) if row['encoding'] == 'gzip' else data
        v.require(v.sha(raw) == row['decoded_sha256'] and len(raw) == row['decoded_bytes'],
                  'Omitted duplicate decoded identity/length')
    previous = repo/'tests/reference/m1_acceptance'
    historical = repo/'tests/reference/m1_iterative_step_campaigns'
    for name,(digest,count) in v.HISTORICAL.items():
        label,relative = name.split('/',1)
        root = previous if label == 'source_review_packet' else historical
        v.require(v.sha(v.safe_path(root,relative).read_bytes()) == digest,'Changed historical manifest')
        parent,filename = relative.rsplit('/',1) if '/' in relative else ('',relative)
        v.verify_closed(root/parent,filename,{'review':'review_sha256.json'} if name ==
            'source_review_packet/archive_sha256.json' else None,historical=True,expected_count=count)
    snapshot_bytes = gzip.decompress((previous/'snapshot.json.gz').read_bytes())
    v.require(v.sha(snapshot_bytes) == v.SNAPSHOT,'Snapshot identity')
    snapshot = v.loads(snapshot_bytes)
    frozen = {}
    for name,digest in snapshot['source_sha256'].items():
        if name.startswith(('apps/','crates/','scripts/','benchmarks/','reana/','tests/reference/external_mhd/')) or name in (
                'Cargo.toml','Cargo.lock','rust-toolchain.toml'):
            data = subprocess.check_output(['git','show',v.REVISION+':'+name])
            v.require(v.sha(data) == digest,'Historical Git blob differs: '+name)
            frozen[name] = data
    v.require(len([n for n in frozen if not n.startswith('tests/reference/') and n != 'rust-toolchain.toml']) == 226,
              'Frozen scientific source count')
    # Validated collection closure/readiness and source prerequisites precede creation.
    out.mkdir(parents=True)
    artifacts = []

    def store(data,name,origin,compress=False):
        target = v.safe_path(out,name)
        target.parent.mkdir(parents=True,exist_ok=True)
        v.require(not target.exists(),'Duplicate artifact: '+name)
        encoded = gzip.compress(data,mtime=0) if compress else data
        target.write_bytes(encoded)
        artifacts.append(dict(path=name,origin=origin,encoding='gzip' if compress else 'identity',
            original_bytes=len(data),original_sha256=v.sha(data),
            stored_bytes=len(encoded),stored_sha256=v.sha(encoded)))

    for name in sorted(selected):
        data = v.safe_path(source,name).read_bytes()
        v.require(v.sha(data) == input_manifest[name],'Changed source artifact: '+name)
        compress = name.endswith('.json') and name != 'summary.json'
        store(data,'fresh/'+name+('.gz' if compress else ''),
              dict(kind='complete_fresh_collection',path=name,manifest_sha256=manifest_digest),compress)
    store(original_bytes,'fresh/original_collection_sha256.json',
          dict(kind='full_original_collection_manifest',manifest_sha256=manifest_digest,
               raw_inputs_retained_outside_this_packet=True))
    for directory,label in ((previous,'source_review_packet'),(historical,'historical_campaigns')):
        before = {n:v.sha(p.read_bytes()) for n,p in v.files(directory,historical=True).items()}
        for name in sorted(before):
            data = v.safe_path(directory,name).read_bytes()
            v.require(v.sha(data) == before[name],'Historical payload changed')
            store(data,label+'/'+name,dict(kind='retained_prior_packet',
                  repository_path=(directory.relative_to(repo)/name).as_posix()))
        v.require(before == {n:v.sha(p.read_bytes()) for n,p in v.files(directory,historical=True).items()},
                  'Historical packet changed during export')
    for name,data in sorted(frozen.items()):
        store(data,'frozen_source/'+name,dict(kind='frozen_git_blob',revision=v.REVISION,path=name))
    catalog = dict(revision=v.REVISION,scientific_files=226,includes_toolchain_and_external_references=True,
                   sha256={n:v.sha(data) for n,data in sorted(frozen.items())})
    store((json.dumps(catalog,indent=1)+'\n').encode(),'frozen_source_catalog.json',
          dict(kind='verified_frozen_git_catalog'))
    for name in ('M1_FINAL_AI_REVIEW.md','M1_CANDIDATE_AUDIT.md','M1_FINAL_ACCEPTANCE_PLAN.md',
                 'M1_FULL_VALIDATION_PLAN.md','M1_FINAL_ARCHIVE_PLAN.md'):
        store((repo/'docs'/name).read_bytes(),'documents/'+name,
              dict(kind='current_review_context',repository_path='docs/'+name))
    store(Path(__file__).read_bytes(),'host_tools/pack_final_review_evidence.py',dict(kind='packager_source'))
    verifier = Path(__file__).with_name('verify_final_review_evidence.py')
    store(verifier.read_bytes(),'verify_final_review_evidence.py',dict(kind='portable_read_only_verifier'))
    record = dict(schema='openmhd.m1-final-review-evidence.v2',
        created_utc=datetime.now(timezone.utc).isoformat(),source_revision=v.REVISION,
        snapshot_sha256=v.SNAPSHOT,binary_sha256=v.BINARY,
        input_collection_manifest_sha256=manifest_digest,
        fresh_export=dict(selected_paths=sorted(selected),omitted_large_inputs=omitted),
        historical_boundary=v.BOUNDARY,
        current_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        full_m1_accepted=False,final_ai_output_review_passed=False,
        raw_input_scope='All238 actual inputs witnessed by complete collection and exact workflow receipts; raw duplicates explicitly omitted, not included or independently evolved here.',
        source_scope='Historical Git blobs; no perpetual development-working-tree requirement.',
        next='Separate reviewer pins evidence/sha256.json; review/, acceptance.json and outer closure are later siblings, never inserted into evidence/.',
        artifacts=artifacts)
    (out/'artifact_index.json').write_text(json.dumps(record,indent=1,allow_nan=False)+'\n')
    v.require(v.safe_path(source,'sha256.json').read_bytes() == original_bytes
        and input_manifest == v.verify_closed(source,'sha256.json'),'Collection changed during packaging')
    manifest = {n:v.sha(p.read_bytes()) for n,p in sorted(v.files(out).items())}
    (out/'sha256.json').write_text(json.dumps(manifest,indent=1)+'\n')
    # No reducer execution: shared portable consistency checks must also succeed.
    result = v.verify_evidence(out)
    print(json.dumps(dict(output=str(out),**result),indent=1,allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
