# Issue #7: prospective wave/loop validation and mean-field boost investigation

Registered after issue #6 and before new #7 measurements. The existing `paper-global-v2` [physical packet](../benchmarks/m1/packet-v2.json) and all historical results remain unchanged. This work adds the Alfvén/loop initial conditions, analytic comparisons, reproducible runs/plots and the unresolved nonuniform mean-field boost investigation. It does not declare a successful benchmark result in advance.

## Mean-field boost mechanism: prospective checks

At identical initial A/phi, boost fluid and generators by b, and take one common step dt. Put c=b cross mean_B. Initial A rates differ by c. Endpoint A_star differs by dt*c, while phi_star, H and the old-data fluid predictor are matched in translated coordinates. The target-baseline donor difference annihilates constant shifts. Thus the predicted first-step identity is

```text
A1_boost - A1_base = dt*c - (dt²/2) H1^T c
B1_boost - B1_base = -(dt²/2) curl_LS(H1^T c).
```

H1 is the analytically differentiated frozen auxiliary interpolant sampled at the endpoint, not an LS derivative of u. The second identity tests a mixed discrete/analytic derivative commutator; it is not inferred from the continuum curl(grad)=0 identity. Verify each component in the actual coupled step with absolute error <=1e-11, common dt=1e-4, N8/16 regular/jitter .15, and mean_B=(.3,.2,.1), boost=(2,-1,0), using the smooth initial state from issue #6. Require exactly one accepted step in both runs. Directly record the predicted and observed B residual norms and their difference.

For the unchanged v2 method, run that smooth case through t=.02 at N8/16/32/64 on regular/jittered meshes, dt cap=.00025, plus a temporal ladder at N16 with caps .001/.0005/.00025. Record volume-weighted vector-B and transformed-velocity L1/L2, pressure/density/energy errors, max errors, all diagnostics/counters, and every refinement order. These are mechanism/diagnostic observations; no retroactive success tolerance or required order is assigned to the known discrepancy. All successful evolved cases must remain finite/positive and satisfy the existing 1e-10 conservative-budget gate. Failed runs remain recorded failures.

## Optional prospective gauge comparator (requires design review)

Name a new profile `bulk-frame-v1`; preserve the default `paper-global-v2`. Fix V_ref = initial total momentum / initial total mass, which is constant for the periodic conservative gas system. Represent the total periodic potential as A=a+C, C(0)=0, C_dot=V_ref cross mean_B. Evolve a using the existing rates except the mean-field source becomes `(u-V_ref) cross mean_B`; distortion uses a, and cleaning uses div(a). Curl and div ignore the uniform C analytically, so compute them directly from a to avoid subtractive cancellation. Expose C and the reconstruction convention in outputs.

This chooses gauge psi=u dot a rather than psi=u dot A. It is an explicit continuum-equivalent gauge amendment with a different discrete algorithm, not a correction to a misquoted paper equation. Simply substituting A=a+C into v2 would retain an extra `-H^T C` term; this comparator intentionally omits that term through the changed gauge, rather than pretending it is just a storage reparameterization. It adds no fictitious force and does not alter lab-frame gas fluxes, generator motion, auxiliary origin, limiting, cleaning C1 or CFL bounds. Under a joint boost, V_ref shifts by b and the a/phi equations are covariant; total A gains the expected mean-field gauge offset. Do not silently replace the paper profile or reuse its name.

Before acceptance of this comparator: verify the algebra/one-step identity; reproduce issue #6 uniform/gauge cases; repeat the nonuniform mean-field boost ladder above with componentwise transformed rho/p/v/B/energy errors <=1e-9 and matching auxiliary roots; test nonzero phi, a three-component boost, a rectangular jittered mesh and prescribed/fluid-following motion. Record total A and reduced a separately. Retain the v2 discrepancy as measured historical evidence. Any failed prospective comparator gate remains a failure.

## Wave/loop benchmark protocol

Use the original packet's periodic unit-square N32/64/128/256 ladders and deterministic jitter family. Alfvén travelling/standing states use the derived R1 potential, rho=1, p=.1, gamma=5/3, mean B=(1,0,0), transverse amplitude .1, v_parallel=0/1 and output t=0,.25,1. Initial discrete/analytic curl error is separate from final physical error. Report fitted L1 order over the finest three N values and the original order>=1.8, finest B L1/.1<=.02 gate. Preserve the original N64 temporal ladder and same-grid finer-dt reference; gauge and physical-field accuracy remain distinct.

