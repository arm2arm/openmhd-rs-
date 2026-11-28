use galaxy_types::{CellId, EntityId};
use moving_mesh::{parallel, three_d::*};
use std::num::NonZeroUsize;

fn team() -> NonZeroUsize {
    std::env::var("OPENMHD_TEST_THREADS")
        .unwrap_or("2".into())
        .parse()
        .unwrap()
}
fn sites() -> Vec<Generator3> {
    (0..27)
        .map(|i| {
            let pos = [i % 3, (i / 3) % 3, i / 9];
            Generator3 {
                id: CellId::new(EntityId::new(8, i as u64)),
                position: std::array::from_fn(|k| {
                    (pos[k] as f64 + 0.5 + ((19 * i + 7 * k + 3 * i * k) % 11) as f64 / 128.0) / 3.0
                }),
                winding: Image3::ZERO,
            }
        })
        .collect()
}
fn data(g: &ValidatedGeometry3) -> String {
    format!("{:?}|{:?}|{:?}", g.cells(), g.faces(), g.quality())
}
#[test]
fn three_d_owner_geometry_and_motion_match_in_serial_order() {
    let xyz = sites();
    let d = Domain3 {
        anchor: [0.0; 3],
        width: [1.; 3],
        boundary: Boundary3::Periodic,
    };
    let run = || {
        let g = HalfSpaceOracle3::build_motion_epoch(d, &xyz).unwrap();
        let w = g
            .cells()
            .iter()
            .enumerate()
            .map(|(i, c)| {
                (
                    c.generator.id,
                    [0.0625, ((i % 7) as f64 - 3.) / 256., -0.125],
                )
            })
            .collect();
        let rates = prescribed_motion_rates3(&g, &w, [0.; 3]).unwrap();
        let mut words = data(&g);
        for i in 0..g.faces().len() {
            words.push_str(&format!(
                "{:?}",
                rates.face(g.face_ref(i).unwrap()).unwrap()
            ));
        }
        for i in 0..g.cells().len() {
            words.push_str(&format!(
                "{:?}",
                rates.cell(g.cell_ref(i).unwrap()).unwrap()
            ));
        }
        let moved = advance_generators3(&g, &w, 0.03125).unwrap();
        words.push_str(&data(&moved.geometry));
        words
    };
    let expected = run();
    assert_eq!(parallel::with_team(team(), run).unwrap(), expected);
}

#[test]
fn periodic_active_supports_match_by_persistent_owner() {
    let xyz = sites();
    let d = Domain3 {
        anchor: [0.0; 3],
        width: [1.; 3],
        boundary: Boundary3::Periodic,
    };
    let run = || {
        let g = HalfSpaceOracle3::build_supported_periodic(d, &xyz).unwrap();
        let mut words = data(g.geometry());
        for i in 0..g.geometry().faces().len() {
            words.push_str(&format!(
                "{:?}",
                g.vertex_supports(g.geometry().face_ref(i).unwrap())
                    .unwrap()
            ));
        }
        words
    };
    assert_eq!(run(), parallel::with_team(team(), run).unwrap());
}

#[test]
fn morton_owner_handles_reordering_heavy_cells_empty_ranks_and_self_images() {
    use mhd_parallel::partition::{Partition, Site};
    let sites: Vec<_> = (0..8)
        .map(|i| Site {
            id: EntityId::new(1, i),
            position: [i as f64 / 7., 0., 0.],
            weight: 1,
        })
        .collect();
    let ranks = NonZeroUsize::new(4).unwrap();
    let build = |s: &[Site]| Partition::new(s, [0.; 3], [1.; 3], ranks);
    let base = build(&sites).unwrap();
    let mut shuffled = sites.clone();
    shuffled.reverse();
    let other = build(&shuffled).unwrap();
    for (i, s) in sites.iter().enumerate() {
        assert_eq!(base.owner(s.id).unwrap(), i / 2);
        assert_eq!(other.owner(s.id), base.owner(s.id));
        assert_eq!(base.face_owner(s.id, Some(s.id)), base.owner(s.id));
        assert_eq!(
            base.face_owner(s.id, Some(sites[0].id)),
            base.owner(sites[0].id)
        );
    }
    let mut uneven = sites.clone();
    uneven[0].weight = 128;
    let weighted = build(&uneven).unwrap();
    assert_ne!(weighted.owner(sites[0].id), base.owner(sites[0].id));
    assert!(build(&[]).unwrap().owner(sites[0].id).is_err());
    assert!(build(&[sites[0], sites[0]]).is_err());
    assert!(
        build(&[Site {
            weight: 0,
            ..sites[0]
        }])
        .is_err()
    );
}
