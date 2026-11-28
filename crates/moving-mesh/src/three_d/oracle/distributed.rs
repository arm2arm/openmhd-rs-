//! Exchange the three original defining halfspaces per clipped vertex. Reconstructing
//! the exact intersections preserves the dyadic coordinates and their rounding during
//! moment integration. Every receiver runs the ordinary manifold and closure checks.
use super::*;
use mhd_io::{Decoder, Encoder, digest};
use mhd_parallel::{layout::Layout, partition::Partition};

impl OwnerClipping<'_> {
    fn packet(&self, owner: usize, generation: &[u8; 32]) -> std::result::Result<Vec<u8>, String> {
        let planes = self.planes(owner).map_err(|e| e.to_string())?;
        let mut budget = Budget::default();
        let polygons = self.clip(&planes, &mut budget).map_err(|e| e.to_string())?;
        let mut e = Encoder::new();
        e.bytes(generation);
        e.usize(owner);
        for n in [
            budget.predicates,
            budget.planes,
            budget.contacts,
            polygons.len(),
        ] {
            e.usize(n);
        }
        for p in polygons {
            e.usize(p.plane);
            e.usize(p.vertices.len());
            for v in p.vertices {
                for index in v.defining {
                    e.usize(index);
                }
            }
        }
        Ok(e.finish())
    }
    fn receive(
        &self,
        owner: usize,
        generation: &[u8; 32],
        packet: &[u8],
        result: &mut OwnerAssembly,
    ) -> std::result::Result<u64, String> {
        let mut d = Decoder::new(packet);
        if d.bytes()? != generation || d.usize()? != owner {
            return Err("different clipping generation or owner".into());
        }
        let predicates = d.usize()?;
        let planes_count = d.usize()?;
        let contacts = d.usize()?;
        let clipping = Budget {
            predicates,
            planes: planes_count,
            contacts,
        };
        if !result.budget.can_append(&clipping) {
            return Err(GeometryError3::ResourceLimit("predicate operations").to_string());
        }
        let planes = self.planes(owner).map_err(|e| e.to_string())?;
        if planes_count > planes.len() || contacts > predicates {
            return Err("invalid clipping work counters".into());
        }
        let count = d.count(16)?;
        if !(4..=clip::MAX_FACES).contains(&count) {
            return Err("invalid number of owner polygons".into());
        }
        let mut polygons = Vec::with_capacity(count);
        // Reconstruction performs extra local checks, excluded from the serial-equivalent
        // predicate ledger. Its own hard budget stays active.
        let mut extra = Budget::default();
        for _ in 0..count {
            let plane = d.usize()?;
            let n = d.count(24)?;
            if plane >= planes.len() || !(3..=256).contains(&n) {
                return Err("invalid owner polygon header".into());
            }
            let mut vertices = Vec::with_capacity(n);
            for _ in 0..n {
                let indices = [d.usize()?, d.usize()?, d.usize()?];
                if indices.iter().any(|&i| i >= planes.len()) {
                    return Err("unknown vertex support in clipping packet".into());
                }
                vertices.push(
                    clip::intersection(indices, &planes, &mut extra).map_err(|e| e.to_string())?,
                );
            }
            polygons.push(clip::Polygon { plane, vertices });
        }
        d.finish()?;
        result.budget.append(clipping);
        self.finish_owner(owner, &planes, polygons, result)
            .map_err(|e| e.to_string())?;
        Ok(predicates.max(1) as u64)
    }
}

impl HalfSpaceOracle3 {
    /// Exact rank-owned clipping with a conservative, full-generator halo.
    /// Measured work per persistent owner can weight the next Morton partition.
    pub fn build_motion_layout<L: Layout>(
        domain: Domain3,
        sites: &[Generator3],
        partition: &Partition,
        layout: &L,
    ) -> std::result::Result<(ValidatedGeometry3, Vec<u64>), String> {
        Self::layout_inner(domain, sites, partition, layout, true, None)
    }
    /// Static geometry with the same plane inventory as the serial reference.
    pub fn build_layout<L: Layout>(
        domain: Domain3,
        sites: &[Generator3],
        partition: &Partition,
        layout: &L,
    ) -> std::result::Result<(ValidatedGeometry3, Vec<u64>), String> {
        Self::layout_inner(domain, sites, partition, layout, false, None)
    }
    /// Retains every active periodic bisector used by the differentiable field operators.
    pub fn build_supported_layout<L: Layout>(
        domain: Domain3,
        sites: &[Generator3],
        partition: &Partition,
        layout: &L,
    ) -> std::result::Result<(SupportedGeometry3, Vec<u64>), String> {
        if domain.boundary != Boundary3::Periodic {
            return Err(GeometryError3::InvalidDomain.to_string());
        }
        let mut support = Vec::new();
        let (geometry, weights) =
            Self::layout_inner(domain, sites, partition, layout, false, Some(&mut support))?;
        Ok((
            SupportedGeometry3 {
                geometry,
                support,
                cartesian_product: false,
            },
            weights,
        ))
    }
    fn layout_inner<L: Layout>(
        domain: Domain3,
        sites: &[Generator3],
        partition: &Partition,
        layout: &L,
        motion_bounds: bool,
        catalog: Option<&mut Vec<FaceVertexSupports3>>,
    ) -> std::result::Result<(ValidatedGeometry3, Vec<u64>), String> {
        if layout.ranks() != partition.ranks() {
            return Err("different layout and partition rank counts".into());
        }
        let generators = inputs(domain, sites).map_err(|e| e.to_string())?;
        let width = domain.width.map(D::from_f64);
        let length = domain.width.into_iter().fold(0.0_f64, f64::max);
        let work = OwnerClipping {
            generators: &generators,
            domain,
            width: &width,
            length,
            motion_bounds,
            supported: catalog.is_some(),
        };
        let mut id = Encoder::new();
        id.string("openmhd-owner-clip-v1");
        id.floats(&domain.width);
        id.floats(&domain.anchor);
        id.boolean(domain.boundary == Boundary3::Periodic);
        id.boolean(motion_bounds);
        id.boolean(work.supported);
        let mut owners = Vec::with_capacity(generators.len());
        for site in &generators {
            let entity = site.id.entity();
            id.u64(entity.namespace());
            id.u64(entity.counter());
            id.floats(&site.position);
            for wind in site.winding.0 {
                id.u64(wind as u64);
            }
            owners.push(partition.owner(entity)?);
        }
        let generation = digest(&[&id.finish()]);
        let parts = layout.packets(&owners, |i| work.packet(i, &generation))?;
        if parts.len() != owners.len() {
            return Err("incomplete owner clipping exchange".into());
        }
        let mut result = OwnerAssembly::default();
        let mut weights = Vec::with_capacity(parts.len());
        for (i, p) in parts.into_iter().enumerate() {
            weights.push(work.receive(i, &generation, &p, &mut result)?);
        }
        let g = Self::finish_geometry(result, &generators, domain, width, length, catalog)
            .map_err(|e| e.to_string())?;
        Ok((g, weights))
    }
}
