"""Run one pinned native M2c case, retaining its raw output even on a step failure."""
import gzip
import hashlib
import json
import subprocess
import time
from pathlib import Path


def digest(body):
    return hashlib.sha256(body).hexdigest()


def main():
    case = json.loads(Path("case.json").read_bytes())
    exe = Path("program")
    binary = gzip.decompress(Path("program.gz").read_bytes())
    if digest(binary) != case["binary"]:
        raise ValueError("native executable checksum mismatch")
    exe.write_bytes(binary)
    exe.chmod(0o755)
    command = [str(exe.resolve()), *case["args"]]
    start = time.monotonic()
    timed_out = False
    with Path("stdout.raw").open("xb") as out, Path("stderr.txt").open("xb") as err:
        try:
            rc = subprocess.run(command, stdout=out, stderr=err, timeout=case["seconds"]).returncode
        except subprocess.TimeoutExpired:
            rc, timed_out = None, True
    seconds = time.monotonic() - start
    counts = {}
    raw_hash = hashlib.sha256()
    with Path("stdout.raw").open("rb") as data, Path("stdout.gz").open("xb") as dest:
        with gzip.GzipFile(filename="", fileobj=dest, mode="wb", mtime=0) as stream:
            for line in data:
                raw_hash.update(line)
                stream.write(line)
                words = line.split(None, 1)
                if words:
                    tag = words[0].decode("ascii", errors="replace")
                    counts[tag] = counts.get(tag, 0) + 1
    parts = {}
    with Path("stdout.gz").open("rb") as zipped:
        while True:
            block = zipped.read(700_000)
            if not block:
                break
            name = "stdout.part%04d" % len(parts)
            Path(name).write_bytes(block)
            parts[name] = {"sha256": digest(block), "bytes": len(block)}
    report = dict(case=case, returncode=rc, timed_out=timed_out, seconds=seconds, counts=counts,
                  parts=parts, stdout_sha256=raw_hash.hexdigest(), stderr_sha256=digest(Path("stderr.txt").read_bytes()),
                  peak_rss_kib=None, native_stdout_bytes=Path("stdout.raw").stat().st_size)
    # Linux reports child peak RSS in KiB.
    import resource
    report["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    Path("result.json").write_text(json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
