"""Short diagnostic of face divergence with unequal Fourier wave numbers.

The original O02 data and pass criteria are unchanged. This control uses the
same Rust executable with a potential that breaks x/y exchange symmetry.
"""
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import numpy as np
from m2b_o02 import write_input,face_divergence,norms
from m2b_periodic_geometry import geometry

def main():
    pin=json.loads(Path("selection.json").read_bytes());n=pin["n"]
    for name,digest in pin["inputs"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:raise ValueError("Changed diagnostic input")
    g=geometry(n,False);x,y,_=g["cell"].T;v=g["vol"]
    sx,cx=np.sin(math.tau*x),np.cos(math.tau*x);sy,cy=np.sin(2*math.tau*y),np.cos(2*math.tau*y)
    a=np.zeros((len(v),3));a[:,2]=sx*sy
    exact=np.column_stack((2*math.tau*sx*cy,-math.tau*cx*sy,np.zeros(len(v))))
    write_input(Path("metrics.bin"),g,a,[0.,0.,0.])
    binary=Path("operator");binary.chmod(0o700)
    res=subprocess.run([str(binary.resolve()),"metrics.bin","field.bin","2"],capture_output=True,timeout=210)
    Path("native.stderr").write_bytes(res.stderr);res.check_returncode()
    with Path("field.bin").open("rb") as stream:
        if struct.unpack("<8sI",stream.read(12))!=(b"M2BR2v01",n**3):raise ValueError("Native dimensions")
        linear=np.fromfile(stream,dtype="<f8",count=12*n**3).reshape(-1,12)
        quad=np.fromfile(stream,dtype="<f8",count=13*n**3).reshape(-1,13)
        if stream.read(1):raise ValueError("Trailing data")
    def measure(p):
        other=face_divergence(g,p[:,:3])
        discrepancy=float(np.max(abs(other-p[:,5])))
        if discrepancy>1024*np.finfo(float).eps*n*2*math.tau:raise ValueError("Independent divergence")
        return dict(curl_l1=float(np.average(np.linalg.norm(p[:,:3]-exact,axis=1),weights=v)),
                    face_mean=norms(p[:,5],v),independent_difference=discrepancy)
    record=dict(selection=pin,linear=measure(linear),quadratic=measure(quad),
                exact_field_face_mean=norms(face_divergence(g,exact),v),
                native_output_sha256=hashlib.sha256(Path("field.bin").read_bytes()).hexdigest())
    Path("diagnostic.json").write_text(json.dumps(record,allow_nan=False,indent=2)+"\n")

if __name__=="__main__":main()
