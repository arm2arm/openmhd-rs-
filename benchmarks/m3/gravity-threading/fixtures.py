"""Extract the original step-zero catalogues and reference forces from two measured Rust runs."""
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

ORIGINS = {
    256: ("cases-512c762ebb.tar.gz", "69ac2778c39d2a43b6afe43167a74bbea48273b28f53303281bfd5cbea668d65",
          "0af6e06c-b876-4c1a-867d-523211b98c28"),
    2048: ("large-kdk-512c762ebb-131cbfc7.tar.gz", "08155fd3dc9bbd9a9be63815d9dd8d1268abddf76253aa7451cb5ebb963c23fe",
           "c117a172-1e51-447b-a020-ef79a038c380"),
}
RUST_EXE = "3253e35aeced9ad82439a201eef4825fc144da511c028e04cc4658c31eb250d9"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(obj):
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)+"\n").encode()


def fixture(n, archive_root):
    if n == 2:
        # d=(3,0,0), epsilon=4 and the softened distance is exactly 5.
        data = b"2\n0 2 0 0 0\n1 3 3 0 0\n"
        ref = dict(origin="analytic softened binary", n=n, epsilon=4.0, energy=-6/5,
                   acceleration=[[9/125,0.,0.],[-6/125,0.,0.]], phi=[-3/5,-2/5])
    else:
        name, original_sha, uuid = ORIGINS[n]
        archive = (archive_root/name).read_bytes()
        need(sha(archive)==original_sha, "published Rust packet")
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            rows=json.load(tar.extractfile("index.json"))
            entry, = [row for row in rows if row["uuid"]==uuid]
            def get(h):
                b=tar.extractfile(h).read()
                need(sha(b)==h,"published Rust member checksum")
                return b
            receipt=json.loads(get(entry["members"]["receipt"]))
            terminal=json.loads(get(entry["members"]["terminal"]))
            result=json.loads(get(entry["outputs"]["result.json"]))
            obs=get(entry["outputs"]["observations.gz"])
        need(receipt["uuid"]==terminal["id"]==uuid and terminal["status"]=="finished"
             and receipt["outputs"]["observations.gz"]==dict(bytes=len(obs),sha256=sha(obs))
             and result["case"]["binary_sha256"]==RUST_EXE and result["case"]["threads"]==1
             and result["case"]["selector"]==f"two-population{n}", "Rust force-reference identity")
        raw = gzip.decompress(obs)
        need(sha(raw)==result["observations_sha256"], "Rust output generation")
        data_csv, marker, ledger = raw.decode().partition("step,time,mass,kinetic,potential,energy,px,py,pz,lx,ly,lz\n")
        need(bool(marker), "Rust energy ledger")
        samples=[r for r in csv.DictReader(io.StringIO(data_csv)) if int(r["step"])==0]
        potential=[r["potential"] for r in csv.DictReader(io.StringIO(marker+ledger)) if int(r["step"])==0]
        need([int(r["id"]) for r in samples]==list(range(n)) and len(potential)==1,"step-zero particles and energy")
        data=(str(n)+"\n"+"".join(" ".join(r[k] for k in ("id","mass","x","y","z"))+"\n" for r in samples)).encode()
        ref=dict(origin="Rust gravity-trajectory step zero",uuid=uuid,n=n,epsilon=.125,
                 binary_sha256=RUST_EXE,archive_sha256=original_sha,observations_sha256=sha(raw),
                 energy=float(potential[0]),acceleration=[[float(r[k]) for k in ("ax","ay","az")] for r in samples])
    ref["catalogue_sha256"]=sha(data)
    return data,ref


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("count",type=int,choices=(2,256,2048))
    cli.add_argument("published_m3",type=Path)
    cli.add_argument("destination",type=Path)
    a=cli.parse_args()
    catalogue,ref=fixture(a.count,a.published_m3)
    a.destination.mkdir(parents=True,exist_ok=True)
    (a.destination/"catalogue.txt").write_bytes(catalogue)
    (a.destination/"reference.json").write_bytes(encoded(ref))
