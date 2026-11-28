"""Execute one native correctness leaf or one fixed-layout strong-scaling measurement."""
import csv
import gzip
import hashlib
import io
import json
import os
import resource
import statistics
import subprocess
import time
from pathlib import Path

case = json.loads(Path("case.json").read_bytes())
exe = Path(case["binary"]).resolve()
threads = case["threads"]
env = dict(os.environ, OPENMHD_TEST_THREADS=str(threads))
sha = lambda data: hashlib.sha256(data).hexdigest()
if sha(exe.read_bytes()) != case["binary_sha256"] or int(env["RAYON_NUM_THREADS"]) != threads:
    raise ValueError("different executable or thread allocation")
exe.chmod(0o755)
selector = case["selector"]
kind = case["kind"]
samples = []
fingerprints = []
if kind == "geometry":
    # 64 cubic cells undergo a rigid, exactly representable displacement.
    n = 4
    rows = ["domain periodic 0 0 0 1 1 1"]
    for i in range(n ** 3):
        x, y, z = ((j + 0.5) / n for j in (i % n, i // n % n, i // n ** 2))
        rows.append(f"cell {i+1:032x} {x} {y} {z} 0 0 0 0.125 -0.0625 0.25 1")
    Path("initial.txt").write_text("\n".join(rows) + "\n")
elif kind == "gravity":
    # Two equal-mass Cartesian populations. The larger fixture doubles each axis.
    count = case.get("particles", 256)
    if count not in (256, 2048):
        raise ValueError("unregistered particle count")
    scale = 1 if count == 256 else 2
    nx, ny, nz = 8*scale, 4*scale, 4*scale
    steps = 16 if count == 256 else 4
    stride = steps//2
    rows = []
    for i in range(count):
        pop, j = divmod(i, count//2)
        x = (2*pop-1)*0.75 + (j % nx - (nx-1)/2)/(16*scale)
        y = (j//nx % ny - (ny-1)/2)/(16*scale)
        z = (j//(nx*ny) - (nz-1)/2)/(16*scale)
        rows.append(f"{i} {pop} {1/count:.17g} {x} {y} {z} 0 {(1-2*pop)/16} 0")
    Path("initial.txt").write_text("\n".join(rows) + "\n")

replicates = 1 if kind == "test" else 3
for rep in range(replicates):
    if kind == "test":
        args = ["--exact", selector, "--nocapture", "--test-threads=1"]
    elif kind == "gravity":
        args = ["--threads", str(threads), "initial.txt", "0.125", "0.0001", str(steps), str(stride), f"snapshot-{rep}"]
    elif kind == "geometry":
        args = ["--threads", str(threads), "initial.txt", "0.125"]
    else:
        raise ValueError("unknown case kind")
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.monotonic()
    child = subprocess.run([str(exe), *args], capture_output=True, env=env, timeout=600)
    wall = time.monotonic() - t0
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    Path("stderr.txt").write_bytes(child.stderr)
    if child.returncode:
        Path("failed-stdout.txt").write_bytes(child.stdout)
        raise RuntimeError(f"{selector} exited {child.returncode}: {child.stderr[-2000:]!r}")
    if kind == "test":
        text = child.stdout.decode()
        if ("running 1 test\n" not in text or "test " + selector + " ... ok" not in text
                or "test result: ok. 1 passed; 0 failed; 0 ignored;" not in text):
            raise ValueError("missing exact successful leaf")
        scientific = child.stdout
    elif kind == "gravity":
        a = (Path(f"snapshot-{rep}") / "particles.csv").read_bytes()
        b = (Path(f"snapshot-{rep}") / "conservation.csv").read_bytes()
        endpoints = list(csv.DictReader(io.StringIO(a.decode())))
        ledger = list(csv.DictReader(io.StringIO(b.decode())))
        if [(int(r["step"]), int(r["id"])) for r in endpoints] != [(step, i) for step in (0, stride, steps) for i in range(count)] or len(ledger) != 3:
            raise ValueError("missing gravity endpoint or particle")
        scientific = a + b
    else:
        cells = {}
        for r in csv.DictReader(io.StringIO(child.stdout.decode())):
            cells.setdefault(int(r["step"]), set()).add(r["owner"])
        if set(cells) != {0, 1} or any(len(ids) != 64 for ids in cells.values()):
            raise ValueError("missing geometry epoch or owner")
        scientific = child.stdout
    fingerprints.append(sha(scientific))
    if rep == 0:
        Path("observations.gz").write_bytes(gzip.compress(scientific, mtime=0))
    samples.append(dict(seconds=wall, user_seconds=after.ru_utime-before.ru_utime,
                        system_seconds=after.ru_stime-before.ru_stime, max_rss_kib=after.ru_maxrss))
if len(set(fingerprints)) != 1:
    raise ValueError("different repeated scientific output")
out = dict(case=case, args=args, samples=samples, observations_sha256=fingerprints[0],
           median_seconds=statistics.median(s["seconds"] for s in samples),
           affinity=sorted(os.sched_getaffinity(0)), cpu_max=Path("/sys/fs/cgroup/cpu.max").read_text().strip())
Path("result.json").write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
