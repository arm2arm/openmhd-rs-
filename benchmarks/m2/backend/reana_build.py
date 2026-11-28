"""Build the benchmark from the source and vendored Cargo inputs verified by remote.prepare."""
import json
from pathlib import Path
import shutil
import subprocess

from remote import OUTPUT, RUNTIME, SOURCE, WORK, environment, extract, sha, verify_source


def main():
    snapshot = json.loads((WORK / "snapshot.json").read_bytes())
    verify_source(snapshot)
    vendor_archive = WORK / "vendor.tar.gz"
    if sha(vendor_archive) != snapshot["archives"][vendor_archive.name]["sha256"]:
        raise ValueError("vendored package archive changed")
    vendor = RUNTIME / "benchmark-vendor"
    vendor.mkdir()
    extract(vendor_archive, vendor, regular_only=True)
    cargo_home = RUNTIME / "cargo"
    cargo_home.mkdir(exist_ok=True)
    config = cargo_home / "config.toml"
    if config.exists():
        raise ValueError("unexpected Cargo source selection")
    config.write_text('[source.crates-io]\nreplace-with = "bench-source"\n[source.bench-source]\ndirectory = ' +
                      json.dumps(str(vendor)) + '\n')
    work = SOURCE / "benchmarks/m2/backend"
    out = OUTPUT / "benchmark"
    out.mkdir()
    env = dict(environment(), CARGO_NET_OFFLINE="true")
    report = dict(source=snapshot["source_revision"], vendor_sha256=sha(vendor_archive),
                  runtime_sha256=sha(OUTPUT / "runtime.json"), lock_sha256=sha(work / "Cargo.lock"), commands=[])
    commands = [["cargo", "fmt", "--", "--check"],
                ["cargo", "clippy", "--locked", "--offline", "--all-targets", "--", "-D", "warnings"],
                ["cargo", "build", "--locked", "--offline", "--release"]]
    for i, cmd in enumerate(commands):
        log = out / f"build-{i}.log"
        with log.open("xb") as f:
            r = subprocess.run(cmd, cwd=work, env=env, stdout=f, stderr=subprocess.STDOUT)
        report["commands"].append(dict(argv=cmd, returncode=r.returncode, log_sha256=sha(log)))
        (out / "build.json").write_text(json.dumps(report, indent=2) + "\n")
        if r.returncode != 0:
            raise SystemExit(r.returncode)
    binary = out / "m2-backend-benchmark"
    shutil.copyfile(work / "target/release" / binary.name, binary)
    report["binary_sha256"] = sha(binary)
    verify_source(snapshot)
    (out / "build.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
