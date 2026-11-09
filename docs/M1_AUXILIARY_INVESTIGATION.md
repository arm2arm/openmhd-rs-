# Auxiliary projection and temporal convergence — prospective contract

## Hypothesis and scope (2026-11-08)

The existing auxiliary field is C1 in position for a fixed set of corner jets.
However, rebuilding those jets assigns each fluid cell wholly to its nearest
auxiliary corner. A moving origin can transfer a cell abruptly between bins,
changing the corner averages discontinuously even for smooth fluid data. This
is a candidate cause of the jittered standing wave's reduced Heun time order;
the existing evidence does not yet separate it from limiting and face switches.

Add a separately named engineering comparator, `bulk-frame-heun-spline-v1`.
It changes only the projection from volume-weighted nearest-bin averages to
normalized tensor-product cubic weights. It retains reevaluated Heun, the
moving auxiliary origin, signal-weighted face completion, spatial stencils,
cleaning, conservation and positivity/retry rules. It supports fixed/rigid
meshes only. All historical profiles and the default remain unchanged. This
is not an algorithm attributed to the paper and does not establish M1 acceptance.

For a sample with auxiliary-grid coordinate q, let j=floor(q), f=q-j. Deposit
to corners j-1,j,j+1,j+2 with weights

```
[(1-f)^3, 4-6f^2+3f^3, 1+3f+3f^2-3f^3, f^3] / 6.
```

Use periodic indices and tensor products in x/y, including summed periodic
aliases when the grid has fewer than four intervals. Each corner velocity is
sum(V_i W_i v_i)/sum(V_i W_i). Keep the original 4/2/1 global coarsening rule
for empty support. The weights sum to one and are C2 across support/grid
boundaries; normalized averages are smooth while denominators stay positive.
Root changes remain a potential nonsmooth event and must be recorded. The
global volume-mean velocity and origin evolution are unchanged.

## Checks declared before implementation/measurement

* Unit checks: partition of unity and nonnegative weights, periodic aliases,
  constant preservation, translation/boost covariance, invalid inputs, and
  continuity of both velocity and its spatial Jacobian when a sample crosses
  an old bin boundary. Retain a fixture demonstrating the old finite jump.
* Apply the existing fixed/rigid uniform, smooth coupled time-order,
  three-component boost/permutation and deterministic threading tests to the
  new comparator. Keep the same budget <=1e-10 and positivity requirements.
* Freeze the previous binary; require old profiles' initial/final CSVs and
  history to remain byte-identical on small deterministic fixtures.
* REANA factorial comparison: two Heun profiles, limiting enabled/disabled,
  regular/jitter=.15 meshes, travelling/standing waves. N32, t=.04, caps
  .0004/.0002/.0001 and finite reference .000025; 64 evolutions plus 16 boosted
  counterparts at .0001. Use up to 24 independent one-thread simulations.
  The quick check uses N8, t=.004 and is not a physical acceptance packet.
* Report B/v/A/phi time errors and adjacent slopes, analytic wave errors,
  budgets/positivity, all three divergence operators, actual dt/rejections,
  roots/coarsenings and boost/geometry errors. Compare each profile to its own
  fine-step reference; different auxiliary projections define different
  semidiscrete systems. Existing boost limits (wave-relative <=1e-8 and
  geometry <=1e-9) are unchanged. No new physical acceptance threshold.

Improved slopes would support this hypothesis only within the tested packet;
they would not repair the known irregular-mesh curl/spatial or N256 boost
failures. Disabling limiting is a diagnostic, not a proposed shock-safe default.
