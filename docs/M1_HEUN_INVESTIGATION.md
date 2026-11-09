# M1 time-integration investigation

## Prospective contract — 2026-11-08

M0 is accepted under the labelled AI review; M1 physical validation remains
open. The completed endpoint studies show weak physical time convergence,
including for `bulk-frame-signal-v1`. Those results and profiles remain intact.
This investigation isolates a different time integrator; it is an engineering
comparator, **not** a correction attributed to the paper.

`bulk-frame-heun-v1` uses the same bulk-frame gauge, signal-weighted face
completion, raw/limited LS spatial operators, ideal-gas EOS and periodic mean
field as `bulk-frame-signal-v1`. It supports only fixed or constant rigid mesh
motion. Fluid-following and prescribed deforming motion are rejected explicitly.
For those supported meshes, integrated conservative quantities Q, reduced A,
phi and the auxiliary-grid origin form the semidiscrete state Y. At each stage
recover primitives using Q/V and curl(A), rebuild primitive/A limiting and the
auxiliary velocity from that stage's primitives and origin, and evaluate every
fluid, potential and cleaning rate. Face reconstruction is spatial only.

The stages are Y*=Y0+dt R(Y0), Y1=Y0+dt/2 [R(Y0)+R(Y*)], on the corresponding
rigid endpoint geometry. Unlike the historical endpoint method, stage two uses
Q*, curl(A*), phi*, refreshed auxiliary jets and freshly evaluated cleaning
div(A*) and sound speed. The origin rate is the volume-mean velocity at each
stage; periodic wrapping occurs after the unwrapped sum. The fixed gauge-offset
rate remains Vref cross mean_B. Every conservative face exchange is shared and
opposite. Both stages and final closure must be finite and positive; retain
the existing CFL, cleaning, transport and immutable-retry checks. Record second
stage auxiliary roots/coarsening separately. There are no floors or energy resets.

## Checks declared before implementation

* Small deterministic Rust checks: reject unsupported motion; constant-state
  preservation; three-component boost and cell-permutation agreement; positive
  states and normalized conservative budgets <=1e-10; finite values for each of
  the existing three independent magnetic divergence diagnostics.
* On a smooth, unlimited N8 fixed-mesh problem with all coupled fields active,
  halve dt three times at fixed final time. Require self-difference ratios
  between 3.4 and 4.6 for Q, A, phi and B, with no rejections and dt caps reached.
  This is a bounded semidiscrete time-order check, not physical spatial validation.
* A dedicated REANA study compares historical signal and Heun wave time ladders
  on regular and jitter=.15 fixed meshes, travelling and standing waves. Use
  N32, t=.04, caps .0004/.0002/.0001 and finite reference .000025. Report B/v/A/phi
  time errors, adjacent slopes, conservation, all divergence operators, actual
  timesteps, rejections and auxiliary roots. No acceptance threshold is added
  retroactively to the earlier M1 temporal packet.
* Include base/boost pairs (2,-1,0) at the .0001 cap with mesh velocity shifted
  by the boost, recording field/geometry errors against the existing 1e-8
  wave-relative boost bound. Keep failures visible.

Auxiliary bin membership, root changes, slope limiting and Riemann branches can
make the semidiscrete operator nonsmooth. A smooth small-case Heun order check
does not prove order across those switches or repair irregular-mesh curl error.
The N256 boost failure and general shock/vortex validation remain separate work.

Results will be appended after measurement. The existing full Linux baseline
studies remain frozen and running independently on REANA.
