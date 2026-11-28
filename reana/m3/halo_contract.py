"""Run a single compiled MPI contract control and retain every rank's verdict."""
import json
import os
from pathlib import Path
import subprocess
from mpi_case import require, sha
from mpi_runtime import environment


def main():
    case = json.loads(Path("case.json").read_bytes())
    exe = Path("halo_contract").resolve()
    require(sha(exe.read_bytes()) == case["binary_sha256"], "contract executable identity")
    ranks, mode, selector = case["ranks"], case["halo"], case["selector"]
    require(int(os.environ["RAYON_NUM_THREADS"]) == ranks, "declared MPI resources")
    exe.chmod(0o755)
    env = environment("mpi", dict(os.environ, RAYON_NUM_THREADS="1", OMP_NUM_THREADS="1",
                                  OPENBLAS_NUM_THREADS="1"))
    run = subprocess.run(["mpiexec", "-launcher", "fork", "-n", str(ranks), str(exe), mode, selector],
                         env=env, capture_output=True, timeout=case["timeout"])
    log = run.stdout + run.stderr
    Path("process.log").write_bytes(log)
    require(run.returncode == 0, log[-1400:].decode(errors="replace"))
    expected = [f"verified {selector} {mode} rank={r}" for r in range(ranks)]
    require(sorted(run.stdout.decode().splitlines()) == sorted(expected), "rank verdicts")
    Path("result.json").write_text(json.dumps(dict(case=case, ranks=ranks, process_sha256=sha(log))) + "\n")


if __name__ == "__main__":
    main()
