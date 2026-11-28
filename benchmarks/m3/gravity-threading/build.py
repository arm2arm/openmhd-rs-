"""Build the benchmark only, with the pinned M3 Linux image, Rust toolchain and MPICH."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib

from remote import RUST, RUST_MANIFEST_SHA256, download, extract
from mpi_runtime import environment as mpi_environment


def checksum(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    root = Path.cwd()
    release = json.loads(Path("build-inputs.json").read_bytes())
    for name, pin in release["files"].items():
        if checksum(Path(name)) != pin:
            raise ValueError("changed build input "+name)
    runtime = root/"runtime"
    downloads = runtime/"downloads"
    downloads.mkdir(parents=True)
    manifest = downloads/"rust.toml"
    download(f"https://static.rust-lang.org/dist/channel-rust-{RUST}.toml",manifest,RUST_MANIFEST_SHA256)
    packages = tomllib.loads(manifest.read_text())["pkg"]
    target = "x86_64-unknown-linux-gnu"
    for name in ("rustc","cargo","rust-std","rustfmt-preview","clippy-preview"):
        p = packages[name]["target"][target]
        archive = downloads/Path(p["xz_url"]).name
        download(p["xz_url"],archive,p["xz_hash"])
        extract(archive,downloads)
        unpacked = downloads/archive.name.removesuffix(".tar.xz")
        subprocess.run(["sh",str(unpacked/"install.sh"),"--prefix="+str(runtime/"rust"),"--disable-ldconfig"],
                       check=True,stdout=subprocess.DEVNULL)
        shutil.rmtree(unpacked)
    vendor = runtime/"vendor"
    vendor.mkdir()
    extract(Path("vendor.tar.gz"),vendor,regular_only=True)
    cargo = runtime/"cargo"
    cargo.mkdir()
    (cargo/"config.toml").write_text('[source.crates-io]\nreplace-with="vendored"\n[source.vendored]\ndirectory='+json.dumps(str(vendor))+"\n")
    env = dict(os.environ,PATH=str(runtime/"rust/bin")+os.pathsep+os.environ["PATH"],
               CARGO_HOME=str(cargo),CARGO_BUILD_JOBS="2",CARGO_NET_OFFLINE="true")
    env = mpi_environment(runtime/"mpi",env)
    commands = [["rustc","-Vv"],["cargo","--version"],["cc","--version"],["mpicc","-show"],["mpiexec","--version"],
        ["cargo","fmt","--all","--","--check"],
        ["cargo","clippy","--release","--locked","--offline","--all-targets","--","-D","warnings"],
        ["cargo","build","--release","--offline","--locked"],
        ["mpicc","-std=c11","-O3","-fopenmp","-fno-fast-math","-ffp-contract=off","-Wall","-Wextra","-Werror",
         "gravity_kernel.c","target/release/libgravity_bench_team.a","-ldl","-lpthread","-lm","-o","gravity-kernel"],
        ["strip","gravity-kernel"],["ldd","gravity-kernel"]]
    records = []
    with Path("build.log").open("wb") as log:
        for command in commands:
            process = subprocess.run(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            log.write(("$ "+" ".join(command)+"\n").encode()+process.stdout)
            log.flush()
            records.append(dict(argv=command,returncode=process.returncode,
                                stdout_sha256=hashlib.sha256(process.stdout).hexdigest()))
            if process.returncode:
                raise SystemExit(process.returncode)
    libraries = process.stdout.decode()
    if "libmpi.so" not in libraries or "libgomp.so" not in libraries or "not found" in libraries:
        raise ValueError("MPI/OpenMP dynamic linkage")
    result = dict(schema="openmhd.m3.threading-benchmark-build.v1",sources=release,commands=records,
                  rust_manifest=RUST_MANIFEST_SHA256,linked=libraries,executable=checksum(Path("gravity-kernel")),
                  log_sha256=checksum(Path("build.log")))
    Path("build.json").write_text(json.dumps(result,indent=2)+"\n")


if __name__ == "__main__":
    main()
