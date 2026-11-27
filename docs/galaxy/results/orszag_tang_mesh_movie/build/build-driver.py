"""Remote locked build for the time-resolved planar Orszag-Tang background."""
import hashlib
import json
import subprocess
from pathlib import Path
from remote import OUTPUT, SOURCE, WORK, environment, verify_source

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    snap = json.loads((WORK / "snapshot.json").read_bytes())
    verify_source(snap)
    destination = OUTPUT / "orszag-flow"
    destination.mkdir()
    env = dict(environment(), CARGO_NET_OFFLINE="true")
    commands = [
        ["cargo", "fmt", "--all", "--", "--check"],
        ["cargo", "clippy", "--workspace", "--all-targets", "--all-features", "--locked", "--offline", "--", "-D", "warnings"],
        ["cargo", "build", "--release", "--locked", "--offline", "-p", "mhd-planar","--example","orszag-tang-flow","--message-format=json"],
    ]
    report = dict(source_revision=snap["source_revision"], runtime_sha256=digest(OUTPUT / "runtime.json"), commands=[], executables={})
    def save():
        (destination / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    for i, command in enumerate(commands):
        log = destination / f"build-{i}.log"
        with log.open("xb") as stream:
            done = subprocess.run(command, cwd=SOURCE, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=1200)
        report["commands"].append(dict(argv=command, returncode=done.returncode, sha256=digest(log)))
        save()
        if done.returncode:
            raise RuntimeError(log.read_text()[-5000:])
    messages = [json.loads(line) for line in log.read_text().splitlines() if line.startswith("{")]
    tests, = [Path(m["executable"]) for m in messages if m.get("reason")=="compiler-artifact" and m["target"]["name"]=="orszag-tang-flow" and m.get("executable")]
    for name, binary in {"orszag-flow": tests}.items():
        compact = destination / name
        subprocess.run(["strip", "-o", str(compact), str(binary)], check=True)
        if compact.read_bytes()[:4] != b"\x7fELF":
            raise ValueError("Expected Linux executable")
        report["executables"][name] = dict(sha256=digest(compact), original_sha256=digest(binary))
    verify_source(snap)
    save()

if __name__ == "__main__":
    main()
