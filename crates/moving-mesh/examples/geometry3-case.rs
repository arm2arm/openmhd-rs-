//! Source-only proposal for a standalone, single-input G01 candidate export.
//! No candidate/reference calculation has been run by writing this file.
//! Intended future location: crates/moving-mesh/examples/geometry3-case.rs.
use galaxy_types::{CellId, EntityId};
use moving_mesh::three_d::{
    Boundary3, Domain3, FaceKey3, Generator3, HalfSpaceOracle3, Image3, Tensor3, Vec3,
};
use std::fmt::Write as FmtWrite;
use std::fs::File;
use std::io::{Read, Write as IoWrite};
use std::path::Path;
use std::process::ExitCode;

const MAX_INPUT_BYTES: u64 = 128 * 1024;
const MAX_OUTPUT_BYTES: usize = 16 * 1024 * 1024;
const MAX_GENERATORS: usize = 512;
type Result<T> = std::result::Result<T, String>;

fn token<'a>(tokens: &mut impl Iterator<Item = &'a str>) -> Result<&'a str> {
    tokens
        .next()
        .ok_or_else(|| "Truncated candidate input".to_owned())
}

fn expect<'a>(tokens: &mut impl Iterator<Item = &'a str>, expected: &str) -> Result<()> {
    if token(tokens)? != expected {
        return Err(format!("Expected literal field {expected}"));
    }
    Ok(())
}

fn scalar<'a>(tokens: &mut impl Iterator<Item = &'a str>) -> Result<f64> {
    let text = token(tokens)?;
    if text.len() != 16
        || !text
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("Expected exactly sixteen lowercase binary64 hex digits".to_owned());
    }
    let bits = u64::from_str_radix(text, 16).map_err(|_| "Invalid binary64 word".to_owned())?;
    let value = f64::from_bits(bits);
    if !value.is_finite() {
        return Err("Nonfinite candidate input".to_owned());
    }
    Ok(value)
}

fn vector<'a>(tokens: &mut impl Iterator<Item = &'a str>) -> Result<Vec3> {
    Ok([scalar(tokens)?, scalar(tokens)?, scalar(tokens)?])
}

fn integer<'a>(tokens: &mut impl Iterator<Item = &'a str>) -> Result<i64> {
    let text = token(tokens)?;
    let value: i64 = text
        .parse()
        .map_err(|_| "Invalid image integer".to_owned())?;
    if value.to_string() != text {
        return Err("Noncanonical image integer".to_owned());
    }
    Ok(value)
}

fn image<'a>(tokens: &mut impl Iterator<Item = &'a str>) -> Result<Image3> {
    Ok(Image3([
        integer(tokens)?,
        integer(tokens)?,
        integer(tokens)?,
    ]))
}

fn parse(raw: &str) -> Result<(String, Domain3, Vec<Generator3>)> {
    if !raw.is_ascii() {
        return Err("Candidate input must be ASCII".to_owned());
    }
    let mut tokens = raw.split_ascii_whitespace();
    expect(&mut tokens, "openmhd-geometry3-input-v1")?;
    expect(&mut tokens, "case")?;
    let case = token(&mut tokens)?;
    if case.is_empty()
        || case.len() > 160
        || !case
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_')
    {
        return Err("Invalid case label".to_owned());
    }
    expect(&mut tokens, "boundary")?;
    let boundary = match token(&mut tokens)? {
        "periodic" => Boundary3::Periodic,
        "bounded" => Boundary3::Bounded,
        _ => return Err("Unknown domain boundary".to_owned()),
    };
    expect(&mut tokens, "anchor")?;
    let anchor = vector(&mut tokens)?;
    expect(&mut tokens, "width")?;
    let width = vector(&mut tokens)?;
    expect(&mut tokens, "count")?;
    let count_text = token(&mut tokens)?;
    let count: usize = count_text
        .parse()
        .map_err(|_| "Invalid generator count".to_owned())?;
    if count.to_string() != count_text || !(1..=MAX_GENERATORS).contains(&count) {
        return Err("Noncanonical or out-of-bounds generator count".to_owned());
    }
    let mut generators = Vec::with_capacity(count);
    for _ in 0..count {
        expect(&mut tokens, "generator")?;
        let text = token(&mut tokens)?;
        let entity: EntityId = text
            .parse()
            .map_err(|_| "Invalid persistent ID".to_owned())?;
        if entity.to_string() != text {
            return Err("Persistent ID must be thirty-two lowercase hex digits".to_owned());
        }
        generators.push(Generator3 {
            id: CellId::new(entity),
            position: vector(&mut tokens)?,
            winding: image(&mut tokens)?,
        });
    }
    expect(&mut tokens, "end")?;
    if tokens.next().is_some() {
        return Err("Extra candidate input fields".to_owned());
    }
    Ok((
        case.to_owned(),
        Domain3 {
            anchor,
            width,
            boundary,
        },
        generators,
    ))
}

fn put_scalar(out: &mut String, value: f64) {
    write!(out, " {:016x}", value.to_bits()).expect("Writing to String cannot fail");
}

fn put_vector(out: &mut String, value: Vec3) {
    for entry in value {
        put_scalar(out, entry);
    }
}

fn put_tensor(out: &mut String, value: Tensor3) {
    for row in value {
        put_vector(out, row);
    }
}

fn put_image(out: &mut String, value: Image3) {
    write!(out, " {} {} {}", value.0[0], value.0[1], value.0[2])
        .expect("Writing to String cannot fail");
}

fn bounded_output(out: &str) -> Result<()> {
    if out.len() > MAX_OUTPUT_BYTES {
        return Err("Candidate transcript exceeds byte limit".to_owned());
    }
    Ok(())
}

