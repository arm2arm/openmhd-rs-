"""Execute exactly one declared leaf or physical case using the parent executable."""
from pathlib import Path
import gzip
import hashlib
import json
import subprocess
import time


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    case = json.loads(Path("case.json").read_bytes())
    raw = gzip.decompress(Path("program.gz").read_bytes())
    if digest(raw) != case["program_sha256"]:
        raise ValueError("executable differs from the immutable build")
    exe = Path("program")
    exe.write_bytes(raw)
    exe.chmod(0o755)
    started = time.monotonic()
    done = subprocess.run([str(exe.resolve()), *case["args"]], capture_output=True, timeout=case["timeout"])
    elapsed = time.monotonic() - started
    out = done.stdout
    if case["kind"] == "test":
        selected = case["args"][1]
        observed = b"running 1 test\n" in out and ("test " + selected + " ... ok").encode() in out and b"test result: ok. 1 passed;" in out
    else:
        count = int(case["args"][4]) ** 3
        observed = (sum(s.startswith(b"INITIAL ") for s in out.splitlines()) == count
                    and sum(s.startswith(b"FINAL ") for s in out.splitlines()) == count
                    and sum(s.startswith(b"STAGE ") for s in out.splitlines()) == 2 * int(case["args"][2])
                    and sum(s.startswith(b"GAUGE ") for s in out.splitlines()) == 1)
    Path("stdout.gz").write_bytes(gzip.compress(out, mtime=0))
    Path("stderr.txt").write_bytes(done.stderr)
    result = dict(case=case, returncode=done.returncode, complete=done.returncode == 0 and observed,
                  seconds=elapsed, stdout_sha256=digest(out), stderr_sha256=digest(done.stderr))
    # A scientific refusal is a retained case outcome; the host gates dependent releases on complete.
    Path("result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
