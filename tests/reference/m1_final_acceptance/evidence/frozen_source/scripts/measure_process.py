#!/usr/bin/env python3
"""Measure one Linux command tree without depending on an external time binary.

ru_maxrss is the largest process RSS reported by wait4, including reaped
descendants. It is not the sum of simultaneous workers' memory usage.
"""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if sys.platform != 'linux' or not command:
        parser.error('Requires Linux and a command after --')
    start = time.monotonic()
    result = subprocess.run(command)
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    args.output.write_text(json.dumps(dict(
        command=command, returncode=result.returncode,
        wall_seconds=time.monotonic()-start, cpu_seconds=usage.ru_utime+usage.ru_stime,
        peak_process_rss_bytes=int(usage.ru_maxrss)*1024,
        measurement='Linux wait4 ru_maxrss; largest process, not concurrent sum'), indent=2)+'\n')
    return result.returncode if result.returncode >= 0 else 128-result.returncode


if __name__ == '__main__': raise SystemExit(main())
