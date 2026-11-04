# M0 benchmark packet, version 1

The machine-readable [packet](../benchmarks/m0/packet.json) fixes the initial serial-reference problems, units, configurations, resolution ladders and acceptance tolerances for issue #2. The profile is [paper-global-v1](M0_ENGINEERING_DECISIONS.md); its full implementation is future M1 work. Existing planar pilot results keep their original gates and limitations. This packet does not declare that the future solver has passed.

## Registration and scope

Commit `56c6b1e` registered the packet and external input files before the first external runs or evaluation of any new candidate solver against them. Commit `624b211` added the missing Brio velocity reference-refinement tolerance before computing any refinement metric; only one unchanged boundary row had been inspected while debugging the table parser. Later changes increased history-output precision and checked time/boundary/conservation metadata; the profile-error tolerances were not tuned to outcomes. Previous small pilot results were known when selecting these future gates.

These are the initial M1 cases: circularly polarized Alfvén wave, kinematic loop transport plus coupled-loop boost checks, Brio-Wu and Orszag-Tang at t=.5. Later vortex t=1/2.5, full 3D, nonperiodic boundaries, local timesteps and MPI need separate extensions. An analytic transport solution is not claimed as the exact coupled finite-field loop solution.

## Configurations and initial fields

All runs use f64, nondimensional length/density/time, mu0=1, global timesteps, no explicit resistivity and no entropy energy reset. Initial phi=0. Periodic B is fixed mean_B plus the unlimited discrete curl of periodic A. Initialize total energy from the **discrete** B to preserve the prescribed initial gas pressure; separately report initial discrete-vs-analytic B error. Uniformly translating generators retain persistent cell IDs and unwrapped paths.

The regular generator positions are `((i+.5)Lx/nx,(j+.5)Ly/ny)`. The irregular family is the current deterministic `Mesh::lattice` formula, with `k=i+nx*j`:

```text
x=(i+.5+.15*sin(1.7*k+.3))*Lx/nx
y=(j+.5+.15*cos(2.3*k+.7))*Ly/ny
```

There is no random seed. Fix this formula in all reference configurations; changing it creates a new family. Regular meshes are the primary profile gates; the jittered family must independently satisfy physical-state, budget and diagnostic gates and report its own error sequence. Do not combine their fitted orders.

**Alfvén:** unit periodic square, all three vector components, gamma=5/3, rho=1, p=.1, amplitude a=.1, mean_B=(1,0,0). At phase `theta=2pi[x+(1-v_parallel)t]`, the analytic physical solution is

```text
v=(v_parallel, a sin(theta), a cos(theta))
B=(1, a sin(theta), a cos(theta))
```

Initialize `A=(0,a*sin(2pi*x)/(2pi),a*cos(2pi*x)/(2pi))`. This is the derived correction to printed R1, explicitly not a verbatim paper initialization. The travelling and standing cases have v_parallel=0 and 1. At later times compare physical B/v to the analytic wave; A/phi depend on the implemented gauge and are not assigned the initial formula translated as an exact general-gauge solution. For a boost b use phase `2pi[x+(1-v_parallel-b_x)t]` and add b to v; translate mesh coordinates when that mode is configured. Spatial B errors fit the finest three values of N=32,64,128,256, with order >=1.8 and finest L1/.1 <=.02. At fixed N64 use the listed dt ladder against the same-grid finer-dt reference, report order, and distinguish physical B from the first-order gauge-cleaning mode. Initial B/curl error must be reported separately from evolution error.

**Loop:** unit periodic square, gamma=5/3, rho=p=1, v=(2,1,0), mean_B=0, `Az=.001/sqrt(4pi)*max(0,.3-r)`, with r the periodic distance to (.5,.5). Exact prescribed-flow transport is `A(x,y,t)=A_initial(wrap(x-2t),wrap(y-t))`. B inside the loop is `amplitude*(-dy/r,dx/r,0)` and zero outside; the centre and cusp are excluded from pointwise analytic B comparisons. Fixed/comoving, regular/jittered resolution families and the added boost (2,-1,0) are distinct configurations. The coupled version uses the physical gas equations and is judged by budgets, positivity, a boosted comparison and resolution trends; finite magnetic feedback precludes an exact unchanging-gas assertion.

