"""Prepare readable candidate notices from checked source bytes, without a build.

This preserves the original audit observations. It neither adopts dependencies
nor certifies an integrated release. The output directory must not exist.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json_gz(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def relative_path(value):
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        raise ValueError("Unsafe or noncanonical material path: " + value)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    packet = Path(__file__).resolve().parent
    repository = packet.parents[2]
    audit = read_json_gz(packet / "audit.json.gz")
    materials = read_json_gz(packet / "license_materials.json.gz")
    texts = materials["texts_by_sha256"]
    for digest, text in texts.items():
        assert sha(text.encode("utf-8")) == digest
    assert materials["audit_json_sha256"] == sha(
        gzip.decompress((packet / "audit.json.gz").read_bytes()))
    assert set(audit["packages"]) == set(materials["packages"])
    assert len(materials["packages"]) == 33
    destination = args.destination
    if destination.exists():
        raise FileExistsError("Retain existing output; choose a new destination")

    # Validate all archive identities before writing output. No member executes.
    archives = {}
    cache = Path.home() / ".cargo/registry/cache"
    for key, package in materials["packages"].items():
        archive, = cache.glob("*/" + package["name"] + "-" + package["version"] + ".crate")
        digest = sha(archive.read_bytes())
        assert digest == package["archive_sha256"] == audit["packages"][key]["archive_sha256"]
        archives[key] = archive

    # Exact D1 omission from the independently checked published archive.
    glam_key, = [key for key, p in materials["packages"].items() if p["name"] == "glam"]
    glam = materials["packages"][glam_key]
    assert glam["version"] == "0.27.0"
    with tarfile.open(archives[glam_key]) as archive:
        attribution = archive.extractfile("glam-0.27.0/ATTRIBUTION.md").read()
        glam_readme = archive.extractfile("glam-0.27.0/README.md").read()
    assert len(attribution) == 3718
    assert sha(attribution) == "9f0738ead3dcc72bac87afc652c2466e1bc130d235db7798f98da4d4ef013639"
    assert hashlib.sha1(b"blob 3718\0" + attribution).hexdigest() == "34ae900e9c0706e51b9bb78a8fc0c8f1a8a03be8"
    assert glam["published_vcs"]["git"]["sha1"] == "9f694bcc56808716eb269a5489a214b4e47df026"

    files, package_records = {}, {}

    def write(relative, data):
        relative_path(relative)
        if relative in files:
            assert files[relative]["sha256"] == sha(data)
            return
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        files[relative] = dict(bytes=len(data), sha256=sha(data))

    write("LICENSE", (repository / "LICENSE").read_bytes())
    table = []
    for key, package in sorted(materials["packages"].items()):
        name, version = package["name"], package["version"]
        prefix = "licenses/" + name + "-" + version + "/"
        record = dict(name=name, version=version,
                      archive_sha256=package["archive_sha256"],
                      elected_option=package["proposed_license_option"],
                      declared_license=package["declared_license"],
                      materials={}, source_notice_files={})
        with tarfile.open(archives[key]) as archive:
            archive_prefix = name + "-" + version + "/"
            for path, digest in package["registry_materials"].items():
                relative_path(path)
                data = archive.extractfile(archive_prefix + path).read()
                assert sha(data) == digest and data == texts[digest].encode("utf-8")
                write(prefix + path, data)
                record["materials"][path] = dict(origin="checked registry archive", sha256=digest)

            # Retain every selected comment, with source path/hash and byte sizes.
            # This is not an exhaustive source-notice scan or source distribution.
            notices = ["Selected exact source notices; preserve complete original files in source releases.\n"]
            for path, source in sorted(package["source_comment_notices"].items()):
                data = archive.extractfile(archive_prefix + path).read()
                assert sha(data) == source["source_sha256"]
                notices.append("\nSOURCE " + path + "\nSHA256 " + sha(data) + "\n")
                for digest in source["notice_text_sha256"]:
                    block = texts[digest].encode("utf-8")
                    assert block in data
                    notices.append("NOTICE SHA256 " + digest + " BYTES " + str(len(block)) + "\n")
                    notices.append(block.decode("utf-8"))
                    notices.append("\nEND NOTICE\n")
                record["source_notice_files"][path] = source
            if package["source_comment_notices"]:
                write(prefix + "SOURCE_NOTICES.txt", "".join(notices).encode("utf-8"))

        upstream = materials["pinned_upstreams"].get(name)
        if upstream:
            for source in upstream["materials"]:
                path, digest = source["upstream_path"], source["sha256"]
                write(prefix + path, texts[digest].encode("utf-8"))
                record["materials"][path] = dict(origin="pinned upstream supplement", **source)
        if name == "meshless_voronoi":
            # The conditional README grant names Apache 2.0 but omits its text.
            source, = [s for s in materials["pinned_upstreams"]["rstar"]["materials"]
                       if s["upstream_path"] == "LICENSE-APACHE"]
            write(prefix + "LICENSE-APACHE", texts[source["sha256"]].encode("utf-8"))
            record["materials"]["LICENSE-APACHE"] = dict(
                origin="complete standard Apache-2.0 text, retained rstar root supplement",
                **source)
        if name == "glam":
            write(prefix + "ATTRIBUTION.md", attribution)
            write(prefix + "README.md", glam_readme)
            record["materials"]["ATTRIBUTION.md"] = dict(
                origin="checked registry archive; independent review D1",
                bytes=len(attribution), sha256=sha(attribution),
                git_blob_sha1="34ae900e9c0706e51b9bb78a8fc0c8f1a8a03be8",
                published_commit=glam["published_vcs"]["git"]["sha1"],
                additive_terms="Three MIT grants: DirectXMath, Realtime Math, GLM")
            record["materials"]["README.md"] = dict(origin="checked registry archive", sha256=sha(glam_readme))
        package_records[key] = record
        table.append("| " + name + " " + version + " | " + record["elected_option"] +
                     " | [materials](" + prefix + ") | `" + package["archive_sha256"] + "` |")

    index = """# Candidate third-party license and attribution bundle

