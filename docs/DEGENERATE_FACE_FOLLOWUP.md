# HLLD degenerate-face observation from issue #7

This is an unresolved observation from a separate **AI review**, not an accepted flux revision. The conservative HLLD flux and its returned intermediate magnetic/velocity state have different sensitivities near a collapsed rotational/contact fan. The vector-potential face source uses `numerical_EMF - u cross B_face`, so checking conservative flux alone misses this issue.

For `rho=p=1`, `gamma=5/3`, normal `(0,-1,0)`, face velocity `(.2,-.1,0)`, auxiliary velocity `(.21,-.1,.04)`, left/right gas velocities `(.2 ± .00168128073437985,-.1,.04)` and `B=(0,By,-.004562414995177748)`:

- `By=±1e-18` selects double-star `Bx=±.00168128073437986` and `vx=.2`.
- `By=0` selects a single star with `Bx=0`, `vx=.20168128073437985`.
- Conservative flux changes are about `1e-21`, while the y component of the actual A-face source changes by `7.67e-6` at zero normal field.
- Reversing the normal and swapping left/right at exactly zero normal field preserves conservative flux orientation but changes that A-face source by `1.53e-5`.

The exact Cartesian-constructor experiment produced initial geometry differences of order `1e-16` compared with clipping. Fixed/rigid comparison fixtures passed, but a rectangular 6×8 fluid-following shear fixture exceeded the preregistered `1e-11` potential-equivalence gate after two steps (`6.83e-10`). The AI probe isolated the above returned-state sensitivity. The Cartesian shortcut was withdrawn. Ordered clipping pruning instead retains the original surviving plane arithmetic and passes bit-identical geometry comparisons. The flux routine has not been changed to hide the observation.

The [standalone AI probe](../tests/reference/m1_wave_loop/ai_degenerate_face.rs) and [measured output](../tests/reference/m1_wave_loop/ai_degenerate_face.log) are archived. Reproduce from the repository root:

```sh
cargo build --release --locked -p mhd-core
rustc --edition=2024 tests/reference/m1_wave_loop/ai_degenerate_face.rs \
  --extern mhd_core=target/release/libmhd_core.rlib -L dependency=target/release/deps \
  -o /tmp/openmhd-degenerate-face
/tmp/openmhd-degenerate-face
```

A fix first needs an explicit engineering convention for the A-face completion when the intermediate state is nonunique. Do not silently replace numerical EMF by `v_face cross B_face`, change the historical profile, or invent a threshold from successful outputs. Prospectively test signed normal-field amplitudes through zero, contact speeds through zero, one-ULP input perturbations, face rotations/reversal, cell-ID permutations and joint three-component boosts. Check the complete A-face source at the existing `1e-11` algebra tolerance as well as conservative orientation/flux identities. Include uniform controls, tangential velocity/B jumps, density contrasts, finite-normal-field rotational waves, positivity/fallback cases and the original geometry-equivalence fixture. Repeat #6/#7 physical packets after the convention is reviewed and implemented.