Loop A_z=.001/sqrt(4pi)*max(0,.3-r), rho=p=1, v=(2,1,0), mean B=0, gamma=5/3, t=1. Keep prescribed-flow transport and coupled-MHD comparisons distinct. Use fixed/comoving regular/jittered geometries and joint boost (2,-1,0); retain the original .001 relative coupled-B boost gate and all positivity/budget gates. Do not treat analytic passive transport as an exact coupled finite-field solution. Report magnetic energy and all three divergence operators along with errors. Keep original failed or unexecuted gate statuses explicit.

## Equivalent computational improvements

The current all-pairs clipping construction and repeated complete geometry validation are too costly for large square reference meshes. Before changing either, verify an exact regular Cartesian Voronoi constructor against the existing clipping builder on square/rectangular boxes, all periodic face images, cell volumes/centroids, neighbour/face derivatives and limiter output. Geometry remains explicit and validated, with persistent IDs and shared oriented faces. Jittered/general geometry continues to use checked clipping unless a separately verified candidate-pruning implementation is added.

Cache only validated immutable geometry/stencils, and batch scalar-component limiting so validation occurs once per shared mesh rather than once per field. Never cache state-dependent extrema or gradients. Compare identical initial states through multiple steps on fixed/rigid and deforming meshes against the original outputs before accepting an optimization; ordinary relative-plus-absolute equivalence tolerance is 1e-11. Do not reduce transverse resolution or substitute a different integrator for the declared N-by-N benchmark without labelling a separate diagnostic experiment. Record measured runtime and any unexecuted configurations honestly.

## Review and delivery

Run workspace format/Clippy/build/tests, deterministic small numerical fixtures, declared studies and separate labelled AI design/implementation review. Archive configs, code/compiler provenance, numeric tables, plots and limitations. Closing #7 requires its work items and acceptance checks to be concretely accounted for; passing #7 alone does not establish shock/vortex or the full M1 scientific release.

### Prospective clipping acceleration, preserving arithmetic order

The exact Cartesian shortcut is withdrawn from this change: its multi-step equivalence gate failed for a rectangular, initially regular, mean-zero, fluid-following fixture (potential difference 6.83e-10 after two steps, versus the registered 1e-11 bound). An independent AI probe traced the sensitivity to nearly zero normal-field HLLD intermediate states, despite essentially identical conservative fluxes. This is a recorded failure, not a relaxed tolerance or a reason to change the historical flux routine without a separate investigation.

Instead, prospectively test a bounding tree over contiguous generator-ID ranges. Traverse left before right, preserving every surviving plane's original pass/j/sx/sy order. Skip a whole range only when a conservative lower bound on all its periodic-image distances exceeds the *current* polygon's enclosing-circle clipping rejection bound (including an outward floating-point margin). Every skipped plane would have taken the existing no-op circle-rejection branch; do not use seed clipping, reorder planes or discard a plane merely because it is redundant in the final polygon. Preserve an explicit all-pairs builder. Require bit-identical cells/faces against that builder on regular/jittered, rectangular, translated, deformed and permuted fixtures, matched rejection of invalid/duplicate points, and identical multiple-step evolved states with both initial constructors. This is computational pruning only, not a new mesh definition or a new numerical profile.

### Alfvén boost normalization clarification

The M0 packet fixes a relative-L1 boost threshold of 1e-8, but did not uniquely tabulate the Alfvén boost field scales. The initial study's absolute-max gate label was therefore incorrect and is withdrawn; the raw norms/evolved snapshots remain valid. For these already executed runs report both conventions: `(B_scale,v_scale)=(.1,.1)` from transverse-wave amplitude, and `(1,max(sqrt(v_parallel²+.01),sqrt(1/6)))` from mean B and initial speed/sound speed. In both use rho_scale=1, p_scale=.1 and exact unboosted E_scale=.66+.5*v_parallel². Classify agreement under both conventions explicitly; mixed outcomes remain normalization clarification pending. This is a post-run clarification, not a claim that either exact table was unambiguously preregistered. For future studies adopt the wave-amplitude table prospectively, while continuing to report both. Geometry/time pairing must pass independently before interpreting any boost norm.
