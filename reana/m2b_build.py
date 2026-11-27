"""Compile M2b drivers with the installed immutable REANA Rust toolchain."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from remote import SOURCE, OUTPUT, WORK, environment, verify_source

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main(names):
    snapshot = json.loads((WORK / "snapshot.json").read_bytes())
    env = dict(environment(), CARGO_NET_OFFLINE="true")
    dst = OUTPUT / "m2b"
    dst.mkdir()
    output = dict(source_revision=snapshot["source_revision"], snapshot_sha256=sha(WORK/"snapshot.json"),
                  runtime_sha256=sha(OUTPUT/"runtime.json"), commands=[], binaries={})
    commands = [["cargo","fmt","--all","--","--check"],
                ["cargo","clippy","--workspace","--all-targets","--all-features","--locked","--offline","--","-D","warnings"],
                ["cargo","build","--release","--locked","--offline","-p","mhd-vector-pot",
                 *[arg for name in names for arg in ("--example",name)]]]
    for i,cmd in enumerate(commands):
        path=dst/f"{i}.log"
        with path.open("xb") as stream:
            run=subprocess.run(cmd,cwd=SOURCE,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=1500)
        output["commands"].append(dict(argv=cmd,returncode=run.returncode,log_sha256=sha(path)))
        (dst/"build.json").write_text(json.dumps(output,indent=2)+"\n")
        if run.returncode:
            sys.stderr.write(path.read_text()[-12000:]);return run.returncode
    for name in names:
        path=SOURCE/"target/release/examples"/name
        if not path.read_bytes().startswith(b"\x7fELF"):raise ValueError("Expected ELF build product")
        target=dst/name
        # Keep the portable executable under REANA's transfer-size boundary.
        subprocess.run(["strip","-o",str(target),str(path)],check=True)
        output["binaries"][name]=dict(whole_sha256=sha(path),sha256=sha(target),bytes=target.stat().st_size)
    verify_source(snapshot)
    (dst/"build.json").write_text(json.dumps(output,indent=2)+"\n")
    return 0

if __name__=="__main__":
    sys.exit(main(sys.argv[1:]))
