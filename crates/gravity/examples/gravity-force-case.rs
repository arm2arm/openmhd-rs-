//! Unadopted one-input GP-2 exporter. No component or physical acceptance.
//! Uses production checked catalog/model/evaluation/diagnostics without a kick.
use gravity::diagnostics::{VirialResidual, VirialUndefined, measure};
use gravity::direct::{DirectConfig, evaluate};
use gravity::softening::{FixedPlummer, GravityModel, SofteningClass};
use gravity::state::{Catalog, CollisionlessKind, Particle, ParticleMetadata};
use gravity::units::UnitSystem;
use gravity::{EntityId, Identity, ParticleId, Vec3};
use sha2::{Digest, Sha256};
use std::fmt::Write as FmtWrite;
use std::fs::File;
use std::io::{Read, Write as IoWrite};
use std::path::Path;
use std::str::SplitAsciiWhitespace;

const MAX_INPUT_BYTES: u64 = 262_144;
const MAX_OUTPUT_BYTES: usize = 4 * 1024 * 1024;
const MAX_PARTICLES: usize = 32;
type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

fn reject(message: &str) -> Box<dyn std::error::Error> {
    std::io::Error::new(std::io::ErrorKind::InvalidData, message).into()
}

fn hex(raw: &[u8]) -> String {
    let mut out = String::with_capacity(raw.len() * 2);
    for byte in raw {
        write!(&mut out, "{byte:02x}").expect("writing to String cannot fail");
    }
    out
}

fn word(value: f64) -> String {
    format!("{:016x}", value.to_bits())
}

fn vector(value: Vec3) -> String {
    value.map(word).join(" ")
}

fn bounded_input(path: &Path) -> Result<Vec<u8>> {
    let original = std::fs::symlink_metadata(path)?;
    if original.file_type().is_symlink() || !original.is_file() {
        return Err(reject("input must be a regular non-symlink file"));
    }
    let mut file = File::open(path)?;
    let before = file.metadata()?;
    if !before.is_file() || before.len() > MAX_INPUT_BYTES {
        return Err(reject("input type or size limit"));
    }
    let mut raw = Vec::new();
    (&mut file)
        .take(MAX_INPUT_BYTES + 1)
        .read_to_end(&mut raw)?;
    let after = file.metadata()?;
    if raw.len() as u64 != before.len()
        || before.len() != after.len()
        || before.modified()? != after.modified()?
        || original.len() != before.len()
        || original.modified()? != before.modified()?
        || !raw.is_ascii()
        || !raw.ends_with(b"\n")
    {
        return Err(reject(
            "input changed, is oversized, or is not newline-terminated ASCII",
        ));
    }
    Ok(raw)
}

struct Tokens<'a>(SplitAsciiWhitespace<'a>);
impl<'a> Tokens<'a> {
    fn take(&mut self) -> Result<&'a str> {
        self.0.next().ok_or_else(|| reject("truncated input"))
    }

    fn expect(&mut self, expected: &str) -> Result<()> {
        if self.take()? != expected {
            return Err(reject("unexpected input field"));
        }
        Ok(())
    }

    fn unsigned(&mut self) -> Result<u64> {
        let raw = self.take()?;
        if raw.is_empty() || raw.len() > 20 || !raw.bytes().all(|c| c.is_ascii_digit()) {
            return Err(reject("invalid unsigned decimal"));
        }
        let value: u64 = raw.parse()?;
        if value.to_string() != raw {
            return Err(reject("noncanonical unsigned decimal"));
        }
        Ok(value)
    }

    fn scalar(&mut self) -> Result<f64> {
        let raw = self.take()?;
        if raw.len() != 16
            || !raw
                .bytes()
                .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
        {
            return Err(reject("expected canonical finite binary64 word"));
        }
        let value = f64::from_bits(u64::from_str_radix(raw, 16)?);
        if !value.is_finite() {
            return Err(reject("nonfinite binary64 input"));
        }
        Ok(value)
    }

    fn vector(&mut self) -> Result<Vec3> {
        Ok([self.scalar()?, self.scalar()?, self.scalar()?])
    }

    fn label(&mut self) -> Result<String> {
        let raw = self.take()?;
        if raw.is_empty()
            || raw.len() > 160
            || !raw
                .bytes()
                .all(|c| c.is_ascii_alphanumeric() || b"._-".contains(&c))
        {
            return Err(reject("invalid bounded ASCII label"));
        }
        Ok(raw.to_owned())
    }
}

fn identity(out: &mut String, label: &str, value: &Identity) -> Result<()> {
    writeln!(
        out,
        "identity {label} {} {} {}",
        value.bytes().len(),
        hex(&value.sha256()),
        hex(value.bytes())
    )?;
    Ok(())
}

