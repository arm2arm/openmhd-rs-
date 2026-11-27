# A 3D collisionless merger with 100 particles per galaxy

Two spherical progenitors start five length units apart on a bound, off-centre orbit. Each contains exactly 100 live, equal-mass particles. Every particle interacts gravitationally with the other 199. IDs and progenitor labels persist throughout the evolution. The run uses dimensionless units with $G=1$ and mass one per progenitor.

## Initial conditions and evolution

The density model is a Plummer sphere with scale radius 0.55 and radial cutoff 2.2. Each galaxy has 50 stratified enclosed-mass radii, with an independently chosen isotropic axis and two antipodal particles at each radius. Given radius $r$, the squared speed as a fraction of the squared escape speed is drawn from $\mathrm{Beta}(3/2,9/2)$. Velocities are isotropic and antipodally paired. The two seeds are 20261127 and 20261128. A single rescaling per galaxy enforces $2K=-W$ for its realized softened internal forces, where $W=\sum_i m_i\,\mathbf r_i\cdot\mathbf a_i$. This supplies a low-resolution, initially virialized galaxy model. [Plummer sampling background, section 4.3.3](https://arxiv.org/pdf/astro-ph/0610872#page=8).

| Parameter | Value |
| --- | --- |
| Particle mass | 0.01 |
| Initial centres | $(-2.5,0,0)$ and $(2.5,0,0)$ |
| Initial bulk velocities | $(0.12,0.14,0.05)$ and its negative |
| Boundary and force law | Isolated, direct pairwise Newtonian gravity with fixed Plummer softening $\epsilon=0.25$ |
| Integrator | Synchronized kick–drift–kick |
| Standard run | 10,240 steps of $1/256$ to $t=40$ |
| Recorded states | Initial state and every 0.125 time units, 321 samples |

Gas, stars as a separate material component, and dark-matter subcomponents are outside this single-species experiment. The two colours identify galaxies of origin. Every particle carries mass and responds to the same three-dimensional force law.

## Diagnostics fixed before execution

The standard merger, a same-seed isolated copy of galaxy A, and a merger with half the timestep run separately. The latter two use the same saved times. At every saved time, an independent NumPy pair sum checks the Rust accelerations, total energy, momentum and angular momentum. The scaled force tolerance is $10^{-12}$, the scaled ledger tolerance $10^{-11}$ and the relative energy-drift limit $5\times 10^{-4}$.

To follow surviving cores, tag the 20 initially most-bound particles of each isolated progenitor by specific internal energy and keep their IDs fixed. Each core position is the componentwise median of its tracers. The remnant centre uses the componentwise median of all particles. Its inner half comprises the 100 nearest particles.

The finite-run mixed-remnant criterion uses the interval $32\leq t\leq40$. Both the 90th percentile of the core separations in that interval and the final separation must lie below one initial progenitor half-mass radius. Each origin must contribute at least 25% of the inner half at every sampled time in that interval. At least 90% of the full system must be instantaneously bound at the last endpoint, using the total potential with self terms excluded and velocities in the system centre-of-mass frame. Record the continuous diagnostics even when any criterion fails.

## Reproduce

Build the Rust release example, then give the Python case driver a fresh output directory. The driver requires Python 3 and NumPy. Select `isolated` or `merger-half-dt` to reproduce either comparison.

~~~sh
cargo build --release --locked -p gravity --example gravity-trajectory
python3 reana/nbody_merger_100.py merger target/release/examples/gravity-trajectory merger-output
~~~

The driver exports 3D positions, velocities, accelerations, initial core IDs, and the Rust conservation ledger. [Case driver](../../reana/nbody_merger_100.py) · [Rust trajectory exporter](../../crates/gravity/examples/gravity-trajectory.rs).
