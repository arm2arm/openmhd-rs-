# M2c cubic divergence rule, revision 2

The owner authorized a separately named validation rule on 2026-11-27. The registered identifier is `m2c-shared-face-cubic-divergence-v2`. It applies to the opt-in shared-face quadratic curl with the face-adjacency stencil. Revision 1 retains both cubic strict-decrease failures. The numerical method, binary, magnetic sampling and irregular-mesh gates are unchanged. [Revision 1 measurements](M2C_MOVING_CURL_RESULTS.md#cell-average-field-and-divergence) · [Original dimensional roundoff budget](M2B_CLOSURE_PROTOCOL.md).

## Scope and prospective controls

Use the periodic unit cube, binary64, h=1/N and N=8,16,32. Use two background fields, zero and (0.3,−0.2,0.4). The static native binary is the previously validated 217560c build with SHA-256 `23564f5544474264c09cc9ffb03fcc8788cd0ed4afbbbf968a29d20baf084052`. Submit one fresh 2-CPU, 8-GiB REANA workflow per field, background and resolution. Freeze this protocol and the measurement source before submission.

- Equal wave numbers use the original cyclic potential Aₖ = sin(2πxⱼ) sin(2πxₗ), with j and l the next two axes after k.
- The held-out equal-wave test shifts x, y and z by 1/11, 2/13 and 3/17 box lengths inside the trigonometric functions. Its magnetic reference is the analytic cell-average curl, including the exact cube sinc factor. These phase-shifted cases have no prior candidate outputs.
- Unequal wave numbers use only A_z = sin(2πx) sin(4πy). The two magnetic components have the common cell-average factor sinc(π/N) sinc(2π/N), with sinc(u) = sin(u)/u. Unequal wave numbers break the axis-exchange cancellation. The original zero-background results of this control and both unshifted equal-wave ladders were already known. The new measurements explicitly compare their native input and output hashes with the original workflows.

For both equal-wave fields, the cell-fit and arithmetic-face divergences cancel on the cubic mesh in exact arithmetic. The dimensional binary64 RMS bound is

$$
128\epsilon_{64}\left[(2\pi+\|\overline{\mathbf B}\|_2)/h+1/h^2\right].
$$

Every affected operator at **every** resolution must satisfy this original budget. The limited-face RMS must decrease strictly on every halving. On both unequal-wave ladders all three measured RMS values must exceed the budget and decrease strictly on both refinements. Independently calculate arithmetic-face divergence and the six-neighbour centered divergence from the native field. They must reproduce the two corresponding native measurements within the same dimensional roundoff budget. For every null case, add a known 2⁻³⁰ sin(2πx) perturbation to Bₓ in a diagnostic copy. Its independently recomputed divergence RMS must exceed the budget. Retain the original and perturbed measurements separately.

All equal-wave ladders retain field order ≥1.8 and finest relative L1 ≤0.1. All cases retain the 10⁻⁹ scaled mean bound and the 10⁻¹² scaled signed shared-face divergence bound. For the six irregular mesh families, reuse the 36 original hash-verified workflows and recheck all 12 strict ladders. No irregular family or unequal-wave control is eligible for the roundoff exception. The rule concerns these Fourier fixtures; localized fields, other stencil policies, time integration, topology changes and physical MHD acceptance have their own gates.