**Brio-Wu:** candidate periodic `[0,2] x [0,1/8]`, gamma=2, interface x=1, zero v. Left rho=1,p=1,By=1; right rho=1/8,p=.1,By=-1; mean_B=(.75,0,0). Use `Az=-x` for x<1 and `Az=x-2` otherwise, Ax=Ay=0. The total candidate nx is 256/512/1024 over length 2 (128/256/512 cells per unit length), ny=4. Analyse x∈[.5,1.5] at t=.1. The independent Athena domain is [-.5,.5] with outflow boundaries and interface zero; translate its x by +1. Its unmodified endpoint boundary states are verified. For the periodic candidate, record the integrated maximum signal travel over all stages and require <.45 so the seam does not influence the central comparison. This diagnostic must be implemented before certifying a candidate result.

**Orszag-Tang:** unit periodic square, gamma=5/3, rho=25/(36pi), p=5/(12pi), v=(-sin(2pi*y),sin(2pi*x),0), mean_B=0 and `Az=[cos(2pi*y)/(2pi)+cos(4pi*x)/(4pi)]/sqrt(4pi)`. Compare N64/128/256 at t=.5 on a fixed 64² bin grid. Athena's unmodified generator uses [-.5,.5]² with different apparent trigonometric signs. The coordinate transformation (x,y)_candidate=(x,y)_Athena+(.5,.5) exactly reproduces these initial formulas. No vector component sign flip is needed. Athena initializes its face B by a staggered curl, so its initial cell B differs at finite resolution from a cell-centred LS curl; report that representation error.

## Norms, budgets, boosts and output contract

For analytic smooth fields, `L1(q)=sum(V_i |q_i-q_exact(c_i,t)|)/sum(V_i)` and L2 is the square root of the corresponding weighted square mean. Vector B errors use Euclidean magnitude. Report component errors too. Spatial fit is least squares of log(error) against log(1/N), over the predeclared finest three resolutions; never select a favourable range afterward.

For regular shock columns, conservatively average the independent fine-cell **primitive sample field** over each candidate x-cell interval, then volume-average the absolute differences across all candidate rows in the central unit interval. For jittered Voronoi cells, use exact polygon overlap with the reference's vertical slabs, clipping at the analysis-interval boundaries. Normalize by the fixed packet scales, not a solution-dependent denominator. Do not interpolate point values across a discontinuity. For the vortex, integrate each candidate piecewise-constant primitive sample field into the fixed 64² bins, using exact overlap areas for irregular polygons; compare these averages with the archived reference bin averages. This projection is linear in the sampled primitive field. Averaging primitive pressure is not the same as recovering pressure from averaged conservative quantities; do not interchange them. Save unprojected extrema as well as bin errors so aggregation cannot hide invalid states.

Conservation residuals use total cell mass, momentum and total energy, subtracting integrated boundary/source contributions. Normalize each by `max(sum_i |Q_i(0)|, Vbox*Qscale,1e-30)` with fixed initial scales: rho_scale, rho_scale*v_scale for each momentum component, and the initial thermal+kinetic+magnetic energy density scale; v_scale=max(initial max|v|, initial max cs). Use the packet budget tolerance 1e-10. The independent unit-domain shock ledger has boundary rates (mass,px,py,pz,E)=(0,.9,-1.5,0,0), derived from the prescribed left/right stresses; the periodic vortex rates are zero. Its reported absolute reference residual is also checked against 1e-10 in these nondimensional unit boxes.

Joint boosts compare density/pressure/B in the same physical coordinates after subtracting b*t; subtract b from velocity and apply the corresponding kinetic-energy transform before comparing conservative states. Use relative L1 with the same fixed field scales. Case-specific gates override global defaults: the coupled loop B boost gate is .001; the default 1e-8 applies to other boost configurations. A is gauge-dependent, particularly with mean B, and is not required to match untransformed. Failed tight boost gates are reported as failures, not assumed passed from continuum invariance.

Record all three divergence operators from [COUPLED_2D.md](COUPLED_2D.md): raw neighbour LS, arithmetic-face sum and separately limited-face sum. Record dimensionless RMS/max using the fixed Bfloor convention in the engineering decisions, volume-weighted mean B and drift, initial curl error, phi/div(A), extrema, gas budgets, LS condition indicators, rejected attempts by cause and flux fallback counts. Fixed/rigid translation uniform states can use roundoff gates; deforming meshes require measured temporal order and geometric conservation error, not an unsupported machine-zero assertion.

