# General-solver shock/vortex execution contract

This implements the existing M0 packet, not new physical tolerances. The first
candidate is `bulk-frame-heun-spline-v1`; historical profiles remain available.
Before the full study, preliminary N64 Brio and N16 vortex probes established
that the driver can evolve these configurations. Those probes are not passes
of the registered resolution ladders.

* Brio-Wu: gamma=2, periodic [0,2] x [0,1/8], total nx=256/512/1024, ny=4,
  interface x=1, mean B=(.75,0,0), t=.1. Track x-characteristic travel in the
  fixed/rigid mesh frame, integrating dt times the maximum over reconstructed
  left/right states at both accepted stages and the final cell closure.
  Rejected attempts do not advance physical time. The bound must remain <.45
  to certify characteristic isolation from the second periodic interface.
  This is not a strict numerical-domain-of-dependence proof.
* Orszag-Tang: gamma=5/3, unit periodic square, N64/128/256, t=.5, the M0
  normalized density/pressure/velocity/Az fields and mean B=0.
* Both cases: regular and the existing jitter=.15 mesh family, base and joint
  fluid/grid boost (2,-1,0). These produce 24 full evolutions, with no floors,
  energy resets or changed limiter/flux/stencil. Quick execution checks use
  Brio nx=64/128 and vortex N16/32, preserving final times; they leave full
  profile gates unexecuted. Run large cases on REANA with 24 independent workers.

The exact oriented Voronoi half-planes are exported. The measurement script
clips them to recover each cell polygon, checks its area against the recorded
cell volume, retains explicit unwrapped vertices, and checks periodic area
coverage. Reference comparison uses polygon-overlap areas: average fine
Athena primitive samples over each candidate shock cell before taking its
absolute error; integrate candidate vortex primitive samples into fixed 64²
bins before comparing with the pinned reference averages. No point sampling
across shocks or primitive recovery from averaged conservative variables.

The M0 rho/p/vx/By and rho/p/Bx/By profile limits, finest-better-than-coarsest
checks, Bx/mean-B/divergence requirements, positivity and <=1e-10 budgets stay
unchanged. Regular families are the packet's primary profile gates; jittered
profile errors are reported separately, with required state/budget/diagnostic
checks. Both families must pass the registered 1e-8 boost bound. Use fixed
packet rho/p/B scales; velocity and energy comparison scales are the unboosted
initial budget scales (momentum divided by mass scale, and energy divided by
domain volume). Report per-field L1 and geometry differences, not an aggregate
that can hide failures. Compare only complete, same-time, persistent-ID data.

Retain initial discrete-curl errors, raw extrema, all three divergence
operators, mean-field drift, phi/div(A), counters, failure files, exact commands,
compiler/platform/source/reference/output hashes and projected data. Source
hashes and gates must not change within a submitted study. Passing this packet
alone is insufficient for M1: the full wave/loop/mean-field gates still apply.
