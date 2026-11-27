"""Build the two release examples used for the gravity evolution visualization."""
import hashlib
import json
from pathlib import Path
import subprocess

from remote import OUTPUT, SOURCE, WORK, environment, verify_source


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    snap = json.loads((WORK / "snapshot.json").read_bytes())
    verify_source(snap)
    destination = OUTPUT / "gravity"
    destination.mkdir()
    env = dict(environment(), CARGO_NET_OFFLINE="true")
    examples = {"gravity-trajectory": "gravity", "geometry3-case": "moving-mesh"}
    commands = [
        ["cargo", "fmt", "--all", "--", "--check"],
        ["cargo", "clippy", "--locked", "--offline", "-p", "gravity", "-p", "moving-mesh",
         "--all-targets", "--all-features", "--", "-D", "warnings"],
        *[["cargo", "build", "--release", "--locked", "--offline", "-p", package, "--example", example]
          for example, package in examples.items()],
    ]
    report = dict(source_revision=snap["source_revision"], runtime_sha256=digest(OUTPUT / "runtime.json"),
                  commands=[], executables={})
    for i, command in enumerate(commands):
        log = destination / f"build-{i}.log"
        with log.open("xb") as stream:
            done = subprocess.run(command, cwd=SOURCE, env=env, stdout=stream,
                                  stderr=subprocess.STDOUT, timeout=1200)
        report["commands"].append(dict(argv=command, returncode=done.returncode, sha256=digest(log)))
        (destination / "build.json").write_text(json.dumps(report, indent=2) + "\n")
        if done.returncode:
            raise RuntimeError(log.read_text()[-8000:])
    for name in examples:
        binary = SOURCE / "target/release/examples" / name
        compact = destination / name
        subprocess.run(["strip", "-o", str(compact), str(binary)], check=True)
        if compact.read_bytes()[:4] != b"\x7fELF":
            raise ValueError("Expected Linux executable")
        report["executables"][name] = dict(sha256=digest(compact), original_sha256=digest(binary))
    verify_source(snap)
    (destination / "build.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
