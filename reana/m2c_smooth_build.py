"""Build the frozen M2c smooth-step executable and discover its regression controls."""
import gzip
import json
from pathlib import Path
import subprocess
from remote import OUTPUT, RUNTIME, SOURCE, WORK, environment, extract, sha, verify_source


def main():
    snapshot = json.loads((WORK / "snapshot.json").read_bytes())
    verify_source(snapshot)
    vendor = RUNTIME / "vendor"
    vendor.mkdir()
    extract(WORK / "vendor.tar.gz", vendor, regular_only=True)
    cargo = RUNTIME / "cargo"
    cargo.mkdir(exist_ok=True)
    (cargo / "config.toml").write_text('[source.crates-io]\nreplace-with="vendored"\n'
        '[source.vendored]\ndirectory=' + json.dumps(str(vendor)) + '\n')
    env = dict(environment(), CARGO_NET_OFFLINE="true", CARGO_BUILD_JOBS="4")
    out = OUTPUT / "smooth"
    out.mkdir()
    report = dict(source=snapshot["source_revision"], lock=sha(SOURCE / "Cargo.lock"),
                  vendor=sha(WORK / "vendor.tar.gz"), runtime=sha(OUTPUT / "runtime.json"),
                  commands=[], programs={})
    commands = [
        ["cargo", "fmt", "--all", "--", "--check"],
        ["cargo", "clippy", "--workspace", "--all-targets", "--all-features", "--locked",
         "--offline", "--", "-D", "warnings"],
        ["cargo", "build", "--release", "--locked", "--offline", "-p", "mhd-vector-pot",
         "--example", "m2c-smooth-step", "--message-format=json"],
        ["cargo", "test", "--release", "--locked", "--offline", "-p", "mhd-vector-pot",
         "--lib", "--test", "m2c_coupled", "--no-run", "--message-format=json"],
    ]
    def save():
        (out / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    for i, cmd in enumerate(commands):
        log = out / f"build-{i}.log"
        with log.open("xb") as f:
            rc = subprocess.run(cmd, cwd=SOURCE, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
        report["commands"].append(dict(argv=cmd, returncode=rc, sha256=sha(log)))
        save()
        if rc:
            raise SystemExit(rc)
        if i >= 2:
            for line in log.read_text().splitlines():
                if not line.startswith("{"):
                    continue
                msg = json.loads(line)
                if msg.get("reason") != "compiler-artifact" or not msg.get("executable"):
                    continue
                program = msg["target"]["name"]
                if program not in ("m2c-smooth-step", "m2c_coupled", "mhd_vector_pot"):
                    continue
                binary = Path(msg["executable"])
                selectors = []
                if i == 3:
                    listing = subprocess.check_output([binary, "--list", "--format", "terse"], text=True)
                    selectors = [s[:-6] for s in listing.splitlines() if s.endswith(": test")
                                 and (program == "m2c_coupled" or s.startswith("moving3::"))]
                    if not selectors:
                        raise ValueError("missing test selectors")
                stripped = out / program
                subprocess.run(["strip", "-o", stripped, binary], check=True)
                data = stripped.read_bytes()
                zipped = out / (program + ".gz")
                zipped.write_bytes(gzip.compress(data, compresslevel=6, mtime=0))
                report["programs"][program] = dict(sha256=sha(stripped), bytes=len(data),
                    compressed_sha256=sha(zipped), selectors=selectors)
    if set(report["programs"]) != {"m2c-smooth-step", "m2c_coupled", "mhd_vector_pot"}:
        raise ValueError("incomplete program catalog")
    verify_source(snapshot)
    save()


if __name__ == "__main__":
    main()

