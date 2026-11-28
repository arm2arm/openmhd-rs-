"""Compile and discover the workspace on REANA. No test methods execute in this job."""
import gzip
import json
from pathlib import Path
import subprocess

from workspace_catalog import selectors
from remote import OUTPUT, RUNTIME, SOURCE, WORK, environment, extract, sha, verify_source


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def main():
    snap = json.loads((WORK / "snapshot.json").read_bytes())
    verify_source(snap)
    source_id = snap["source_revision"]
    vendor = RUNTIME / "test-vendor"
    vendor.mkdir()
    extract(WORK / "vendor.tar.gz", vendor, regular_only=True)
    cargo = RUNTIME / "cargo"
    cargo.mkdir(exist_ok=True)
    (cargo / "config.toml").write_text('[source.crates-io]\nreplace-with="vendored"\n'
        '[source.vendored]\ndirectory=' + json.dumps(str(vendor)) + '\n')
    # Cargo embeds this path in its restart integration test binary. Independent
    # test pods install the exact parent application at the same private /tmp path.
    target = Path("/tmp") / ("openmhd-m3-" + source_id)
    target.mkdir(mode=0o700)
    env = dict(environment(), CARGO_NET_OFFLINE="true", CARGO_TARGET_DIR=str(target))
    out = OUTPUT / "regression"
    out.mkdir()
    records = dict(source=source_id, target=str(target), runtime=sha(OUTPUT / "runtime.json"),
                   vendor=sha(WORK / "vendor.tar.gz"), locked=sha(SOURCE / "Cargo.lock"),
                   commands=[], targets=[], binaries={})
    commands = [
        ["cargo", "fmt", "--all", "--", "--check"],
        ["cargo", "clippy", "--workspace", "--all-targets", "--all-features", "--locked",
         "--offline", "--", "-D", "warnings"],
        ["cargo", "test", "--workspace", "--release", "--locked", "--offline", "--all-features",
         "--no-run", "--message-format=json"],
    ]
    for i, cmd in enumerate(commands):
        log = out / f"build-{i}.log"
        with log.open("xb") as fd:
            rc = subprocess.run(cmd, env=env, cwd=SOURCE, stdout=fd, stderr=subprocess.STDOUT).returncode
        records["commands"].append(dict(argv=cmd, returncode=rc, sha256=sha(log)))
        write(out / "catalog.json", records)
        if rc:
            raise SystemExit(rc)

    def export(exe):
        key = sha(exe)
        if key not in records["binaries"]:
            dest = out / "stripped"
            subprocess.run(["strip", "-o", str(dest), str(exe)], check=True)
            archive = out / (key + ".gz")
            archive.write_bytes(gzip.compress(dest.read_bytes(), compresslevel=4, mtime=0))
            records["binaries"][key] = dict(sha256=sha(dest), bytes=dest.stat().st_size,
                compressed_sha256=sha(archive), compressed_bytes=archive.stat().st_size)
            dest.unlink()
        return key

    messages = [json.loads(line) for line in log.read_bytes().splitlines() if line.startswith(b"{")]
    for m in messages:
        if m.get("reason") != "compiler-artifact" or not m.get("executable"):
            continue
        exe = Path(m["executable"])
        if not m["profile"]["test"]:
            if m["target"]["name"] == "vector-potential" and m["target"]["kind"] == ["bin"]:
                if exe != target / "release/vector-potential":
                    raise ValueError("unexpected checkpoint integration application path")
                records["restart_application"] = export(exe)
            continue
        path = Path(m["manifest_path"]).relative_to(SOURCE).as_posix()
        name = m["target"]["name"]
        names = selectors(exe)
        ignored = selectors(exe, ignored=True)
        if not set(ignored) <= set(names):
            raise ValueError("ignored libtest case missing from catalog")
        records["targets"].append(dict(manifest=path,name=name,kind=m["target"]["kind"],selectors=names,
            ignored=ignored,binary=export(exe) if names else None))
    if not records.get("restart_application") or not records["targets"]:
        raise ValueError("workspace or restart application missing")
    ids = [(x["manifest"], x["name"], tuple(x["kind"])) for x in records["targets"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate workspace target")
    verify_source(snap)
    write(out / "catalog.json", records)


if __name__ == "__main__":
    main()