For Bfloor=1e-12*Bscale, fix Bscale=1 for Alfvén (the mean field), .001/sqrt(4pi) for the loop, 1 for Brio-Wu and 1/sqrt(4pi) for the vortex. These diagnostic scales are separate from Alfvén's .1 transverse-wave error normalization.

Candidate snapshots use CSV columns `cell_id,x,y,volume,rho,p,vx,vy,vz,bx,by,bz,ax,ay,az,phi` plus explicit time and configuration/provenance metadata. Geometry for irregular-bin projections must include polygon vertices in the same periodic image. Existing pilot CSV adapters do not yet satisfy this full contract. Reference CSVs use `x,y,rho,p,vx,vy,vz,bx,by,bz`; shock rows retain native resolution, vortex rows are 64² averages. Every reference archive includes hashes, solver/compiler revision, input hashes, output times and build/run commands.

## Independent references and reproduction

[Athena++ v24.0](https://github.com/PrincetonUniversity/athena/tree/209a9258ee158d1965557f1a5c4193101b704dd9) is pinned at `209a9258ee158d1965557f1a5c4193101b704dd9`. Its [BSD-3-Clause license](https://github.com/PrincetonUniversity/athena/blob/209a9258ee158d1965557f1a5c4193101b704dd9/LICENSE) permits this use; the license is retained with the archive. Source and binaries are built outside the project and are not imported into the Rust implementation. Cite [Stone et al. (2020), Athena++](https://doi.org/10.3847/1538-4365/ab929b) when using these data scientifically.

The two codes share a published HLLD method but no implementation code. Athena evolves magnetic fields by constrained transport, independently of our A/curl representation. These are independently generated finite-resolution references, not author-supplied curves or exact solutions. The Athena VL2/PLM setup differs from the paper figure's piecewise-constant shock reference and is labelled accordingly.

```sh
# Standard Python library, git, make and clang++; external build has no MPI/OpenMP.
python3 scripts/run_external_references.py --jobs 4
python3 scripts/check_m0_spec.py
```

The runner clones the pinned tag if absent, rejects a wrong or modified source checkout, builds each problem, runs both resolutions, verifies final times/finite positive states, and checks refinement and conservation gates. Full raw outputs/build logs remain under `results/external_references/`; the small compressed CSV/history/license/provenance files are archived in `tests/reference/external_mhd/`. Reproduction may differ at floating-point roundoff across compilers; the recorded hashes identify the actual archived run, not a requirement for cross-platform byte equality.

## Measured reference uncertainty

The first independent study gives the following scaled L1 change upon reference refinement, before comparing the future general Rust method:

| Reference family | rho | p | vx | Bx | By |
| --- | --- | --- | --- | --- | --- |
| Brio 4096→8192, on 4096 bins | .000239061 | .000179467 | .000393430 | constant .75 | .000253376 |
| Vortex 256²→512², on 64² bins | .00642790 | .0120745 | reported profiles | .00986440 | .00881230 |

All preregistered reference-profile gates pass. These differences estimate resolution sensitivity on the stated comparison bins, not a rigorous error bound or proof of an entropy-selected unique shock solution. A candidate result must report both its discrepancy and this reference uncertainty. The finer runs are the primary stored comparison data; retain the coarser runs to make the uncertainty reproducible.

The final high-precision conservation ledgers have maximum absolute mass/momentum/energy residuals 7.88e-14 / 1.39e-13 for the two shock runs (after boundary-stress subtraction), and 5.44e-14 / 1.53e-12 for the two periodic vortex runs. All are below the 1e-10 gate; all final native densities/pressures are positive. The runner removes its generated history file before rerunning because Athena appends history; it rejects duplicate or nonmonotone times. Raw history bytes and compressed CSVs are retained with verified hashes. Run `python3 scripts/check_reference_packet.py` for offline archive checks, also enforced in CI.

Issue #2 concerns this versioned specification/input/reference packet. Passing the actual candidate gates, implementing the general profile and longer-time validation are M1 work. Any adjustment to these gates must create a new version with a stated reason and prospective runs; it must not retrospectively turn a failure into a pass.
