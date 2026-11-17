# Prospective pressure-weighted HLLD/HLL comparison (2026-11-10, #24)

Declared before implementation or execution. The [shock-only correction](M1_SHOCK_SENSOR_PLAN.md)
is active but fails the column boost gate at 7.50395e-6; both N32 vortices pass.
Global HLL passes that shock but fails the regular vortex divergence norm.
Keep both failed experiments and all original thresholds.

## Motivation and source boundary

[Simon & Mandal (2018), §7, Eqs. (99)–(100), §8–9](https://arxiv.org/html/1803.04954#S7)
use a minimum neighbouring gas-pressure ratio raised to an exponent to control
HLLC antidiffusion. Their selected exponent is three. Their analysis also
distinguishes density and momentum perturbations: modifying mass transport
alone need not stabilize every shock. This motivates a broader bounded
comparison; it does not prove our slow-shock instability has the same cause.

Our proposed **MHD extension is not their HLLC-ADC algorithm**: blend the
entire HLLD and HLL flux vectors, including induction, using one scalar.
Use all faces incident on either owner on a Voronoi mesh, rather than their
Cartesian transverse stencil. No external code is copied. This is also an
engineering departure from Springel et al.'s HLLD, not an AREPO claim.

## Fixed definition

For a face with owners L and R and positive unreconstructed cell gas
pressures, let K contain every face incident on L or R. Define

```text
omega = min over k in K of (min(p_left(k),p_right(k)) /
                            max(p_left(k),p_right(k)))^3
F = omega F_HLLD + (1-omega) F_HLL.
```

The exponent is fixed at the source's value, not a fitting parameter. No
case-name, coordinate-direction, shock-strength threshold or row-symmetry
switch is used. The scalar is invariant under owner reversal, rotation,
uniform boosts and pressure-unit changes. Constant gas pressure gives
omega=1, preserving HLLD for contacts and rotational discontinuities.
For smooth positive pressure omega approaches one with mesh refinement;
the wave convergence and loop gates must nevertheless be measured.

Use the existing common normal B, signal bounds and face-rest-frame states.
Blend all eight flux components with the same weight before the ALE transform;
blend the admissible intermediate states for the original completion, while
preserving the signal-weighted completion of the quadratic candidate.
If HLLD is inadmissible, retain the counted HLL fallback. At weights exactly
one and zero return the historical HLLD and HLL arithmetic respectively.
One shared face still contributes equal and opposite conservative updates.
No general positivity or entropy-stability guarantee is inferred from blending.

Use explicit `--riemann hlld-pressure` / `hlld-pressure-blend-v1` metadata,
initially restricted to the fixed/rigid quadratic profile with the existing
screened projection. Keep all earlier flux choices available. Record the
actual weight and frozen flux differences separately from the earlier theta
correction; do not combine the two modifications.

## Bounded progression

On REANA verify endpoint parity, full flux convexity, uniform/contact states,
joint boosts, rotations and owner reversal, pressure-stencil invariance and
periodic conservative coupling. Run format, strict Clippy, release/all-target
Rust and Python/M0 checks.

Then repeat the registered eight-case shock/vortex comparison with HLLD,
HLL and this new choice: nx1024 regular/column Brio base/boost to t=.1 and
N32 regular/jitter vortex base/boost to t=.5. All 96 HLLD/HLL scientific
control files must match. Require the unchanged 1e-8 shock boost gate,
original shock reference/Bx/seam limits, vortex mean-field/divergence gates,
positivity, budgets and all boost pairs. Correct observational shock windows
to rest-frame coordinates; preserve the original sensor report's absolute-x
window and document that reporting error.

Use eight two-thread cases, 16-GB memory, 600-second case limits. Tests and
evolutions run only on REANA. Escalate to all five bounded stages and full
gates only on success. A failed trial blocks the long campaign; do not tune
the exponent or relax the gates. Full M1 acceptance and separate final review
remain outstanding.
