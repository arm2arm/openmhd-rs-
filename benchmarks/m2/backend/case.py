"""Execute one frozen, single-threaded REANA selection and preserve its raw outcome."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    run = json.loads(Path("case.json").read_bytes())
    exe = Path("benchmark")
    binary = b"".join(Path(n).read_bytes() for n in run["binary_parts"])
    if sha(binary) != run["binary_sha256"]:
        raise ValueError("benchmark executable identity")
    exe.write_bytes(binary)
    exe.chmod(0o755)
    if any(os.environ.get(k) != "1" for k in ("OMP_NUM_THREADS", "RAYON_NUM_THREADS", "OPENBLAS_NUM_THREADS")):
        raise ValueError("one-thread execution environment")
    argv = [str(exe.resolve()), run["backend"], run["fixture"]]
    started = time.monotonic()
    timed_out = False
    with open("stdout.txt", "xb") as stdout, open("stderr.txt", "xb") as stderr:
        try:
            rc = subprocess.run(argv, stdout=stdout, stderr=stderr, timeout=run["timeout_seconds"]).returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            rc = None
    elapsed = time.monotonic() - started
    raw = Path("stdout.txt").read_bytes()
    Path("stdout.txt.gz").write_bytes(gzip.compress(raw, mtime=0))
    result = dict(case=run, exit_code=rc, timed_out=timed_out, elapsed_seconds=elapsed,
                  architecture=platform.machine(), stdout_sha256=sha(raw),
                  stderr_sha256=sha(Path("stderr.txt").read_bytes()))
    Path("result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
