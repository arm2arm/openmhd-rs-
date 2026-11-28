"""Run one ordinary test from a qualified workspace build, retaining its original libtest logs."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

from workspace_catalog import selectors


def sha(data):
    return hashlib.sha256(data).hexdigest()


def install(archive, path, identity):
    compressed = Path(archive).read_bytes()
    if len(compressed) != identity["compressed_bytes"] or sha(compressed) != identity["compressed_sha256"]:
        raise ValueError("wrong compressed executable")
    body = gzip.decompress(compressed)
    if len(body) != identity["bytes"] or sha(body) != identity["sha256"]:
        raise ValueError("wrong parent executable")
    with path.open("xb") as fd:
        fd.write(body)
    path.chmod(0o700)


def main():
    case = json.loads(Path("case.json").read_bytes())
    catalog_bytes = Path("catalog.json").read_bytes()
    if sha(catalog_bytes) != case["catalog_sha256"]:
        raise ValueError("parent catalog changed")
    catalog = json.loads(catalog_bytes)
    if catalog["source"] != case["source"] or any(c["returncode"] for c in catalog["commands"]):
        raise ValueError("source/build outcome")
    t, = [t for t in catalog["targets"] if (t["manifest"], t["name"], t["kind"]) ==
          (case["manifest"], case["name"], case["kind"])]
    sel = case["selector"]
    selection = case.get("selection", "ordinary")
    if selection not in ("ordinary", "ignored"):
        raise ValueError("unknown libtest selection")
    if sel not in t["selectors"] or (sel in t["ignored"]) != (selection == "ignored") or t["binary"] != case["binary"]:
        raise ValueError("selector outside released workspace catalog")
    exe = Path("libtest").resolve()
    install("program.gz", exe, catalog["binaries"][t["binary"]])
    if (t["manifest"], t["name"]) == ("apps/openmhd/Cargo.toml", "restart"):
        root = Path("/tmp") / ("openmhd-m3-" + case["source"])
        if str(root) != catalog["target"] or not re.fullmatch("[a-f0-9]{40}", case["source"]):
            raise ValueError("Cargo application location")
        root.mkdir(mode=0o700)
        (root / "release").mkdir()
        install("application.gz", root / "release/vector-potential", catalog["binaries"][catalog["restart_application"]])
    env = dict(os.environ, RUST_TEST_THREADS="1", OPENMHD_TEST_THREADS="1", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    if int(env["RAYON_NUM_THREADS"]) != case["cpus"]:
        raise ValueError("workflow CPU declaration")
    if selectors(exe, env=env) != t["selectors"]:
        raise ValueError("downloaded binary has a different catalog")
    cmd = [str(exe), "--exact", sel, "--test-threads=1"]
    if selection == "ignored":
        if selectors(exe, ignored=True, env=env) != t["ignored"]:
            raise ValueError("downloaded binary has a different ignored catalog")
        cmd.extend(["--ignored", "--show-output"])
    start = time.monotonic()
    run = subprocess.run(cmd, env=env, capture_output=True, timeout=case["timeout"])
    Path("stdout.txt").write_bytes(run.stdout)
    Path("stderr.txt").write_bytes(run.stderr)
    lines = run.stdout.decode().splitlines()
    passed = (run.returncode == 0 and "running 1 test" in lines and
              "test " + sel + " ... ok" in lines and
              any(line.startswith("test result: ok. 1 passed; 0 failed; 0 ignored;") for line in lines))
    result = dict(case=case, returncode=run.returncode, passed=passed, seconds=time.monotonic()-start,
                  binary_sha256=sha(exe.read_bytes()), stdout_sha256=sha(run.stdout), stderr_sha256=sha(run.stderr))
    Path("result.json").write_text(json.dumps(result, sort_keys=True, indent=2)+"\n")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
