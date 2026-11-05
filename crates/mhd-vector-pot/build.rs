//! Strict restart compatibility includes numerical/driver sources and build settings.
use std::{
    env, fs,
    path::{Path, PathBuf},
    process::Command,
};
fn visit(path: &Path, out: &mut Vec<PathBuf>) {
    if path.is_dir() {
        for e in fs::read_dir(path).unwrap() {
            visit(&e.unwrap().path(), out);
        }
    } else if path.extension().is_some_and(|x| x == "rs") {
        out.push(path.to_owned());
    }
}
fn main() {
    let root = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap())
        .join("../..")
        .canonicalize()
        .unwrap();
    let mut paths = vec![
        root.join("Cargo.toml"),
        root.join("Cargo.lock"),
        root.join("crates/mhd-vector-pot/build.rs"),
    ];
    for dir in [
        "crates/mhd-core",
        "crates/mhd-io",
        "crates/moving-mesh",
        "crates/mhd-vector-pot",
        "apps/openmhd",
    ] {
        let base = root.join(dir);
        paths.push(base.join("Cargo.toml"));
        visit(&base.join("src"), &mut paths);
        println!("cargo:rerun-if-changed={}", base.join("src").display());
    }
    paths.sort();
    let mut generated = String::from("const SOURCE_PARTS: &[&[u8]] = &[\n");
    for path in paths {
        println!("cargo:rerun-if-changed={}", path.display());
        generated.push_str(&format!("include_bytes!({:?}),\n", path.to_str().unwrap()));
    }
    let rustc = Command::new(env::var("RUSTC").unwrap())
        .arg("-Vv")
        .output()
        .unwrap();
    assert!(rustc.status.success());
    let mut build = String::from_utf8(rustc.stdout).unwrap();
    for key in [
        "TARGET",
        "PROFILE",
        "OPT_LEVEL",
        "DEBUG",
        "CARGO_ENCODED_RUSTFLAGS",
        "CARGO_CFG_TARGET_FEATURE",
        "CARGO_CFG_TARGET_ENDIAN",
        "CARGO_CFG_TARGET_POINTER_WIDTH",
    ] {
        println!("cargo:rerun-if-env-changed={key}");
        build.push_str(&format!("{key}={:?}\n", env::var(key).ok()));
    }
    generated.push_str(&format!("{:?}.as_bytes(),\n];\n", build));
    fs::write(
        PathBuf::from(env::var("OUT_DIR").unwrap()).join("restart_build.rs"),
        generated,
    )
    .unwrap();
}
