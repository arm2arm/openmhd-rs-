#!/usr/bin/env python3
"""Prepare/acquire/check native one-leaf REANA cases; never submit or recover.

Only source-written: independent review and real REANA preflight are mandatory
before use. See docs/galaxy/NATIVE_CASE_IMPLEMENTATION.md for exact interfaces.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/galaxy_evidence'))
from pipeline import main


if __name__ == '__main__':
    main()
