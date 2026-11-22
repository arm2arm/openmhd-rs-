"""Read Cargo's resolved metadata and retained registry/license bytes; no build."""
import hashlib
import json
from pathlib import Path
import tarfile
import tomllib


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


root = Path(__file__).resolve().parent
lock = tomllib.loads((root/'Cargo.lock').read_text())
checksums = {(p['name'], p['version']): p.get('checksum') for p in lock['package']}
graphs, packages = {}, {}
for target in ('all_targets', 'linux', 'macos'):
    metadata_path = root/('metadata_'+target+'.json')
    metadata = json.loads(metadata_path.read_text())
    nodes = {node['id']: node for node in metadata['resolve']['nodes']}
    reached = {metadata['resolve']['root']}
    while True:
        updated = reached | {edge['pkg'] for key in reached for edge in nodes[key]['deps']}
        if updated == reached:
            break
        reached = updated
    reached.remove(metadata['resolve']['root'])
    graphs[target] = dict(original_metadata_sha256=sha(metadata_path),
                          packages=sorted(reached),
                          nodes={key: nodes[key] for key in sorted(reached)})
    for package in metadata['packages']:
        key = package['id']
        if key not in reached or key in packages:
            continue
        manifest = Path(package['manifest_path'])
        source = manifest.parent
        checksum = checksums[package['name'], package['version']]
        archive = (source.parents[2]/'cache'/source.parent.name /
                   (package['name']+'-'+package['version']+'.crate'))
        assert sha(archive) == checksum, package['name']
        license_files = {}
        with tarfile.open(archive) as packed:
            for file in sorted(source.rglob('*')):
                if file.is_file() and file.name.upper().startswith(('LICENSE', 'COPYING', 'COPYRIGHT')):
                    relative = str(file.relative_to(source))
                    digest = sha(file)
                    original = packed.extractfile(source.name+'/'+relative).read()
                    assert hashlib.sha256(original).hexdigest() == digest
                    license_files[relative] = digest
        build_scripts = {str(Path(item['src_path']).relative_to(source)):
                         sha(Path(item['src_path'])) for item in package['targets']
                         if 'custom-build' in item['kind']}
        packages[key] = dict(name=package['name'], version=package['version'],
                             source=package['source'], archive_sha256=checksum,
                             archive_bytes=archive.stat().st_size,
                             manifest_sha256=sha(manifest),
                             declared_license=package['license'],
                             declared_license_file=package['license_file'],
                             actual_license_file_sha256=license_files,
                             custom_build_source_sha256=build_scripts,
                             rust_version=package['rust_version'])

report = dict(schema='openmhd.geometry3.dependency-metadata-audit.v1',
              status='metadata and retained source-byte audit only; not a build, numerical probe or dependency adoption',
              prepared_on='2026-11-22',
              cargo='cargo 1.85.1 (d73d2caf9 2024-12-31)',
              rustc='rustc 1.85.1 (4eb161250 2025-03-15)',
              metadata_execution_host='aarch64-apple-darwin',
              selected_dependency=dict(name='meshless_voronoi', version='=0.7.2',
                                       default_features=False, features=['ibig']),
              inputs={name: sha(root/name) for name in ('Cargo.toml', 'Cargo.lock', 'metadata-only.rs')},
              collection_source_sha256=sha(Path(__file__)), graphs=graphs, packages=packages,
              unresolved=['The meshless_voronoi, rstar, r-efi and wasip2 archives lack standalone license/notice texts under LICENSE/COPYING/COPYRIGHT names; declared metadata is not complete distribution packaging. The first two are reachable on the audited Linux/macOS paths. Resolve grants/notices before adoption.',
                          'Actual builds, build-script effects, target/feature regression and license/notice distribution closure remain unperformed.',
                          'The audit lock is for an isolated scratch package, not the project Cargo.lock. Any adoption must preserve or re-audit the actual integrated resolution.'],
              dependency_adopted=False, numerical_execution=False, license_distribution_closure_accepted=False)
(root/'audit.json').write_text(json.dumps(report, indent=1)+'\n')
print('Registry archives verified:', len(packages))
print('Reachable target package counts:', {key: len(value['packages']) for key, value in graphs.items()})
print('Packages without standalone license files:', [p['name'] for p in packages.values() if not p['actual_license_file_sha256']])
