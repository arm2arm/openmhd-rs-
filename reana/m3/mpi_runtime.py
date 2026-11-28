"""Install immutable user-space MPI and libclang wheel contents for Linux REANA jobs."""
import hashlib
import os
import subprocess
import time
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

WHEELS = {
    "mpich": (
        "https://files.pythonhosted.org/packages/dd/8f/39928760a15e4af007f8d1db3d5241a8b3dad53b0a32ee016acb994b58c3/mpich-4.3.2-py3-none-manylinux_2_28_x86_64.whl",
        "afb503104df7e3ba828d86e78f54427ef410e9fc4a2da113de529fc851128ed4",
    ),
    "libclang": (
        "https://files.pythonhosted.org/packages/1d/fc/716c1e62e512ef1c160e7984a73a5fc7df45166f2ff3f254e71c58076f7c/libclang-18.1.1-py2.py3-none-manylinux2010_x86_64.whl",
        "c533091d8a3bbf7460a00cb6c1a71da93bffe148f172c7d03b1c31fbf8aa2a0b",
    ),
}

def environment(root, env, build=False):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in (["mpich", "libclang"] if build else ["mpich"]):
        url, expected = WHEELS[name]
        archive = root / url.split("/")[-1]
        if not archive.exists():
            for attempt in range(4):
                try:
                    with urllib.request.urlopen(url, timeout=90) as stream:
                        data = stream.read()
                    if hashlib.sha256(data).hexdigest() != expected:
                        raise ValueError("bad " + name + " wheel digest")
                    archive.write_bytes(data)
                    break
                except OSError:
                    if attempt == 3:
                        raise
                    time.sleep(2 ** attempt)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise ValueError("bad retained " + name + " wheel digest")
        with zipfile.ZipFile(archive) as wheel:
            for info in wheel.infolist():
                if info.is_dir():
                    continue
                path = PurePosixPath(info.filename)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("unsafe wheel member")
                if name == "mpich" and len(path.parts)>2 and path.parts[1]=="data":
                    target = root.joinpath(*path.parts[2:])
                elif name == "libclang" and path.name == "libclang.so":
                    target = root / "clang" / path.name
                else:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(wheel.read(info))
                target.chmod(0o755 if "bin" in path.parts else 0o644)
    result = dict(env)
    result["PATH"] = str(root/"bin") + os.pathsep + result["PATH"]
    result["LD_LIBRARY_PATH"] = str(root/"lib") + os.pathsep + result.get("LD_LIBRARY_PATH", "")
    result["MPI_CC"] = result["MPICC"] = str(root/"bin/mpicc")
    result["LIBCLANG_PATH"] = str(root/"clang")
    if build:
        gccinc = subprocess.check_output(["cc","-print-file-name=include"],text=True,env=result).strip()
        result["BINDGEN_EXTRA_CLANG_ARGS"] = "-isystem " + gccinc
    return result
