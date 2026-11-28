"""Restage one published layout exactly, using the compressed executable from its original REANA workflow."""
import argparse
import gzip
import json
from pathlib import Path

from verify_node_scaling import bundle, registered
from verify_evidence import require, sha

ROOT = Path(__file__).resolve().parents[2]


def prepare(plan_path, records, key, compressed_binary, destination):
    plan = json.loads(plan_path.read_bytes())
    require(plan["cases"] == registered() and key in plan["cases"], "registered layout")
    index, blobs = bundle(records)
    selected, = [entry for entry in index.values() if entry["key"] == key]
    members = selected["members"]
    inputs = json.loads(blobs[members["inputs"]])["files"]
    payload = {
        "reana.yaml": blobs[members["spec"]],
        "case.json": blobs[members["case.json"]],
        "openmhd-mpi.gz": compressed_binary.read_bytes(),
        "mpi_runtime.py": (ROOT/"reana/m3/mpi_runtime.py").read_bytes(),
        "mpi_case.py": (ROOT/"reana/m3/mpi_case.py").read_bytes(),
    }
    for name, path in (("flip.txt","docs/galaxy/fixtures/m2c_tessellation_flip.txt"),
                       ("jitter.bits","crates/mhd-vector-pot/tests/fixtures/m2c_shared_jitter.bits")):
        if name in inputs:
            payload[name]=(ROOT/path).read_bytes()
    config=json.loads(payload["case.json"])
    require(config["study_plan_sha256"]==sha(plan_path.read_bytes())
            and sha(gzip.decompress(payload["openmhd-mpi.gz"])) == plan["binary_sha256"], "plan and executable")
    require(set(payload)==set(inputs) and all(sha(raw)==inputs[name]["sha256"] and len(raw)==inputs[name]["bytes"]
            for name,raw in payload.items()), "original input bytes")
    destination.mkdir(exist_ok=False,parents=True)
    for name, raw in payload.items():
        (destination/name).write_bytes(raw)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan",type=Path)
    parser.add_argument("records",type=Path)
    parser.add_argument("case",choices=sorted(registered()))
    parser.add_argument("compressed_binary",type=Path)
    parser.add_argument("destination",type=Path)
    args=parser.parse_args()
    prepare(args.plan,args.records,args.case,args.compressed_binary,args.destination)
