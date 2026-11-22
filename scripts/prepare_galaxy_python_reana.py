#!/usr/bin/env python3
"""Prepare/acquire individual galaxy Python checks; never submit or restart.

Run methods only on REANA after the actual immutable import preflight. This
route includes exact-reference arithmetic; it grants no component acceptance.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/galaxy_python_evidence'))
from prepare_metadata_reana import main


if __name__ == '__main__':
    raise SystemExit(main())
