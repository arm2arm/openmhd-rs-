"""Freeze inputs, run one registered control, or measure one immutable G-GRAD case."""
import argparse
import base64
from datetime import datetime, timezone
import gzip
import io
import os
from pathlib import Path
import sys
import unittest
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"scripts"), str(ROOT/"tools/m1_evidence")]

import galaxy_gravity_bridge as bridge
import galaxy_gravity_force_case as original
import galaxy_gravity_gradient as gradient
import galaxy_gravity_reference as reference
import galaxy_test_case as launcher
import reana_metadata_job as supervisor
from test_galaxy_gravity_gradient import GradientTests

BINARY_SHA = "b7185b92b1c5052f5fc315e2fa8720eae54cb26742ed4b028127449d938f0196"
BINARY_REVISION = "58fe532f642e17f4961ce1ce7497882a88cbf069"
RESOURCES = dict(threads=1, memory="1Gi", timeout_seconds=180)
HELPER_FILES = ("scripts/galaxy_geometry3_reference.py", "scripts/galaxy_gravity_bridge.py",
                "scripts/galaxy_gravity_compare.py", "scripts/galaxy_gravity_reference.py",
                "scripts/galaxy_gravity_gradient.py", "scripts/test_galaxy_gravity_gradient.py",
                "reana/galaxy_gravity_gradient_case.py", "reana/galaxy_gravity_force_case.py",
                "reana/galaxy_test_case.py", "tools/m1_evidence/reana_metadata_job.py")

def read(name):
    return original.regular_bytes(ROOT, name)

def utc():
    return datetime.now(timezone.utc).isoformat()

def selectors():
    return unittest.defaultTestLoader.getTestCaseNames(GradientTests)

def source():
    manifest = original.parse(read("source.json"))
    original.require(set(manifest["files"]) == set(HELPER_FILES), "Exact source inventory")
    for name in HELPER_FILES:
        raw = read(name)
        original.require(original.sha(raw) == manifest["files"][name], "Source changed at " + name)
        compile(raw, name, "exec")
    original.require(manifest["binary_revision"] == BINARY_REVISION and manifest["binary_sha256"] == BINARY_SHA
                     and original.sha(read("gravity.part0000")) == BINARY_SHA, "Original released Rust executable")
    return manifest

def registered():
    return {name: gradient.fixture(name).decode("ascii") for name in gradient.CASE_NAMES}

def parent_record(source_sha):
    raw = read("parent.json")
    parent = original.parse(raw)
    original.require(str(UUID(parent["uuid"])) == parent["uuid"] and parent["mode"] == "preflight"
                     and parent["status"] == "passed" and parent["tests_run"] == 0
                     and parent["source_sha256"] == source_sha and parent["selectors"] == selectors()
                     and parent["fixtures"] == registered(), "Certified parent with these exact inputs")
    return parent

def science(name, parent, source_sha, evidence, record):
    gate = original.parse(read("controls.json"))
    original.require(gate["parent_uuid"] == parent["uuid"] and gate["source_sha256"] == source_sha
                     and set(gate["methods"]) == set(parent["selectors"]), "Complete control prerequisite")
    ids = [item["uuid"] for item in gate["methods"].values()]
    original.require(len(set(ids)) == len(ids) and all(str(UUID(v))==v for v in ids)
                     and all(item["passed"] is True and item["tests_run"] == 1
                             for item in gate["methods"].values()), "Distinct passing control workflows")
    literal = read("input.txt")
    original.require(literal == parent["fixtures"][name].encode("ascii"), "Original frozen input words")
    private = ROOT/"outputs/work"
    private.mkdir()
    executable = private/"gravity-force-case"
    executable.write_bytes(read("gravity.part0000"))
    executable.chmod(0o700)
    input_path = private/"input.txt"
    input_path.write_bytes(literal)
    journal = private/"native"
    journal.mkdir()
    links = dict(binary_sha256=BINARY_SHA, input_sha256=original.sha(literal), source_sha256=source_sha,
                 parent_uuid=parent["uuid"], controls_sha256=original.sha(read("controls.json")))
    record.update(links=links)
    env = dict(os.environ, RUST_TEST_THREADS="1", RAYON_NUM_THREADS="1", OMP_NUM_THREADS="1",
               OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    try:
        cmd = launcher.launch_native(supervisor, [str(executable),str(input_path)], private, env, journal,
                                     RESOURCES["timeout_seconds"], links)
    finally:
        for leaf in ("command.json","stdout.txt","stderr.txt"):
            if (journal/leaf).exists():
                evidence["native/"+leaf] = base64.b64encode((journal/leaf).read_bytes()).decode("ascii")
    stdout, stderr = [(journal/n).read_bytes() for n in ("stdout.txt","stderr.txt")]
    proc = original.process_evidence(cmd, literal, stdout, stderr, "G1-GRAD-"+name)
    snapshot = bridge.decode_snapshot(literal, stdout, stderr, proc)
    projection = bridge.project_reference(snapshot)
    physical = reference.parse_input(projection["reference_input_bytes"])
    algebra = reference.evaluate(physical)
    report = gradient.compare(name, physical, projection["join"]["evaluation"], algebra)
    evidence.update(input_ascii=literal.decode("ascii"), projection=projection["join"],
                    algebra=algebra, gradient=report)
    record.update(particles=report["particles"], coordinates=len(report["coordinates"]),
                  passing_coordinates=sum(r["passed"] for r in report["coordinates"]))
    original.require(report["passed"], "One or more registered coordinate gates failed")

def execute(mode, name):
    out = ROOT/"outputs"
    out.mkdir()
    record = dict(schema="openmhd.gravity-gradient-run.v1", status="failed", mode=mode, name=name,
                  uuid=str(UUID(ROOT.name)), started_utc=utc(), resources=RESOURCES, full_g1_accepted=False)
    evidence = {}
    try:
        manifest = source()
        source_sha = original.sha(read("source.json"))
        record.update(source_sha256=source_sha, revision=manifest["revision"], python=sys.version,
                      runtime=list(os.uname()), build_revision=BINARY_REVISION, binary_sha256=BINARY_SHA)
        if mode == "preflight":
            words = registered()
            for n, data in words.items():
                original.require(bridge.parse_input(data.encode("ascii"))["case"] == "G1-GRAD-"+n, "Fixture grammar")
            record.update(selectors=selectors(), fixtures=words, tests_run=0)
        else:
            parent = parent_record(source_sha)
            record.update(parent_uuid=parent["uuid"], parent_sha256=original.sha(read("parent.json")))
            if mode == "control":
                original.require(name in parent["selectors"], "Registered direct selector")
                stream = io.StringIO()
                result = unittest.TextTestRunner(stream=stream, verbosity=2).run(GradientTests(name))
                evidence["unittest"] = stream.getvalue()
                record.update(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                              skips=len(result.skipped))
                original.require(result.testsRun==1 and result.wasSuccessful() and not result.skipped
                                 and not result.expectedFailures and not result.unexpectedSuccesses,
                                 "One unskipped control must pass")
            else:
                science(name, parent, source_sha, evidence, record)
        original.require(source() == manifest, "Source and binary stable through completion")
        record["status"] = "passed"
    except Exception as error:
        record.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        packed = gzip.compress(original.encode(evidence), mtime=0)
        (out/"evidence.json.gz").write_bytes(packed)
        record.update(finished_utc=utc(), evidence=original.descriptor(packed))
        (out/"result.json").write_bytes(original.encode(record))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preflight", "control", "case"))
    parser.add_argument("name", nargs="?", default="")
    args = parser.parse_args()
    execute(args.mode, args.name)
