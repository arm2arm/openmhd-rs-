"""Read pinned upstream license/source identities; no build or code execution."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request


root = Path(__file__).resolve().parent / 'upstream'
root.mkdir(exist_ok=True)
projects = [
    ('meshless_voronoi', 'yuyttenhove/meshless_voro', '3120dc9e75f12e1a1dc73bfde3797fbdce2459ed'),
    ('rstar', 'georust/rstar', 'c8c5bf9e41468281d030869d409e3f67f1aaf5b7'),
    ('r-efi', 'r-efi/r-efi', '97b55bed1c2c91dcbf787674849f05337ff80b33'),
    ('wasip2', 'bytecodealliance/wasi-rs', '3da562c06214feafc14d37bf290671636caa6718'),
]


def fetch(url, destination):
    assert not destination.exists(), 'Do not replace retained source observations'
    request = urllib.request.Request(url, headers={'User-Agent': 'OpenMHD-RS-source-audit'})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
            destination.write_bytes(data)
            return dict(url=url, final_url=response.url, status=response.status,
                        path=str(destination), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    except urllib.error.HTTPError as error:
        data = error.read()
        destination.write_bytes(data)
        return dict(url=url, status=error.code, path=str(destination), bytes=len(data),
                    sha256=hashlib.sha256(data).hexdigest(), successful_source=False)


def one(project):
    name, repository, commit = project
    directory = root / name
    directory.mkdir(exist_ok=True)
    tree_path = directory / 'tree.json'
    tree_receipt = fetch('https://api.github.com/repos/' + repository + '/git/trees/' + commit + '?recursive=1', tree_path)
    report = dict(package=name, repository=repository, commit=commit, tree=tree_receipt)
    if tree_receipt['status'] == 200:
        tree = json.loads(tree_path.read_text())
        assert tree['sha'] == commit and not tree['truncated']
        paths = [entry['path'] for entry in tree['tree'] if entry['type'] == 'blob'
                 and Path(entry['path']).name.upper().startswith(('LICENSE', 'LICENCE', 'COPYING', 'COPYRIGHT', 'NOTICE', 'AUTHORS'))]
        report['license_paths_in_tree'] = paths
        report['source_files'] = []
        for index, path in enumerate(paths):
            receipt = fetch('https://raw.githubusercontent.com/' + repository + '/' + commit + '/' + path,
                            directory / (str(index) + '-' + Path(path).name))
            receipt['upstream_path'] = path
            report['source_files'].append(receipt)
    (directory / 'receipt.json').write_text(json.dumps(report, indent=1) + '\n')
    return dict(package=name, status=tree_receipt['status'], paths=report.get('license_paths_in_tree'))


with ThreadPoolExecutor(max_workers=4) as pool:
    for report in pool.map(one, projects):
        print(json.dumps(report))
