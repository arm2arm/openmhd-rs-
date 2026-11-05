use mhd_io::{Decoder, Encoder};
use mhd_vector_pot::general::Simulation;
use std::{
    fs,
    path::{Path, PathBuf},
};

#[derive(Default)]
pub struct Options {
    pub resume: Option<PathBuf>,
    pub output: Option<PathBuf>,
    pub destination: Option<PathBuf>,
    pub every: Option<usize>,
    pub stop_after: Option<usize>,
    pub physical: Vec<String>,
}
impl Options {
    pub fn parse() -> Result<Self, String> {
        let mut out = Self::default();
        let mut args = std::env::args().skip(1);
        while let Some(arg) = args.next() {
            if matches!(
                arg.as_str(),
                "--resume"
                    | "--output"
                    | "--restart-out"
                    | "--checkpoint-steps"
                    | "--stop-after-steps"
            ) {
                let value = args
                    .next()
                    .ok_or_else(|| format!("missing value for {arg}"))?;
                match arg.as_str() {
                    "--resume" => out.resume = Some(value.into()),
                    "--output" => out.output = Some(value.into()),
                    "--restart-out" => out.destination = Some(value.into()),
                    _ => {
                        let n = value
                            .parse::<usize>()
                            .map_err(|_| format!("invalid count for {arg}"))?;
                        if n == 0 {
                            return Err(format!("{arg} must be positive"));
                        }
                        if arg == "--checkpoint-steps" {
                            out.every = Some(n);
                        } else {
                            out.stop_after = Some(n);
                        }
                    }
                }
            } else {
                // Preserve physical argument/value pairs, including values beginning with '-'.
                let flag = matches!(arg.as_str(), "--unlimited" | "--mesh-only" | "--help");
                out.physical.push(arg.clone());
                if !flag {
                    out.physical.push(
                        args.next()
                            .ok_or_else(|| format!("missing value for {arg}"))?,
                    );
                }
            }
        }
        if out.resume.is_some() && !out.physical.is_empty() {
            return Err("--resume restores the saved physical configuration and target schedule; only --output, --restart-out, --checkpoint-steps and --stop-after-steps may accompany it".into());
        }
        Ok(out)
    }
}
pub struct Context {
    pub arguments: Vec<String>,
    pub every: usize,
    pub final_time: f64,
    pub pending: Vec<f64>,
    pub initial: String,
    pub history: Vec<String>,
    /// Self-contained original initial.csv and completed analysis CSVs.
    pub outputs: Vec<(String, String)>,
}
impl Context {
    pub fn encode(&self) -> Vec<u8> {
        let mut w = Encoder::new();
        w.string("vector-potential-driver-v1");
        w.usize(self.arguments.len());
        for s in &self.arguments {
            w.string(s);
        }
        w.usize(self.every);
        w.float(self.final_time);
        w.usize(self.pending.len());
        for &t in &self.pending {
            w.float(t);
        }
        w.string(&self.initial);
        w.usize(self.history.len());
        for s in &self.history {
            w.string(s);
        }
        w.usize(self.outputs.len());
        for (name, data) in &self.outputs {
            w.string(name);
            w.string(data);
        }
        w.finish()
    }
    pub fn decode(bytes: &[u8], sim: &Simulation) -> Result<Self, String> {
        let mut r = Decoder::new(bytes);
        if r.string()? != "vector-potential-driver-v1" {
            return Err("restart lacks compatible CLI context".into());
        }
        let n = r.count(8)?;
        let arguments = (0..n).map(|_| r.string()).collect::<Result<_, _>>()?;
        let every = r.usize()?;
        let final_time = r.float()?;
        let n = r.count(8)?;
        let pending = (0..n).map(|_| r.float()).collect::<Result<Vec<_>, _>>()?;
        let initial = r.string()?;
        let n = r.count(8)?;
        let history = (0..n).map(|_| r.string()).collect::<Result<Vec<_>, _>>()?;
        let n = r.count(16)?;
        let outputs = (0..n)
            .map(|_| Ok((r.string()?, r.string()?)))
            .collect::<Result<Vec<_>, String>>()?;
        r.finish()?;
        if !final_time.is_finite()
            || final_time < sim.time()
            || pending
                .iter()
                .any(|t| !t.is_finite() || *t < sim.time() || *t > final_time)
            || pending.windows(2).any(|w| w[0] >= w[1])
            || pending.last().is_some_and(|t| *t != final_time)
            || (pending.is_empty() && sim.time() != final_time)
            || history.is_empty()
            || outputs.first().map(|o| o.0.as_str()) != Some("initial.csv")
        {
            return Err("invalid restart driver schedule/history".into());
        }
        let mut names = std::collections::BTreeSet::new();
        for (name, _) in &outputs {
            if !names.insert(name)
                || !(name == "initial.csv"
                    || (name.starts_with("checkpoint_")
                        && name.ends_with(".csv")
                        && name
                            .chars()
                            .all(|c| c.is_ascii_alphanumeric() || "_.-".contains(c))))
            {
                return Err("invalid restart output name".into());
            }
        }
        Ok(Self {
            arguments,
            every,
            final_time,
            pending,
            initial,
            history,
            outputs,
        })
    }
    pub fn restore_outputs(&self, path: &Path) -> Result<(), String> {
        fs::create_dir_all(path).map_err(|e| e.to_string())?;
        for (name, data) in &self.outputs {
            fs::write(path.join(name), data).map_err(|e| e.to_string())?;
        }
        self.write_history(path)
    }
    pub fn write_history(&self, path: &Path) -> Result<(), String> {
        mhd_io::write_atomic(
            &path.join("history.json"),
            format!("[{}]\n", self.history.join(",")).as_bytes(),
        )
    }
}
