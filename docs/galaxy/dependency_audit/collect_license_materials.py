"""Retain candidate dependency license/notice sources; no build or adoption.

Run in the ignored metadata-audit directory containing audit.json and upstream/.
The copyright-comment scan is an overinclusive aid, not a legal completeness
certificate or a parser for arbitrary source-language comments.
"""
import gzip
import hashlib
import json
from pathlib import Path
import re
import tarfile


root = Path(__file__).resolve().parent
audit = json.loads((root / 'audit.json').read_text())
registry = Path.home() / '.cargo/registry/cache'
texts = {}
packages = {}


def retain(data):
    digest = hashlib.sha256(data).hexdigest()
    texts.setdefault(digest, data.decode('utf-8'))
    return digest


def blob_sha(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


for key, package in audit['packages'].items():
    name, version = package['name'], package['version']
    archive, = registry.glob('*/' + name + '-' + version + '.crate')
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == package['archive_sha256']
    files, comments = {}, {}
    with tarfile.open(archive) as packed:
        prefix = name + '-' + version + '/'
        for member in packed.getmembers():
            if not member.isfile():
                continue
            relative = member.name.removeprefix(prefix)
            leaf = Path(relative).name.upper()
            source = packed.extractfile(member).read()
            if leaf.startswith(('LICENSE', 'LICENCE', 'COPYING', 'COPYRIGHT', 'NOTICE', 'AUTHORS')):
                files[relative] = retain(source)
            elif name in ('meshless_voronoi', 'rstar', 'r-efi', 'wasip2') and relative in ('README.md', 'Cargo.toml.orig'):
                files[relative] = retain(source)
            if Path(relative).suffix.lower() in ('.rs', '.c', '.h', '.cc', '.cpp'):
                content = source.decode('utf-8')
                blocks = re.findall(r'/\*[\s\S]*?\*/|(?m:^[ \t]*//[^\n]*(?:\n[ \t]*//[^\n]*)*)', content)
                selected = [block for block in blocks if re.search(
                    r'copyright|SPDX-License|permission (?:is hereby|to use)|public domain', block, re.I)]
                if selected:
                    comments[relative] = dict(source_sha256=hashlib.sha256(source).hexdigest(),
                                             notice_text_sha256=[retain(block.encode()) for block in selected])
        vcs_path = prefix + '.cargo_vcs_info.json'
        vcs = json.loads(packed.extractfile(vcs_path).read()) if vcs_path in packed.getnames() else None
    option = 'MIT' if name in ('byteorder', 'libm', 'r-efi') else 'Apache-2.0'
    if name == 'unicode-ident':
        option += ' AND Unicode-3.0'
    packages[key] = dict(name=name, version=version, archive_sha256=package['archive_sha256'],
                         proposed_license_option=option, declared_license=package['declared_license'],
                         published_vcs=vcs, registry_materials=files, source_comment_notices=comments)

upstreams = {}
for path in sorted((root / 'upstream').glob('*/receipt.json')):
    report = json.loads(path.read_text())
    assert report['tree']['status'] == 200
    tree_bytes = Path(report['tree']['path']).read_bytes()
    assert hashlib.sha256(tree_bytes).hexdigest() == report['tree']['sha256']
    tree = json.loads(tree_bytes)
    assert tree['sha'] == report['commit'] and not tree['truncated']
    blobs = {entry['path']: entry['sha'] for entry in tree['tree'] if entry['type'] == 'blob'}
    published, = [package for package in packages.values() if package['name'] == report['package']]
    assert published['published_vcs']['git']['sha1'] == report['commit']
    materials = []
    for file in report.get('source_files', []):
        assert file['status'] == 200
        data = Path(file['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == file['sha256']
        assert blob_sha(data) == blobs[file['upstream_path']]
        materials.append(dict(upstream_path=file['upstream_path'], url=file['url'],
                              sha256=retain(data), git_blob_sha1=blobs[file['upstream_path']]))
    upstreams[report['package']] = dict(repository=report['repository'], commit=report['commit'],
        tree_url=report['tree']['url'], tree_sha256=report['tree']['sha256'],
        license_paths_in_complete_tree=report['license_paths_in_tree'], materials=materials)

result = dict(schema='openmhd.geometry3.dependency-license-source-materials.v1',
    date='2026-11-22', source_collector_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    audit_json_sha256=hashlib.sha256((root / 'audit.json').read_bytes()).hexdigest(),
    status='Proposed options and retained primary license/notice sources, pending independent distribution review; dependency not adopted.',
    packages=packages, pinned_upstreams=upstreams, texts_by_sha256=texts,
    limitations=[
        'The source-comment scan is an overinclusive aid, not a complete legal/source-language parser.',
        'The original filename scan omitted AUTHORS and workspace-root licenses; absence of LICENSE-named files is not absence of a grant.',
        'meshless_voronoi README explicitly offers Apache-2.0 or MIT with ibig/dashu/num_bigint; the locked graphs select ibig only. No standalone license/notice file occurs in its pinned tree.',
        'Proposed Apache options require the complete applicable license and supplied notices; MIT-only choices and Unicode-3.0 retain their own terms. Final packaging must be reviewed for the actual integrated graph and artifact.',
        'No compilation, build-script execution, geometry probe, numerical test, adoption or legal completeness certification is performed.'
    ], dependency_adopted=False, independent_review_passed=False)
target = root / 'license_materials.json.gz'
assert not target.exists(), 'Never overwrite a retained source observation'
target.write_bytes(gzip.compress((json.dumps(result, indent=1) + '\n').encode(), mtime=0))
print('Packages:', len(packages), 'retained distinct texts:', len(texts),
      'copyright-comment source files:', sum(len(p['source_comment_notices']) for p in packages.values()))
print('Retained material bytes:', target.stat().st_size)