fn render(raw: &str) -> Result<String> {
    let (case, domain, input) = parse(raw)?;
    let geometry = HalfSpaceOracle3::build(domain, &input).map_err(|error| error.to_string())?;
    let mut out =
        String::from("openmhd-geometry3-candidate-v1\ncomponent_accepted false\nstatus complete\n");
    writeln!(out, "case {case}\nepoch {}", geometry.epoch().value())
        .expect("Writing to String cannot fail");
    let boundary = if domain.boundary == Boundary3::Periodic {
        "periodic"
    } else {
        "bounded"
    };
    write!(out, "domain {boundary}").expect("Writing to String cannot fail");
    put_vector(&mut out, domain.anchor);
    put_vector(&mut out, domain.width);
    out.push('\n');
    writeln!(
        out,
        "counts {} {}",
        geometry.cells().len(),
        geometry.faces().len()
    )
    .expect("Writing to String cannot fail");
    // Retain every actual parsed word in original input order as a comparison fence.
    for generator in &input {
        write!(out, "input_generator {}", generator.id.entity())
            .expect("Writing to String cannot fail");
        put_vector(&mut out, generator.position);
        put_image(&mut out, generator.winding);
        out.push('\n');
    }
    for cell in geometry.cells() {
        write!(out, "cell {}", cell.generator.id.entity()).expect("Writing to String cannot fail");
        put_scalar(&mut out, cell.volume);
        put_vector(&mut out, cell.centroid_offset);
        put_tensor(&mut out, cell.central_second_moment);
        put_scalar(&mut out, cell.surface_area);
        put_scalar(&mut out, cell.bounding_radius);
        put_scalar(&mut out, cell.minimum_generator_face_distance);
        writeln!(out, " {}", cell.incidences.len()).expect("Writing to String cannot fail");
        for incidence in &cell.incidences {
            write!(
                out,
                "incidence {} {} {}",
                cell.generator.id.entity(),
                incidence.face,
                incidence.sign
            )
            .expect("Writing to String cannot fail");
            if let Some((id, shift)) = incidence.neighbour {
                write!(out, " some {}", id.entity()).expect("Writing to String cannot fail");
                put_image(&mut out, shift);
            } else {
                out.push_str(" none");
            }
            put_vector(&mut out, incidence.chart_translation);
            out.push('\n');
        }
        bounded_output(&out)?;
    }
    for (index, face) in geometry.faces().iter().enumerate() {
        write!(out, "face {index} {}", face.left).expect("Writing to String cannot fail");
        if let Some(right) = face.right {
            write!(out, " some {right}").expect("Writing to String cannot fail");
        } else {
            out.push_str(" none");
        }
        match face.key {
            FaceKey3::Interior { lo, hi, hi_image } => {
                write!(out, " interior {} {}", lo.entity(), hi.entity())
                    .expect("Writing to String cannot fail");
                put_image(&mut out, hi_image);
            }
            FaceKey3::Boundary { cell, patch } => {
                write!(out, " boundary {} {}", cell.entity(), patch.0)
                    .expect("Writing to String cannot fail");
            }
        }
        put_image(&mut out, face.right_wrapped_image);
        put_scalar(&mut out, face.area);
        put_vector(&mut out, face.normal);
        put_vector(&mut out, face.centroid_offset);
        put_scalar(&mut out, face.plane_distance);
        put_tensor(&mut out, face.covariance);
        writeln!(out, " {}", face.polygon.len()).expect("Writing to String cannot fail");
        for (ordinal, vertex) in face.polygon.iter().enumerate() {
            write!(out, "vertex {index} {ordinal}").expect("Writing to String cannot fail");
            put_vector(&mut out, *vertex);
            out.push('\n');
            bounded_output(&out)?;
        }
    }
    out.push_str("quality");
    let quality = geometry.quality();
    put_scalar(&mut out, quality.relative_volume_closure);
    put_scalar(&mut out, quality.maximum_normal_closure);
    put_scalar(&mut out, quality.maximum_affine_closure);
    put_scalar(&mut out, quality.maximum_centroid_closure);
    writeln!(
        out,
        " {} {} {}\nend",
        quality.certified_contact_planes, quality.clipping_planes, quality.predicate_operations
    )
    .expect("Writing to String cannot fail");
    bounded_output(&out)?;
    Ok(out)
}

fn run(path: &Path) -> Result<()> {
    let metadata = path.symlink_metadata().map_err(|error| error.to_string())?;
    if !metadata.is_file() || metadata.len() > MAX_INPUT_BYTES {
        return Err("Expected a regular bounded input file".to_owned());
    }
    let file = File::open(path).map_err(|error| error.to_string())?;
    if !file
        .metadata()
        .map_err(|error| error.to_string())?
        .is_file()
    {
        return Err("Input handle is not a regular file".to_owned());
    }
    let mut raw = String::new();
    file.take(MAX_INPUT_BYTES + 1)
        .read_to_string(&mut raw)
        .map_err(|error| error.to_string())?;
    if raw.len() as u64 > MAX_INPUT_BYTES {
        return Err("Input exceeds byte limit".to_owned());
    }
    let output = render(&raw)?;
    // Do not stream a success prefix before geometry validation has returned.
    std::io::stdout()
        .lock()
        .write_all(output.as_bytes())
        .map_err(|error| error.to_string())
}

fn main() -> ExitCode {
    let arguments: Vec<_> = std::env::args_os().collect();
    if arguments.len() != 2 {
        eprintln!("Expected exactly one geometry3 input-file argument");
        return ExitCode::FAILURE;
    }
    match run(Path::new(&arguments[1])) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("geometry3 candidate export rejected: {error}");
            ExitCode::FAILURE
        }
    }
}
