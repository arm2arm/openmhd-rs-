//! A fixed-width row has one producer and zero or more consumer ranks.
//! Repeated periodic images share the transferred row, not the numerical incidence.
use std::collections::BTreeMap;

#[derive(Debug)]
pub struct HaloPlan {
    owners: Vec<usize>,
    receivers: Vec<Vec<usize>>,
}
impl HaloPlan {
    pub fn new(
        owners: Vec<usize>,
        needs: impl IntoIterator<Item = (usize, usize)>,
    ) -> Result<Self, String> {
        let mut receivers = vec![Vec::new(); owners.len()];
        for (row, rank) in needs {
            receivers
                .get_mut(row)
                .ok_or("halo dependency outside row catalog")?
                .push(rank);
        }
        for peers in &mut receivers {
            peers.sort_unstable();
            peers.dedup();
        }
        Ok(Self { owners, receivers })
    }
    pub fn owners(&self) -> &[usize] {
        &self.owners
    }
    pub fn receivers(&self, row: usize) -> &[usize] {
        &self.receivers[row]
    }
    pub fn wanted(&self, row: usize, rank: usize) -> bool {
        self.receivers[row].binary_search(&rank).is_ok()
    }
    pub fn validate(&self, ranks: usize) -> Result<(), String> {
        if self
            .owners
            .iter()
            .chain(self.receivers.iter().flatten())
            .any(|&r| r >= ranks)
        {
            return Err("halo owner or receiver outside communicator".into());
        }
        Ok(())
    }
}
pub type HaloRows<const N: usize> = BTreeMap<usize, [f64; N]>;

/// Each face ordinal, in canonical order, appears on its physical incidences.
/// A self-image contributes no net exchange; each image face still has a producer.
pub struct FaceHalo {
    pub to_faces: HaloPlan,
    pub to_cells: HaloPlan,
    pub incidences: Vec<Vec<(usize, bool)>>,
}
impl FaceHalo {
    pub fn new(
        cells: Vec<usize>,
        faces: Vec<usize>,
        endpoints: &[(usize, Option<usize>)],
    ) -> Result<Self, String> {
        if faces.len() != endpoints.len() {
            return Err("face owner and endpoint counts differ".into());
        }
        let mut to_faces = Vec::new();
        let mut to_cells = Vec::new();
        let mut incidences = vec![Vec::new(); cells.len()];
        for (j, (&producer, &(left, right))) in faces.iter().zip(endpoints).enumerate() {
            for (i, forward) in [(Some(left), true), (right, false)] {
                if let Some(i) = i {
                    let &rank = cells.get(i).ok_or("face endpoint outside cell catalog")?;
                    to_faces.push((i, producer));
                    to_cells.push((j, rank));
                    if right != Some(left) {
                        incidences[i].push((j, forward));
                    }
                }
            }
        }
        Ok(Self {
            to_faces: HaloPlan::new(cells, to_faces)?,
            to_cells: HaloPlan::new(faces, to_cells)?,
            incidences,
        })
    }
}
