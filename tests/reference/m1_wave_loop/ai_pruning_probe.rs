use moving_mesh::Mesh;
fn main() {
    let mut seed = 0x735a91f4ca93u64;
    let mut next = || {
        seed = seed
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        ((seed >> 11) as f64) / (1u64 << 53) as f64
    };
    let mut valid = 0;
    let mut rejected = 0;
    for scale in [1e-9, 1.0, 1e9] {
        for variant in 0..8 {
            let lengths = [1.3 * scale, 0.7 * scale];
            let mut points = Vec::new();
            for j in 0..7 {
                for i in 0..8 {
                    points.push([
                        ((i as f64 + 0.5) + 0.45 * (next() - 0.5)) * lengths[0] / 8.,
                        ((j as f64 + 0.5) + 0.45 * (next() - 0.5)) * lengths[1] / 7.,
                    ]);
                }
            }
            for i in (1..points.len()).rev() {
                let k = (next() * (i + 1) as f64) as usize;
                points.swap(i, k);
            }
            if variant == 6 {
                points[1] = [points[0][0] + 1e-13 * scale, points[0][1]];
            }
            if variant == 7 {
                points[1] = [points[0][0] + lengths[0], points[0][1]];
            }
            let a = Mesh::build(points.clone(), lengths);
            let b = Mesh::build_all_pairs(points, lengths);
            match (a, b) {
                (Ok(a), Ok(b)) => {
                    assert_eq!(
                        format!("{a:?}"),
                        format!("{b:?}"),
                        "scale={scale} variant={variant}"
                    );
                    valid += 1;
                }
                (Err(_), Err(_)) => rejected += 1,
                (a, b) => {
                    panic!("classification mismatch scale={scale} variant={variant}: {a:?}/{b:?}")
                }
            }
        }
    }
    println!(
        "Independent shuffled jitter probes: {valid} bit-identical valid pairs, {rejected} matched near/periodic duplicate rejections"
    );
}
