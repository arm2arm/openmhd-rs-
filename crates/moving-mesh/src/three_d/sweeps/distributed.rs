//! Conservative update on the Euler/Heun union of canonical faces.
use super::*;
use mhd_parallel::halo::{FaceHalo, HaloPlan};

impl SharedSweeps3 {
    /// Read conserved states and physical face exchanges on their producers only.
    /// A rank may supply just its owned input rows. The complete output ledger is
    /// assembled on rank zero; cell owners perform the canonical compensated sum.
    pub fn exchanges_to_root_on<const N: usize, L: Layout>(
        &self,
        physical: &BTreeMap<FaceKey3, [f64; N]>,
        old: &BTreeMap<CellId, [f64; N]>,
        predicted: Option<&BTreeMap<CellId, [f64; N]>>,
        part: &Partition,
        layout: &L,
    ) -> Result<Option<SweepExchange3<N>>, String> {
        layout.agree(&[u8::from(self.predictor), u8::from(predicted.is_some())])?;
        if part.ranks() != layout.ranks() || predicted.is_some() == self.predictor {
            return Err("invalid distributed sweep stage".into());
        }
        let keys: Vec<_> = self.faces.keys().copied().collect();
        let cells = self
            .owners
            .iter()
            .map(|id| part.owner(id.entity()))
            .collect::<Result<Vec<_>, _>>()?;
        let index: BTreeMap<_, _> = self
            .owners
            .iter()
            .enumerate()
            .map(|(i, &id)| (id, i))
            .collect();
        let endpoints: Vec<_> = keys
            .iter()
            .map(|k| match k {
                FaceKey3::Interior { lo, hi, .. } => (index[lo], Some(index[hi])),
                FaceKey3::Boundary { cell, .. } => (index[cell], None),
            })
            .collect();
        // The canonical left ID is the smaller persistent ID for interior faces.
        let faces = endpoints.iter().map(|&(l, _)| cells[l]).collect();
        let routes = FaceHalo::new(cells, faces, &endpoints)?;
        let read = |state: &BTreeMap<CellId, [f64; N]>, i: usize| {
            state
                .get(&self.owners[i])
                .copied()
                .filter(|v| v.iter().all(|x| x.is_finite()))
                .ok_or_else(|| format!("missing or nonfinite sweep state at row {i}"))
        };
        let initial = layout.halo_rows("sweep-old", &routes.to_faces, |i| read(old, i))?;
        let provisional = predicted
            .map(|q| layout.halo_rows("sweep-predicted", &routes.to_faces, |i| read(q, i)))
            .transpose()?;
        let flux = layout.halo_rows("sweep-faces", &routes.to_cells, |j| {
            let key = keys[j];
            let mut v = *physical.get(&key).ok_or("missing owned physical sweep")?;
            let (l, r) = endpoints[j];
            if let Some(r) = r.filter(|&r| r != l) {
                let predicted_pair = provisional.as_ref().map(|q| (&q[&l], &q[&r]));
                apply_correction(
                    &mut v,
                    self.faces[&key].correction,
                    &initial[&l],
                    &initial[&r],
                    predicted_pair,
                );
            }
            if v.iter().any(|x| !x.is_finite()) {
                return Err("nonfinite sweep exchange".into());
            }
            Ok(v)
        })?;
        let root_plan =
            |owners: &[usize]| HaloPlan::new(owners.to_vec(), (0..owners.len()).map(|i| (i, 0)));
        let increments = layout.halo_rows(
            "sweep-output-cells",
            &root_plan(routes.to_faces.owners())?,
            |i| {
                let mut sums = [Sum::default(); N];
                for &(j, forward) in &routes.incidences[i] {
                    for (s, x) in sums.iter_mut().zip(flux[&j]) {
                        s.add(if forward { -x } else { x });
                    }
                }
                let v = sums.map(Sum::get);
                if v.iter().any(|x| !x.is_finite()) {
                    return Err("nonfinite sweep increment".into());
                }
                Ok(v)
            },
        )?;
        let output = layout.halo_rows(
            "sweep-output-faces",
            &root_plan(routes.to_cells.owners())?,
            |j| Ok(flux[&j]),
        )?;
        Ok((layout.rank() == 0).then(|| SweepExchange3 {
            faces: output.into_iter().map(|(j, x)| (keys[j], x)).collect(),
            cell_increments: increments
                .into_iter()
                .map(|(i, x)| (self.owners[i], x))
                .collect(),
        }))
    }
}
