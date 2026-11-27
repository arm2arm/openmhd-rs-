# Moving 3D Voronoi generators and oriented faces

`moving_mesh::three_d::advance_generators3` advances a validated mesh through a finite interval with one prescribed, constant velocity per persistent cell ID. It returns a fresh geometry and a sorted correspondence between the positive-area faces at the two endpoints. Use the returned geometry as the input to the next step. The serial half-space reference supports up to 512 generators in a periodic orthorhombic box or a stationary box with six walls.

```rust
let step = advance_generators3(&mesh, &generator_velocities, dt)?;
let owner = step.geometry.cell_by_id(id).ok_or("unknown cell")?;
for face in step.geometry.oriented_faces(owner)? {
    let outward = face.outward_normal();
    let polygon = face.vertices().collect::<Vec<_>>();
    // Polygon coordinates are offsets from this owner's generator.
    // face.handle addresses the canonical area and motion rate in this epoch.
}
```

## Geometry contract

In a periodic box the lifted position is $r_i=x_i+Lk_i$, with wrapped coordinates $x_i$ and checked integer windings $k_i$. The drift removes whole box widths before adding the remaining displacement to the wrapped coordinates. This preserves the generator's small offset during a large translation. A neighbor with wrapped image $s$ has trajectory image $s+k_i-k_j$. That image and the two persistent IDs identify the shared face across a seam. A wall face is keyed by its owner and wall patch. Rebuilds use the validated static oracle, with exact dyadic side predicates and binary64 geometric moments. Invalid velocities, image overflow, an out-of-domain endpoint or a failed rebuild leave the input geometry usable.

Both interior owners refer to the same polygon and area. The builder compares the two independently clipped polygon loops by exact rational vertex equality, allowing a cyclic shift and requiring reverse traversal after translation. The owner view reverses the normal and polygon loop on the right while keeping vertex zero as the common fan pivot. A periodic self-face has two incidences on the same cell in different image charts. A wall has one outward incidence. Handles from an earlier epoch are rejected by the rebuilt geometry.

A retained face has handles into both epochs. An appearing or disappearing face has one. These records describe the sampled geometries. An intermediate face can have positive area even if both endpoints lack it. The separate moving-MHD milestone requires event isolation, time-integrated shared exchanges and a finite-step geometric-conservation law. [3D mesh specification](MESH_3D_SPEC.md) · [Physical exchange gates](MOVING_MHD_STAGE_SPEC.md).

## Run a moving mesh

The driver consumes the same text catalog as `lloyd3-step`. It uses the prescribed velocities, with the sound-speed column reserved for the Lloyd driver. Each argument after the filename is a positive time increment. This example samples the analytic five-generator contact at $t=0$, $1/2$ and $1$.

```sh
cargo run --release --locked -p moving-mesh --example moving-voronoi3 -- \
  docs/galaxy/fixtures/m2c_tessellation_flip.txt 0.5 0.5 > mesh.csv
```

The CSV has one row per outward polygon vertex per incidence. It records the wrapped generator position, windings, volume, epoch-local face index, sign, neighbor and trajectory image (or wall patch), face area, outward normal and vertex offset. Add the vertex offset to the owner's position to draw the polygon in that chart. The driver writes the counts of retained, appearing and disappearing faces for each step to standard error.

## Validation protocol

The reference cases use binary64, prescribed linear paths and code units of length and time. The mesh rebuild is independent of fluid variables. Each selection runs on one REANA CPU with 4 GiB after the frozen workspace format, strict Clippy and locked release build. The registered M01 geometry cases have a 600-second execution budget each. The 8³ case enables the previously qualified larger exact-predicate budget. [M01 and M02 registration](MESH_3D_SPEC.md).

- **Rigid periodic translation.** Use 4³ and 8³ cell-centered cubic lattices, velocity $(2,-1,1/2)$ and $\Delta t=2.75$. All winding integers and wrapped coordinates must match the analytic lift. Match all face keys and require normalized volumes, face areas, normals and centroid offsets to agree within $10^{-10}$.
- **Smooth finite differences.** Use a 4³ Cartesian product lattice, first periodic and then bounded. In each axis, the four velocity samples are $(0,1,0,-1)$ times $1/8$, $1/16$ or $-1/8$ respectively. In a coordinate interval, the faces are the midpoints of neighboring generators, with fixed exterior walls. Their velocities give exact widths, volumes, centroid paths and face speeds. Evaluate at $\pm h$ for $h=1/128,1/256,1/512,1/1024$. The centered volume derivative of a product of three linear widths has error $h^2\dot l_x\dot l_y\dot l_z$. Divide the maximum error by the initial cell volume (one code time unit). Require adjacent orders of at least 1.8 and finest error at most $10^{-7}$. Compare endpoint volumes, centroids and instantaneous velocities to the analytic values within $10^{-12}$.
- **Birth and death of a triangular face.** Three equatorial sites lie on the circle of radius $5/16$ around the origin. Two poles start at $z=-5/16$ and $6/16$; the upper pole moves at $-1/8$. The pole-to-pole bisector meets the three equatorial bisectors in a point at $t=1/2$. At $t=1$ the new face has area $1/192$, centroid $(-1/288,0,-1/32)$ and outward normal $(0,0,1)$ for the lower pole. Reversing the path must remove it and restore the original key set.
- **Shared-face consistency.** Reintegrate the owner-oriented polygon fans and signed cell tetrahedra independently. Check positive winding, areas, per-cell normal closure, volumes and total box volume to $10^{-10}$ in the corresponding local scales. Exercise self-neighbors at windings above $2^{53}$, irregular periodic shear with reversed input order, stale handles and atomic rejection. The example-driver run uses the same five input sites and is checked independently from its CSV.

### Exact motion-epoch bounds

A motion rebuild still enumerates every admitted generator and image. Before clipping it can use the closest exactly axis-aligned bisectors and the six initial box planes to bound the cell in each signed coordinate direction. Let $b_{k,-}, b_{k,+}$ be those six distances from the generator and put

$$R^2=\sum_{k=1}^3 \max(b_{k,-},b_{k,+})^2.$$

A bisector with generator separation $d$ is at distance $|d|/2$. If $|d|^2/2 > 2R^2$, every point in the bounding box lies strictly on the owner's side. Such a plane can be removed. Exact dyadic comparisons retain equality, so contacts at a box corner remain eligible. The builder keeps the six initial planes and the planes that define the tighter bounds. Without a tighter bound it uses the full inventory. The static and vertex-support entry points retain their original schedules.

An additional control compares this path with the full clipping inventory on a periodic 27-site Cartesian product and a nine-site irregular fixed-wall catalog. Both comparisons must exercise actual pruning, preserve the complete face-key inventory, orientation, polygon vertices, areas, volumes and centroids, and pass independent reintegration of every cell. The original 600-second limit, both rigid resolutions and all physical tolerances apply to the revised implementation.
