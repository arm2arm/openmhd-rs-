"""Parse Rust libtest discovery output without counting summaries as methods."""
import re
import subprocess


def selectors(executable, ignored=False, env=None):
    argv = [str(executable), "--list", "--format=terse"]
    if ignored:
        argv.append("--ignored")
    names = []
    for line in subprocess.check_output(argv, text=True, env=env).splitlines():
        if line.endswith(": test"):
            names.append(line[:-6])
        elif line and not re.fullmatch(rf"{len(names)} tests?, 0 benchmarks?", line):
            raise ValueError("unexpected libtest discovery line " + repr(line))
    if len(names) != len(set(names)):
        raise ValueError("duplicate libtest selector")
    return names
