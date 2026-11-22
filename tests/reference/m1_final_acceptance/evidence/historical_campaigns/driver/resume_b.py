#!/usr/bin/env python3
"""Resume configuration B ('step') of the 2026-11-17 follow-up campaigns alone (2026-11-19).

B stopped at its precondition on 2026-11-17 at 20:44 UTC: the result download of
medium case 0034 had failed, although the case had finished on REANA with all
outputs. That failed record is kept as
results/followup_step_precondition_20261117.download-failure.json. A check on
2026-11-19 downloaded the result: 48/48 medium cases complete, no observation
or execution error.

This runs the unchanged driver.py with CONFIGS reduced to B. Every step with
evidence is skipped and nothing is resubmitted. The precondition is evaluated
again from the complete observations; only if it passes are the wave and
physics plans prepared, uploaded and monitored, then the final verdict
written. The owner asked on 2026-11-19 to resume B.

Stop it with: kill $(cat results/followup_campaign_tools_20261117/driver.pid)
"""
import importlib.util
import os
import sys
from pathlib import Path

T = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('driver', T/'driver.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
driver.CONFIGS = {'step': driver.CONFIGS['step']}

if __name__ == '__main__':
    if os.fork():
        sys.exit(0)
    os.setsid()
    if os.fork():
        sys.exit(0)
    devnull = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(devnull, fd)
    driver.log('--- resume of B alone (resume_b.py), owner request of 2026-11-19')
    driver.main()