fn optional_vector(out: &mut String, label: &str, value: Option<Vec3>) -> Result<()> {
    match value {
        Some(v) => writeln!(out, "diagnostic {label} some {}", vector(v))?,
        None => writeln!(out, "diagnostic {label} none")?,
    }
    Ok(())
}

fn optional_scalar(out: &mut String, label: &str, value: Option<f64>) -> Result<()> {
    match value {
        Some(v) => writeln!(out, "diagnostic {label} some {}", word(v))?,
        None => writeln!(out, "diagnostic {label} none")?,
    }
    Ok(())
}

fn run() -> Result<()> {
    let mut args = std::env::args_os().skip(1);
    let path = args
        .next()
        .ok_or_else(|| reject("one input path required"))?;
    if args.next().is_some() {
        return Err(reject("one input path required"));
    }
    let raw = bounded_input(Path::new(&path))?;
    let text = std::str::from_utf8(&raw)?;
    let mut tokens = Tokens(text.split_ascii_whitespace());
    tokens.expect("openmhd-gravity-force-input-v1")?;
    tokens.expect("case")?;
    let case = tokens.label()?;
    tokens.expect("stage")?;
    tokens.expect("static-force-snapshot")?;
    tokens.expect("clock")?;
    let time = tokens.scalar()?;
    let revision = tokens.unsigned()?;
    tokens.expect("backend")?;
    let backend_revision = tokens.unsigned()?;
    tokens.expect("units")?;
    let units = match tokens.take()? {
        "dimensionless-g1" => UnitSystem::dimensionless_g1(),
        "si" => {
            let l = tokens.scalar()?;
            let m = tokens.scalar()?;
            let v = tokens.scalar()?;
            let g = tokens.scalar()?;
            let mu0 = tokens.scalar()?;
            let provenance = tokens.label()?;
            UnitSystem::si(l, m, v, g, mu0, &provenance)?
        }
        _ => return Err(reject("unknown explicit unit system")),
    };
    tokens.expect("softening")?;
    let epsilon = tokens.scalar()?;
    let class = SofteningClass::new(u16::try_from(tokens.unsigned()?)?);
    let model = GravityModel::new(units, FixedPlummer::new(epsilon, class)?);
    let config = DirectConfig::new(backend_revision);
    tokens.expect("count")?;
    let count = usize::try_from(tokens.unsigned()?)?;
    if count > MAX_PARTICLES {
        return Err(reject("32-particle arithmetic-comparison limit"));
    }
    let mut particles = Vec::with_capacity(count);
    for _ in 0..count {
        tokens.expect("particle")?;
        let id_text = tokens.take()?;
        let entity: EntityId = id_text.parse()?;
        if entity.to_string() != id_text {
            return Err(reject("noncanonical persistent identity"));
        }
        let kind = match tokens.take()? {
            "dm" => CollisionlessKind::DarkMatter,
            "star" => CollisionlessKind::Star,
            _ => return Err(reject("collisionless particle kind required")),
        };
        let component = u16::try_from(tokens.unsigned()?)?;
        let galaxy = u32::try_from(tokens.unsigned()?)?;
        let particle_class = SofteningClass::new(u16::try_from(tokens.unsigned()?)?);
        let mass = tokens.scalar()?;
        let position = tokens.vector()?;
        let momentum = tokens.vector()?;
        particles.push(Particle::from_momentum(
            ParticleId::new(entity),
            mass,
            position,
            momentum,
            ParticleMetadata {
                kind,
                softening: particle_class,
                component,
                galaxy,
            },
        )?);
    }
    tokens.expect("end")?;
    if tokens.0.next().is_some() {
        return Err(reject("extra input tokens"));
    }
    let input_order: Vec<_> = particles.iter().map(Particle::id).collect();
    let catalog = Catalog::new(time, revision, particles)?;
    let evaluation = evaluate(&catalog, &model, &config)?;
    evaluation.validate_for(&catalog, &model, &config)?;
    let diagnostics = measure(&catalog, &model, &config, &evaluation)?;
    let mut out = String::new();
    writeln!(&mut out, "openmhd-gravity-force-candidate-v1")?;
    writeln!(&mut out, "status complete")?;
    writeln!(&mut out, "component_accepted false")?;
    writeln!(&mut out, "case {case}")?;
    writeln!(&mut out, "stage static-force-snapshot")?;
    writeln!(&mut out, "input_sha256 {}", hex(&Sha256::digest(&raw)))?;
    writeln!(
        &mut out,
        "clock {} {}",
        word(catalog.time()),
        catalog.revision()
    )?;
    writeln!(&mut out, "backend_revision {}", config.revision())?;
    writeln!(
        &mut out,
        "model isolated common-fixed-plummer excluded {} {} {}",
        word(model.g()),
        word(model.softening().epsilon()),
        model.softening().class().value()
    )?;
    writeln!(&mut out, "units_physical {}", model.units().is_physical())?;
    writeln!(
        &mut out,
        "counts {} {}",
        catalog.particles().len(),
        evaluation.pair_count()
    )?;
    for id in input_order {
        writeln!(&mut out, "input_order {}", id.entity())?;
    }
    identity(&mut out, "sources", catalog.source_identity())?;
    identity(&mut out, "state", catalog.state_identity())?;
    identity(&mut out, "model", model.identity())?;
    identity(&mut out, "units", model.units().identity())?;
    identity(&mut out, "backend", config.identity())?;
    let pins = evaluation.pins();
    writeln!(
        &mut out,
        "cache_clock {:016x} {}",
        pins.time_bits(),
        pins.state_revision()
    )?;
    identity(&mut out, "cache_sources", pins.sources())?;
    identity(&mut out, "cache_state", pins.state())?;
    identity(&mut out, "cache_model", pins.model())?;
    identity(&mut out, "cache_units", pins.units())?;
    identity(&mut out, "cache_backend", pins.backend())?;
    for particle in catalog.particles() {
        let kind = match particle.kind() {
            CollisionlessKind::DarkMatter => "dm",
            CollisionlessKind::Star => "star",
        };
        writeln!(
            &mut out,
            "particle {} {kind} {} {} {} {} {} {}",
            particle.id().entity(),
            particle.component(),
            particle.galaxy(),
            particle.softening().value(),
            word(particle.mass()),
            vector(particle.position()),
            vector(particle.momentum())
        )?;
    }
    for sample in evaluation.samples() {
        writeln!(
            &mut out,
            "sample {} {} {} {} {}",
            sample.id().entity(),
            vector(sample.force()),
            word(sample.specific_potential()),
            word(sample.force_scale()),
            word(sample.potential_scale())
        )?;
    }
    writeln!(
        &mut out,
        "evaluation_scales {} {} {} {}",
        word(evaluation.pair_energy()),
        word(evaluation.energy_scale()),
        word(evaluation.net_force_scale()),
        word(evaluation.torque_scale())
    )?;
    let canonical = evaluation.canonical_bytes();
    writeln!(
        &mut out,
        "evaluation_bytes {} {} {}",
        canonical.len(),
        hex(&Sha256::digest(&canonical)),
        hex(&canonical)
    )?;
    writeln!(&mut out, "raw_force {}", vector(diagnostics.net_force))?;
    writeln!(
        &mut out,
        "raw_torque_origin {}",
        vector(diagnostics.torque_origin)
    )?;
    writeln!(&mut out, "diagnostic mass {}", word(diagnostics.mass))?;
    writeln!(
        &mut out,
        "diagnostic momentum {}",
        vector(diagnostics.momentum)
    )?;
    writeln!(
        &mut out,
        "diagnostic angular_momentum_origin {}",
        vector(diagnostics.angular_momentum_origin)
    )?;
    writeln!(
        &mut out,
        "diagnostic kinetic_lab {}",
        word(diagnostics.kinetic_lab)
    )?;
    writeln!(
        &mut out,
        "diagnostic pair_energy {}",
        word(diagnostics.pair_energy)
    )?;
    writeln!(
        &mut out,
        "diagnostic hamiltonian_lab {}",
        word(diagnostics.hamiltonian_lab)
    )?;
    optional_vector(&mut out, "center_of_mass", diagnostics.center_of_mass)?;
    optional_vector(&mut out, "center_velocity", diagnostics.center_velocity)?;
    optional_vector(
        &mut out,
        "angular_momentum_internal",
        diagnostics.angular_momentum_internal,
    )?;
    optional_scalar(&mut out, "kinetic_internal", diagnostics.kinetic_internal)?;
    optional_scalar(&mut out, "virial_work", diagnostics.virial_work)?;
    optional_scalar(&mut out, "inertia_internal", diagnostics.inertia_internal)?;
    match diagnostics.virial_residual {
        VirialResidual::Defined(value) => writeln!(
            &mut out,
            "diagnostic virial_residual defined {}",
            word(value)
        )?,
        VirialResidual::Undefined(VirialUndefined::EmptyCatalog) => {
            writeln!(&mut out, "diagnostic virial_residual undefined empty")?
        }
        VirialResidual::Undefined(VirialUndefined::NonpositiveScale) => writeln!(
            &mut out,
            "diagnostic virial_residual undefined nonpositive-scale"
        )?,
    }
    writeln!(&mut out, "end")?;
    if out.len() > MAX_OUTPUT_BYTES {
        return Err(reject("complete output exceeds export limit"));
    }
    std::io::stdout().lock().write_all(out.as_bytes())?;
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("gravity-force-case failed: {error}");
        std::process::exit(1);
    }
}