This is a readable packaging candidate for the isolated, metadata-only
`meshless_voronoi =0.7.2`, default-features=false, ibig-only dependency graph.
It does not adopt that graph, ship a simulator binary or certify a release.
OpenMHD's own MIT terms are in LICENSE. Dependencies retain their own terms.

All 33 audited registry packages are included conservatively; this does not
claim all are incorporated in a particular target binary. Host/build versus
target reachability and the actual integrated graph require a fresh review.
The elected alternatives below do not make all retained OR alternatives
cumulative. Additive incorporated-code conditions still apply, including
glam's three MIT grants and unicode-ident's Unicode-3.0 terms.

| Package | Elected option | Readable material location | Checked archive SHA-256 |
| --- | --- | --- | --- |
""" + "\n".join(table) + """

Each package directory retains original material filenames. Pinned upstream
root licenses supplement rstar and wasip2. The mesh README contains its
backend-conditional grant; a complete standard Apache-2.0 copy is supplied.
r-efi retains AUTHORS, unicode-ident retains LICENSE-UNICODE, and glam retains
the entire ATTRIBUTION.md including all three additive MIT notices.

SOURCE_NOTICES.txt files preserve the original selected comments, labelled
by complete source-file SHA-256, comment SHA-256 and UTF-8 byte length. In
particular, libm's full LICENSE.txt and all 69 selected source-notice records
are retained, including notices requiring binary-documentation retention.
These files are readable notices, not executable source or a complete source
notice census. The old 213-record scanner missed some provenance comments
and non-Rust headers; its limitations are preserved, not treated as closure.

For a source release, preserve the complete original source archives/headers,
including heapless build.rs and src/pool/arc.rs provenance and zerocopy's
non-Rust headers, and include the supplements above. Prominently mark any
modified dependency files. This notice-only directory does not replace those
sources. For a binary, installer or container, include this readable index,
license/attribution files and OpenMHD LICENSE with the artifact; a developer
cache or compressed audit database alone does not satisfy that layout.

Before distribution, independently inspect the integrated graph and final
artifact's readable notice paths, source modifications and actual contents.
This candidate has no simulator binary, installer, container or vendored
source release to inspect. Its documentary hashes do not accept dependency
adoption, compilation, M1, geometry or moving-MHD physics. The original audit
and independent review remain historical observations with their old hashes.
"""
    write("THIRD_PARTY.md", index.encode("utf-8"))
    receipt = dict(schema="openmhd.geometry3.readable-notice-candidate.v1",
                   prepared_on="2026-11-22", dependency_adopted=False,
                   final_artifact_reviewed=False, independent_revision_review_passed=False,
                   source_builder_sha256=sha(Path(__file__).read_bytes()),
                   original_audit_gzip_sha256=sha((packet / "audit.json.gz").read_bytes()),
                   original_materials_gzip_sha256=sha((packet / "license_materials.json.gz").read_bytes()),
                   original_review_report_sha256=sha((packet.parent / "MESH_DEPENDENCY_REVIEW.md").read_bytes()),
                   package_count=len(package_records), packages=package_records,
                   files=dict(sorted(files.items())))
    write("materials.json", (json.dumps(receipt, indent=2) + "\n").encode("utf-8"))
    (destination / "sha256.json").write_text(json.dumps(dict(
        schema="openmhd.source-packet-sha256.v1",
        files={path: data["sha256"] for path, data in sorted(files.items())}), indent=2) + "\n")
    print(json.dumps(dict(packages=len(package_records), payload_files=len(files),
                          glam_attribution_sha256=sha(attribution),
                          dependency_adopted=False, final_artifact_reviewed=False)))


if __name__ == "__main__":
    main()
