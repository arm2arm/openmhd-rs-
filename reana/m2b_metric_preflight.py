"""Check the Fourier benchmark's jittered metrics against the accepted G02 data."""
import hashlib
import json
from pathlib import Path
import numpy as np
import scipy
from m2b_periodic_geometry import geometry,compare_oracle


def main():
    provenance=json.loads(Path("oracle.json").read_bytes())
    archive=Path("m2a-jitter8.npz")
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=provenance["extracted_npz"]:
        raise ValueError("G02 metric receipt")
    mesh=geometry(8,True)
    with np.load(archive) as exact:
        errors=compare_oracle(mesh,exact)
    report=dict(cells=len(mesh["cell"]),faces=len(mesh["area"]),max_errors=errors,reference=provenance,
                geometry_source_sha256=hashlib.sha256(Path("m2b_periodic_geometry.py").read_bytes()).hexdigest(),
                numpy=np.__version__,scipy=scipy.__version__)
    Path("comparison.json").write_text(json.dumps(report,allow_nan=False,indent=2)+"\n")

if __name__=="__main__":main()
