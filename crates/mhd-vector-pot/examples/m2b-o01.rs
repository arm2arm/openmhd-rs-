//! Evaluate one external manufactured stencil. The wire input contains only
//! the fit selector, component, volume, mean field and keyed observations.
use mhd_vector_pot::operators3::{recover, trace};
use moving_mesh::three_d::{
    Image3,
    fit::{FitOrder3, PointFit3, SampleKey3, StencilSample3},
};
use std::{
    error::Error,
    io::{self, Read},
};

fn main() -> Result<(), Box<dyn Error>> {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    let mut lines = input.lines();
    let header: Vec<_> = lines
        .next()
        .ok_or("wire header")?
        .split_whitespace()
        .collect();
    if header.len() != 7 || header[0] != "M2B1" {
        return Err("wire header".into());
    }
    let order = match header[1] {
        "linear" => FitOrder3::Linear,
        "quadratic" => FitOrder3::Quadratic,
        _ => return Err("fit selector".into()),
    };
    let component: usize = header[2].parse()?;
    if component >= 3 {
        return Err("component".into());
    }
    let word = |s: &str| u64::from_str_radix(s, 16).map(f64::from_bits);
    let volume = word(header[3])?;
    let mean = [word(header[4])?, word(header[5])?, word(header[6])?];
    let mut rows = Vec::new();
    let mut observations = std::collections::BTreeMap::new();
    for line in lines {
        let r: Vec<_> = line.split_whitespace().collect();
        if r.len() != 9 || r[0].len() != 32 || !r[0].is_ascii() {
            return Err("wire sample".into());
        }
        let id = SampleKey3::from_words(
            u64::from_str_radix(&r[0][..16], 16)?,
            u64::from_str_radix(&r[0][16..], 16)?,
            Image3([r[1].parse()?, r[2].parse()?, r[3].parse()?]),
        );
        let delta = [word(r[4])?, word(r[5])?, word(r[6])?];
        let area = if r[7] == "-" { None } else { Some(word(r[7])?) };
        rows.push(StencilSample3 {
            key: id,
            displacement: delta,
            face_area: area,
        });
        let mut a = [0.; 3];
        a[component] = word(r[8])?;
        if observations.insert(id, a).is_some() {
            return Err("duplicate sample key".into());
        }
    }
    let fit = match PointFit3::build(order, volume, rows) {
        Ok(f) => f,
        Err(e) => {
            println!("reject {e}");
            return Ok(());
        }
    };
    let values = fit
        .samples()
        .iter()
        .map(|s| observations[&s.key])
        .collect::<Vec<_>>();
    let out = recover(&fit, &values, mean)?;
    let scalar = out.potential[component];
    println!(
        "fit {} {} {:.17e} {:.17e} {:.17e}",
        fit.quality.samples,
        fit.quality.rank,
        fit.quality.kappa1_r,
        fit.quality.kappa1_bounds[0],
        fit.quality.kappa1_bounds[1]
    );
    fn display(label: &str, values: impl IntoIterator<Item = f64>) {
        print!("{label}");
        for x in values {
            print!(" {:016x}", x.to_bits());
        }
        println!();
    }
    display("value", [scalar.value]);
    display("gradient", scalar.gradient);
    display("field", out.field);
    display("div_a", [out.div_a]);
    display("residual", [scalar.weighted_rms_residual]);
    if let Some(h) = scalar.hessian {
        display("hessian", h.into_iter().flatten());
    }
    if let Some(j) = out.same_fit_jacobian {
        display("curl_jacobian", j.into_iter().flatten());
        display("div_b_same_fit", [trace(j)]);
    }
    Ok(())
}
