# Prospective HLLD shock-sensor trial (2026-11-10, #24)

Declared before implementation or execution. Global HLL passes the finest
shock but fails the regular N32 vortex normalized divergence gate. Preserve
[both observations](../tests/reference/m1_hll_campaign/bounded_failure/README.md).
Neither blanket diffusion nor a different diagnostic normalization is adopted.

## Published correction and scope

[Minoshima & Miyoshi (2021), §2.1, Eqs. (9)–(13)](https://arxiv.org/html/2108.04991#S2.SS1)
reduce the total-pressure jump's contribution to HLLD's contact speed when
transverse compression exceeds normal compression. Their chosen exponent is
four. Test that correction with the ordinary intermediate pressure (Eq. (7));
leave the separate low-Mach modification off. This is their shock-only
comparison, not full LHLLD. Athena++'s
[implementation](https://raw.githubusercontent.com/PrincetonUniversity/athena/main/src/hydro/rsolvers/mhd/lhlld.cpp)
was consulted; no source code is imported. This adds engineering choices
relative to Springel et al., not undocumented AREPO behaviour.

Set `dL=rhoL*(SL-uL)`, `dR=rhoR*(SR-uR)`, `cf=max(cfL,cfR)` and use total
pressures `pTL,pTR`:

```text
theta = min(1, (cf-min(delta_normal,0)) / (cf-min(delta_transverse,0)))^4
SM = (dR*uR - dL*uL - theta*(pTR-pTL)) / (dR-dL)
Pstar = (dR*pTL - dL*pTR + dL*dR*(uR-uL)) / (dR-dL).
```

Do not derive `Pstar` from only the left state after modifying `SM`: that
introduces an unintended pressure change. Existing HLLD/HLL retain their
exact arithmetic. The new option may use historical HLLD exactly when
`theta=1`; otherwise use the expressions above and existing admissibility
checks/fallback. Every shared conservative face update remains equal/opposite.

## Explicit 2D Voronoi extension to test

The published sensor uses Cartesian neighbours. This is our own geometric
extension, requiring independent verification. For a face normal `n`, use
in-plane tangent `t=(-ny,nx)`. Let `dij` be the periodic centroid displacement
from cell i to face neighbour j and `dvij=vj-vi` the unreconstructed velocity
difference. Define:

```text
delta_normal = (vR-vL) dot n
delta_transverse = min(0, min over neighbours of L and R of
                      (dvij dot t) * (dij dot t) / |dij|).
```

On an orthogonal Cartesian mesh this reduces to the four transverse
differences of Eq. (12); normal neighbours contribute zero. On a Voronoi mesh
it projects both velocity difference and neighbour direction. It is symmetric
under exchanging owners, independent of uniform boosts, and covariant under
in-plane rotation. Verify these properties with manufactured fields and
periodic faces. There is no shock-strength threshold, case-name switch,
row-symmetry constraint or fitted coefficient. Keep exponent four; do not
tune it against these failed benchmarks.

Use separate explicit flux metadata, initially restricted to the existing
fixed/rigid quadratic candidate. Original endpoint, literal-state and global
HLL choices remain available. No positivity/general-stability guarantee is
claimed for this trial.

## Bounded evidence before escalation

1. On REANA run format, strict Clippy, release/all-target Rust tests,
   Python/M0 checks and new sensor/flux tests. Cover Cartesian reduction,
   affine-flow geometry, uniform/contact consistency, owner reversal,
   rotation and joint boosts. Check the pressure formula independently.
2. Compare HLLD, HLL and the new option on eight cases each: nx1024
   regular/column Brio base/boost at t=.1, and N32 regular/jittered vortex
   base/boost at t=.5. Require historical HLLD/HLL scientific-file hashes
   to match; keep their known failures visible.
3. The new option must pass unchanged shock boost/reference/Bx/seam and
   vortex mean-field/divergence gates with positivity, budgets and boosts.
   Record sensor activation and its effect near the problematic slow shock.
4. Only after this passes, rerun the five-stage bounded gate and subsequent
   full campaign. Full M1 still requires every gate and final review.

Use at most eight two-thread cases (16 worker cores), 16 GB memory and 600
seconds per case for the focused comparison, below the owner's 24-core / 64-GB
cap. All tests/evolutions run on REANA. A failure blocks long matrices.
