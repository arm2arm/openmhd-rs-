use std::{
    fs,
    path::{Path, PathBuf},
    process::{Command, Output},
};
fn run(args: &[&str], output: &Path) -> Output {
    Command::new(env!("CARGO_BIN_EXE_vector-potential"))
        .args(args)
        .arg("--output")
        .arg(output)
        .output()
        .unwrap()
}
fn success(result: Output) {
    assert!(
        result.status.success(),
        "{}\n{}",
        String::from_utf8_lossy(&result.stdout),
        String::from_utf8_lossy(&result.stderr)
    );
}
fn dir(name: &str) -> PathBuf {
    let path = std::env::temp_dir().join(format!("openmhd-restart-{}-{name}", std::process::id()));
    fs::create_dir_all(&path).unwrap();
    path
}
fn compare(a: &Path, b: &Path) {
    for name in [
        "initial.csv",
        "checkpoint_0.01000000.csv",
        "checkpoint_0.02000000.csv",
        "final.csv",
        "summary.json",
        "history.json",
        "polygons.csv",
    ] {
        assert_eq!(
            fs::read(a.join(name)).unwrap(),
            fs::read(b.join(name)).unwrap(),
            "output {name}"
        );
    }
}
#[test]
fn cli_resume_is_self_contained_and_preserves_schedule() {
    let root = dir("continuation");
    let baseline = root.join("whole");
    let split = root.join("split");
    let resumed = root.join("resumed");
    let args = [
        "--case",
        "alfven",
        "--profile",
        "bulk-frame-hll-projected-v1",
        "--n",
        "6",
        "--jitter",
        "0.15",
        "--time",
        "0.03",
        "--dt",
        "0.002",
        "--checkpoint",
        "0.01",
        "--checkpoint",
        "0.02",
        "--motion",
        "rigid",
        "--mesh-x",
        "4",
        "--mesh-y",
        "-3",
        "--boost-x",
        "4",
        "--boost-y",
        "-3",
    ];
    success(run(&args, &baseline));
    for stop in [3, 5, 8, 10] {
        // Between targets, exactly at first and second target, after an output.
        let stop = stop.to_string();
        let mut partial = args.to_vec();
        partial.extend(["--checkpoint-steps", "2", "--stop-after-steps", &stop]);
        success(run(&partial, &split));
        assert!(!split.join("final.csv").exists());
        let checkpoint = root.join("saved.chk");
        fs::copy(split.join("restart.chk"), &checkpoint).unwrap();
        fs::remove_dir_all(&split).unwrap(); // Resume cannot depend on old output files or initial mesh cache.
        success(run(
            &[
                "--resume",
                checkpoint.to_str().unwrap(),
                "--checkpoint-steps",
                "3",
            ],
            &resumed,
        ));
        compare(&baseline, &resumed);
        // A completed checkpoint re-emits complete output without duplicating history.
        let final_copy = root.join("completed");
        success(run(
            &["--resume", resumed.join("restart.chk").to_str().unwrap()],
            &final_copy,
        ));
        compare(&baseline, &final_copy);
        if stop == "3" {
            let relative = root.join("relative");
            fs::create_dir_all(&relative).unwrap();
            fs::copy(resumed.join("restart.chk"), relative.join("saved.chk")).unwrap();
            success(
                Command::new(env!("CARGO_BIN_EXE_vector-potential"))
                    .current_dir(&relative)
                    .args(["--resume", "saved.chk"])
                    .output()
                    .unwrap(),
            );
            compare(&baseline, &relative);
        }
        fs::remove_dir_all(final_copy).unwrap();
        fs::remove_dir_all(&resumed).unwrap();
        let rejected = run(
            &["--resume", checkpoint.to_str().unwrap(), "--time", "0.04"],
            &resumed,
        );
        assert!(!rejected.status.success());
        assert!(!resumed.exists());
        let mut corrupt = fs::read(&checkpoint).unwrap();
        let last = corrupt.len() - 1;
        corrupt[last] ^= 1;
        fs::write(&checkpoint, corrupt).unwrap();
        assert!(
            !run(&["--resume", checkpoint.to_str().unwrap()], &resumed)
                .status
                .success()
        );
        assert!(!resumed.exists());
    }
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn colliding_analysis_names_fail_before_output_creation() {
    let root = dir("collision");
    let output = root.join("out");
    let result = run(
        &[
            "--case",
            "uniform",
            "--n",
            "4",
            "--time",
            ".003",
            "--checkpoint",
            ".001",
            "--checkpoint",
            ".001000001",
            "--checkpoint-steps",
            "1",
        ],
        &output,
    );
    assert!(!result.status.success());
    assert!(String::from_utf8_lossy(&result.stderr).contains("collide"));
    assert!(!output.exists());
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn abrupt_process_termination_resumes_last_atomic_checkpoint() {
    use std::{
        io::{BufRead, BufReader},
        process::Stdio,
    };
    let root = dir("killed");
    let whole = root.join("whole");
    let partial = root.join("partial");
    let resumed = root.join("resumed");
    let args = [
        "--case",
        "smooth",
        "--n",
        "6",
        "--time",
        "0.03",
        "--dt",
        "0.0002",
        "--checkpoint",
        "0.01",
        "--checkpoint",
        "0.02",
    ];
    success(run(&args, &whole));
    let mut child = Command::new(env!("CARGO_BIN_EXE_vector-potential"))
        .args(args)
        .args(["--checkpoint-steps", "2"])
        .arg("--output")
        .arg(&partial)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let mut observed = false;
    for line in BufReader::new(child.stdout.take().unwrap()).lines() {
        if line.unwrap().contains("restart saved: step=4,") {
            observed = true;
            break;
        }
    }
    assert!(observed);
    child.kill().unwrap();
    assert!(!child.wait().unwrap().success());
    // Also remove stale completion/failure markers when reusing an output directory.
    fs::create_dir_all(&resumed).unwrap();
    for name in ["final.csv", "summary.json", "polygons.csv", "failure.txt"] {
        fs::write(resumed.join(name), "stale").unwrap();
    }
    success(run(
        &["--resume", partial.join("restart.chk").to_str().unwrap()],
        &resumed,
    ));
    compare(&whole, &resumed);
    assert!(!resumed.join("failure.txt").exists());
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn restart_must_not_overwrite_analysis_file() {
    let root = dir("destination");
    let output = root.join("out");
    let result = run(
        &[
            "--n",
            "4",
            "--restart-out",
            output.join("initial.csv").to_str().unwrap(),
        ],
        &output,
    );
    assert!(!result.status.success());
    assert!(String::from_utf8_lossy(&result.stderr).contains("conflicts"));
    assert!(!output.join("initial.csv").exists());
    fs::remove_dir_all(root).unwrap();
}
